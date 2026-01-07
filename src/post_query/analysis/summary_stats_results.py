"""
Summary table of boolean classification flags from the main analysis dataset.

This script creates a publication-ready LaTeX table for classification results:
- LLM flags, validation flags, human audit flags, benchmark flags

Outputs:
- data/outputs/tables/summary_stats_results.csv
- data/outputs/tables/summary_stats_results.tex
- data/outputs/tables/summary_stats_results.txt
"""

#%%
import config
import pandas as pd
import numpy as np
from pathlib import Path

#----------------------------------------------------------------------------
# Helper functions
#----------------------------------------------------------------------------

def fmt_int(x: int) -> str:
    return f"{int(x):,}"

def fmt_pct(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}\\%"

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

panel_data = []
for var, label in BOOLEAN.items():
    col = df[var].dropna()
    n = col.count()
    t = int(col.sum())
    pct = fmt_pct(t / n * 100) if n > 0 else "NA"
    panel_data.append({
        "Variable": label,
        "N":        fmt_int(n),
        "Count_T":  fmt_int(t),
        "Percent_T": pct
    })

#----------------------------------------------------------------------------
# Save CSV
#----------------------------------------------------------------------------

panel_df = pd.DataFrame(panel_data)
panel_df.to_csv(CSV_PATH, index=False)

#----------------------------------------------------------------------------
# LaTeX output
#----------------------------------------------------------------------------

def make_latex_table(panel):
    rows = "\n".join([
        f"{r['Variable']} & {r['N']} & {r['Count_T']} & {r['Percent_T']} \\\\"
        for r in panel
    ])
    return (
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrr}" "\n"
        r"\toprule" "\n"
        r"Variable & $N$ & Count (True) & Percent (True) \\" "\n"
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
""" + make_latex_table(panel_data) + r"""
\end{minipage}
\begin{minipage}{\textwidth}
\vspace{1em}
\footnotesize
\textit{Notes:} Reports non-missing $N$, count of TRUE values, and percent TRUE for key boolean classification flags.
\end{minipage}
\end{table}
""".strip()

TEX_PATH.write_text(latex)

#----------------------------------------------------------------------------
# Save description
#----------------------------------------------------------------------------

TXT_PATH.write_text(
    "Publication-ready summary table for classification results:\n"
    "Boolean flags – N, count = TRUE, percent = TRUE (based on non-missing).\n"
    "Formatted for manuscript, uses readable headers."
)

#----------------------------------------------------------------------------
# Done
#----------------------------------------------------------------------------

print("Summary statistics results table written to:")
print(f"  • CSV  : {CSV_PATH}")
print(f"  • LaTeX: {TEX_PATH}")
print(f"  • TXT  : {TXT_PATH}")

