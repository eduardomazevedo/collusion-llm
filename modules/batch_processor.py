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
5. Check batch error information
"""
from openai import OpenAI
import json
import config
import modules.capiq as capiq
from modules.queries_db import insert_query_result
from typing import List, Dict, Tuple
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

    def __init__(self, provider=None, model=None, prompts_path=None, temperature=None, max_tokens=None):
        """
        Initializes the BatchProcessor class.

        :param provider: The LLM provider.
        :param model: LLM model name.
        :param prompts_path: Path to JSON file containing system prompts.
        :param temperature: Temperature setting for the model.
        :param max_tokens: Maximum tokens in the response.
        """
        self.provider = provider.lower() if provider else config.PROVIDER
        self.model = config.OPENAI_MODEL
        self.prompts_path =config.PROMPTS_PATH
        self.prompts = self._load_prompts()
        self.client = OpenAI()
        self.temperature = config.TEMPERATURE
        self.max_tokens = config.MAX_TOKENS

    def _load_prompts(self):
        """Load prompts from the prompts JSON file."""
        try:
            with open(self.prompts_path, 'r') as f:
                prompts = json.load(f)
            return prompts
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompts file not found at {self.prompts_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in prompts file at {self.prompts_path}")

    def create_batch_input_file(self, prompt_name: str, transcriptids: List[int], 
                              output_path: str = "batch_input.jsonl") -> str:
        """
        Create a JSONL file for batch processing.

        Args:
            prompt_name: Name of the prompt to use
            transcriptids: List of transcript IDs to process
            output_path: Path to save the JSONL file

        Returns:
            Path to the created batch input file
        """
        prompt_config = self.prompts.get(prompt_name)
        response_model = RESPONSE_FORMAT_CLASSES.get(prompt_config["response_format"])
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found in prompts")

        # Get transcript texts
        transcript_texts = capiq.get_transcripts(transcriptids)
        
        # Create batch input file
        with open(output_path, "w") as f:
            for transcriptid in transcriptids:
                if transcriptid in transcript_texts:
                    transcript_data = json.loads(transcript_texts[transcriptid])
                    request = {
                        "custom_id": f"request-{transcriptid}",
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": self.model,
                            "temperature": self.temperature,
                            "response_format": response_model.model_json_schema(),
                            "messages": [
                                {"role": "system", "content": prompt_config["system_message"]},
                                {"role": "user", "content": prep_transcript_for_review(transcript_data)}
                            ],
                            "max_tokens": self.max_tokens
                        }
                    }
                    f.write(json.dumps(request) + "\n")

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
        
        # Create status dictionary
        status_info = {
            "status": batch.status,
            "completed": 0,
            "failed": 0,
            "total": 0,
            "success_rate": 0.0,
            "error": None
        }
        
        # Add detailed status information
        if hasattr(batch, 'request_counts'):
            completed = batch.request_counts.completed
            failed = batch.request_counts.failed
            total = batch.request_counts.total
            
            status_info.update({
                "completed": completed,
                "failed": failed,
                "total": total,
                "success_rate": (completed/(completed+failed))*100 if (completed+failed) > 0 else 0
            })
            
            # Print only essential status information
            if batch.status == "in_progress":
                print(f"Status: {batch.status} ({completed}/{total} completed)")
            elif batch.status == "completed":
                print(f"Status: {batch.status} - {completed} successful, {failed} failed")
            elif batch.status == "failed":
                print(f"Status: {batch.status} - {failed} failed")
                if hasattr(batch, 'error'):
                    status_info["error"] = batch.error
                    print(f"Error: {batch.error}")
        
        return status_info

    def process_batch_results(self, batch_id: str, prompt_name: str) -> Dict:
        """
        Process the results of a completed batch job.

        Args:
            batch_id: ID of the batch job
            prompt_name: name of the prompt (used for database insertion)

        Returns:
            Dictionary mapping transcript IDs to their raw response bodies
        """
        import json
        from json import JSONDecoder, JSONDecodeError

        status_info = self.check_batch_status(batch_id)
        if status_info["status"] != "completed":
            print(f"\nBatch is still {status_info['status']}. Please wait for completion before processing results.")
            if status_info["status"] == "in_progress":
                completed = status_info["completed"]
                failed = status_info["failed"]
                total = status_info["total"]
                print(f"Progress: {completed}/{total} completed, {failed} failed")
            return {}

        # Retrieve the batch to get the output file ID
        batch = self.client.batches.retrieve(batch_id)

        print("\n[1/3] Downloading batch results...")
        file_content = self.client.files.content(batch.output_file_id)
        results = {}

        print("\n[2/3] Processing responses...")
        lines = file_content.text.splitlines()
        total_lines = len(lines)
        for i, line in enumerate(lines, start=1):
            if i % 100 == 0:
                print(f"  Processed {i}/{total_lines} responses...")

            # Parse the outer JSONL line
            try:
                response = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skipping line {i}: cannot parse JSONL wrapper: {e}")
                continue

            # Extract transcript ID
            try:
                transcriptid = int(response["custom_id"].split("-")[1])
            except (KeyError, ValueError) as e:
                print(f"Skipping line {i}: invalid custom_id format: {e}")
                continue

            # Store the raw response body
            body = response["response"]["body"]
            results[transcriptid] = body

            # Safely extract the JSON object from the content field
            content_str = body['choices'][0]['message']['content']
            decoder = JSONDecoder()
            try:
                content_data, _ = decoder.raw_decode(content_str)
                
                # Insert into database with all required parameters
                insert_query_result(
                    prompt_name=prompt_name,
                    transcriptid=transcriptid,
                    response=content_str,
                    llm_provider=self.provider,
                    model_name=self.model,
                    call_type="batch",
                    temperature=self.temperature,
                    max_response=self.max_tokens,
                    input_tokens=body.get('usage', {}).get('prompt_tokens'),
                    output_tokens=body.get('usage', {}).get('completion_tokens')
                )
            except JSONDecodeError as e:
                print(f"Error parsing JSON for transcript {transcriptid}: {e}")
                print(f"Content: {content_str}")
                insert_query_result(
                    prompt_name=prompt_name,
                    transcriptid=transcriptid,
                    response=content_str,
                    llm_provider=self.provider,
                    model_name=self.model,
                    call_type="batch",
                    temperature=self.temperature,
                    max_response=self.max_tokens,
                    input_tokens=None,
                    output_tokens=None
                )

        print("\n[3/3] Results processing complete")
        print(f"✓ Processed {len(results)} responses")
        print("✓ All valid responses saved to database")
        return results

    def check_batch_error(self, batch_id: str) -> Dict:
        """
        Check the error information for a batch job.
        
        Args:
            batch_id: ID of the batch job
            
        Returns:
            Dictionary containing error information
        """
        batch = self.client.batches.retrieve(batch_id)
        
        error_info = {
            "status": batch.status,
            "error_file_id": batch.error_file_id if hasattr(batch, 'error_file_id') else None,
            "error_message": batch.error if hasattr(batch, 'error') else None,
            "error_content": None,
            "request_counts": None
        }
        
        # Add request counts if available
        if hasattr(batch, 'request_counts'):
            error_info["request_counts"] = {
                "completed": batch.request_counts.completed,
                "failed": batch.request_counts.failed,
                "total": batch.request_counts.total
            }
        
        if error_info["error_file_id"]:
            try:
                error_content = self.client.files.content(error_info["error_file_id"])
                error_info["error_content"] = error_content.text
                
                # Try to parse error content as JSON for better formatting
                try:
                    error_json = json.loads(error_content.text)
                    error_info["error_content"] = json.dumps(error_json, indent=2)
                except json.JSONDecodeError:
                    pass  # Keep as plain text if not valid JSON
            except Exception as e:
                error_info["error_content"] = f"Error retrieving error file: {str(e)}"
            
        return error_info

    def list_available_models(self) -> List[str]:
        """
        List all available models for the current project.
        
        Returns:
            List of model names that are available to use
        """
        models = self.client.models.list()
        return [model.id for model in models.data]