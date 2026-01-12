#%%
"""
LLM Collusion Tagging Analysis - Sector and Segment Correlates

This script analyzes collusion tagging behavior by:
- GICS sectors (level 2)
- High collusion segments (SIC-based)

Uses detailed_industry_results.csv to get structure and LLM flag data.
Creates combined tables and figures with both groups clearly distinguished.
Saves statistics for both to YAML.
"""

#%%
import config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportion_confint
from pathlib import Path
import yaml
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from modules.colors import GHIBLI_COLORS, apply_ghibli_theme, STYLE_CONFIG, ghibli_palette

#%%
# Apply Ghibli theme
apply_ghibli_theme()

#%%
# Paths
output_dir = Path("data/outputs")
figure_dir = output_dir / "figures"
table_dir = output_dir / "tables"
yaml_dir = Path("data/yaml")
for path in [figure_dir, table_dir, yaml_dir]:
    path.mkdir(parents=True, exist_ok=True)

#%%
# Define the high collusion segments
# Format: (segment_name, sic_codes, match_type)
# match_type: 'exact' for exact SIC code match, 'prefix' for codes starting with the prefix
HIGH_COLLUSION_SEGMENTS = [
    ('Cement, Glass & Concrete', ['3241', '321', '327'], 'mixed'),  # 3241 exact, 321/327 prefix
    ('Commodity Chemicals', ['281', '286', '287'], 'prefix'),
    ('Heavy Civil Construction', ['161', '162'], 'prefix'),
    ('Pulp, Paper & Packaging', ['261', '262', '263', '265'], 'prefix'),
    ('Primary Metals', ['331', '332', '333'], 'prefix'),
]

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

def get_gics_sectors(detailed_df):
    """Extract GICS sectors (level 2) from detailed results."""
    sector_df = detailed_df[
        (detailed_df['classification_system'] == 'gics') & 
        (detailed_df['level'] == 2)
    ].copy()
    
    # Ensure codes are strings and zero-padded
    sector_df['code'] = sector_df['code'].astype(str).str.zfill(8)
    
    # Add group_type column
    sector_df['group_type'] = 'GICS Sector'
    
    # Standardize column names for merging
    sector_df['group_name'] = sector_df['name']
    sector_df['tag_pct'] = sector_df['pct_llm_flagged']
    sector_df['n'] = sector_df['n_transcripts']
    sector_df['num_hits'] = sector_df['n_llm_flagged']
    
    return sector_df

