#!/usr/bin/env python3
"""
Generate model-level benchmarking outputs against human ratings.

Rows: models (panelized by model family)
Metrics: pooled confusion-matrix metrics against benchmark human labels

Prompt mapping:
- Modern structured models: SimpleCapacityV8.1.1
- Older/legacy models: SimpleCapacityV8.1.1_JSON

Outputs:
- data/benchmarking/model_transcript_scores.csv
- data/benchmarking/model_metrics.csv
- data/outputs/tables/model_benchmark_first_run.csv/.tex/.txt
"""

import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import config
from modules.utils import extract_score_from_unstructured_response

DEFAULT_PROMPT_MODERN = "SimpleCapacityV8.1.1"
DEFAULT_PROMPT_LEGACY = "SimpleCapacityV8.1.1_JSON"
REASONING_ONLY_MODELS = ["gpt-5.1", "gpt-5.2", "gpt-5.3-chat-latest"]
EXCLUDED_OLD_MODELS = {"gpt-4", "gpt-3.5-turbo-instruct"}
TRIMMED_OLD_MODELS = {"gpt-3.5-turbo", "davinci-002", "babbage-002"}
SCORES_PATH = os.path.join(config.DATA_DIR, "benchmarking", "model_transcript_scores.csv")
METRICS_PATH = os.path.join(config.DATA_DIR, "benchmarking", "model_metrics.csv")
TABLES_DIR = os.path.join(config.DATA_DIR, "outputs", "tables")


def load_human() -> pd.DataFrame:
    df = pd.read_csv(config.HUMAN_RATINGS_PATH)
    df = df[(df["joe_score"].notna()) | (df["acl_manual_flag"].notna())].copy()
    df["transcriptid"] = df["transcriptid"].astype(int)
    df["joe_binary"] = (df["joe_score"] >= config.JOE_SCORE_THRESHOLD).astype("Int64")
    return df


def parse_llm_score(response: str) -> Optional[float]:
    if not response:
        return None
    score = None
    try:
        data = json.loads(response)
        if isinstance(data, dict):
            score = data.get("score")
    except Exception:
        pass
    if score is None:
        extracted = extract_score_from_unstructured_response(response)
        if extracted is not None:
            score = extracted
    if score is None:
        return None
    try:
        return float(score)
    except Exception:
        return None


def load_model_list_from_config(provider: str = "openai") -> List[str]:
    llm_cfg_path = os.path.join(config.ROOT, "assets", "llm_config.json")
    with open(llm_cfg_path, "r") as f:
        cfg = json.load(f)
    model_cfg = cfg.get("providers", {}).get(provider, {}).get("models", {})
    return sorted(
        [
            model_name
            for model_name, props in model_cfg.items()
            if props.get("supports_structured_output", False)
        ]
    )


def build_model_specs(modern_models: List[str]) -> List[Dict[str, str]]:
    specs = []
    for m in modern_models:
        if m in REASONING_ONLY_MODELS:
            continue
        specs.append(
            {
                "model": m,
                "panel": "Modern Structured Models",
                "prompt_name": DEFAULT_PROMPT_MODERN,
            }
        )
    for m in REASONING_ONLY_MODELS:
        if m not in modern_models:
            continue
        specs.append(
            {
                "model": m,
                "panel": "Reasoning-Only GPT-5.x Models",
                "prompt_name": DEFAULT_PROMPT_MODERN,
            }
        )
    for m in ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]:
        if m in EXCLUDED_OLD_MODELS:
            continue
        specs.append(
            {
                "model": m,
                "panel": "Older Chat Models (JSON Prompt)",
                "prompt_name": DEFAULT_PROMPT_LEGACY,
            }
        )
    # Legacy completion models intentionally excluded from appendix table.
    return specs


