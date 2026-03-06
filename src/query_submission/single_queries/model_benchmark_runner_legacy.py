#!/usr/bin/env python3
"""
Run benchmark single-call queries for older OpenAI model families.

This runner is isolated from model_benchmark_runner.py and is intended for:
1) Older chat models using JSON mode with SimpleCapacityV8.1.1_JSON
2) Legacy completion models using an adapted completions-style JSON prompt

Default prompt key for DB entries: SimpleCapacityV8.1.1_JSON
"""

import argparse
import concurrent.futures as cf
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
from openai import OpenAI

import config
import modules.capiq as capiq
from modules.llm import LLMQuery
from modules.queries_db import insert_query_result
from modules.utils import (
    extract_invalid_response,
    extract_score_from_unstructured_response,
    prep_transcript_for_review,
)


DEFAULT_PROMPT = "SimpleCapacityV8.1.1_JSON"
TRACKER_PATH = os.path.join(config.CACHE_DIR, "model_benchmark_legacy_tracker.csv")

DEFAULT_CHAT_JSON_MODELS = ["gpt-4-turbo", "gpt-3.5-turbo"]
DEFAULT_CHAT_TEXT_MODELS = ["gpt-4"]
DEFAULT_COMPLETIONS_MODELS = ["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_benchmark_transcript_ids() -> List[int]:
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    ids = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())]["transcriptid"]
    return sorted(ids.dropna().astype(int).unique().tolist())


