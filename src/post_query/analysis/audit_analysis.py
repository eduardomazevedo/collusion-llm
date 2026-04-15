"""
Human audit analysis for manuscript audit sections.

Outputs:
- data/outputs/tables/human_audit_performance_bins.{csv,tex,txt}
- data/outputs/tables/human_audit_score_bins_10.{csv,tex,txt}
- data/outputs/figures/human_audit_score_histogram_10bins_{1x1,16x9}.{png,pdf}
- data/yaml/audit.yaml
"""

#%%
import os
import sys
import yaml
import unicodedata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(ROOT_DIR)

import config
from modules.colors import apply_ghibli_theme, GHIBLI_COLORS, STYLE_CONFIG

#%%
# Apply Ghibli theme
apply_ghibli_theme()

#%%
# Paths
TABLE_DIR = os.path.join(config.DATA_DIR, "outputs", "tables")
FIGURE_DIR = os.path.join(config.DATA_DIR, "outputs", "figures")
YAML_PATH = os.path.join(config.DATA_DIR, "yaml", "audit.yaml")

os.makedirs(TABLE_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(YAML_PATH), exist_ok=True)

#%%
# Load audit file
print(f"Loading audit file: {config.HUMAN_AUDIT_PATH}")
audit_df = pd.read_excel(config.HUMAN_AUDIT_PATH)

if "T/F/N" not in audit_df.columns:
    raise ValueError("Expected 'T/F/N' column not found in audit file.")

audit_df["audit_label"] = (
    audit_df["T/F/N"].astype(str).str.strip().str.upper()
)
audit_df = audit_df[audit_df["audit_label"].isin(["T", "F", "N"])].copy()

label_counts = audit_df["audit_label"].value_counts().to_dict()
print(f"Audit label counts: {label_counts}")

audit_tf = audit_df[audit_df["audit_label"].isin(["T", "F"])].copy()

score_col = None
if "mean_score" in audit_tf.columns:
    score_col = "mean_score"
elif "original_score" in audit_tf.columns:
    score_col = "original_score"
else:
    raise ValueError("Expected 'mean_score' or 'original_score' in audit file.")

print(f"Using score column: {score_col}")

#%%
# Summary stats
sample_count = int(len(audit_tf))
true_count = int((audit_tf["audit_label"] == "T").sum())
false_count = int((audit_tf["audit_label"] == "F").sum())
true_rate_pct = true_count / sample_count * 100 if sample_count else 0.0

score_min = float(audit_tf[score_col].min())
score_max = float(audit_tf[score_col].max())
score_mean = float(audit_tf[score_col].mean())
score_sd = float(audit_tf[score_col].std())

# Corpus share
main_dataset_path = os.path.join(config.DATA_DIR, "datasets", "main_analysis_dataset.feather")
if os.path.exists(main_dataset_path):
    main_df = pd.read_feather(main_dataset_path)
    total_transcripts = int(len(main_df))
    sample_rate_pct = sample_count / total_transcripts * 100 if total_transcripts else 0.0
    print(f"Main dataset transcripts: {total_transcripts:,}")
else:
    total_transcripts = None
    sample_rate_pct = None
    print("Main dataset not found; skipping audit share of corpus.")

#%%
def format_bin_label(start, end, right_inclusive, decimals=None):
    if decimals is None:
        if np.isclose(start, round(start)) and np.isclose(end, round(end)):
            decimals = 0
        else:
            decimals = 2
    fmt = f"{{:.{decimals}f}}" if decimals > 0 else "{:.0f}"
    left = fmt.format(start)
    right = fmt.format(end)
    closing = "]" if right_inclusive else ")"
    # Wrap in braces so LaTeX doesn't treat the leading "[" as a line-break option.
    return f"{{[{left}, {right}{closing}}}"


