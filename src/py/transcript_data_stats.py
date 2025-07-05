import config
import pandas as pd
import os
import yaml
from datetime import datetime

# Load the transcript detail data
data_path = os.path.join(config.DATA_DIR, 'transcript-detail.feather')
df = pd.read_feather(data_path)

# Print the variable names (column names)
print("Variable names in transcript-detail.feather:")
print(df.columns.tolist())

# Also print basic info about the dataset
print(f"\nDataset shape: {df.shape}")
print(f"Number of rows: {df.shape[0]}")
print(f"Number of columns: {df.shape[1]}")

# Filter to transcripts with transcriptid in the transcript_id in
# the query database data/queries.sqlite
import sqlite3

# Connect to the queries database and get unique transcript IDs
conn = sqlite3.connect(config.DATABASE_PATH)
query_transcript_ids = pd.read_sql_query("SELECT DISTINCT transcript_id FROM queries", conn)
conn.close()

# Filter the transcript data to only include transcripts that have queries
initial_count = len(df)
df_filtered = df[df['transcriptid'].isin(query_transcript_ids['transcript_id'])]
filtered_count = len(df_filtered)
dropped_count = initial_count - filtered_count

print(f"\nFiltering Results:")
print(f"Initial transcripts: {initial_count:,}")
print(f"Transcripts with queries: {filtered_count:,}")
print(f"Transcripts dropped: {dropped_count:,} ({dropped_count/initial_count*100:.1f}%)")

# Use filtered data for all subsequent analysis
df = df_filtered

# Calculate summary statistics
n_transcripts = len(df)
n_companies = df['companyid'].nunique()

# Convert date column to datetime if it's not already
df['mostimportantdateutc'] = pd.to_datetime(df['mostimportantdateutc'])

# Calculate date range
first_date = df['mostimportantdateutc'].min()
last_date = df['mostimportantdateutc'].max()

# Calculate audio length statistics
mean_length_seconds = df['audiolengthsec'].mean()

# Create readable description for mean length
mean_minutes = int(mean_length_seconds // 60)
mean_seconds_remainder = int(mean_length_seconds % 60)
mean_length_description = f"{mean_minutes} minutes {mean_seconds_remainder} seconds"

# Calculate total length
total_length_seconds = df['audiolengthsec'].sum()
total_length_hours = total_length_seconds / 3600
total_length_days = total_length_hours / 24
total_length_years = total_length_days / 365.25  # Account for leap years

# Create description of total length
if total_length_years >= 1:
    total_length_description = f"{total_length_years:.2f} years"
elif total_length_days >= 1:
    total_length_description = f"{total_length_days:.1f} days"
else:
    total_length_description = f"{total_length_hours:.1f} hours"

# Create statistics dictionary
stats = {
    'n_transcripts': int(n_transcripts),
    'n_companies': int(n_companies),
    'first_date': first_date.strftime('%Y-%m-%d'),
    'last_date': last_date.strftime('%Y-%m-%d'),
    'mean_length_seconds': float(mean_length_seconds),
    'mean_length_description': mean_length_description,
    'total_length_description': total_length_description,
    'total_length_years': float(total_length_years)
}

# Print statistics
print("\nSummary Statistics:")
for key, value in stats.items():
    print(f"{key}: {value}")

# Save to YAML file
output_dir = os.path.join(config.OUTPUT_DIR, 'yaml')
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'transcript-stats.yaml')

with open(output_path, 'w') as f:
    yaml.dump(stats, f, default_flow_style=False, sort_keys=False)

print(f"\nStatistics saved to: {output_path}")

