#!/usr/bin/env python3
"""Create the fixed transcript sample for the original-score repetition experiment.

The experiment samples transcripts from five-point original-score bins below 75.
Only transcripts with exactly one existing production query are eligible, ensuring
that ten new responses will produce exactly eleven total trials.
"""

#%%
import argparse
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import config
from modules.utils import extract_score_from_unstructured_response


#%%
PROMPT_NAME = "SimpleCapacityV8.1.1"
MODEL_NAME = "gpt-4o-mini"
BIN_WIDTH = 5
MIN_SCORE = 0
MAX_SCORE_EXCLUSIVE = 75
DEFAULT_SAMPLE_SIZE = 500
DEFAULT_SEED = 42
DEFAULT_OUTPUT_PATH = os.path.join(
    config.DATA_DIR,
    "intermediaries",
    "score_bin_repeat_sample.csv",
)


#%%
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sample transcripts for ten additional LLM runs by original-score bin."
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of transcripts per five-point bin (default: {DEFAULT_SAMPLE_SIZE}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed used for sampling (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help="Output CSV path.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing sample manifest.",
    )
    return parser.parse_args()


#%%
def load_query_counts():
    """Load existing query counts for the production prompt and model."""
    print(f"Reading query counts from: {config.DATABASE_PATH}")
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        query_counts = pd.read_sql_query(
            """
            SELECT transcriptid, COUNT(*) AS existing_query_count
            FROM queries
            WHERE prompt_name = ? AND model_name = ?
            GROUP BY transcriptid
            """,
            conn,
            params=(PROMPT_NAME, MODEL_NAME),
        )

    query_counts["transcriptid"] = query_counts["transcriptid"].astype("int64")
    query_counts["existing_query_count"] = query_counts[
        "existing_query_count"
    ].astype("int64")
    print(f"Found query counts for {len(query_counts):,} transcripts")
    return query_counts


#%%
def validate_original_responses(sample):
    """Confirm sampled original scores can be recovered from their first responses."""
    transcript_ids = sample["transcriptid"].astype(int).tolist()
    placeholders = ",".join("?" for _ in transcript_ids)

    print("Validating sampled scores against the earliest database responses...")
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        responses = pd.read_sql_query(
            f"""
            SELECT q.transcriptid, q.response
            FROM queries q
            JOIN (
                SELECT transcriptid, MIN(query_id) AS first_query_id
                FROM queries
                WHERE prompt_name = ? AND model_name = ?
                GROUP BY transcriptid
            ) first_queries ON q.query_id = first_queries.first_query_id
            WHERE q.transcriptid IN ({placeholders})
            """,
            conn,
            params=[PROMPT_NAME, MODEL_NAME, *transcript_ids],
        )

    responses["parsed_original_score"] = responses["response"].apply(
        extract_score_from_unstructured_response
    )
    validation = sample[["transcriptid", "original_score"]].merge(
        responses[["transcriptid", "parsed_original_score"]],
        on="transcriptid",
        how="left",
        validate="one_to_one",
    )

    missing_responses = int(validation["parsed_original_score"].isna().sum())
    if missing_responses:
        raise ValueError(
            f"Could not recover a valid original score for {missing_responses:,} "
            "sampled transcripts"
        )

    score_mismatches = ~np.isclose(
        validation["original_score"],
        validation["parsed_original_score"],
    )
    if score_mismatches.any():
        raise ValueError(
            f"Found {int(score_mismatches.sum()):,} sampled transcripts whose "
            "saved original score differs from the earliest database response"
        )

    print(f"Validated all {len(validation):,} sampled original responses")


#%%
def create_sample(sample_size, seed):
    """Construct and validate the score-bin sample."""
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")

    original_scores_path = os.path.join(
        config.DATA_DIR,
        "intermediaries",
        "original_score.csv",
    )
    print(f"Reading original scores from: {original_scores_path}")
    scores = pd.read_csv(original_scores_path)

    required_columns = {"transcriptid", "score"}
    missing_columns = required_columns - set(scores.columns)
    if missing_columns:
        raise ValueError(
            f"Original-score file is missing columns: {sorted(missing_columns)}"
        )

    scores = scores[["transcriptid", "score"]].copy()
    scores["transcriptid"] = pd.to_numeric(
        scores["transcriptid"], errors="raise"
    ).astype("int64")
    scores["score"] = pd.to_numeric(scores["score"], errors="coerce")

    if scores["transcriptid"].duplicated().any():
        duplicate_count = int(scores["transcriptid"].duplicated().sum())
        raise ValueError(
            f"Original-score file contains {duplicate_count:,} duplicate transcript IDs"
        )

    invalid_score_count = int(scores["score"].isna().sum())
    if invalid_score_count:
        print(f"Excluding {invalid_score_count:,} transcripts with missing scores")
        scores = scores[scores["score"].notna()].copy()

    out_of_range = ~scores["score"].between(0, 100, inclusive="both")
    if out_of_range.any():
        raise ValueError(
            f"Found {int(out_of_range.sum()):,} original scores outside [0, 100]"
        )

    query_counts = load_query_counts()
    scores = scores.merge(
        query_counts,
        on="transcriptid",
        how="left",
        validate="one_to_one",
    )

    missing_query_counts = int(scores["existing_query_count"].isna().sum())
    if missing_query_counts:
        raise ValueError(
            f"{missing_query_counts:,} scored transcripts have no matching "
            f"{PROMPT_NAME}/{MODEL_NAME} database query"
        )

    transcript_details = pd.read_feather(
        config.TRANSCRIPT_DETAIL_PATH,
        columns=["transcriptid"],
    )
    available_transcript_ids = set(
        transcript_details["transcriptid"].dropna().astype("int64")
    )
    scores["available_in_transcript_detail"] = scores["transcriptid"].isin(
        available_transcript_ids
    )

    experiment_scores = scores[
        scores["score"].ge(MIN_SCORE)
        & scores["score"].lt(MAX_SCORE_EXCLUSIVE)
    ].copy()
    experiment_scores["score_bin_lower"] = (
        np.floor(experiment_scores["score"] / BIN_WIDTH) * BIN_WIDTH
    ).astype("int64")
    experiment_scores["score_bin_upper"] = (
        experiment_scores["score_bin_lower"] + BIN_WIDTH
    )

    repeated_count = int((experiment_scores["existing_query_count"] > 1).sum())
    unavailable_count = int(
        (~experiment_scores["available_in_transcript_detail"]).sum()
    )
    print(f"Excluding {repeated_count:,} transcripts that already have repetitions")
    print(
        f"Excluding {unavailable_count:,} transcripts absent from "
        "transcript_detail.feather"
    )

    eligible = experiment_scores[
        experiment_scores["existing_query_count"].eq(1)
        & experiment_scores["available_in_transcript_detail"]
    ].copy()

    expected_bins = list(range(MIN_SCORE, MAX_SCORE_EXCLUSIVE, BIN_WIDTH))
    eligible_counts = eligible.groupby("score_bin_lower").size()
    insufficient_bins = {
        bin_lower: int(eligible_counts.get(bin_lower, 0))
        for bin_lower in expected_bins
        if int(eligible_counts.get(bin_lower, 0)) < sample_size
    }
    if insufficient_bins:
        details = ", ".join(
            f"[{lower}, {lower + BIN_WIDTH}): {count}"
            for lower, count in insufficient_bins.items()
        )
        raise ValueError(
            f"Not enough eligible transcripts for sample size {sample_size}: {details}"
        )

    rng = np.random.default_rng(seed)
    sampled_groups = []

    print("\nEligible and sampled transcripts by bin:")
    for bin_lower in expected_bins:
        bin_upper = bin_lower + BIN_WIDTH
        bin_df = eligible[
            eligible["score_bin_lower"].eq(bin_lower)
        ].sort_values("transcriptid")
        selected_positions = rng.choice(
            len(bin_df),
            size=sample_size,
            replace=False,
        )
        sampled_bin = bin_df.iloc[selected_positions].copy()
        sampled_bin = sampled_bin.sort_values("transcriptid").reset_index(drop=True)
        sampled_bin["sample_rank"] = np.arange(1, sample_size + 1)
        sampled_groups.append(sampled_bin)
        print(
            f"  [{bin_lower:>2}, {bin_upper:>2}): "
            f"{len(bin_df):>7,} eligible; {len(sampled_bin):>3,} sampled"
        )

    sample = pd.concat(sampled_groups, ignore_index=True)
    sample["sample_seed"] = seed
    sample["prompt_name"] = PROMPT_NAME
    sample["model_name"] = MODEL_NAME

    output_columns = [
        "transcriptid",
        "original_score",
        "score_bin_lower",
        "score_bin_upper",
        "sample_rank",
        "existing_query_count",
        "sample_seed",
        "prompt_name",
        "model_name",
    ]
    sample = sample.rename(columns={"score": "original_score"})
    sample = sample[output_columns].sort_values(
        ["score_bin_lower", "sample_rank"]
    ).reset_index(drop=True)

    expected_rows = len(expected_bins) * sample_size
    if len(sample) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows:,} sampled rows but created {len(sample):,}"
        )
    if sample["transcriptid"].duplicated().any():
        raise RuntimeError("Sample contains duplicate transcript IDs")
    if not sample["existing_query_count"].eq(1).all():
        raise RuntimeError("Sample contains transcripts with prior repetitions")

    validate_original_responses(sample)
    return sample


#%%
def save_sample(sample, output_path, overwrite):
    """Save the sample manifest atomically."""
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(
            f"Output already exists: {output_path}. Use --overwrite to replace it."
        )

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    temporary_path = f"{output_path}.tmp.{os.getpid()}"
    sample.to_csv(temporary_path, index=False)
    os.replace(temporary_path, output_path)
    print(f"\nSaved {len(sample):,} sampled transcripts to: {output_path}")
    print(f"Planned additional queries: {len(sample) * 10:,}")


#%%
if __name__ == "__main__":
    args = parse_args()
    print("Creating original-score-bin repetition sample")
    print(f"Prompt: {PROMPT_NAME}")
    print(f"Model: {MODEL_NAME}")
    print(f"Sample size per bin: {args.sample_size:,}")
    print(f"Random seed: {args.seed}")

    sample_df = create_sample(args.sample_size, args.seed)
    save_sample(sample_df, args.output, args.overwrite)
