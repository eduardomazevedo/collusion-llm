#!/usr/bin/env python3
"""
Run one single-query benchmark pass across multiple models for a fixed prompt.

This script is intentionally separate from batch benchmarking so it does not
interfere with ongoing batch submissions. It targets the benchmark sample
(transcripts with Joe score or ACL manual flag) and runs only missing
transcript-model pairs for the selected prompt.

Default behavior:
- prompt: SimpleCapacityV8.1.1
- models: structured-output models from assets/llm_config.json
- exactly one required run per transcript per model
"""

import argparse
import concurrent.futures as cf
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd

import config
import modules.capiq as capiq
from modules.llm import LLMQuery
from modules.queries_db import insert_query_result
from modules.utils import prep_transcript_for_review


TRACKER_PATH = os.path.join(config.CACHE_DIR, "model_benchmark_tracker.csv")
DEFAULT_PROMPT = "SimpleCapacityV8.1.1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_benchmark_transcript_ids() -> List[int]:
    """Return transcript IDs with either Joe score or ACL label."""
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    ids = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())]["transcriptid"]
    return sorted(ids.dropna().astype(int).unique().tolist())


def load_structured_models(provider: str = "openai") -> List[str]:
    """Return models marked as structured-output capable in llm_config."""
    llm_cfg_path = os.path.join(config.ROOT, "assets", "llm_config.json")
    with open(llm_cfg_path, "r") as f:
        cfg = json.load(f)

    model_cfg = cfg.get("providers", {}).get(provider, {}).get("models", {})
    models = [
        model_name
        for model_name, props in model_cfg.items()
        if props.get("supports_structured_output", False)
    ]
    return sorted(models)


def ensure_tracker(models: List[str], prompt_name: str, target_runs: int) -> pd.DataFrame:
    """Load or initialize tracker and seed missing model rows."""
    cols = [
        "model",
        "prompt_name",
        "target_runs",
        "status",
        "total_benchmark",
        "existing_before",
        "to_run",
        "saved_count",
        "failed_estimate",
        "started_at",
        "completed_at",
        "last_error",
        "updated_at",
    ]
    if os.path.exists(TRACKER_PATH):
        df = pd.read_csv(TRACKER_PATH)
        for col in cols:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[cols]
    else:
        df = pd.DataFrame(columns=cols)

    existing_keys = set(
        zip(
            df["model"].fillna(""),
            df["prompt_name"].fillna(""),
            pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int),
        )
    )

    for model in models:
        key = (model, prompt_name, int(target_runs))
        if key not in existing_keys:
            df.loc[len(df)] = {
                "model": model,
                "prompt_name": prompt_name,
                "target_runs": int(target_runs),
                "status": "not_started",
                "total_benchmark": pd.NA,
                "existing_before": pd.NA,
                "to_run": pd.NA,
                "saved_count": pd.NA,
                "failed_estimate": pd.NA,
                "started_at": pd.NA,
                "completed_at": pd.NA,
                "last_error": pd.NA,
                "updated_at": utc_now_iso(),
            }

    return df


def save_tracker(df: pd.DataFrame) -> None:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    df.to_csv(TRACKER_PATH, index=False)


def get_existing_counts(prompt_name: str, model_name: str, transcript_ids: List[int]) -> Dict[int, int]:
    """Count existing rows by transcript for this prompt/model on benchmark IDs."""
    if not transcript_ids:
        return {}
    conn = sqlite3.connect(config.DATABASE_PATH)
    placeholders = ",".join(["?"] * len(transcript_ids))
    query = f"""
        SELECT transcriptid, COUNT(*) as n
        FROM queries
        WHERE prompt_name = ?
          AND model_name = ?
          AND transcriptid IN ({placeholders})
        GROUP BY transcriptid
    """
    rows = conn.execute(query, [prompt_name, model_name, *transcript_ids]).fetchall()
    conn.close()
    return {int(tid): int(n) for tid, n in rows}


def deficits_for_target(existing_counts: Dict[int, int], transcript_ids: List[int], target_runs: int) -> List[int]:
    """Return transcript IDs needing at least one more run up to target_runs."""
    missing = []
    for tid in transcript_ids:
        if existing_counts.get(int(tid), 0) < int(target_runs):
            missing.append(int(tid))
    return missing


