#!/usr/bin/env python3
"""
Generate detailed industry-level breakdown of LLM flagging results.

This script creates a comprehensive breakdown of LLM flagging rates by industry
classification at all hierarchy levels for GICS, NAICS, and SIC classification systems.

Output file:
- data/outputs/tables/detailed_industry_results.csv

Columns:
- classification_system: "gics", "naics", or "sic"
- level: Hierarchy level (2, 4, 6, 8 for GICS; 2-6 for NAICS; 2-4 for SIC)
- code: Classification code
- name: Human-readable name/description
- n_transcripts: Number of transcripts in this classification
- n_llm_flagged: Number of transcripts flagged by LLM
- pct_llm_flagged: Percentage of transcripts flagged by LLM
"""

#%%
import config
import pandas as pd
import numpy as np
import os
from pathlib import Path

# Ensure we're running from root
config.ensure_running_from_root()

# Create output directory if it doesn't exist
output_dir = Path("data/outputs/tables")
output_dir.mkdir(parents=True, exist_ok=True)

#%%
# Load main analysis dataset
print("Loading main analysis dataset...")
data_path = Path("data/datasets/main_analysis_dataset.feather")
df = pd.read_feather(data_path)
print(f"Loaded {len(df):,} transcripts")

# Load classification files
print("\nLoading industry classification files...")
gics_path = Path("data/intermediaries/gics_classifications.feather")
naics_path = Path("data/intermediaries/naics_classifications.feather")
sic_path = Path("data/intermediaries/sic_classifications.feather")

gics_df = pd.read_feather(gics_path)
print(f"Loaded {len(gics_df)} GICS classifications")

naics_df = pd.read_feather(naics_path)
print(f"Loaded {len(naics_df)} NAICS classifications")

sic_df = pd.read_feather(sic_path)
print(f"Loaded {len(sic_df)} SIC classifications")

#%%
# Prepare data
# Convert codes to strings for consistent matching
df['gics_sector'] = df['gics_sector'].astype(str).str.zfill(8) if df['gics_sector'].notna().any() else df['gics_sector']
df['gics_group'] = df['gics_group'].astype(str).str.zfill(8) if df['gics_group'].notna().any() else df['gics_group']
df['gics_industry'] = df['gics_industry'].astype(str).str.zfill(8) if df['gics_industry'].notna().any() else df['gics_industry']
df['gics_subindustry'] = df['gics_subindustry'].astype(str).str.zfill(8) if df['gics_subindustry'].notna().any() else df['gics_subindustry']
df['naics'] = df['naics'].astype(str).str.zfill(6) if df['naics'].notna().any() else df['naics']
df['sic'] = df['sic'].astype(str).str.zfill(4) if df['sic'].notna().any() else df['sic']

# Ensure classification dataframes have codes as strings
gics_df['giccd'] = gics_df['giccd'].astype(str)
naics_df['naics'] = naics_df['naics'].astype(str)
sic_df['sic'] = sic_df['sic'].astype(str)

#%%
# Process GICS classifications
print("\nProcessing GICS classifications...")
gics_results = []

# GICS Sector (level 2)
if 'gics_sector' in df.columns and df['gics_sector'].notna().any():
    sector_df = df[df['gics_sector'].notna()].copy()
    sector_stats = (
        sector_df.groupby('gics_sector')['llm_flag']
        .agg(['count', 'sum'])
        .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
        .reset_index()
    )
    sector_stats['pct_llm_flagged'] = (sector_stats['n_llm_flagged'] / sector_stats['n_transcripts'] * 100).round(2)
    sector_stats = sector_stats.merge(
        gics_df[gics_df['level'] == 2][['giccd', 'gicdesc', 'level']],
        left_on='gics_sector',
        right_on='giccd',
        how='left'
    )
    sector_stats['classification_system'] = 'gics'
    sector_stats = sector_stats.rename(columns={'giccd': 'code', 'gicdesc': 'name'})
    sector_stats = sector_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
    gics_results.append(sector_stats)
    print(f"  Processed {len(sector_stats)} GICS sectors")

