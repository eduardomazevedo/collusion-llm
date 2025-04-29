#!/usr/bin/env python3
"""
Script to run batch processing operations for all companies in the Capital IQ sample.
This script handles creating batches that stay within OpenAI's size limits:
- Max 45,000 requests per batch
- Max 35,000,000 tokens per batch (including prompt and transcripts)

Usage:
    python big_batch_runner.py <prompt_name> [--operation <operation>]
    
Operations:
    create: Create batch input files
    submit: Submit batch jobs
    status: Check batch status
    process: Process batch results
    error: Check batch error information
    models: List available models
    all: Run all operations in sequence
"""

import argparse
import os
import pandas as pd
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from modules.batch_processor import BatchProcessor
from modules.utils import token_size
import config

def get_prompt_tokens(prompt_text: str) -> int:
    """
    Calculate the number of tokens in a prompt text.
    
    Args:
        prompt_text: The prompt text to calculate tokens for
        
    Returns:
        int: Number of tokens in the prompt
    """
    return token_size(prompt_text)

def get_company_transcripts() -> pd.DataFrame:
    """
    Get all companies and their transcripts from companies-transcripts.csv.
    
    Returns:
        DataFrame with companyid, companyname, transcriptid, and headline columns
    """
    csv_path = os.path.join(config.DATA_DIR, 'companies-transcripts.csv')
    try:
        print("\nReading companies-transcripts.csv...")
        df = pd.read_csv(csv_path)
        print("\nCSV Info:")
        print(df.info())
        print("\nFirst few rows:")
        print(df.head())
        print("\nColumn names:", df.columns.tolist())
        return df
    except FileNotFoundError:
        print(f"Error: Could not find companies-transcripts.csv at {csv_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error reading companies-transcripts.csv: {str(e)}")
        return pd.DataFrame()

def get_transcript_tokens() -> Dict[int, int]:
    """
    Get token sizes for all transcripts from transcript-tokens.csv.
    
    Returns:
        Dictionary mapping transcript IDs to their token sizes
    """
    csv_path = os.path.join(config.DATA_DIR, 'transcript-tokens.csv')
    try:
        print("\nReading transcript-tokens.csv...")
        df = pd.read_csv(csv_path)
        print("\nCSV Info:")
        print(df.info())
        print("\nFirst few rows:")
        print(df.head())
        print("\nColumn names:", df.columns.tolist())
        
        # Check for any missing values
        print("\nMissing values per column:")
        print(df.isnull().sum())
        
        # Check for empty values in tokensize column
        empty_tokens = df[df['tokensize'].isna()]
        print(f"\nFound {len(empty_tokens)} transcripts with empty token size")
        
        # Create the dictionary, excluding empty values
        token_dict = {}
        for _, row in df.iterrows():
            if pd.notna(row['tokensize']):  # Only include non-empty token sizes
                token_dict[int(row['transcriptid'])] = int(row['tokensize'])
        
        print(f"\nCreated dictionary with {len(token_dict)} entries")
        return token_dict
    except FileNotFoundError:
        print(f"Error: Could not find transcript-tokens.csv at {csv_path}")
        return {}
    except Exception as e:
        print(f"Error reading transcript-tokens.csv: {str(e)}")
        return {}

