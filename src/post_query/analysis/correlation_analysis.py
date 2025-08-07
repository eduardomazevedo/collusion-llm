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
df['log_market_value'] = np.log(df['market_value_total_mil'].replace(0, np.nan))
df['sector'] = df['gics_sector'].astype('category')
df['year'] = df['transcript_year'].astype('category')

#%%
# Summary statistics
benchmark_df = df[df['benchmark_sample'] == 1]

# Statistics for non-missing observations by variable
sector_valid = df[df['gics_sector'].notna()]
year_valid = df[df['transcript_year'].notna()]
mkvalt_valid = df[df['market_value_total_mil'].notna()]

summary_stats = {
    'total_transcripts': len(df),
    'llm_tagged_collusive': int(df['llm_flag'].sum()),
    'llm_tagged_collusive_pct': float(df['llm_flag'].mean() * 100),
    'benchmark_sample': int(df['benchmark_sample'].sum()),
    'benchmark_llm_tagged_collusive': int(benchmark_df['llm_flag'].sum()),
    'benchmark_llm_tagged_collusive_pct': float(benchmark_df['llm_flag'].mean() * 100),
    'benchmark_human_tagged_collusive': int(df['benchmark_human_flag'].sum()),
    'benchmark_human_tagged_collusive_pct': float(df['benchmark_human_flag'].mean() * 100),
    
    # Non-missing observations statistics
    'sector_valid_observations': len(sector_valid),
    'sector_valid_tag_rate': float(sector_valid['llm_flag'].mean() * 100),
    'year_valid_observations': len(year_valid),
    'year_valid_tag_rate': float(year_valid['llm_flag'].mean() * 100),
    'mkvalt_valid_observations': len(mkvalt_valid),
    'mkvalt_valid_tag_rate': float(mkvalt_valid['llm_flag'].mean() * 100),
    
    # Missing observations statistics
    'sector_missing_observations': int(df['gics_sector'].isna().sum()),
    'year_missing_observations': int(df['transcript_year'].isna().sum()),
    'mkvalt_missing_observations': int(df['market_value_total_mil'].isna().sum()),
    'mkvalt_missing_tag_rate': float(df[df['market_value_total_mil'].isna()]['llm_flag'].mean() * 100)
}
with open(yaml_dir / "correlates_collusive_communication.yaml", "w") as f:
    yaml.dump(summary_stats, f)

#%%
# Market value decile table and plot
df_mv = df.dropna(subset=['market_value_total_mil']).copy()
df_mv['mv_decile'] = pd.qcut(df_mv['market_value_total_mil'], q=10, labels=False) + 1
mv_stats = (
    df_mv.groupby('mv_decile')
    .agg(n=('llm_flag', 'count'), avg_mkvalt=('market_value_total_mil', 'mean'), num_hits=('llm_flag', 'sum'))
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
# Add horizontal line for sample average
sample_avg = df_mv['llm_flag'].mean() * 100
ax.axhline(y=sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
ax.set_xlabel("Market Value Decile")
ax.set_ylabel("LLM Tagged Collusive (%)")
ax.set_ylim(0, None)
save_figure("market_value_deciles", "LLM tag rate by market value decile. Produced by correlation_analysis.py", fig)

#%%
# Sector table and plot (horizontal bars)
# Load GICS sector mapping
with open(Path("assets/gics_sectors.yaml"), "r") as f:
    gics_sectors = yaml.safe_load(f)

sector_stats = (
    df.groupby('gics_sector')['llm_flag']
    .agg(['mean', 'count', 'sum'])
    .rename(columns={'mean': 'llm_tag_pct', 'count': 'n', 'sum': 'num_hits'})
    .reset_index()
)
sector_stats['llm_tag_pct'] *= 100
# Map sector codes to names - convert string sector codes to integers for mapping
sector_stats['gics_sector_int'] = sector_stats['gics_sector'].astype(int)
sector_stats['sector_name'] = sector_stats['gics_sector_int'].map(gics_sectors)
sector_stats[['ci_low', 'ci_high']] = sector_stats.apply(
    lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
)
# Sort from most to least collusive
sector_sorted = sector_stats.sort_values("llm_tag_pct", ascending=False)
save_table(
    sector_sorted[['sector_name', 'llm_tag_pct', 'ci_low', 'ci_high', 'n']],
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
# Add vertical line for sample average (using sector_valid data for consistency)
sector_sample_avg = sector_valid['llm_flag'].mean() * 100
ax.axvline(x=sector_sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
ax.set_yticks(np.arange(len(sector_sorted)))
ax.set_yticklabels(sector_sorted['sector_name'])
ax.set_xlabel("LLM Tagged Collusive (%)")
ax.set_xlim(0, None)
plt.tight_layout()
save_figure("sector_tag_rates", "LLM tag rate by sector (horizontal bar chart). Produced by correlation_analysis.py", fig)

#%%
# Year table and plot
df_year = df[df['transcript_year'] >= 2008].copy()
# Ensure transcript_year is integer for proper axis labels
df_year['transcript_year'] = df_year['transcript_year'].astype(int)
year_stats = (
    df_year.groupby('transcript_year')['llm_flag']
    .agg(['mean', 'count', 'sum'])
    .rename(columns={'mean': 'llm_tag_pct', 'count': 'n', 'sum': 'num_hits'})
    .reset_index()
)
year_stats['llm_tag_pct'] *= 100
year_stats[['ci_low', 'ci_high']] = year_stats.apply(
    lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
)
save_table(
    year_stats[['transcript_year', 'llm_tag_pct', 'ci_low', 'ci_high', 'n']],
    "year_tag_rates",
    "LLM tagging rate by fiscal year with 95% CI. Produced by correlation_analysis.py"
)

fig, ax = plt.subplots()
ax.errorbar(
    year_stats['transcript_year'],
    year_stats['llm_tag_pct'],
    yerr=[year_stats['llm_tag_pct'] - year_stats['ci_low'], year_stats['ci_high'] - year_stats['llm_tag_pct']],
    fmt='o-', capsize=4
)
# Add horizontal line for sample average
year_sample_avg = df_year['llm_flag'].mean() * 100
ax.axhline(y=year_sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
ax.set_xlabel("Year")
ax.set_ylabel("LLM Tagged Collusive (%)")
ax.set_ylim(0, None)
# Set x-axis to show only integer years
ax.set_xticks(year_stats['transcript_year'])
save_figure("year_tag_rates", "LLM tag rate by year. Produced by correlation_analysis.py", fig)