# GICS Group (level 4)
if 'gics_group' in df.columns and df['gics_group'].notna().any():
    group_df = df[df['gics_group'].notna()].copy()
    group_stats = (
        group_df.groupby('gics_group')['llm_flag']
        .agg(['count', 'sum'])
        .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
        .reset_index()
    )
    group_stats['pct_llm_flagged'] = (group_stats['n_llm_flagged'] / group_stats['n_transcripts'] * 100).round(2)
    group_stats = group_stats.merge(
        gics_df[gics_df['level'] == 4][['giccd', 'gicdesc', 'level']],
        left_on='gics_group',
        right_on='giccd',
        how='left'
    )
    group_stats['classification_system'] = 'gics'
    group_stats = group_stats.rename(columns={'giccd': 'code', 'gicdesc': 'name'})
    group_stats = group_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
    gics_results.append(group_stats)
    print(f"  Processed {len(group_stats)} GICS groups")

# GICS Industry (level 6)
if 'gics_industry' in df.columns and df['gics_industry'].notna().any():
    industry_df = df[df['gics_industry'].notna()].copy()
    industry_stats = (
        industry_df.groupby('gics_industry')['llm_flag']
        .agg(['count', 'sum'])
        .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
        .reset_index()
    )
    industry_stats['pct_llm_flagged'] = (industry_stats['n_llm_flagged'] / industry_stats['n_transcripts'] * 100).round(2)
    industry_stats = industry_stats.merge(
        gics_df[gics_df['level'] == 6][['giccd', 'gicdesc', 'level']],
        left_on='gics_industry',
        right_on='giccd',
        how='left'
    )
    industry_stats['classification_system'] = 'gics'
    industry_stats = industry_stats.rename(columns={'giccd': 'code', 'gicdesc': 'name'})
    industry_stats = industry_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
    gics_results.append(industry_stats)
    print(f"  Processed {len(industry_stats)} GICS industries")

# GICS Sub-Industry (level 8)
if 'gics_subindustry' in df.columns and df['gics_subindustry'].notna().any():
    subindustry_df = df[df['gics_subindustry'].notna()].copy()
    subindustry_stats = (
        subindustry_df.groupby('gics_subindustry')['llm_flag']
        .agg(['count', 'sum'])
        .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
        .reset_index()
    )
    subindustry_stats['pct_llm_flagged'] = (subindustry_stats['n_llm_flagged'] / subindustry_stats['n_transcripts'] * 100).round(2)
    subindustry_stats = subindustry_stats.merge(
        gics_df[gics_df['level'] == 8][['giccd', 'gicdesc', 'level']],
        left_on='gics_subindustry',
        right_on='giccd',
        how='left'
    )
    subindustry_stats['classification_system'] = 'gics'
    subindustry_stats = subindustry_stats.rename(columns={'giccd': 'code', 'gicdesc': 'name'})
    subindustry_stats = subindustry_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
    gics_results.append(subindustry_stats)
    print(f"  Processed {len(subindustry_stats)} GICS sub-industries")

# Combine all GICS results
if gics_results:
    gics_final = pd.concat(gics_results, ignore_index=True)
    print(f"Total GICS results: {len(gics_final)} rows")
else:
    gics_final = pd.DataFrame(columns=['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged'])

#%%
# Process NAICS classifications
print("\nProcessing NAICS classifications...")
naics_results = []

