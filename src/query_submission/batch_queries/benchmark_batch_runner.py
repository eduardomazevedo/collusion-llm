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
import fcntl
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
LOCK_PATH = os.path.join(config.CACHE_DIR, "benchmark_batch_runner.lock")

# OpenAI batch statuses that imply the job is still running / holding queue capacity
LIVE_STATUSES = {"validating", "in_progress", "finalizing", "canceling"}

# Conservative token budget for queued batches (below published limits)
MAX_TOKENS_IN_QUEUE = 9_000_000
# Per-batch creation cap; keep below queue cap so a single batch can be submitted.
MAX_TOKENS_PER_BATCH_FILE = 8_000_000


def target_runs_series(df: pd.DataFrame) -> pd.Series:
    """Safe integer view of target_runs with NA -> -1 for filtering masks."""
    return pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int)


def is_saved(value) -> bool:
    """Robust boolean parser for saved_to_db values loaded from CSV."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    # Handles numpy bool scalars and any remaining truthy scalar types.
    return bool(value)


def load_benchmark_transcript_ids() -> List[int]:
    """Return transcript IDs with Joe score or ACL flag present."""
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    ids = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())]["transcriptid"]
    return ids.dropna().astype(int).unique().tolist()


def get_existing_counts(prompt_name: str, model_name: str) -> Dict[int, int]:
    """Get existing query counts by transcript for a prompt/model pair."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    rows = conn.execute(
        """
        SELECT transcriptid, COUNT(*) as n
        FROM queries
        WHERE prompt_name = ? AND model_name = ?
        GROUP BY transcriptid
        """,
        (prompt_name, model_name),
    ).fetchall()
    conn.close()
    return {int(r[0]): int(r[1]) for r in rows}


def get_transcript_deficits(
    prompt_name: str,
    benchmark_ids: List[int],
    model_name: str,
    target_runs: int,
) -> Dict[int, int]:
    """Return transcript->missing_runs deficits for a prompt/model/target_runs."""
    existing = get_existing_counts(prompt_name, model_name)
    deficits: Dict[int, int] = {}
    for tid in benchmark_ids:
        current = existing.get(tid, 0)
        missing = max(0, target_runs - current)
        if missing > 0:
            deficits[int(tid)] = int(missing)
    return deficits


def get_transcript_deficits_from_existing(
    existing_counts: Dict[int, int],
    benchmark_ids: List[int],
    target_runs: int,
) -> Dict[int, int]:
    """Return transcript->missing_runs deficits given precomputed existing counts."""
    deficits: Dict[int, int] = {}
    for tid in benchmark_ids:
        current = existing_counts.get(int(tid), 0)
        missing = max(0, int(target_runs) - int(current))
        if missing > 0:
            deficits[int(tid)] = int(missing)
    return deficits


def get_effective_target_for_phase(
    existing_counts: Dict[int, int],
    benchmark_ids: List[int],
    final_target_runs: int,
) -> Tuple[int, str]:
    """
    Phase logic:
    1) Ensure at least 1 run for all transcripts.
    2) Then increase the floor one level at a time (2, 3, ..., final_target_runs).
    """
    if len(benchmark_ids) == 0:
        return int(final_target_runs), "empty"

    min_count = min(existing_counts.get(int(tid), 0) for tid in benchmark_ids)
    if min_count < 1:
        return 1, "coverage"
    if min_count < int(final_target_runs):
        return min_count + 1, "repeats_step"
    return int(final_target_runs), "complete"


