import pandas as pd
import numpy as np
from modules.llm import LLMQuery
import config
import argparse
from typing import List, Optional
import logging
import sys
import time

def load_human_ratings() -> pd.DataFrame:
    """Load the human ratings data from CSV."""
    try:
        df = pd.read_csv(config.HUMAN_RATINGS_PATH)
        logging.info(f"Loaded {len(df)} human ratings from {config.HUMAN_RATINGS_PATH}")
        return df
    except FileNotFoundError:
        logging.error(f"Human ratings file not found at {config.HUMAN_RATINGS_PATH}")
        raise
    except pd.errors.EmptyDataError:
        logging.error(f"Human ratings file is empty: {config.HUMAN_RATINGS_PATH}")
        raise
    except Exception as e:
        logging.error(f"Error loading human ratings: {e}")
        raise

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
                    f"Available: {len(positive_cases)} positive cases, {len(negative_cases)} negative cases"
                )
            
            # Randomly sample from each group
            selected_positive = np.random.choice(positive_cases, size=n_positive, replace=False)
            selected_negative = np.random.choice(negative_cases, size=n_negative, replace=False)
            
            return np.concatenate([selected_positive, selected_negative]).tolist()
    
    # If no balanced subset requested, return all filtered transcripts
    return df['transcriptid'].tolist()

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Run prompts on transcripts with human ratings')
    parser.add_argument('prompt_name', help='Name of the prompt to run (must exist in prompts.json)')
    parser.add_argument('--source', choices=['joe', 'acl'], help='Filter transcripts by source of human rating')
    parser.add_argument('--balanced-subset', type=int, help='Run on a balanced random subset of this size')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum number of retries for API failures (default: 3)')
    parser.add_argument('--retry-delay', type=int, default=5,
                       help='Delay in seconds between retries (default: 5)')
    
    args = parser.parse_args()
    
    try:
        # Set random seed for reproducibility if using balanced subset
        if args.balanced_subset:
            np.random.seed(42)
            logging.info(f"Using random seed 42 for balanced subset of {args.balanced_subset}")
        
        # Load human ratings
        df = load_human_ratings()
        
        # Get transcript IDs based on filtering criteria
        try:
            transcript_ids = get_test_transcripts(df, args.source, args.balanced_subset)
            logging.info(f"Selected {len(transcript_ids)} transcripts for benchmarking")
        except ValueError as e:
            logging.error(f"Error selecting transcripts: {e}")
            return 1
        
        print(f"Running prompt '{args.prompt_name}' on {len(transcript_ids)} transcripts")
        
        # Initialize LLM query
        try:
            llm_query = LLMQuery()
        except Exception as e:
            logging.error(f"Failed to initialize LLM query: {e}")
            return 1
        
        # Run prompt on transcripts with retry logic
        retries = 0
        while retries <= args.max_retries:
            try:
                responses = llm_query.apply_prompt_to_transcripts(
                    args.prompt_name,
                    transcript_ids
                )
                break  # Success, exit retry loop
            except Exception as e:
                retries += 1
                if retries > args.max_retries:
                    logging.error(f"Failed after {args.max_retries} retries: {e}")
                    return 1
                else:
                    logging.warning(f"Attempt {retries} failed: {e}. Retrying in {args.retry_delay} seconds...")
                    time.sleep(args.retry_delay)
        
        print(f"Successfully processed {len(responses)} transcripts")
        print("Responses have been saved to the database")
        return 0
        
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 