def load_llm_rows(model_specs: List[Dict[str, str]], benchmark_ids: List[int]) -> pd.DataFrame:
    if not model_specs or not benchmark_ids:
        return pd.DataFrame(columns=["model_name", "panel", "prompt_name", "transcriptid", "date", "response", "llm_score"])

    conn = sqlite3.connect(config.DATABASE_PATH)
    all_rows = []
    ph_ids = ",".join("?" * len(benchmark_ids))
    for spec in model_specs:
        q = f"""
        SELECT model_name, transcriptid, date, response
        FROM queries
        WHERE prompt_name = ?
          AND model_name = ?
          AND transcriptid IN ({ph_ids})
        ORDER BY transcriptid ASC, date ASC
        """
        rows = pd.read_sql_query(q, conn, params=[spec["prompt_name"], spec["model"], *benchmark_ids])
        if rows.empty:
            continue
        rows["panel"] = spec["panel"]
        rows["prompt_name"] = spec["prompt_name"]
        all_rows.append(rows)
    conn.close()

    if not all_rows:
        return pd.DataFrame(columns=["model_name", "panel", "prompt_name", "transcriptid", "date", "response", "llm_score"])

    df = pd.concat(all_rows, ignore_index=True)
    df["transcriptid"] = df["transcriptid"].astype(int)
    df["llm_score"] = df["response"].apply(parse_llm_score)
    return df


def first_usable_scores(llm_rows: pd.DataFrame) -> pd.DataFrame:
    if llm_rows.empty:
        return pd.DataFrame(
            columns=["model_name", "panel", "prompt_name", "transcriptid", "date", "llm_score", "has_score", "n_rows_for_pair"]
        )

    # Keep earliest row with a parseable score for each model-transcript pair.
    valid = llm_rows[llm_rows["llm_score"].notna()].copy()
    first_valid = (
        valid.sort_values("date")
        .groupby(["model_name", "panel", "prompt_name", "transcriptid"], as_index=False)
        .head(1)
        .copy()
    )
    first_valid["has_score"] = 1

    counts = (
        llm_rows.groupby(["model_name", "panel", "prompt_name", "transcriptid"], as_index=False)
        .size()
        .rename(columns={"size": "n_rows_for_pair"})
    )
    out = first_valid.merge(
        counts,
        on=["model_name", "panel", "prompt_name", "transcriptid"],
        how="left",
    )
    return out[
        [
            "model_name",
            "panel",
            "prompt_name",
            "transcriptid",
            "date",
            "llm_score",
            "has_score",
            "n_rows_for_pair",
        ]
    ]


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
        "specificity": specificity,
        "f1": f1,
    }


def compute_metrics(human: pd.DataFrame, scores: pd.DataFrame, model_specs: List[Dict[str, str]]) -> pd.DataFrame:
    rows = []
    benchmark_n = len(human)

    for spec in model_specs:
        model = spec["model"]
        panel = spec["panel"]
        prompt_name = spec["prompt_name"]
        model_scores = scores[scores["model_name"] == model][["transcriptid", "llm_score"]].copy()
        merged = human[["transcriptid", "joe_score", "acl_manual_flag", "joe_binary"]].merge(
            model_scores, on="transcriptid", how="left"
        )
        merged = merged[merged["llm_score"].notna()].copy()
        n_used = len(merged)

        if n_used == 0:
            rows.append(
                {
                    "panel": panel,
                    "model": model,
                    "prompt_name": prompt_name,
                    "n_used": 0,
                    "n_total": benchmark_n,
                    "coverage": 0.0,
                    "tp": np.nan,
                    "fp": np.nan,
                    "tn": np.nan,
                    "fn": np.nan,
                    "precision": np.nan,
                    "recall": np.nan,
                    "specificity": np.nan,
                    "f1": np.nan,
                }
            )
            continue

        labels = []
        for _, r in merged.iterrows():
            if pd.notna(r["acl_manual_flag"]):
                labels.append(int(r["acl_manual_flag"]))
            else:
                labels.append(int(r["joe_binary"]))
        y_true = np.array(labels)
        y_pred = (merged["llm_score"] >= config.LLM_SCORE_THRESHOLD).astype(int).values
        m = confusion_metrics(y_true, y_pred)

        row = {
            "panel": panel,
            "model": model,
            "prompt_name": prompt_name,
            "n_used": int(n_used),
            "n_total": int(benchmark_n),
            "coverage": float(n_used / benchmark_n) if benchmark_n else np.nan,
        }
        row.update(m)
        rows.append(row)

    return pd.DataFrame(rows)


