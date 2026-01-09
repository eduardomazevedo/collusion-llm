#%%
"""
LLM Collusion Tagging Analysis - Other Correlates

This script analyzes collusion tagging behavior across three flag variables by:
- Calculating summary statistics and saving to YAML for llm_flag, llm_validation_flag, and human_audit_flag
- Creating tables of tag rates by market value and year for each flag variable
- Generating corresponding figures (PDF + PNG, 1:1 and 16:9) for each flag variable
- Analyzing industry-specific samples (Chemicals, Construction, Cement)
- Creating LLM score histograms
- Treating NA values in validation and audit flags as False (not flagged)
"""

#%%
import config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from statsmodels.stats.proportion import proportion_confint
from pathlib import Path
import yaml
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from modules.colors import GHIBLI_PALETTE

#%%
# Paths
output_dir = Path("data/outputs")
figure_dir = output_dir / "figures"
table_dir = output_dir / "tables"
yaml_dir = Path("data/yaml")
for path in [figure_dir, table_dir, yaml_dir]:
    path.mkdir(parents=True, exist_ok=True)

#%%
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

def save_table(
    df,
    name,
    description,
    latex_column_rename=None,
    escape=True,
    latex_cell_transform=None
):
    csv_path = table_dir / f"{name}.csv"
    tex_path = table_dir / f"{name}.tex"
    df.to_csv(csv_path, index=False)
    if latex_cell_transform:
        latex_df = df.copy()
        for col, fn in latex_cell_transform.items():
            if col in latex_df.columns:
                latex_df[col] = latex_df[col].map(fn)
    else:
        latex_df = df.copy()
    if latex_column_rename:
        latex_df = latex_df.rename(columns=latex_column_rename)
    latex_df.to_latex(
        tex_path,
        index=False,
        float_format="%.2f",
        longtable=True,
        escape=escape
    )
    with open(table_dir / f"{name}.txt", "w") as f:
        f.write(description)

def save_score_histogram(scores, name, description, bins=20, threshold=None):
    if scores.empty:
        print(f"Skipping histogram {name}: no scores available.")
        return
    fig, ax = plt.subplots()
    ax.hist(scores, bins=bins, color=GHIBLI_PALETTE['deep_teal'], edgecolor="white")
    if threshold is not None:
        ax.axvline(threshold, color=GHIBLI_PALETTE['red'], linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlabel("Score")
    ax.set_ylabel("Count")
    plt.tight_layout()
    save_figure(name, description, fig)

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
    return f"[{left}, {right}{closing}"

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
        'bin': labels,
        'count': counts.astype(int)
    })
    return table_df

