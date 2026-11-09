"""Create the expert CSV and transcript bundle for the false-negative audit.

The script reads the committed audit manifest, adds the original LLM output and
transcript metadata, downloads and formats each full transcript from WRDS, and
creates a ZIP archive for the human auditor. Generated files are kept under
`data/outputs/` and are not committed.
"""

#%%
import argparse
import csv
import json
import os
import shutil
import sqlite3
import time
import zipfile

import numpy as np
import pandas as pd

import config
from modules import capiq
from modules.utils import (
    extract_invalid_response,
    extract_score_from_unstructured_response,
    prep_transcript_for_review,
)

#%%
PROMPT_NAME = "SimpleCapacityV8.1.1"
MODEL_NAME = "gpt-4o-mini"
DEFAULT_SAMPLE_PATH = os.path.join(
    config.ROOT,
    "assets",
    "false_negative_audit_sample.csv",
)
DEFAULT_CSV_PATH = os.path.join(
    config.OUTPUTS_DIR,
    "false_negative_audit_for_expert.csv",
)
DEFAULT_BUNDLE_DIR = os.path.join(
    config.OUTPUTS_DIR,
    "false_negative_audit_bundle",
)
DEFAULT_ZIP_PATH = os.path.join(
    config.OUTPUTS_DIR,
    "false_negative_audit_bundle.zip",
)

#%%
parser = argparse.ArgumentParser(
    description="Create the false-negative audit spreadsheet and transcript bundle."
)
parser.add_argument("--sample", default=DEFAULT_SAMPLE_PATH)
parser.add_argument("--csv-output", default=DEFAULT_CSV_PATH)
parser.add_argument("--bundle-dir", default=DEFAULT_BUNDLE_DIR)
parser.add_argument("--zip-output", default=DEFAULT_ZIP_PATH)
parser.add_argument("--batch-size", type=int, default=20)
parser.add_argument(
    "--overwrite-transcripts",
    action="store_true",
    help="Download and replace transcript text files that already exist.",
)
args = parser.parse_args()

if args.batch_size <= 0:
    raise ValueError("--batch-size must be positive")

#%%
def extract_response_field(response, field, default=""):
    """Extract a field from a structured or recoverable LLM response."""
    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict):
            value = parsed.get(field, default)
        else:
            value = default
    except (json.JSONDecodeError, TypeError):
        value = extract_invalid_response(response, [field]).get(field, default)

    if field == "excerpts" and isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if value is None:
        return default
    return str(value)


#%%
print(f"Loading fixed audit sample: {args.sample}")
sample = pd.read_csv(args.sample)
required_sample_columns = {"transcriptid", "stratum", "original_score"}
missing_sample_columns = required_sample_columns - set(sample.columns)
if missing_sample_columns:
    raise ValueError(
        f"Audit sample is missing columns: {sorted(missing_sample_columns)}"
    )

sample = sample[["transcriptid", "stratum", "original_score"]].copy()
sample["transcriptid"] = pd.to_numeric(
    sample["transcriptid"], errors="raise"
).astype("int64")
sample["original_score"] = pd.to_numeric(
    sample["original_score"], errors="raise"
)

if len(sample) != 200:
    raise ValueError(f"Expected 200 sampled transcripts, found {len(sample):,}")
if sample["transcriptid"].duplicated().any():
    raise ValueError("Audit sample contains duplicate transcript IDs")
print(f"Loaded {len(sample):,} sampled transcripts")

#%%
print("Loading transcript metadata...")
metadata_path = os.path.join(
    config.DATA_DIR,
    "datasets",
    "main_analysis_dataset.feather",
)
metadata = pd.read_feather(
    metadata_path,
    columns=[
        "transcriptid",
        "companyname",
        "mostimportantdateutc",
        "headline",
    ],
)
metadata["transcriptid"] = metadata["transcriptid"].astype("int64")
metadata = metadata[metadata["transcriptid"].isin(sample["transcriptid"])].copy()

