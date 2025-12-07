#!/usr/bin/env python3
"""
Batch runner for benchmarking prompts on the human-labeled transcript sample.

Workflow:
1) Identify benchmarking transcripts (those with Joe or ACL labels).
2) For each target prompt, find transcripts missing in the queries table.
3) Create a batch JSONL (one per prompt) with only the missing transcripts.
4) Submit batches while respecting a conservative token queue budget.
5) Refresh status and, when completed, process results into the queries DB
   (including malformed responses, which are still inserted by BatchProcessor).
6) Track everything in a CSV for resumability.

Usage (examples):
  python benchmark_batch_runner.py --operation create
  python benchmark_batch_runner.py --operation submit
  python benchmark_batch_runner.py --operation status
  python benchmark_batch_runner.py --operation process
  python benchmark_batch_runner.py --operation run  # create+submit/process sequentially

The tracker CSV lives at data/cache/benchmark_batch_tracker.csv.
"""

import argparse
import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

import config
from modules.batch_processor import BatchProcessor
from modules.utils import token_size


# Default prompt set to run on the benchmarking sample
DEFAULT_PROMPTS = [
    "SimpleScoreV1",
    "SimpleFlagV1",
    "SimpleFlagScoreV1",
    "PriceCapacityV1",
    "PriceCapacityV2",
    "PriceCapacityV3",
    "PriceCapacityV4",
    "PriceCapacityV5",
    "PriceCapacityV6",
    "SimpleCapacityV8",
    "SimpleCapacityV8.1",
    "SimpleCapacityV8.1.1",
    "SimpleCapacityV8.2",
    "SimpleCapacityV8.3",
    "SimpleCapacityV8.4",
]

TRACKER_PATH = os.path.join(config.CACHE_DIR, "benchmark_batch_tracker.csv")

# OpenAI batch statuses that imply the job is still running / holding queue capacity
LIVE_STATUSES = {"validating", "in_progress", "finalizing", "canceling"}

# Conservative token budget for queued batches (below published limits)
MAX_TOKENS_IN_QUEUE = 9_000_000


def load_benchmark_transcript_ids() -> List[int]:
    """Return transcript IDs with Joe score or ACL flag present."""
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    ids = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())]["transcriptid"]
    return ids.dropna().astype(int).unique().tolist()


