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
from pathlib import Path
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from modules.colors import GHIBLI_COLORS, apply_ghibli_theme, STYLE_CONFIG

#%%
# Setup paths
OUT_DIR = Path("data/outputs/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

#%%
# Apply Ghibli theme
apply_ghibli_theme()

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
# Define colors for consistency using Ghibli color sequence
# GHIBLI_COLORS: [Red, Teal, Gold, Blue, Green, Gray]
COLORS = {
    'LLM Flagged Only': GHIBLI_COLORS[0],      # Red (primary)
    'LLM Validated': GHIBLI_COLORS[1],         # Deep Teal (secondary)
    'Audit Validated': GHIBLI_COLORS[2]        # Gold (third in theme)
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
                # Add horizontal jitter to make overlapping points more visible
                np.random.seed(42)  # For reproducibility
                jitter = np.random.uniform(-0.5, 0.5, size=len(group_df))
                ax.scatter(
                    group_df['original_score'] + jitter,
                    group_df['mean_score_ten_repeats'],
                    c=COLORS[group],
                    label=f'{group} (N={group_counts.get(group, 0):,})',
                    alpha=0.3
                )
        
        # Add 45-degree line (y = x) for reference
        ax.plot([0, 100], [0, 100], 
               color=STYLE_CONFIG["line_color"], linestyle='--', label='45-degree line')
        
        # Add linear fit
        x_data = flagged_df['original_score'].values
        y_data = flagged_df['mean_score_ten_repeats'].values
        
        # Fit linear polynomial
        coeffs = np.polyfit(x_data, y_data, 1)
        poly = np.poly1d(coeffs)
        
        # Generate smooth line for plotting (extend to full x-axis range)
        x_fit = np.linspace(70, 100, 100)
        y_fit = poly(x_fit)
        
        ax.plot(x_fit, y_fit, 
               color=STYLE_CONFIG["line_color"], label='Linear fit')
        
        ax.set_xlabel('Original LLM Score')
        ax.set_ylabel('Mean LLM Score (11 Queries)')
        ax.set_xlim(70, 100)
        ax.set_ylim(0, 100)  # Full range for y-axis
        ax.legend(loc='lower right', title='Validation Status')
        
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