if metadata["transcriptid"].duplicated().any():
    raise ValueError("Transcript metadata contains duplicate transcript IDs")
if len(metadata) != len(sample):
    missing_ids = sorted(set(sample["transcriptid"]) - set(metadata["transcriptid"]))
    raise ValueError(f"Missing transcript metadata for IDs: {missing_ids}")

#%%
print("Loading original and repeated LLM queries...")
transcript_ids = sample["transcriptid"].astype(int).tolist()
placeholders = ",".join("?" for _ in transcript_ids)
with sqlite3.connect(config.DATABASE_PATH) as conn:
    queries = pd.read_sql_query(
        f"""
        SELECT query_id, transcriptid, response
        FROM queries
        WHERE prompt_name = ?
          AND model_name = ?
          AND transcriptid IN ({placeholders})
        ORDER BY query_id
        """,
        conn,
        params=[PROMPT_NAME, MODEL_NAME, *transcript_ids],
    )

queries["score"] = queries["response"].apply(
    extract_score_from_unstructured_response
)
if queries["score"].isna().any():
    bad_query_ids = queries.loc[queries["score"].isna(), "query_id"].tolist()
    raise ValueError(f"Could not extract scores for query IDs: {bad_query_ids}")

query_counts = queries.groupby("transcriptid").size()
missing_query_ids = sorted(set(transcript_ids) - set(query_counts.index.astype(int)))
if missing_query_ids:
    raise ValueError(f"No matching LLM query found for IDs: {missing_query_ids}")

query_rows = []
for transcriptid, group in queries.groupby("transcriptid", sort=False):
    group = group.sort_values("query_id")
    original = group.iloc[0]
    query_rows.append(
        {
            "transcriptid": int(transcriptid),
            "query_id": int(original["query_id"]),
            "database_original_score": float(original["score"]),
            "mean_score": float(group["score"].mean()),
            "n_queries": int(len(group)),
            "reasoning": extract_response_field(original["response"], "reasoning"),
            "excerpts": extract_response_field(original["response"], "excerpts"),
        }
    )
query_summary = pd.DataFrame(query_rows)

#%%
expert = sample.merge(query_summary, on="transcriptid", validate="one_to_one")
expert = expert.merge(metadata, on="transcriptid", validate="one_to_one")

if not np.allclose(
    expert["original_score"],
    expert["database_original_score"],
):
    mismatches = expert.loc[
        ~np.isclose(
            expert["original_score"],
            expert["database_original_score"],
        ),
        "transcriptid",
    ].tolist()
    raise ValueError(f"Manifest and database original scores differ for IDs: {mismatches}")

expert = expert.rename(columns={"transcriptid": "transcript_id"})
expert["T/F/U"] = ""
expert["JH comments"] = ""
expert = expert[
    [
        "transcript_id",
        "stratum",
        "query_id",
        "original_score",
        "mean_score",
        "n_queries",
        "reasoning",
        "excerpts",
        "companyname",
        "mostimportantdateutc",
        "T/F/U",
        "JH comments",
    ]
]

os.makedirs(os.path.dirname(args.csv_output), exist_ok=True)
expert.to_csv(
    args.csv_output,
    index=False,
    encoding="utf-8-sig",
    quoting=csv.QUOTE_ALL,
)
print(f"Saved expert spreadsheet: {args.csv_output}")

#%%
transcript_dir = os.path.join(args.bundle_dir, "transcripts")
os.makedirs(transcript_dir, exist_ok=True)

metadata_by_id = metadata.set_index("transcriptid")
ids_to_download = []
for transcriptid in transcript_ids:
    text_path = os.path.join(transcript_dir, f"{transcriptid}.txt")
    if args.overwrite_transcripts or not os.path.exists(text_path):
        ids_to_download.append(transcriptid)

print(
    f"Transcript files already present: "
    f"{len(transcript_ids) - len(ids_to_download):,}"
)
print(f"Transcript files to download: {len(ids_to_download):,}")