def transcripts_already_processed(prompt_name: str) -> set:
    """Get transcript IDs already present in queries for a prompt."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    rows = conn.execute(
        "SELECT DISTINCT transcriptid FROM queries WHERE prompt_name = ?",
        (prompt_name,),
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def get_missing_transcripts(prompt_name: str, benchmark_ids: List[int]) -> List[int]:
    """Return benchmark transcripts missing for the given prompt."""
    existing = transcripts_already_processed(prompt_name)
    return [tid for tid in benchmark_ids if tid not in existing]


def ensure_tracker(prompts: Optional[List[str]] = None) -> pd.DataFrame:
    """Load or initialize the tracker CSV. Seed missing prompt rows if provided."""
    cols = [
        "prompt",
        "batch_file",
        "batch_id",
        "status",
        "saved_to_db",
        "submitted_at",
        "completed_at",
        "total_requests",
        "total_tokens",
        "total_completed",
        "total_failed",
    ]
    if os.path.exists(TRACKER_PATH):
        df = pd.read_csv(TRACKER_PATH)
        # Add any missing columns for forward compatibility
        for col in cols:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[cols]
    else:
        df = pd.DataFrame(columns=cols)

    # Seed rows for prompts that don't yet exist in tracker
    if prompts:
        existing_prompts = set(df["prompt"].dropna())
        for prompt in prompts:
            if prompt not in existing_prompts:
                df.loc[len(df)] = {
                    "prompt": prompt,
                    "batch_file": pd.NA,
                    "batch_id": pd.NA,
                    "status": "not_created",
                    "saved_to_db": False,
                    "submitted_at": pd.NA,
                    "completed_at": pd.NA,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_completed": pd.NA,
                    "total_failed": pd.NA,
                }

    return df


def estimate_batch_tokens(batch_file: str) -> int:
    """
    Estimate total tokens in a batch file by summing prompt+user message tokens per line.
    """
    total_tokens = 0
    with open(batch_file, "r") as f:
        for line in f:
            req = json.loads(line)
            messages = req.get("body", {}).get("messages", [])
            if len(messages) >= 2:
                sys_msg = messages[0].get("content", "")
                user_msg = messages[1].get("content", "")
                total_tokens += token_size(sys_msg) + token_size(user_msg)
    return total_tokens


def save_tracker(df: pd.DataFrame) -> None:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    df.to_csv(TRACKER_PATH, index=False)


def queued_tokens(df: pd.DataFrame) -> int:
    """Sum total_tokens for batches that are live/submitted."""
    mask = df["status"].isin(LIVE_STATUSES.union({"submitted"}))
    return int(df.loc[mask, "total_tokens"].fillna(0).sum())


def create_batches(prompts: List[str], benchmark_ids: List[int]) -> pd.DataFrame:
    """Create batch input files for prompts; append tracker entries for missing IDs."""
    processor = BatchProcessor()
    df = ensure_tracker(prompts)
    os.makedirs(config.CACHE_DIR, exist_ok=True)

    for prompt in prompts:
        existing_rows = df[df["prompt"] == prompt]
        existing = existing_rows.iloc[0] if not existing_rows.empty else None
        missing_ids = get_missing_transcripts(prompt, benchmark_ids)

        # If a batch file already exists for this prompt, don't recreate it
        if existing is not None:
            batch_file = existing.get("batch_file")
            if isinstance(batch_file, str) and os.path.exists(batch_file):
                print(f"[create] Prompt {prompt}: batch file already exists at {batch_file}; skipping recreate.")
                continue

        if not missing_ids:
            print(f"[create] Prompt {prompt}: no missing transcripts; skipping.")
            if existing is None or pd.isna(existing.get("batch_id")):
                df.loc[df["prompt"] == prompt, ["status", "saved_to_db", "total_requests", "total_tokens"]] = [
                    "no_missing",
                    True,
                    0,
                    0,
                ]
            continue

        output_path = os.path.join(config.CACHE_DIR, f"{prompt}_benchmark.jsonl")
        print(f"[create] Prompt {prompt}: writing {len(missing_ids)} requests to {output_path}")
        processor.create_batch_input_file(prompt_name=prompt, transcriptids=missing_ids, output_path=output_path)

        total_tokens = estimate_batch_tokens(output_path)
        # Remove any prior tracker row for this prompt (keep latest batch file)
        if existing_rows.empty:
            df.loc[len(df)] = {
                "prompt": prompt,
                "batch_file": output_path,
                "batch_id": pd.NA,
                "status": "created",
                "saved_to_db": False,
                "submitted_at": pd.NA,
                "completed_at": pd.NA,
                "total_requests": len(missing_ids),
                "total_tokens": total_tokens,
                "total_completed": pd.NA,
                "total_failed": pd.NA,
            }
        else:
            df.loc[df["prompt"] == prompt, ["batch_file", "status", "saved_to_db", "total_requests", "total_tokens"]] = [
                output_path,
                "created",
                False,
                len(missing_ids),
                total_tokens,
            ]

    save_tracker(df)
    return df


def submit_next_batch(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Submit the next unsubmitted batch if no live batch is in progress.
    Returns updated tracker and batch_id (or None if nothing submitted).
    """
    # Choose the first batch in status created/failed with a batch_file present
    candidates = df[
        (df["status"].isin(["created", "failed", "not_created", pd.NA])) &
        df["batch_file"].notna()
    ]
    if candidates.empty:
        print("[submit] No pending batches to submit.")
        return df, None

    row = candidates.iloc[0]
    prompt = row["prompt"]
    batch_file = row["batch_file"]
    batch_tokens = row.get("total_tokens", 0)

    if not os.path.exists(batch_file):
        print(f"[submit] Batch file missing: {batch_file}")
        return df, None

    live_tokens = queued_tokens(df)
    if live_tokens + batch_tokens > MAX_TOKENS_IN_QUEUE:
        print(
            f"[submit] Skipping submission; queue would exceed token budget "
            f"({live_tokens + batch_tokens:,} > {MAX_TOKENS_IN_QUEUE:,})."
        )
        return df, None

    processor = BatchProcessor()
    print(f"[submit] Submitting batch for prompt {prompt} from {batch_file}")
    batch_id = processor.submit_batch(batch_file)
    now = datetime.utcnow().isoformat()

    df.loc[df["prompt"] == prompt, ["batch_id", "status", "submitted_at"]] = [batch_id, "submitted", now]
    save_tracker(df)
    return df, batch_id


