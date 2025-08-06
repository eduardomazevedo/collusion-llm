"""
Basic stats of LLM collusion detection performance based on benchmark sample and human audit.
"""

#%%
import config
import pandas as pd
import numpy as np
import yaml
from scipy import stats
from modules import queries_db, capiq, llm, utils

def calculate_confidence_interval(successes, trials, confidence=0.95):
    """Calculate confidence interval for a proportion using normal approximation"""
    if trials == 0:
        return (0, 0)
    p = successes / trials
    alpha = 1 - confidence
    z = stats.norm.ppf(1 - alpha/2)
    se = np.sqrt(p * (1 - p) / trials)
    margin = z * se
    return (max(0, p - margin), min(1, p + margin))

# Load main analysis dataset
df = pd.read_feather('data/datasets/main_analysis_dataset.feather')
print(f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns")

#%%
# Filter to LLM-flagged observations
df_filtered = df[df['llm_flag'] == True][['transcriptid', 'benchmark_sample', 'benchmark_human_flag', 'human_audit_flag']]
df_benchmark = df[df['benchmark_sample'] == True]

print(f"LLM-flagged transcripts: {len(df_filtered)}")
print(f"Benchmark sample: {len(df_benchmark)}")

#%%
# Overall dataset statistics
print("=== OVERALL DATASET STATISTICS ===")
print()

total_transcripts = len(df)
total_llm_flagged = df['llm_flag'].sum()
total_benchmark = df['benchmark_sample'].sum()

llm_flagged_pct = (total_llm_flagged / total_transcripts * 100) if total_transcripts > 0 else 0
benchmark_pct = (total_benchmark / total_transcripts * 100) if total_transcripts > 0 else 0

llm_flagged_ci = calculate_confidence_interval(total_llm_flagged, total_transcripts)
benchmark_ci = calculate_confidence_interval(total_benchmark, total_transcripts)

print(f"Total transcripts in dataset: {total_transcripts:,}")
print()

print(f"LLM Flagged Transcripts:")
print(f"  Count: {total_llm_flagged:,}")
print(f"  Percentage of all transcripts: {llm_flagged_pct:.2f}%")
print(f"  95% CI: [{llm_flagged_ci[0]*100:.2f}%, {llm_flagged_ci[1]*100:.2f}%]")
print()

print(f"Benchmark Sample:")
print(f"  Count: {total_benchmark:,}")
print(f"  Percentage of all transcripts: {benchmark_pct:.2f}%")
print(f"  95% CI: [{benchmark_ci[0]*100:.2f}%, {benchmark_ci[1]*100:.2f}%]")

#%%
# Summary statistics for LLM-flagged transcripts
print("=== SUMMARY STATISTICS FOR LLM-FLAGGED TRANSCRIPTS ===")
print()

# Benchmark sample probability
total_llm_flagged = len(df_filtered)
benchmark_observations = df_filtered['benchmark_sample'].sum()
benchmark_prob = (benchmark_observations / total_llm_flagged * 100) if total_llm_flagged > 0 else 0
benchmark_ci = calculate_confidence_interval(benchmark_observations, total_llm_flagged)

print(f"Benchmark Sample Probability:")
print(f"  Probability LLM-flagged transcript is in benchmark: {benchmark_prob:.1f}%")
print(f"  95% CI: [{benchmark_ci[0]*100:.1f}%, {benchmark_ci[1]*100:.1f}%]")
print()

# Human audit statistics
human_audit_observations = df_filtered['human_audit_flag'].notna().sum()
human_audit_true = df_filtered['human_audit_flag'].sum()
human_audit_pct = (human_audit_true / human_audit_observations * 100) if human_audit_observations > 0 else 0
human_audit_ci = calculate_confidence_interval(human_audit_true, human_audit_observations)

print(f"Human Audit:")
print(f"  Total observations with human audit: {human_audit_observations}")
print(f"  Human audit = True: {human_audit_true} ({human_audit_pct:.1f}%)")
print(f"  95% CI: [{human_audit_ci[0]*100:.1f}%, {human_audit_ci[1]*100:.1f}%]")
print()

# Benchmark sample statistics
benchmark_human_true = df_filtered[df_filtered['benchmark_sample'] == True]['benchmark_human_flag'].sum()
benchmark_human_pct = (benchmark_human_true / benchmark_observations * 100) if benchmark_observations > 0 else 0
benchmark_human_ci = calculate_confidence_interval(benchmark_human_true, benchmark_observations)

print(f"Benchmark Sample:")
print(f"  Total observations in benchmark sample: {benchmark_observations}")
print(f"  Benchmark human flag = True: {benchmark_human_true} ({benchmark_human_pct:.1f}%)")
print(f"  95% CI: [{benchmark_human_ci[0]*100:.1f}%, {benchmark_human_ci[1]*100:.1f}%]")
print()

# LLM tagged + Human audit true -> Benchmark probability
llm_human_audit_true = df_filtered['human_audit_flag'].sum()
llm_human_audit_true_in_benchmark = df_filtered[(df_filtered['human_audit_flag'] == True) & (df_filtered['benchmark_sample'] == True)].shape[0]
llm_human_audit_benchmark_prob = (llm_human_audit_true_in_benchmark / llm_human_audit_true * 100) if llm_human_audit_true > 0 else 0
llm_human_audit_benchmark_ci = calculate_confidence_interval(llm_human_audit_true_in_benchmark, llm_human_audit_true)

print(f"LLM Tagged + Human Audit True -> Benchmark:")
print(f"  Total LLM-tagged with true human audit: {llm_human_audit_true}")
print(f"  Also in benchmark sample: {llm_human_audit_true_in_benchmark} ({llm_human_audit_benchmark_prob:.1f}%)")
print(f"  95% CI: [{llm_human_audit_benchmark_ci[0]*100:.1f}%, {llm_human_audit_benchmark_ci[1]*100:.1f}%]")

#%%
# Reverse analysis: LLM tagging given human ratings
print("=== REVERSE ANALYSIS: LLM TAGGING GIVEN HUMAN RATINGS ===")
print()

# Human true -> LLM tagged
human_true_total = df_benchmark['benchmark_human_flag'].sum()
human_true_llm_tagged = df_benchmark[(df_benchmark['benchmark_human_flag'] == True) & (df_benchmark['llm_flag'] == True)].shape[0]
human_true_llm_prob = (human_true_llm_tagged / human_true_total * 100) if human_true_total > 0 else 0
human_true_llm_ci = calculate_confidence_interval(human_true_llm_tagged, human_true_total)

print(f"Human True -> LLM Tagged:")
print(f"  Total transcripts tagged as true by humans: {human_true_total}")
print(f"  LLM also tagged: {human_true_llm_tagged} ({human_true_llm_prob:.1f}%)")
print(f"  95% CI: [{human_true_llm_ci[0]*100:.1f}%, {human_true_llm_ci[1]*100:.1f}%]")
print()

# Human false -> LLM tagged
human_false_total = (df_benchmark['benchmark_human_flag'] == False).sum()
human_false_llm_tagged = df_benchmark[(df_benchmark['benchmark_human_flag'] == False) & (df_benchmark['llm_flag'] == True)].shape[0]
human_false_llm_prob = (human_false_llm_tagged / human_false_total * 100) if human_false_total > 0 else 0
human_false_llm_ci = calculate_confidence_interval(human_false_llm_tagged, human_false_total)

print(f"Human False -> LLM Tagged:")
print(f"  Total transcripts tagged as false by humans: {human_false_total}")
print(f"  LLM still tagged: {human_false_llm_tagged} ({human_false_llm_prob:.1f}%)")
print(f"  95% CI: [{human_false_llm_ci[0]*100:.1f}%, {human_false_llm_ci[1]*100:.1f}%]")

#%%
# Save statistics to YAML file
print("\n=== SAVING STATISTICS TO YAML ===")

def safe_convert(value):
    """Convert numpy/pandas types to standard Python types"""
    if hasattr(value, 'item'):
        return value.item()
    elif isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    else:
        return value

stats_yaml = {
    'overall_dataset_statistics': {
        'total_transcripts': safe_convert(total_transcripts),
        'llm_flagged': {
            'count': safe_convert(total_llm_flagged),
            'percentage': round(float(llm_flagged_pct), 2),
            'confidence_interval_95': {
                'lower': round(float(llm_flagged_ci[0]) * 100, 2),
                'upper': round(float(llm_flagged_ci[1]) * 100, 2)
            }
        },
        'benchmark_sample': {
            'count': safe_convert(total_benchmark),
            'percentage': round(float(benchmark_pct), 2),
            'confidence_interval_95': {
                'lower': round(float(benchmark_ci[0]) * 100, 2),
                'upper': round(float(benchmark_ci[1]) * 100, 2)
            }
        }
    },
    'llm_flagged_transcript_analysis': {
        'total_llm_flagged': safe_convert(total_llm_flagged),
        'benchmark_sample_probability': {
            'percentage': round(float(benchmark_prob), 1),
            'count': safe_convert(benchmark_observations),
            'confidence_interval_95': {
                'lower': round(float(benchmark_ci[0]) * 100, 1),
                'upper': round(float(benchmark_ci[1]) * 100, 1)
            }
        },
        'human_audit': {
            'total_observations': safe_convert(human_audit_observations),
            'true_count': safe_convert(human_audit_true),
            'true_percentage': round(float(human_audit_pct), 1),
            'confidence_interval_95': {
                'lower': round(float(human_audit_ci[0]) * 100, 1),
                'upper': round(float(human_audit_ci[1]) * 100, 1)
            }
        },
        'benchmark_sample_validation': {
            'total_observations': safe_convert(benchmark_observations),
            'human_flag_true_count': safe_convert(benchmark_human_true),
            'human_flag_true_percentage': round(float(benchmark_human_pct), 1),
            'confidence_interval_95': {
                'lower': round(float(benchmark_human_ci[0]) * 100, 1),
                'upper': round(float(benchmark_human_ci[1]) * 100, 1)
            }
        },
        'llm_human_audit_benchmark_overlap': {
            'llm_human_audit_true_total': safe_convert(llm_human_audit_true),
            'also_in_benchmark_count': safe_convert(llm_human_audit_true_in_benchmark),
            'also_in_benchmark_percentage': round(float(llm_human_audit_benchmark_prob), 1),
            'confidence_interval_95': {
                'lower': round(float(llm_human_audit_benchmark_ci[0]) * 100, 1),
                'upper': round(float(llm_human_audit_benchmark_ci[1]) * 100, 1)
            }
        }
    },
    'reverse_analysis_human_to_llm': {
        'human_true_to_llm_tagged': {
            'human_true_total': safe_convert(human_true_total),
            'llm_also_tagged_count': safe_convert(human_true_llm_tagged),
            'llm_also_tagged_percentage': round(float(human_true_llm_prob), 1),
            'confidence_interval_95': {
                'lower': round(float(human_true_llm_ci[0]) * 100, 1),
                'upper': round(float(human_true_llm_ci[1]) * 100, 1)
            }
        },
        'human_false_to_llm_tagged': {
            'human_false_total': safe_convert(human_false_total),
            'llm_still_tagged_count': safe_convert(human_false_llm_tagged),
            'llm_still_tagged_percentage': round(float(human_false_llm_prob), 1),
            'confidence_interval_95': {
                'lower': round(float(human_false_llm_ci[0]) * 100, 1),
                'upper': round(float(human_false_llm_ci[1]) * 100, 1)
            }
        }
    }
}

# Save to YAML file
output_path = 'data/yaml/llm_tagged_stats.yaml'
with open(output_path, 'w') as f:
    yaml.dump(stats_yaml, f, default_flow_style=False, sort_keys=False, indent=2)

print(f"Statistics saved to: {output_path}")
# %%
