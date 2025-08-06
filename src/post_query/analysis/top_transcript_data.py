#!/usr/bin/env python3
"""
Script to create data on the flagged transcripts. Creates a file for data analysis and a file for Joe Harrington to use with more details.

This script:
1. Reads list of top transcripts from top_transcripts.csv
2. Gets queries from the queries table for SimpleCapacityV8.1.1 prompt
3. Aggregates queries by transcriptid with required variables
4. Merges follow-up analysis data from analysis_queries table
5. Merges company name and date from transcript_detail.feather

Output files:
1. data/outputs/top_transcript_data_for_joe.csv - Full dataset with all columns including text fields
   Columns: transcriptid, companyname, mostimportantdateutc, original_score, mean_score_ten_repeats,
   mean_score_all_repeats, mean_follow_up_score, n_queries, n_follow_up_queries, reasoning, excerpts

2. data/datasets/top_transcripts_data.csv - Core dataset for analysis without text fields
   Columns: transcriptid, original_score, mean_score_ten_repeats, mean_score_all_repeats,
   mean_follow_up_score, n_queries, n_follow_up_queries
"""

import sys
import os
import sqlite3
import pandas as pd
import json
import numpy as np

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import config
from modules.utils import extract_score_from_unstructured_response, extract_invalid_response


def extract_from_response(response: str, field: str, default=None):
    """
    Extract a field from a response string using JSON parsing with robust fallback.
    
    Args:
        response: The response string from the database
        field: The field name to extract
        default: Default value to return if field not found or invalid JSON
        
    Returns:
        The extracted field value, or default if not found or invalid JSON
    """
    # Special handling for score fields - use the specialized function
    if field == 'score':
        score = extract_score_from_unstructured_response(response)
        return score if score is not None else default
    
    # For other fields, try JSON parsing first
    try:
        response_dict = json.loads(response)
        if isinstance(response_dict, dict):
            return response_dict.get(field, default)
    except (json.JSONDecodeError, TypeError):
        # If JSON parsing fails, use the robust extraction
        try:
            extracted = extract_invalid_response(response, [field])
            value = extracted.get(field, default)
            return value if value is not None else default
        except:
            pass
    
    return default


