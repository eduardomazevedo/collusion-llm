#!/usr/bin/env python3
"""
Generate prompt-level benchmarking outputs against human ratings.

Outputs:
- data/benchmarking/prompt_transcript_scores.csv (first-run score per prompt/transcript)
- data/benchmarking/prompt_metrics.csv (metrics from first-run scores)
- data/benchmarking/prompt_transcript_scores_avg11.csv (mean score from first 11 runs)
- data/benchmarking/prompt_metrics_avg11.csv (metrics from avg-11 scores)
- data/outputs/tables/prompt_benchmark_first_run.csv/.tex/.txt
- data/outputs/tables/prompt_benchmark_avg11.csv/.tex/.txt
"""

import argparse
import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import config
from modules.utils import extract_score_from_unstructured_response


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

SCORES_FIRST_PATH = os.path.join(config.DATA_DIR, "benchmarking", "prompt_transcript_scores.csv")
METRICS_FIRST_PATH = os.path.join(config.DATA_DIR, "benchmarking", "prompt_metrics.csv")
SCORES_AVG11_PATH = os.path.join(config.DATA_DIR, "benchmarking", "prompt_transcript_scores_avg11.csv")
METRICS_AVG11_PATH = os.path.join(config.DATA_DIR, "benchmarking", "prompt_metrics_avg11.csv")
TABLES_DIR = os.path.join(config.DATA_DIR, "outputs", "tables")

BASIC_PROMPTS = ["SimpleScoreV1", "SimpleFlagV1", "SimpleFlagScoreV1"]
REFINED_PROMPTS = [p for p in DEFAULT_PROMPTS if p not in BASIC_PROMPTS]


def load_human() -> pd.DataFrame:
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    df = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())].copy()
    df["transcriptid"] = df["transcriptid"].astype(int)
    return df


def parse_llm_response(resp: str) -> Tuple[Optional[float], Optional[bool], Optional[str], Optional[str]]:
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
        extracted = extract_score_from_unstructured_response(resp)
        if extracted is not None:
            score = float(extracted)
    return (float(score) if score is not None else None, flag, reasoning, excerpts)


