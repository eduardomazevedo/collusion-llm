#!/usr/bin/env python3
"""
Create a dataset of Compustat data in data/company_year_compustat.parquet.

This script:
1. Loads US and Global Compustat data
2. Adds a 'loc' variable to US data (set to 'USA')
3. Combines both datasets
4. Merges with gvkey_table to get companyid
5. Saves the result as a parquet file with companyid and fyear as keys
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

def main():
    # Define file paths
    base_path = Path(__file__).parent.parent.parent.parent
    us_file = base_path / "data" / "raw" / "compustat" / "compustat_us.csv"
    global_file = base_path / "data" / "raw" / "compustat" / "compustat_global.csv"
    gvkey_table_file = base_path / "data" / "gvkey_table.feather"
    output_file = base_path / "data" / "company_year_compustat.parquet"
    
    print("Loading Compustat US data...")
    us_df = pd.read_csv(us_file)
    print(f"Loaded {len(us_df):,} US records")
    
    print("Loading Compustat Global data...")
    global_df = pd.read_csv(global_file)
    print(f"Loaded {len(global_df):,} Global records")
    
    # Add 'loc' variable to US dataset
    print("Adding 'loc' variable to US data...")
    us_df['loc'] = 'USA'
    
    # Get all unique columns from both datasets
    us_cols = set(us_df.columns)
    global_cols = set(global_df.columns)
    all_cols = us_cols.union(global_cols)
    
    print(f"US-only columns: {us_cols - global_cols}")
    print(f"Global-only columns: {global_cols - us_cols}")
    
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
    
    print(f"Using {len(all_cols)} total columns including mkvalt: {', '.join(all_cols[:10])}{'...' if len(all_cols) > 10 else ''}")
    
    # Combine the datasets
    print("Combining US and Global datasets...")
    combined_df = pd.concat([us_df, global_df], ignore_index=True)
    print(f"Combined dataset has {len(combined_df):,} records")
    
    # Load gvkey_table for mapping gvkey to companyid
    print("Loading gvkey table...")
    gvkey_df = pd.read_feather(gvkey_table_file)
    print(f"Loaded {len(gvkey_df):,} gvkey mappings")
    print(f"GVKEY table columns: {list(gvkey_df.columns)}")
    
    # Merge with gvkey_table to get companyid
    print("Merging with gvkey table...")
    # Convert gvkey to string in both datasets to ensure proper matching
    combined_df['gvkey'] = combined_df['gvkey'].astype(str).str.zfill(6)
    gvkey_df['gvkey'] = gvkey_df['gvkey'].astype(str).str.zfill(6)
    
    final_df = combined_df.merge(gvkey_df, on='gvkey', how='inner')
    print(f"After merge: {len(final_df):,} records")
    
    # Ensure we have the required key columns
    if 'companyid' not in final_df.columns:
        raise ValueError("companyid column not found after merge")
    if 'fyear' not in final_df.columns:
        raise ValueError("fyear column not found in dataset")
    
    # Sort by companyid and fyear for better organization
    final_df = final_df.sort_values(['companyid', 'fyear'])
    
    # Display some summary statistics
    print(f"\nDataset summary:")
    print(f"Total records: {len(final_df):,}")
    print(f"Unique companies: {final_df['companyid'].nunique():,}")
    print(f"Year range: {final_df['fyear'].min()} - {final_df['fyear'].max()}")
    print(f"Columns: {len(final_df.columns)}")
    
    # Save to parquet
    print(f"\nSaving to {output_file}...")
    final_df.to_parquet(output_file, index=False)
    print("Dataset saved successfully!")
    
    # Display sample of the data
    print(f"\nSample of final dataset:")
    print(final_df[['companyid', 'gvkey', 'fyear', 'conm', 'loc', 'emp']].head(10))

if __name__ == "__main__":
    main()