if 'naics' in df.columns and df['naics'].notna().any():
    naics_valid_df = df[df['naics'].notna()].copy()
    print(f"  Found {len(naics_valid_df):,} transcripts with NAICS codes")
    
    # Group by actual NAICS codes in the data first (most efficient)
    naics_code_stats = (
        naics_valid_df.groupby('naics')['llm_flag']
        .agg(['count', 'sum'])
        .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
        .reset_index()
    )
    naics_code_stats['pct_llm_flagged'] = (naics_code_stats['n_llm_flagged'] / naics_code_stats['n_transcripts'] * 100).round(2)
    
    # Merge with classification names to get level
    naics_code_stats = naics_code_stats.merge(
        naics_df[['naics', 'naicsdesc', 'level']],
        on='naics',
        how='left'
    )
    
    # For codes not found, try to infer level from code length
    missing = naics_code_stats[naics_code_stats['level'].isna()]
    if len(missing) > 0:
        print(f"  Warning: {len(missing)} NAICS codes in data not found in classification file")
        # Infer level from code length (number of significant digits)
        missing['level'] = missing['naics'].apply(
            lambda x: len(str(x).lstrip('0')) if str(x).lstrip('0') else 0
        )
        naics_code_stats.loc[missing.index, 'level'] = missing['level']
        # Try to find parent codes for names
        for idx in missing.index:
            code = naics_code_stats.loc[idx, 'naics']
            # Try to find a parent classification
            for prefix_len in range(len(code.lstrip('0')) - 1, 1, -1):
                prefix = code[:prefix_len].lstrip('0').zfill(6)
                parent_match = naics_df[naics_df['naics'].str.startswith(prefix[:len(prefix.lstrip('0'))])]
                if len(parent_match) > 0:
                    parent_match = parent_match.iloc[0]
                    naics_code_stats.loc[idx, 'naicsdesc'] = f"{parent_match['naicsdesc']} (code: {code})"
                    break
    
    # Filter out rows with invalid levels
    naics_code_stats = naics_code_stats[naics_code_stats['level'].notna() & (naics_code_stats['level'] > 0)]
    
    naics_code_stats['classification_system'] = 'naics'
    naics_code_stats = naics_code_stats.rename(columns={'naics': 'code', 'naicsdesc': 'name'})
    naics_code_stats = naics_code_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
    
    # Now create hierarchical aggregations for each level
    for level in [2, 3, 4, 5]:
        # Extract prefix at this level from actual codes
        naics_valid_df['naics_prefix'] = naics_valid_df['naics'].str[:level].str.zfill(6)
        
        # Group by prefix
        prefix_stats = (
            naics_valid_df.groupby('naics_prefix')['llm_flag']
            .agg(['count', 'sum'])
            .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
            .reset_index()
        )
        prefix_stats['pct_llm_flagged'] = (prefix_stats['n_llm_flagged'] / prefix_stats['n_transcripts'] * 100).round(2)
        
        # Match to classification file to get names
        # Find classifications at this level that match the prefixes
        level_classifications = naics_df[naics_df['level'] == level].copy()
        prefix_to_class = {}
        for _, class_row in level_classifications.iterrows():
            class_code = class_row['naics']
            # Find prefixes that start with this classification code
            matching_prefixes = prefix_stats[
                prefix_stats['naics_prefix'].str.startswith(class_code)
            ]['naics_prefix'].tolist()
            for prefix in matching_prefixes:
                if prefix not in prefix_to_class:
                    prefix_to_class[prefix] = {
                        'code': class_code,
                        'name': class_row['naicsdesc'],
                        'level': level
                    }
        
        # Add classification info
        prefix_stats['code'] = prefix_stats['naics_prefix'].map(lambda x: prefix_to_class.get(x, {}).get('code', x))
        prefix_stats['name'] = prefix_stats['naics_prefix'].map(lambda x: prefix_to_class.get(x, {}).get('name', f'NAICS {x[:level]}'))
        prefix_stats['level'] = prefix_stats['naics_prefix'].map(lambda x: prefix_to_class.get(x, {}).get('level', level))
        
        prefix_stats['classification_system'] = 'naics'
        prefix_stats = prefix_stats.drop(columns=['naics_prefix'])
        prefix_stats = prefix_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
        
        # Remove duplicates (keep most specific code-level results)
        prefix_stats = prefix_stats.drop_duplicates(subset=['code'], keep='first')
        
        if len(prefix_stats) > 0:
            naics_results.append(prefix_stats)
            print(f"  Processed {len(prefix_stats)} NAICS aggregations at level {level}")
    
    # Add detailed code-level results
    naics_results.append(naics_code_stats)
    print(f"  Processed {len(naics_code_stats)} unique NAICS codes")

