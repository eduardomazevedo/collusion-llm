#!/usr/bin/env python3
"""
Script to export token sizes for all transcripts in companies-transcripts.csv.
Usage:
    python export_token_sizes.py
"""

import os
import pandas as pd
from modules.utils import get_token_size
import config

def main():
    # Read the companies-transcripts.csv file
    csv_path = os.path.join(config.DATA_DIR, 'companies-transcripts.csv')
    try:
        df = pd.read_csv(csv_path, header=0, names=['companyid', 'companyname', 'transcriptid', 'headline'])
    except FileNotFoundError:
        print(f"Error: Could not find companies-transcripts.csv at {csv_path}")
        return

    # Get unique transcript IDs
    transcript_ids = df['transcriptid'].unique()
    total_transcripts = len(transcript_ids)
    print(f"Found {total_transcripts} unique transcripts")

    # Check if transcript-tokens.csv exists and load it
    output_path = os.path.join(config.DATA_DIR, 'transcript-tokens.csv')
    if os.path.exists(output_path):
        try:
            results_df = pd.read_csv(output_path, header=0, names=['transcriptid', 'tokensize'])
            processed_ids = set(results_df['transcriptid'].unique())
            print(f"Found {len(processed_ids)} already processed transcripts")
        except Exception as e:
            print(f"Error reading existing transcript-tokens.csv: {str(e)}")
            results_df = pd.DataFrame(columns=['transcriptid', 'tokensize'])
            processed_ids = set()
    else:
        results_df = pd.DataFrame(columns=['transcriptid', 'tokensize'])
        processed_ids = set()

    # Filter out already processed transcripts
    remaining_ids = [tid for tid in transcript_ids if tid not in processed_ids]
    print(f"Remaining transcripts to process: {len(remaining_ids)}")

    # Process each transcript
    for i, transcript_id in enumerate(remaining_ids, 1):
        try:
            token_size = get_token_size(int(transcript_id))
            current_progress = len(processed_ids) + i
            
            # Add new result to the dataframe
            new_row = pd.DataFrame({
                'transcriptid': [transcript_id],
                'tokensize': [token_size]
            })
            results_df = pd.concat([results_df, new_row], ignore_index=True)
            
            # Save progress every 100 transcripts or on the last transcript
            if i % 100 == 0 or i == len(remaining_ids):
                results_df.to_csv(output_path, index=False)
                print(f"Saved progress: {current_progress}/{total_transcripts} transcripts processed")
                
        except Exception as e:
            print(f"Error processing transcript {transcript_id}: {str(e)}")
            # Add failed transcript with None token size
            new_row = pd.DataFrame({
                'transcriptid': [transcript_id],
                'tokensize': [None]
            })
            results_df = pd.concat([results_df, new_row], ignore_index=True)

    print(f"Processing complete. Results saved to {output_path}")

if __name__ == "__main__":
    main() 