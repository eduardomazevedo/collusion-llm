"""
Script to extract top transcript list from the database.

This script:
1. Queries the database for only SimpleCapacityV8.1.1 prompts
2. For each transcriptid, keeps only the smallest query_id (earliest query)
3. Extracts the "score" field from the JSON response
4. Keeps only rows with score >= 75
5. Saves only the transcriptid column to data/top_transcripts.csv
"""

import sys
import os
import sqlite3
import pandas as pd
import json

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import config


def extract_top_transcripts():
    """
    Extract SimpleCapacityV8.1.1 prompts from the database,
    keeping only the earliest query for each transcriptid,
    extracting the score from JSON response,
    filtering for score >= 75,
    and save only transcriptid to a CSV file.
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(config.DATABASE_PATH)
        
        # Query only the specific prompt, keeping the smallest query_id for each transcriptid
        # Only select the columns we want
        query = """
        SELECT query_id, prompt_name, transcriptid, response
        FROM queries 
        WHERE prompt_name = 'SimpleCapacityV8.1.1' 
        AND query_id IN (
            SELECT MIN(query_id) 
            FROM queries 
            WHERE prompt_name = 'SimpleCapacityV8.1.1' 
            GROUP BY transcriptid
        )
        ORDER BY query_id
        """
        
        # Read the data into a DataFrame
        df = pd.read_sql_query(query, conn)
        
        # Close the connection
        conn.close()
        
        # Extract score from JSON response
        scores = []
        for response in df['response']:
            try:
                response_data = json.loads(response)
                score = response_data.get('score', 0)
                scores.append(score)
            except (json.JSONDecodeError, KeyError, TypeError):
                scores.append(0)
        
        # Add score column
        df['score'] = scores
        
        # Filter for score >= 75
        df_filtered = df[df['score'] >= 75].copy()
        
        # Sort by score descending
        df_filtered = df_filtered.sort_values('score', ascending=False)
        
        # Save only transcriptid to CSV
        output_path = os.path.join(config.DATA_DIR, "top_transcripts.csv")
        df_filtered[['transcriptid']].to_csv(output_path, index=False)
        
        print(f"Extracted {len(df)} total rows from SimpleCapacityV8.1.1 prompts")
        print(f"Filtered to {len(df_filtered)} rows with score >= 75")
        print(f"Saved transcriptids to: {output_path}")
        
        # Show a preview of the data
        print("\nPreview of extracted data (score >= 75):")
        print("=" * 50)
        print(df_filtered[['transcriptid', 'score']].head())
        
        # Show unique transcript count
        unique_transcripts = df_filtered['transcriptid'].nunique()
        print(f"\nUnique transcripts with score >= 75: {unique_transcripts}")
        
        # Show score statistics
        if len(df_filtered) > 0:
            print(f"\nScore statistics:")
            print(f"  Min score: {df_filtered['score'].min()}")
            print(f"  Max score: {df_filtered['score'].max()}")
            print(f"  Mean score: {df_filtered['score'].mean():.1f}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    extract_top_transcripts() 