#%%
"""
LLM Collusion Tagging Analysis - High Collusion Segments

This script analyzes collusion tagging rates for eight high collusion segments.
Uses detailed_industry_results.csv as input to calculate tag rates for each segment.

Output file:
- data/outputs/tables/collusive_segments_tag_rates.csv
"""

#%%
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import config
import pandas as pd
import numpy as np

# Ensure we're running from root
config.ensure_running_from_root()

# Create output directory if it doesn't exist
output_dir = Path("data/outputs/tables")
output_dir.mkdir(parents=True, exist_ok=True)

#%%
# Define the eight high collusion segments
# Format: (segment_name, sic_codes, match_type)
# match_type: 'exact' for exact SIC code match, 'prefix' for codes starting with the prefix
HIGH_COLLUSION_SEGMENTS = [
    ('Cement', ['3241'], 'exact'),
    ('Commodity Chemicals', ['281', '286', '287'], 'prefix'),
    ('Heavy Civil Construction', ['161', '162'], 'prefix'),
    ('Pulp, Paper & Packaging', ['261', '262', '263', '265'], 'prefix'),
    ('Primary Metals', ['331', '332', '333'], 'prefix'),
    ('Glass & Concrete', ['321', '327'], 'prefix'),
    ('Asphalt & Refining', ['291', '295'], 'prefix'),
    ('Wholesale Materials', ['503'], 'prefix'),
]

#%%
# Load detailed industry results
print("Loading detailed industry results...")
detailed_results_path = Path("data/outputs/tables/detailed_industry_results.csv")

if not detailed_results_path.exists():
    raise FileNotFoundError(
        f"Detailed industry results file not found at {detailed_results_path}. "
        "Please run detailed_industry_results.py first."
    )

detailed_df = pd.read_csv(detailed_results_path)
print(f"Loaded {len(detailed_df):,} industry classification results")

# Ensure codes are strings for matching
detailed_df['code'] = detailed_df['code'].astype(str)

#%%
# Filter segments from detailed results
print("\nFiltering high collusion segments...")
segment_results = []

# Filter to SIC codes only
sic_df = detailed_df[detailed_df['classification_system'] == 'sic'].copy()
print(f"Found {len(sic_df):,} SIC classification results")

for segment_name, sic_codes, match_type in HIGH_COLLUSION_SEGMENTS:
    print(f"\nProcessing {segment_name}...")
    
    # Find all matching rows
    all_matches = []
    
    for sic_code in sic_codes:
        if match_type == 'exact':
            # Exact match: SIC code must be exactly this (handle zero-padding)
            sic_code_clean = str(sic_code).zfill(4)
            matches = sic_df[sic_df['code'].astype(str).str.zfill(4) == sic_code_clean]
        else:  # prefix
            # Prefix match: SIC code must start with this prefix
            # Handle both 3-digit and 4-digit codes in the data
            sic_code_clean = str(sic_code).zfill(4)
            # Match codes that start with this prefix (at any level)
            # This will match 281, 2810, 2811, etc.
            matches = sic_df[
                sic_df['code'].astype(str).str.zfill(4).str.startswith(sic_code_clean)
            ]
        
        if len(matches) > 0:
            all_matches.append(matches)
            print(f"  SIC {sic_code} ({match_type}): {len(matches)} classification(s) found")
    
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
        'segment_name': segment_name,
        'classification_system': 'sic',
        'level': int(representative['level']),
        'sic_codes': ', '.join(sic_codes),
        'classification_name': representative['name'] if len(combined_matches) == 1 else f"{segment_name} (aggregated)",
        'n_transcripts': int(total_transcripts),
        'n_llm_flagged': int(total_flagged),
        'pct_llm_flagged': round(pct_flagged, 2)
    }
    segment_results.append(result_row)
    print(f"  {segment_name}: {total_transcripts:,} transcripts, {total_flagged:,} flagged ({pct_flagged:.2f}%)")

#%%
# Create results dataframe
if len(segment_results) == 0:
    print("\nERROR: No segments found. Please check HIGH_COLLUSION_SEGMENTS definitions.")
    results_df = pd.DataFrame(columns=[
        'segment_name', 'classification_system', 'level', 'sic_codes', 
        'classification_name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged'
    ])
else:
    results_df = pd.DataFrame(segment_results)
    
    # Sort by pct_llm_flagged descending
    results_df = results_df.sort_values('pct_llm_flagged', ascending=False).reset_index(drop=True)
    
    print(f"\n{'='*80}")
    print(f"Found {len(results_df)} segments")
    print(f"{'='*80}")
    print(f"\nResults summary:")
    print(results_df[['segment_name', 'sic_codes', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']].to_string(index=False))

#%%
# Save results
output_path = output_dir / "collusive_segments_tag_rates.csv"
results_df.to_csv(output_path, index=False)
print(f"\nSaved collusive segments tag rates to: {output_path}")
print(f"Total segments: {len(results_df)}")

print("\nDone!")