def refresh_status(df: pd.DataFrame) -> pd.DataFrame:
    """Refresh status/counts for batches with a batch_id; keep rows for all prompts."""
    processor = BatchProcessor()
    for idx, row in df.iterrows():
        batch_id = row["batch_id"]
        if pd.isna(batch_id):
            # Leave created/unsubmitted rows untouched
            continue
        status_info = processor.check_batch_status(str(batch_id))
        status = status_info.get("status")
        completed = status_info.get("completed", pd.NA)
        failed = status_info.get("failed", pd.NA)
        total = status_info.get("total", row.get("total_requests"))

        df.loc[idx, "status"] = status
        df.loc[idx, "total_completed"] = completed
        df.loc[idx, "total_failed"] = failed
        if pd.notna(total):
            df.loc[idx, "total_requests"] = total
        if status == "completed":
            df.loc[idx, "completed_at"] = datetime.now(timezone.utc).isoformat()
    save_tracker(df)
    return df


def process_completed(df: pd.DataFrame) -> pd.DataFrame:
    """Process completed batches that are not yet saved to DB."""
    processor = BatchProcessor()
    for idx, row in df.iterrows():
        if row.get("status") != "completed":
            continue
        if row.get("saved_to_db") is True:
            continue
        batch_id = row["batch_id"]
        prompt = row["prompt"]
        print(f"[process] Processing batch {batch_id} for prompt {prompt}")
        results = processor.process_batch_results(str(batch_id), prompt)
        print(f"[process] Saved {len(results)} responses for prompt {prompt}")
        df.loc[idx, "saved_to_db"] = True
    save_tracker(df)
    return df


def run_sequence(prompts: List[str]) -> None:
    """End-to-end: create missing batches, submit if idle, refresh, process completed."""
    benchmark_ids = load_benchmark_transcript_ids()
    print(f"[run] Benchmark transcripts: {len(benchmark_ids)}")

    df = ensure_tracker()
    df = create_batches(prompts, benchmark_ids)
    df, submitted = submit_next_batch(df)
    if submitted:
        print(f"[run] Submitted batch_id: {submitted}")
    df = refresh_status(df)
    df = process_completed(df)
    print("[run] Tracker updated.")
    print(df[["prompt", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark batch runner for selected prompts.")
    parser.add_argument(
        "--prompts",
        type=str,
        help="Comma-separated prompt names (defaults to predefined list)",
    )
    parser.add_argument(
        "--operation",
        choices=["create", "submit", "status", "process", "run"],
        default="run",
        help="Action to perform",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    prompts = DEFAULT_PROMPTS if not args.prompts else [p.strip() for p in args.prompts.split(",")]

    if args.operation == "create":
        benchmark_ids = load_benchmark_transcript_ids()
        create_batches(prompts, benchmark_ids)
        df = ensure_tracker(prompts)
        print(df[["prompt", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        print("[create] Done.")
        return

    if args.operation == "submit":
        df = ensure_tracker(prompts)
        df, submitted = submit_next_batch(df)
        print(df[["prompt", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        print(f"[submit] Submitted: {submitted}")
        return

    if args.operation == "status":
        df = ensure_tracker(prompts)
        refresh_status(df)
        print(df[["prompt", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        return

    if args.operation == "process":
        df = ensure_tracker(prompts)
        refresh_status(df)
        process_completed(df)
        df = ensure_tracker(prompts)
        print(df[["prompt", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        return

    if args.operation == "run":
        run_sequence(prompts)
        return


if __name__ == "__main__":
    main()
