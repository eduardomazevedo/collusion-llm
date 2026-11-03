#!/usr/bin/env python3
"""Manage resumable OpenAI batches for the score-bin repetition experiment.

The runner targets eleven total `SimpleCapacityV8.1.1` / `gpt-4o-mini`
queries for every transcript in the fixed score-bin sample. It creates one
request per transcript per phase, which raises the minimum query count from 1
to 2, then 2 to 3, and so on until all transcripts have 11 queries.

No operation submits paid queries unless the explicit `submit` command is used
with `--confirm-submit`.

Examples:
    python score_bin_repeat_runner.py plan
    python score_bin_repeat_runner.py create
    python score_bin_repeat_runner.py submit --confirm-submit
    python score_bin_repeat_runner.py status
    python score_bin_repeat_runner.py process
    python score_bin_repeat_runner.py advance --max-batches 5 --confirm-submit
"""

#%%
import argparse
import fcntl
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import config
from modules.batch_processor import BatchProcessor
from modules.queries_db import insert_query_result
from modules.utils import extract_score_from_unstructured_response, token_size


#%%
PROMPT_NAME = "SimpleCapacityV8.1.1"
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 1.0
MAX_RESPONSE_TOKENS = 500
TARGET_RUNS = 11
MAX_REQUESTS_PER_BATCH = 500
MAX_TOKENS_PER_BATCH_FILE = 8_000_000

SAMPLE_PATH = os.path.join(
    config.DATA_DIR,
    "intermediaries",
    "score_bin_repeat_sample.csv",
)
CACHE_DIR = os.path.join(config.CACHE_DIR, "score_bin_repeat_batches")
TRACKER_PATH = os.path.join(CACHE_DIR, "tracker.csv")
LOCK_PATH = os.path.join(CACHE_DIR, "runner.lock")

LIVE_STATUSES = {
    "validating",
    "in_progress",
    "finalizing",
    "canceling",
    "submitted",
}
TRACKER_COLUMNS = [
    "batch_number",
    "phase_target",
    "sample_sha256",
    "batch_file",
    "batch_id",
    "status",
    "saved_to_db",
    "created_at",
    "submitted_at",
    "completed_at",
    "processed_at",
    "total_requests",
    "total_tokens",
    "total_completed",
    "total_failed",
    "inserted_rows",
    "skipped_existing_rows",
    "invalid_response_rows",
    "missing_output_ids",
]
TRACKER_TEXT_COLUMNS = [
    "sample_sha256",
    "batch_file",
    "batch_id",
    "status",
    "created_at",
    "submitted_at",
    "completed_at",
    "processed_at",
]


