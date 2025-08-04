#%%
"""
LLM Collusion Tagging Analysis

This script analyzes LLM collusion tagging behavior by:
- Calculating summary statistics and saving to YAML.
- Fitting logistic regressions.
- Creating tables of LLM tag rates by market value, sector, and year.
- Generating corresponding figures (PDF + PNG, 1:1 and 16:9).
"""

#%%
import config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import re
from statsmodels.stats.proportion import proportion_confint
from pathlib import Path
import yaml

#%%
# Paths
output_dir = Path("data/outputs")
figure_dir = output_dir / "figures"
table_dir = output_dir / "tables"
yaml_dir = Path("data/yaml")
for path in [figure_dir, table_dir, yaml_dir]:
    path.mkdir(parents=True, exist_ok=True)

#%%
def clean_column(col):
    return re.sub(r'\W|^(?=\d)', '_', col)

def proportion_ci(count, nobs, alpha=0.05):
    low, high = proportion_confint(count, nobs, alpha=alpha, method='wilson')
    return low * 100, high * 100

def save_figure(name, description, fig=None):
    fig = fig or plt.gcf()
    for aspect, size in {"1x1": (6, 6), "16x9": (12, 6.75)}.items():
        fig.set_size_inches(*size)
        path = figure_dir / f"{name}_{aspect}"
        fig.savefig(f"{path}.png", dpi=300)
        fig.savefig(f"{path}.pdf")
    with open(figure_dir / f"{name}.txt", "w") as f:
        f.write(description)
    plt.close(fig)

def save_table(df, name, description):
    csv_path = table_dir / f"{name}.csv"
    tex_path = table_dir / f"{name}.tex"
    df.to_csv(csv_path, index=False)
    df.to_latex(tex_path, index=False, float_format="%.2f", longtable=True)
    with open(table_dir / f"{name}.txt", "w") as f:
        f.write(description)

#%%
# Load and prepare data
data_path = Path("data/datasets/main_analysis_dataset.feather")
df = pd.read_feather(data_path)
df['log_mkvalt'] = np.log(df['mkvalt'].replace(0, np.nan))
df['sector'] = df['gsector'].astype('category')
df['year'] = df['fyear'].astype('category')

#%%
# Summary statistics
benchmark_df = df[df['benchmark_sample'] == 1]
summary_stats = {
    'total_transcripts': len(df),
    'llm_tagged_collusive': int(df['llm_flag'].sum()),
    'llm_tagged_collusive_pct': float(df['llm_flag'].mean() * 100),
    'benchmark_sample': int(df['benchmark_sample'].sum()),
    'benchmark_llm_tagged_collusive': int(benchmark_df['llm_flag'].sum()),
    'benchmark_llm_tagged_collusive_pct': float(benchmark_df['llm_flag'].mean() * 100),
    'benchmark_human_tagged_collusive': int(df['benchmark_human_flag'].sum()),
    'benchmark_human_tagged_collusive_pct': float(df['benchmark_human_flag'].mean() * 100)
}
with open(yaml_dir / "summary_stats.yaml", "w") as f:
    yaml.dump(summary_stats, f)

#%%
# Market value decile table and plot
df_mv = df.dropna(subset=['mkvalt']).copy()
df_mv['mv_decile'] = pd.qcut(df_mv['mkvalt'], q=10, labels=False) + 1
mv_stats = (
    df_mv.groupby('mv_decile')
    .agg(n=('llm_flag', 'count'), avg_mkvalt=('mkvalt', 'mean'), num_hits=('llm_flag', 'sum'))
    .reset_index()
)
mv_stats['llm_tag_pct'] = mv_stats['num_hits'] / mv_stats['n'] * 100
mv_stats[['ci_low', 'ci_high']] = mv_stats.apply(
    lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
)
save_table(
    mv_stats[['mv_decile', 'n', 'avg_mkvalt', 'llm_tag_pct', 'ci_low', 'ci_high']],
    "market_value_deciles",
    "LLM tagging by market value decile. Produced by correlation_analysis.py"
)

fig, ax = plt.subplots()
ax.errorbar(
    mv_stats['mv_decile'],
    mv_stats['llm_tag_pct'],
    yerr=[mv_stats['llm_tag_pct'] - mv_stats['ci_low'], mv_stats['ci_high'] - mv_stats['llm_tag_pct']],
    fmt='o-', capsize=4
)
ax.set_title("LLM Tag Rate by Market Value Decile")
ax.set_xlabel("Market Value Decile")
ax.set_ylabel("LLM Tagged Collusive (%)")
save_figure("market_value_deciles", "LLM tag rate by market value decile. Produced by correlation_analysis.py", fig)

#%%
# Sector table and plot (horizontal bars)
sector_stats = (
    df.groupby('sector')['llm_flag']
    .agg(['mean', 'count', 'sum'])
    .rename(columns={'mean': 'llm_tag_pct', 'count': 'n', 'sum': 'num_hits'})
    .reset_index()
)
sector_stats['llm_tag_pct'] *= 100
sector_stats[['ci_low', 'ci_high']] = sector_stats.apply(
    lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
)
sector_sorted = sector_stats.sort_values("llm_tag_pct")
save_table(
    sector_sorted[['sector', 'llm_tag_pct', 'ci_low', 'ci_high', 'n']],
    "sector_tag_rates",
    "LLM tagging rate by sector with 95% CI. Produced by correlation_analysis.py"
)

fig, ax = plt.subplots()
ax.barh(
    y=np.arange(len(sector_sorted)),
    width=sector_sorted['llm_tag_pct'],
    xerr=[sector_sorted['llm_tag_pct'] - sector_sorted['ci_low'], sector_sorted['ci_high'] - sector_sorted['llm_tag_pct']],
    capsize=4, color='skyblue'
)
ax.set_yticks(np.arange(len(sector_sorted)))
ax.set_yticklabels(sector_sorted['sector'])
ax.set_xlabel("LLM Tagged Collusive (%)")
ax.set_title("LLM Tag Rate by Sector")
save_figure("sector_tag_rates", "LLM tag rate by sector (horizontal bar chart). Produced by correlation_analysis.py", fig)

#%%
# Year table and plot
df_year = df[df['fyear'] >= 2008].copy()
year_stats = (
    df_year.groupby('fyear')['llm_flag']
    .agg(['mean', 'count', 'sum'])
    .rename(columns={'mean': 'llm_tag_pct', 'count': 'n', 'sum': 'num_hits'})
    .reset_index()
)
year_stats['llm_tag_pct'] *= 100
year_stats[['ci_low', 'ci_high']] = year_stats.apply(
    lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
)
save_table(
    year_stats[['fyear', 'llm_tag_pct', 'ci_low', 'ci_high', 'n']],
    "year_tag_rates",
    "LLM tagging rate by fiscal year with 95% CI. Produced by correlation_analysis.py"
)

fig, ax = plt.subplots()
ax.errorbar(
    year_stats['fyear'],
    year_stats['llm_tag_pct'],
    yerr=[year_stats['llm_tag_pct'] - year_stats['ci_low'], year_stats['ci_high'] - year_stats['llm_tag_pct']],
    fmt='o-', capsize=4
)
ax.set_title("LLM Tag Rate by Year")
ax.set_xlabel("Year")
ax.set_ylabel("LLM Tagged Collusive (%)")
save_figure("year_tag_rates", "LLM tag rate by year. Produced by correlation_analysis.py", fig)