def write_outputs(scores: pd.DataFrame, metrics: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(SCORES_PATH), exist_ok=True)
    scores.to_csv(SCORES_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    print(f"[scores] Wrote {SCORES_PATH}")
    print(f"[metrics] Wrote {METRICS_PATH}")


def to_table_display(metrics: pd.DataFrame) -> pd.DataFrame:
    df = metrics.copy()
    df["model"] = df["model"].apply(
        lambda m: f"{m}(*)" if m in TRIMMED_OLD_MODELS else m
    )
    df = df[
        ["panel", "model", "tp", "fp", "tn", "fn", "precision", "recall", "specificity", "f1"]
    ].rename(
        columns={
            "panel": "Panel",
            "model": "Model",
            "tp": "TP",
            "fp": "FP",
            "tn": "TN",
            "fn": "FN",
            "precision": "Precision",
            "recall": "Recall",
            "specificity": "Specificity",
            "f1": "F1",
        }
    )

    for col in ["TP", "FP", "TN", "FN"]:
        df[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(int(x)))
    for col in ["Precision", "Recall", "Specificity", "F1"]:
        df[col] = df[col].apply(lambda x: "" if pd.isna(x) else f"{float(x):.3f}")
    return df


def write_table_assets(metrics: pd.DataFrame) -> None:
    os.makedirs(TABLES_DIR, exist_ok=True)
    base = "model_benchmark_first_run"
    csv_path = os.path.join(TABLES_DIR, f"{base}.csv")
    tex_path = os.path.join(TABLES_DIR, f"{base}.tex")
    txt_path = os.path.join(TABLES_DIR, f"{base}.txt")

    display = to_table_display(metrics)
    display.to_csv(csv_path, index=False)

    cols = ["Model", "TP", "FP", "TN", "FN", "Precision", "Recall", "Specificity", "F1"]
    lines = []
    lines.append("\\begin{tabular}{lrrrrrrrr}")
    lines.append("\\toprule")
    lines.append(" & ".join(cols) + " \\\\")
    lines.append("\\midrule")
    panel_order = [
        "Modern Structured Models",
        "Reasoning-Only GPT-5.x Models",
        "Older Chat Models (JSON Prompt)",
        "Legacy Completion Models (JSON Prompt)",
    ]
    for panel in panel_order:
        panel_df = display[display["Panel"] == panel]
        if panel_df.empty:
            continue
        lines.append(f"\\multicolumn{{9}}{{l}}{{\\textbf{{{panel}}}}} \\\\")
        lines.append("\\midrule")
        for _, row in panel_df.iterrows():
            lines.append(" & ".join([str(row[c]) for c in cols]) + " \\\\")
        lines.append("\\midrule")

    if lines[-1] == "\\midrule":
        lines[-1] = "\\bottomrule"
    else:
        lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    with open(tex_path, "w") as f:
        f.write("\n".join(lines))

    with open(txt_path, "w") as f:
        f.write(
            "Model-level benchmark metrics against pooled human labels using "
            "model-family-specific prompt mapping and the first usable score per "
            "model-transcript pair.\n"
        )
        f.write("Generated by: src/post_query/benchmarking/models_benchmark.py\n")

    print(f"[table] Wrote {csv_path}")
    print(f"[table] Wrote {tex_path}")
    print(f"[table] Wrote {txt_path}")


def main() -> None:
    human = load_human()
    benchmark_ids = human["transcriptid"].astype(int).tolist()

    modern_models = load_model_list_from_config()
    model_specs = build_model_specs(modern_models)
    models = [s["model"] for s in model_specs]
    print(
        f"[setup] benchmark_n={len(benchmark_ids)} | models={len(models)} "
        f"({', '.join(models)})"
    )

    llm_rows = load_llm_rows(model_specs, benchmark_ids)
    print(f"[load] rows from queries={len(llm_rows)}")

    scores = first_usable_scores(llm_rows)
    metrics = compute_metrics(human, scores, model_specs)

    write_outputs(scores, metrics)
    write_table_assets(metrics)


if __name__ == "__main__":
    main()