def make_histogram_table(scores, bins):
    counts, bin_edges = np.histogram(scores, bins=bins)
    if np.allclose(bin_edges, np.round(bin_edges)):
        decimals = 0
    else:
        decimals = 2
    labels = []
    for i in range(len(counts)):
        labels.append(format_bin_label(
            bin_edges[i],
            bin_edges[i + 1],
            right_inclusive=(i == len(counts) - 1),
            decimals=decimals
        ))
    table_df = pd.DataFrame({
        "bin": labels,
        "count": counts.astype(int)
    })
    return table_df


def save_figure(name, description, fig=None):
    fig = fig or plt.gcf()
    for aspect, size in {"1x1": (6, 6), "16x9": (12, 6.75)}.items():
        fig.set_size_inches(*size)
        base_path = os.path.join(FIGURE_DIR, f"{name}_{aspect}")
        fig.savefig(f"{base_path}.png", dpi=300)
        fig.savefig(f"{base_path}.pdf")
    with open(os.path.join(FIGURE_DIR, f"{name}.txt"), "w") as f:
        f.write(description)
    plt.close(fig)


def save_table(df, name, description, latex_column_rename=None, escape=True):
    csv_path = os.path.join(TABLE_DIR, f"{name}.csv")
    tex_path = os.path.join(TABLE_DIR, f"{name}.tex")
    df.to_csv(csv_path, index=False)
    latex_df = df.copy()
    if latex_column_rename:
        latex_df = latex_df.rename(columns=latex_column_rename)
    latex_df.to_latex(
        tex_path,
        index=False,
        escape=escape
    )
    with open(os.path.join(TABLE_DIR, f"{name}.txt"), "w") as f:
        f.write(description)


def format_range(low, high):
    return f"{low:.2f}-{high:.2f}"


def bin_stats(df, label):
    count = int(len(df))
    true_pos = int((df["audit_label"] == "T").sum())
    false_pos = int((df["audit_label"] == "F").sum())
    rate = true_pos / count * 100 if count else 0.0
    min_score = float(df[score_col].min()) if count else np.nan
    max_score = float(df[score_col].max()) if count else np.nan
    return {
        "label": label,
        "count": count,
        "true_pos": true_pos,
        "false_pos": false_pos,
        "rate": rate,
        "min_score": min_score,
        "max_score": max_score,
    }


def split_by_target_counts(df, top_count, middle_count, bottom_count):
    total = len(df)
    target_total = top_count + middle_count + bottom_count
    if total != target_total:
        print(
            "WARNING: Audit sample size does not match target bins "
            f"({total} != {target_total}). Adjusting bottom bin to fit."
        )
        bottom_count = total - top_count - middle_count
        if bottom_count < 0:
            raise ValueError("Target counts exceed audit sample size.")

    sorted_df = df.sort_values(score_col, ascending=False).reset_index(drop=True)
    top_min = float(sorted_df.loc[top_count - 1, score_col])
    bottom_start_idx = total - bottom_count
    bottom_max = float(sorted_df.loc[bottom_start_idx, score_col])

    top_bin = df[df[score_col] >= top_min].copy()
    bottom_bin = df[df[score_col] <= bottom_max].copy()
    middle_bin = df[(df[score_col] < top_min) & (df[score_col] > bottom_max)].copy()

    if len(top_bin) != top_count or len(middle_bin) != middle_count or len(bottom_bin) != bottom_count:
        print(
            "WARNING: Bin counts differ from targets after applying score cutoffs. "
            f"Top={len(top_bin)}, Middle={len(middle_bin)}, Bottom={len(bottom_bin)}"
        )

    return top_bin, middle_bin, bottom_bin, top_min, bottom_max

#%%
# Summary statistics table
print("Building summary statistics table...")
summary_row = {
    "Sample": "Human audit sample",
    "N": sample_count,
    "Score min": f"{score_min:.2f}",
    "Score max": f"{score_max:.2f}",
    "Score mean (SD)": f"{score_mean:.2f} ({score_sd:.2f})"
}
summary_df = pd.DataFrame([summary_row])

summary_csv_path = os.path.join(TABLE_DIR, "human_audit_summary_stats.csv")
summary_df.to_csv(summary_csv_path, index=False)

save_table(
    summary_df,
    "human_audit_summary_stats",
    "Summary statistics for the human audit sample. "
    "Generated by: src/post_query/analysis/audit_analysis.py",
    escape=False
)