try:
    for start in range(0, len(ids_to_download), args.batch_size):
        batch_ids = ids_to_download[start:start + args.batch_size]
        batch_number = start // args.batch_size + 1
        batch_total = (len(ids_to_download) + args.batch_size - 1) // args.batch_size
        print(
            f"Downloading transcript batch {batch_number}/{batch_total} "
            f"({len(batch_ids):,} transcripts)..."
        )

        last_error = None
        transcript_json = None
        for attempt in range(1, 4):
            try:
                transcript_json = capiq.get_transcripts(batch_ids, limit=10_000_000)
                break
            except Exception as error:
                last_error = error
                if attempt == 3:
                    raise
                print(f"  Attempt {attempt}/3 failed: {error}. Retrying in 5 seconds...")
                capiq.disconnect()
                time.sleep(5)

        if transcript_json is None:
            raise RuntimeError(f"Failed to download transcript batch: {last_error}")

        missing_downloads = sorted(set(batch_ids) - set(transcript_json))
        if missing_downloads:
            raise ValueError(f"WRDS returned no transcript text for IDs: {missing_downloads}")

        for transcriptid in batch_ids:
            components = json.loads(transcript_json[transcriptid])
            formatted_transcript = prep_transcript_for_review(components)
            if not formatted_transcript.strip():
                raise ValueError(f"Formatted transcript is empty for ID {transcriptid}")

            row = metadata_by_id.loc[transcriptid]
            header = (
                f"Transcript ID: {transcriptid}\n"
                f"Company: {row['companyname']}\n"
                f"Date: {row['mostimportantdateutc']}\n"
                f"Headline: {row['headline']}\n"
                "\n"
            )
            text_path = os.path.join(transcript_dir, f"{transcriptid}.txt")
            temporary_path = f"{text_path}.tmp"
            with open(temporary_path, "w", encoding="utf-8") as text_file:
                text_file.write(header)
                text_file.write(formatted_transcript)
                if not formatted_transcript.endswith("\n"):
                    text_file.write("\n")
            os.replace(temporary_path, text_path)

        completed = min(start + len(batch_ids), len(ids_to_download))
        print(f"  Saved {completed:,}/{len(ids_to_download):,} downloaded transcripts")
finally:
    capiq.disconnect()

#%%
expected_text_paths = [
    os.path.join(transcript_dir, f"{transcriptid}.txt")
    for transcriptid in transcript_ids
]
missing_text_paths = [path for path in expected_text_paths if not os.path.exists(path)]
empty_text_paths = [
    path for path in expected_text_paths
    if os.path.exists(path) and os.path.getsize(path) == 0
]
if missing_text_paths or empty_text_paths:
    raise RuntimeError(
        f"Bundle validation failed: {len(missing_text_paths):,} missing and "
        f"{len(empty_text_paths):,} empty transcript files"
    )

bundle_csv_path = os.path.join(args.bundle_dir, os.path.basename(args.csv_output))
shutil.copy2(args.csv_output, bundle_csv_path)

os.makedirs(os.path.dirname(args.zip_output), exist_ok=True)
temporary_zip_path = f"{args.zip_output}.tmp"
with zipfile.ZipFile(
    temporary_zip_path,
    mode="w",
    compression=zipfile.ZIP_DEFLATED,
    compresslevel=6,
) as archive:
    archive.write(bundle_csv_path, arcname=os.path.basename(bundle_csv_path))
    for transcriptid, text_path in zip(transcript_ids, expected_text_paths):
        archive.write(text_path, arcname=f"transcripts/{transcriptid}.txt")
os.replace(temporary_zip_path, args.zip_output)

print("\nAudit bundle complete")
print(f"  Spreadsheet rows: {len(expert):,}")
print(f"  Transcript files: {len(expected_text_paths):,}")
print(f"  Bundle directory: {args.bundle_dir}")
print(f"  ZIP archive: {args.zip_output}")
