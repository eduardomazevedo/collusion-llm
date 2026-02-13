"""
Create manuscript labels for quoted excerpts in audit sections.

Builds labels of the form:
    Company Name | Event Type | DD Mon YYYY

for query IDs referenced in:
    manuscript/audit_types.tex
    manuscript/audit_errors.tex

Output:
    data/yaml/quoted_excerpt_labels.yaml
"""

#%%
import re
import sqlite3
from pathlib import Path

import pandas as pd
import yaml


#%%
ROOT = Path(__file__).resolve().parents[3]
TEX_CONFIGS = [
    {"name": "audit_types", "path": ROOT / "manuscript" / "audit_types.tex"},
    {"name": "audit_errors", "path": ROOT / "manuscript" / "audit_errors.tex"},
]
QUERIES_DB_PATH = ROOT / "data" / "datasets" / "queries.sqlite"
TRANSCRIPT_DETAIL_PATH = ROOT / "data" / "datasets" / "transcript_detail.feather"
OUTPUT_YAML_PATH = ROOT / "data" / "yaml" / "quoted_excerpt_labels.yaml"


def escape_latex(text: str) -> str:
    """Escape LaTeX-sensitive characters for safe insertion via \\data{}."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(text))


def format_date(value) -> str:
    """Format date as DD Mon YYYY."""
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return str(value) if pd.notna(value) else ""
    return dt.strftime("%d %b %Y")


def parse_query_ids(tex_path: Path, section_name: str) -> list[int]:
    """
    Parse query IDs from a section tex file.

    Supports:
    - Legacy style: $[123456]$
    - New style: [\\data{quoted_excerpt_labels/<section>/q123456}]
    """
    content = tex_path.read_text(encoding="utf-8")

    legacy_ids = [int(x) for x in re.findall(r"\$\s*\[(\d+)\]\s*\$", content)]
    new_pattern = rf"\\data\{{quoted_excerpt_labels/{section_name}/q(\d+)\}}"
    new_ids = [int(x) for x in re.findall(new_pattern, content)]

    # Keep order of appearance across both patterns, de-duplicated.
    ordered_ids = []
    seen = set()
    for qid in legacy_ids + new_ids:
        if qid not in seen:
            ordered_ids.append(qid)
            seen.add(qid)
    return ordered_ids


#%%
print("Parsing query IDs from manuscript audit sections...")
section_ids: dict[str, list[int]] = {}
for cfg in TEX_CONFIGS:
    ids = parse_query_ids(cfg["path"], cfg["name"])
    section_ids[cfg["name"]] = ids
    print(f"  {cfg['name']}: {len(ids)} query IDs")

all_ids = sorted({qid for ids in section_ids.values() for qid in ids})
if not all_ids:
    raise ValueError("No query IDs found in audit_types.tex or audit_errors.tex.")

print(f"Total unique query IDs: {len(all_ids)}")


#%%
print("Loading query -> transcript mapping from queries database...")
with sqlite3.connect(QUERIES_DB_PATH) as conn:
    placeholders = ",".join(["?"] * len(all_ids))
    query_map_df = pd.read_sql_query(
        f"""
        SELECT query_id, transcriptid
        FROM queries
        WHERE query_id IN ({placeholders})
        """,
        conn,
        params=all_ids,
    )

if len(query_map_df) != len(all_ids):
    found = set(query_map_df["query_id"].tolist())
    missing = [qid for qid in all_ids if qid not in found]
    raise ValueError(f"Missing query_id values in queries table: {missing}")


#%%
print("Loading transcript metadata...")
td_cols = ["transcriptid", "companyname", "keydeveventtypename", "mostimportantdateutc"]
transcript_df = pd.read_feather(TRANSCRIPT_DETAIL_PATH)[td_cols].copy()

meta_df = query_map_df.merge(transcript_df, on="transcriptid", how="left")

missing_meta = meta_df[
    meta_df["companyname"].isna()
    | meta_df["keydeveventtypename"].isna()
    | meta_df["mostimportantdateutc"].isna()
]
if len(missing_meta) > 0:
    missing_ids = sorted(missing_meta["query_id"].tolist())
    raise ValueError(f"Missing transcript metadata for query_id values: {missing_ids}")


#%%
print("Building labels YAML...")
labels_by_query_id = {}
for _, row in meta_df.iterrows():
    company = str(row["companyname"]).strip()
    event = str(row["keydeveventtypename"]).strip()
    date_str = format_date(row["mostimportantdateutc"])
    label = f"{company} | {event} | {date_str}"
    labels_by_query_id[int(row["query_id"])] = escape_latex(label)

yaml_out: dict[str, dict[str, str]] = {"audit_types": {}, "audit_errors": {}}
for section_name, ids in section_ids.items():
    for qid in ids:
        yaml_out[section_name][f"q{qid}"] = labels_by_query_id[qid]

OUTPUT_YAML_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_YAML_PATH, "w", encoding="utf-8") as f:
    yaml.dump(yaml_out, f, default_flow_style=False, sort_keys=False, allow_unicode=False)

print(f"Wrote: {OUTPUT_YAML_PATH}")