#%%
# Table X2: performance bins
print("Building performance table...")
top_bin, middle_bin, bottom_bin, top_min, bottom_max = split_by_target_counts(
    audit_tf,
    top_count=106,
    middle_count=101,
    bottom_count=94
)

full_stats = bin_stats(audit_tf, "Full sample")
top_stats = bin_stats(top_bin, "Top bin")
middle_stats = bin_stats(middle_bin, "Middle bin")
bottom_stats = bin_stats(bottom_bin, "Bottom bin")

middle_min = float(middle_bin[score_col].min())
middle_max = float(middle_bin[score_col].max())

performance_rows = [
    {
        "Sample": "Full sample",
        "Scores": format_range(score_min, score_max),
        "Number": full_stats["count"],
        "True positive": full_stats["true_pos"],
        "False positive": full_stats["false_pos"],
        "True positive rate": f"{full_stats['rate']:.1f}\\%"
    },
    {
        "Sample": "Top bin",
        "Scores": format_range(top_min, score_max),
        "Number": top_stats["count"],
        "True positive": top_stats["true_pos"],
        "False positive": top_stats["false_pos"],
        "True positive rate": f"{top_stats['rate']:.1f}\\%"
    },
    {
        "Sample": "Middle bin",
        "Scores": format_range(middle_min, middle_max),
        "Number": middle_stats["count"],
        "True positive": middle_stats["true_pos"],
        "False positive": middle_stats["false_pos"],
        "True positive rate": f"{middle_stats['rate']:.1f}\\%"
    },
    {
        "Sample": "Bottom bin",
        "Scores": format_range(score_min, bottom_max),
        "Number": bottom_stats["count"],
        "True positive": bottom_stats["true_pos"],
        "False positive": bottom_stats["false_pos"],
        "True positive rate": f"{bottom_stats['rate']:.1f}\\%"
    },
]

performance_df = pd.DataFrame(performance_rows)

performance_csv_path = os.path.join(TABLE_DIR, "human_audit_performance_bins.csv")
performance_df.to_csv(performance_csv_path, index=False)

performance_tex_path = os.path.join(TABLE_DIR, "human_audit_performance_bins.tex")
with open(performance_tex_path, "w") as f:
    f.write(
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\caption{LLM Performance Statistics}\n"
        "\\label{tab:audit_performance_bins}\n"
        "\\begin{tabular}{l c c c c c}\n"
        "\\hline\n"
        "Sample & Scores & Number & True positive & False positive & True positive rate \\\\\n"
        "\\hline\n"
    )
    for row in performance_rows:
        f.write(
            f"{row['Sample']} & {row['Scores']} & {row['Number']} & "
            f"{row['True positive']} & {row['False positive']} & {row['True positive rate']} \\\\\n"
        )
    f.write("\\hline\n\\end{tabular}\n\\end{table}\n")

with open(os.path.join(TABLE_DIR, "human_audit_performance_bins.txt"), "w") as f:
    f.write(
        "Human audit true/false positive rates by score bins. "
        "Generated by: src/post_query/analysis/audit_analysis.py"
    )

#%%
# Table X1 + Figure Y1: score distribution
print("Building score distribution table and figure...")
score_bins_table = make_histogram_table(audit_tf[score_col], bins=10)
save_table(
    score_bins_table,
    "human_audit_score_bins_10",
    "Ten-bin score counts for LLM-validated scores in the human audit sample. "
    "Generated by: src/post_query/analysis/audit_analysis.py",
    escape=False
)

fig, ax = plt.subplots()
ax.hist(
    audit_tf[score_col],
    bins=10,
    color=GHIBLI_COLORS[0],
    edgecolor=STYLE_CONFIG["edge_color"],
    linewidth=STYLE_CONFIG["edge_width"]
)
ax.set_xlabel("LLM-validated score")
ax.set_ylabel("Count")
plt.tight_layout()
save_figure(
    "human_audit_score_histogram_10bins",
    "Histogram of LLM-validated scores for the human audit sample (10 bins). "
    "Generated by: src/post_query/analysis/audit_analysis.py",
    fig=fig
)