def get_high_collusion_segments(detailed_df):
    """Extract high collusion segments from detailed results."""
    # Filter to SIC codes only
    sic_df = detailed_df[detailed_df['classification_system'] == 'sic'].copy()
    
    segment_results = []
    
    for segment_name, sic_codes, match_type in HIGH_COLLUSION_SEGMENTS:
        # Find all matching rows
        all_matches = []
        
        # Handle mixed match type: first code is exact, rest are prefix
        if match_type == 'mixed':
            for i, sic_code in enumerate(sic_codes):
                sic_code_clean = str(sic_code).zfill(4)
                if i == 0:
                    # First code: exact match
                    matches = sic_df[sic_df['code'].astype(str).str.zfill(4) == sic_code_clean]
                else:
                    # Remaining codes: prefix match
                    matches = sic_df[
                        sic_df['code'].astype(str).str.zfill(4).str.startswith(sic_code_clean)
                    ]
                
                if len(matches) > 0:
                    all_matches.append(matches)
        else:
            # Standard handling: all codes use same match type
            for sic_code in sic_codes:
                if match_type == 'exact':
                    # Exact match: SIC code must be exactly this (handle zero-padding)
                    sic_code_clean = str(sic_code).zfill(4)
                    matches = sic_df[sic_df['code'].astype(str).str.zfill(4) == sic_code_clean]
                else:  # prefix
                    # Prefix match: SIC code must start with this prefix
                    sic_code_clean = str(sic_code).zfill(4)
                    matches = sic_df[
                        sic_df['code'].astype(str).str.zfill(4).str.startswith(sic_code_clean)
                    ]
                
                if len(matches) > 0:
                    all_matches.append(matches)
        
        if len(all_matches) == 0:
            print(f"  WARNING: No matches found for {segment_name}")
            continue
        
        # Combine all matches and remove duplicates (same code might appear at different levels)
        combined_matches = pd.concat(all_matches, ignore_index=True)
        
        # Remove duplicates based on code, keeping the most detailed (highest level)
        combined_matches = combined_matches.sort_values('level', ascending=False).drop_duplicates(subset=['code'], keep='first')
        
        # Aggregate results: sum transcripts and flagged counts, recalculate percentage
        total_transcripts = combined_matches['n_transcripts'].sum()
        total_flagged = combined_matches['n_llm_flagged'].sum()
        pct_flagged = (total_flagged / total_transcripts * 100) if total_transcripts > 0 else 0.0
        
        # Get representative classification info (use the one with most transcripts)
        representative = combined_matches.loc[combined_matches['n_transcripts'].idxmax()]
        
        # Create result row
        result_row = {
            'group_name': segment_name,
            'group_type': 'High Collusion Segment',
            'classification_system': 'sic',
            'level': int(representative['level']),
            'code': ', '.join(sic_codes),  # Store SIC codes as string for segments
            'classification_name': representative['name'] if len(combined_matches) == 1 else f"{segment_name} (aggregated)",
            'n': int(total_transcripts),
            'num_hits': int(total_flagged),
            'tag_pct': round(pct_flagged, 2)
        }
        segment_results.append(result_row)
        print(f"  {segment_name}: {total_transcripts:,} transcripts, {total_flagged:,} flagged ({pct_flagged:.2f}%)")
    
    if len(segment_results) == 0:
        return pd.DataFrame()
    
    return pd.DataFrame(segment_results)

