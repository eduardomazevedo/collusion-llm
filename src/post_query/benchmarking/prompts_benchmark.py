#!/usr/bin/env python3
"""
Generate per-transcript benchmarking data and summary metrics for selected prompts.

Outputs:
- data/benchmarking/prompt_transcript_scores.csv: one row per prompt/transcript in the
  benchmarking set (Joe or ACL labeled), with human labels, thresholds, and parsed LLM fields.
- data/benchmarking/prompt_metrics.csv: TP/FP/TN/FN, precision, recall, F1, specificity for
  Joe-only, ACL-only, and pooled labels; plus MAE of LLM score vs Joe score on the Joe subsample.
"""

import argparse
import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple
import sys

import numpy as np
import pandas as pd

import config
from modules.utils import extract_score_from_unstructured_response
from modules.colors import GHIBLI_COLORS, apply_ghibli_theme, STYLE_CONFIG

# Default prompts to benchmark
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

SCORES_PATH = os.path.join(config.DATA_DIR, "benchmarking", "prompt_transcript_scores.csv")
METRICS_PATH = os.path.join(config.DATA_DIR, "benchmarking", "prompt_metrics.csv")
FIGURES_DIR = os.path.join(config.DATA_DIR, "outputs", "figures")


def load_human() -> pd.DataFrame:
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    df = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())].copy()
    df["transcriptid"] = df["transcriptid"].astype(int)
    return df


def parse_llm_response(resp: str) -> Tuple[Optional[float], Optional[bool], Optional[str], Optional[str]]:
    """
    Return (score, flag, reasoning, excerpts_str) from an LLM response string.
    """
    score = None
    flag = None
    reasoning = None
    excerpts = None
    if not resp:
        return score, flag, reasoning, excerpts
    try:
        data = json.loads(resp)
        if isinstance(data, dict):
            score = data.get("score")
            # Normalize flag field names
            for key in ["signal", "indicator", "overall_indicator"]:
                if key in data:
                    flag = data[key]
                    break
            reasoning = data.get("reasoning")
            ex = data.get("excerpts")
            if isinstance(ex, list):
                excerpts = "; ".join(map(str, ex))
    except Exception:
        pass
    if score is None:
        s = extract_score_from_unstructured_response(resp)
        if s is not None:
            score = float(s)
    return (float(score) if score is not None else None, flag, reasoning, excerpts)