def update_row(
    df: pd.DataFrame,
    model: str,
    prompt_name: str,
    target_runs: int,
    updates: Dict,
) -> pd.DataFrame:
    mask = (
        (df["model"] == model)
        & (df["prompt_name"] == prompt_name)
        & (pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int) == int(target_runs))
    )
    if not mask.any():
        return df
    idx = df[mask].index[0]
    for k, v in updates.items():
        df.loc[idx, k] = v
    df.loc[idx, "updated_at"] = utc_now_iso()
    return df


def run_model(
    model: str,
    prompt_name: str,
    benchmark_ids: List[int],
    target_runs: int,
    df: pd.DataFrame,
    workers: int,
    max_retries: int,
    retry_delay: float,
    reasoning_effort: str,
) -> pd.DataFrame:
    total_benchmark = len(benchmark_ids)
    existing_before = get_existing_counts(prompt_name, model, benchmark_ids)
    to_run_ids = deficits_for_target(existing_before, benchmark_ids, target_runs)

    print(
        f"[model] {model} | prompt={prompt_name} | benchmark={total_benchmark} | "
        f"existing={total_benchmark - len(to_run_ids)} | to_run={len(to_run_ids)}"
    )

    df = update_row(
        df,
        model,
        prompt_name,
        target_runs,
        {
            "status": "running" if to_run_ids else "completed",
            "total_benchmark": total_benchmark,
            "existing_before": total_benchmark - len(to_run_ids),
            "to_run": len(to_run_ids),
            "saved_count": 0 if to_run_ids else 0,
            "failed_estimate": 0 if not to_run_ids else pd.NA,
            "started_at": utc_now_iso() if to_run_ids else pd.NA,
            "completed_at": pd.NA,
            "last_error": pd.NA,
        },
    )
    save_tracker(df)

    if not to_run_ids:
        print(f"[model] {model}: no deficits; skipping.")
        return df

    try:
        # Validate model capability once up-front.
        probe = LLMQuery(model=model, reasoning_effort=reasoning_effort)
        if not probe.model_config.get("supports_structured_output", False):
            raise ValueError(
                "Model is not configured for structured output in assets/llm_config.json."
            )

        print(f"[model] {model}: fetching transcript payloads for {len(to_run_ids)} transcripts...")
        transcript_texts = capiq.get_transcripts(to_run_ids)
        prepared_inputs: Dict[int, str] = {}
        for tid in to_run_ids:
            if tid not in transcript_texts:
                continue
            transcript_data = json.loads(transcript_texts[tid])
            prepared_inputs[tid] = prep_transcript_for_review(transcript_data)

        missing_payload = len(to_run_ids) - len(prepared_inputs)
        if missing_payload > 0:
            print(f"[model] {model}: warning - missing transcript payload for {missing_payload} IDs.")

        thread_local = threading.local()

        def get_llm() -> LLMQuery:
            llm = getattr(thread_local, "llm", None)
            if llm is None:
                llm = LLMQuery(model=model, reasoning_effort=reasoning_effort)
                thread_local.llm = llm
            return llm

        def run_one(tid: int):
            if tid not in prepared_inputs:
                return tid, None, None, "MissingTranscriptPayload"

            user_input = prepared_inputs[tid]
            attempt = 0
            while attempt <= max_retries:
                try:
                    llm = get_llm()
                    response, token_info = llm.generate_response(prompt_name, user_input)
                    return tid, response, token_info, None
                except Exception as err:
                    attempt += 1
                    if attempt > max_retries:
                        return tid, None, None, f"{type(err).__name__}: {str(err)}"
                    time.sleep(retry_delay * (2 ** (attempt - 1)))

            return tid, None, None, "UnknownError"

        requested_ids = sorted(prepared_inputs.keys())
        n_requested = len(requested_ids)
        print(
            f"[model] {model}: submitting {n_requested} single calls "
            f"with workers={workers}, max_retries={max_retries}"
        )

        saved_count = 0
        failed = 0
        processed = 0

        with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = {ex.submit(run_one, tid): tid for tid in requested_ids}
            for fut in cf.as_completed(futures):
                tid, response, token_info, err = fut.result()
                processed += 1
                if err is None and response is not None and token_info is not None:
                    insert_query_result(
                        prompt_name=prompt_name,
                        transcriptid=int(tid),
                        response=response,
                        llm_provider="openai",
                        model_name=model,
                        call_type="single",
                        temperature=probe.temperature,
                        max_response=probe.max_tokens,
                        input_tokens=token_info.get("input_tokens"),
                        output_tokens=token_info.get("output_tokens"),
                    )
                    saved_count += 1
                else:
                    failed += 1
                    print(f"[model] {model}: failed transcriptid={tid} | {err}")

                if processed % 10 == 0 or processed == n_requested:
                    print(
                        f"[model] {model}: progress {processed}/{n_requested} | "
                        f"saved={saved_count} failed={failed}"
                    )
                    df = update_row(
                        df,
                        model,
                        prompt_name,
                        target_runs,
                        {
                            "saved_count": saved_count,
                            "failed_estimate": failed,
                        },
                    )
                    save_tracker(df)

        failed_estimate = failed + missing_payload
        final_status = "completed" if failed_estimate == 0 else "partial"
        print(
            f"[model] {model}: done | saved={saved_count}/{len(to_run_ids)} | "
            f"failed_estimate={failed_estimate}"
        )

        df = update_row(
            df,
            model,
            prompt_name,
            target_runs,
            {
                "status": final_status,
                "saved_count": saved_count,
                "failed_estimate": failed_estimate,
                "completed_at": utc_now_iso(),
            },
        )
        save_tracker(df)
        return df

    except Exception as e:
        err = f"{type(e).__name__}: {str(e)}"
        print(f"[model] {model}: ERROR -> {err}")
        df = update_row(
            df,
            model,
            prompt_name,
            target_runs,
            {
                "status": "error",
                "last_error": err,
                "completed_at": utc_now_iso(),
            },
        )
        save_tracker(df)
        return df