#%%
def utc_now():
    """Return the current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def is_true(value):
    """Interpret tracker values robustly after CSV serialization."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def sample_sha256():
    """Return a stable checksum for the fixed sample manifest."""
    digest = hashlib.sha256()
    with open(SAMPLE_PATH, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sample():
    """Load and validate the fixed experiment sample."""
    if not os.path.exists(SAMPLE_PATH):
        raise FileNotFoundError(
            f"Sample manifest not found: {SAMPLE_PATH}. Run "
            "create_score_bin_repeat_sample.py first."
        )

    sample = pd.read_csv(SAMPLE_PATH)
    required_columns = {
        "transcriptid",
        "original_score",
        "score_bin_lower",
        "score_bin_upper",
        "existing_query_count",
        "prompt_name",
        "model_name",
    }
    missing_columns = required_columns - set(sample.columns)
    if missing_columns:
        raise ValueError(
            f"Sample manifest is missing columns: {sorted(missing_columns)}"
        )

    sample["transcriptid"] = pd.to_numeric(
        sample["transcriptid"], errors="raise"
    ).astype("int64")
    if sample["transcriptid"].duplicated().any():
        raise ValueError("Sample manifest contains duplicate transcript IDs")
    if not sample["prompt_name"].eq(PROMPT_NAME).all():
        raise ValueError(f"Every sample row must use prompt {PROMPT_NAME}")
    if not sample["model_name"].eq(MODEL_NAME).all():
        raise ValueError(f"Every sample row must use model {MODEL_NAME}")

    bin_counts = sample.groupby(["score_bin_lower", "score_bin_upper"]).size()
    if len(bin_counts) != 15 or not bin_counts.eq(500).all():
        raise ValueError(
            "Expected exactly 500 transcripts in each of 15 score bins below 75"
        )

    sort_columns = [
        column
        for column in ["sample_rank", "score_bin_lower", "transcriptid"]
        if column in sample.columns
    ]
    return sample.sort_values(sort_columns).reset_index(drop=True)


def get_query_counts(transcript_ids):
    """Return matching query counts for the requested transcript IDs."""
    counts = {int(transcriptid): 0 for transcriptid in transcript_ids}
    batch_size = 900

    with sqlite3.connect(config.DATABASE_PATH) as conn:
        for start in range(0, len(transcript_ids), batch_size):
            batch_ids = [int(value) for value in transcript_ids[start:start + batch_size]]
            placeholders = ",".join("?" for _ in batch_ids)
            rows = conn.execute(
                f"""
                SELECT transcriptid, COUNT(*)
                FROM queries
                WHERE prompt_name = ?
                  AND model_name = ?
                  AND transcriptid IN ({placeholders})
                GROUP BY transcriptid
                """,
                [PROMPT_NAME, MODEL_NAME, *batch_ids],
            ).fetchall()
            for transcriptid, count in rows:
                counts[int(transcriptid)] = int(count)

    return counts


#%%
def empty_tracker():
    """Return an empty tracker with the expected schema."""
    return pd.DataFrame(columns=TRACKER_COLUMNS)


def load_tracker():
    """Load the batch history tracker."""
    if not os.path.exists(TRACKER_PATH):
        return empty_tracker()

    tracker = pd.read_csv(TRACKER_PATH)
    for column in TRACKER_COLUMNS:
        if column not in tracker.columns:
            tracker[column] = pd.NA
    tracker = tracker[TRACKER_COLUMNS]
    for column in TRACKER_TEXT_COLUMNS:
        tracker[column] = tracker[column].astype("object")
    return tracker


def save_tracker(tracker):
    """Save the tracker atomically."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    temporary_path = f"{TRACKER_PATH}.tmp.{os.getpid()}"
    tracker.to_csv(temporary_path, index=False)
    os.replace(temporary_path, TRACKER_PATH)


def validate_tracker_sample(tracker, checksum):
    """Prevent using a tracker created for a different sample manifest."""
    if tracker.empty:
        return
    known_checksums = set(tracker["sample_sha256"].dropna().astype(str))
    if known_checksums and known_checksums != {checksum}:
        raise ValueError(
            "The sample manifest checksum differs from the existing tracker. "
            "Do not change the sample after batch creation begins."
        )


def print_tracker(tracker):
    """Print a concise tracker summary."""
    if tracker.empty:
        print("No batches have been created.")
        return

    columns = [
        "batch_number",
        "phase_target",
        "status",
        "batch_id",
        "total_requests",
        "total_completed",
        "total_failed",
        "saved_to_db",
    ]
    print(tracker[columns].tail(20).to_string(index=False))


#%%
def calculate_plan(sample):
    """Calculate current progress and remaining query deficits."""
    transcript_ids = sample["transcriptid"].astype(int).tolist()
    counts = get_query_counts(transcript_ids)
    progress = sample[[
        "transcriptid",
        "score_bin_lower",
        "score_bin_upper",
    ]].copy()
    progress["current_queries"] = progress["transcriptid"].map(counts).astype(int)
    progress["remaining_queries"] = (
        TARGET_RUNS - progress["current_queries"]
    ).clip(lower=0)
    return progress


def print_plan(progress):
    """Print experiment progress overall and by original-score bin."""
    total_current = int(progress["current_queries"].sum())
    total_remaining = int(progress["remaining_queries"].sum())
    completed = int(progress["current_queries"].ge(TARGET_RUNS).sum())
    minimum = int(progress["current_queries"].min())
    maximum = int(progress["current_queries"].max())

    print("Score-bin repetition experiment plan")
    print(f"Sample transcripts: {len(progress):,}")
    print(f"Target queries per transcript: {TARGET_RUNS}")
    print(f"Current matching queries: {total_current:,}")
    print(f"Remaining queries: {total_remaining:,}")
    print(f"Completed transcripts: {completed:,}/{len(progress):,}")
    print(f"Current query-count range: {minimum}-{maximum}")

    by_bin = progress.groupby(
        ["score_bin_lower", "score_bin_upper"], as_index=False
    ).agg(
        transcripts=("transcriptid", "size"),
        completed=("current_queries", lambda values: int((values >= TARGET_RUNS).sum())),
        current_queries=("current_queries", "sum"),
        remaining_queries=("remaining_queries", "sum"),
    )
    print("\nProgress by original-score bin:")
    print(by_bin.to_string(index=False))


#%%
def estimate_batch_tokens(batch_file):
    """Estimate input tokens in a generated JSONL batch file."""
    total_tokens = 0
    with open(batch_file, "r") as file:
        for line in file:
            request = json.loads(line)
            messages = request.get("body", {}).get("messages", [])
            for message in messages:
                total_tokens += token_size(message.get("content", ""))
    return total_tokens


def unresolved_batches(tracker):
    """Return batches that must be submitted, completed, or processed first."""
    if tracker.empty:
        return tracker
    saved = tracker["saved_to_db"].apply(is_true)
    return tracker[
        tracker["status"].isin(
            ["created", "submitted", "validating", "in_progress", "finalizing", "completed"]
        )
        & ~saved
    ]


def create_batch(sample, tracker, checksum):
    """Create the next phase-balanced batch input file without submitting it."""
    pending = unresolved_batches(tracker)
    if not pending.empty:
        print("A batch is already waiting for submission or processing:")
        print_tracker(pending)
        print("No new batch was created.")
        return tracker

    progress = calculate_plan(sample)
    if progress["remaining_queries"].sum() == 0:
        print("All sampled transcripts already have eleven matching queries.")
        return tracker

    minimum_count = int(progress["current_queries"].min())
    phase_target = min(minimum_count + 1, TARGET_RUNS)
    candidate_ids = set(
        progress.loc[
            progress["current_queries"].lt(phase_target),
            "transcriptid",
        ].astype(int)
    )
    request_ids = [
        int(transcriptid)
        for transcriptid in sample["transcriptid"]
        if int(transcriptid) in candidate_ids
    ][:MAX_REQUESTS_PER_BATCH]

    if not request_ids:
        raise RuntimeError(
            f"No requests selected even though phase target {phase_target} is incomplete"
        )

    batch_number = 1 if tracker.empty else int(
        pd.to_numeric(tracker["batch_number"], errors="coerce").max()
    ) + 1
    output_path = os.path.join(
        CACHE_DIR,
        f"batch_{batch_number:04d}_target_{phase_target:02d}.jsonl",
    )

    print(
        f"Creating batch {batch_number} with {len(request_ids):,} requests "
        f"for phase target {phase_target}"
    )
    processor = BatchProcessor(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_RESPONSE_TOKENS,
    )
    processor.create_batch_input_file(
        prompt_name=PROMPT_NAME,
        transcriptids=request_ids,
        output_path=output_path,
    )

    with open(output_path, "r") as file:
        line_count = sum(1 for line in file if line.strip())
    if line_count != len(request_ids):
        raise RuntimeError(
            f"Expected {len(request_ids):,} batch requests but wrote {line_count:,}"
        )

    total_tokens = estimate_batch_tokens(output_path)
    if total_tokens > MAX_TOKENS_PER_BATCH_FILE:
        os.remove(output_path)
        raise RuntimeError(
            f"Generated batch contains {total_tokens:,} estimated input tokens, above "
            f"the {MAX_TOKENS_PER_BATCH_FILE:,} safety limit. Reduce "
            "MAX_REQUESTS_PER_BATCH and create it again."
        )

    row = {
        "batch_number": batch_number,
        "phase_target": phase_target,
        "sample_sha256": checksum,
        "batch_file": output_path,
        "batch_id": pd.NA,
        "status": "created",
        "saved_to_db": False,
        "created_at": utc_now(),
        "submitted_at": pd.NA,
        "completed_at": pd.NA,
        "processed_at": pd.NA,
        "total_requests": len(request_ids),
        "total_tokens": total_tokens,
        "total_completed": pd.NA,
        "total_failed": pd.NA,
        "inserted_rows": pd.NA,
        "skipped_existing_rows": pd.NA,
        "invalid_response_rows": pd.NA,
        "missing_output_ids": pd.NA,
    }
    tracker.loc[len(tracker), TRACKER_COLUMNS] = [
        row[column] for column in TRACKER_COLUMNS
    ]
    save_tracker(tracker)

    print(f"Created: {output_path}")
    print(f"Estimated input tokens: {total_tokens:,}")
    print("The batch has not been submitted.")
    return tracker


#%%
def submit_batch(tracker, confirm_submit):
    """Submit the single pending created batch."""
    if not confirm_submit:
        raise ValueError(
            "Submission requires --confirm-submit because it initiates paid LLM queries"
        )

    live = tracker[tracker["status"].isin(LIVE_STATUSES)]
    if not live.empty:
        print("A submitted batch is already active; no new batch was submitted.")
        print_tracker(live)
        return tracker

    completed_unsaved = tracker[
        tracker["status"].eq("completed")
        & ~tracker["saved_to_db"].apply(is_true)
    ]
    if not completed_unsaved.empty:
        print("A completed batch must be processed before submitting another batch.")
        print_tracker(completed_unsaved)
        return tracker

    candidates = tracker[tracker["status"].eq("created")]
    if candidates.empty:
        print("No created batch is waiting for submission.")
        return tracker
    if len(candidates) > 1:
        raise RuntimeError("More than one unsubmitted batch exists in the tracker")

    index = candidates.index[0]
    batch_file = tracker.loc[index, "batch_file"]
    if not os.path.exists(batch_file):
        raise FileNotFoundError(f"Batch input file not found: {batch_file}")

    processor = BatchProcessor(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_RESPONSE_TOKENS,
    )
    print(f"Submitting batch file: {batch_file}")
    batch_id = processor.submit_batch(batch_file)
    tracker.loc[index, ["batch_id", "status", "submitted_at"]] = [
        batch_id,
        "submitted",
        utc_now(),
    ]
    save_tracker(tracker)
    print(f"Submitted batch ID: {batch_id}")
    return tracker


def refresh_status(tracker):
    """Refresh OpenAI status for all submitted, unprocessed batches."""
    if tracker.empty:
        print("No batches have been created.")
        return tracker

    processor = BatchProcessor(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_RESPONSE_TOKENS,
    )
    for index, row in tracker.iterrows():
        if pd.isna(row["batch_id"]) or is_true(row["saved_to_db"]):
            continue
        if row["status"] == "created":
            continue

        status_info = processor.check_batch_status(str(row["batch_id"]))
        status = status_info.get("status")
        tracker.loc[index, "status"] = status
        tracker.loc[index, "total_completed"] = status_info.get("completed", pd.NA)
        tracker.loc[index, "total_failed"] = status_info.get("failed", pd.NA)
        if status == "completed" and pd.isna(row["completed_at"]):
            tracker.loc[index, "completed_at"] = utc_now()

    save_tracker(tracker)
    return tracker


#%%
def transcript_ids_from_batch_file(batch_file):
    """Read and validate transcript IDs from a generated batch file."""
    transcript_ids = []
    with open(batch_file, "r") as file:
        for line in file:
            request = json.loads(line)
            custom_id = request["custom_id"]
            parts = custom_id.split("-")
            if len(parts) < 3 or parts[0] != "request":
                raise ValueError(f"Unexpected custom_id in batch file: {custom_id}")
            transcript_ids.append(int(parts[1]))

    if len(transcript_ids) != len(set(transcript_ids)):
        raise ValueError("Experiment batch files must contain each transcript at most once")
    return transcript_ids


def process_completed_batches(tracker):
    """Import completed outputs idempotently using each batch's phase target."""
    candidates = tracker[
        tracker["status"].eq("completed")
        & ~tracker["saved_to_db"].apply(is_true)
    ]
    if candidates.empty:
        print("No completed, unprocessed batch is available.")
        return tracker

    processor = BatchProcessor(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_RESPONSE_TOKENS,
    )

    for index, row in candidates.iterrows():
        batch_id = str(row["batch_id"])
        batch_file = row["batch_file"]
        phase_target = int(row["phase_target"])
        expected_ids = transcript_ids_from_batch_file(batch_file)
        expected_id_set = set(expected_ids)
        current_counts = get_query_counts(expected_ids)

        batch = processor.client.batches.retrieve(batch_id)
        if not batch.output_file_id:
            raise RuntimeError(f"Completed batch {batch_id} has no output file")
        output = processor.client.files.content(batch.output_file_id)

        inserted = 0
        skipped_existing = 0
        failed_output_lines = 0
        seen_ids = set()
        lines = output.text.splitlines()
        print(
            f"Processing batch {batch_id}: {len(lines):,} output lines, "
            f"phase target {phase_target}"
        )

        for line_number, line in enumerate(lines, start=1):
            try:
                response = json.loads(line)
                custom_id = response["custom_id"]
                transcriptid = int(custom_id.split("-")[1])
            except (KeyError, ValueError, json.JSONDecodeError) as error:
                print(f"Skipping malformed output line {line_number}: {error}")
                failed_output_lines += 1
                continue

            if transcriptid not in expected_id_set:
                raise ValueError(
                    f"Batch output contains unexpected transcript ID {transcriptid}"
                )
            if transcriptid in seen_ids:
                raise ValueError(
                    f"Batch output contains duplicate transcript ID {transcriptid}"
                )
            seen_ids.add(transcriptid)

            if current_counts.get(transcriptid, 0) >= phase_target:
                skipped_existing += 1
                continue

            try:
                body = response["response"]["body"]
                content = body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as error:
                print(
                    f"Skipping failed response for transcript {transcriptid}: {error}"
                )
                failed_output_lines += 1
                continue

            parsed_score = extract_score_from_unstructured_response(content)
            if parsed_score is None or not 0 <= parsed_score <= 100:
                print(
                    f"Skipping invalid score response for transcript {transcriptid}"
                )
                failed_output_lines += 1
                continue

            insert_query_result(
                prompt_name=PROMPT_NAME,
                transcriptid=transcriptid,
                response=content,
                llm_provider="openai",
                model_name=MODEL_NAME,
                call_type="batch",
                temperature=TEMPERATURE,
                max_response=MAX_RESPONSE_TOKENS,
                input_tokens=body.get("usage", {}).get("prompt_tokens"),
                output_tokens=body.get("usage", {}).get("completion_tokens"),
            )
            current_counts[transcriptid] = current_counts.get(transcriptid, 0) + 1
            inserted += 1
            if inserted % 100 == 0:
                print(f"  Inserted {inserted:,}/{len(lines):,} responses")

        tracker.loc[index, "saved_to_db"] = True
        tracker.loc[index, "processed_at"] = utc_now()
        missing_output = len(expected_id_set - seen_ids)
        tracker.loc[index, "inserted_rows"] = inserted
        tracker.loc[index, "skipped_existing_rows"] = skipped_existing
        tracker.loc[index, "invalid_response_rows"] = failed_output_lines
        tracker.loc[index, "missing_output_ids"] = missing_output
        save_tracker(tracker)

        print(f"Inserted rows: {inserted:,}")
        print(f"Skipped rows already at phase target: {skipped_existing:,}")
        print(f"Malformed or failed output lines: {failed_output_lines:,}")
        print(f"Expected transcript IDs absent from output: {missing_output:,}")
        if failed_output_lines or missing_output:
            print(
                "Missing responses remain below target and will be picked up by a "
                "future batch."
            )

    return tracker


#%%
def advance_batches(
    sample,
    tracker,
    checksum,
    max_batches,
    poll_minutes,
    confirm_submit,
):
    """Complete a bounded number of batches, polling conservatively between checks."""
    if not confirm_submit:
        raise ValueError(
            "Advance requires --confirm-submit because it submits paid LLM batches"
        )
    if max_batches <= 0:
        raise ValueError("--max-batches must be positive")
    if poll_minutes <= 0:
        raise ValueError("--poll-minutes must be positive")

    completed_in_run = 0
    poll_seconds = poll_minutes * 60
    print(
        f"Starting bounded advance: up to {max_batches} completed batches, "
        f"checking every {poll_minutes:g} minutes"
    )

    while completed_in_run < max_batches:
        tracker = refresh_status(tracker)

        stopped = tracker[
            tracker["status"].isin(["failed", "expired", "cancelled", "canceled"])
            & ~tracker["saved_to_db"].apply(is_true)
        ]
        if not stopped.empty:
            print("Stopping because a batch entered a failure or cancellation state:")
            print_tracker(stopped)
            return tracker

        completed = tracker[
            tracker["status"].eq("completed")
            & ~tracker["saved_to_db"].apply(is_true)
        ]
        if not completed.empty:
            api_failures = pd.to_numeric(
                completed["total_failed"], errors="coerce"
            ).fillna(0)
            if api_failures.gt(0).any():
                print(
                    "Stopping before import because OpenAI reports failed requests. "
                    "Inspect and process this batch manually."
                )
                print_tracker(completed)
                return tracker

            batch_numbers = set(
                pd.to_numeric(completed["batch_number"], errors="raise").astype(int)
            )
            tracker = process_completed_batches(tracker)
            processed = tracker[
                pd.to_numeric(tracker["batch_number"], errors="coerce").isin(
                    batch_numbers
                )
            ]
            invalid_rows = pd.to_numeric(
                processed["invalid_response_rows"], errors="coerce"
            ).fillna(0)
            missing_ids = pd.to_numeric(
                processed["missing_output_ids"], errors="coerce"
            ).fillna(0)
            if invalid_rows.gt(0).any() or missing_ids.gt(0).any():
                print(
                    "Stopping because imported output had invalid responses or "
                    "missing transcript IDs."
                )
                print_tracker(processed)
                return tracker

            completed_in_run += len(batch_numbers)
            print(
                f"Completed {completed_in_run}/{max_batches} batches in this run."
            )
            if completed_in_run >= max_batches:
                break
            continue

        live = tracker[tracker["status"].isin(LIVE_STATUSES)]
        if not live.empty:
            print_tracker(live)
            print(
                f"No action needed. Waiting {poll_minutes:g} minutes before "
                "checking again..."
            )
            time.sleep(poll_seconds)
            continue

        created = tracker[tracker["status"].eq("created")]
        if created.empty:
            progress = calculate_plan(sample)
            if int(progress["remaining_queries"].sum()) == 0:
                print("All sampled transcripts have reached eleven queries.")
                break
            tracker = create_batch(sample, tracker, checksum)

        tracker = submit_batch(tracker, confirm_submit=True)
        print(
            f"Batch submitted. Waiting {poll_minutes:g} minutes before the "
            "first status check..."
        )
        time.sleep(poll_seconds)

    print(
        f"Bounded advance finished after completing {completed_in_run} batch(es)."
    )
    print_plan(calculate_plan(sample))
    return tracker


#%%
def parse_args():
    """Parse runner arguments."""
    parser = argparse.ArgumentParser(
        description="Manage batches for the score-bin repetition experiment."
    )
    parser.add_argument(
        "operation",
        choices=["plan", "create", "submit", "status", "process", "advance"],
        help="Operation to perform.",
    )
    parser.add_argument(
        "--confirm-submit",
        action="store_true",
        help="Required confirmation for operations that submit paid batches.",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=5,
        help="Maximum batches to complete during advance (default: 5).",
    )
    parser.add_argument(
        "--poll-minutes",
        type=float,
        default=10.0,
        help="Minutes between status checks during advance (default: 10).",
    )
    return parser.parse_args()


def main():
    """Run one explicit batch-management operation."""
    args = parse_args()
    os.makedirs(CACHE_DIR, exist_ok=True)

    with open(LOCK_PATH, "w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another score-bin repeat runner process is active. Exiting.")
            return

        sample = load_sample()
        checksum = sample_sha256()
        tracker = load_tracker()
        validate_tracker_sample(tracker, checksum)

        if args.operation == "plan":
            print_plan(calculate_plan(sample))
        elif args.operation == "create":
            tracker = create_batch(sample, tracker, checksum)
            print_tracker(tracker)
        elif args.operation == "submit":
            tracker = submit_batch(tracker, args.confirm_submit)
            print_tracker(tracker)
        elif args.operation == "status":
            tracker = refresh_status(tracker)
            print_tracker(tracker)
        elif args.operation == "process":
            tracker = refresh_status(tracker)
            tracker = process_completed_batches(tracker)
            print_tracker(tracker)
        elif args.operation == "advance":
            tracker = advance_batches(
                sample=sample,
                tracker=tracker,
                checksum=checksum,
                max_batches=args.max_batches,
                poll_minutes=args.poll_minutes,
                confirm_submit=args.confirm_submit,
            )
            print_tracker(tracker)


if __name__ == "__main__":
    main()