def analyze_segments(combined_df, overall_llm_rate=None):
    """
    Generate combined analysis for GICS sectors and high collusion segments.
    Creates table and figure with both groups clearly distinguished.
    
    Parameters:
    -----------
    combined_df : DataFrame
        Combined sectors and segments dataframe
    overall_llm_rate : float, optional
        Overall LLM flag rate from the entire dataset (as percentage). 
        If None, will calculate from sectors weighted by n_transcripts.
    """
    xlabel = "LLM Flagged as Collusive (%)"
    
    # Separate sectors and segments
    sectors = combined_df[combined_df['group_type'] == 'GICS Sector'].copy()
    segments = combined_df[combined_df['group_type'] == 'High Collusion Segment'].copy()
    
    # Sort each group by tag rate (descending)
    sectors = sectors.sort_values("tag_pct", ascending=False).reset_index(drop=True)
    segments = segments.sort_values("tag_pct", ascending=False).reset_index(drop=True)
    
    # Calculate confidence intervals for each group
    sectors[['ci_low', 'ci_high']] = sectors.apply(
        lambda r: proportion_ci(int(r['num_hits']), int(r['n'])), axis=1, result_type='expand'
    )
    segments[['ci_low', 'ci_high']] = segments.apply(
        lambda r: proportion_ci(int(r['num_hits']), int(r['n'])), axis=1, result_type='expand'
    )
    
    # Combine for table (sectors first, then segments)
    combined_sorted = pd.concat([sectors, segments], ignore_index=True)
    
    # Save table
    save_table(
        combined_sorted[['group_type', 'group_name', 'tag_pct', 'ci_low', 'ci_high', 'n']].rename(
            columns={'group_name': 'name'}
        ),
        "segment_tag_rates_llm",
        "LLM tagging rate by sector and high collusion segment with 95% CI. Produced by correlates_segments.py"
    )
    
    # Create figure with separated sections using full-width header bars
    # Note: This figure does NOT follow the standard 1x1 and 16x9 double formatting
    # due to the specific layout requirements with header bars
    fig, ax = plt.subplots(figsize=(10, 9))  # Made taller to accommodate spacing
    
    # Add gap between sections for visual separation
    gap_size = 1.5  # Increased gap for better separation between sections
    
    # Calculate y positions: sectors at top, then gap, then segments
    n_sectors = len(sectors)
    n_segments = len(segments)
    
    # Layout from top to bottom (higher y = higher on plot):
    # - Sector header (highest y)
    # - Sector bars (below header)
    # - Gap
    # - Segment header
    # - Segment bars (below header, lowest y)
    
    # Position segments first (bottom of plot), then gap, then sectors (top)
    segment_y_start = 0
    # Ensure exactly n_segments positions, using linspace to avoid float precision issues
    segment_y_positions = np.linspace(segment_y_start, segment_y_start + n_segments - 1, n_segments) if n_segments > 0 else np.array([])
    
    # Header bar positions - positioned clearly ABOVE their respective sections
    # Segment header: positioned above segment bars with reduced spacing
    header_segment_y = segment_y_start + n_segments + 0.6  # 0.6 spacing above segment bars
    
    # Gap between sections
    sector_y_start = header_segment_y + gap_size
    
    # Sector bars: positioned above the gap
    # Ensure exactly n_sectors positions, using linspace to avoid float precision issues
    sector_y_positions = np.linspace(sector_y_start, sector_y_start + n_sectors - 1, n_sectors) if n_sectors > 0 else np.array([])
    
    # Sector header: positioned above sector bars with reduced spacing
    header_sector_y = sector_y_start + n_sectors + 0.6  # 0.6 spacing above sector bars
    
    # Calculate max x value for proper scaling
    max_tag_rate = 0
    if n_sectors > 0:
        max_tag_rate = max(max_tag_rate, sectors['tag_pct'].max(), sectors['ci_high'].max())
    if n_segments > 0:
        max_tag_rate = max(max_tag_rate, segments['tag_pct'].max(), segments['ci_high'].max())
    x_max = max_tag_rate * 1.15  # Add 15% padding
    
    # Plot header bars (full width, light color background)
    # Increased height to 0.55 (10% taller than 0.5) for better text fit
    if n_sectors > 0:
        ax.barh(header_sector_y, x_max, color=GHIBLI_COLORS[1], alpha=0.3, height=0.55, 
                edgecolor=GHIBLI_COLORS[1], linewidth=1)
    if n_segments > 0:
        ax.barh(header_segment_y, x_max, color=GHIBLI_COLORS[0], alpha=0.3, height=0.55, 
                edgecolor=GHIBLI_COLORS[0], linewidth=1)
    
    # Plot sectors (at top)
    if n_sectors > 0:
        sector_values = sectors['tag_pct']
        sector_ci_low = sectors['ci_low']
        sector_ci_high = sectors['ci_high']
        xerr_low_sectors = np.maximum(0, sector_values - sector_ci_low)
        xerr_high_sectors = np.maximum(0, sector_ci_high - sector_values)
        ax.barh(
            y=sector_y_positions,
            width=sector_values,
            xerr=[xerr_low_sectors, xerr_high_sectors],
            color=GHIBLI_COLORS[1], label='GICS Sector',
            edgecolor=STYLE_CONFIG["edge_color"],
            linewidth=STYLE_CONFIG["edge_width"],
            ecolor=STYLE_CONFIG["error_color"]
        )
    
    # Plot segments (at bottom)
    if n_segments > 0:
        segment_values = segments['tag_pct']
        segment_ci_low = segments['ci_low']
        segment_ci_high = segments['ci_high']
        xerr_low_segments = np.maximum(0, segment_values - segment_ci_low)
        xerr_high_segments = np.maximum(0, segment_ci_high - segment_values)
        ax.barh(
            y=segment_y_positions,
            width=segment_values,
            xerr=[xerr_low_segments, xerr_high_segments],
            color=GHIBLI_COLORS[0], label='High Collusion Segment',
            edgecolor=STYLE_CONFIG["edge_color"],
            linewidth=STYLE_CONFIG["edge_width"],
            ecolor=STYLE_CONFIG["error_color"]
        )
    
    # Add header text centered on header bars
    if n_sectors > 0:
        ax.text(x_max * 0.5, header_sector_y, 'GICS Sectors', fontsize=12, fontweight='bold',
                ha='center', va='center')
    if n_segments > 0:
        ax.text(x_max * 0.5, header_segment_y, 'High Collusion Segments', fontsize=12, fontweight='bold',
                ha='center', va='center')
    
    # Combine all y positions and labels for y-axis
    all_y_positions = np.concatenate([sector_y_positions, segment_y_positions])
    all_labels = list(sectors['group_name']) + list(segments['group_name'])
    
    # Insert header positions with empty string labels (headers are shown as full-width bars)
    if n_sectors > 0:
        all_y_positions = np.insert(all_y_positions, 0, header_sector_y)
        all_labels = [''] + all_labels[:n_sectors] + all_labels[n_sectors:]
    
    if n_segments > 0:
        insert_idx = n_sectors + (1 if n_sectors > 0 else 0)
        all_y_positions = np.insert(all_y_positions, insert_idx, header_segment_y)
        all_labels.insert(insert_idx, '')  # Empty string for header
    
    # Add vertical line for overall average
    # Use provided overall_llm_rate, or calculate as weighted average of sectors only (excluding segments)
    if overall_llm_rate is not None:
        overall_avg = overall_llm_rate
    else:
        # Calculate weighted average from sectors only (weighted by n_transcripts)
        # This represents the overall dataset average since sectors cover all transcripts
        if n_sectors > 0:
            total_transcripts = sectors['n'].sum()
            weighted_sum = (sectors['tag_pct'] * sectors['n']).sum()
            overall_avg = weighted_sum / total_transcripts if total_transcripts > 0 else 0
        else:
            overall_avg = 0
    
    ax.axvline(x=overall_avg, color=STYLE_CONFIG["line_color"], linestyle='--', label='Overall Average')
    
    # Set labels
    ax.set_yticks(all_y_positions)
    ax.set_yticklabels(all_labels)
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, x_max)
    # Set ylim to accommodate header bars at top and all data bars
    # Add spacing at bottom to prevent bars from being glued to axis
    y_min = min(segment_y_positions) - 0.8 if n_segments > 0 else -0.8  # Increased bottom spacing
    y_max = header_sector_y + 0.5 if n_sectors > 0 else (header_segment_y + 0.5 if n_segments > 0 else 0)
    ax.set_ylim(y_min, y_max)
    ax.legend(loc='upper right')
    ax.grid(axis='x')
    plt.tight_layout()
    
    # Save figure - Note: This figure uses a custom size (10x9) and does NOT follow
    # the standard 1x1 and 16x9 double formatting due to the specific layout requirements
    fig.set_size_inches(10, 9)
    path_base = figure_dir / "segment_tag_rates_llm"
    fig.savefig(f"{path_base}.png", dpi=300, bbox_inches='tight')
    fig.savefig(f"{path_base}.pdf", bbox_inches='tight')
    with open(figure_dir / "segment_tag_rates_llm.txt", "w") as f:
        f.write("LLM tag rate by sector and high collusion segment (horizontal bar chart with full-width header bars). Produced by correlates_segments.py. Note: Custom figure size (10x8), not standard 1x1/16x9 format.")
    plt.close(fig)
    
    # Calculate statistics for each group type (sectors and segments already sorted and calculated above)
    sector_stats = {
        'n_total': int(sectors['n'].sum()) if n_sectors > 0 else 0,
        'avg_rate': float(sectors['tag_pct'].mean()) if n_sectors > 0 else 0.0
    }
    segment_stats = {
        'n_total': int(segments['n'].sum()) if n_segments > 0 else 0,
        'avg_rate': float(segments['tag_pct'].mean()) if n_segments > 0 else 0.0
    }
    
    return sector_stats, segment_stats

