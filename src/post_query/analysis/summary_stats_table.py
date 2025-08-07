"""
Summary table of continuous and boolean variables from the main analysis dataset.

This script creates a publication‑ready LaTeX table with two panels:

• Panel A – mean, median, min, max, N for selected continuous variables  
• Panel B – N (non-missing), count = TRUE, percent = TRUE for key boolean flags

Outputs:
- data/outputs/tables/summary_stats.csv
- data/outputs/tables/summary_stats.tex
- data/outputs/tables/summary_stats.txt
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

def fmt_pct(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}\\%"

#----------------------------------------------------------------------------
# I/O paths
#----------------------------------------------------------------------------

OUT_DIR = Path("data/outputs/tables")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT_DIR / "summary_stats.csv"
TEX_PATH = OUT_DIR / "summary_stats.tex"
TXT_PATH = OUT_DIR / "summary_stats.txt"

#----------------------------------------------------------------------------
# Load data
#----------------------------------------------------------------------------

df = pd.read_feather("data/datasets/main_analysis_dataset.feather")

#----------------------------------------------------------------------------
# Panel A – Continuous variables
#----------------------------------------------------------------------------

CONTINUOUS = {
    "market_value_total_mil": "Market Value (mil USD)",
    "employees_thousands":   "Employees (thousands)",
    "audiolengthsec":        "Audio Length (seconds)",
    "transcript_year":       "Transcript Year"
}

panel_a = []
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

    panel_a.append({
        "Variable": label,
        "Mean":    mean_fmt,
        "Median":  med_fmt,
        "Min":     min_fmt,
        "Max":     max_fmt,
        "N":       fmt_int(col.count())
    })

#----------------------------------------------------------------------------
# Panel B – Boolean classification flags
#----------------------------------------------------------------------------

BOOLEAN = {
    "llm_flag":             "LLM Flagged Collusive",
    "llm_validation_flag":  "LLM Validation Flag",
    "human_audit_sample":   "Human Audit Sample",
    "human_audit_flag":     "Human Audit Flagged Collusive",
    "benchmark_sample":     "In Benchmark Sample",
    "benchmark_human_flag": "Human Benchmark Flagged Collusive"
}

panel_b = []
for var, label in BOOLEAN.items():
    col = df[var].dropna()
    n = col.count()
    t = int(col.sum())
    pct = fmt_pct(t / n * 100) if n > 0 else "NA"
    panel_b.append({
        "Variable": label,
        "N":        fmt_int(n),
        "Count_T":  fmt_int(t),
        "Percent_T": pct
    })

#----------------------------------------------------------------------------
# Save long CSV (tidy)
#----------------------------------------------------------------------------

panel_a_df = pd.DataFrame(panel_a)
panel_b_df = pd.DataFrame(panel_b)

csv_df = pd.concat([panel_a_df.assign(Panel="A"), panel_b_df.assign(Panel="B")])
csv_df.to_csv(CSV_PATH, index=False)

#----------------------------------------------------------------------------
# LaTeX output (Panel A full-width, Panel B clean headers)
#----------------------------------------------------------------------------

def make_latex_panel_a(panel):
    rows = "\n".join([
        f"{r['Variable']} & {r['Mean']} & {r['Median']} & {r['Min']} & {r['Max']} & {r['N']} \\\\"
        for r in panel
    ])
    return (
        r"\textbf{Panel A: Continuous variables} \\[0.25em]" "\n" +
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrr}" "\n"
        r"\toprule" "\n"
        r"Variable & Mean & Median & Min & Max & $N$ \\" "\n"
        r"\midrule" "\n" +
        rows + "\n" +
        r"\bottomrule" "\n"
        r"\end{tabular*}"
    )

def make_latex_panel_b(panel):
    rows = "\n".join([
        f"{r['Variable']} & {r['N']} & {r['Count_T']} & {r['Percent_T']} \\\\"
        for r in panel
    ])
    return (
        r"\textbf{Panel B: Boolean classification flags} \\[0.25em]" "\n" +
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
\caption{Summary statistics for the main analysis dataset}
\label{tab:summary_stats}
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
\textit{Notes:} Panel~A reports mean, median, min, max, and non-missing $N$ for continuous variables.
Panel~B reports non-missing $N$, count of TRUE values, and percent TRUE for key boolean flags.
\end{minipage}
\end{table}
""".strip()

TEX_PATH.write_text(latex)

#----------------------------------------------------------------------------
# Save description
#----------------------------------------------------------------------------

TXT_PATH.write_text(
    "Publication-ready summary table with two panels:\n"
    "A) Continuous variables – mean, median, min, max, N (year mean has 1 decimal).\n"
    "B) Boolean flags – N, count = TRUE, percent = TRUE (based on non-missing).\n"
    "Formatted for manuscript, Panel A spans full width, Panel B uses readable headers."
)

#----------------------------------------------------------------------------
# Done
#----------------------------------------------------------------------------

print("Summary statistics table written to:")
print(f"  • CSV  : {CSV_PATH}")
print(f"  • LaTeX: {TEX_PATH}")
print(f"  • TXT  : {TXT_PATH}")