# Combine all NAICS results (remove duplicates, keeping most detailed)
if naics_results:
    naics_final = pd.concat(naics_results, ignore_index=True)
    # Remove duplicates, keeping the most detailed (higher level number = more specific)
    naics_final = naics_final.sort_values('level', ascending=False).drop_duplicates(subset=['code'], keep='first')
    print(f"Total NAICS results: {len(naics_final)} rows")
else:
    naics_final = pd.DataFrame(columns=['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged'])

#%%
# Process SIC classifications
print("\nProcessing SIC classifications...")
sic_results = []

if 'sic' in df.columns and df['sic'].notna().any():
    sic_valid_df = df[df['sic'].notna()].copy()
    print(f"  Found {len(sic_valid_df):,} transcripts with SIC codes")
    
    # Group by actual SIC codes in the data first (most efficient)
    sic_code_stats = (
        sic_valid_df.groupby('sic')['llm_flag']
        .agg(['count', 'sum'])
        .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
        .reset_index()
    )
    sic_code_stats['pct_llm_flagged'] = (sic_code_stats['n_llm_flagged'] / sic_code_stats['n_transcripts'] * 100).round(2)
    
    # Merge with classification names to get level
    sic_code_stats = sic_code_stats.merge(
        sic_df[['sic', 'sicdesc', 'level']],
        on='sic',
        how='left'
    )
    
    # For codes not found, try to infer level from code length
    missing = sic_code_stats[sic_code_stats['level'].isna()]
    if len(missing) > 0:
        print(f"  Warning: {len(missing)} SIC codes in data not found in classification file")
        # Infer level from code length (number of significant digits)
        missing['level'] = missing['sic'].apply(
            lambda x: len(str(x).lstrip('0')) if str(x).lstrip('0') else 0
        )
        sic_code_stats.loc[missing.index, 'level'] = missing['level']
        # Try to find parent codes for names
        for idx in missing.index:
            code = sic_code_stats.loc[idx, 'sic']
            # Try to find a parent classification
            for prefix_len in range(len(code.lstrip('0')) - 1, 1, -1):
                prefix = code[:prefix_len].lstrip('0').zfill(4)
                parent_match = sic_df[sic_df['sic'].str.startswith(prefix[:len(prefix.lstrip('0'))])]
                if len(parent_match) > 0:
                    parent_match = parent_match.iloc[0]
                    sic_code_stats.loc[idx, 'sicdesc'] = f"{parent_match['sicdesc']} (code: {code})"
                    break
    
    # Filter out rows with invalid levels
    sic_code_stats = sic_code_stats[sic_code_stats['level'].notna() & (sic_code_stats['level'] > 0)]
    
    sic_code_stats['classification_system'] = 'sic'
    sic_code_stats = sic_code_stats.rename(columns={'sic': 'code', 'sicdesc': 'name'})
    sic_code_stats = sic_code_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
    
    # Now create hierarchical aggregations for each level
    for level in [2, 3]:
        # Extract prefix at this level from actual codes
        sic_valid_df['sic_prefix'] = sic_valid_df['sic'].str[:level].str.zfill(4)
        
        # Group by prefix
        prefix_stats = (
            sic_valid_df.groupby('sic_prefix')['llm_flag']
            .agg(['count', 'sum'])
            .rename(columns={'count': 'n_transcripts', 'sum': 'n_llm_flagged'})
            .reset_index()
        )
        prefix_stats['pct_llm_flagged'] = (prefix_stats['n_llm_flagged'] / prefix_stats['n_transcripts'] * 100).round(2)
        
        # Match to classification file to get names
        # Find classifications at this level that match the prefixes
        level_classifications = sic_df[sic_df['level'] == level].copy()
        prefix_to_class = {}
        for _, class_row in level_classifications.iterrows():
            class_code = class_row['sic']
            # Find prefixes that start with this classification code
            matching_prefixes = prefix_stats[
                prefix_stats['sic_prefix'].str.startswith(class_code)
            ]['sic_prefix'].tolist()
            for prefix in matching_prefixes:
                if prefix not in prefix_to_class:
                    prefix_to_class[prefix] = {
                        'code': class_code,
                        'name': class_row['sicdesc'],
                        'level': level
                    }
        
        # Add classification info
        prefix_stats['code'] = prefix_stats['sic_prefix'].map(lambda x: prefix_to_class.get(x, {}).get('code', x))
        prefix_stats['name'] = prefix_stats['sic_prefix'].map(lambda x: prefix_to_class.get(x, {}).get('name', f'SIC {x[:level]}'))
        prefix_stats['level'] = prefix_stats['sic_prefix'].map(lambda x: prefix_to_class.get(x, {}).get('level', level))
        
        prefix_stats['classification_system'] = 'sic'
        prefix_stats = prefix_stats.drop(columns=['sic_prefix'])
        prefix_stats = prefix_stats[['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged']]
        
        # Remove duplicates
        prefix_stats = prefix_stats.drop_duplicates(subset=['code'], keep='first')
        
        if len(prefix_stats) > 0:
            sic_results.append(prefix_stats)
            print(f"  Processed {len(prefix_stats)} SIC aggregations at level {level}")
    
    # Add detailed code-level results
    sic_results.append(sic_code_stats)
    print(f"  Processed {len(sic_code_stats)} unique SIC codes")