def create_batches(prompt_name: str) -> List[str]:
    """
    Create batch input files for all companies, staying within OpenAI limits.
    
    Args:
        prompt_name: Name of the prompt to use
        
    Returns:
        List of paths to created batch input files
    """
    processor = BatchProcessor()
    prompt_config = processor.prompts.get(prompt_name)
    if not prompt_config:
        raise ValueError(f"Prompt '{prompt_name}' not found in prompts")
    
    # Get prompt token size
    prompt_tokens = get_prompt_tokens(prompt_config["system_message"])
    print(f"Prompt token size: {prompt_tokens}")
    
    # Get all companies and transcripts
    companies_df = get_company_transcripts()
    if companies_df.empty:
        return []
    
    # Get transcript token sizes
    transcript_tokens = get_transcript_tokens()
    if not transcript_tokens:
        return []
    
    # Create batches directory
    batches_dir = os.path.join(config.OUTPUT_DIR, f"{prompt_name}_batches")
    os.makedirs(batches_dir, exist_ok=True)
    
    # Create diagnostic DataFrame
    diagnostic_df = companies_df.copy()
    diagnostic_df['token_size'] = diagnostic_df['transcriptid'].map(transcript_tokens)
    diagnostic_df['has_token_size'] = diagnostic_df['token_size'].notna()
    diagnostic_df['batch_number'] = 0
    diagnostic_df['text_length'] = 0  # New column for text length
    
    # Save initial diagnostic file
    diagnostic_path = os.path.join(config.DATA_DIR, 'transcript_diagnostics.csv')
    diagnostic_df.to_csv(diagnostic_path, index=False)
    print(f"\nCreated diagnostic file at {diagnostic_path}")
    
    # Initialize batch variables
    batch_files = []
    batch_num = 1
    
    # Group transcripts by company
    company_groups = companies_df.groupby('companyid')
    total_companies = len(company_groups)
    print(f"\nProcessing {total_companies} companies...")
    
    # Process each company's transcripts
    for company_id, group in company_groups:
        company_name = group['companyname'].iloc[0]
        company_transcripts = group['transcriptid'].tolist()
        
        # Calculate total tokens for this company's transcripts
        company_tokens = 0
        valid_transcripts = []
        
        for tid in company_transcripts:
            if tid in transcript_tokens and transcript_tokens[tid] is not None:
                # Add prompt tokens to each transcript's token count
                total_tokens = transcript_tokens[tid] + prompt_tokens
                company_tokens += total_tokens
                valid_transcripts.append(tid)
                diagnostic_df.loc[diagnostic_df['transcriptid'] == tid, 'batch_number'] = batch_num
        
        # Skip companies with no valid transcripts
        if not valid_transcripts:
            print(f"Company {company_name} skipped - no valid transcripts")
            continue
        
        # Create a batch for this company's transcripts
        print(f"\nCreating batch for company {company_name} (ID: {company_id}): {len(valid_transcripts)} transcripts, {company_tokens:,} tokens")
        # Convert company_id to string without decimal point
        company_id_str = str(int(company_id))
        batch_path = os.path.join(batches_dir, f"input_companyid_{company_id_str}.jsonl")
        
        # Create batch file
        output_path = processor.create_batch_input_file(
            prompt_name=prompt_name,
            transcript_ids=valid_transcripts,
            output_path=batch_path
        )
        
        # Get list of processed transcripts from the batch file
        processed_transcripts = set()
        with open(batch_path, 'r') as f:
            for line in f:
                request = json.loads(line)
                transcript_id = int(request['custom_id'].split('-')[1])
                processed_transcripts.add(transcript_id)
                
                # Update text length (using the user message content)
                try:
                    text_length = len(request['body']['messages'][1]['content'])
                    diagnostic_df.loc[diagnostic_df['transcriptid'] == transcript_id, 'text_length'] = text_length
                except (KeyError, IndexError) as e:
                    print(f"\nError accessing content for transcript {transcript_id}: {str(e)}")
                    print("Request structure:")
                    print(json.dumps(request, indent=2))
        
        # Report batch completion statistics
        print(f"\nBatch for company {company_name} (ID: {company_id}) completed:")
        print(f"- Intended to process: {len(valid_transcripts)} transcripts")
        print(f"- Successfully processed: {len(processed_transcripts)} transcripts")
        missing_count = len(valid_transcripts) - len(processed_transcripts)
        if missing_count > 0:
            print(f"- Missing transcripts: {missing_count}")
        print(f"- Total tokens: {company_tokens:,}")
        print(f"- Output file: {batch_path}")
        
        batch_files.append(batch_path)
        batch_num += 1
        
        # Update diagnostic file periodically (every 1000 entries)
        if len(processed_transcripts) % 1000 == 0:
            diagnostic_df.to_csv(diagnostic_path, index=False)
            print(f"Processed {len(processed_transcripts)} transcripts")
    
    # Save final diagnostic file
    diagnostic_df.to_csv(diagnostic_path, index=False)
    
    print(f"\nCreated {len(batch_files)} batch files in {batches_dir}")
    return batch_files

