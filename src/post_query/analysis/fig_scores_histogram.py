"""
Generate histogram figures for LLM score distributions.

This script creates two figures:
1. Histogram of original score for the entire sample (20 bins)
2. Stacked histogram of mean scores (11 queries) for LLM Flagged samples, split by validation status (50 bins)

Outputs (for each figure, both 1x1 and 16x9 formats, PNG and PDF):
- data/outputs/figures/original_score_entire_sample_*
- data/outputs/figures/mean_score_validated_samples_*
"""

#%%
import config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from modules.colors import GHIBLI_PALETTE

#%%
# Setup paths
OUT_DIR = Path("data/outputs/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

#%%
# Load data
df = pd.read_feather("data/datasets/main_analysis_dataset.feather")
top_transcripts_data_df = pd.read_csv(os.path.join(config.DATA_DIR, 'datasets', 'top_transcripts_data.csv'))

# Merge to get mean_score_ten_repeats
df_with_scores = df.merge(
    top_transcripts_data_df[['transcriptid', 'mean_score_ten_repeats']],
    on='transcriptid',
    how='left'
)

#%%
# Set style
sns.set_style("whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11

#%%
# Define colors for consistency using Ghibli palette
COLORS = {
    'LLM Flagged': GHIBLI_PALETTE['deep_teal'],      # Deep Teal (first priority color)
    'LLM Validated': GHIBLI_PALETTE['warm_red'],     # Warm Red (second priority color)
    'Audit Validated': GHIBLI_PALETTE['green']       # Spirited Meadow (green)
}

#%%
# ============================================================================
# Figure 1: Histogram of original score for entire sample
# ============================================================================

def create_entire_sample_histogram():
    """Create histogram of original scores for entire sample."""
    # Get original scores, excluding NA
    original_scores = df['original_score'].dropna()
    
    for aspect_ratio in ['1x1', '16x9']:
        if aspect_ratio == '1x1':
            figsize = (8, 8)
        else:
            figsize = (12, 6.75)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Create histogram with 20 bins
        ax.hist(original_scores, bins=20, edgecolor='black', alpha=0.7, color=GHIBLI_PALETTE['deep_teal'])
        
        ax.set_xlabel('Original LLM Score', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Add summary statistics
        mean_score = original_scores.mean()
        median_score = original_scores.median()
        ax.axvline(mean_score, color=GHIBLI_PALETTE['red'], linestyle='--', linewidth=2, label=f'Mean: {mean_score:.1f}')
        ax.axvline(median_score, color=GHIBLI_PALETTE['warm_red'], linestyle='--', linewidth=2, label=f'Median: {median_score:.1f}')
        ax.legend()
        
        plt.tight_layout()
        
        # Save PNG and PDF
        for fmt in ['png', 'pdf']:
            filename = f"original_score_entire_sample_{aspect_ratio}.{fmt}"
            filepath = OUT_DIR / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        plt.close()

#%%
# ============================================================================
# Helper: Assign each observation to its smallest group
# ============================================================================

def assign_smallest_group(row):
    """
    Assign each observation to its smallest group.
    Groups are nested: Audit Validated ⊂ LLM Validated ⊂ LLM Flagged
    """
    def is_true(val):
        return pd.notna(val) and bool(val)

    if is_true(row['human_audit_flag']):
        return 'Audit Validated'
    elif is_true(row['llm_validation_flag']):
        return 'LLM Validated'
    elif is_true(row['llm_flag']):
        return 'LLM Flagged Only'
    else:
        return None

#%%
# ============================================================================
# Figure 2: Stacked histogram of mean scores (11 queries) for validated samples
# ============================================================================

def create_validated_samples_mean_histogram():
    """Create stacked histogram of mean scores (11 queries: original + 10 follow-ups), split by smallest group membership."""
    # Get LLM flagged observations with mean_score_ten_repeats
    flagged_df = df_with_scores[df_with_scores['llm_flag'] == True].copy()
    flagged_df = flagged_df[flagged_df['mean_score_ten_repeats'].notna()]
    flagged_df['group'] = flagged_df.apply(assign_smallest_group, axis=1)
    
    # Get counts for legend
    group_counts = flagged_df['group'].value_counts()
    
    for aspect_ratio in ['1x1', '16x9']:
        if aspect_ratio == '1x1':
            figsize = (8, 8)
        else:
            figsize = (12, 6.75)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Define bins - full range for mean scores, 50 bins
        bins = np.linspace(0, 100, 51)  # 50 bins from 0 to 100
        
        # Get scores for each group (in stacking order: bottom to top)
        groups_order = ['LLM Flagged Only', 'LLM Validated', 'Audit Validated']
        colors_order = [
            GHIBLI_PALETTE['deep_teal'],  # Deep Teal (first priority)
            GHIBLI_PALETTE['warm_red'],   # Warm Red (second priority)
            GHIBLI_PALETTE['green']       # Spirited Meadow (green)
        ]
        
        scores_by_group = []
        labels = []
        colors = []
        for group, color in zip(groups_order, colors_order):
            group_scores = flagged_df[flagged_df['group'] == group]['mean_score_ten_repeats'].dropna()
            if len(group_scores) > 0:
                scores_by_group.append(group_scores)
                n = group_counts.get(group, 0)
                labels.append(f'{group} (N={n})')
                colors.append(color)
        
        # Create stacked histogram
        ax.hist(scores_by_group, bins=bins, stacked=True, label=labels, 
               color=colors, edgecolor='black', alpha=0.8)
        
        ax.set_xlabel('Mean LLM Score (11 Queries)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 100)
        
        plt.tight_layout()
        
        # Save PNG and PDF
        for fmt in ['png', 'pdf']:
            filename = f"mean_score_validated_samples_{aspect_ratio}.{fmt}"
            filepath = OUT_DIR / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        plt.close()

#%%
# ============================================================================
# Generate all figures
# ============================================================================

if __name__ == "__main__":
    print("Generating score histogram figures...")
    print("\n1. Entire sample original score histogram...")
    create_entire_sample_histogram()
    
    print("\n2. Validated samples mean score (11 queries) histograms...")
    create_validated_samples_mean_histogram()
    
    print("\nAll figures generated successfully!")