def get_latest_llm(prompts: List[str]) -> pd.DataFrame:
    """
    Get the latest response per prompt/transcript from queries for the selected prompts.
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    placeholders = ",".join("?" * len(prompts))
    q = f"""
    SELECT prompt_name, transcriptid, response, date, model_name
    FROM queries
    WHERE prompt_name IN ({placeholders})
    ORDER BY date DESC
    """
    df = pd.read_sql_query(q, conn, params=prompts)
    conn.close()
    if df.empty:
        return df
    df["transcriptid"] = df["transcriptid"].astype(int)
    # Keep earliest per prompt/transcript (aligns with manuscript counts that use first-run scores)
    df = df.sort_values("date").groupby(["prompt_name", "transcriptid"]).head(1)
    df[["llm_score", "llm_flag", "llm_reasoning", "llm_excerpts"]] = df["response"].apply(
        lambda x: pd.Series(parse_llm_response(x))
    )
    return df


def confusion_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    n = len(y_true)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
    }


def compute_metrics_for_prompt(prompt: str, df_scores: pd.DataFrame) -> Dict[str, float]:
    out: Dict[str, float] = {"prompt": prompt}
    df = df_scores[df_scores["prompt"] == prompt].copy()

    # Build a binary prediction: prefer numeric score threshold, else fall back to explicit flag
    df["llm_pred"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    has_score = df["llm_score"].notna()
    if has_score.any():
        df.loc[has_score, "llm_pred"] = df.loc[has_score, "llm_score"] >= config.LLM_SCORE_THRESHOLD
    has_flag = df["llm_flag"].notna()
    if has_flag.any():
        flag_series = df.loc[has_flag, "llm_flag"]
        if flag_series.dtype == object:
            flag_series = flag_series.map(lambda x: str(x).strip().lower() == "true" if pd.notna(x) else pd.NA)
        df.loc[has_flag & df["llm_pred"].isna(), "llm_pred"] = flag_series.astype("boolean")

    # Joe metrics
    joe = df[df["joe_score"].notna() & df["llm_pred"].notna()]
    if len(joe):
        pred = joe["llm_pred"].astype(int).values
        true = joe["joe_binary"].astype(int).values
        m = confusion_metrics(true, pred)
        out.update({f"joe_{k}": v for k, v in m.items()})
    else:
        out.update({f"joe_{k}": np.nan for k in ["n", "tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"]})
    # MAE only applies when a numeric score exists
    joe_mae = df[df["joe_score"].notna() & df["llm_score"].notna()]
    out["joe_mae"] = float(np.abs(joe_mae["llm_score"] - joe_mae["joe_score"]).mean()) if len(joe_mae) else np.nan

    # ACL metrics
    acl = df[df["acl_manual_flag"].notna() & df["llm_pred"].notna()]
    if len(acl):
        pred = acl["llm_pred"].astype(int).values
        true = acl["acl_manual_flag"].astype(int).values
        m = confusion_metrics(true, pred)
        out.update({f"acl_{k}": v for k, v in m.items()})
    else:
        out.update({f"acl_{k}": np.nan for k in ["n", "tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"]})

    # Pooled metrics (ACL if available, else Joe binary)
    pooled = df[(df["acl_manual_flag"].notna()) | (df["joe_score"].notna())]
    pooled = pooled[pooled["llm_pred"].notna()]
    if len(pooled):
        labels = []
        for _, r in pooled.iterrows():
            if pd.notna(r["acl_manual_flag"]):
                labels.append(int(r["acl_manual_flag"]))
            else:
                labels.append(int(r["joe_binary"]))
        pred = pooled["llm_pred"].astype(int).values
        m = confusion_metrics(np.array(labels), pred)
        out.update({f"pooled_{k}": v for k, v in m.items()})
    else:
        out.update({f"pooled_{k}": np.nan for k in ["n", "tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"]})

    return out


def build_scores_table(prompts: List[str]) -> pd.DataFrame:
    human = load_human()
    llm = get_latest_llm(prompts)
    records = []
    for prompt in prompts:
        base = human[["transcriptid", "joe_score", "acl_manual_flag"]].copy()
        base["prompt"] = prompt
        # Merge in LLM fields (may be missing)
        llm_sub = llm[llm["prompt_name"] == prompt][
            ["transcriptid", "llm_score", "llm_flag", "llm_reasoning", "llm_excerpts", "model_name", "date"]
        ]
        merged = base.merge(llm_sub, on="transcriptid", how="left")
        merged["joe_threshold"] = config.JOE_SCORE_THRESHOLD
        merged["joe_binary"] = (merged["joe_score"] >= config.JOE_SCORE_THRESHOLD).astype("Int64")
        records.append(merged)
    df_scores = pd.concat(records, ignore_index=True)
    return df_scores


def generate_scatterplots(df_scores: pd.DataFrame, prompts: List[str]) -> None:
    """Generate scatter plots of LLM score vs Joe score for each prompt."""
    import matplotlib.pyplot as plt
    
    # Apply Ghibli theme
    apply_ghibli_theme()

    os.makedirs(FIGURES_DIR, exist_ok=True)
    for prompt in prompts:
        data = df_scores[(df_scores["prompt"] == prompt) & df_scores["joe_score"].notna() & df_scores["llm_score"].notna()]
        if data.empty:
            print(f"[scatter] Prompt {prompt}: no overlapping Joe/LLM scores; skipping.")
            continue
        for size_label, figsize in [("1x1", (6, 6)), ("16x9", (16, 9))]:
            plt.figure(figsize=figsize)
            plt.scatter(data["joe_score"], data["llm_score"], alpha=0.6, c=GHIBLI_COLORS[1])
            plt.plot([0, 100], [0, 100], color=STYLE_CONFIG["line_color"], linestyle="--", label="45° line")
            plt.xlim(0, 100)
            plt.ylim(0, 100)
            plt.xlabel("Joe score")
            plt.ylabel("LLM score")
            plt.title(f"{prompt}: LLM vs Joe")
            plt.legend()
            base = f"llm_vs_joe_{prompt}_{size_label}"
            pdf_path = os.path.join(FIGURES_DIR, f"{base}.pdf")
            png_path = os.path.join(FIGURES_DIR, f"{base}.png")
            plt.savefig(pdf_path, bbox_inches="tight")
            plt.savefig(png_path, bbox_inches="tight", dpi=300)
            plt.close()
        # Note file (one per prompt)
        note_path = os.path.join(FIGURES_DIR, f"llm_vs_joe_{prompt}.txt")
        with open(note_path, "w") as f:
            f.write(f"Scatter of LLM score vs Joe score for prompt {prompt} on benchmarking transcripts.\n")
            f.write("Produced by prompts_benchmark.py\n")


def main():
    parser = argparse.ArgumentParser(description="Benchmark prompts against human labels.")
    parser.add_argument("--prompts", type=str, help="Comma-separated prompts (default predefined list)")
    parser.add_argument("--scores-output", type=str, default=SCORES_PATH, help="CSV for per-transcript scores")
    parser.add_argument("--metrics-output", type=str, default=METRICS_PATH, help="CSV for summary metrics")
    parser.add_argument("--no-figures", action="store_true", help="Skip generating scatterplot figures")
    args = parser.parse_args()

    prompts = DEFAULT_PROMPTS if not args.prompts else [p.strip() for p in args.prompts.split(",")]

    print("Building per-transcript scores table...")
    df_scores = build_scores_table(prompts)
    os.makedirs(os.path.dirname(args.scores_output), exist_ok=True)
    df_scores.to_csv(args.scores_output, index=False)
    print(f"Saved per-transcript scores to {args.scores_output}")

    print("Computing metrics...")
    metrics = [compute_metrics_for_prompt(p, df_scores) for p in prompts]
    df_metrics = pd.DataFrame(metrics)
    # Format numeric columns: round to 2 decimals if fractional, keep integers as-is
    def _fmt_num(val):
        if pd.isna(val):
            return np.nan
        try:
            fval = float(val)
        except Exception:
            return val
        if fval.is_integer():
            return int(fval)
        return round(fval, 2)

    for col in df_metrics.select_dtypes(include=[np.number]).columns:
        df_metrics[col] = df_metrics[col].apply(_fmt_num)

    df_metrics.to_csv(args.metrics_output, index=False)
    print(f"Saved metrics to {args.metrics_output}")

    if not args.no_figures:
        print("Generating scatter plots...")
        generate_scatterplots(df_scores, prompts)


if __name__ == "__main__":
    main()