class BatchTracker:
    """Class to track batch processing status and manage token limits."""
    
    def __init__(self, prompt_name: str):
        """
        Initialize the BatchTracker.
        
        Args:
            prompt_name: Name of the prompt being used
        """
        self.prompt_name = prompt_name
        self.batches_dir = os.path.join(config.OUTPUT_DIR, f"{prompt_name}_batches")
        self.tracking_file = os.path.join(config.DATA_DIR, 'batch_tracking.csv')
        
        # Cost constants (per 1,000,000 tokens)
        self.INPUT_COST_PER_MILLION = 0.075
        self.OUTPUT_COST_PER_MILLION = 0.3
        self.AVG_OUTPUT_TOKENS = 250
        
        # Initialize DataFrame columns
        self.columns = [
            'company_id', 'company_name', 'input_file', 'token_size',
            'batch_id', 'status', 'submission_time', 'completion_time',
            'output_file', 'estimated_input_cost', 'estimated_output_cost',
            'total_estimated_cost'
        ]
        
        # Load or create tracking DataFrame
        if os.path.exists(self.tracking_file):
            self.df = pd.read_csv(self.tracking_file)
            # Convert timestamps to datetime
            for col in ['submission_time', 'completion_time']:
                if col in self.df.columns:
                    self.df[col] = pd.to_datetime(self.df[col])
        else:
            self.df = pd.DataFrame(columns=self.columns)
    
    def calculate_costs(self, token_size: int, num_transcripts: int) -> Tuple[float, float, float]:
        """
        Calculate estimated costs for a batch.
        
        Args:
            token_size: Total input token size
            num_transcripts: Number of transcripts in the batch
            
        Returns:
            Tuple of (input_cost, output_cost, total_cost)
        """
        # Calculate input cost
        input_cost = (token_size / 1_000_000) * self.INPUT_COST_PER_MILLION
        
        # Calculate output cost (estimated 250 tokens per response)
        output_tokens = num_transcripts * self.AVG_OUTPUT_TOKENS
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_MILLION
        
        total_cost = input_cost + output_cost
        
        return input_cost, output_cost, total_cost
    
    def add_batch(self, company_id: int, company_name: str, input_file: str, token_size: int):
        """
        Add a new batch to the tracker.
        
        Args:
            company_id: Company ID
            company_name: Company name
            input_file: Path to input file
            token_size: Total token size for the batch
        """
        # Count number of transcripts in the input file
        with open(input_file, 'r') as f:
            num_transcripts = sum(1 for _ in f)
        
        # Calculate costs
        input_cost, output_cost, total_cost = self.calculate_costs(token_size, num_transcripts)
        
        new_row = {
            'company_id': company_id,
            'company_name': company_name,
            'input_file': input_file,
            'token_size': token_size,
            'batch_id': None,
            'status': 'not_submitted',
            'submission_time': None,
            'completion_time': None,
            'output_file': None,
            'estimated_input_cost': input_cost,
            'estimated_output_cost': output_cost,
            'total_estimated_cost': total_cost
        }
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        self.save()
    
    def get_total_estimated_cost(self) -> float:
        """Get total estimated cost for all batches."""
        return self.df['total_estimated_cost'].sum()
    
    def get_completed_cost(self) -> float:
        """Get total estimated cost for completed batches."""
        return self.df[self.df['status'] == 'completed']['total_estimated_cost'].sum()
    
    def get_remaining_cost(self) -> float:
        """Get total estimated cost for remaining batches."""
        return self.df[self.df['status'] != 'completed']['total_estimated_cost'].sum()
    
    def update_batch(self, company_id: int, **kwargs):
        """
        Update batch information.
        
        Args:
            company_id: Company ID to update
            **kwargs: Fields to update and their values
        """
        mask = self.df['company_id'] == company_id
        for key, value in kwargs.items():
            if key in self.df.columns:
                self.df.loc[mask, key] = value
        self.save()
    
    def get_submitted_tokens(self) -> int:
        """Get total tokens of submitted but not completed batches."""
        mask = (self.df['status'] == 'submitted')
        return self.df.loc[mask, 'token_size'].sum()
    
    def get_available_tokens(self) -> int:
        """Get available tokens within the 35M limit."""
        return 35000000 - self.get_submitted_tokens()
    
    def get_next_batch(self) -> Optional[Dict]:
        """
        Get the next batch to submit based on available tokens.
        
        Returns:
            Dictionary with batch information or None if no batches available
        """
        mask = (self.df['status'] == 'not_submitted')
        available_batches = self.df[mask].sort_values('token_size')
        
        for _, batch in available_batches.iterrows():
            if batch['token_size'] <= self.get_available_tokens():
                return batch.to_dict()
        
        return None
    
    def save(self):
        """Save tracking DataFrame to CSV."""
        self.df.to_csv(self.tracking_file, index=False)

