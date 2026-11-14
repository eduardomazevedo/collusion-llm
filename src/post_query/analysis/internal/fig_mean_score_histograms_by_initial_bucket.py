"""Generate internal histograms of eleven-query mean scores by initial-score bucket.

The analysis covers five-point initial-score buckets from [50, 55) through
[80, 85). Below-threshold observations come from the fixed score-bin repetition
sample; observations initially scoring at least 75 come from the original
LLM-flagged validation sample.

Outputs are written to:
- data/outputs/internal/mean_score_histograms_by_initial_bucket/
"""

#%%
import os
import sqlite3
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))

import config
from modules.colors import GHIBLI_COLORS, STYLE_CONFIG, apply_ghibli_theme
from modules.utils import extract_score_from_unstructured_response

#%%
PROMPT_NAME = "SimpleCapacityV8.1.1"
MODEL_NAME = "gpt-4o-mini"
BUCKET_LOWER_BOUNDS = list(range(50, 85, 5))
HISTOGRAM_BINS = np.arange(0, 102, 2)

OUT_DIR = Path(
    "data/outputs/internal/mean_score_histograms_by_initial_bucket"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

apply_ghibli_theme()

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
below_threshold_sample = below_threshold_sample[
    below_threshold_sample["original_score"].ge(50)
    & below_threshold_sample["original_score"].lt(75)
].copy()

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

missing_scores = int(below_threshold_queries["score"].isna().sum())
if missing_scores:
    raise ValueError(f"Could not parse {missing_scores:,} repetition-query scores")

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

incomplete = below_threshold_summary["query_count"].ne(11)
if incomplete.any():
    raise ValueError(
        "Expected exactly eleven queries for every below-threshold transcript; "
        f"found {int(incomplete.sum()):,} incomplete or over-complete transcripts"
    )

below_threshold = below_threshold_sample.merge(
    below_threshold_summary,
    on="transcriptid",
    how="left",
    validate="one_to_one",
)
if below_threshold["mean_score"].isna().any():
    missing = int(below_threshold["mean_score"].isna().sum())
    raise ValueError(f"Missing repetition results for {missing:,} transcripts")
if not np.allclose(
    below_threshold["original_score"],
    below_threshold["database_original_score"],
):
    raise ValueError("Saved original scores do not match the first database query")

below_threshold = below_threshold[
    ["transcriptid", "original_score", "mean_score"]
].copy()
print(f"Loaded {len(below_threshold):,} transcripts from initial scores [50, 75)")

#%%
print("Loading the original LLM-flagged validation sample...")
flagged_path = os.path.join(
    config.DATA_DIR,
    "datasets",
    "top_transcripts_data.csv",
)
flagged = pd.read_csv(
    flagged_path,
    usecols=[
        "transcriptid",
        "original_score",
        "mean_score_ten_repeats",
        "n_queries",
    ],
).rename(columns={"mean_score_ten_repeats": "mean_score"})
flagged = flagged[
    flagged["original_score"].ge(75)
    & flagged["original_score"].lt(85)
].copy()

incomplete_flagged = flagged["n_queries"].lt(11) | flagged["mean_score"].isna()
if incomplete_flagged.any():
    print(
        f"Excluding {int(incomplete_flagged.sum()):,} flagged transcripts without "
        "complete eleven-query results"
    )
flagged = flagged[~incomplete_flagged].copy()
flagged = flagged[["transcriptid", "original_score", "mean_score"]].copy()
print(f"Loaded {len(flagged):,} transcripts from initial scores [75, 85)")

#%%
plot_data = pd.concat([below_threshold, flagged], ignore_index=True)
if plot_data["transcriptid"].duplicated().any():
    duplicates = int(plot_data["transcriptid"].duplicated().sum())
    raise ValueError(f"Combined data contain {duplicates:,} duplicate transcripts")

plot_data["bucket_lower"] = (
    np.floor(plot_data["original_score"] / 5) * 5
).astype(int)
plot_data = plot_data[plot_data["bucket_lower"].isin(BUCKET_LOWER_BOUNDS)].copy()

bucket_data = {
    lower: plot_data.loc[
        plot_data["bucket_lower"].eq(lower), "mean_score"
    ].to_numpy()
    for lower in BUCKET_LOWER_BOUNDS
}
empty_buckets = [lower for lower, scores in bucket_data.items() if len(scores) == 0]
if empty_buckets:
    raise ValueError(f"No observations found for bucket lower bounds: {empty_buckets}")

summary = pd.DataFrame(
    [
        {
            "initial_score_bucket": f"[{lower}, {lower + 5})",
            "n": len(scores),
            "mean_of_eleven_query_mean": scores.mean(),
            "median_of_eleven_query_mean": np.median(scores),
        }
        for lower, scores in bucket_data.items()
    ]
)
print("\nRequested bucket summary:")
print(summary.to_string(index=False, float_format=lambda value: f"{value:.2f}"))

percentage_heights = []
for scores in bucket_data.values():
    counts, _ = np.histogram(scores, bins=HISTOGRAM_BINS)
    percentage_heights.extend(counts / len(scores) * 100)
common_y_max = max(percentage_heights) * 1.15

#%%
def draw_histogram(ax, scores, lower):
    """Draw one percentage histogram with a conditional-mean reference line."""
    weights = np.full(len(scores), 100 / len(scores))
    ax.hist(
        scores,
        bins=HISTOGRAM_BINS,
        weights=weights,
        color=GHIBLI_COLORS[0],
        edgecolor=STYLE_CONFIG["edge_color"],
        linewidth=STYLE_CONFIG["edge_width"],
    )
    conditional_mean = scores.mean()
    ax.axvline(
        conditional_mean,
        color=STYLE_CONFIG["line_color"],
        linestyle="--",
        linewidth=1.5,
        alpha=STYLE_CONFIG["line_alpha"],
    )
    ax.text(
        0.985,
        0.90,
        f"Initial score [{lower}, {lower + 5})   N={len(scores):,}   Mean={conditional_mean:.1f}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        color=STYLE_CONFIG["text_color"],
        fontsize=9,
    )
    ax.set_xlim(0, 100)
    ax.set_ylim(0, common_y_max)
    ax.set_xticks(np.arange(0, 101, 10))


#%%
print("\nGenerating individual histograms...")
for lower, scores in bucket_data.items():
    for aspect_ratio, figsize in [("1x1", (8, 8)), ("16x9", (12, 6.75))]:
        fig, ax = plt.subplots(figsize=figsize)
        draw_histogram(ax, scores, lower)
        ax.set_xlabel("Mean LLM Score (11 Queries)")
        ax.set_ylabel("Percent of Transcripts")
        plt.tight_layout()

        for file_format in ["png", "pdf"]:
            output_path = OUT_DIR / (
                f"mean_score_initial_{lower}_{lower + 5}_{aspect_ratio}."
                f"{file_format}"
            )
            fig.savefig(output_path, dpi=300, bbox_inches="tight")
            print(f"Saved: {output_path}")
        plt.close(fig)

#%%
print("\nGenerating the full-page stacked-panel figure...")
fig, axes = plt.subplots(
    len(BUCKET_LOWER_BOUNDS),
    1,
    figsize=(8.5, 11),
    sharex=True,
    sharey=True,
)
for ax, lower in zip(axes, BUCKET_LOWER_BOUNDS):
    draw_histogram(ax, bucket_data[lower], lower)

axes[-1].set_xlabel("Mean LLM Score (11 Queries)")
fig.supylabel("Percent of Transcripts", x=0.015)
fig.subplots_adjust(left=0.10, right=0.98, top=0.99, bottom=0.07, hspace=0.28)

for file_format in ["png", "pdf"]:
    output_path = OUT_DIR / (
        f"mean_score_histograms_all_initial_buckets_portrait.{file_format}"
    )
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved: {output_path}")
plt.close(fig)

#%%
note_path = OUT_DIR / "mean_score_histograms_by_initial_bucket.txt"
note_path.write_text(
    "Histograms of transcript-level mean LLM collusive scores across eleven "
    "identical queries, conditional on five-point initial-score buckets from "
    "[50, 55) through [80, 85). Bars report the percentage of transcripts in "
    "two-point mean-score intervals; dashed black lines mark bucket-specific "
    "means. Buckets below 75 use the fixed score-bin repetition sample, while "
    "buckets at or above 75 use the original LLM-flagged validation sample. "
    "Produced by src/post_query/analysis/internal/"
    "fig_mean_score_histograms_by_initial_bucket.py.\n"
)
print(f"Saved: {note_path}")
print("Internal score-bucket histograms generated successfully")
