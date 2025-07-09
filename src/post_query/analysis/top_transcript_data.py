#!/usr/bin/env python3
"""
Script to create top_transcripts_data.csv with aggregated query data and follow-up analysis.

This script:
1. Reads list of top transcripts from top_transcripts.csv
2. Gets queries from the queries table for SimpleCapacityV8.1.1 prompt
3. Aggregates queries by transcriptid with required variables
4. Merges follow-up analysis data from analysis_queries table
5. Merges company name and date from transcript-detail.feather
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


def extract_from_response(response: str, field: str, default=None):
    """
    Extract a field from a response string using JSON parsing.
    
    Args:
        response: The response string from the database
        field: The field name to extract
        default: Default value to return if field not found or invalid JSON
        
    Returns:
        The extracted field value, or default if not found or invalid JSON
    """
    try:
        response_dict = json.loads(response)
        if isinstance(response_dict, dict):
            return response_dict.get(field, default)
    except (json.JSONDecodeError, TypeError):
        pass
    
    return default


def create_top_transcript_data():
    """
    Create top_transcript_data.csv with aggregated query data and follow-up analysis.
    """
    print("Starting creation of top_transcript_data.csv...")
    
    # Step 1: Read list of top transcripts
    print("Step 1: Reading top transcripts list...")
    top_transcripts_path = os.path.join(config.DATA_DIR, "top_transcripts.csv")
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
    
    # Group by transcriptid and aggregate
    aggregated_df = queries_df.groupby('transcriptid').agg({
        'score': ['first', 'mean'],  # first score as original_score, mean as mean_score
        'reasoning': 'first',        # reasoning from first query
        'excerpts': 'first',         # excerpts from first query
        'query_id': 'count'          # count of queries
    }).reset_index()
    
    # Flatten column names
    aggregated_df.columns = ['transcriptid', 'original_score', 'mean_score', 'reasoning', 'excerpts', 'n_queries']
    
    # Step 5: Get follow-up analysis data
    print("Step 5: Getting follow-up analysis data...")
    
    # Get all query_ids for the top transcripts to use in analysis query
    top_query_ids = queries_df['query_id'].tolist()
    
    if top_query_ids:
        # Query analysis_queries table for follow-up data
        analysis_placeholders = ','.join(['?'] * len(top_query_ids))
        analysis_query = f"""
        SELECT reference_query_id, response
        FROM analysis_queries 
        WHERE reference_query_id IN ({analysis_placeholders})
        """
        
        analysis_df = pd.read_sql_query(analysis_query, conn, params=top_query_ids)
        
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
        'mean_score',
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
    output_path = os.path.join(config.DATA_DIR, "top_transcripts_data.csv")
    final_df.to_csv(output_path, index=False)
    
    print(f"Successfully created {output_path}")
    print(f"Final dataset has {len(final_df)} rows")
    print(f"Columns: {list(final_df.columns)}")
    
    # Show summary statistics
    print("\nSummary statistics:")
    print(f"Transcripts with follow-up analysis: {final_df['n_follow_up_queries'].sum()}")
    print(f"Average original score: {final_df['original_score'].mean():.2f}")
    print(f"Average mean score: {final_df['mean_score'].mean():.2f}")
    if not final_df['mean_follow_up_score'].isna().all():
        print(f"Average follow-up score: {final_df['mean_follow_up_score'].mean():.2f}")
    
    return final_df


def extract_excerpts_from_response(response: str) -> str:
    """
    Extract excerpts from a response string using JSON parsing.
    Special handling for excerpts since they might be a list that needs to be joined.
    
    Args:
        response: The response string from the database
        
    Returns:
        str: The extracted excerpts as a string, or empty string if not found or invalid JSON
    """
    try:
        response_dict = json.loads(response)
        if isinstance(response_dict, dict):
            excerpts = response_dict.get('excerpts', [])
            if isinstance(excerpts, list):
                return '; '.join(excerpts)
            return str(excerpts)
    except (json.JSONDecodeError, TypeError):
        pass
    
    return ''


if __name__ == "__main__":
    try:
        result_df = create_top_transcript_data()
        print("\nScript completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