#%%
# Company counts from true positives
print("Computing company counts for true positives...")
company_counts = {}
unique_company_count = None
if "companyname" in audit_tf.columns:
    true_pos_df = audit_tf[audit_tf["audit_label"] == "T"].copy()
    true_pos_df["companyname_clean"] = true_pos_df["companyname"].astype(str).str.strip()
    true_pos_df["companyname_norm"] = true_pos_df["companyname_clean"].map(
        lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    )
    unique_company_count = int(true_pos_df["companyname_norm"].nunique())

    target_companies = {
        # NOTE: In assets/human_audit_final.xlsx, GOL appears with a spreadsheet
        # encoding issue as something like "Gol Linhas A√©reas Inteligentes S.A.".
        # After the Unicode normalization above, that becomes
        # "Gol Linhas Areas Inteligentes S.A." ("Areas", not "Aereas").
        # This breaks the generic exact/contains matching logic that works for the
        # other companies, so we handle GOL explicitly here.
        "gol_linhas_aereas_inteligentes": "Gol Linhas Areas Inteligentes",
        "micron_technology": "Micron Technology",
        "norske_skogindustrier": "Norske Skogindustrier",
        "coca_cola_bottlers_japan": "Coca-Cola Bottlers Japan",
    }
    for key, company in target_companies.items():
        if key == "gol_linhas_aereas_inteligentes":
            mask = true_pos_df["companyname_norm"].str.lower().str.contains(
                company.lower(), na=False
            )
        else:
            mask = true_pos_df["companyname_norm"].str.lower() == company.lower()
            if not mask.any():
                mask = true_pos_df["companyname_norm"].str.lower().str.contains(
                    company.lower(), na=False
                )
        company_counts[key] = int(mask.sum())
else:
    print("companyname column missing; skipping company counts.")

#%%
# Save YAML constants
print(f"Saving YAML constants: {YAML_PATH}")
audit_yaml = {
    "sample_count": sample_count,
    "true_positive_count": true_count,
    "false_positive_count": false_count,
    "true_positive_rate_pct": float(true_rate_pct),
    "score_min": float(score_min),
    "score_max": float(score_max),
    "sample_rate_pct": float(sample_rate_pct) if sample_rate_pct is not None else None,
    "top_bin": {
        "count": top_stats["count"],
        "true_positive_count": top_stats["true_pos"],
        "false_positive_count": top_stats["false_pos"],
        "true_positive_rate_pct": float(top_stats["rate"]),
        "score_min": float(top_min),
        "score_max": float(score_max),
    },
    "middle_bin": {
        "count": middle_stats["count"],
        "true_positive_count": middle_stats["true_pos"],
        "false_positive_count": middle_stats["false_pos"],
        "true_positive_rate_pct": float(middle_stats["rate"]),
        "score_min": float(middle_min),
        "score_max": float(top_min),
    },
    "bottom_bin": {
        "count": bottom_stats["count"],
        "true_positive_count": bottom_stats["true_pos"],
        "false_positive_count": bottom_stats["false_pos"],
        "true_positive_rate_pct": float(bottom_stats["rate"]),
        "score_min": float(score_min),
        "score_max": float(bottom_max),
    },
    "true_positive_companies": {
        "unique_count": unique_company_count,
        "gol_linhas_aereas_inteligentes_count": company_counts.get(
            "gol_linhas_aereas_inteligentes"
        ),
        "micron_technology_count": company_counts.get("micron_technology"),
        "norske_skogindustrier_count": company_counts.get("norske_skogindustrier"),
        "coca_cola_bottlers_japan_count": company_counts.get(
            "coca_cola_bottlers_japan"
        ),
    },
}

with open(YAML_PATH, "w") as f:
    yaml.dump(audit_yaml, f)

print("Audit analysis complete.")
print(f"  Sample count: {sample_count}")
print(f"  True positives: {true_count}")
print(f"  False positives: {false_count}")
