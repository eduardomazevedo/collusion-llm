"""
Module for batch processing transcripts with OpenAI's Batch API.

This module provides functionality to:
1. Create batch input files
2. Submit batch jobs
3. Monitor batch progress
4. Process batch results
"""

import json
import os
import time
from typing import List, Dict, Optional
from openai import OpenAI
import modules.capiq as capiq
from modules.queries_db import insert_query_result


class BatchProcessor:
    """Class to manage batch processing of transcripts."""

    def __init__(self, client: OpenAI, model: str, prompts: Dict):
        """
        Initialize the BatchProcessor.

        Args:
            client: OpenAI client instance
            model: The OpenAI model to use for batch processing
            prompts: Dictionary containing system prompts
        """
        self.client = client
        self.model = model
        self.prompts = prompts

    def create_batch_input_file(self, prompt_name: str, transcript_ids: List[int], 
                              output_path: str = "batch_input.jsonl") -> str:
        """
        Create a JSONL file for batch processing.

        Args:
            prompt_name: Name of the prompt to use
            transcript_ids: List of transcript IDs to process
            output_path: Path to save the JSONL file

        Returns:
            Path to the created JSONL file
        """
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found in prompts")

        print("Fetching transcript texts...")
        transcript_texts = capiq.get_transcripts(transcript_ids)

        print(f"Creating batch input file at {output_path}...")
        with open(output_path, "w") as f:
            for i, transcript_id in enumerate(transcript_ids, 1):
                if i % 100 == 0:
                    print(f"Processed {i}/{len(transcript_ids)} transcripts...")
                request = {
                    "custom_id": f"request-{transcript_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": prompt_config["system_message"]},
                            {"role": "user", "content": transcript_texts[transcript_id]}
                        ],
                        "max_tokens": 1000
                    }
                }
                f.write(json.dumps(request) + "\n")

        print("✓ Batch input file created successfully")
        return output_path

    def submit_batch(self, input_file_path: str, metadata: Optional[Dict] = None) -> str:
        """
        Submit a batch job to OpenAI.

        Args:
            input_file_path: Path to the JSONL input file
            metadata: Optional metadata for the batch job

        Returns:
            Batch ID
        """
        print("Uploading input file to OpenAI...")
        # Upload the input file
        with open(input_file_path, "rb") as f:
            file = self.client.files.create(
                file=f,
                purpose="batch"
            )
        print(f"✓ File uploaded successfully (ID: {file.id})")

        print("Creating batch job...")
        # Create the batch
        batch = self.client.batches.create(
            input_file_id=file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata=metadata
        )
        print(f"✓ Batch job created successfully (ID: {batch.id})")

        return batch.id

    def check_batch_status(self, batch_id: str) -> Dict:
        """Check the status of a batch job."""
        batch = self.client.batches.retrieve(batch_id)
        print(f"Batch status: {batch.status}")
        if batch.status == "in_progress":
            print(f"Progress: {batch.request_counts['completed']}/{batch.request_counts['total']} requests completed")
        return batch

    def process_batch_results(self, batch_id: str) -> Dict:
        """
        Process the results of a completed batch job.

        Args:
            batch_id: ID of the batch job

        Returns:
            Dictionary mapping transcript IDs to their responses
        """
        batch = self.check_batch_status(batch_id)
        
        if batch.status != "completed":
            raise ValueError(f"Batch {batch_id} is not completed. Current status: {batch.status}")

        print("Downloading batch results...")
        # Download and process results
        file_content = self.client.files.content(batch.output_file_id)
        results = {}
        
        print("Processing responses...")
        for i, line in enumerate(file_content.text.splitlines(), 1):
            if i % 100 == 0:
                print(f"Processed {i} responses...")
            response = json.loads(line)
            transcript_id = int(response["custom_id"].split("-")[1])
            results[transcript_id] = response["response"]["body"]
            
            # Always save to database
            insert_query_result("batch", transcript_id, json.dumps(response["response"]["body"]))

        print("✓ All responses processed and saved to database")
        return results

    def wait_for_batch_completion(self, batch_id: str, check_interval: int = 300) -> None:
        """
        Wait for a batch job to complete.

        Args:
            batch_id: ID of the batch job
            check_interval: Time in seconds between status checks
        """
        print("\nWaiting for batch completion...")
        last_status = None
        while True:
            status = self.check_batch_status(batch_id)
            if status.status != last_status:
                print(f"Status changed to: {status.status}")
                last_status = status.status
            
            if status.status in ["completed", "failed", "expired", "cancelled"]:
                break
                
            print(f"Next status check in {check_interval} seconds...")
            time.sleep(check_interval)

    def cancel_batch(self, batch_id: str) -> None:
        """Cancel a batch job."""
        print(f"Cancelling batch {batch_id}...")
        self.client.batches.cancel(batch_id)
        print("✓ Batch cancellation requested") 