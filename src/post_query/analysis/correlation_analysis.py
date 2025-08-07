#%%
"""
LLM Collusion Tagging Analysis

This script analyzes collusion tagging behavior across three flag variables by:
- Calculating summary statistics and saving to YAML for llm_flag, llm_validation_flag, and human_audit_flag
- Creating tables of tag rates by market value, sector, and year for each flag variable
- Generating corresponding figures (PDF + PNG, 1:1 and 16:9) for each flag variable
- Treating NA values in validation and audit flags as False (not flagged)
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

def analyze_flag_by_market_value(df, flag_col, flag_name):
    """Generate market value decile analysis for a flag variable"""
    # Create descriptive y-axis label based on flag type
    if flag_name == 'llm':
        ylabel = "LLM Flagged as Collusive (%)"
    elif flag_name == 'llm_validation':
        ylabel = "LLM Flagged and Validated as Collusive (%)"
    elif flag_name == 'human_audit':
        ylabel = "LLM Flagged, Validated, and Human Audited as Collusive (%)"
    else:
        ylabel = "Tagged as Collusive (%)"
    
    df_mv = df.dropna(subset=['market_value_total_mil']).copy()
    df_mv['mv_decile'] = pd.qcut(df_mv['market_value_total_mil'], q=10, labels=False) + 1
    mv_stats = (
        df_mv.groupby('mv_decile')
        .agg(n=(flag_col, 'count'), avg_mkvalt=('market_value_total_mil', 'mean'), num_hits=(flag_col, 'sum'))
        .reset_index()
    )
    mv_stats['tag_pct'] = mv_stats['num_hits'] / mv_stats['n'] * 100
    mv_stats[['ci_low', 'ci_high']] = mv_stats.apply(
        lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
    )
    
    # Save table
    save_table(
        mv_stats[['mv_decile', 'n', 'avg_mkvalt', 'tag_pct', 'ci_low', 'ci_high']],
        f"market_value_deciles_{flag_name}",
        f"{flag_name} tagging by market value decile. Produced by correlation_analysis.py"
    )
    
    # Create figure
    fig, ax = plt.subplots()
    ax.errorbar(
        mv_stats['mv_decile'],
        mv_stats['tag_pct'],
        yerr=[mv_stats['tag_pct'] - mv_stats['ci_low'], mv_stats['ci_high'] - mv_stats['tag_pct']],
        fmt='o-', capsize=4
    )
    # Add horizontal line for sample average
    sample_avg = df_mv[flag_col].mean() * 100
    ax.axhline(y=sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax.set_xlabel("Market Value Decile")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, None)
    save_figure(f"market_value_deciles_{flag_name}", f"{flag_name} tag rate by market value decile. Produced by correlation_analysis.py", fig)
    
    return len(df_mv), float(df_mv[flag_col].mean() * 100)

def analyze_flag_by_sector(df, flag_col, flag_name, gics_sectors):
    """Generate sector analysis for a flag variable"""
    # Create descriptive x-axis label based on flag type
    if flag_name == 'llm':
        xlabel = "LLM Flagged as Collusive (%)"
    elif flag_name == 'llm_validation':
        xlabel = "LLM Flagged and Validated as Collusive (%)"
    elif flag_name == 'human_audit':
        xlabel = "LLM Flagged, Validated, and Human Audited as Collusive (%)"
    else:
        xlabel = "Tagged as Collusive (%)"
    
    sector_valid = df[df['gics_sector'].notna()]
    sector_stats = (
        sector_valid.groupby('gics_sector', observed=True)[flag_col]
        .agg(['mean', 'count', 'sum'])
        .rename(columns={'mean': 'tag_pct', 'count': 'n', 'sum': 'num_hits'})
        .reset_index()
    )
    sector_stats['tag_pct'] *= 100
    # Map sector codes to names - convert string sector codes to integers for mapping
    sector_stats['gics_sector_int'] = sector_stats['gics_sector'].astype(int)
    sector_stats['sector_name'] = sector_stats['gics_sector_int'].map(gics_sectors)
    sector_stats[['ci_low', 'ci_high']] = sector_stats.apply(
        lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
    )
    # Sort from most to least collusive
    sector_sorted = sector_stats.sort_values("tag_pct", ascending=False)
    save_table(
        sector_sorted[['sector_name', 'tag_pct', 'ci_low', 'ci_high', 'n']],
        f"sector_tag_rates_{flag_name}",
        f"{flag_name} tagging rate by sector with 95% CI. Produced by correlation_analysis.py"
    )
    
    fig, ax = plt.subplots()
    ax.barh(
        y=np.arange(len(sector_sorted)),
        width=sector_sorted['tag_pct'],
        xerr=[sector_sorted['tag_pct'] - sector_sorted['ci_low'], sector_sorted['ci_high'] - sector_sorted['tag_pct']],
        capsize=4, color='skyblue'
    )
    # Add vertical line for sample average
    sector_sample_avg = sector_valid[flag_col].mean() * 100
    ax.axvline(x=sector_sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax.set_yticks(np.arange(len(sector_sorted)))
    ax.set_yticklabels(sector_sorted['sector_name'])
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, None)
    plt.tight_layout()
    save_figure(f"sector_tag_rates_{flag_name}", f"{flag_name} tag rate by sector (horizontal bar chart). Produced by correlation_analysis.py", fig)
    
    return len(sector_valid), float(sector_valid[flag_col].mean() * 100)

def analyze_flag_by_year(df, flag_col, flag_name):
    """Generate year analysis for a flag variable"""
    # Create descriptive y-axis label based on flag type
    if flag_name == 'llm':
        ylabel = "LLM Flagged as Collusive (%)"
    elif flag_name == 'llm_validation':
        ylabel = "LLM Flagged and Validated as Collusive (%)"
    elif flag_name == 'human_audit':
        ylabel = "LLM Flagged, Validated, and Human Audited as Collusive (%)"
    else:
        ylabel = "Tagged as Collusive (%)"
    
    df_year = df[df['transcript_year'] >= 2008].copy()
    # Ensure transcript_year is integer for proper axis labels
    df_year['transcript_year'] = df_year['transcript_year'].astype(int)
    year_stats = (
        df_year.groupby('transcript_year')[flag_col]
        .agg(['mean', 'count', 'sum'])
        .rename(columns={'mean': 'tag_pct', 'count': 'n', 'sum': 'num_hits'})
        .reset_index()
    )
    year_stats['tag_pct'] *= 100
    year_stats[['ci_low', 'ci_high']] = year_stats.apply(
        lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
    )
    save_table(
        year_stats[['transcript_year', 'tag_pct', 'ci_low', 'ci_high', 'n']],
        f"year_tag_rates_{flag_name}",
        f"{flag_name} tagging rate by fiscal year with 95% CI. Produced by correlation_analysis.py"
    )
    
    fig, ax = plt.subplots()
    ax.errorbar(
        year_stats['transcript_year'],
        year_stats['tag_pct'],
        yerr=[year_stats['tag_pct'] - year_stats['ci_low'], year_stats['ci_high'] - year_stats['tag_pct']],
        fmt='o-', capsize=4
    )
    # Add horizontal line for sample average
    year_sample_avg = df_year[flag_col].mean() * 100
    ax.axhline(y=year_sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, None)
    # Set x-axis to show only integer years and rotate to prevent overlap
    ax.set_xticks(year_stats['transcript_year'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    save_figure(f"year_tag_rates_{flag_name}", f"{flag_name} tag rate by year. Produced by correlation_analysis.py", fig)
    
    return len(df_year), float(df_year[flag_col].mean() * 100)


#%%
# Load and prepare data
data_path = Path("data/datasets/main_analysis_dataset.feather")
df = pd.read_feather(data_path)

# Create clean flag variables (treat NAs as False)
df['llm_flag_clean'] = df['llm_flag']  # Already clean
df['llm_validation_flag_clean'] = df['llm_validation_flag'].fillna(False).astype(bool)
df['human_audit_flag_clean'] = df['human_audit_flag'].fillna(False).astype(bool)

# Prepare other variables
df['log_market_value'] = np.log(df['market_value_total_mil'].replace(0, np.nan))
df['sector'] = df['gics_sector'].astype('category')
df['year'] = df['transcript_year'].astype('category')

# Load GICS sector mapping
with open(Path("assets/gics_sectors.yaml"), "r") as f:
    gics_sectors = yaml.safe_load(f)

#%%
# Define flag variables to analyze
flag_configs = [
    {'col': 'llm_flag_clean', 'name': 'llm', 'display_name': 'LLM'},
    {'col': 'llm_validation_flag_clean', 'name': 'llm_validation', 'display_name': 'LLM Validation'},
    {'col': 'human_audit_flag_clean', 'name': 'human_audit', 'display_name': 'Human Audit'}
]

#%%
# Summary statistics for all flag variables
benchmark_df = df[df['benchmark_sample'] == 1]

# Statistics for non-missing observations by analysis dimension
sector_valid = df[df['gics_sector'].notna()]
year_valid = df[df['transcript_year'].notna()]
mkvalt_valid = df[df['market_value_total_mil'].notna()]

summary_stats = {
    'total_transcripts': len(df),
    
    # Benchmark sample stats
    'benchmark_sample': int(df['benchmark_sample'].sum()),
    'benchmark_human_tagged_collusive': int(df['benchmark_human_flag'].sum()),
    'benchmark_human_tagged_collusive_pct': float(df['benchmark_human_flag'].mean() * 100),
    
    # Non-missing observations statistics by analysis dimension
    'sector_valid_observations': len(sector_valid),
    'year_valid_observations': len(year_valid),
    'mkvalt_valid_observations': len(mkvalt_valid),
    
    # Missing observations statistics
    'sector_missing_observations': int(df['gics_sector'].isna().sum()),
    'year_missing_observations': int(df['transcript_year'].isna().sum()),
    'mkvalt_missing_observations': int(df['market_value_total_mil'].isna().sum()),
}

# Add statistics for each flag variable
for flag_config in flag_configs:
    col = flag_config['col']
    name = flag_config['name']
    
    # Overall statistics
    summary_stats[f'{name}_tagged_collusive'] = int(df[col].sum())
    summary_stats[f'{name}_tagged_collusive_pct'] = float(df[col].mean() * 100)
    
    # Benchmark sample statistics (for flags that have benchmark data)
    if name == 'llm':
        summary_stats[f'benchmark_{name}_tagged_collusive'] = int(benchmark_df[col].sum())
        summary_stats[f'benchmark_{name}_tagged_collusive_pct'] = float(benchmark_df[col].mean() * 100)
    
    # Tag rates for valid observations by analysis dimension
    summary_stats[f'sector_valid_{name}_tag_rate'] = float(sector_valid[col].mean() * 100)
    summary_stats[f'year_valid_{name}_tag_rate'] = float(year_valid[col].mean() * 100)
    summary_stats[f'mkvalt_valid_{name}_tag_rate'] = float(mkvalt_valid[col].mean() * 100)
    
    # Tag rates for missing observations
    summary_stats[f'mkvalt_missing_{name}_tag_rate'] = float(df[df['market_value_total_mil'].isna()][col].mean() * 100)

# Save summary statistics
with open(yaml_dir / "correlates_collusive_communication.yaml", "w") as f:
    yaml.dump(summary_stats, f)

#%%
# Generate analysis for each flag variable
for flag_config in flag_configs:
    col = flag_config['col']
    name = flag_config['name']
    display_name = flag_config['display_name']
    
    print(f"\nAnalyzing {display_name} flag ({col})...")
    
    # Market value decile analysis
    analyze_flag_by_market_value(df, col, name)
    
    # Sector analysis
    analyze_flag_by_sector(df, col, name, gics_sectors)
    
    # Year analysis  
    analyze_flag_by_year(df, col, name)
    
    print(f"Completed analysis for {display_name} flag")