def submit_and_monitor_batches(prompt_name: str):
    """
    Submit and monitor batches, staying within token limits.
    
    Args:
        prompt_name: Name of the prompt to use
    """
    processor = BatchProcessor()
    tracker = BatchTracker(prompt_name)
    
    # Get all input files
    input_files = [f for f in os.listdir(tracker.batches_dir) 
                  if f.startswith('input_companyid_') and f.endswith('.jsonl')]
    
    if not input_files:
        print("No input files found")
        return
    
    # Add all input files to tracker if not already there
    for input_file in input_files:
        # Extract company ID from filename
        company_id = int(input_file.split('_')[2].split('.')[0])
        
        # Skip if already in tracker
        if company_id in tracker.df['company_id'].values:
            continue
        
        # Get company name from diagnostic file
        diagnostic_df = pd.read_csv(os.path.join(config.DATA_DIR, 'transcript_diagnostics.csv'))
        company_name = diagnostic_df[diagnostic_df['companyid'] == company_id]['companyname'].iloc[0]
        
        # Get token size from diagnostic file
        token_size = diagnostic_df[diagnostic_df['companyid'] == company_id]['token_size'].sum()
        
        # Add to tracker
        tracker.add_batch(
            company_id=company_id,
            company_name=company_name,
            input_file=os.path.join(tracker.batches_dir, input_file),
            token_size=token_size
        )
    
    print(f"\nTracking {len(tracker.df)} batches")
    print(f"Initial available tokens: {tracker.get_available_tokens():,}")
    print(f"Total estimated cost: ${tracker.get_total_estimated_cost():.2f}")
    print(f"  - Input: ${tracker.df['estimated_input_cost'].sum():.2f}")
    print(f"  - Output: ${tracker.df['estimated_output_cost'].sum():.2f}")
    
    while True:
        # Check status of submitted batches
        submitted_batches = tracker.df[tracker.df['status'] == 'submitted']
        for _, batch in submitted_batches.iterrows():
            status = processor.check_batch_status(batch['batch_id'])
            
            if status['status'] == 'completed':
                print(f"\nBatch {batch['batch_id']} completed")
                print(f"Cost for this batch: ${batch['total_estimated_cost']:.2f}")
                print(f"  - Input: ${batch['estimated_input_cost']:.2f}")
                print(f"  - Output: ${batch['estimated_output_cost']:.2f}")
                
                # Update tracker
                tracker.update_batch(
                    batch['company_id'],
                    status='completed',
                    completion_time=datetime.now()
                )
                
                # Process results
                results = processor.process_batch_results(batch['batch_id'], prompt_name)
                
                # Save output file
                output_file = os.path.join(
                    tracker.batches_dir,
                    f"output_companyid_{batch['company_id']}.jsonl"
                )
                with open(output_file, 'w') as f:
                    for result in results.values():
                        f.write(json.dumps(result) + '\n')
                
                tracker.update_batch(
                    batch['company_id'],
                    output_file=output_file
                )
                
                # Print progress
                print(f"\nProgress:")
                print(f"Completed: ${tracker.get_completed_cost():.2f}")
                print(f"Remaining: ${tracker.get_remaining_cost():.2f}")
        
        # Submit new batches if tokens available
        while tracker.get_available_tokens() > 0:
            next_batch = tracker.get_next_batch()
            if not next_batch:
                break
            
            print(f"\nSubmitting batch for company {next_batch['company_name']}")
            print(f"Estimated cost: ${next_batch['total_estimated_cost']:.2f}")
            batch_id = processor.submit_batch(next_batch['input_file'])
            
            tracker.update_batch(
                next_batch['company_id'],
                batch_id=batch_id,
                status='submitted',
                submission_time=datetime.now()
            )
        
        # Check if all batches are completed
        if (tracker.df['status'] == 'completed').all():
            print("\nAll batches completed!")
            print(f"Total cost: ${tracker.get_total_estimated_cost():.2f}")
            break
        
        # Wait 5 minutes before next check
        print(f"\nWaiting 5 minutes... ({datetime.now().strftime('%H:%M:%S')})")
        time.sleep(300)

