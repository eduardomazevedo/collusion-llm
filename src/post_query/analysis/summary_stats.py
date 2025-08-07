"""
Comprehensive summary statistics for the main analysis dataset.

Produces organized summary statistics covering transcript details, company characteristics,
temporal coverage, and LLM/human tagging performance. Outputs both structured YAML and
formatted tables following project specifications.

Output Files Created:
- data/yaml/summary_stats.yaml: Structured statistics for LaTeX \\data{} commands
- data/outputs/tables/summary_stats.*: Summary statistics table (CSV, LaTeX, description)
"""

#%%
import config
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime

#%%
# Setup paths
output_dir = Path("data/outputs")
table_dir = output_dir / "tables"  
yaml_dir = Path("data/yaml")
for path in [table_dir, yaml_dir]:
    path.mkdir(parents=True, exist_ok=True)

def save_table(df, name, description):
    """Save table in CSV and LaTeX formats with description file."""
    csv_path = table_dir / f"{name}.csv"
    tex_path = table_dir / f"{name}.tex"
    df.to_csv(csv_path, index=False)
    
    # Create LaTeX-safe version of the dataframe
    df_latex = df.copy()
    for col in df_latex.columns:
        if df_latex[col].dtype == 'object':
            df_latex[col] = df_latex[col].astype(str).str.replace('%', r'\%', regex=False)
            df_latex[col] = df_latex[col].str.replace('$', r'\$', regex=False)
            df_latex[col] = df_latex[col].str.replace('&', r'\&', regex=False)
            df_latex[col] = df_latex[col].str.replace('#', r'\#', regex=False)
            df_latex[col] = df_latex[col].str.replace('_', r'\_', regex=False)
    
    df_latex.to_latex(tex_path, index=False, float_format="%.2f", longtable=True, escape=False)
    with open(table_dir / f"{name}.txt", "w") as f:
        f.write(description)

#%%
# Load main analysis dataset
df = pd.read_feather("data/datasets/main_analysis_dataset.feather")
print(f"Loaded main analysis dataset with {len(df):,} transcripts")

#%%
# === BASIC TRANSCRIPT STATISTICS ===
n_transcripts = len(df)
n_companies = df['companyid'].nunique()
n_unique_events = df['keydevid'].nunique()

# Date range analysis
df['date'] = pd.to_datetime(df['mostimportantdateutc'])
first_date = df['date'].min()
last_date = df['date'].max()
date_range_years = (last_date - first_date).days / 365.25

# Audio length statistics (excluding missing values)
audio_stats = df['audiolengthsec'].describe()
total_audio_hours = df['audiolengthsec'].sum() / 3600
total_audio_days = total_audio_hours / 24
total_audio_years = total_audio_days / 365.25