def ensure_tracker(models: List[str], prompt_name: str, target_runs: int) -> pd.DataFrame:
    cols = [
        "model",
        "prompt_name",
        "target_runs",
        "mode",
        "status",
        "total_benchmark",
        "existing_before",
        "to_run",
        "saved_count",
        "failed_count",
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
            mode = (
                "chat_json" if model in DEFAULT_CHAT_JSON_MODELS
                else "chat_text" if model in DEFAULT_CHAT_TEXT_MODELS
                else "completions"
            )
            df.loc[len(df)] = {
                "model": model,
                "prompt_name": prompt_name,
                "target_runs": int(target_runs),
                "mode": mode,
                "status": "not_started",
                "total_benchmark": pd.NA,
                "existing_before": pd.NA,
                "to_run": pd.NA,
                "saved_count": pd.NA,
                "failed_count": pd.NA,
                "started_at": pd.NA,
                "completed_at": pd.NA,
                "last_error": pd.NA,
                "updated_at": utc_now_iso(),
            }
    return df


def save_tracker(df: pd.DataFrame) -> None:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    df.to_csv(TRACKER_PATH, index=False)


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
        # Prevent pandas dtype warnings when writing strings into NaN/float-inferred columns.
        if isinstance(v, str) and k in df.columns and df[k].dtype != object:
            df[k] = df[k].astype(object)
        df.loc[idx, k] = v
    df.loc[idx, "updated_at"] = utc_now_iso()
    return df


def get_existing_counts(prompt_name: str, model_name: str, transcript_ids: List[int]) -> Dict[int, int]:
    if not transcript_ids:
        return {}
    conn = sqlite3.connect(config.DATABASE_PATH)
    placeholders = ",".join(["?"] * len(transcript_ids))
    q = f"""
        SELECT transcriptid, COUNT(*) as n
        FROM queries
        WHERE prompt_name = ?
          AND model_name = ?
          AND transcriptid IN ({placeholders})
        GROUP BY transcriptid
    """
    rows = conn.execute(q, [prompt_name, model_name, *transcript_ids]).fetchall()
    conn.close()
    return {int(tid): int(n) for tid, n in rows}


def deficits_for_target(existing_counts: Dict[int, int], transcript_ids: List[int], target_runs: int) -> List[int]:
    return [int(tid) for tid in transcript_ids if existing_counts.get(int(tid), 0) < int(target_runs)]


def get_prompt_input_token_estimates(prompt_name: str, transcript_ids: List[int]) -> Dict[int, int]:
    """
    Estimate prompt-side input tokens by transcript from prior rows in queries DB.
    Uses the latest row with non-null input_tokens for each transcript/prompt.
    """
    if not transcript_ids:
        return {}
    conn = sqlite3.connect(config.DATABASE_PATH)
    placeholders = ",".join(["?"] * len(transcript_ids))
    q = f"""
        SELECT transcriptid, input_tokens, date
        FROM queries
        WHERE prompt_name = ?
          AND transcriptid IN ({placeholders})
          AND input_tokens IS NOT NULL
        ORDER BY date DESC
    """
    rows = conn.execute(q, [prompt_name, *transcript_ids]).fetchall()
    conn.close()

    out: Dict[int, int] = {}
    for tid, input_tokens, _ in rows:
        tid = int(tid)
        if tid not in out:
            out[tid] = int(input_tokens)
    return out


def normalize_response_to_json(response_text: str) -> Optional[str]:
    """
    Normalize response to canonical JSON shape with required numeric score:
      {"score": int, "reasoning": str, "excerpts": list[str]}
    """
    if not response_text:
        return None

    parsed: Dict = {}
    try:
        candidate = json.loads(response_text)
        if isinstance(candidate, dict):
            parsed = candidate
    except Exception:
        pass

    if not parsed:
        try:
            parsed = extract_invalid_response(response_text, ["score", "reasoning", "excerpts"])
        except Exception:
            parsed = {}

    score = parsed.get("score")
    if score is None:
        extracted_score = extract_score_from_unstructured_response(response_text)
        if extracted_score is not None:
            score = extracted_score

    try:
        if score is None:
            return None
        score_num = float(score)
    except Exception:
        return None

    # enforce benchmark-compatible score bounds
    if score_num < 0 or score_num > 100:
        return None

    reasoning = parsed.get("reasoning", "")
    if reasoning is None:
        reasoning = ""
    reasoning = str(reasoning)

    excerpts = parsed.get("excerpts", [])
    if excerpts is None:
        excerpts = []
    if isinstance(excerpts, str):
        excerpts = [excerpts]
    if not isinstance(excerpts, list):
        excerpts = [str(excerpts)]
    excerpts = [str(x) for x in excerpts]

    normalized = {
        "score": int(round(score_num)),
        "reasoning": reasoning,
        "excerpts": excerpts,
    }
    return json.dumps(normalized)


def insert_with_retry(
    *,
    prompt_name: str,
    transcriptid: int,
    response: str,
    model_name: str,
    temperature: float,
    max_response: int,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    retries: int = 5,
    delay: float = 1.0,
) -> None:
    attempt = 0
    while True:
        try:
            insert_query_result(
                prompt_name=prompt_name,
                transcriptid=transcriptid,
                response=response,
                llm_provider="openai",
                model_name=model_name,
                call_type="single",
                temperature=temperature,
                max_response=max_response,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            return
        except sqlite3.OperationalError as e:
            attempt += 1
            if attempt > retries:
                raise e
            time.sleep(delay * (2 ** (attempt - 1)))


def run_chat_json_call(
    model: str,
    prompt_name: str,
    transcript_input: str,
    llm: LLMQuery,
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    try:
        prompt_cfg = llm._get_prompt(prompt_name)
        system_message = (
            prompt_cfg["system_message"]
            + "\n\nReturn only a valid JSON object. No extra text."
        )
        response = llm.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": transcript_input},
            ],
            response_format={"type": "json_object"},
            temperature=llm.temperature,
            max_tokens=max_tokens_cap(model, llm.max_tokens),
        )
        content = response.choices[0].message.content if response.choices else ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None

        normalized = normalize_response_to_json(content)
        if normalized is None:
            return None, None, None, "InvalidResponseFormat"
        return (
            normalized,
            input_tokens,
            output_tokens,
            None,
        )
    except Exception as e:
        return None, None, None, f"{type(e).__name__}: {str(e)}"


def max_tokens_cap(model: str, requested: int) -> int:
    # Conservative caps for older model families.
    caps = {
        "gpt-4": 1024,
        "gpt-4-turbo": 1024,
        "gpt-3.5-turbo": 1024,
        "gpt-3.5-turbo-instruct": 1024,
        "davinci-002": 1024,
        "babbage-002": 1024,
    }
    return min(int(requested), caps.get(model, int(requested)))


def model_context_window(model: str) -> Optional[int]:
    # Context windows used for conservative pre-skip checks in legacy runner.
    windows = {
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-instruct": 4096,
        "davinci-002": 16384,
        "babbage-002": 16384,
    }
    return windows.get(model)


def shrink_transcript_tail(text: str, keep_ratio: float, min_chars: int = 1200) -> str:
    """Trim transcript text from the end while keeping at least min_chars."""
    if not text:
        return text
    keep_ratio = max(0.01, min(1.0, float(keep_ratio)))
    keep_len = max(min_chars, int(len(text) * keep_ratio))
    keep_len = min(keep_len, len(text))
    return text[:keep_len]


def is_context_limit_error(error: Optional[str]) -> bool:
    if not error:
        return False
    e = str(error).lower()
    return ("context_length_exceeded" in e) or ("maximum context length" in e)


def run_chat_text_call(
    model: str,
    prompt_name: str,
    transcript_input: str,
    llm: LLMQuery,
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    try:
        prompt_cfg = llm._get_prompt(prompt_name)
        system_message = prompt_cfg["system_message"]
        response = llm.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": transcript_input},
            ],
            temperature=llm.temperature,
            max_tokens=max_tokens_cap(model, llm.max_tokens),
        )
        content = response.choices[0].message.content if response.choices else ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None

        normalized = normalize_response_to_json(content)
        if normalized is None:
            return None, input_tokens, output_tokens, "InvalidResponseFormat"
        return normalized, input_tokens, output_tokens, None
    except Exception as e:
        return None, None, None, f"{type(e).__name__}: {str(e)}"


