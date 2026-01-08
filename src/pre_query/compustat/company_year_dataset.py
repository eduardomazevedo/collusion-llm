#!/usr/bin/env python3
"""
Create a dataset of Compustat data in data/datasets/company_year_compustat.feather.

This script:
1. Loads US and Global Compustat data from feather files
2. Harmonizes column structures between the two datasets
3. Stacks both datasets
4. Merges with gvkey_table to get companyid. gvkey-companyid mapping is refined to keep the gvkey with the most observations for each companyid.
5. Renames variables to more descriptive names
6. Saves the result as a feather file with companyid and fiscal_year as keys

Output columns:
- companyid: Capital IQ company identifier
- fiscal_year: Fiscal year of observation
- company_name: Company name as recorded in Compustat
- company_status: Company status (A=Active, I=Inactive)
- currency_code: Currency code of financial data (USD, EUR, etc.)
- data_date: Date of financial data observation
- employees_thousands: Number of employees in thousands
- incorporation_country: Country of incorporation code
- gics_group: GICS industry group code
- gics_industry: GICS industry code
- gics_sector: GICS sector code
- gics_subindustry: GICS sub-industry code
- gvkey: Compustat Global Company Key
- industry_format: Industry format (INDL=Industrial, FS=Financial Services)
- domicile_country: Location/domicile country code
- market_value_total_mil: Market value of total capital in millions USD
"""

#%% Start
import config
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import sys

# Define file paths
us_file = "data/raw/compustat/compustat_us.feather"
global_file = "data/raw/compustat/compustat_global.feather"
gvkey_table_file = "data/intermediaries/gvkey_table.feather"
output_file = "data/datasets/company_year_compustat.feather"

#%% Load data
us_df = pd.read_feather(us_file)
global_df = pd.read_feather(global_file)


# Sort the datasets by 'gvkey' and 'fyear' for consistency
us_df = us_df.sort_values(['gvkey', 'fyear'])
global_df = global_df.sort_values(['gvkey', 'fyear'])


#%% Assert that tables are unique on 'gvkey' and 'fyear'
# Check for duplicates in US dataset
us_duplicates = us_df.duplicated(subset=['gvkey', 'fyear'], keep=False)
if us_duplicates.any():
    raise ValueError(f"Found {us_duplicates.sum()} duplicate rows in US dataset based on 'gvkey' and 'fyear'. This should not happen.")
else:
    print("No duplicate rows found in US dataset based on 'gvkey' and 'fyear'.")

# Check for duplicates in Global dataset
global_duplicates = global_df.duplicated(subset=['gvkey', 'fyear'], keep=False)
if global_duplicates.any():
    raise ValueError(f"Found {global_duplicates.sum()} duplicate rows in Global dataset based on 'gvkey' and 'fyear'. This should not happen.")
else:
    print("No duplicate rows found in Global dataset based on 'gvkey' and 'fyear'.")

#%% Harmonize datasets
# Get all unique columns from both datasets
us_cols = set(us_df.columns)
global_cols = set(global_df.columns)
all_cols = us_cols.union(global_cols)

# Add missing columns to each dataset with NaN values
for col in all_cols:
    if col not in us_df.columns:
        us_df[col] = pd.NA
    if col not in global_df.columns:
        global_df[col] = pd.NA

# Ensure both datasets have the same columns in the same order
all_cols = sorted(list(all_cols))
us_df = us_df[all_cols]
global_df = global_df[all_cols]


#%% Concatenate datasets
# Combine the datasets, preferring US data when there are overlaps
print("Combining US and Global datasets...")

# Add source indicator before combining
us_df['data_source'] = 'US'
global_df['data_source'] = 'Global'

combined_df = pd.concat([us_df, global_df], ignore_index=True)
print(f"Combined dataset before deduplication has {len(combined_df):,} observations")

# Check for and resolve overlapping gvkey-fyear pairs
# Keep US observations when there are duplicates
combined_df = combined_df.sort_values(['gvkey', 'fyear', 'data_source'])  # US comes before Global alphabetically
combined_df_deduplicated = combined_df.drop_duplicates(subset=['gvkey', 'fyear'], keep='first')

n_removed = len(combined_df) - len(combined_df_deduplicated)
if n_removed > 0:
    print(f"Removed {n_removed:,} overlapping observations (kept US data when available)")
else:
    print("No overlapping gvkey-fyear pairs found between US and Global datasets")

# Drop the temporary source column
combined_df = combined_df_deduplicated.drop('data_source', axis=1)
print(f"Combined dataset after deduplication has {len(combined_df):,} observations")