# Mean audio length in readable format
mean_audio_seconds = df['audiolengthsec'].mean()
mean_audio_minutes = int(mean_audio_seconds // 60)
mean_audio_seconds_remainder = int(mean_audio_seconds % 60)

#%%
# === TEMPORAL COVERAGE ===
year_coverage = df['transcript_year'].agg(['min', 'max', 'nunique'])
transcripts_by_year = df.groupby('transcript_year').size()
avg_transcripts_per_year = transcripts_by_year.mean()

#%%
# === COMPANY CHARACTERISTICS ===
# Market value statistics (excluding missing)
mv_valid = df['market_value_total_mil'].dropna()
n_companies_with_mv = mv_valid.groupby(df.loc[mv_valid.index, 'companyid']).size().shape[0]
mv_stats = mv_valid.describe()

# Employee statistics (excluding missing)  
emp_valid = df['employees_thousands'].dropna()
n_companies_with_emp = emp_valid.groupby(df.loc[emp_valid.index, 'companyid']).size().shape[0]
emp_stats = emp_valid.describe()

# Sector coverage
sector_coverage = df['gics_sector'].value_counts()
n_sectors = df['gics_sector'].nunique()

# Country coverage
country_coverage = df['incorporation_country'].value_counts()
n_countries = df['incorporation_country'].nunique()

#%%
# === LLM AND HUMAN TAGGING STATISTICS ===
# Overall tagging rates
llm_tagged = df['llm_flag'].sum()
llm_tag_rate = llm_tagged / n_transcripts * 100

# Benchmark sample statistics
benchmark_sample = df['benchmark_sample'].sum()
benchmark_rate = benchmark_sample / n_transcripts * 100

# Human benchmark tagging (only for benchmark sample)
benchmark_df = df[df['benchmark_sample'] == True]
human_tagged_benchmark = benchmark_df['benchmark_human_flag'].sum()
human_benchmark_rate = human_tagged_benchmark / len(benchmark_df) * 100 if len(benchmark_df) > 0 else 0

# LLM validation statistics
llm_validation_available = df['llm_validation_flag'].notna().sum()
llm_validation_tagged = df['llm_validation_flag'].sum()
llm_validation_rate = llm_validation_tagged / llm_validation_available * 100 if llm_validation_available > 0 else 0

# Human audit statistics
human_audit_sample = df['human_audit_sample'].sum()
human_audit_available = df['human_audit_flag'].notna().sum()
human_audit_tagged = df['human_audit_flag'].sum()
human_audit_rate = human_audit_tagged / human_audit_available * 100 if human_audit_available > 0 else 0

# Agreement statistics (benchmark sample only)
benchmark_both_available = benchmark_df[
    benchmark_df['benchmark_human_flag'].notna() & 
    benchmark_df['llm_flag'].notna()
]

# Benchmark validation statistics by human tagging
# Collusive transcripts in benchmark that are LLM validated
benchmark_collusive = benchmark_df[benchmark_df['benchmark_human_flag'] == True]
benchmark_collusive_validated_count = int(benchmark_collusive['llm_validation_flag'].sum()) if len(benchmark_collusive) > 0 else 0
benchmark_collusive_validated_pct = (benchmark_collusive_validated_count / len(benchmark_collusive) * 100) if len(benchmark_collusive) > 0 else 0

# Non-collusive transcripts in benchmark that are LLM validated  
benchmark_not_collusive = benchmark_df[benchmark_df['benchmark_human_flag'] == False]
benchmark_not_collusive_validated_count = int(benchmark_not_collusive['llm_validation_flag'].sum()) if len(benchmark_not_collusive) > 0 else 0
benchmark_not_collusive_validated_pct = (benchmark_not_collusive_validated_count / len(benchmark_not_collusive) * 100) if len(benchmark_not_collusive) > 0 else 0

# Odds ratio of validation probability for collusive vs non-collusive
collusive_validation_prob = benchmark_collusive_validated_pct / 100
not_collusive_validation_prob = benchmark_not_collusive_validated_pct / 100
benchmark_validation_odds_ratio = (
    (collusive_validation_prob / (1 - collusive_validation_prob)) / 
    (not_collusive_validation_prob / (1 - not_collusive_validation_prob))
) if not_collusive_validation_prob > 0 and not_collusive_validation_prob < 1 and collusive_validation_prob < 1 else None

#%%
# === CREATE STRUCTURED YAML OUTPUT ===
summary_stats = {
    'dataset_overview': {
        'total_transcripts': int(n_transcripts),
        'unique_companies': int(n_companies),
        'unique_events': int(n_unique_events),
        'date_range_years': float(date_range_years),
        'first_date': first_date.strftime('%Y-%m-%d'),
        'last_date': last_date.strftime('%Y-%m-%d')
    },
    
    'temporal_coverage': {
        'year_range_start': int(year_coverage['min']),
        'year_range_end': int(year_coverage['max']),
        'years_covered': int(year_coverage['nunique']),
        'avg_transcripts_per_year': float(avg_transcripts_per_year)
    },
    
    'audio_characteristics': {
        'mean_length_seconds': float(mean_audio_seconds),
        'mean_length_description': f"{mean_audio_minutes} minutes {mean_audio_seconds_remainder} seconds",
        'total_audio_hours': float(total_audio_hours),
        'total_audio_years': float(total_audio_years),
        'audio_available_pct': float(df['audiolengthsec'].notna().mean() * 100)
    },
    
    'company_characteristics': {
        'sectors_covered': int(n_sectors),
        'countries_covered': int(n_countries),
        'companies_with_market_value': int(n_companies_with_mv),
        'companies_with_employees': int(n_companies_with_emp),
        'median_market_value_mil': float(mv_stats['50%']) if len(mv_valid) > 0 else None,
        'median_employees_thousands': float(emp_stats['50%']) if len(emp_valid) > 0 else None
    },
    
    'tagging_performance': {
        'llm_tagged_count': int(llm_tagged),
        'llm_tag_rate_pct': float(llm_tag_rate),
        'benchmark_sample_count': int(benchmark_sample),
        'benchmark_sample_rate_pct': float(benchmark_rate),
        'human_benchmark_tagged_count': int(human_tagged_benchmark),
        'human_benchmark_rate_pct': float(human_benchmark_rate),
        'llm_validation_available': int(llm_validation_available),
        'llm_validation_tagged': int(llm_validation_tagged),
        'llm_validation_rate_pct': float(llm_validation_rate),
        'human_audit_sample_count': int(human_audit_sample),
        'human_audit_tagged_count': int(human_audit_tagged),
        'human_audit_rate_pct': float(human_audit_rate),
        'human_audit_false_positive_rate_pct': float(100 - human_audit_rate),
        'benchmark_collusive_validated_count': int(benchmark_collusive_validated_count),
        'benchmark_collusive_validated_pct': float(benchmark_collusive_validated_pct),
        'benchmark_not_collusive_validated_count': int(benchmark_not_collusive_validated_count),
        'benchmark_not_collusive_validated_pct': float(benchmark_not_collusive_validated_pct),
        'benchmark_validation_odds_ratio': float(benchmark_validation_odds_ratio) if benchmark_validation_odds_ratio is not None else None
    }
}

#%%
# === CREATE SUMMARY TABLE ===
summary_table_data = []

# Dataset Overview
summary_table_data.extend([
    ['Dataset Overview', '', ''],
    ['Total Transcripts', f'{n_transcripts:,}', ''],
    ['Unique Companies', f'{n_companies:,}', ''],
    ['Date Range', f'{first_date.strftime("%Y-%m-%d")} to {last_date.strftime("%Y-%m-%d")}', f'{date_range_years:.1f} years'],
    ['', '', ''],
])

# Temporal Coverage
summary_table_data.extend([
    ['Temporal Coverage', '', ''],
    ['Years Covered', f'{year_coverage["min"]} - {year_coverage["max"]}', f'{year_coverage["nunique"]} years'],
    ['Avg Transcripts/Year', f'{avg_transcripts_per_year:.0f}', ''],
    ['', '', ''],
])

# Audio Characteristics  
summary_table_data.extend([
    ['Audio Characteristics', '', ''],
    ['Mean Length', f'{mean_audio_minutes}m {mean_audio_seconds_remainder}s', f'{mean_audio_seconds:.0f} seconds'],
    ['Total Audio Duration', f'{total_audio_years:.1f} years', f'{total_audio_hours:,.0f} hours'],
    ['Audio Available', f'{df["audiolengthsec"].notna().mean()*100:.1f}%', f'{df["audiolengthsec"].notna().sum():,} transcripts'],
    ['', '', ''],
])

# Company Characteristics
summary_table_data.extend([
    ['Company Characteristics', '', ''],
    ['GICS Sectors', f'{n_sectors}', ''],
    ['Countries', f'{n_countries}', ''],
    ['Companies w/ Market Value', f'{n_companies_with_mv:,}', f'{n_companies_with_mv/n_companies*100:.1f}% of companies'],
    ['Median Market Value', f'${mv_stats["50%"]:,.0f}M' if len(mv_valid) > 0 else 'N/A', ''],
    ['Companies w/ Employee Data', f'{n_companies_with_emp:,}', f'{n_companies_with_emp/n_companies*100:.1f}% of companies'],
    ['', '', ''],
])

# Tagging Performance
summary_table_data.extend([
    ['Tagging Performance', '', ''],
    ['LLM Tagged', f'{llm_tagged:,}', f'{llm_tag_rate:.2f}%'],
    ['Benchmark Sample', f'{benchmark_sample:,}', f'{benchmark_rate:.2f}%'],
    ['Human Benchmark Tagged', f'{human_tagged_benchmark:,}', f'{human_benchmark_rate:.1f}% of benchmark'],
    ['LLM Validation Available', f'{llm_validation_available:,}', f'{llm_validation_rate:.1f}% tagged'],
    ['Human Audit Sample', f'{human_audit_sample:,}', f'{human_audit_rate:.1f}% tagged'],
    ['Human Audit False Positive Rate', f'{100 - human_audit_rate:.1f}%', f'{human_audit_sample - human_audit_tagged:,} false positives'],
    ['Benchmark Collusive Validated', f'{benchmark_collusive_validated_count:,}', f'{benchmark_collusive_validated_pct:.1f}% of collusive'],
    ['Benchmark Non-Collusive Validated', f'{benchmark_not_collusive_validated_count:,}', f'{benchmark_not_collusive_validated_pct:.1f}% of non-collusive'],
    ['Validation Odds Ratio', f'{benchmark_validation_odds_ratio:.1f}' if benchmark_validation_odds_ratio is not None else 'N/A', 'Collusive vs Non-Collusive'],
])

summary_table_df = pd.DataFrame(summary_table_data, columns=['Category', 'Value', 'Additional Info'])

#%%
# === SAVE OUTPUTS ===
# Save YAML
yaml_path = yaml_dir / "summary_stats.yaml"
with open(yaml_path, 'w') as f:
    yaml.dump(summary_stats, f, default_flow_style=False, sort_keys=False)

# Save table
save_table(
    summary_table_df,
    "summary_stats",
    "Comprehensive summary statistics for the main analysis dataset including transcript coverage, company characteristics, temporal span, and tagging performance metrics."
)

print(f"\nSummary statistics saved to:")
print(f"  YAML: {yaml_path}")
print(f"  Table: {table_dir}/summary_stats.csv")
print(f"         {table_dir}/summary_stats.tex")

print(f"\nKey Statistics:")
print(f"  Transcripts: {n_transcripts:,}")
print(f"  Companies: {n_companies:,}")
print(f"  Date Range: {date_range_years:.1f} years")
print(f"  LLM Tagged: {llm_tagged:,} ({llm_tag_rate:.2f}%)")
print(f"  Benchmark Sample: {benchmark_sample:,} ({benchmark_rate:.2f}%)")
