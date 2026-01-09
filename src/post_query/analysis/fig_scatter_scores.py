"""
Generate scatter plot comparing original LLM scores to mean scores from 11 queries.

This script creates a scatter plot:
- X-axis: Original LLM Score (75-100 range, since we only have repetition scores for flagged transcripts)
- Y-axis: Mean LLM Score (11 Queries)
- Points colored by smallest validation group: LLM Flagged Only, LLM Validated, Audit Validated

Outputs (both 1x1 and 16x9 formats, PNG and PDF):
- data/outputs/figures/scatter_scores_original_vs_mean_*
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
from scipy.interpolate import UnivariateSpline
from statsmodels.nonparametric.smoothers_lowess import lowess

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
    'LLM Flagged Only': GHIBLI_PALETTE['deep_teal'],  # Deep Teal (first priority color)
    'LLM Validated': GHIBLI_PALETTE['warm_red'],      # Warm Red (second priority color)
    'Audit Validated': GHIBLI_PALETTE['green']        # Spirited Meadow (green)
}

#%%
# ============================================================================
# Helper: Assign each observation to its smallest group
# ============================================================================

def assign_smallest_group(row):
    """
    Assign each observation to its smallest group.
    Groups are nested: Audit Validated ⊂ LLM Validated ⊂ LLM Flagged
    """
    if row['human_audit_flag'] == True:
        return 'Audit Validated'
    elif row['llm_validation_flag'] == True:
        return 'LLM Validated'
    elif row['llm_flag'] == True:
        return 'LLM Flagged Only'
    else:
        return None

#%%
# ============================================================================
# Scatter plot: Original Score vs Mean Score (11 Queries)
# ============================================================================

def create_scatter_scores():
    """Create scatter plot of original score vs mean score from 11 queries (original + 10 follow-ups)."""
    # Get LLM flagged observations with both scores
    flagged_df = df_with_scores[df_with_scores['llm_flag'] == True].copy()
    flagged_df = flagged_df[
        flagged_df['original_score'].notna() & 
        flagged_df['mean_score_ten_repeats'].notna()
    ]
    flagged_df['group'] = flagged_df.apply(assign_smallest_group, axis=1)
    
    # Get counts for legend
    group_counts = flagged_df['group'].value_counts()
    
    for aspect_ratio in ['1x1', '16x9']:
        if aspect_ratio == '1x1':
            figsize = (8, 8)
        else:
            figsize = (12, 6.75)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot points for each group
        groups_order = ['LLM Flagged Only', 'LLM Validated', 'Audit Validated']
        
        for group in groups_order:
            group_df = flagged_df[flagged_df['group'] == group]
            if len(group_df) > 0:
                ax.scatter(
                    group_df['original_score'],
                    group_df['mean_score_ten_repeats'],
                    c=COLORS[group],
                    label=f'{group} (N={group_counts.get(group, 0)})',
                    alpha=0.6,
                    s=50,
                    edgecolors='black',
                    linewidths=0.5
                )
        
        # Add 45-degree line (y = x) for reference
        ax.plot([0, 100], [0, 100], 
               color=GHIBLI_PALETTE['gray'], linestyle='--', linewidth=1.5, alpha=0.5, label='45-degree line')
        
        # Add LOWESS smooth fit
        x_data = flagged_df['original_score'].values
        y_data = flagged_df['mean_score_ten_repeats'].values
        
        # Sort by x for smooth line
        sort_idx = np.argsort(x_data)
        x_sorted = x_data[sort_idx]
        y_sorted = y_data[sort_idx]
        
        # LOWESS smoothing
        smoothed = lowess(y_sorted, x_sorted, frac=0.3)
        ax.plot(smoothed[:, 0], smoothed[:, 1], 
               color=GHIBLI_PALETTE['red'], linewidth=2, alpha=0.7, label='Smooth fit')
        
        ax.set_xlabel('Original LLM Score', fontsize=12)
        ax.set_ylabel('Mean LLM Score (11 Queries)', fontsize=12)
        ax.set_xlim(75, 100)
        ax.set_ylim(0, 100)  # Full range for y-axis
        ax.legend(loc='upper right', title='Validation Status')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save PNG and PDF
        for fmt in ['png', 'pdf']:
            filename = f"scatter_scores_original_vs_mean_{aspect_ratio}.{fmt}"
            filepath = OUT_DIR / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        plt.close()

#%%
# ============================================================================
# Generate figure
# ============================================================================

if __name__ == "__main__":
    print("Generating scatter plot of original vs mean scores...")
    create_scatter_scores()
    print("\nFigure generated successfully!")