def main():
    parser = argparse.ArgumentParser(description='Run batch processing operations for all companies')
    parser.add_argument('prompt_name', help='Name of the prompt to use')
    parser.add_argument('--operation', choices=['create', 'submit', 'status', 'process', 'error', 'models', 'all'],
                      default='all', help='Operation to perform')
    args = parser.parse_args()
    
    if args.operation == 'models':
        processor = BatchProcessor()
        print("\nListing available models...")
        models = processor.list_available_models()
        print("\nAvailable models:")
        for model in sorted(models):
            print(f"- {model}")
        return
    
    # Set up batches directory
    batches_dir = os.path.join(config.OUTPUT_DIR, f"{args.prompt_name}_batches")
    os.makedirs(batches_dir, exist_ok=True)
    
    if args.operation == 'create':
        batch_files = create_batches(args.prompt_name)
        print(f"\nCreated {len(batch_files)} batch files in {batches_dir}")
        return
    
    if args.operation == 'submit':
        submit_and_monitor_batches(args.prompt_name)
        return
    
    if args.operation == 'status':
        tracker = BatchTracker(args.prompt_name)
        print("\nBatch Status Summary:")
        print(tracker.df[['company_id', 'company_name', 'status', 'token_size']])
        return
    
    if args.operation == 'process':
        tracker = BatchTracker(args.prompt_name)
        completed_batches = tracker.df[tracker.df['status'] == 'completed']
        
        if completed_batches.empty:
            print("No completed batches found")
            return
        
        processor = BatchProcessor()
        for _, batch in completed_batches.iterrows():
            print(f"\nProcessing batch for company {batch['company_name']}")
            processor.process_batch_results(batch['batch_id'], args.prompt_name)
        
        return
    
    if args.operation == 'error':
        tracker = BatchTracker(args.prompt_name)
        failed_batches = tracker.df[tracker.df['status'] == 'failed']
        
        if failed_batches.empty:
            print("No failed batches found")
            return
        
        processor = BatchProcessor()
        for _, batch in failed_batches.iterrows():
            print(f"\nChecking errors for company {batch['company_name']}")
            error_info = processor.check_batch_error(batch['batch_id'])
            print(f"Error: {error_info['error_message']}")
        
        return
    
    if args.operation == 'all':
        # Create batches
        batch_files = create_batches(args.prompt_name)
        if not batch_files:
            print("No batches created")
            return
        
        # Submit and monitor batches
        submit_and_monitor_batches(args.prompt_name)
        
        return

if __name__ == "__main__":
    main() 