def create_top_transcript_data():
    """
    Create top_transcript_data_for_joe.csv with aggregated query data and follow-up analysis.
    """
    print("Starting creation of top_transcript_data_for_joe.csv...")
    
    # Step 1: Read list of top transcripts
    print("Step 1: Reading top transcripts list...")
    top_transcripts_path = os.path.join(config.DATA_DIR, "intermediaries", "top_transcripts.csv")
    top_transcripts_df = pd.read_csv(top_transcripts_path)
    top_transcript_ids = top_transcripts_df['transcriptid'].tolist()
    print(f"Found {len(top_transcript_ids)} top transcript IDs")
    
    # Step 2: Get queries for SimpleCapacityV8.1.1 prompt efficiently
    print("Step 2: Querying database for SimpleCapacityV8.1.1 prompts...")
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # Use parameterized query to avoid SQL injection and improve performance
    placeholders = ','.join(['?'] * len(top_transcript_ids))
    query = f"""
    SELECT query_id, transcriptid, response, date
    FROM queries 
    WHERE prompt_name = 'SimpleCapacityV8.1.1' 
    AND model_name = 'gpt-4o-mini'
    AND transcriptid IN ({placeholders})
    ORDER BY query_id
    """
    
    queries_df = pd.read_sql_query(query, conn, params=top_transcript_ids)
    print(f"Found {len(queries_df)} queries for top transcripts")
    
    # Step 3: Extract scores and other data from responses
    print("Step 3: Extracting data from responses...")
    queries_df['score'] = queries_df['response'].apply(lambda x: extract_from_response(x, 'score'))
    queries_df['reasoning'] = queries_df['response'].apply(lambda x: extract_from_response(x, 'reasoning', ''))
    queries_df['excerpts'] = queries_df['response'].apply(lambda x: extract_excerpts_from_response(x))
    
    # Step 4: Aggregate by transcriptid
    print("Step 4: Aggregating data by transcriptid...")
    
    # Sort by query_id to ensure we get the first query for each transcript
    queries_df = queries_df.sort_values('query_id')
    
    # Custom aggregation function to handle the specific mean calculations
    def custom_aggregation(group):
        n_queries = len(group)
        
        # Original score (first query)
        original_score = group['score'].iloc[0]
        
        # Mean score of all repeats
        mean_score_all_repeats = group['score'].mean()
        
        # Mean score of first 11 queries (first + 10 repeats)
        if n_queries >= 11:
            mean_score_ten_repeats = group['score'].iloc[:11].mean()
        else:
            mean_score_ten_repeats = np.nan
            
        # Other fields from first query
        reasoning = group['reasoning'].iloc[0]
        excerpts = group['excerpts'].iloc[0]
        
        return pd.Series({
            'original_score': original_score,
            'mean_score_ten_repeats': mean_score_ten_repeats,
            'mean_score_all_repeats': mean_score_all_repeats,
            'reasoning': reasoning,
            'excerpts': excerpts,
            'n_queries': n_queries
        })
    
    # Apply custom aggregation
    aggregated_df = queries_df.groupby('transcriptid').apply(custom_aggregation, include_groups=False).reset_index()
    
    # Check for transcripts with fewer than 11 queries and raise warning
    transcripts_with_few_queries = aggregated_df[aggregated_df['n_queries'] < 11]
    if len(transcripts_with_few_queries) > 0:
        print(f"WARNING: {len(transcripts_with_few_queries)} transcripts have fewer than 11 queries:")
        for _, row in transcripts_with_few_queries.iterrows():
            print(f"  - Transcript {row['transcriptid']}: {row['n_queries']} queries")
        print("  mean_score_ten_repeats will be set to NA for these transcripts.")
    
    # Step 5: Get follow-up analysis data
    print("Step 5: Getting follow-up analysis data...")
    
    # Get all query_ids for the top transcripts to use in analysis query
    top_query_ids = queries_df['query_id'].tolist()
    
    if top_query_ids:
        # Query analysis_queries table for follow-up data in batches to avoid SQL limit
        batch_size = 500  # SQLite typically supports ~999 parameters
        analysis_dfs = []
        
        for i in range(0, len(top_query_ids), batch_size):
            batch_ids = top_query_ids[i:i + batch_size]
            analysis_placeholders = ','.join(['?'] * len(batch_ids))
            analysis_query = f"""
            SELECT reference_query_id, response
            FROM analysis_queries 
            WHERE reference_query_id IN ({analysis_placeholders})
            """
            
            batch_df = pd.read_sql_query(analysis_query, conn, params=batch_ids)
            analysis_dfs.append(batch_df)
        
        # Combine all batches
        analysis_df = pd.concat(analysis_dfs, ignore_index=True) if analysis_dfs else pd.DataFrame()
        
        # Extract follow-up scores
        analysis_df['follow_up_score'] = analysis_df['response'].apply(lambda x: extract_from_response(x, 'score'))
        
        # Merge with queries_df to get transcriptid
        follow_up_with_transcript = pd.merge(
            analysis_df, 
            queries_df[['query_id', 'transcriptid']], 
            left_on='reference_query_id', 
            right_on='query_id',
            how='left'
        )
        
        # Aggregate follow-up data by transcriptid
        transcript_follow_up = follow_up_with_transcript.groupby('transcriptid').agg({
            'follow_up_score': 'mean',
            'reference_query_id': 'count'
        }).reset_index()
        
        # Rename columns
        transcript_follow_up.columns = ['transcriptid', 'mean_follow_up_score', 'n_follow_up_queries']
        
        # Merge with aggregated_df
        aggregated_df = pd.merge(
            aggregated_df, 
            transcript_follow_up, 
            on='transcriptid', 
            how='left'
        )
    else:
        # No follow-up data found
        aggregated_df['mean_follow_up_score'] = np.nan
        aggregated_df['n_follow_up_queries'] = 0
    
    # Step 6: Merge with transcript details
    print("Step 6: Merging with transcript details...")
    transcript_detail_df = pd.read_feather(config.TRANSCRIPT_DETAIL_PATH)
    
    # Select only the columns we need
    transcript_detail_subset = transcript_detail_df[['transcriptid', 'companyname', 'mostimportantdateutc']].copy()
    
    # Merge with aggregated data
    final_df = pd.merge(
        aggregated_df, 
        transcript_detail_subset, 
        on='transcriptid', 
        how='left'
    )
    
    # Close database connection
    conn.close()
    
    # Reorder columns
    column_order = [
        'transcriptid',
        'companyname',
        'mostimportantdateutc',
        'original_score',
        'mean_score_ten_repeats',
        'mean_score_all_repeats',
        'mean_follow_up_score',
        'n_queries',
        'n_follow_up_queries',
        'reasoning',
        'excerpts'
    ]
    
    # Reorder columns (only include columns that exist)
    existing_columns = [col for col in column_order if col in final_df.columns]
    final_df = final_df[existing_columns]
    
    # Step 7: Save to CSV
    print("Step 7: Saving to CSV...")
    # Create outputs directory if it doesn't exist
    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    output_path = os.path.join(config.OUTPUTS_DIR, "top_transcript_data_for_joe.csv")
    final_df.to_csv(output_path, index=False)
    
    print(f"Successfully created {output_path}")
    
    # Step 8: Save core dataset version without merged variables and text fields
    print("Step 8: Saving core dataset version...")
    # Create datasets directory if it doesn't exist
    datasets_dir = os.path.join(config.DATA_DIR, "datasets")
    os.makedirs(datasets_dir, exist_ok=True)
    
    # Select only core variables (drop companyname, mostimportantdateutc, reasoning, excerpts)
    core_columns = [
        'transcriptid',
        'original_score',
        'mean_score_ten_repeats',
        'mean_score_all_repeats',
        'mean_follow_up_score',
        'n_queries',
        'n_follow_up_queries'
    ]
    
    # Filter to only include columns that exist in the dataframe
    existing_core_columns = [col for col in core_columns if col in final_df.columns]
    core_df = final_df[existing_core_columns].copy()
    
    # Save core dataset
    core_output_path = os.path.join(datasets_dir, "top_transcripts_data.csv")
    core_df.to_csv(core_output_path, index=False)
    
    print(f"Successfully created {core_output_path}")
    print(f"Core dataset has {len(core_df)} rows and {len(core_df.columns)} columns")
    print(f"Core columns: {list(core_df.columns)}")
    
    print(f"Full dataset has {len(final_df)} rows")
    print(f"Full columns: {list(final_df.columns)}")
    
    # Show summary statistics
    print("\nSummary statistics:")
    print(f"Transcripts with follow-up analysis: {final_df['n_follow_up_queries'].sum()}")
    print(f"Average original score: {final_df['original_score'].mean():.2f}")
    print(f"Average mean score (ten repeats): {final_df['mean_score_ten_repeats'].mean():.2f}")
    print(f"Average mean score (all repeats): {final_df['mean_score_all_repeats'].mean():.2f}")
    if not final_df['mean_follow_up_score'].isna().all():
        print(f"Average follow-up score: {final_df['mean_follow_up_score'].mean():.2f}")
    
    return final_df


