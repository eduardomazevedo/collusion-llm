#!/usr/bin/env python3
"""
Download Compustat US data from WRDS using the list of GVKEYs present in our transcripts.

This script downloads financial data from comp_na_daily_all.funda and company information
for all GVKEYs in the gvkey_list.txt file. We mostly want covariates for sector, market value, number of employees.

The data is made unique by gvkey-fyear pairs, prioritizing INDL over FS industry format and keeping the latest
observation for each company-year. 

Variables produced:
- costat: Company status (A=Active, I=Inactive)
- indfmt: Industry format (INDL=Industrial, FS=Financial Services)
- gvkey: Global company key identifier
- datadate: Data date
- conm: Company name
- fyear: Fiscal year
- fic: Incorporation country
- ggroup: GICS group
- gind: GICS industry
- gsector: GICS sector
- gsubind: GICS sub-industry
- loc: Location/domicile
- emp: Number of employees (thousands)
- mkvalt: Market value (millions USD)
"""

#%%
import config
import wrds
import pandas as pd
import os

# Ensure we're running from root
config.ensure_running_from_root()

print(f"Connecting to WRDS with username: {config.WRDS_USERNAME}")

# Connect to WRDS
conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
print("WRDS connection established!")

#%%
# Read the list of GVKEYs
gvkey_list_path = "data/intermediaries/gvkey_list.txt"
print(f"Reading GVKEYs from {gvkey_list_path}")

with open(gvkey_list_path, 'r') as f:
    gvkeys = [line.strip() for line in f.readlines() if line.strip()]

print(f"Found {len(gvkeys)} GVKEYs to query")

#%%
# Convert list to SQL format for the IN clause
gvkey_list_sql = "', '".join(gvkeys)
gvkey_list_sql = f"'{gvkey_list_sql}'"

print(f"Prepared GVKEY list for SQL query (first 10): {gvkey_list_sql[:100]}...")

#%%
# Build the SQL query
query = f"""
SELECT
    comp_na_daily_all.funda.costat,
    comp_na_daily_all.funda.curcd,
    comp_na_daily_all.funda.datafmt,
    comp_na_daily_all.funda.indfmt,
    comp_na_daily_all.funda.consol,
    comp_na_daily_all.funda.gvkey,
    comp_na_daily_all.funda.datadate,
    comp_na_daily_all.funda.conm,
    comp_na_daily_all.funda.fyear,
    comp_na_daily_all.funda.fic,
    id_table.ggroup,
    id_table.gind,
    id_table.gsector,
    id_table.gsubind,
    id_table.loc,
    comp_na_daily_all.funda.emp,
    comp_na_daily_all.funda.mkvalt

FROM comp_na_daily_all.funda
INNER JOIN (
    SELECT
        gvkey,
        ggroup,
        gind,
        gsector,
        gsubind,
        loc
    FROM comp_na_daily_all.company
    WHERE comp_na_daily_all.company.gvkey IN (
        {gvkey_list_sql}
    )
) AS id_table 

ON comp_na_daily_all.funda.gvkey = id_table.gvkey

AND ("comp_na_daily_all"."funda"."consol" = ANY (ARRAY['C']) 
     AND "comp_na_daily_all"."funda"."indfmt" = ANY (ARRAY['INDL','FS']) 
     AND "comp_na_daily_all"."funda"."datafmt" = ANY (ARRAY['STD']) 
     AND "comp_na_daily_all"."funda"."curcd" = 'USD'
     AND "comp_na_daily_all"."funda"."costat" = ANY (ARRAY['A','I']))
"""

print("Executing Compustat query...")
print(f"Query preview: {query[:200]}...")

#%%
# Execute the query
df = conn.raw_sql(query)
print(f"Query completed! Retrieved {len(df)} records")

# Close connection
conn.close()
print("WRDS connection closed.")

#%%
# Data formatting and type conversion
print("Formatting data types...")

# Convert categorical variables
categorical_columns = ['costat', 'curcd', 'datafmt', 'indfmt', 'consol', 'fic', 'ggroup', 'gind', 'gsector', 'gsubind', 'loc']
for col in categorical_columns:
    if col in df.columns:
        df[col] = df[col].astype('category')

# Convert date columns
if 'datadate' in df.columns:
    df['datadate'] = pd.to_datetime(df['datadate']).dt.date

# Convert numeric columns to appropriate types
numeric_columns = ['fyear', 'emp', 'mkvalt']
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Convert gvkey to string (keep leading zeros)
if 'gvkey' in df.columns:
    df['gvkey'] = df['gvkey'].astype(str)

print("Data formatting completed.")

#%%
# Print summary statistics
print("\nDataset Summary:")
print(f"Shape: {df.shape}")
print(f"Date range: {df['datadate'].min()} to {df['datadate'].max()}")
print(f"Unique companies (gvkey): {df['gvkey'].nunique()}")
print(f"Unique years (fyear): {df['fyear'].nunique()}")

print("\nColumns:")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")


#%% Remove duplicates
# Try to keep indfmt 'INDL' over 'FS' for the same gvkey and fyear (accounting standard for industrial vs financial companies)
# And try to keep last observation for each gvkey and fyear
indfmt_priority = {'INDL': 1, 'FS': 2}
df['indfmt_rank'] = df['indfmt'].map(indfmt_priority)

# Sort by priority and drop duplicates
df = (
    df.sort_values(by=['gvkey', 'fyear', 'indfmt_rank', 'datadate'], ascending=[True, True, True, False])
      .drop_duplicates(subset=['gvkey', 'fyear'], keep='first')
      .drop(columns='indfmt_rank')
)

# Assert no duplicates remain
assert df.duplicated(subset=['gvkey', 'fyear']).sum() == 0, "Duplicates found after deduplication!"


#%% 
# Assert constant columns and drop them
# These columns should have unique values since we filtered for them in the SQL query
constant_columns = ['curcd', 'datafmt', 'consol']
for col in constant_columns:
    unique_vals = df[col].nunique()
    print(f"Column {col} has {unique_vals} unique values: {df[col].unique()}")
    assert unique_vals == 1, f"Expected {col} to have only one unique value, but found {unique_vals}"

# Drop the constant columns
df = df.drop(columns=constant_columns)
print(f"Dropped constant columns: {constant_columns}")


#%%
# Reorder columns to put gvkey and fyear first
cols = df.columns.tolist()
key_cols = ['gvkey', 'fyear']
other_cols = [col for col in cols if col not in key_cols]
df = df[key_cols + other_cols]
print(f"Reordered columns with gvkey and fyear first")


#%%
# Save the data
output_dir = "data/raw/compustat"
os.makedirs(output_dir, exist_ok=True)

# Save as feather
feather_path = os.path.join(output_dir, "compustat_us.feather")
print(f"Saving data to {feather_path}")
df.to_feather(feather_path)

print(f"\nDownload completed successfully!")
print(f"Final dataset: {len(df)} observations across {df['gvkey'].nunique()} companies")