# Combine all SIC results (remove duplicates, keeping most detailed)
if sic_results:
    sic_final = pd.concat(sic_results, ignore_index=True)
    # Remove duplicates, keeping the most detailed (higher level number = more specific)
    sic_final = sic_final.sort_values('level', ascending=False).drop_duplicates(subset=['code'], keep='first')
    print(f"Total SIC results: {len(sic_final)} rows")
else:
    sic_final = pd.DataFrame(columns=['classification_system', 'level', 'code', 'name', 'n_transcripts', 'n_llm_flagged', 'pct_llm_flagged'])

#%%
# Combine all results
print("\nCombining all results...")
all_results = pd.concat([gics_final, naics_final, sic_final], ignore_index=True)

# Sort by classification system, level, and pct_llm_flagged (descending)
all_results = all_results.sort_values(
    ['classification_system', 'level', 'pct_llm_flagged'],
    ascending=[True, True, False]
).reset_index(drop=True)

# Ensure integer types for counts
all_results['n_transcripts'] = all_results['n_transcripts'].astype(int)
all_results['n_llm_flagged'] = all_results['n_llm_flagged'].astype(int)

# Handle level column - fill NaN with 0 and convert to int
all_results['level'] = all_results['level'].fillna(0).astype(int)
# Remove rows with invalid level (0)
all_results = all_results[all_results['level'] > 0]

#%%
# Save results
output_path = output_dir / "detailed_industry_results.csv"
all_results.to_csv(output_path, index=False)
print(f"\nSaved detailed industry results to: {output_path}")
print(f"Total rows: {len(all_results):,}")

# Calculate unique transcript counts (to avoid double-counting from hierarchical aggregations)
print(f"\nSummary by classification system:")
for system in ['gics', 'naics', 'sic']:
    system_df = all_results[all_results['classification_system'] == system]
    if len(system_df) > 0:
        # Get unique transcript counts from original data
        if system == 'gics':
            # For GICS, count unique transcripts with any GICS code
            unique_transcripts = df[
                df[['gics_sector', 'gics_group', 'gics_industry', 'gics_subindustry']].notna().any(axis=1)
            ]
        elif system == 'naics':
            unique_transcripts = df[df['naics'].notna()]
        else:  # sic
            unique_transcripts = df[df['sic'].notna()]
        
        unique_count = len(unique_transcripts)
        unique_flagged = unique_transcripts['llm_flag'].sum()
        unique_flag_rate = (unique_flagged / unique_count * 100) if unique_count > 0 else 0
        
        print(f"  {system.upper()}: {len(system_df)} classification codes")
        print(f"    Levels: {sorted(system_df['level'].unique())}")
        print(f"    Unique transcripts: {unique_count:,}")
        print(f"    Unique flagged: {unique_flagged:,}")
        print(f"    Overall flag rate: {unique_flag_rate:.2f}%")
        print(f"    Note: Sum of n_transcripts ({system_df['n_transcripts'].sum():,}) is higher due to hierarchical aggregations")

print("\nDone!")
