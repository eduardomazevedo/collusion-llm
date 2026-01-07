"""
Summary table of boolean classification flags and LLM scores from the main analysis dataset.

This script creates a publication-ready LaTeX table with two panels:
- Panel A: Boolean classification flags (LLM flags, validation flags, human audit flags, benchmark flags)
- Panel B: LLM score statistics (average initial score in entire sample, and scores in LLM flagged sample)

Outputs:
- data/outputs/tables/summary_stats_results.csv
- data/outputs/tables/summary_stats_results.tex
- data/outputs/tables/summary_stats_results.txt
"""

#%%
import config
import pandas as pd
import numpy as np
import os
from pathlib import Path

#----------------------------------------------------------------------------
# Helper functions
#----------------------------------------------------------------------------

def fmt_int(x: int) -> str:
    return f"{int(x):,}"

def fmt_pct(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}\\%"

def fmt_float(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}"

#----------------------------------------------------------------------------
# I/O paths
#----------------------------------------------------------------------------

OUT_DIR = Path("data/outputs/tables")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT_DIR / "summary_stats_results.csv"
TEX_PATH = OUT_DIR / "summary_stats_results.tex"
TXT_PATH = OUT_DIR / "summary_stats_results.txt"

#----------------------------------------------------------------------------
# Load data
#----------------------------------------------------------------------------

df = pd.read_feather("data/datasets/main_analysis_dataset.feather")
top_transcripts_data_df = pd.read_csv(os.path.join(config.DATA_DIR, 'datasets', 'top_transcripts_data.csv'))

#----------------------------------------------------------------------------
# Boolean classification flags (results)
#----------------------------------------------------------------------------

BOOLEAN = {
    "llm_flag":             "LLM Flagged Collusive",
    "llm_validation_flag":  "LLM Validation Flag",
    "human_audit_sample":   "Human Audit Sample",
    "human_audit_flag":     "Human Audit Flagged Collusive",
    "benchmark_sample":     "In Benchmark Sample",
    "benchmark_human_flag": "Human Benchmark Flagged Collusive"
}

panel_a = []
for var, label in BOOLEAN.items():
    col = df[var].dropna()
    n = col.count()
    t = int(col.sum())
    pct = fmt_pct(t / n * 100) if n > 0 else "NA"
    panel_a.append({
        "Variable": label,
        "N":        fmt_int(n),
        "Count_T":  fmt_int(t),
        "Percent_T": pct
    })

#----------------------------------------------------------------------------
# Panel B – LLM Score Statistics by Sample
#----------------------------------------------------------------------------

# Merge with top_transcripts_data to get mean_score_ten_repeats (only available for LLM flagged)
df_with_scores = df.merge(
    top_transcripts_data_df[['transcriptid', 'mean_score_ten_repeats']],
    on='transcriptid',
    how='left'
)

def calc_stats(series):
    """Calculate mean, sd, and N for a series, handling empty/missing data."""
    valid = series.dropna()
    if len(valid) == 0:
        return None, None, 0
    mean = valid.mean()
    sd = valid.std()
    n = len(valid)
    return mean, sd, n

# Define samples
samples = {
    "Entire Sample": df_with_scores,
    "LLM Flagged": df_with_scores[df_with_scores['llm_flag'] == True],
    "LLM Validated": df_with_scores[df_with_scores['llm_validation_flag'] == True],
    "Audit Validated": df_with_scores[df_with_scores['human_audit_flag'] == True]
}

# Build panel B data
panel_b = []
for sample_name, sample_df in samples.items():
    # Original score
    orig_mean, orig_sd, orig_n = calc_stats(sample_df['original_score'])
    
    # Mean score 10 repetitions (only for LLM flagged samples)
    # Entire Sample doesn't have this, so show "—"
    if sample_name == "Entire Sample":
        mean10_str = "—"
        mean10_n = 0
        mean10_n_str = "--"
    else:
        mean10_mean, mean10_sd, mean10_n = calc_stats(sample_df['mean_score_ten_repeats'])
        if mean10_mean is not None:
            mean10_str = f"{fmt_float(mean10_mean, 2)} ({fmt_float(mean10_sd, 2)})"
        else:
            mean10_str = "—"
        mean10_n_str = fmt_int(mean10_n)
    
    # Format original score
    if orig_mean is not None:
        orig_str = f"{fmt_float(orig_mean, 2)} ({fmt_float(orig_sd, 2)})"
    else:
        orig_str = "—"
    
    panel_b.append({
        "Sample": sample_name,
        "Original Score": orig_str,
        "N (Original)": fmt_int(orig_n),
        "Mean Score (10 Rep)": mean10_str,
        "N (10 Rep)": mean10_n_str
    })

