import pandas as pd
import argparse
from typing import List, Optional
from modules.llm import LLMQuery
import config
import os

def get_transcript_ids(
    company_ids: List[str],
    transcript_ids: Optional[List[str]] = None
) -> List[str]:
    """
    Get transcript IDs for specified companies and optional specific transcripts.
    
    Args:
        company_ids: List of company IDs to get transcripts for
        transcript_ids: Optional list of specific transcript IDs to filter by
    
    Returns:
        List of transcript IDs
    """
    # Read the companies-transcripts.csv file
    csv_path = os.path.join(config.DATA_DIR, 'companies-transcripts.csv')
    print(f"Looking for CSV file at: {csv_path}")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Could not find companies-transcripts.csv at {csv_path}")
    
    # Read the CSV file
    print(f"Reading CSV file...")
    df = pd.read_csv(csv_path)
    print(f"Total rows in CSV: {len(df)}")
    
    # Convert company IDs to float for comparison (since they're stored as float in the CSV)
    company_ids = [float(cid) for cid in company_ids]
    print(f"Filtering for company IDs: {company_ids}")
    
    # Filter by company IDs (they're already float in the DataFrame)
    df = df[df['companyid'].isin(company_ids)]
    print(f"Rows after company ID filter: {len(df)}")
    
    # If specific transcript IDs are provided, filter by those
    if transcript_ids:
        print(f"Filtering for transcript IDs: {transcript_ids}")
        df = df[df['transcriptid'].isin(transcript_ids)]
        print(f"Rows after transcript ID filter: {len(df)}")
    
    result = df['transcriptid'].tolist()
    print(f"Final number of transcript IDs: {len(result)}")
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Run prompts on specified company transcripts')
    parser.add_argument('prompt_name', help='Name of the prompt to run (must exist in prompts.json)')
    parser.add_argument('company_ids', nargs='+', help='Company IDs to process')
    parser.add_argument('--transcripts', nargs='+', help='Optional specific transcript IDs to process')
    
    args = parser.parse_args()
    
    # Get transcript IDs based on company IDs and optional transcript filter
    transcript_ids = get_transcript_ids(args.company_ids, args.transcripts)
    
    if not transcript_ids:
        print("No transcripts found matching the specified criteria")
        return
    
    print(f"Running prompt '{args.prompt_name}' on {len(transcript_ids)} transcripts")
    
    # Initialize LLM query
    llm_query = LLMQuery()
    
    # Run prompt on transcripts
    responses = llm_query.apply_prompt_to_transcripts(
        args.prompt_name,
        transcript_ids
    )
    
    print(f"Successfully processed {len(responses)} transcripts")
    print("Responses have been saved to the database")

if __name__ == '__main__':
    main() 