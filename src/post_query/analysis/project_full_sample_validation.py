"""Project eleven-query LLM validation counts for the full transcript sample.

The script estimates, within five-point original-score buckets, the probability
that a transcript's mean score across eleven identical queries is at least 75.
It then applies those bucket-specific probabilities to the observed original-
score distribution in the full transcript sample.

Outputs:
- data/outputs/tables/projected_full_sample_llm_validation.csv
- data/outputs/tables/projected_full_sample_llm_validation.tex
- data/outputs/tables/projected_full_sample_llm_validation.txt
"""

#%%
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

import config
from modules.utils import extract_score_from_unstructured_response

#%%
PROMPT_NAME = "SimpleCapacityV8.1.1"
MODEL_NAME = "gpt-4o-mini"
VALIDATION_THRESHOLD = 75
BIN_WIDTH = 5

OUTPUT_DIR = Path("data/outputs/tables")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = OUTPUT_DIR / "projected_full_sample_llm_validation.csv"
TEX_PATH = OUTPUT_DIR / "projected_full_sample_llm_validation.tex"
TXT_PATH = OUTPUT_DIR / "projected_full_sample_llm_validation.txt"

#%%
print("Loading below-threshold repetition sample...")
sample_path = os.path.join(
    config.DATA_DIR,
    "intermediaries",
    "score_bin_repeat_sample.csv",
)
below_threshold_sample = pd.read_csv(
    sample_path,
    usecols=["transcriptid", "original_score"],
)
transcript_ids = below_threshold_sample["transcriptid"].astype(int).tolist()

query_frames = []
with sqlite3.connect(config.DATABASE_PATH) as conn:
    for start in range(0, len(transcript_ids), 900):
        batch_ids = transcript_ids[start:start + 900]
        placeholders = ",".join("?" for _ in batch_ids)
        query_frames.append(
            pd.read_sql_query(
                f"""
                SELECT query_id, transcriptid, response
                FROM queries
                WHERE prompt_name = ?
                  AND model_name = ?
                  AND transcriptid IN ({placeholders})
                ORDER BY query_id
                """,
                conn,
                params=[PROMPT_NAME, MODEL_NAME, *batch_ids],
            )
        )

below_threshold_queries = pd.concat(query_frames, ignore_index=True)
below_threshold_queries["score"] = below_threshold_queries["response"].apply(
    extract_score_from_unstructured_response
)
if below_threshold_queries["score"].isna().any():
    missing_count = int(below_threshold_queries["score"].isna().sum())
    raise ValueError(f"Could not parse {missing_count:,} repetition-query scores")

below_threshold_summary = (
    below_threshold_queries.sort_values("query_id")
    .groupby("transcriptid")
    .agg(
        query_count=("score", "size"),
        database_original_score=("score", "first"),
        mean_score=("score", "mean"),
    )
    .reset_index()
)
if not below_threshold_summary["query_count"].eq(11).all():
    incomplete_count = int((below_threshold_summary["query_count"] != 11).sum())
    raise ValueError(
        f"Expected eleven queries per below-threshold transcript; "
        f"found {incomplete_count:,} incomplete transcripts"
    )

below_threshold = below_threshold_sample.merge(
    below_threshold_summary,
    on="transcriptid",
    validate="one_to_one",
)
if not np.allclose(
    below_threshold["original_score"],
    below_threshold["database_original_score"],
):
    raise ValueError("Saved original scores do not match first database-query scores")

#%%
print("Loading original flagged-sample repetitions...")
flagged = pd.read_csv(
    os.path.join(config.DATA_DIR, "datasets", "top_transcripts_data.csv"),
    usecols=["transcriptid", "original_score", "mean_score_ten_repeats"],
).rename(columns={"mean_score_ten_repeats": "mean_score"})
flagged = flagged.dropna(subset=["original_score", "mean_score"]).copy()

repetition_results = pd.concat(
    [
        below_threshold[["transcriptid", "original_score", "mean_score"]],
        flagged[["transcriptid", "original_score", "mean_score"]],
    ],
    ignore_index=True,
)
if repetition_results["transcriptid"].duplicated().any():
    duplicate_count = int(repetition_results["transcriptid"].duplicated().sum())
    raise ValueError(f"Repetition results contain {duplicate_count:,} duplicate IDs")

repetition_results["score_bucket"] = (
    np.floor(repetition_results["original_score"] / BIN_WIDTH) * BIN_WIDTH
).astype(int)
repetition_results["llm_validated"] = (
    repetition_results["mean_score"] >= VALIDATION_THRESHOLD
)

validation_rates = (
    repetition_results.groupby("score_bucket")
    .agg(
        repetition_sample_n=("transcriptid", "size"),
        llm_validated_n=("llm_validated", "sum"),
    )
    .reset_index()
)
validation_rates["validation_probability"] = (
    validation_rates["llm_validated_n"]
    / validation_rates["repetition_sample_n"]
)

#%%
print("Loading full-sample original-score distribution...")
full_sample = pd.read_csv(
    os.path.join(config.DATA_DIR, "intermediaries", "original_score.csv"),
    usecols=["transcriptid", "score"],
)
if full_sample["score"].isna().any():
    raise ValueError("Full-sample original-score file contains missing scores")