def extract_excerpts_from_response(response: str) -> str:
    """
    Extract excerpts from a response string using JSON parsing with robust fallback.
    Special handling for excerpts since they might be a list that needs to be joined.
    
    Args:
        response: The response string from the database
        
    Returns:
        str: The extracted excerpts as a string, or empty string if not found or invalid JSON
    """
    # Try JSON parsing first
    try:
        response_dict = json.loads(response)
        if isinstance(response_dict, dict):
            excerpts = response_dict.get('excerpts', [])
            if isinstance(excerpts, list):
                return '; '.join(excerpts)
            return str(excerpts)
    except (json.JSONDecodeError, TypeError):
        # If JSON parsing fails, use the robust extraction
        try:
            extracted = extract_invalid_response(response, ['excerpts'])
            excerpts = extracted.get('excerpts', '')
            
            # The extracted excerpts might still be a string representation of a list
            # Try to clean it up
            if excerpts:
                # Remove brackets if present
                excerpts = excerpts.strip()
                if excerpts.startswith('[') and excerpts.endswith(']'):
                    excerpts = excerpts[1:-1]
                # Clean up quotes and split by common delimiters
                excerpts = excerpts.replace('"', '').replace("'", '')
                # If there are multiple excerpts separated by commas, join them with semicolons
                if ',' in excerpts:
                    parts = [part.strip() for part in excerpts.split(',')]
                    return '; '.join(parts)
                return excerpts
        except:
            pass
    
    return ''


if __name__ == "__main__":
    try:
        result_df = create_top_transcript_data()
        print("\nScript completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
