#!/usr/bin/env python3

#%%
import config
import pandas as pd
import os

# Load the transcript detail data
df = pd.read_feather(config.TRANSCRIPT_DETAIL_PATH)

# Select only the columns we need
result_df = df[['companyid', 'companyname', 'transcriptid', 'headline']].copy()

# Count rows before deduplication
rows_before = len(result_df)

# Remove any duplicate rows
result_df = result_df.drop_duplicates()

# Count rows after deduplication (sanity check; shouldn't be any duplicates)
rows_after = len(result_df)
print(f"\nRows before deduplication: {rows_before}")
print(f"Rows after deduplication: {rows_after}")
print(f"Rows removed by deduplication: {rows_before - rows_after}")

# Sort by companyid and transcriptid for better readability
result_df = result_df.sort_values(['companyid', 'transcriptid'])

# Count unique companies
num_companies = result_df['companyid'].nunique()
print(f"\nNumber of unique companies: {num_companies}")

# Save to CSV
output_path = config.COMPANIES_TRANSCRIPTS_PATH

# Create the directory if it doesn't exist
os.makedirs(os.path.dirname(output_path), exist_ok=True)

result_df.to_csv(output_path, index=False)

print(f"Exported {len(result_df)} unique company-transcript combinations to {output_path}") 