full_sample["score_bucket"] = (
    np.floor(full_sample["score"] / BIN_WIDTH) * BIN_WIDTH
).astype(int)
full_sample_counts = (
    full_sample.groupby("score_bucket")
    .size()
    .rename("full_sample_n")
    .reset_index()
)

expected_buckets = pd.DataFrame(
    {"score_bucket": np.arange(0, 100, BIN_WIDTH, dtype=int)}
)
table = (
    expected_buckets.merge(validation_rates, on="score_bucket", how="left")
    .merge(full_sample_counts, on="score_bucket", how="left")
)
if table[["repetition_sample_n", "validation_probability"]].isna().any().any():
    missing_buckets = table.loc[
        table["validation_probability"].isna(), "score_bucket"
    ].tolist()
    raise ValueError(f"Missing repetition estimates for buckets: {missing_buckets}")

table["full_sample_n"] = table["full_sample_n"].fillna(0).astype(int)
table["projected_llm_validated"] = (
    table["full_sample_n"] * table["validation_probability"]
)
table["projected_llm_validated_n"] = np.rint(
    table["projected_llm_validated"]
).astype(int)

projected_total = float(table["projected_llm_validated"].sum())
projected_total_rounded = int(np.rint(projected_total))
full_sample_total = int(table["full_sample_n"].sum())

print("\nBucket-specific projection:")
print(
    table[
        [
            "score_bucket",
            "repetition_sample_n",
            "llm_validated_n",
            "validation_probability",
            "full_sample_n",
            "projected_llm_validated_n",
        ]
    ].to_string(
        index=False,
        formatters={
            "validation_probability": lambda value: f"{100 * value:.2f}%",
        },
    )
)
print(
    f"\nProjected full-sample LLM validations: "
    f"{projected_total_rounded:,} of {full_sample_total:,} transcripts "
    f"({100 * projected_total / full_sample_total:.3f}%)"
)

#%%
csv_table = table[
    [
        "score_bucket",
        "repetition_sample_n",
        "llm_validated_n",
        "validation_probability",
        "full_sample_n",
        "projected_llm_validated_n",
    ]
].copy()
csv_total = pd.DataFrame(
    [
        {
            "score_bucket": "Total",
            "repetition_sample_n": int(table["repetition_sample_n"].sum()),
            "llm_validated_n": int(table["llm_validated_n"].sum()),
            "validation_probability": "",
            "full_sample_n": full_sample_total,
            "projected_llm_validated_n": projected_total_rounded,
        }
    ]
)
csv_table = pd.concat([csv_table, csv_total], ignore_index=True)
csv_table.to_csv(CSV_PATH, index=False)

latex_rows = []
for row in table.itertuples(index=False):
    latex_rows.append(
        f"{row.score_bucket} & "
        f"{row.repetition_sample_n:,} & "
        f"{row.llm_validated_n:,} & "
        f"{100 * row.validation_probability:.2f}\\% & "
        f"{row.full_sample_n:,} & "
        f"{row.projected_llm_validated_n:,} \\\\"
    )
latex_rows.append(
    f"\\textbf{{Total}} & -- & -- & -- & "
    f"\\textbf{{{full_sample_total:,}}} & "
    f"\\textbf{{{projected_total_rounded:,}}} \\\\"
)

latex = r"""\begin{table}[ht]
\centering
\caption{Projected LLM Validation Counts for the Full Transcript Sample}
\label{tab:projected_full_sample_llm_validation}
\begin{tabular}{rrrrrr}
\toprule
Score & Repetition & Validated & Validation & Full-sample & Projected \\
Bucket & Sample $N$ & $N$ & Probability & $N$ & Validated $N$ \\
\midrule
""" + "\n".join(latex_rows) + r"""
\bottomrule
\end{tabular}
\begin{minipage}{\textwidth}
\vspace{1em}
\footnotesize
\textit{Notes:} Score buckets are five-point intervals beginning at the value shown. Validation probability is the share of transcripts in the repetition sample whose mean score across eleven identical queries (the original query plus ten repetitions) is at least 75. Full-sample $N$ reports the number of transcripts in each original-score bucket. Projected Validated $N$ applies the bucket-specific validation probability to the corresponding full-sample count and rounds to the nearest transcript. The total is calculated from unrounded bucket-level projections. Estimates for the 90 and 95 buckets are based on only 17 and 2 repeated transcripts, respectively, and should therefore be interpreted cautiously.
\end{minipage}
\end{table}
"""
TEX_PATH.write_text(latex)

TXT_PATH.write_text(
    "Estimated probability of LLM validation after eleven identical queries by "
    "five-point original-score bucket, together with the observed number of "
    "full-sample transcripts in each bucket and the projected number that would "
    "validate. Produced by "
    "src/post_query/analysis/project_full_sample_validation.py. The projection "
    f"implies approximately {projected_total_rounded:,} validated transcripts "
    f"among {full_sample_total:,} total transcripts.\n"
)

print(f"Saved: {CSV_PATH}")
print(f"Saved: {TEX_PATH}")
print(f"Saved: {TXT_PATH}")
