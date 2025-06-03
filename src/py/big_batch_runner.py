#!/usr/bin/env python3
"""
Script to run batch processing operations for all companies in the Capital IQ sample.
This script handles creating batches that stay within OpenAI's size limits:
- Max 50,000 requests per batch
- Max 40,000,000 tokens per batch (including prompt and transcripts)

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
import openai

# Constants for OpenAI limits
MAX_REQUESTS_PER_BATCH = 50000
MAX_TOKENS_PER_BATCH = 10000000
MAX_TOKENS_IN_QUEUE = 10000000
INPUT_TOKEN_PRICE = 0.075 / 1000000  # $0.075 per 1M tokens
OUTPUT_TOKEN_PRICE = 0.3 / 1000000   # $0.3 per 1M tokens
AVG_OUTPUT_TOKENS = 250
MAX_OUTPUT_TOKENS = 500

# Map API statuses to your internal states
API_TO_INTERNAL = {
    'validating':   'in_progress',
    'in_progress':  'in_progress',
    'finalizing':   'in_progress',
    'canceling':    'canceling',
    'completed':    'completed',
    'failed':       'failed',
    'expired':      'expired',
    'canceled':     'canceled',
    'api_completed': 'api_completed'  # New status for individually processed batches
}

def get_company_transcripts() -> pd.DataFrame:
    """
    Get all companies and their transcripts from companies-transcripts.csv.
    
    Returns:
        DataFrame with companyid, companyname, transcriptid, and headline columns
    """
    csv_path = os.path.join(config.DATA_DIR, 'companies-transcripts.csv')
    try:
        return pd.read_csv(csv_path)
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

def check_batch_size(batch_file: str, prompt_tokens: int, transcript_tokens: Dict[int, int]) -> Tuple[bool, int, int]:
    """
    Check if a batch file is within OpenAI's size limits.
    
    Args:
        batch_file: Path to the batch input file
        prompt_tokens: Number of tokens in the prompt
        transcript_tokens: Dictionary mapping transcript IDs to their token sizes
        
    Returns:
        Tuple of (is_valid, total_requests, total_tokens)
    """
    total_requests = 0
    total_tokens = 0
    
    with open(batch_file, 'r') as f:
        for line in f:
            request = json.loads(line)
            transcript_id = int(request['custom_id'].split('-')[1])
            
            if transcript_id in transcript_tokens:
                total_requests += 1
                total_tokens += prompt_tokens + transcript_tokens[transcript_id]
    
    is_valid = (total_requests <= MAX_REQUESTS_PER_BATCH and 
                total_tokens <= MAX_TOKENS_PER_BATCH)
    
    return is_valid, total_requests, total_tokens

def estimate_batch_cost(batch_file: str, prompt_tokens: int, transcript_tokens: Dict[int, int]) -> Tuple[float, float]:
    """
    Estimate the cost of processing a batch.
    
    Args:
        batch_file: Path to the batch input file
        prompt_tokens: Number of tokens in the prompt
        transcript_tokens: Dictionary mapping transcript IDs to their token sizes
        
    Returns:
        Tuple of (input_cost, output_cost) in dollars
    """
    total_input_tokens = 0
    total_requests = 0
    
    with open(batch_file, 'r') as f:
        for line in f:
            request = json.loads(line)
            transcript_id = int(request['custom_id'].split('-')[1])
            
            if transcript_id in transcript_tokens:
                total_requests += 1
                total_input_tokens += prompt_tokens + transcript_tokens[transcript_id]
    
    # Calculate costs
    input_cost = total_input_tokens * INPUT_TOKEN_PRICE
    output_cost = total_requests * MAX_OUTPUT_TOKENS * OUTPUT_TOKEN_PRICE
    
    return input_cost, output_cost

def create_batches(prompt_name: str) -> List[str]:
    """
    Create batch input files for all companies, staying within OpenAI limits.
    
    Args:
        prompt_name: Name of the prompt to use
        
    Returns:
        List of paths to created batch input files
    """
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    prompt_config = processor.prompts.get(prompt_name)
    if not prompt_config:
        raise ValueError(f"Prompt '{prompt_name}' not found in prompts")
    
    # Get prompt token size
    prompt_tokens = token_size(prompt_config["system_message"])
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
    
    def __init__(self, prompt_name: str, client):
        """
        Initialize the BatchTracker.
        
        Args:
            prompt_name: Name of the prompt being used
        """
        self.prompt_name = prompt_name
        self.batches_dir = os.path.join(config.OUTPUT_DIR, f"{prompt_name}_batches")
        self.tracking_file = os.path.join(config.DATA_DIR, 'batch-tracker.csv')
        self.client = client
        
        # Get prompt tokens once at initialization
        prompt_config = BatchProcessor().prompts.get(self.prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{self.prompt_name}' not found in prompts")
        self.prompt_tokens = token_size(prompt_config["system_message"])
        print(f"\nPrompt token size: {self.prompt_tokens}")
        
        # Get list of all batch files
        if os.path.exists(self.batches_dir):
            self.batch_files = [f for f in os.listdir(self.batches_dir) if f.endswith('.jsonl')]
            print(f"\nFound {len(self.batch_files)} batch files in {self.batches_dir}")
        else:
            print(f"\nWarning: Batches directory not found: {self.batches_dir}")
            self.batch_files = []
        
        # Load or create tracking DataFrame
        if os.path.exists(self.tracking_file):
            self.df = pd.read_csv(self.tracking_file)
            print(f"\nLoaded existing tracking file with {len(self.df)} batches")
            
            # Check if we need to add more batches
            if len(self.df) < len(self.batch_files):
                print(f"\nAdding {len(self.batch_files) - len(self.df)} missing batches to tracker...")
                self._add_missing_batches()
        else:
            # Create new tracking DataFrame
            self.df = pd.DataFrame(columns=[
                'batch_file', 'company_id', 'company_name', 'total_requests',
                'total_tokens', 'input_cost', 'output_cost', 'batch_id',
                'status', 'total_requests',
                'saved_to_db'
            ])
            
            if self.batch_files:
                print("\nCreating new tracking file with all batches...")
                self._add_missing_batches()
            else:
                print("Creating empty tracking file")
                self.save()
    
    def _add_missing_batches(self):
        """Add any missing batches to the tracker."""
        # Get transcript tokens
        transcript_tokens = get_transcript_tokens()

        # Load company IDs and names once, then build lookup dict
        companies_df = get_company_transcripts(usecols=['companyid', 'companyname'])
        company_map = dict(
            zip(companies_df['companyid'], companies_df['companyname'])
        )

        # Get existing batch files from tracker
        existing_files = set(self.df['batch_file'].tolist())

        # Count how many new batches we need to add
        new_batches = [f for f in self.batch_files if os.path.join(self.batches_dir, f) not in existing_files]
        total_new = len(new_batches)
        print(f"\nFound {total_new} new batches to add to tracker")

        # Add each batch to tracker if not already present
        added_count = 0
        for batch_file in new_batches:
            batch_path = os.path.join(self.batches_dir, batch_file)

            try:
                # Extract company ID from filename
                company_id = int(batch_file.split('_')[2].split('.')[0])
                # Fast lookup of company name
                company_name = company_map.get(company_id, 'UNKNOWN')

                # Calculate batch size and cost using the pre-computed prompt tokens
                is_valid, total_requests, total_tokens = check_batch_size(
                    batch_path, self.prompt_tokens, transcript_tokens
                )
                input_cost, output_cost = estimate_batch_cost(
                    batch_path, self.prompt_tokens, transcript_tokens
                )

                # Add to tracker
                self.add_batch(
                    batch_path, company_id, company_name,
                    total_requests, total_tokens, input_cost, output_cost
                )
                added_count += 1
                print(f"Added batch {added_count}/{total_new}: {batch_file}")
            except Exception as e:
                print(f"Error processing batch {batch_file}: {str(e)}")
                continue

        print(f"\nFinished adding batches: {added_count}/{total_new} successfully added to tracker")
        self.save()
    
    def add_batch(
        self,
        batch_file: str,
        company_id: int,
        company_name: str,
        total_requests: int,
        total_tokens: int,
        input_cost: float,
        output_cost: float
    ):
        """
        Append one row to tracker both in-memory and on disk, without rewriting the entire CSV.
        """
        # Build the new row as a dict
        new_row = {
            'batch_file': batch_file,
            'company_id': company_id,
            'company_name': company_name,
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'batch_id': '',
            'status': '',
            'saved_to_db': False
        }

        # 1) Update in-memory DataFrame
        self.df.loc[len(self.df)] = new_row

        # 2) Append the single row to the CSV tracker file
        pd.DataFrame([new_row]).to_csv(
            self.tracker_csv_path,  # path used in your save() method
            mode='a',
            header=False,
            index=False
        )
    
    def update_batch(self, batch_file: str, **kwargs):
        """
        Update batch information.
        
        Args:
            batch_file: Path to the batch input file
            **kwargs: Fields to update and their new values
        """
        mask = self.df['batch_file'] == batch_file
        if not mask.any():
            print(f"Warning: Batch file {batch_file} not found in tracker")
            return
        
        for key, value in kwargs.items():
            if key in self.df.columns:
                self.df.loc[mask, key] = value
        
        self.save()
    
    def get_submitted_tokens(self) -> int:
        """
        List *all* batch jobs, keep only those whose `status` still holds tokens
        (‘validating’, ‘in progress’, ‘finalizing’, ‘canceling’), and sum their `.tokens`.
        """
        live_stat = {"validating", "in_progress", "finalizing"}
        # this returns a paginated iterator; pulling it into a list will fetch every page
        all_batches = list(self.client.batches.list())
        live_batches = [
            batch
            for batch in all_batches
            
            if batch.status.lower() in live_stat
        ]
        # Make list of batch_ids from live_batches
        live_batch_ids = [batch.id for batch in live_batches]
        # Get the total tokens for each live_batch element based on batch_id from tracker df
        live_batches_df = self.df[self.df['batch_id'].isin(live_batch_ids)]
        return live_batches_df['total_tokens'].sum()
    
    def get_submitted_tokens_local(self) -> int:
        """
        Get total number of tokens for batches in tracker df that have status "in_progress"
        """
        in_progress_df = self.df[self.df['status'] == 'in_progress']
        return in_progress_df['total_tokens'].sum()


    def get_available_tokens(self) -> int:
        """Subtract live‐queued tokens from the queue limit to get available capacity."""
        used = self.get_submitted_tokens_local()
        return max(0, MAX_TOKENS_IN_QUEUE - used)
    
    def get_next_batch(self) -> Optional[Dict]:
        """
        Get the next batch that can be submitted.
        
        Returns:
            Dictionary with batch information or None if no batch can be submitted
        """
        # Get batches that haven't been submitted yet and aren't api_completed
        unsubmitted = self.df[
            (self.df['status'].isna()) | 
            (self.df['status'] == 'failed')
        ]
        if unsubmitted.empty:
            return None
        
        # Return the first unsubmitted batch
        return unsubmitted.iloc[0].to_dict()
    
    def save(self):
        """Save the tracking DataFrame to file."""
        self.df.to_csv(self.tracking_file, index=False)
        print(f"\nSaved tracking data to {self.tracking_file}")
    
    def save_completed_batches_to_db(self, processor: BatchProcessor):
        """
        Save completed batches that haven't been saved to the database yet.
        
        Args:
            processor: BatchProcessor instance to use for saving
        """
        # Get completed batches that haven't been saved to db
        to_save = self.df[(self.df['status'] == 'completed') & (~self.df['saved_to_db'])]
        
        if to_save.empty:
            return
        
        print(f"\nSaving {len(to_save)} completed batches to database...")
        
        for _, batch in to_save.iterrows():
            try:
                print(f"Saving batch {batch['batch_id']} for {batch['company_name']}...")
                # Process and save batch results to database
                processor.process_batch_results(batch['batch_id'], self.prompt_name)
                
                # Update tracking
                self.update_batch(
                    batch['batch_file'],
                    saved_to_db=True
                )
                print(f"Successfully saved batch {batch['batch_id']} to database")
            except Exception as e:
                print(f"Error saving batch {batch['batch_id']} to database: {str(e)}")
    
    def get_progress_summary(self) -> str:
        """Get a summary of batch processing progress."""
        total_batches = len(self.df)
        completed = len(self.df[self.df['status'] == 'completed'])
        in_progress = len(self.df[self.df['status'] == 'in_progress'])
        failed = len(self.df[self.df['status'] == 'failed'])
        pending = total_batches - completed - in_progress - failed
        saved_to_db = self.df['saved_to_db'].sum()
        
        # Calculate progress percentage
        progress = (completed + failed) / total_batches * 100 if total_batches > 0 else 0
        
        # Get current queue size
        queue_size = self.get_submitted_tokens_local()
        queue_percent = (queue_size / MAX_TOKENS_IN_QUEUE) * 100
        
        return (f"\nProgress: {progress:.1f}% ({completed + failed}/{total_batches} batches)\n"
                f"Status: {completed} completed, {in_progress} in progress, {failed} failed, {pending} pending\n"
                f"Queue: {queue_size:,} tokens ({queue_percent:.1f}% of limit)\n"
                f"Saved to DB: {saved_to_db}/{completed}")

def process_batch_with_individual_calls(batch_file: str, prompt_name: str, processor: BatchProcessor) -> bool:
    """
    Process a batch file using individual API calls instead of batch API.
    
    Args:
        batch_file: Path to the batch input file
        prompt_name: Name of the prompt being used
        processor: BatchProcessor instance
        
    Returns:
        bool: True if all requests were successful, False otherwise
    """
    print(f"\nProcessing batch {batch_file} with individual API calls...")
    
    # Get the LLM instance
    from modules.llm import LLMQuery
    llm = LLMQuery()
    
    # Read the batch file
    with open(batch_file, 'r') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    successful = 0
    failed = 0
    
    for i, line in enumerate(lines, 1):
        try:
            # Parse the request
            request = json.loads(line)
            transcript_id = int(request['custom_id'].split('-')[1])
            transcript_text = request['body']['messages'][1]['content']
            
            print(f"\nProcessing request {i}/{total_lines} for transcript {transcript_id}...")
            
            # Generate response using individual API call
            response = llm.generate_response(
                prompt_name=prompt_name,
                user_input=transcript_text
            )
            
            # Save to database
            from modules.queries_db import insert_query_result
            insert_query_result(
                prompt_name=prompt_name,
                transcript_id=transcript_id,
                response=response[0],  # First element is the response string
                llm_provider=processor.provider,
                model_name=processor.model,
                call_type="individual",
                temperature=processor.temperature,
                max_response=processor.max_tokens,
                input_tokens=response[1]['input_tokens'],
                output_tokens=response[1]['output_tokens']
            )
            
            successful += 1
            print(f"✓ Successfully processed transcript {transcript_id}")
            
        except Exception as e:
            failed += 1
            print(f"✗ Failed to process transcript {transcript_id}: {str(e)}")
            continue
    
    print(f"\nBatch processing complete: {successful} successful, {failed} failed")
    return failed == 0

def submit_and_monitor_batches(prompt_name: str):
    processor = BatchProcessor(temperature=1.0, max_tokens=500)
    tracker = BatchTracker(prompt_name, client=processor.client)
    
    # Check if there are any failed batches at the start
    failed_batches = tracker.df[tracker.df['status'] == 'failed']
    encountered_failure = not failed_batches.empty
    if encountered_failure:
        print(f"\nFound {len(failed_batches)} failed batches. Will process next batch individually while monitoring in-progress batches.")

    # Main submit + interleaved monitor loop
    while True:
        # 1) Summary of all statuses
        print(tracker.get_progress_summary())

        # 2) Refresh in-progress batches
        in_prog = tracker.df[tracker.df['status'] == 'in_progress']
        if not in_prog.empty:
            print("Checking in_progress batches...")
            for _, row in in_prog.iterrows():
                status_info = processor.check_batch_status(row['batch_id'])
                api_status = status_info['status'].lower()

                # 1) If it's "failed," see if the error code is token_limit_exceeded
                if api_status == "failed" and status_info.get("error"):
                    err_obj = status_info["error"]  # e.g. {"code": "token_limit_exceeded", …}
                    if getattr(err_obj, "code", "") == "token_limit_exceeded":
                        print(f"  Batch {row['batch_id']} failed due to queue‐token limit. Keeping it pending for retry.")
                        tracker.update_batch(row['batch_file'], batch_id=None, status=None)
                        continue

                internal_status = API_TO_INTERNAL.get(api_status, "failed")
                if internal_status in ("completed", "failed"):
                    print(f"  Batch {row['batch_id']} -> {internal_status}")
                    tracker.update_batch(
                        row['batch_file'],
                        batch_id=row['batch_id'],
                        status=internal_status
                    )
                    # If we encounter a failure, set the flag
                    if internal_status == 'failed' and not encountered_failure:
                        encountered_failure = True
                        print("\nEncountered first batch failure. Will process next batch individually while monitoring in-progress batches.")
            tracker.save_completed_batches_to_db(processor)

        # If we encountered a failure, process next batch individually
        if encountered_failure:
            # Get next unprocessed batch
            next_batch = tracker.get_next_batch()
            if next_batch is not None:
                # Process the batch with individual API calls
                success = process_batch_with_individual_calls(
                    next_batch['batch_file'],
                    prompt_name,
                    processor
                )
                if success:
                    tracker.update_batch(
                        next_batch['batch_file'],
                        status='api_completed'
                    )
                    print(f"Successfully processed batch {next_batch['batch_file']} with individual API calls")
                else:
                    print(f"Failed to process batch {next_batch['batch_file']} with individual API calls")
                    tracker.update_batch(
                        next_batch['batch_file'],
                        status='failed'
                    )
            else:
                print("\nNo more batches to process. Resetting failed batches for retry...")
                # Reset failed batches
                failed_mask = tracker.df['status'] == 'failed'
                if failed_mask.any():
                    tracker.df.loc[failed_mask, ['batch_id', 'status']] = [None, None]
                    tracker.save()
                    print(f"Reset {failed_mask.sum()} failed batches for retry")
                encountered_failure = False
            
            # Wait a bit before next iteration
            time.sleep(30)
            continue

        # 3) Next unsubmitted/retryable batch
        next_batch = tracker.get_next_batch()
        if next_batch is None:
            print("\nAll batches have been submitted.")
            break

        # 4) Check token availability
        available = tracker.get_available_tokens()
        if next_batch['total_tokens'] > available:
            print(f"\nOnly {available:,} tokens free; waiting for slots...")
            time.sleep(30)
            continue

        # 5) Attempt submission
        try:
            batch_id = processor.submit_batch(next_batch['batch_file'])
        except openai.OpenAIError as e:
            code = getattr(e, 'code', '').lower()
            msg  = str(e).lower()
            if code == 'token_limit_exceeded' or 'enqueued token limit' in msg or 'token limit' in msg:
                print(f"Queue limit reached on {next_batch['batch_file']}: {e}")
                tracker.update_batch(
                    next_batch['batch_file'],
                    batch_id=None,
                    status=pd.NA
                )
                time.sleep(30)
                continue
            else:
                print(f"Permanent failure on {next_batch['batch_file']}: {e}")
                tracker.update_batch(
                    next_batch['batch_file'],
                    batch_id=None,
                    status='failed'
                )
                # Set failure flag if this is the first failure
                if not encountered_failure:
                    encountered_failure = True
                    print("\nEncountered first batch failure. Will process next batch individually while monitoring in-progress batches.")
        else:
            print(f"Submitted {next_batch['batch_file']} -> {batch_id}")
            tracker.update_batch(
                next_batch['batch_file'],
                batch_id=batch_id,
                status='in_progress'
            )

        time.sleep(5)

    # Final drain monitor loop
    while True:
        in_prog = tracker.df[tracker.df['status'] == 'in_progress']
        if in_prog.empty:
            print("\nAll batches completed.")
            break

        print("Final check of in_progress batches...")
        for _, row in in_prog.iterrows():
            status_info = processor.check_batch_status(row['batch_id'])
            api_status = status_info['status'].lower()

            # 1) If it's "failed," see if the error code is token_limit_exceeded
            if api_status == "failed" and status_info.get("error"):
                err_obj = status_info["error"]  # e.g. {"code": "token_limit_exceeded", …}
                if getattr(err_obj, "code", "") == "token_limit_exceeded":
                    print(f"  Batch {row['batch_id']} failed due to queue‐token limit. Keeping it pending for retry.")
                    tracker.update_batch(row['batch_file'], batch_id=None, status=None)
                    continue

            internal_status = API_TO_INTERNAL.get(api_status, "failed")
            if internal_status in ("completed", "failed"):
                print(f"  Batch {row['batch_id']} -> {internal_status}")
                tracker.update_batch(
                    row['batch_file'],
                    batch_id=row['batch_id'],
                    status=internal_status
                )
        tracker.save_completed_batches_to_db(processor)
        time.sleep(30)



def main():
    parser = argparse.ArgumentParser(description='Run batch processing operations for all companies')
    parser.add_argument('prompt_name', help='Name of the prompt to use')
    parser.add_argument('operation', choices=['create', 'submit', 'all'],
                      default='all', help='Operation to perform')
    args = parser.parse_args()
    
    if args.operation in ['create', 'all']:
        print("\nCreating batch files...")
        batch_files = create_batches(args.prompt_name)
        if not batch_files:
            print("No batch files were created")
            return
    
    if args.operation in ['submit', 'all']:
        print("\nSubmitting and monitoring batches...")
        submit_and_monitor_batches(args.prompt_name)

if __name__ == "__main__":
    main() 