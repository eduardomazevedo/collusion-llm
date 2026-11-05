"""Generate the original-versus-mean LLM score scatter used in Figure 4.

The figure combines the original LLM-flagged validation sample with the later
below-threshold score-bin repetition sample. Each transcript has an original
score and a mean across eleven identical queries. Large dots show the
conditional mean within five-point original-score bins.

Outputs:
- data/outputs/figures/scatter_scores_original_vs_mean_{1x1,16x9}.{png,pdf}
- data/outputs/figures/scatter_scores_original_vs_mean.txt
"""

#%%
import os
import sqlite3
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

import config
from modules.colors import GHIBLI_COLORS, apply_ghibli_theme, STYLE_CONFIG
from modules.utils import extract_score_from_unstructured_response

#%%
OUT_DIR = Path("data/outputs/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_NAME = "SimpleCapacityV8.1.1"
MODEL_NAME = "gpt-4o-mini"
THRESHOLD = 75
BIN_WIDTH = 5

apply_ghibli_theme()

#%%
print("Loading the original LLM-flagged validation sample...")
flagged = pd.read_csv(
    os.path.join(config.DATA_DIR, "datasets", "top_transcripts_data.csv"),
    usecols=["transcriptid", "original_score", "mean_score_ten_repeats"],
).rename(columns={"mean_score_ten_repeats": "mean_score"})
flagged = flagged.dropna(subset=["original_score", "mean_score"]).copy()
flagged["sample"] = "Original LLM-flagged sample"
print(f"Loaded {len(flagged):,} transcripts with eleven-query mean scores")

#%%
print("Loading the below-threshold score-bin repetition sample...")
sample_path = os.path.join(
    config.DATA_DIR,
    "intermediaries",
    "score_bin_repeat_sample.csv",
)
below_threshold_sample = pd.read_csv(
    sample_path,
    usecols=["transcriptid", "original_score"],
)
below_threshold_ids = below_threshold_sample["transcriptid"].astype(int).tolist()

query_frames = []
with sqlite3.connect(config.DATABASE_PATH) as conn:
    for start in range(0, len(below_threshold_ids), 900):
        batch_ids = below_threshold_ids[start:start + 900]
        placeholders = ",".join("?" for _ in batch_ids)
        query_frames.append(
            pd.read_sql_query(
                f"""
                SELECT query_id, transcriptid, response
                FROM queries
                WHERE prompt_name = ?
                  AND model_name = ?
                  AND transcriptid IN ({placeholders})
                ORDER BY query_id
                """,
                conn,
                params=[PROMPT_NAME, MODEL_NAME, *batch_ids],
            )
        )

below_threshold_queries = pd.concat(query_frames, ignore_index=True)
below_threshold_queries["score"] = below_threshold_queries["response"].apply(
    extract_score_from_unstructured_response
)

if below_threshold_queries["score"].isna().any():
    missing_count = int(below_threshold_queries["score"].isna().sum())
    raise ValueError(f"Could not parse {missing_count:,} repetition-query scores")

below_threshold_summary = (
    below_threshold_queries.sort_values("query_id")
    .groupby("transcriptid")
    .agg(
        query_count=("score", "size"),
        database_original_score=("score", "first"),
        mean_score=("score", "mean"),
    )
    .reset_index()
)

if not below_threshold_summary["query_count"].eq(11).all():
    incomplete_count = int((below_threshold_summary["query_count"] != 11).sum())
    raise ValueError(
        f"Expected eleven queries for every below-threshold transcript; "
        f"found {incomplete_count:,} incomplete transcripts"
    )

below_threshold = below_threshold_sample.merge(
    below_threshold_summary,
    on="transcriptid",
    how="left",
    validate="one_to_one",
)
if below_threshold["mean_score"].isna().any():
    missing_count = int(below_threshold["mean_score"].isna().sum())
    raise ValueError(f"Missing repetition results for {missing_count:,} transcripts")
if not np.allclose(
    below_threshold["original_score"],
    below_threshold["database_original_score"],
):
    raise ValueError("Saved original scores do not match the first database query")

below_threshold["sample"] = "Below-threshold repetition sample"
print(f"Loaded {len(below_threshold):,} transcripts with eleven queries each")

#%%
plot_data = pd.concat(
    [
        below_threshold[["transcriptid", "original_score", "mean_score", "sample"]],
        flagged[["transcriptid", "original_score", "mean_score", "sample"]],
    ],
    ignore_index=True,
)

if plot_data["transcriptid"].duplicated().any():
    duplicate_count = int(plot_data["transcriptid"].duplicated().sum())
    raise ValueError(f"Combined figure data contain {duplicate_count:,} duplicate transcripts")

plot_data["score_bin_lower"] = (
    np.floor(plot_data["original_score"] / BIN_WIDTH) * BIN_WIDTH
).clip(upper=100 - BIN_WIDTH)
conditional_means = (
    plot_data.groupby("score_bin_lower")
    .agg(
        modal_original_score=(
            "original_score",
            lambda values: values.mode().sort_values().iloc[0],
        ),
        mean_score=("mean_score", "mean"),
        score_sd=("mean_score", "std"),
        transcript_count=("transcriptid", "size"),
    )
    .reset_index()
)
conditional_means["mean_score_se"] = (
    conditional_means["score_sd"]
    / np.sqrt(conditional_means["transcript_count"])
)
conditional_means["ci_95"] = 1.96 * conditional_means["mean_score_se"]

print(f"Combined figure sample: {len(plot_data):,} transcripts")
print(
    "Below-threshold transcripts with an eleven-query mean at or above 75: "
    f"{int((below_threshold['mean_score'] >= THRESHOLD).sum()):,} "
    f"of {len(below_threshold):,}"
)
print("\nConditional means by original-score bin:")
print(
    conditional_means[
        [
            "score_bin_lower",
            "modal_original_score",
            "transcript_count",
            "mean_score",
            "ci_95",
        ]
    ].to_string(index=False, float_format=lambda value: f"{value:.2f}")
)

#%%
def create_scatter_scores():
    """Create the combined scatter in square and widescreen formats."""
    for aspect_ratio, figsize in [("1x1", (8, 8)), ("16x9", (12, 6.75))]:
        fig, ax = plt.subplots(figsize=figsize)

        rng = np.random.default_rng(42)
        horizontal_jitter = rng.uniform(-0.45, 0.45, size=len(plot_data))
        ax.scatter(
            plot_data["original_score"] + horizontal_jitter,
            plot_data["mean_score"],
            color=GHIBLI_COLORS[0],
            alpha=0.16,
            s=18,
            label=f"Transcripts (N={len(plot_data):,})",
        )

        ax.plot(
            [0, 100],
            [0, 100],
            color=STYLE_CONFIG["line_color"],
            linestyle=":",
            linewidth=1.5,
            alpha=STYLE_CONFIG["line_alpha"],
            label="45-degree line",
        )
        ax.axhline(
            THRESHOLD,
            color=STYLE_CONFIG["line_color"],
            linestyle="--",
            linewidth=2.5,
            label="Validation / flagging threshold (75)",
        )
        ax.axvline(
            THRESHOLD,
            color=STYLE_CONFIG["line_color"],
            linestyle="--",
            linewidth=2.5,
            label="_nolegend_",
        )
        ax.errorbar(
            conditional_means["modal_original_score"],
            conditional_means["mean_score"],
            yerr=conditional_means["ci_95"],
            fmt="none",
            ecolor=STYLE_CONFIG["error_color"],
            elinewidth=1.8,
            capsize=4,
            capthick=1.8,
            zorder=6,
        )
        ax.scatter(
            conditional_means["modal_original_score"],
            conditional_means["mean_score"],
            color=GHIBLI_COLORS[1],
            alpha=1,
            s=115,
            zorder=5,
            label="Conditional mean and 95% CI (5-point bins)",
        )

        ax.set_xlabel("Original LLM Score")
        ax.set_ylabel("Mean LLM Score (11 Queries)")
        ax.set_xlim(-2, 100)
        ax.set_ylim(0, 100)
        ax.set_xticks(np.arange(0, 101, 10))
        ax.set_yticks(np.arange(0, 101, 10))
        ax.legend(loc="upper left")

        plt.tight_layout()
        for file_format in ["png", "pdf"]:
            output_path = OUT_DIR / (
                f"scatter_scores_original_vs_mean_{aspect_ratio}.{file_format}"
            )
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            print(f"Saved: {output_path}")
        plt.close(fig)


#%%
if __name__ == "__main__":
    print("\nGenerating combined original-versus-mean score scatter...")
    create_scatter_scores()

    note_path = OUT_DIR / "scatter_scores_original_vs_mean.txt"
    note_path.write_text(
        "Scatter plot of original LLM scores against mean scores across eleven "
        "identical queries. The figure combines the original LLM-flagged "
        "validation sample with the later stratified sample of transcripts whose "
        "original scores were below 75. Large red dots are conditional means in "
        "five-point original-score bins, with black bars showing 95% confidence "
        "intervals. The dashed horizontal and vertical lines mark the validation "
        "and original flagging thresholds of 75, respectively. Produced by "
        "src/post_query/analysis/fig_scatter_scores.py.\n"
    )
    print(f"Saved: {note_path}")
    print("Figure generated successfully")
