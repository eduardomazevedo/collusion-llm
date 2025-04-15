"""
Module for batch processing transcripts with OpenAI's asynchronous Batch API.

This module provides functionality to:
1. Create batch input files
Sources:
- OpenAI batch cookbook: https://cookbook.openai.com/examples/batch_processing
- Forum suggestion for batch with structured outputs: https://community.openai.com/t/using-pydantic-structured-outputs-in-batch-mode/955756/2
2. Submit batch jobs
3. Monitor batch progress
4. Process batch results (i.e. save to database)
"""
from openai import OpenAI
import json
import config
import modules.capiq as capiq
from modules.queries_db import insert_query_result
from typing import List, Dict
from tooldantic import ToolBaseModel, OpenAiResponseFormatGenerator
from modules.utils import prep_transcript_for_review

class CustomSchemaGenerator(OpenAiResponseFormatGenerator):
    is_inlined_refs = True

class BaseModel(ToolBaseModel):
    _schema_generator = CustomSchemaGenerator

class CapacityScoreReasoning(BaseModel):
    score: int
    reasoning: str

class ScoreReasonExcerpts(BaseModel):
    score: int
    reasoning: str
    excerpts: list[str]

# Map response format names to Pydantic models
RESPONSE_FORMAT_CLASSES = {
    "CapacityScoreReasoning": CapacityScoreReasoning,
    "ScoreReasonExcerpts": ScoreReasonExcerpts
}

class BatchProcessor:
    """Class to manage batch processing of transcripts."""

    def __init__(self, provider="openai", model=None, prompts_path=None):
        """
        Initializes the BatchProcessor class.

        :param provider: The LLM provider (default: "openai").
        :param model: LLM model name, defaults to OpenAI's model or config.OPENAI_MODEL.
        :param prompts_path: Path to JSON file containing system prompts.
        """
        self.provider = provider.lower()
        self.model = model or getattr(config, "OPENAI_MODEL", "gpt-4o-mini")
        self.prompts_path = prompts_path or config.PROMPTS_PATH
        self.prompts = self._load_prompts()
        self.client = OpenAI()

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

        print("\n[1/3] Fetching transcript texts...")
        transcript_texts = capiq.get_transcripts(transcript_ids)
        print(f"✓ Retrieved {len(transcript_texts)} transcript texts")

        print("\n[2/3] Creating batch input file...")
        print(f"Output path: {output_path}")
        with open(output_path, "w") as f:
            for transcript_id in transcript_ids:
                request = {
                    "custom_id": f"request-{transcript_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "temperature": 1,
                        "response_format": prompt_config["response_format"].model_json_schema(),
                        "messages": [
                            {"role": "system", "content": prompt_config["system_message"]},
                            {"role": "user", "content": prep_transcript_for_review(transcript_texts[transcript_id])}
                        ],
                        "max_tokens": 1000
                    }
                }
                f.write(json.dumps(request) + "\n")

        print("\n[3/3] Batch input file created successfully")
        print(f"✓ File contains {len(transcript_ids)} requests")
        return output_path

    def submit_batch(self, input_file_path: str) -> str:
        """
        Submit a batch job to OpenAI.

        Args:
            input_file_path: Path to the JSONL input file
            metadata: Optional metadata for the batch job

        Returns:
            Batch ID
        """
        print("\n[1/2] Uploading input file to OpenAI...")
        # Upload the input file
        with open(input_file_path, "rb") as f:
            file = self.client.files.create(
                file=f,
                purpose="batch"
            )
        print(f"✓ File uploaded successfully")
        print(f"  File ID: {file.id}")

        print("\n[2/2] Creating batch job...")
        # Create the batch
        batch = self.client.batches.create(
            input_file_id=file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        print(f"✓ Batch job created successfully")
        print(f"  Batch ID: {batch.id}")

        return batch.id

    def check_batch_status(self, batch_id: str) -> Dict:
        """Check the status of a batch job."""
        batch = self.client.batches.retrieve(batch_id)
        print(f"\nBatch status: {batch.status}")
        if batch.status == "completed":
            completed = batch.request_counts.completed
            failed = batch.request_counts.failed
            total = batch.request_counts.total
            print(f"  Completed: {completed}, Failed: {failed}, Total: {total}")
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
            raise ValueError(f"Batch {batch_id} is not completed.")

        print("\n[1/3] Downloading batch results...")
        # Download and process results
        file_content = self.client.files.content(batch.output_file_id)
        results = {}
        
        print("\n[2/3] Processing responses...")
        total_lines = len(file_content.text.splitlines())
        for i, line in enumerate(file_content.text.splitlines(), 1):
            if i % 100 == 0:
                print(f"  Processed {i}/{total_lines} responses...")
            response = json.loads(line)
            transcript_id = int(response["custom_id"].split("-")[1])
            results[transcript_id] = response["response"]["body"]
            
            # Always save to database
            insert_query_result("batch", transcript_id, json.dumps(response["response"]["body"]['choices'][0]['message']['content']))

        print("\n[3/3] Results processing complete")
        print(f"✓ Processed {len(results)} responses")
        print("✓ All responses saved to database")
        return results