#%%
# Load detailed industry results
print("Loading detailed industry results...")
detailed_results_path = Path("data/outputs/tables/detailed_industry_results.csv")
detailed_df = pd.read_csv(detailed_results_path)
print(f"Loaded {len(detailed_df):,} industry classification results")

# Ensure codes are strings for matching
detailed_df['code'] = detailed_df['code'].astype(str)

#%%
# Extract GICS sectors
print("\nExtracting GICS sectors...")
sector_df = get_gics_sectors(detailed_df)
print(f"Found {len(sector_df)} GICS sectors")

#%%
# Extract high collusion segments
print("\nExtracting high collusion segments...")
segment_df = get_high_collusion_segments(detailed_df)
print(f"Found {len(segment_df)} high collusion segments")

#%%
# Combine sectors and segments
print("\nCombining sectors and segments...")
combined_df = pd.concat([sector_df, segment_df], ignore_index=True)
print(f"Total groups: {len(combined_df)} ({len(sector_df)} sectors + {len(segment_df)} segments)")

#%%
# Load main dataset to calculate overall LLM flag rate
print("\nLoading main dataset to calculate overall LLM flag rate...")
main_data_path = Path("data/datasets/main_analysis_dataset.feather")
if main_data_path.exists():
    main_df = pd.read_feather(main_data_path)
    # Calculate overall LLM flag rate as percentage
    overall_llm_rate = main_df['llm_flag'].mean() * 100
    print(f"Overall LLM flag rate from main dataset: {overall_llm_rate:.2f}%")
    print(f"Total transcripts in main dataset: {len(main_df):,}")