def run_completions_call(
    model: str,
    prompt_name: str,
    transcript_input: str,
    llm: LLMQuery,
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    try:
        prompt_cfg = llm._get_prompt(prompt_name)
        system_message = prompt_cfg["system_message"]
        full_prompt = (
            f"{system_message}\n\n"
            "You MUST output ONLY a valid JSON object with this exact schema:\n"
            "{\n"
            "  \"score\": <integer 0-100>,\n"
            "  \"reasoning\": \"<brief explanation>\",\n"
            "  \"excerpts\": [\"<excerpt 1>\", \"<excerpt 2>\"]\n"
            "}\n\n"
            "If unsure, still output valid JSON with best-effort values.\n\n"
            "Transcript:\n"
            f"{transcript_input}\n\n"
            "Return ONLY the JSON object. Do not add any text before or after."
        )
        completion = llm.client.completions.create(
            model=model,
            prompt=full_prompt,
            temperature=llm.temperature,
            max_tokens=max_tokens_cap(model, llm.max_tokens),
        )
        text = completion.choices[0].text if completion.choices else ""
        usage = getattr(completion, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None

        normalized = normalize_response_to_json(text)
        if normalized is None:
            return None, input_tokens, output_tokens, "InvalidResponseFormat"
        return normalized, input_tokens, output_tokens, None
    except Exception as e:
        return None, None, None, f"{type(e).__name__}: {str(e)}"


def run_model(
    model: str,
    mode: str,
    prompt_name: str,
    benchmark_ids: List[int],
    target_runs: int,
    df: pd.DataFrame,
    max_attempts: int,
    retry_delay: float,
    workers: int,
    prepared_inputs: Dict[int, str],
) -> pd.DataFrame:
    total_benchmark = len(benchmark_ids)
    existing_before = get_existing_counts(prompt_name, model, benchmark_ids)
    to_run_ids = deficits_for_target(existing_before, benchmark_ids, target_runs)

    print(
        f"[model] {model} | mode={mode} | prompt={prompt_name} | benchmark={total_benchmark} | "
        f"existing={total_benchmark - len(to_run_ids)} | to_run={len(to_run_ids)}"
    )

    df = update_row(
        df,
        model,
        prompt_name,
        target_runs,
        {
            "mode": mode,
            "status": "running" if to_run_ids else "completed",
            "total_benchmark": total_benchmark,
            "existing_before": total_benchmark - len(to_run_ids),
            "to_run": len(to_run_ids),
            "saved_count": 0,
            "failed_count": 0,
            "started_at": utc_now_iso() if to_run_ids else pd.NA,
            "completed_at": pd.NA,
            "last_error": pd.NA,
        },
    )
    save_tracker(df)

    if not to_run_ids:
        print(f"[model] {model}: no deficits; skipping.")
        return df

    # Build model-local inputs so any trimming does not affect other models.
    model_inputs: Dict[int, str] = {
        int(tid): prepared_inputs[int(tid)] for tid in to_run_ids if int(tid) in prepared_inputs
    }

    # Pre-trim transcripts that are estimated to exceed context budget.
    input_token_estimates = get_prompt_input_token_estimates(prompt_name, to_run_ids)
    output_cap = max_tokens_cap(model, config.MAX_TOKENS)
    context_window = model_context_window(model)
    if context_window is not None:
        input_budget = context_window - output_cap
        trimmed = 0
        over_limit_ids = []
        for tid in to_run_ids:
            est = input_token_estimates.get(int(tid))
            if est is None or est <= input_budget or int(tid) not in model_inputs:
                continue
            over_limit_ids.append(int(tid))
            keep_ratio = (input_budget / float(est)) * 0.96
            before_len = len(model_inputs[int(tid)])
            model_inputs[int(tid)] = shrink_transcript_tail(model_inputs[int(tid)], keep_ratio)
            after_len = len(model_inputs[int(tid)])
            if after_len < before_len:
                trimmed += 1

        if over_limit_ids:
            print(
                f"[model] {model}: pre-trimmed {trimmed}/{len(over_limit_ids)} over-limit transcripts "
                f"(budget={input_budget} input tokens)."
            )
            df = update_row(
                df,
                model,
                prompt_name,
                target_runs,
                {"last_error": f"PreTrimContextLimit:{len(over_limit_ids)}"},
            )
            save_tracker(df)

    if not to_run_ids:
        df = update_row(
            df,
            model,
            prompt_name,
            target_runs,
            {
                "status": "partial",
                "saved_count": 0,
                "failed_count": int(df.loc[
                    (df["model"] == model)
                    & (df["prompt_name"] == prompt_name)
                    & (pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int) == int(target_runs)),
                    "failed_count",
                ].fillna(0).iloc[0]),
                "completed_at": utc_now_iso(),
            },
        )
        save_tracker(df)
        print(f"[model] {model}: nothing left to run after pre-skip.")
        return df

    thread_local = threading.local()

    def get_llm() -> LLMQuery:
        llm = getattr(thread_local, "llm", None)
        if llm is None:
            llm = LLMQuery(model=model)
            thread_local.llm = llm
        return llm

    def run_one(tid: int):
        if tid not in model_inputs:
            return tid, None, None, None, "MissingTranscriptPayload"

        transcript_input = model_inputs[tid]
        normalized = None
        in_tok = None
        out_tok = None
        error = None

        for attempt in range(1, max_attempts + 1):
            llm = get_llm()
            if mode == "chat_json":
                normalized, in_tok, out_tok, error = run_chat_json_call(
                    model=model,
                    prompt_name=prompt_name,
                    transcript_input=transcript_input,
                    llm=llm,
                )
            elif mode == "chat_text":
                normalized, in_tok, out_tok, error = run_chat_text_call(
                    model=model,
                    prompt_name=prompt_name,
                    transcript_input=transcript_input,
                    llm=llm,
                )
            else:
                normalized, in_tok, out_tok, error = run_completions_call(
                    model=model,
                    prompt_name=prompt_name,
                    transcript_input=transcript_input,
                    llm=llm,
                )

            if normalized is not None:
                return tid, normalized, in_tok, out_tok, None

            # If context is still too large, trim more from the end and retry.
            if attempt < max_attempts and is_context_limit_error(error):
                trimmed_input = shrink_transcript_tail(transcript_input, keep_ratio=0.90)
                if len(trimmed_input) < len(transcript_input):
                    transcript_input = trimmed_input
                    continue

            if attempt < max_attempts:
                time.sleep(retry_delay * (2 ** (attempt - 1)))

        return tid, None, in_tok, out_tok, error

    saved = 0
    failed = int(
        df.loc[
            (df["model"] == model)
            & (df["prompt_name"] == prompt_name)
            & (pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int) == int(target_runs)),
            "failed_count",
        ].fillna(0).iloc[0]
    )
    last_error = None

    print(
        f"[model] {model}: submitting {len(to_run_ids)} calls with workers={workers}, "
        f"max_attempts={max_attempts}"
    )
    with cf.ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futures = {ex.submit(run_one, tid): tid for tid in to_run_ids}
        for i, fut in enumerate(cf.as_completed(futures), start=1):
            tid, normalized, in_tok, out_tok, error = fut.result()
            if normalized is None:
                failed += 1
                last_error = error
                print(f"[model] {model}: failed transcriptid={tid} | error={error}")
            else:
                try:
                    llm_for_cfg = get_llm()
                    insert_with_retry(
                        prompt_name=prompt_name,
                        transcriptid=int(tid),
                        response=normalized,
                        model_name=model,
                        temperature=llm_for_cfg.temperature,
                        max_response=llm_for_cfg.max_tokens,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                    )
                    saved += 1
                except Exception as e:
                    failed += 1
                    last_error = f"{type(e).__name__}: {str(e)}"
                    print(f"[model] {model}: DB save failed transcriptid={tid} | {last_error}")

            if i % 10 == 0 or i == len(to_run_ids):
                print(f"[model] {model}: progress {i}/{len(to_run_ids)} | saved={saved} failed={failed}")
                df = update_row(
                    df,
                    model,
                    prompt_name,
                    target_runs,
                    {"saved_count": saved, "failed_count": failed, "last_error": last_error},
                )
                save_tracker(df)

    final_status = "completed" if failed == 0 else "partial"
    df = update_row(
        df,
        model,
        prompt_name,
        target_runs,
        {
            "status": final_status,
            "saved_count": saved,
            "failed_count": failed,
            "last_error": last_error,
            "completed_at": utc_now_iso(),
        },
    )
    save_tracker(df)
    print(f"[model] {model}: done | saved={saved}/{len(to_run_ids)} | failed={failed}")
    return df