def make_one_point_bins(scores):
    if scores.empty:
        return np.array([])
    min_score = int(np.floor(scores.min()))
    max_score = int(np.ceil(scores.max()))
    return np.arange(min_score, max_score + 2, 1)

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
        f"{flag_name} tagging by market value decile. Produced by correlates_others.py"
    )
    
    # Create figure
    fig, ax = plt.subplots()
    # Calculate error bars, ensuring they're non-negative
    yerr_low = np.maximum(0, mv_stats['tag_pct'] - mv_stats['ci_low'])
    yerr_high = np.maximum(0, mv_stats['ci_high'] - mv_stats['tag_pct'])
    ax.errorbar(
        mv_stats['mv_decile'],
        mv_stats['tag_pct'],
        yerr=[yerr_low, yerr_high],
        fmt='o-', capsize=4,
        color=GHIBLI_PALETTE['deep_teal']
    )
    # Add horizontal line for sample average
    sample_avg = df_mv[flag_col].mean() * 100
    ax.axhline(y=sample_avg, color=GHIBLI_PALETTE['red'], linestyle='--', linewidth=1, alpha=0.7)
    ax.set_xlabel("Market Value Decile")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, None)
    save_figure(f"market_value_deciles_{flag_name}", f"{flag_name} tag rate by market value decile. Produced by correlates_others.py", fig)
    
    return len(df_mv), float(df_mv[flag_col].mean() * 100)

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
        f"{flag_name} tagging rate by fiscal year with 95% CI. Produced by correlates_others.py"
    )
    
    fig, ax = plt.subplots()
    # Calculate error bars, ensuring they're non-negative
    yerr_low = np.maximum(0, year_stats['tag_pct'] - year_stats['ci_low'])
    yerr_high = np.maximum(0, year_stats['ci_high'] - year_stats['tag_pct'])
    ax.errorbar(
        year_stats['transcript_year'],
        year_stats['tag_pct'],
        yerr=[yerr_low, yerr_high],
        fmt='o-', capsize=4,
        color=GHIBLI_PALETTE['deep_teal']
    )
    # Add horizontal line for sample average
    year_sample_avg = df_year[flag_col].mean() * 100
    ax.axhline(y=year_sample_avg, color=GHIBLI_PALETTE['red'], linestyle='--', linewidth=1, alpha=0.7)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, None)
    # Set x-axis to show only integer years and rotate to prevent overlap
    ax.set_xticks(year_stats['transcript_year'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    save_figure(f"year_tag_rates_{flag_name}", f"{flag_name} tag rate by year. Produced by correlates_others.py", fig)
    
    return len(df_year), float(df_year[flag_col].mean() * 100)

def analyze_industry_sample(df, sample_mask, industry_name, flag_col, flag_name):
    """
    Analyze collusion flagging rates for a specific industry sample.
    Calculates summary statistics (saved to YAML, no tables generated).
    """
    sample_df = df[sample_mask].copy()
    n_sample = len(sample_df)
    
    if n_sample == 0:
        print(f"Warning: {industry_name} sample has no observations. Skipping analysis.")
        return None, None
    
    # Calculate tag rates
    tag_rate = sample_df[flag_col].mean() * 100
    n_tagged = int(sample_df[flag_col].sum())
    
    return n_sample, tag_rate

#%%
# Load and prepare data
data_path = Path("data/datasets/main_analysis_dataset.feather")
df = pd.read_feather(data_path)

top_transcripts_path = os.path.join(config.DATA_DIR, "datasets", "top_transcripts_data.csv")
top_transcripts_df = pd.read_csv(top_transcripts_path)
print(f"Loaded top transcripts data with {len(top_transcripts_df):,} transcripts")

human_audit_path = os.path.join("assets", "human_audit_top_transcripts.csv")
human_audit_df = pd.read_csv(human_audit_path)

# Create clean flag variables (treat NAs as False)
df['llm_flag_clean'] = df['llm_flag']  # Already clean
df['llm_validation_flag_clean'] = df['llm_validation_flag'].fillna(False).astype(bool)
df['human_audit_flag_clean'] = df['human_audit_flag'].fillna(False).astype(bool)

# Prepare other variables
df['log_market_value'] = np.log(df['market_value_total_mil'].replace(0, np.nan))
df['sector'] = df['gics_sector'].astype('category')
df['year'] = df['transcript_year'].astype('category')

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
    summary_stats[f'year_valid_{name}_tag_rate'] = float(year_valid[col].mean() * 100)
    summary_stats[f'mkvalt_valid_{name}_tag_rate'] = float(mkvalt_valid[col].mean() * 100)
    
    # Tag rates for missing observations
    summary_stats[f'mkvalt_missing_{name}_tag_rate'] = float(df[df['market_value_total_mil'].isna()][col].mean() * 100)

#%%
# LLM score histograms for flagged and validated sets
flagged_scores = top_transcripts_df['original_score'].dropna()
validated_scores = top_transcripts_df.loc[
    top_transcripts_df['mean_score_ten_repeats'].notna() &
    (top_transcripts_df['mean_score_ten_repeats'] >= config.LLM_SCORE_THRESHOLD),
    'mean_score_ten_repeats'
].dropna()

print(f"Creating LLM-flagged score histogram (n={len(flagged_scores):,})...")
save_score_histogram(
    flagged_scores,
    "llm_flagged_score_histogram",
    "Histogram of LLM-flagged scores (original score, score >= threshold). Produced by correlates_others.py",
    threshold=config.LLM_SCORE_THRESHOLD
)

print(f"Creating LLM-validated score histogram (n={len(validated_scores):,})...")
save_score_histogram(
    validated_scores,
    "llm_validated_score_histogram",
    "Histogram of LLM-validated scores (mean of first 10 repeats, first 11 queries). Produced by correlates_others.py",
    threshold=config.LLM_SCORE_THRESHOLD
)

# One-point bin tables for flagged and validated scores
bin_header_map = {
    'bin': 'Bin',
    'count': 'Count'
}
latex_bin_transform = {'bin': lambda s: f"{{{s}}}"}
flagged_bins = make_one_point_bins(flagged_scores)
if len(flagged_bins) > 0:
    flagged_table = make_histogram_table(flagged_scores, bins=flagged_bins)
    save_table(
        flagged_table,
        "llm_flagged_score_bins_1pt",
        "One-point score bin counts for LLM-flagged scores. Produced by correlates_others.py",
        latex_column_rename=bin_header_map,
        escape=False,
        latex_cell_transform=latex_bin_transform
    )

validated_bins = make_one_point_bins(validated_scores)
if len(validated_bins) > 0:
    validated_table = make_histogram_table(validated_scores, bins=validated_bins)
    save_table(
        validated_table,
        "llm_validated_score_bins_1pt",
        "One-point score bin counts for LLM-validated scores. Produced by correlates_others.py",
        latex_column_rename=bin_header_map,
        escape=False,
        latex_cell_transform=latex_bin_transform
    )

# Human audit sample: LLM-validated score histograms and tables
human_audit_scores = top_transcripts_df.loc[
    top_transcripts_df['transcriptid'].isin(human_audit_df['transcript_id']),
    'mean_score_ten_repeats'
].dropna()

if human_audit_scores.empty:
    print("Skipping human audit LLM-validated histograms: no scores available.")
else:
    print(f"Creating human audit LLM-validated score histogram (10 bins) (n={len(human_audit_scores):,})...")
    save_score_histogram(
        human_audit_scores,
        "human_audit_llm_validated_score_histogram_10bins",
        "Histogram of LLM-validated scores for the human audit sample (10 bins). Produced by correlates_others.py",
        bins=10,
        threshold=config.LLM_SCORE_THRESHOLD
    )
    human_audit_table_10 = make_histogram_table(human_audit_scores, bins=10)
    save_table(
        human_audit_table_10,
        "human_audit_llm_validated_score_bins_10",
        "Ten-bin score counts for LLM-validated scores in the human audit sample. Produced by correlates_others.py",
        latex_column_rename=bin_header_map,
        escape=False,
        latex_cell_transform=latex_bin_transform
    )

    print(f"Creating human audit LLM-validated score histogram (20 bins) (n={len(human_audit_scores):,})...")
    save_score_histogram(
        human_audit_scores,
        "human_audit_llm_validated_score_histogram_20bins",
        "Histogram of LLM-validated scores for the human audit sample (20 bins). Produced by correlates_others.py",
        bins=20,
        threshold=config.LLM_SCORE_THRESHOLD
    )
    human_audit_table_20 = make_histogram_table(human_audit_scores, bins=20)
    save_table(
        human_audit_table_20,
        "human_audit_llm_validated_score_bins_20",
        "Twenty-bin score counts for LLM-validated scores in the human audit sample. Produced by correlates_others.py",
        latex_column_rename=bin_header_map,
        escape=False,
        latex_cell_transform=latex_bin_transform
    )

#%%
# Generate analysis for each flag variable (market value and year)
for flag_config in flag_configs:
    col = flag_config['col']
    name = flag_config['name']
    display_name = flag_config['display_name']
    
    print(f"\nAnalyzing {display_name} flag ({col})...")
    
    # Market value decile analysis
    analyze_flag_by_market_value(df, col, name)
    
    # Year analysis  
    analyze_flag_by_year(df, col, name)
    
    print(f"Completed analysis for {display_name} flag")

#%%
# Industry-specific samples: Chemicals, Construction, and Cement
# Uses preferred SIC/NAICS codes when available, falls back to GICS codes if not available
# Definitions:
# - Chemicals: SIC 2800-2899 (preferred) or GICS 151010 (fallback)
# - Construction: SIC 1500-1799 (preferred), NAICS 23* (alternative), or GICS 2010* (fallback)
# - Cement: SIC 3241 (preferred), NAICS 327310 (alternative), or GICS 151020 (fallback, broader than ideal)

# Check available SIC and NAICS codes for industry sample definitions
print("\nChecking available SIC and NAICS codes for industry sample definitions...")
has_sic = 'sic' in df.columns and df['sic'].notna().any()
has_naics = 'naics' in df.columns and df['naics'].notna().any()
print(f"SIC codes available: {has_sic}")
print(f"NAICS codes available: {has_naics}")

if has_sic:
    available_sic = df[df['sic'].notna()]['sic'].unique()
    print(f"Found {len(available_sic)} unique SIC codes")
if has_naics:
    available_naics = df[df['naics'].notna()]['naics'].unique()
    print(f"Found {len(available_naics)} unique NAICS codes")

# Define industry samples using preferred SIC/NAICS codes
# Chemicals: SIC 2800-2899 (Chemicals and Allied Products)
# Alternative: GICS industry 151010 if SIC not available
if has_sic:
    # SIC codes are 4-digit strings, check if they start with "28"
    chemicals_mask = df['sic'].notna() & df['sic'].astype(str).str.startswith('28')
    n_chemicals = chemicals_mask.sum()
    print(f"\nChemicals sample (SIC 2800-2899): {n_chemicals:,} transcripts")
else:
    # Fallback to GICS
    chemicals_mask = df['gics_industry'].notna() & (df['gics_industry'] == '151010')
    n_chemicals = chemicals_mask.sum()
    print(f"\nChemicals sample (GICS 151010, SIC not available): {n_chemicals:,} transcripts")

# Construction: SIC 1500-1799 (Construction contractors)
# SIC 15: General Building Contractors, SIC 16: Heavy Construction, SIC 17: Special Trade Contractors
# Alternative: NAICS starting with 23 if SIC not available
if has_sic:
    # SIC codes starting with "15", "16", or "17"
    construction_mask = df['sic'].notna() & (
        df['sic'].astype(str).str.startswith('15') |
        df['sic'].astype(str).str.startswith('16') |
        df['sic'].astype(str).str.startswith('17')
    )
    n_construction = construction_mask.sum()
    print(f"\nConstruction sample (SIC 1500-1799): {n_construction:,} transcripts")
elif has_naics:
    # Fallback to NAICS starting with 23 (Construction)
    construction_mask = df['naics'].notna() & df['naics'].astype(str).str.startswith('23')
    n_construction = construction_mask.sum()
    print(f"\nConstruction sample (NAICS 23*, SIC not available): {n_construction:,} transcripts")
else:
    # Fallback to GICS
    construction_mask = df['gics_industry'].notna() & df['gics_industry'].astype(str).str.startswith('2010')
    n_construction = construction_mask.sum()
    print(f"\nConstruction sample (GICS 2010*, SIC/NAICS not available): {n_construction:,} transcripts")

# Cement: SIC 3241 (Cement, Hydraulic)
# Alternative: NAICS 327310 if SIC not available
# Warning: Do not use GICS 151020 as it includes glass, sand, timber
if has_sic:
    cement_mask = df['sic'].notna() & (df['sic'].astype(str) == '3241')
    n_cement = cement_mask.sum()
    print(f"\nCement sample (SIC 3241): {n_cement:,} transcripts")
elif has_naics:
    # Fallback to NAICS 327310 (Cement Manufacturing)
    cement_mask = df['naics'].notna() & (df['naics'].astype(str) == '327310')
    n_cement = cement_mask.sum()
    print(f"\nCement sample (NAICS 327310, SIC not available): {n_cement:,} transcripts")
else:
    # Last resort: GICS 151020 (warns user this is broader than ideal)
    cement_mask = df['gics_industry'].notna() & (df['gics_industry'] == '151020')
    n_cement = cement_mask.sum()
    print(f"\nCement sample (GICS 151020, SIC/NAICS not available): {n_cement:,} transcripts")
    print("  WARNING: GICS 151020 is 'Construction Materials' and includes glass, sand, timber - broader than ideal")

# Store industry samples
industry_samples = {
    'chemicals': chemicals_mask,
    'construction': construction_mask,
    'cement': cement_mask
}

#%%
# Analyze each industry sample for each flag variable
industry_summary_stats = {}

for industry_name, sample_mask in industry_samples.items():
    n_total = sample_mask.sum()
    industry_summary_stats[f'{industry_name}_n_transcripts'] = int(n_total)
    
    if n_total == 0:
        print(f"\nSkipping {industry_name} sample: no observations")
        continue
    
    print(f"\n{'='*60}")
    print(f"Analyzing {industry_name.upper()} sample ({n_total:,} transcripts)")
    print(f"{'='*60}")
    
    for flag_config in flag_configs:
        col = flag_config['col']
        name = flag_config['name']
        display_name = flag_config['display_name']
        
        n_sample, tag_rate = analyze_industry_sample(
            df, sample_mask, industry_name, col, name
        )
        
        if n_sample is not None:
            industry_summary_stats[f'{industry_name}_{name}_tag_rate'] = float(tag_rate)
            industry_summary_stats[f'{industry_name}_{name}_n_tagged'] = int(df[sample_mask][col].sum())

# Add industry sample statistics to summary_stats
if industry_summary_stats:
    summary_stats.update(industry_summary_stats)
    print(f"\nAdded industry sample statistics to summary stats")

# Save all summary statistics to YAML (single write at the end)
yaml_path = yaml_dir / "correlates_collusive_communication.yaml"
with open(yaml_path, "w") as f:
    yaml.dump(summary_stats, f)
print(f"\nSaved all summary statistics to {yaml_path}")

print("\n" + "="*60)
print("Completed industry-specific sample analysis")
print("="*60)