def flag_to_num(value) -> float:
    """Normalize flag-like values to 0/1 numeric for averaging/comparison."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        if value in [0, 1]:
            return float(value)
        return np.nan
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"true", "1", "yes", "y"}:
            return 1.0
        if val in {"false", "0", "no", "n"}:
            return 0.0
    return np.nan


def load_llm_rows(prompts: List[str], model_name: str) -> pd.DataFrame:
    conn = sqlite3.connect(config.DATABASE_PATH)
    placeholders = ",".join("?" * len(prompts))
    q = f"""
    SELECT prompt_name, transcriptid, response, date, model_name
    FROM queries
    WHERE prompt_name IN ({placeholders}) AND model_name = ?
    ORDER BY date ASC
    """
    df = pd.read_sql_query(q, conn, params=prompts + [model_name])
    conn.close()
    if df.empty:
        return df
    df["transcriptid"] = df["transcriptid"].astype(int)
    parsed = df["response"].apply(lambda x: pd.Series(parse_llm_response(x)))
    parsed.columns = ["llm_score", "llm_flag", "llm_reasoning", "llm_excerpts"]
    return pd.concat([df, parsed], axis=1)


def first_run_scores(llm_rows: pd.DataFrame) -> pd.DataFrame:
    if llm_rows.empty:
        return pd.DataFrame(
            columns=[
                "prompt_name",
                "transcriptid",
                "llm_score",
                "llm_flag",
                "llm_reasoning",
                "llm_excerpts",
                "model_name",
                "date",
                "n_runs_used",
            ]
        )
    first = llm_rows.sort_values("date").groupby(["prompt_name", "transcriptid"], as_index=False).head(1).copy()
    first["n_runs_used"] = first["llm_score"].notna().astype(int)
    return first[
        [
            "prompt_name",
            "transcriptid",
            "llm_score",
            "llm_flag",
            "llm_reasoning",
            "llm_excerpts",
            "model_name",
            "date",
            "n_runs_used",
        ]
    ]


def avg_repeat_scores(llm_rows: pd.DataFrame, repeats: int = 11, strict: bool = True) -> pd.DataFrame:
    if llm_rows.empty:
        return pd.DataFrame(
            columns=[
                "prompt_name",
                "transcriptid",
                "llm_score",
                "llm_flag",
                "model_name",
                "date",
                "n_runs_used",
            ]
        )

    ordered = llm_rows.sort_values("date").copy()
    ordered["run_index"] = ordered.groupby(["prompt_name", "transcriptid"]).cumcount() + 1
    first_n = ordered[ordered["run_index"] <= repeats].copy()

    first_n["llm_flag_num"] = first_n["llm_flag"].apply(flag_to_num)

    agg = (
        first_n.groupby(["prompt_name", "transcriptid", "model_name"], as_index=False)
        .agg(
            llm_score=("llm_score", "mean"),
            llm_flag=("llm_flag_num", "mean"),
            date=("date", "min"),
            n_runs_used=("run_index", "count"),
        )
    )
    if strict:
        agg.loc[agg["n_runs_used"] < repeats, "llm_score"] = np.nan
        agg.loc[agg["n_runs_used"] < repeats, "llm_flag"] = np.nan
    return agg[["prompt_name", "transcriptid", "llm_score", "llm_flag", "model_name", "date", "n_runs_used"]]


def build_scores_table(prompts: List[str], llm_scores: pd.DataFrame) -> pd.DataFrame:
    human = load_human()
    records = []

    llm_cols = ["transcriptid", "llm_score", "llm_flag", "model_name", "date", "n_runs_used"]
    for optional_col in ["llm_reasoning", "llm_excerpts"]:
        if optional_col in llm_scores.columns:
            llm_cols.insert(4, optional_col)

    for prompt in prompts:
        base = human[["transcriptid", "joe_score", "acl_manual_flag"]].copy()
        base["prompt"] = prompt
        llm_sub = llm_scores[llm_scores["prompt_name"] == prompt][llm_cols] if not llm_scores.empty else pd.DataFrame(columns=llm_cols)
        merged = base.merge(llm_sub, on="transcriptid", how="left")
        merged["joe_threshold"] = config.JOE_SCORE_THRESHOLD
        merged["joe_binary"] = (merged["joe_score"] >= config.JOE_SCORE_THRESHOLD).astype("Int64")
        records.append(merged)
    return pd.concat(records, ignore_index=True)


def confusion_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
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

    df["llm_pred"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    has_score = df["llm_score"].notna()
    if has_score.any():
        df.loc[has_score, "llm_pred"] = df.loc[has_score, "llm_score"] >= config.LLM_SCORE_THRESHOLD
    has_flag = df["llm_flag"].notna()
    if has_flag.any():
        flag_num = df.loc[has_flag, "llm_flag"].apply(flag_to_num)
        flag_pred = (flag_num >= 0.5).astype("boolean")
        df.loc[has_flag & df["llm_pred"].isna(), "llm_pred"] = flag_pred

    joe = df[df["joe_score"].notna() & df["llm_pred"].notna()]
    if len(joe):
        m = confusion_metrics(joe["joe_binary"].astype(int).values, joe["llm_pred"].astype(int).values)
        out.update({f"joe_{k}": v for k, v in m.items()})
    else:
        out.update({f"joe_{k}": np.nan for k in ["tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"]})

    acl = df[df["acl_manual_flag"].notna() & df["llm_pred"].notna()]
    if len(acl):
        m = confusion_metrics(acl["acl_manual_flag"].astype(int).values, acl["llm_pred"].astype(int).values)
        out.update({f"acl_{k}": v for k, v in m.items()})
    else:
        out.update({f"acl_{k}": np.nan for k in ["tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"]})

    pooled = df[(df["acl_manual_flag"].notna()) | (df["joe_score"].notna())]
    pooled = pooled[pooled["llm_pred"].notna()]
    if len(pooled):
        labels = []
        for _, row in pooled.iterrows():
            if pd.notna(row["acl_manual_flag"]):
                labels.append(int(row["acl_manual_flag"]))
            else:
                labels.append(int(row["joe_binary"]))
        m = confusion_metrics(np.array(labels), pooled["llm_pred"].astype(int).values)
        out.update({f"pooled_{k}": v for k, v in m.items()})
    else:
        out.update({f"pooled_{k}": np.nan for k in ["tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"]})

    return out


def format_metrics_csv(df_metrics: pd.DataFrame) -> pd.DataFrame:
    df = df_metrics.copy()
    rate_cols = [c for c in df.columns if any(m in c for m in ["precision", "recall", "f1", "specificity"])]
    count_cols = [c for c in df.columns if c.endswith("_tp") or c.endswith("_fp") or c.endswith("_tn") or c.endswith("_fn")]

    for col in rate_cols:
        df[col] = df[col].apply(lambda x: round(float(x), 3) if pd.notna(x) else np.nan)
    for col in count_cols:
        df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else np.nan)
    return df


def compute_pooled_metrics_for_row(
    df_scores: pd.DataFrame,
    prompt_name: str,
    panel_name: str,
    method_label: str,
    pred_mode: str,
) -> Dict[str, float]:
    row = {
        "panel": panel_name,
        "method": method_label,
        "prompt": prompt_name,
        "pred_mode": pred_mode,
    }

    subset = df_scores[df_scores["prompt"] == prompt_name].copy()
    subset = subset[(subset["acl_manual_flag"].notna()) | (subset["joe_score"].notna())]

    if pred_mode == "score":
        subset = subset[subset["llm_score"].notna()].copy()
        subset["llm_pred"] = (subset["llm_score"] >= config.LLM_SCORE_THRESHOLD).astype(int)
    elif pred_mode == "flag":
        subset["flag_num"] = subset["llm_flag"].apply(flag_to_num)
        subset = subset[subset["flag_num"].notna()].copy()
        subset["llm_pred"] = (subset["flag_num"] >= 0.5).astype(int)
    else:
        raise ValueError(f"Unknown pred_mode: {pred_mode}")

    if subset.empty:
        for col in ["tp", "fp", "tn", "fn", "precision", "recall", "specificity", "f1"]:
            row[col] = np.nan
        return row

    labels = []
    for _, r in subset.iterrows():
        if pd.notna(r["acl_manual_flag"]):
            labels.append(int(r["acl_manual_flag"]))
        else:
            labels.append(int(r["joe_binary"]))

    metrics = confusion_metrics(np.array(labels), subset["llm_pred"].values.astype(int))
    row.update(metrics)
    return row


def build_panel_metrics(df_scores: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("Basic Variants", "SimpleScoreV1", "SimpleScoreV1", "score"),
        ("Basic Variants", "SimpleFlagV1", "SimpleFlagV1", "flag"),
        ("Basic Variants", "SimpleFlagScoreV1", "SimpleFlagScoreV1 (Score)", "score"),
        ("Basic Variants", "SimpleFlagScoreV1", "SimpleFlagScoreV1 (Flag)", "flag"),
    ]
    for prompt in REFINED_PROMPTS:
        specs.append(("Refined Variants", prompt, prompt, "score"))

    rows = [
        compute_pooled_metrics_for_row(df_scores, prompt, panel, label, mode)
        for panel, prompt, label, mode in specs
    ]
    return pd.DataFrame(rows)


def format_panel_display(df_panel: pd.DataFrame) -> pd.DataFrame:
    display = df_panel.copy()
    display = display[["panel", "method", "tp", "fp", "tn", "fn", "precision", "recall", "specificity", "f1"]]
    rename = {
        "panel": "Panel",
        "method": "Prompt",
        "tp": "TP",
        "fp": "FP",
        "tn": "TN",
        "fn": "FN",
        "precision": "Precision",
        "recall": "Recall",
        "specificity": "Specificity",
        "f1": "F1",
    }
    display = display.rename(columns=rename)

    for col in ["TP", "FP", "TN", "FN"]:
        display[col] = display[col].apply(lambda x: "" if pd.isna(x) else str(int(x)))
    for col in ["Precision", "Recall", "Specificity", "F1"]:
        display[col] = display[col].apply(lambda x: "" if pd.isna(x) else f"{float(x):.3f}")
    return display


def build_panel_latex(df_display: pd.DataFrame) -> str:
    cols = ["Prompt", "TP", "FP", "TN", "FN", "Precision", "Recall", "Specificity", "F1"]
    lines = []
    lines.append("\\begin{tabular}{lrrrrrrrr}")
    lines.append("\\toprule")
    lines.append(" & ".join(cols) + " \\\\")
    lines.append("\\midrule")

    for panel_name in ["Basic Variants", "Refined Variants"]:
        lines.append(f"\\multicolumn{{9}}{{l}}{{\\textbf{{{panel_name}}}}} \\\\")
        lines.append("\\midrule")
        panel_df = df_display[df_display["Panel"] == panel_name]
        for _, row in panel_df.iterrows():
            row_vals = [row[c] for c in cols]
            lines.append(" & ".join(row_vals) + " \\\\")
        lines.append("\\midrule")

    lines[-1] = "\\bottomrule"
    lines.append("\\end{tabular}")
    return "\n".join(lines)


def write_table_assets(df_panel_metrics: pd.DataFrame, basename: str, description: str) -> None:
    os.makedirs(TABLES_DIR, exist_ok=True)
    csv_path = os.path.join(TABLES_DIR, f"{basename}.csv")
    tex_path = os.path.join(TABLES_DIR, f"{basename}.tex")
    txt_path = os.path.join(TABLES_DIR, f"{basename}.txt")

    df_display = format_panel_display(df_panel_metrics)
    df_display.to_csv(csv_path, index=False)

    latex = build_panel_latex(df_display)
    with open(tex_path, "w") as f:
        f.write(latex)
    with open(txt_path, "w") as f:
        f.write(description + "\n")
        f.write("Generated by: src/post_query/benchmarking/prompts_benchmark.py\n")

    print(f"[table] Wrote {csv_path}")
    print(f"[table] Wrote {tex_path}")
    print(f"[table] Wrote {txt_path}")


def compute_and_save_metrics(prompts: List[str], df_scores: pd.DataFrame, metrics_path: str) -> pd.DataFrame:
    metrics = [compute_metrics_for_prompt(prompt, df_scores) for prompt in prompts]
    df_metrics = format_metrics_csv(pd.DataFrame(metrics))
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    df_metrics.to_csv(metrics_path, index=False)
    print(f"[metrics] Saved {metrics_path}")
    return df_metrics


def main():
    parser = argparse.ArgumentParser(description="Benchmark prompts against human labels.")
    parser.add_argument("--prompts", type=str, help="Comma-separated prompts (default predefined list)")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model name to evaluate")
    parser.add_argument("--avg-repeats", type=int, default=11, help="Number of earliest runs to average for avg table")
    parser.add_argument("--scores-output", type=str, default=SCORES_FIRST_PATH, help="CSV for first-run per-transcript scores")
    parser.add_argument("--metrics-output", type=str, default=METRICS_FIRST_PATH, help="CSV for first-run summary metrics")
    args = parser.parse_args()

    prompts = DEFAULT_PROMPTS if not args.prompts else [p.strip() for p in args.prompts.split(",")]
    print(f"[setup] prompts={len(prompts)}, model={args.model}, avg_repeats={args.avg_repeats}")

    llm_rows = load_llm_rows(prompts, args.model)
    print(f"[load] rows from queries={len(llm_rows)}")

    # First-run outputs
    first_scores = first_run_scores(llm_rows)
    first_df = build_scores_table(prompts, first_scores)
    os.makedirs(os.path.dirname(args.scores_output), exist_ok=True)
    first_df.to_csv(args.scores_output, index=False)
    print(f"[scores] Saved {args.scores_output}")

    first_metrics = compute_and_save_metrics(prompts, first_df, args.metrics_output)
    first_panel_metrics = build_panel_metrics(first_df)
    write_table_assets(
        first_panel_metrics,
        "prompt_benchmark_first_run",
        (
            "Panelized prompt benchmarking against human ratings using first LLM run per transcript. "
            "Basic Prompts panel includes score and/or flag variants; Refined Prompts use score variants. "
            f"Binary thresholds: Joe >= {config.JOE_SCORE_THRESHOLD}, LLM score >= {config.LLM_SCORE_THRESHOLD}; "
            "flag variants classify at flag >= 0.5."
        ),
    )

    # Avg-11 outputs (strict: requires at least 11 runs to contribute score)
    avg_scores = avg_repeat_scores(llm_rows, repeats=args.avg_repeats, strict=True)
    avg_df = build_scores_table(prompts, avg_scores)
    os.makedirs(os.path.dirname(SCORES_AVG11_PATH), exist_ok=True)
    avg_df.to_csv(SCORES_AVG11_PATH, index=False)
    print(f"[scores] Saved {SCORES_AVG11_PATH}")

    avg_metrics = compute_and_save_metrics(prompts, avg_df, METRICS_AVG11_PATH)
    avg_panel_metrics = build_panel_metrics(avg_df)
    write_table_assets(
        avg_panel_metrics,
        "prompt_benchmark_avg11",
        (
            f"Panelized prompt benchmarking using mean score/flag from first {args.avg_repeats} runs per transcript "
            "(strictly requiring all runs to be present). "
            f"Binary thresholds: Joe >= {config.JOE_SCORE_THRESHOLD}, LLM score >= {config.LLM_SCORE_THRESHOLD}; "
            "flag variants classify at mean flag >= 0.5."
        ),
    )


if __name__ == "__main__":
    main()
