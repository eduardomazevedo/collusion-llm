#!/usr/bin/env python3
"""
Create a dataset of Compustat data in data/datasets/company_year_compustat.feather.

This script:
1. Loads US and Global Compustat data
2. Adds a 'loc' variable to US data (set to 'USA')
3. Combines both datasets
4. Merges with gvkey_table to get companyid
5. Saves the result as a parquet file with companyid and fyear as keys
"""

#%% Start
import config
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import sys

# Define file paths
us_file = "data/raw/compustat/compustat_us.csv"
global_file = "data/raw/compustat/compustat_global.csv"
gvkey_table_file = "data/intermediaries/gvkey_table.feather"
output_file = "data/datasets/company_year_compustat.feather"

#%% Load data
us_df = pd.read_csv(us_file)
global_df = pd.read_csv(global_file)


# Sort the datasets by 'gvkey' and 'fyear' for consistency
us_df = us_df.sort_values(['gvkey', 'fyear'])
global_df = global_df.sort_values(['gvkey', 'fyear'])


#%% Assert that tables are unique on 'gvkey' and 'fyear'
# Check for duplicates in US dataset
us_duplicates = us_df.duplicated(subset=['gvkey', 'fyear'], keep=False)
if us_duplicates.any():
    print(f"Found {us_duplicates.sum()} duplicate rows in US dataset based on 'gvkey' and 'fyear'.")
else:
    print("No duplicate rows found in US dataset based on 'gvkey' and 'fyear'.")

# Check for duplicates in Global dataset
global_duplicates = global_df.duplicated(subset=['gvkey', 'fyear'], keep=False)
if global_duplicates.any():
    print(f"Found {global_duplicates.sum()} duplicate rows in Global dataset based on 'gvkey' and 'fyear'.")
else:
    print("No duplicate rows found in Global dataset based on 'gvkey' and 'fyear'.")

#%% Harmonize datasets
# Add 'loc' variable to US dataset
us_df['loc'] = 'USA'

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
# Combine the datasets
print("Combining US and Global datasets...")
combined_df = pd.concat([us_df, global_df], ignore_index=True)


#%% Load gvkey table and check for uniqueness
# Load gvkey_table for mapping gvkey to companyid
gvkey_df = pd.read_feather(gvkey_table_file)

# Print number of duplicate gvkeys, companyids, and pairs in gvkey_df
print("Checking gvkey_table for duplicates...")
gvkey_duplicates = gvkey_df.duplicated(subset=['gvkey'], keep=False)
if gvkey_duplicates.any():
    print(f"Found {gvkey_duplicates.sum()} duplicate gvkeys in gvkey_table.")
else:
    print("No duplicate gvkeys found in gvkey_table.")

companyid_duplicates = gvkey_df.duplicated(subset=['companyid'], keep=False)
if companyid_duplicates.any():
    print(f"Found {companyid_duplicates.sum()} duplicate companyids in gvkey_table.")
else:
    print("No duplicate companyids found in gvkey_table.")

# Check for unique pairs of gvkey and companyid
pair_duplicates = gvkey_df.duplicated(subset=['gvkey', 'companyid'], keep=False)
if pair_duplicates.any():
    print(f"Found {pair_duplicates.sum()} duplicate pairs of gvkey and companyid in gvkey_table.")
else:
    print("No duplicate pairs of gvkey and companyid found in gvkey_table.")

#%% Merge company id
# Merge with gvkey_table to get companyid
# Convert gvkey to string in both datasets to ensure proper matching
combined_df['gvkey'] = combined_df['gvkey'].astype(str).str.zfill(6)
gvkey_df['gvkey'] = gvkey_df['gvkey'].astype(str).str.zfill(6)

final_df = combined_df.merge(gvkey_df, on='gvkey', how='inner')

# Ensure we have the required key columns
if 'companyid' not in final_df.columns:
    raise ValueError("companyid column not found after merge")
if 'fyear' not in final_df.columns:
    raise ValueError("fyear column not found in dataset")

# Sort by companyid and fyear for better organization
final_df = final_df.sort_values(['companyid', 'fyear'])

# Save to feather
final_df.to_feather(output_file)