else:
    print("Warning: Main dataset not found, will calculate overall average from sectors weighted by n_transcripts")
    overall_llm_rate = None

#%%
# Analyze combined data
print("\nAnalyzing combined sectors and segments...")
sector_stats, segment_stats = analyze_segments(combined_df, overall_llm_rate=overall_llm_rate)
print("Completed analysis")

# Get sector rates for healthcare (minimum) and materials (maximum) for LaTeX
healthcare_rate = 0.0
materials_rate = 0.0
if len(sector_df) > 0:
    # Find healthcare and materials sectors (hardcoded as min and max)
    healthcare_mask = sector_df['name'].str.contains('Health Care|Healthcare', case=False, na=False)
    materials_mask = sector_df['name'].str.contains('Materials', case=False, na=False)
    
    if healthcare_mask.any():
        healthcare_rate = float(sector_df.loc[healthcare_mask, 'pct_llm_flagged'].iloc[0])
    if materials_mask.any():
        materials_rate = float(sector_df.loc[materials_mask, 'pct_llm_flagged'].iloc[0])

#%%
# Save statistics to YAML
yaml_path = yaml_dir / "correlates_collusive_communication.yaml"
if yaml_path.exists():
    with open(yaml_path, "r") as f:
        existing_stats = yaml.safe_load(f) or {}
else:
    existing_stats = {}

# Add sector statistics
existing_stats['sector_valid_llm_tag_rate'] = float(sector_stats['avg_rate'])
existing_stats['sector_valid_observations'] = int(sector_stats['n_total'])

# Add overall LLM rate (from entire dataset, not just sectors/segments)
if overall_llm_rate is not None:
    existing_stats['overall_llm_tag_rate'] = float(overall_llm_rate)
else:
    # Fallback: use weighted average of sectors
    if len(sector_df) > 0:
        total_transcripts = sector_df['n_transcripts'].sum()
        weighted_sum = (sector_df['pct_llm_flagged'] * sector_df['n_transcripts']).sum()
        existing_stats['overall_llm_tag_rate'] = float(weighted_sum / total_transcripts if total_transcripts > 0 else 0)
    else:
        existing_stats['overall_llm_tag_rate'] = 0.0

# Add healthcare (minimum) and materials (maximum) sector rates
existing_stats['sector_healthcare_rate'] = healthcare_rate
existing_stats['sector_materials_rate'] = materials_rate

# Add segment statistics
existing_stats['segment_valid_llm_tag_rate'] = float(segment_stats['avg_rate'])
existing_stats['segment_valid_observations'] = int(segment_stats['n_total'])

# Save updated YAML
with open(yaml_path, "w") as f:
    yaml.dump(existing_stats, f)

print(f"\nSaved statistics to {yaml_path}")
print(f"  Sectors: {sector_stats['n_total']:,} observations, {sector_stats['avg_rate']:.2f}% average tag rate")
print(f"  Segments: {segment_stats['n_total']:,} observations, {segment_stats['avg_rate']:.2f}% average tag rate")
print("\n" + "="*60)
print("Completed sector and segment analysis")
print("="*60)