#%% Create observation count table by gvkey
print("\nCreating observation count table by gvkey...")
gvkey_obs_count = combined_df.groupby('gvkey').size().reset_index(name='obs_count')
print(f"Found {len(gvkey_obs_count):,} unique gvkeys in combined Compustat data")

#%% Load gvkey table and check for uniqueness
# Load gvkey_table for mapping gvkey to companyid
gvkey_df = pd.read_feather(gvkey_table_file)
print(f"Original gvkey_table has {len(gvkey_df):,} rows")

# Print number of duplicate gvkeys, companyids, and pairs in gvkey_df
print("\nChecking gvkey_table for duplicates...")
gvkey_duplicates = gvkey_df.duplicated(subset=['gvkey'], keep=False)
if gvkey_duplicates.any():
    print(f"Found {gvkey_duplicates.sum()} duplicate gvkeys in gvkey_table.")
else:
    print("No duplicate gvkeys found in gvkey_table.")

companyid_duplicates = gvkey_df.duplicated(subset=['companyid'], keep=False)
if companyid_duplicates.any():
    print(f"Found {companyid_duplicates.sum()} duplicate companyids in gvkey_table.")
    n_companyids_with_multiple_gvkeys = gvkey_df[companyid_duplicates]['companyid'].nunique()
    print(f"This corresponds to {n_companyids_with_multiple_gvkeys} companyids that have multiple gvkeys.")
else:
    print("No duplicate companyids found in gvkey_table.")

# Check for unique pairs of gvkey and companyid
pair_duplicates = gvkey_df.duplicated(subset=['gvkey', 'companyid'], keep=False)
if pair_duplicates.any():
    print(f"Found {pair_duplicates.sum()} duplicate pairs of gvkey and companyid in gvkey_table.")
else:
    print("No duplicate pairs of gvkey and companyid found in gvkey_table.")

#%% Resolve multiple gvkeys per companyid by selecting the one with most observations
print("\nResolving multiple gvkeys per companyid...")

# Convert gvkey to string with zero-padding for consistent matching
gvkey_df['gvkey'] = gvkey_df['gvkey'].astype(str).str.zfill(6)
gvkey_obs_count['gvkey'] = gvkey_obs_count['gvkey'].astype(str).str.zfill(6)

# Merge observation counts with gvkey table
gvkey_df_with_counts = gvkey_df.merge(gvkey_obs_count, on='gvkey', how='left')
gvkey_df_with_counts['obs_count'] = gvkey_df_with_counts['obs_count'].fillna(0)

# For each companyid, keep only the gvkey with the most observations
# In case of ties, keep the first one (arbitrary but consistent)
gvkey_df_refined = gvkey_df_with_counts.sort_values(['companyid', 'obs_count', 'gvkey'], ascending=[True, False, True])
gvkey_df_refined = gvkey_df_refined.groupby('companyid').first().reset_index()

print(f"Refined gvkey_table has {len(gvkey_df_refined):,} rows")
print(f"Removed {len(gvkey_df) - len(gvkey_df_refined):,} rows")

# Show some examples of what was removed
if len(gvkey_df) > len(gvkey_df_refined):
    removed_gvkeys = set(gvkey_df['gvkey']) - set(gvkey_df_refined['gvkey'])
    print(f"Removed {len(removed_gvkeys):,} gvkeys")

#%% Filter combined dataset to only include gvkeys in refined table
print(f"\nFiltering combined dataset to include only refined gvkeys...")
print(f"Combined dataset before filtering: {len(combined_df):,} observations")

# Convert gvkey in combined dataset for matching
combined_df['gvkey'] = combined_df['gvkey'].astype(str).str.zfill(6)

# Keep only observations for gvkeys in the refined table
refined_gvkeys = set(gvkey_df_refined['gvkey'])
combined_df_filtered = combined_df[combined_df['gvkey'].isin(refined_gvkeys)]

print(f"Combined dataset after filtering: {len(combined_df_filtered):,} observations")
print(f"Removed {len(combined_df) - len(combined_df_filtered):,} observations")

#%% Check for gvkeys corresponding to multiple companyids in refined table
print(f"\nChecking refined gvkey table for gvkeys with multiple companyids...")
gvkey_duplicates_refined = gvkey_df_refined.duplicated(subset=['gvkey'], keep=False)
if gvkey_duplicates_refined.any():
    n_gvkeys_with_multiple_companyids = gvkey_df_refined[gvkey_duplicates_refined]['gvkey'].nunique()
    print(f"WARNING: Found {gvkey_duplicates_refined.sum()} rows with {n_gvkeys_with_multiple_companyids} gvkeys that correspond to multiple companyids.")
    print("Proceeding with merge anyway...")