def print_status(df: pd.DataFrame, prompt_name: str, target_runs: int) -> None:
    mask = (
        (df["prompt_name"] == prompt_name)
        & (pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int) == int(target_runs))
    )
    cols = [
        "model",
        "prompt_name",
        "target_runs",
        "status",
        "total_benchmark",
        "existing_before",
        "to_run",
        "saved_count",
        "failed_estimate",
        "last_error",
        "updated_at",
    ]
    print(df.loc[mask, cols].sort_values("model").to_string(index=False))


def parse_models_arg(models_arg: str) -> List[str]:
    return [m.strip() for m in models_arg.split(",") if m.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one-pass single-call benchmark queries across models."
    )
    parser.add_argument(
        "--operation",
        choices=["run", "status"],
        default="run",
        help="run: submit missing single calls; status: print tracker.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help=f"Prompt name (default: {DEFAULT_PROMPT})",
    )
    parser.add_argument(
        "--target-runs",
        type=int,
        default=1,
        help="Required minimum runs per transcript/model for this prompt (default: 1).",
    )
    parser.add_argument(
        "--models",
        default="",
        help=(
            "Comma-separated model list. If omitted, uses all structured-output "
            "models in assets/llm_config.json."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent single-call workers per model (default: 4).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Per-transcript retries for API failures (default: 2).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base retry delay in seconds; exponential backoff is applied (default: 2.0).",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        default="medium",
        help="Reasoning effort for Responses API reasoning models (default: medium).",
    )

    args = parser.parse_args()
    models = parse_models_arg(args.models) if args.models else load_structured_models()
    benchmark_ids = load_benchmark_transcript_ids()

    print(
        f"[init] benchmark transcripts={len(benchmark_ids)} | prompt={args.prompt} | "
        f"target_runs={args.target_runs} | models={len(models)} | workers={args.workers} "
        f"| reasoning_effort={args.reasoning_effort}"
    )
    print(f"[init] models: {', '.join(models)}")

    df = ensure_tracker(models=models, prompt_name=args.prompt, target_runs=args.target_runs)
    save_tracker(df)

    if args.operation == "status":
        print_status(df, prompt_name=args.prompt, target_runs=args.target_runs)
        return

    for i, model in enumerate(models, start=1):
        print(f"\n[{i}/{len(models)}] Processing model: {model}")
        df = run_model(
            model=model,
            prompt_name=args.prompt,
            benchmark_ids=benchmark_ids,
            target_runs=args.target_runs,
            df=df,
            workers=args.workers,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            reasoning_effort=args.reasoning_effort,
        )

    print("\n[done] Final status:")
    df = ensure_tracker(models=models, prompt_name=args.prompt, target_runs=args.target_runs)
    print_status(df, prompt_name=args.prompt, target_runs=args.target_runs)


if __name__ == "__main__":
    main()