def print_status(df: pd.DataFrame, prompt_name: str, target_runs: int) -> None:
    mask = (
        (df["prompt_name"] == prompt_name)
        & (pd.to_numeric(df["target_runs"], errors="coerce").fillna(-1).astype(int) == int(target_runs))
    )
    cols = [
        "model",
        "mode",
        "prompt_name",
        "target_runs",
        "status",
        "total_benchmark",
        "existing_before",
        "to_run",
        "saved_count",
        "failed_count",
        "last_error",
        "updated_at",
    ]
    if not mask.any():
        print("No tracker rows found for this prompt/target.")
        return
    print(df.loc[mask, cols].sort_values(["mode", "model"]).to_string(index=False))


def parse_models_arg(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run legacy/older-model benchmark single calls with JSON validation."
    )
    parser.add_argument("--operation", choices=["run", "status"], default="run")
    parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT)
    parser.add_argument("--target-runs", type=int, default=1)
    parser.add_argument(
        "--chat-models",
        type=str,
        default=",".join(DEFAULT_CHAT_JSON_MODELS),
        help="Comma-separated older chat models (JSON mode path).",
    )
    parser.add_argument(
        "--chat-text-models",
        type=str,
        default=",".join(DEFAULT_CHAT_TEXT_MODELS),
        help="Comma-separated older chat models that do not support JSON mode.",
    )
    parser.add_argument(
        "--completion-models",
        type=str,
        default=",".join(DEFAULT_COMPLETIONS_MODELS),
        help="Comma-separated completion-style models.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max attempts per transcript to get a valid parseable score.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base retry delay in seconds for exponential backoff.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of parallel workers per model.",
    )
    args = parser.parse_args()

    chat_models = parse_models_arg(args.chat_models)
    chat_text_models = parse_models_arg(args.chat_text_models)
    completion_models = parse_models_arg(args.completion_models)
    models = chat_models + chat_text_models + completion_models
    benchmark_ids = load_benchmark_transcript_ids()

    print(
        f"[init] benchmark={len(benchmark_ids)} | prompt={args.prompt} | target_runs={args.target_runs} | "
        f"chat_models={len(chat_models)} | chat_text_models={len(chat_text_models)} | "
        f"completion_models={len(completion_models)}"
    )
    print(f"[init] chat models: {', '.join(chat_models)}")
    print(f"[init] chat-text models: {', '.join(chat_text_models)}")
    print(f"[init] completion models: {', '.join(completion_models)}")

    df = ensure_tracker(models=models, prompt_name=args.prompt, target_runs=args.target_runs)
    save_tracker(df)

    if args.operation == "status":
        print_status(df, prompt_name=args.prompt, target_runs=args.target_runs)
        return

    # Load and prepare transcript text once to avoid repeated WRDS fetches per model.
    print(f"[init] fetching benchmark transcript payloads once (n={len(benchmark_ids)})...")
    transcript_texts = capiq.get_transcripts(benchmark_ids)
    prepared_inputs: Dict[int, str] = {}
    for tid in benchmark_ids:
        if tid not in transcript_texts:
            continue
        transcript_data = json.loads(transcript_texts[tid])
        prepared_inputs[int(tid)] = prep_transcript_for_review(transcript_data)
    print(
        f"[init] prepared transcript inputs: {len(prepared_inputs)}/{len(benchmark_ids)} "
        "(missing payloads will be logged per model)."
    )

    for i, model in enumerate(models, start=1):
        mode = (
            "chat_json" if model in chat_models
            else "chat_text" if model in chat_text_models
            else "completions"
        )
        print(f"\n[{i}/{len(models)}] Processing model: {model}")
        df = run_model(
            model=model,
            mode=mode,
            prompt_name=args.prompt,
            benchmark_ids=benchmark_ids,
            target_runs=args.target_runs,
            df=df,
            max_attempts=args.max_attempts,
            retry_delay=args.retry_delay,
            workers=args.workers,
            prepared_inputs=prepared_inputs,
        )

    print("\n[done] Final tracker status:")
    df = ensure_tracker(models=models, prompt_name=args.prompt, target_runs=args.target_runs)
    print_status(df, prompt_name=args.prompt, target_runs=args.target_runs)


if __name__ == "__main__":
    main()