def ensure_tracker(
    prompts: Optional[List[str]] = None,
    model_name: Optional[str] = None,
    target_runs: Optional[int] = None,
) -> pd.DataFrame:
    """Load or initialize the tracker CSV. Seed missing prompt rows if provided."""
    cols = [
        "prompt",
        "model",
        "target_runs",
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

    # Seed rows for prompt/model/target combinations that don't yet exist in tracker
    if prompts and model_name and target_runs is not None:
        existing_keys = set(
            zip(
                df["prompt"].fillna(""),
                df["model"].fillna(""),
                target_runs_series(df),
            )
        )
        for prompt in prompts:
            key = (prompt, model_name, int(target_runs))
            if key not in existing_keys:
                df.loc[len(df)] = {
                    "prompt": prompt,
                    "model": model_name,
                    "target_runs": int(target_runs),
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


def sanitize_model_name(model_name: str) -> str:
    return model_name.replace("/", "_").replace(":", "_")


def create_batches(
    prompts: List[str],
    benchmark_ids: List[int],
    model_name: str,
    target_runs: int,
) -> pd.DataFrame:
    """Create batch input files for prompt/model deficits up to target_runs."""
    processor = BatchProcessor(model=model_name)
    df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
    os.makedirs(config.CACHE_DIR, exist_ok=True)

    for prompt in prompts:
        mask = (
            (df["prompt"] == prompt)
            & (df["model"] == model_name)
            & (target_runs_series(df) == int(target_runs))
        )
        existing_rows = df[mask]
        existing = existing_rows.iloc[0] if not existing_rows.empty else None
        existing_counts = get_existing_counts(prompt, model_name)
        effective_target, phase = get_effective_target_for_phase(
            existing_counts,
            benchmark_ids,
            target_runs,
        )
        deficits = get_transcript_deficits_from_existing(
            existing_counts,
            benchmark_ids,
            effective_target,
        )
        total_missing_requests = int(sum(deficits.values()))

        # Do not overwrite rows that are already in-flight or waiting to be processed.
        if existing is not None:
            existing_status = existing.get("status")
            existing_saved = is_saved(existing.get("saved_to_db"))
            if (
                existing_status in LIVE_STATUSES.union({"submitted", "completed"})
                and not existing_saved
            ):
                print(
                    f"[create] Prompt {prompt} ({model_name}, target={target_runs}): "
                    f"skipping create; current batch status={existing_status} "
                    "(waiting for completion/processing)."
                )
                continue

        if total_missing_requests == 0:
            print(
                f"[create] Prompt {prompt} ({model_name}, target={target_runs}): "
                "no deficits; skipping."
            )
            if existing_rows.empty:
                df.loc[len(df)] = {
                    "prompt": prompt,
                    "model": model_name,
                    "target_runs": int(target_runs),
                    "batch_file": pd.NA,
                    "batch_id": pd.NA,
                    "status": "no_missing",
                    "saved_to_db": True,
                    "submitted_at": pd.NA,
                    "completed_at": pd.NA,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_completed": pd.NA,
                    "total_failed": pd.NA,
                }
            else:
                df.loc[mask, ["status", "saved_to_db", "total_requests", "total_tokens"]] = [
                    "no_missing",
                    True,
                    0,
                    0,
                ]
            continue

        # Expand transcript IDs by deficit count (e.g., need 10 more runs -> id appears 10 times)
        expanded_transcript_ids: List[int] = []
        for tid in sorted(deficits):
            expanded_transcript_ids.extend([tid] * deficits[tid])

        model_safe = sanitize_model_name(model_name)
        output_path = os.path.join(
            config.CACHE_DIR,
            f"{prompt}_{model_safe}_target{target_runs}_benchmark.jsonl",
        )
        print(
            f"[create] Prompt {prompt} ({model_name}, target={target_runs}): "
            f"phase={phase}, effective_target={effective_target}, "
            f"writing {len(expanded_transcript_ids)} requests "
            f"across {len(deficits)} transcripts to {output_path}"
        )
        # Build a capped batch file so submission can proceed under queue limits.
        request_ids_for_batch = list(expanded_transcript_ids)
        total_tokens = 0
        while True:
            processor.create_batch_input_file(
                prompt_name=prompt,
                transcriptids=request_ids_for_batch,
                output_path=output_path,
            )
            total_tokens = estimate_batch_tokens(output_path)
            if total_tokens <= MAX_TOKENS_PER_BATCH_FILE or len(request_ids_for_batch) == 1:
                break

            ratio = MAX_TOKENS_PER_BATCH_FILE / max(total_tokens, 1)
            new_size = max(1, int(len(request_ids_for_batch) * ratio))
            if new_size >= len(request_ids_for_batch):
                new_size = len(request_ids_for_batch) - 1
            print(
                f"[create] Prompt {prompt}: capped batch size from "
                f"{len(request_ids_for_batch)} to {new_size} requests "
                f"({total_tokens:,} tokens > {MAX_TOKENS_PER_BATCH_FILE:,})"
            )
            request_ids_for_batch = request_ids_for_batch[:new_size]

        if len(request_ids_for_batch) < len(expanded_transcript_ids):
            print(
                f"[create] Prompt {prompt}: created chunk with "
                f"{len(request_ids_for_batch)} / {len(expanded_transcript_ids)} "
                f"requests ({total_tokens:,} tokens). Remaining deficits will be "
                "picked up in later loops."
            )

        if existing_rows.empty:
            df.loc[len(df)] = {
                "prompt": prompt,
                "model": model_name,
                "target_runs": int(target_runs),
                "batch_file": output_path,
                "batch_id": pd.NA,
                "status": "created",
                "saved_to_db": False,
                "submitted_at": pd.NA,
                "completed_at": pd.NA,
                "total_requests": len(request_ids_for_batch),
                "total_tokens": total_tokens,
                "total_completed": pd.NA,
                "total_failed": pd.NA,
            }
        else:
            df.loc[
                mask,
                ["batch_file", "batch_id", "status", "saved_to_db", "total_requests", "total_tokens", "total_completed", "total_failed"],
            ] = [
                output_path,
                pd.NA,
                "created",
                False,
                len(request_ids_for_batch),
                total_tokens,
                pd.NA,
                pd.NA,
            ]

    save_tracker(df)
    return df


def submit_next_batch(
    df: pd.DataFrame,
    model_name: str,
    target_runs: int,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Submit the next unsubmitted batch if no live batch is in progress.
    Returns updated tracker and batch_id (or None if nothing submitted).
    """
    # Choose the first batch in status created/failed with a batch_file present
    candidates = df[
        (df["model"] == model_name)
        & (target_runs_series(df) == int(target_runs))
        & (df["status"].isin(["created", "failed", "not_created", pd.NA]))
        & df["batch_file"].notna()
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

    processor = BatchProcessor(model=model_name)
    print(f"[submit] Submitting batch for prompt {prompt} from {batch_file}")
    batch_id = processor.submit_batch(batch_file)
    now = datetime.utcnow().isoformat()

    mask = (
        (df["prompt"] == prompt)
        & (df["model"] == model_name)
        & (target_runs_series(df) == int(target_runs))
    )
    df.loc[mask, ["batch_id", "status", "submitted_at"]] = [batch_id, "submitted", now]
    save_tracker(df)
    return df, batch_id


def refresh_status(df: pd.DataFrame, model_name: str, target_runs: int) -> pd.DataFrame:
    """Refresh status/counts for batches with a batch_id; keep rows for all prompts."""
    processor = BatchProcessor(model=model_name)
    for idx, row in df.iterrows():
        row_target_runs = pd.to_numeric(row.get("target_runs"), errors="coerce")
        if (
            row.get("model") != model_name
            or pd.isna(row_target_runs)
            or int(row_target_runs) != int(target_runs)
        ):
            continue
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
    return _process_completed_for_model(df, model_name=None, target_runs=None)


def _process_completed_for_model(
    df: pd.DataFrame,
    model_name: Optional[str],
    target_runs: Optional[int],
) -> pd.DataFrame:
    processor = BatchProcessor(model=model_name) if model_name else BatchProcessor()
    for idx, row in df.iterrows():
        if model_name is not None and row.get("model") != model_name:
            continue
        if target_runs is not None:
            row_target_runs = pd.to_numeric(row.get("target_runs"), errors="coerce")
            if pd.isna(row_target_runs) or int(row_target_runs) != int(target_runs):
                continue
        if row.get("status") != "completed":
            continue
        if is_saved(row.get("saved_to_db")):
            continue
        batch_id = row["batch_id"]
        prompt = row["prompt"]
        print(f"[process] Processing batch {batch_id} for prompt {prompt}")
        results = processor.process_batch_results(str(batch_id), prompt)
        print(f"[process] Saved {len(results)} responses for prompt {prompt}")
        df.loc[idx, "saved_to_db"] = True
    save_tracker(df)
    return df


def run_sequence(prompts: List[str], model_name: str, target_runs: int) -> None:
    """End-to-end: create missing batches, submit if idle, refresh, process completed."""
    benchmark_ids = load_benchmark_transcript_ids()
    print(
        f"[run] Benchmark transcripts: {len(benchmark_ids)} | "
        f"model={model_name} | target_runs={target_runs}"
    )

    df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
    df = create_batches(prompts, benchmark_ids, model_name=model_name, target_runs=target_runs)
    df, submitted = submit_next_batch(df, model_name=model_name, target_runs=target_runs)
    if submitted:
        print(f"[run] Submitted batch_id: {submitted}")
    df = refresh_status(df, model_name=model_name, target_runs=target_runs)
    df = _process_completed_for_model(df, model_name=model_name, target_runs=target_runs)
    print("[run] Tracker updated.")
    mask = (df["model"] == model_name) & (target_runs_series(df) == int(target_runs))
    print(df.loc[mask, ["prompt", "model", "target_runs", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])


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
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Model name to target (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--target-runs",
        type=int,
        default=1,
        help="Required minimum runs per transcript/prompt for the selected model (default: 1)",
    )
    return parser.parse_args()


def main():
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[lock] Another benchmark_batch_runner instance is active. Exiting.")
        lock_file.close()
        return

    args = parse_args()
    prompts = DEFAULT_PROMPTS if not args.prompts else [p.strip() for p in args.prompts.split(",")]
    model_name = args.model
    target_runs = int(args.target_runs)

    if args.operation == "create":
        benchmark_ids = load_benchmark_transcript_ids()
        create_batches(prompts, benchmark_ids, model_name=model_name, target_runs=target_runs)
        df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
        mask = (df["model"] == model_name) & (target_runs_series(df) == int(target_runs))
        print(df.loc[mask, ["prompt", "model", "target_runs", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        print("[create] Done.")
        return

    if args.operation == "submit":
        df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
        df, submitted = submit_next_batch(df, model_name=model_name, target_runs=target_runs)
        mask = (df["model"] == model_name) & (target_runs_series(df) == int(target_runs))
        print(df.loc[mask, ["prompt", "model", "target_runs", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        print(f"[submit] Submitted: {submitted}")
        return

    if args.operation == "status":
        df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
        refresh_status(df, model_name=model_name, target_runs=target_runs)
        mask = (df["model"] == model_name) & (target_runs_series(df) == int(target_runs))
        print(df.loc[mask, ["prompt", "model", "target_runs", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        return

    if args.operation == "process":
        df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
        refresh_status(df, model_name=model_name, target_runs=target_runs)
        _process_completed_for_model(df, model_name=model_name, target_runs=target_runs)
        df = ensure_tracker(prompts, model_name=model_name, target_runs=target_runs)
        mask = (df["model"] == model_name) & (target_runs_series(df) == int(target_runs))
        print(df.loc[mask, ["prompt", "model", "target_runs", "status", "batch_id", "total_requests", "total_completed", "total_failed", "saved_to_db"]])
        return

    if args.operation == "run":
        run_sequence(prompts, model_name=model_name, target_runs=target_runs)
        return


if __name__ == "__main__":
    main()