#----------------------------------------------------------------------------
# Save CSV
#----------------------------------------------------------------------------

panel_a_df = pd.DataFrame(panel_a)
panel_b_df = pd.DataFrame(panel_b)

csv_df = pd.concat([panel_a_df.assign(Panel="A"), panel_b_df.assign(Panel="B")])
csv_df.to_csv(CSV_PATH, index=False)

#----------------------------------------------------------------------------
# LaTeX output
#----------------------------------------------------------------------------

def make_latex_panel_a(panel):
    rows = "\n".join([
        f"{r['Variable']} & {r['N']} & {r['Count_T']} & {r['Percent_T']} \\\\"
        for r in panel
    ])
    return (
        r"\textbf{Panel A: Boolean classification flags} \\[0.25em]" "\n" +
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrr}" "\n"
        r"\toprule" "\n"
        r"Variable & $N$ & Count (True) & Percent (True) \\" "\n"
        r"\midrule" "\n" +
        rows + "\n" +
        r"\bottomrule" "\n"
        r"\end{tabular*}"
    )

def make_latex_panel_b(panel):
    rows = "\n".join([
        f"{r['Sample']} & {r['Original Score']} & {r['N (Original)']} & {r['Mean Score (10 Rep)']} & {r['N (10 Rep)']} \\\\"
        for r in panel
    ])
    return (
        r"\textbf{Panel B: LLM score statistics by sample} \\[0.25em]" "\n" +
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccc}" "\n"
        r"\toprule" "\n"
        r"Sample & \multicolumn{2}{c}{Original Score} & \multicolumn{2}{c}{Mean Score (10 Rep)} \\" "\n"
        r"\cmidrule(lr){2-3} \cmidrule(lr){4-5}" "\n"
        r" & Mean (SD) & $N$ & Mean (SD) & $N$ \\" "\n"
        r"\midrule" "\n" +
        rows + "\n" +
        r"\bottomrule" "\n"
        r"\end{tabular*}"
    )

latex = r"""
\begin{table}[ht]
\centering
\caption{Summary statistics for classification results}
\label{tab:summary_stats_results}
\begin{minipage}{\textwidth}
\raggedright
\vspace{0.5em}
""" + make_latex_panel_a(panel_a) + r"""

\vspace{1.5em}
""" + make_latex_panel_b(panel_b) + r"""
\end{minipage}
\begin{minipage}{\textwidth}
\vspace{1em}
\footnotesize
\textit{Notes:} Panel~A reports non-missing $N$, count of TRUE values, and percent TRUE for key boolean classification flags.
Panel~B reports mean (standard deviation) and sample size $N$ for LLM scores across different samples. Original Score is from the initial query. Mean Score (10 Rep) is the average across the first 10 validation repetitions (original query plus 10 repeats), and is only available for LLM flagged transcripts. "—" indicates the score is not available for that sample.
\end{minipage}
\end{table}
""".strip()

TEX_PATH.write_text(latex)

#----------------------------------------------------------------------------
# Save description
#----------------------------------------------------------------------------

TXT_PATH.write_text(
    "Publication-ready summary table for classification results with two panels:\n"
    "Panel A: Boolean flags – N, count = TRUE, percent = TRUE (based on non-missing).\n"
    "Panel B: LLM score statistics by sample – reports mean (SD) and N for Original Score and Mean Score (10 Rep) across four samples: Entire Sample, LLM Flagged, LLM Validated, and Audit Validated. Mean Score (10 Rep) is only available for LLM flagged transcripts (shows as '—' for Entire Sample).\n"
    "Formatted for manuscript, uses readable headers with grouped columns for each score type."
)

#----------------------------------------------------------------------------
# Done
#----------------------------------------------------------------------------

print("Summary statistics results table written to:")
print(f"  • CSV  : {CSV_PATH}")
print(f"  • LaTeX: {TEX_PATH}")
print(f"  • TXT  : {TXT_PATH}")

