#!/usr/bin/env python3
#%%
"""
Script to rerun batch processing for top transcripts using SimpleCapacityV8.1.1 prompt.
Run interactively for debugging.
"""

import os
import pandas as pd
import sys
from modules.batch_processor import BatchProcessor
import config

#%% Setup
print("Setting up rerun_top_transcripts script...")
print(f"Current working directory: {os.getcwd()}")
print(f"ROOT directory: {config.ROOT}")

# Ensure we're in the root directory
if os.getcwd() != config.ROOT:
    os.chdir(config.ROOT)
    print(f"Changed to root directory: {os.getcwd()}")

# Create output directory for batch files
batch_output_dir = os.path.join(config.OUTPUT_DIR, 'batch_inputs')
os.makedirs(batch_output_dir, exist_ok=True)
print(f"Batch output directory: {batch_output_dir}")

#%% Load transcript IDs
csv_path = os.path.join(config.DATA_DIR, 'top_transcripts.csv')
print(f"Loading transcript IDs from: {csv_path}")

df = pd.read_csv(csv_path)
transcript_ids = df['transcript_id'].tolist()
# Remove transcript_id 3374921 from the list because
# it is not found in capitaliq. Was probably an error.
transcript_ids = [tid for tid in transcript_ids if tid != 3374921]
print(f"Loaded {len(transcript_ids)} transcript IDs")
print(f"First 10 IDs: {transcript_ids[:10]}")

#%% Create batch input file
prompt_name = "SimpleCapacityV8.1.1"
output_path = os.path.join(batch_output_dir, f"{prompt_name}_top_transcripts_input.jsonl")

print(f"Creating batch input file...")
print(f"Prompt: {prompt_name}")
print(f"Number of transcripts: {len(transcript_ids)}")
print(f"Output path: {output_path}")

processor = BatchProcessor(temperature=1.0, max_tokens=500)
input_file = processor.create_batch_input_file(
    prompt_name=prompt_name,
    transcript_ids=transcript_ids,
    output_path=output_path
)
print(f"✓ Batch input file created successfully: {input_file}")

#%% Submit batch job
print(f"Submitting batch job...")
print(f"Input file: {input_file}")

batch_id = processor.submit_batch(input_file)
print(f"✓ Batch job submitted successfully")
print(f"Batch ID: {batch_id}")

#%% Monitor batch status (run this cell to check progress)
print(f"Monitoring batch status for ID: {batch_id}")

status_info = processor.check_batch_status(batch_id)
print(f"Status: {status_info['status']}")
print(f"Completed: {status_info['completed']}")
print(f"Failed: {status_info['failed']}")
print(f"Total: {status_info['total']}")
print(f"Success Rate: {status_info['success_rate']:.1f}%")

if status_info['error']:
    print(f"Error: {status_info['error']}")

#%% Process batch results (run this when batch is completed)
print(f"Processing batch results for ID: {batch_id}")
print(f"Prompt: {prompt_name}")

results = processor.process_batch_results(batch_id, prompt_name)
print(f"✓ Batch results processed successfully")
print(f"Number of results: {len(results)}")

#%% Check batch errors (run this if there are issues)
print(f"Checking for errors in batch ID: {batch_id}")

error_info = processor.check_batch_error(batch_id)
print(f"Batch Status: {error_info['status']}")

if error_info['error_message']:
    print(f"Error Message: {error_info['error_message']}")

if error_info['error_file_id']:
    print(f"Error File ID: {error_info['error_file_id']}")
    if error_info['error_content']:
        print("\nError File Content:")
        print(error_info['error_content']) 