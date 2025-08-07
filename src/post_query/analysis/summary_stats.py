"""
Comprehensive summary statistics for the main analysis dataset.

Produces organized summary statistics covering transcript details, company characteristics,
temporal coverage, and LLM/human tagging performance. Outputs structured YAML for use
in LaTeX documents via \\data{} commands.

Output Files Created:
- data/yaml/summary_stats.yaml: Structured statistics for LaTeX \\data{} commands
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
yaml_dir = Path("data/yaml")
yaml_dir.mkdir(parents=True, exist_ok=True)

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
llm_validation_rate_overall = llm_validation_tagged / n_transcripts * 100

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

# LLM flagged statistics by human tagging (benchmark sample only)
# Collusive transcripts in benchmark that are LLM flagged
benchmark_collusive_flagged_count = int(benchmark_collusive['llm_flag'].sum()) if len(benchmark_collusive) > 0 else 0
benchmark_collusive_flagged_pct = (benchmark_collusive_flagged_count / len(benchmark_collusive) * 100) if len(benchmark_collusive) > 0 else 0

# Non-collusive transcripts in benchmark that are LLM flagged
benchmark_not_collusive_flagged_count = int(benchmark_not_collusive['llm_flag'].sum()) if len(benchmark_not_collusive) > 0 else 0
benchmark_not_collusive_flagged_pct = (benchmark_not_collusive_flagged_count / len(benchmark_not_collusive) * 100) if len(benchmark_not_collusive) > 0 else 0

# Odds ratio of flagging probability for collusive vs non-collusive
collusive_flagged_prob = benchmark_collusive_flagged_pct / 100
not_collusive_flagged_prob = benchmark_not_collusive_flagged_pct / 100
benchmark_flagged_odds_ratio = (
    (collusive_flagged_prob / (1 - collusive_flagged_prob)) / 
    (not_collusive_flagged_prob / (1 - not_collusive_flagged_prob))
) if not_collusive_flagged_prob > 0 and not_collusive_flagged_prob < 1 and collusive_flagged_prob < 1 else None

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
        'llm_validation_rate_overall_sample_pct': float(llm_validation_rate_overall),
        'human_audit_sample_count': int(human_audit_sample),
        'human_audit_tagged_count': int(human_audit_tagged),
        'human_audit_rate_pct': float(human_audit_rate),
        'human_audit_false_positive_rate_pct': float(100 - human_audit_rate),
        'benchmark_collusive_validated_count': int(benchmark_collusive_validated_count),
        'benchmark_collusive_validated_pct': float(benchmark_collusive_validated_pct),
        'benchmark_not_collusive_validated_count': int(benchmark_not_collusive_validated_count),
        'benchmark_not_collusive_validated_pct': float(benchmark_not_collusive_validated_pct),
        'benchmark_validation_odds_ratio': float(benchmark_validation_odds_ratio) if benchmark_validation_odds_ratio is not None else None,
        'benchmark_collusive_flagged_count': int(benchmark_collusive_flagged_count),
        'benchmark_collusive_flagged_pct': float(benchmark_collusive_flagged_pct),
        'benchmark_not_collusive_flagged_count': int(benchmark_not_collusive_flagged_count),
        'benchmark_not_collusive_flagged_pct': float(benchmark_not_collusive_flagged_pct),
        'benchmark_flagged_odds_ratio': float(benchmark_flagged_odds_ratio) if benchmark_flagged_odds_ratio is not None else None
    }
}

#%%
# === SAVE YAML OUTPUT ===
yaml_path = yaml_dir / "summary_stats.yaml"
with open(yaml_path, 'w') as f:
    yaml.dump(summary_stats, f, default_flow_style=False, sort_keys=False)

print(f"\nSummary statistics saved to:")
print(f"  YAML: {yaml_path}")

print(f"\nKey Statistics:")
print(f"  Transcripts: {n_transcripts:,}")
print(f"  Companies: {n_companies:,}")
print(f"  Date Range: {date_range_years:.1f} years")
print(f"  LLM Tagged: {llm_tagged:,} ({llm_tag_rate:.2f}%)")
print(f"  Benchmark Sample: {benchmark_sample:,} ({benchmark_rate:.2f}%)")
