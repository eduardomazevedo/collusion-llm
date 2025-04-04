import pandas as pd
import numpy as np
import json
import argparse
import time
from typing import List, Optional
from modules.llm import LLMQuery
import config

def load_human_ratings() -> pd.DataFrame:
    """Load the human ratings data from CSV."""
    return pd.read_csv(config.HUMAN_RATINGS_PATH)

def get_test_transcripts(
    df: pd.DataFrame,
    source: Optional[str] = None,
    balanced_subset_size: Optional[int] = None
) -> List[int]:
    """
    Get transcript IDs based on filtering criteria.
    
    Args:
        df: DataFrame with human ratings
        source: 'joe' or 'acl' to filter by source
        balanced_subset_size: If provided, return a balanced random subset of this size
    
    Returns:
        List of transcript IDs
    """
    # First filter by source if specified
    if source == 'joe':
        df = df[df['joe_score'].notna()]
        if balanced_subset_size:
            # For Joe's scores, balance between zero and positive scores
            positive_scores = df[df['joe_score'] > 0]['transcriptid'].tolist()
            zero_scores = df[df['joe_score'] == 0]['transcriptid'].tolist()
            
            # Calculate how many of each we need
            n_positive = balanced_subset_size // 2
            n_zero = balanced_subset_size - n_positive
            
            # Check if we have enough samples
            if len(positive_scores) < n_positive or len(zero_scores) < n_zero:
                raise ValueError(
                    f"Not enough samples for balanced subset of size {balanced_subset_size}. "
                    f"Available: {len(positive_scores)} positive, {len(zero_scores)} zero scores"
                )
            
            # Randomly sample from each group
            selected_positive = np.random.choice(positive_scores, size=n_positive, replace=False)
            selected_zero = np.random.choice(zero_scores, size=n_zero, replace=False)
            
            return np.concatenate([selected_positive, selected_zero]).tolist()
            
    elif source == 'acl':
        df = df[df['acl_manual_flag'].notna()]
        if balanced_subset_size:
            # For ACL scores, balance between zero and one flags
            positive_flags = df[df['acl_manual_flag'] == 1]['transcriptid'].tolist()
            zero_flags = df[df['acl_manual_flag'] == 0]['transcriptid'].tolist()
            
            # Calculate how many of each we need
            n_positive = balanced_subset_size // 2
            n_zero = balanced_subset_size - n_positive
            
            # Check if we have enough samples
            if len(positive_flags) < n_positive or len(zero_flags) < n_zero:
                raise ValueError(
                    f"Not enough samples for balanced subset of size {balanced_subset_size}. "
                    f"Available: {len(positive_flags)} positive flags, {len(zero_flags)} zero flags"
                )
            
            # Randomly sample from each group
            selected_positive = np.random.choice(positive_flags, size=n_positive, replace=False)
            selected_zero = np.random.choice(zero_flags, size=n_zero, replace=False)
            
            return np.concatenate([selected_positive, selected_zero]).tolist()
    else:
        # If no source specified, include all transcripts with any human rating
        df = df[df['joe_score'].notna() | df['acl_manual_flag'].notna()]
        if balanced_subset_size:
            # For mixed source, consider both Joe's scores and ACL flags
            # Get positive cases from both sources
            joe_positives = df[df['joe_score'] > 0]['transcriptid'].tolist()
            acl_positives = df[df['acl_manual_flag'] == 1]['transcriptid'].tolist()
            # Combine and remove duplicates
            positive_cases = list(set(joe_positives + acl_positives))
            
            # Get negative cases from both sources
            joe_negatives = df[df['joe_score'] == 0]['transcriptid'].tolist()
            acl_negatives = df[df['acl_manual_flag'] == 0]['transcriptid'].tolist()
            # Combine and remove duplicates
            negative_cases = list(set(joe_negatives + acl_negatives))
            
            # Calculate how many of each we need
            n_positive = balanced_subset_size // 2
            n_negative = balanced_subset_size - n_positive
            
            # Check if we have enough samples
            if len(positive_cases) < n_positive or len(negative_cases) < n_negative:
                raise ValueError(
                    f"Not enough samples for balanced subset of size {balanced_subset_size}. "
                    f"Available: {len(positive_cases)} positive, {len(negative_cases)} negative cases"
                )
            
            # Randomly sample from each group
            selected_positive = np.random.choice(positive_cases, size=n_positive, replace=False)
            selected_negative = np.random.choice(negative_cases, size=n_negative, replace=False)
            
            return np.concatenate([selected_positive, selected_negative]).tolist()
    
    return df['transcriptid'].tolist()

def main():
    parser = argparse.ArgumentParser(description='Run batch processing on test transcripts')
    parser.add_argument('prompt_name', help='Name of the prompt to run')
    parser.add_argument('--source', choices=['joe', 'acl'], help='Source of transcripts')
    parser.add_argument('--balanced', type=int, help='Number of balanced transcripts to select')
    parser.add_argument('--metadata', type=str, help='JSON string with metadata for the batch job')
    
    args = parser.parse_args()
    
    print("\n=== Starting Batch Processing ===")
    print(f"Prompt: {args.prompt_name}")
    if args.source:
        print(f"Source: {args.source}")
    if args.balanced:
        print(f"Balanced subset size: {args.balanced}")
    
    # Load human ratings
    print("\nLoading human ratings data...")
    df = load_human_ratings()
    
    # Get transcript IDs based on criteria
    print("Selecting transcripts...")
    transcript_ids = get_test_transcripts(df, args.source, args.balanced)
    print(f"Selected {len(transcript_ids)} transcripts for processing")
    
    # Parse metadata if provided
    metadata = json.loads(args.metadata) if args.metadata else None
    if metadata:
        print(f"Batch metadata: {json.dumps(metadata, indent=2)}")
    
    # Initialize LLM query object
    print("\nInitializing LLM query...")
    llm_query = LLMQuery()
    
    # Process transcripts in batch
    print("\n=== Submitting Batch Job ===")
    print(f"Creating batch input file for {len(transcript_ids)} transcripts...")
    results = llm_query.process_batch(
        prompt_name=args.prompt_name,
        transcript_ids=transcript_ids,
        metadata=metadata
    )
    
    print("\n=== Batch Job Status ===")
    print("✓ Batch job submitted successfully!")
    print(f"✓ Number of transcripts processed: {len(results)}")
    print("✓ Responses saved to database")
    
    # Update leaderboard
    print("\nUpdating leaderboard...")
    from src.py.make.create_leaderboard import main as update_leaderboard
    update_leaderboard()
    print("✓ Leaderboard updated successfully!")
    
    print("\n=== Batch Processing Complete ===")
    print("Note: Batch results will be available within 24 hours.")
    print("You can check the status of your batch job using the batch ID in the OpenAI dashboard.")

if __name__ == "__main__":
    main() 