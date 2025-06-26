"""
Script to extract and process data for top transcripts.

This script:
1. Loads the list of top transcripts from data/top_transcripts.csv
2. Queries the SQLite database for SimpleCapacityV8.1.1 prompts with gpt-4o-mini model
3. Keeps the string data from the first query, plus mean score and number of observations from the additional queries.
4. Saves the data to data/top_transcripts_data.csv
"""

#%% Start
import sqlite3
import os
from pathlib import Path
import pandas as pd
import json
import config


#%% Load top transcripts CSV
top_transcripts_df = pd.read_csv('data/top_transcripts.csv')
print(f"Loaded {len(top_transcripts_df)} top transcripts")
print(top_transcripts_df.head())

#%% Load queries from SQLite database efficiently
conn = sqlite3.connect('data/queries.sqlite')

# Get top transcript IDs as a set for efficient lookup
top_transcript_ids = set(top_transcripts_df['transcript_id'].tolist())

# Convert to tuple for SQL IN clause (more efficient than string formatting)
id_list = tuple(top_transcript_ids)
if len(id_list) == 1:
    # Handle single item tuple syntax
    id_list = f"({id_list[0]},)"

# Query only the data we need using SQL filtering
query = f"SELECT * FROM queries WHERE transcript_id IN {id_list} AND prompt_name = 'SimpleCapacityV8.1.1' AND model_name = 'gpt-4o-mini'"
filtered_queries_df = pd.read_sql_query(query, conn)
conn.close()

print(f"Loaded {len(filtered_queries_df)} queries from top transcripts")
print(filtered_queries_df.head())

#%% Summary statistics
print(f"Top transcripts: {len(top_transcript_ids)}")
print(f"Filtered queries: {len(filtered_queries_df)}")
print(f"Coverage: {len(filtered_queries_df['transcript_id'].unique())} unique transcripts found in queries")


# %% Sort and drop columns
# Sort by query_id and drop unnecessary columns
filtered_queries_df = filtered_queries_df.sort_values('query_id').drop(
    columns=['date', 'LLM_provider', 'model_name', 'call_type', 'temperature', 'max_response', 'input_tokens', 'output_tokens', 'prompt_name']
)

print("DataFrame after sorting and dropping columns:")
print(filtered_queries_df.head())
print(f"\nColumns remaining: {list(filtered_queries_df.columns)}")


# %% Extract JSON data from response column
# Function to safely extract JSON data
def extract_json_data(response_str):
    """Extract JSON data from response string, return empty dict if parsing fails"""
    try:
        return json.loads(response_str)
    except (json.JSONDecodeError, TypeError):
        return {}

# Extract JSON data from response column and add as new columns
json_data = filtered_queries_df['response'].apply(extract_json_data)
json_df = pd.json_normalize(json_data)

# Add JSON columns directly to the existing DataFrame
for col in json_df.columns:
    filtered_queries_df[col] = json_df[col]

# Drop the original response column since we've extracted its contents
filtered_queries_df = filtered_queries_df.drop(columns=['response'])

print("DataFrame after extracting JSON response:")
print(filtered_queries_df.head())
print(f"\nColumns after JSON extraction: {list(filtered_queries_df.columns)}")
print(f"\nShape: {filtered_queries_df.shape}")


# Group by transcript_id and perform operations
top_transcripts_data = filtered_queries_df.groupby('transcript_id').agg({
    'query_id': 'first',
    'score': ['first', 'mean', 'count'],
    'reasoning': 'first', 
    'excerpts': 'first'
}).reset_index()

# Flatten column names
top_transcripts_data.columns = ['transcript_id', 'query_id', 'original_score', 'mean_score', 'n_queries', 'reasoning', 'excerpts']

print("Top transcripts data after grouping:")
print(top_transcripts_data.head())
print(f"\nShape: {top_transcripts_data.shape}")
print(f"\nColumns: {list(top_transcripts_data.columns)}")


#%% Save
# Save the top transcripts data to CSV
output_path = os.path.join(config.DATA_DIR, "top_transcripts_data.csv")
top_transcripts_data.to_csv(output_path, index=False)

print(f"Saved top transcripts data to: {output_path}")
print(f"Total transcripts: {len(top_transcripts_data)}")
print(f"Average score: {top_transcripts_data['mean_score'].mean():.2f}")
print(f"Average queries per transcript: {top_transcripts_data['n_queries'].mean():.1f}")
