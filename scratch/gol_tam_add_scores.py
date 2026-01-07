"""
Add first LLM score and validated score to the GOL/TAM flagged transcript file.

Reads:
- assets/gol_tam_flagged_transcript_v2.xlsx
- data/datasets/top_transcripts_data.csv
- queries table (first SimpleCapacityV8.1.1 response per transcript)

Writes:
- assets/gol_tam_flagged_transcript_v3.xlsx
"""

#%%
import sys
import os
import sqlite3
import pandas as pd

#%%
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import config
from modules.utils import extract_score_from_unstructured_response

input_path = os.path.join("assets", "gol_tam_flagged_transcript_v2.xlsx")
scores_path = os.path.join("data", "datasets", "top_transcripts_data.csv")
output_path = os.path.join("assets", "gol_tam_flagged_transcript_v3.xlsx")

print(f"Loading transcripts from {input_path}...")
transcripts_df = pd.read_excel(input_path)
print(f"Loaded {len(transcripts_df):,} rows.")

print(f"Loading LLM scores from {scores_path}...")
scores_df = pd.read_csv(scores_path)
print(f"Loaded {len(scores_df):,} transcript scores.")

#%%
if "transcript_id" not in transcripts_df.columns:
    raise ValueError("Expected 'transcript_id' column in the input file.")
if "transcriptid" not in scores_df.columns:
    raise ValueError("Expected 'transcriptid' column in the scores file.")

# Ensure consistent types for merge
transcripts_df["transcript_id"] = pd.to_numeric(transcripts_df["transcript_id"], errors="coerce").astype("Int64")
scores_df["transcriptid"] = pd.to_numeric(scores_df["transcriptid"], errors="coerce").astype("Int64")

scores_subset = scores_df[["transcriptid", "mean_score_ten_repeats"]].copy()
scores_subset = scores_subset.rename(columns={
    "transcriptid": "transcript_id",
    "mean_score_ten_repeats": "llm_validated_score"
})

#%%
def fetch_first_llm_scores(transcript_ids, batch_size=500):
    conn = sqlite3.connect(config.DATABASE_PATH)
    all_rows = []
    transcript_ids = [int(x) for x in transcript_ids if pd.notna(x)]
    print(f"Fetching first LLM scores for {len(transcript_ids):,} transcript IDs...")
    for i in range(0, len(transcript_ids), batch_size):
        batch = transcript_ids[i:i + batch_size]
        placeholders = ",".join(["?"] * len(batch))
        query = f"""
        SELECT q.transcriptid, q.response
        FROM queries q
        JOIN (
            SELECT transcriptid, MIN(query_id) AS min_query_id
            FROM queries
            WHERE prompt_name = 'SimpleCapacityV8.1.1'
              AND model_name = 'gpt-4o-mini'
              AND transcriptid IN ({placeholders})
            GROUP BY transcriptid
        ) m
        ON q.query_id = m.min_query_id
        """
        batch_df = pd.read_sql_query(query, conn, params=batch)
        all_rows.append(batch_df)
        print(f"  Loaded {len(batch_df):,} rows for batch {i // batch_size + 1}")
    conn.close()
    if not all_rows:
        return pd.DataFrame(columns=["transcript_id", "llm_first_score"])
    result = pd.concat(all_rows, ignore_index=True)
    result["llm_first_score"] = result["response"].apply(
        lambda x: extract_score_from_unstructured_response(x)
    )
    return result[["transcriptid", "llm_first_score"]].rename(columns={"transcriptid": "transcript_id"})

print("Merging scores into transcript data...")
first_scores_df = fetch_first_llm_scores(transcripts_df["transcript_id"].dropna().unique())
merged_df = transcripts_df.merge(first_scores_df, on="transcript_id", how="left")
merged_df = merged_df.merge(scores_subset, on="transcript_id", how="left")

#%%
if "headline" not in merged_df.columns or "sentences" not in merged_df.columns:
    raise ValueError("Expected 'headline' and 'sentences' columns to place new fields between them.")

columns = [c for c in merged_df.columns if c not in ["llm_first_score", "llm_validated_score"]]
headline_idx = columns.index("headline") + 1
final_columns = (
    columns[:headline_idx]
    + ["llm_first_score", "llm_validated_score"]
    + columns[headline_idx:]
)
merged_df = merged_df[final_columns]

#%%
missing_first = merged_df["llm_first_score"].isna().sum()
missing_validated = merged_df["llm_validated_score"].isna().sum()
unique_transcripts = merged_df["transcript_id"].nunique(dropna=True)

print(f"Unique transcript IDs: {unique_transcripts:,}")
print(f"Missing LLM first score rows: {missing_first:,}")
print(f"Missing LLM validated score rows: {missing_validated:,}")

print(f"Writing updated file to {output_path}...")
merged_df.to_excel(output_path, index=False)
print("Done.")