else:
    print("No gvkeys correspond to multiple companyids in refined table.")

# Also check that refined table has unique companyids
companyid_duplicates_refined = gvkey_df_refined.duplicated(subset=['companyid'], keep=False)
if companyid_duplicates_refined.any():
    print(f"ERROR: Found {companyid_duplicates_refined.sum()} duplicate companyids in refined gvkey_table!")
    print("This should not happen after refinement.")
    raise ValueError("Refined gvkey table still has duplicate companyids")
else:
    print("Refined gvkey table has unique companyids as expected.")

#%% Merge company id
# Merge with refined gvkey_table to get companyid
print(f"\nMerging with refined gvkey table...")
final_df = combined_df_filtered.merge(gvkey_df_refined[['gvkey', 'companyid']], on='gvkey', how='inner')

print(f"Final dataset has {len(final_df):,} observations")
print(f"Final dataset has {final_df['companyid'].nunique():,} unique companyids")
print(f"Final dataset has {final_df['gvkey'].nunique():,} unique gvkeys")

# Ensure we have the required key columns
if 'companyid' not in final_df.columns:
    raise ValueError("companyid column not found after merge")
if 'fyear' not in final_df.columns:
    raise ValueError("fyear column not found in dataset")

# Sort by companyid and fyear for better organization
final_df = final_df.sort_values(['companyid', 'fyear'])

# Put companyid and fyear first in column order
cols = ['companyid', 'fyear'] + [col for col in final_df.columns if col not in ['companyid', 'fyear']]
final_df = final_df[cols]

# Assert that final dataset is unique on companyid and fyear
print(f"\nChecking final dataset for uniqueness on companyid and fyear...")
final_duplicates = final_df.duplicated(subset=['companyid', 'fyear'], keep=False)
if final_duplicates.any():
    raise ValueError(f"Found {final_duplicates.sum()} duplicate rows in final dataset based on 'companyid' and 'fyear'.")
else:
    print("Final dataset is unique on companyid and fyear.")

#%% Rename columns to more descriptive names
print(f"\nRenaming columns to more descriptive names...")

# Define column mapping from original Compustat names to descriptive names
column_mapping = {
    'companyid': 'companyid',  # Keep as is - this is our key
    'fyear': 'fiscal_year',
    'conm': 'company_name',
    'costat': 'company_status',
    'curcd': 'currency_code',
    'datadate': 'data_date',
    'emp': 'employees_thousands',
    'fic': 'incorporation_country',
    'ggroup': 'gics_group',
    'gind': 'gics_industry',
    'gsector': 'gics_sector',
    'gsubind': 'gics_subindustry',
    'gvkey': 'gvkey',  # Keep as is - this is a standard identifier
    'indfmt': 'industry_format',
    'loc': 'domicile_country',
    'mkvalt': 'market_value_total_mil',
    'sic': 'sic',  # Standard Industrial Classification code (4-digit)
    'naics': 'naics'  # North American Industry Classification System code (6-digit)
}

# Rename columns
final_df = final_df.rename(columns=column_mapping)

# Reorder columns with key variables first
key_cols = ['companyid', 'fiscal_year']
descriptive_cols = ['company_name', 'company_status', 'gvkey']
financial_cols = ['market_value_total_mil', 'employees_thousands', 'currency_code', 'data_date']
classification_cols = ['gics_sector', 'gics_industry', 'gics_group', 'gics_subindustry', 'industry_format', 'sic', 'naics']
location_cols = ['incorporation_country', 'domicile_country']

# Create final column order
final_column_order = key_cols + descriptive_cols + financial_cols + classification_cols + location_cols
final_df = final_df[final_column_order]

print(f"Renamed columns. Final column names: {list(final_df.columns)}")

# Final uniqueness check with new column names
print(f"\nFinal check: dataset is unique on companyid and fiscal_year...")
final_duplicates_renamed = final_df.duplicated(subset=['companyid', 'fiscal_year'], keep=False)
if final_duplicates_renamed.any():
    raise ValueError(f"Found {final_duplicates_renamed.sum()} duplicate rows in final dataset based on 'companyid' and 'fiscal_year'.")
else:
    print("Final dataset is unique on companyid and fiscal_year.")

print(f"\nSaving final dataset with {len(final_df):,} observations to {output_file}")

# Save to feather
final_df.to_feather(output_file)