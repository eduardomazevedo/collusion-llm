#!/usr/bin/env python3
"""
Script to run batch processing operations for given company IDs.
Usage:
    python batch_processor_runner.py <company_ids> <prompt_name> [--operation <operation>]
    
Operations:
    create: Create batch input file
    submit: Submit batch job
    status: Check batch status
    process: Process batch results
    error: Check batch error information
    models: List available models
    all: Run all operations in sequence
"""

import argparse
import os
import pandas as pd
from modules.batch_processor import BatchProcessor
import config

def get_transcript_ids(company_ids):
    """
    Get transcript IDs for given company IDs from companies_transcripts.csv.
    
    Args:
        company_ids: List of company IDs or a single company ID
        
    Returns:
        List of transcript IDs as integers
    """
    # Convert single company ID to list if needed
    if isinstance(company_ids, (int, str)):
        company_ids = [company_ids]
    
    # Convert company IDs to strings for comparison
    company_ids = [str(cid) for cid in company_ids]
    
    # Read the companies_transcripts.csv file
    csv_path = os.path.join(config.DATA_DIR, 'companies_transcripts.csv')
    try:
        df = pd.read_csv(csv_path, names=['companyid', 'companyname', 'transcriptid', 'headline'])
    except FileNotFoundError:
        print(f"Error: Could not find companies_transcripts.csv at {csv_path}")
        return []
    
    # Filter for the given company IDs
    df_filtered = df[df['companyid'].astype(str).isin(company_ids)]
    
    if df_filtered.empty:
        print(f"No transcripts found for company IDs: {company_ids}")
        return []
    
    # Get transcript IDs and convert to integers
    transcript_ids = [int(tid) for tid in df_filtered['transcriptid'].unique()]
    print(f"Loaded {len(transcript_ids)} transcripts")
    
    return transcript_ids

def create_batch_input(company_ids, prompt_name, output_path):
    """Create batch input file for given company IDs."""
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    transcript_ids = get_transcript_ids(company_ids)
    
    if not transcript_ids:
        print(f"No transcripts found for company IDs: {company_ids}")
        return None
    
    print(f"Creating batch input file with {len(transcript_ids)} transcripts...")
    return processor.create_batch_input_file(
        prompt_name=prompt_name,
        transcriptids=transcript_ids,  # This is now a List[int]
        output_path=output_path
    )

def submit_batch(input_file):
    """Submit batch job."""
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    print("Submitting batch job...")
    return processor.submit_batch(input_file)

def check_batch_status(batch_id):
    """Check batch status."""
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    print(f"Checking status of batch {batch_id}...")
    return processor.check_batch_status(batch_id)

def process_batch_results(batch_id, prompt_name):
    """Process batch results."""
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    print(f"Processing results for batch {batch_id}...")
    results = processor.process_batch_results(batch_id, prompt_name)
    if not results:
        print("No results to process yet. The batch is still in progress.")
        return
    print(f"Processed {len(results)} results")
    return results

def check_batch_error(batch_id):
    """Check batch error information."""
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    print(f"Checking error information for batch {batch_id}...")
    error_info = processor.check_batch_error(batch_id)
    
    print(f"\nBatch Status: {error_info['status']}")
    
    if error_info["error_message"]:
        print(f"Error Message: {error_info['error_message']}")
    
    if error_info["error_file_id"]:
        print(f"Error File ID: {error_info['error_file_id']}")
        if error_info["error_content"]:
            print("\nError File Content:")
            print(error_info["error_content"])
    
    return error_info

def list_models():
    """List available models."""
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    print("\nListing available models...")
    models = processor.list_available_models()
    print("\nAvailable models:")
    for model in sorted(models):
        print(f"- {model}")
    return models

def main():
    parser = argparse.ArgumentParser(description='Run batch processing operations for company IDs')
    parser.add_argument('company_ids', help='Company ID(s) to process (comma-separated if multiple)')
    parser.add_argument('prompt_name', help='Name of the prompt to use')
    parser.add_argument('--batch-id', help='Batch ID for status/process/error operations')
    parser.add_argument('--input-file', help='Input file path (relative) for submit operation')
    parser.add_argument('--operation', choices=['create', 'submit', 'status', 'process', 'error', 'models', 'all'],
                      default='all', help='Operation to perform')
    args = parser.parse_args()
    
    if args.operation == 'models':
        list_models()
        return
        
    # Parse company IDs and convert to integers
    try:
        company_ids = [int(cid.strip()) for cid in args.company_ids.split(',')]
    except ValueError:
        print("Error: Company IDs must be integers")
        return
    
    # Set up output directory
    output_dir = os.path.join(config.OUTPUT_DIR, 'batch_inputs')
    os.makedirs(output_dir, exist_ok=True)
    
    if args.operation == 'create':
        output_path = os.path.join(output_dir, f"{args.prompt_name}_input.jsonl")
        input_file = create_batch_input(company_ids, args.prompt_name, output_path)
        if not input_file:
            return
        
        print(f"Batch input file created: {input_file}")
        return
    
    if args.operation == 'submit':
        input_file = args.input_file or os.path.join(output_dir, f"{args.prompt_name}_input.jsonl")
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            return
        
        batch_id = submit_batch(input_file)
        print(f"Batch submitted with ID: {batch_id}")
        
        return
    
    if args.operation == 'status':
        batch_id = args.batch_id
        if not batch_id:
            print("Batch ID is required for status check")
            return
        
        status = check_batch_status(batch_id)
        print(f"Batch status: {status}")
        
        return
    
    if args.operation == 'process':
        batch_id = args.batch_id
        prompt_name = args.prompt_name
        if not batch_id:
            print("Batch ID is required for processing results")
            return
        
        results = process_batch_results(batch_id, prompt_name)
        print(f"Processed {len(results)} results")
        
        return

    if args.operation == 'error':
        batch_id = args.batch_id
        if not batch_id:
            print("Batch ID is required for checking errors")
            return
        
        error_info = check_batch_error(batch_id)
        return

if __name__ == "__main__":
    main() 