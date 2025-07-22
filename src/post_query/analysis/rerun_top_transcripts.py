#!/usr/bin/env python3
#%%
"""
Script to rerun batch processing for top transcripts using SimpleCapacityV8.1.1 prompt.
We start from data/intermediaries/top_transcripts.csv list, which has the transcripts with score >= 75 in the first run (about 4500).
Then run 10 queries on each otherm and upload to the database.
Run interactively, as we have to wait for the batch to complete to get the results. Took about 3 hours on 2025-06-26.
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
batch_output_dir = os.path.join(config.CACHE_DIR, 'batch_inputs')
os.makedirs(batch_output_dir, exist_ok=True)
print(f"Batch output directory: {batch_output_dir}")

#%% Load transcript IDs
csv_path = os.path.join(config.DATA_DIR, 'intermediaries', 'top_transcripts.csv')
print(f"Loading transcript IDs from: {csv_path}")

df = pd.read_csv(csv_path)
transcript_ids = df['transcriptid'].tolist()
# Remove transcriptid 3374921 from the list because
# it is not found in capitaliq. Was probably an error.
transcript_ids = [tid for tid in transcript_ids if tid != 3374921]
print(f"Loaded {len(transcript_ids)} transcript IDs")
print(f"First 10 IDs: {transcript_ids[:10]}")

#%% Split into batches of 500
batch_size = 500
num_batches = len(transcript_ids) // batch_size
batches = [transcript_ids[i:i+batch_size] for i in range(0, len(transcript_ids), batch_size)]
print(f"Split into {len(batches)} batches")
print(f"First batch: {batches[0]}")



#%% Create batch input file
prompt_name = "SimpleCapacityV8.1.1"
processor = BatchProcessor(temperature=config.TEMPERATURE, max_tokens=config.MAX_TOKENS)

print(f"Creating batch input files for {len(batches)} batches...")
print(f"Prompt: {prompt_name}")

input_files = []
for i, batch in enumerate(batches):
    output_path = os.path.join(batch_output_dir, f"{prompt_name}_top_transcripts_batch_{i+1}_input.jsonl")
    
    print(f"\nBatch {i+1}/{len(batches)}:")
    print(f"  Number of transcripts: {len(batch)}")
    print(f"  Output path: {output_path}")
    
    input_file = processor.create_batch_input_file(
        prompt_name=prompt_name,
        transcript_ids=batch,
        output_path=output_path
    )
    input_files.append(input_file)
    print(f"  ✓ Batch input file created successfully: {input_file}")

print(f"\n✓ All {len(input_files)} batch input files created successfully")

#%% Submit batch job
n_runs_per_transcript = 10
print(f"Submitting {len(input_files)} batch jobs {n_runs_per_transcript} times each...")

batch_ids = []
for run in range(n_runs_per_transcript):
    print(f"\n=== Run {run + 1}/{n_runs_per_transcript} ===")
    
    for i, input_file in enumerate(input_files):
        print(f"\nBatch {i+1}/{len(input_files)} (Run {run + 1}):")
        print(f"  Input file: {input_file}")
        
        batch_id = processor.submit_batch(input_file)
        batch_ids.append(batch_id)
        print(f"  ✓ Batch job submitted successfully")
        print(f"  Batch ID: {batch_id}")

print(f"\n✓ All {len(batch_ids)} batch jobs submitted successfully")
print(f"Total batch IDs: {len(batch_ids)}")
print(f"Batch IDs: {batch_ids}")

#%% Monitor batch status (run this cell to check progress)
total_tasks_completed = 0
total_tasks = 0
total_batches_completed = 0
total_tasks_failed = 0

for i, batch_id in enumerate(batch_ids):
    status_info = processor.check_batch_status(batch_id)
    
    total_tasks_completed += status_info['completed']
    total_tasks += status_info['total']
    total_tasks_failed += status_info['failed']
    
    if status_info['status'] == 'completed':
        total_batches_completed += 1

print(f"Progress: {total_tasks_completed}/{total_tasks} tasks completed ({total_tasks_completed/total_tasks*100:.1f}%)")
print(f"Failed tasks: {total_tasks_failed}")
print(f"Batches completed: {total_batches_completed}/{len(batch_ids)} ({total_batches_completed/len(batch_ids)*100:.1f}%)")

#%% Process batch results (run this when batch is completed)
for i, batch_id in enumerate(batch_ids):
    print(f"\nProcessing batch results for ID: {batch_id} ({i+1}/{len(batch_ids)})")
    print(f"Prompt: {prompt_name}")

    results = processor.process_batch_results(batch_id, prompt_name)
    print(f"✓ Batch results processed successfully")
    print(f"Number of results: {len(results)}")
