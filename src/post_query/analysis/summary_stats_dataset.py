"""
Summary table of continuous variables from the main analysis dataset.

This script creates a publication-ready LaTeX table for raw dataset characteristics:
- Market value, employees, audio length, transcript year

Outputs:
- data/outputs/tables/summary_stats_dataset.csv
- data/outputs/tables/summary_stats_dataset.tex
- data/outputs/tables/summary_stats_dataset.txt
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

def fmt_int_nocomma(x: int) -> str:
    return f"{int(x)}"

def fmt_float(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}"

def fmt_float_nocomma(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}"

#----------------------------------------------------------------------------
# I/O paths
#----------------------------------------------------------------------------

OUT_DIR = Path("data/outputs/tables")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT_DIR / "summary_stats_dataset.csv"
TEX_PATH = OUT_DIR / "summary_stats_dataset.tex"
TXT_PATH = OUT_DIR / "summary_stats_dataset.txt"

#----------------------------------------------------------------------------
# Load data
#----------------------------------------------------------------------------

df = pd.read_feather("data/datasets/main_analysis_dataset.feather")

#----------------------------------------------------------------------------
# Continuous variables (raw dataset characteristics)
#----------------------------------------------------------------------------

CONTINUOUS = {
    "market_value_total_mil": "Market Value (mil USD)",
    "employees_thousands":   "Employees (thousands)",
    "audiolengthsec":        "Audio Length (seconds)",
    "transcript_year":       "Transcript Year"
}

panel_data = []
for var, label in CONTINUOUS.items():
    col = df[var].dropna()
    if var == "transcript_year":
        mean_fmt = fmt_float_nocomma(col.mean(), 1)
        med_fmt = fmt_int_nocomma(col.median())
        min_fmt = fmt_int_nocomma(col.min())
        max_fmt = fmt_int_nocomma(col.max())
    else:
        mean_fmt = fmt_float(col.mean())
        med_fmt = fmt_float(col.median())
        if var in ["market_value_total_mil", "employees_thousands"]:
            min_fmt = fmt_float(col.min(), 3)
        else:
            min_fmt = fmt_float(col.min(), 0)
        max_fmt = fmt_float(col.max(), 0)

    panel_data.append({
        "Variable": label,
        "Mean":    mean_fmt,
        "Median":  med_fmt,
        "Min":     min_fmt,
        "Max":     max_fmt,
        "N":       fmt_int(col.count())
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
        f"{r['Variable']} & {r['Mean']} & {r['Median']} & {r['Min']} & {r['Max']} & {r['N']} \\\\"
        for r in panel
    ])
    return (
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrr}" "\n"
        r"\toprule" "\n"
        r"Variable & Mean & Median & Min & Max & $N$ \\" "\n"
        r"\midrule" "\n" +
        rows + "\n" +
        r"\bottomrule" "\n"
        r"\end{tabular*}"
    )

latex = r"""
\begin{table}[ht]
\centering
\caption{Summary statistics for dataset characteristics}
\label{tab:summary_stats_dataset}
\begin{minipage}{\textwidth}
\raggedright
\vspace{0.5em}
""" + make_latex_table(panel_data) + r"""
\end{minipage}
\begin{minipage}{\textwidth}
\vspace{1em}
\footnotesize
\textit{Notes:} Reports mean, median, min, max, and non-missing $N$ for continuous variables describing the dataset characteristics.
\end{minipage}
\end{table}
""".strip()

TEX_PATH.write_text(latex)

#----------------------------------------------------------------------------
# Save description
#----------------------------------------------------------------------------

TXT_PATH.write_text(
    "Publication-ready summary table for dataset characteristics:\n"
    "Continuous variables – mean, median, min, max, N (year mean has 1 decimal).\n"
    "Formatted for manuscript, spans full width."
)

#----------------------------------------------------------------------------
# Done
#----------------------------------------------------------------------------

print("Summary statistics dataset table written to:")
print(f"  • CSV  : {CSV_PATH}")
print(f"  • LaTeX: {TEX_PATH}")
print(f"  • TXT  : {TXT_PATH}")

