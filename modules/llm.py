"""
Module for processing transcripts with LLMs using synchronous response API calls.

Example usage:
    from modules.llm import LLMQuery
    
    # Initialize LLM query object (default provider is OpenAI)
    llm_query = LLMQuery()
    
    # Define transcript IDs
    transcript_ids = [23993]
    
    # Apply a prompt to transcripts, return responses and save to database
    responses = llm_query.apply_prompt_to_transcripts("SimpleCapacityV8.1.1", transcript_ids)

"""

from openai import OpenAI
from pydantic import BaseModel
import json
import config
import modules.capiq as capiq
from modules.queries_db import insert_query_result
import os
from datetime import datetime
from typing import Dict, List, Any


class LLMQuery:
    """Class to manage LLM queries across multiple providers."""

    def __init__(self, provider=None, model=None, prompts_path=None, temperature=None, max_tokens=None):
        """
        Initializes the LLMQuery class.

        :param provider: The LLM provider (str)
        :param model: LLM model name (str)
        :param prompts_path: Path to JSON file containing system prompts (str)
        :param temperature: Temperature setting for the model (float)
        :param max_tokens: Maximum number of tokens in the response (int)
        """
        self.provider = provider.lower() if provider else config.PROVIDER
        self.model = model or config.OPENAI_MODEL
        self.prompts_path = prompts_path or config.PROMPTS_PATH
        self.prompts = self._load_prompts()
        self.client = OpenAI()
        self.temperature = temperature or config.TEMPERATURE
        self.max_tokens = max_tokens or config.MAX_TOKENS
        self.model_config = self._load_model_config()

    def _load_prompts(self):
        """Loads the prompts from the JSON file."""
        try:
            with open(self.prompts_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {self.prompts_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Error decoding JSON in {self.prompts_path}")
    
    def _load_model_config(self) -> Dict[str, Any]:
        """Load model configuration from llm_config.json."""
        config_path = os.path.join(config.ROOT, "assets", "llm_config.json")
        try:
            with open(config_path, "r") as file:
                config_data = json.load(file)
                models = config_data.get("providers", {}).get(self.provider, {}).get("models", {})
                return models.get(self.model, {})
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default config if file doesn't exist or is invalid
            return {
                "supports_structured_output": False,
                "supports_json_output": False,
                "supports_batch": False
            }

    def _get_prompt(self, prompt_name):
        """Fetches a prompt configuration from stored prompts."""
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found in prompts.json")
        return prompt_config

    def generate_response(self, prompt_name, user_input):
        """
        Generates a response using the specified prompt.

        :param prompt_name: The key of the prompt in the JSON file.
        :param user_input: The user-provided text input.
        :return: Tuple of (JSON string from the parsed response, token usage info).
        """
        prompt_config = self._get_prompt(prompt_name)
        response_model = RESPONSE_FORMAT_CLASSES.get(prompt_config["response_format"])
        if response_model is None:
            raise ValueError(f"Invalid response format: {prompt_config['response_format']}")

        # Check model capabilities
        supports_structured = self.model_config.get("supports_structured_output", False)
        supports_json = self.model_config.get("supports_json_output", False)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": prompt_config["system_message"]},
            {"role": "user", "content": user_input},
        ]
        
        # Base completion parameters
        completion_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        
        # Handle max tokens parameter based on model type
        if self.model.startswith('o'):
            # o1 models use max_completion_tokens
            completion_params["max_completion_tokens"] = self.max_tokens
        else:
            # All other models use max_tokens
            completion_params["max_tokens"] = self.max_tokens

        # Handle response format based on model capabilities
        if supports_structured:
            # Use structured output with Pydantic model
            completion_params["response_format"] = response_model
            completion = self.client.beta.chat.completions.parse(**completion_params)
            
            # Extract token usage
            usage = completion.usage
            token_info = {
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens
            }
            
            return completion.choices[0].message.parsed.model_dump_json(), token_info
            
        elif supports_json:
            # Use JSON mode with explicit format instructions
            completion_params["response_format"] = {"type": "json_object"}
            
            # Get expected fields from the Pydantic model
            expected_fields = list(response_model.model_fields.keys())
            
            # Build detailed JSON schema instructions
            json_instructions = "\n\nYou must respond with a valid JSON object containing these fields:"
            for field_name, field_info in response_model.model_fields.items():
                field_type = field_info.annotation
                if field_name == "score":
                    json_instructions += f'\n- "{field_name}": integer between 0 and 100'
                elif field_name == "reasoning":
                    json_instructions += f'\n- "{field_name}": string explaining your analysis'
                elif field_name == "excerpts":
                    json_instructions += f'\n- "{field_name}": array of relevant transcript quotes'
                elif field_type == bool:
                    json_instructions += f'\n- "{field_name}": boolean (true/false)'
                elif field_type == str:
                    json_instructions += f'\n- "{field_name}": string'
                elif field_type == int:
                    json_instructions += f'\n- "{field_name}": integer'
                else:
                    json_instructions += f'\n- "{field_name}": appropriate value'
            
            json_instructions += f"\n\nExample format: {json.dumps({field: '...' for field in expected_fields})}"
            completion_params["messages"][0]["content"] += json_instructions
            
            # Make the API call
            completion = self.client.chat.completions.create(**completion_params)
            
            # Extract token usage
            usage = completion.usage
            token_info = {
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens
            }
            
            # Return the response content directly
            return completion.choices[0].message.content, token_info
            
        else:
            # No JSON support - use text mode with formatting instructions
            # Get expected fields from the Pydantic model
            expected_fields = list(response_model.model_fields.keys())
            
            # Add detailed formatting instructions
            format_instructions = "\n\nPlease format your response as a JSON-like structure with the following fields:"
            for field_name, field_info in response_model.model_fields.items():
                field_type = field_info.annotation
                if field_name == "score":
                    format_instructions += f'\n"{field_name}": [a number between 0 and 100]'
                elif field_name == "reasoning":
                    format_instructions += f'\n"{field_name}": [your detailed explanation]'
                elif field_name == "excerpts":
                    format_instructions += f'\n"{field_name}": [list of relevant quotes from the transcript]'
                elif field_type == bool:
                    format_instructions += f'\n"{field_name}": [true or false]'
                elif field_type == str:
                    format_instructions += f'\n"{field_name}": [text value]'
                elif field_type == int:
                    format_instructions += f'\n"{field_name}": [number]'
                else:
                    format_instructions += f'\n"{field_name}": [appropriate value]'
            
            format_instructions += "\n\nEnsure your response follows this exact structure for proper parsing."
            completion_params["messages"][0]["content"] += format_instructions
            
            # Make the API call
            completion = self.client.chat.completions.create(**completion_params)
            
            # Extract token usage
            usage = completion.usage
            token_info = {
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens
            }
            
            # For text responses, try to parse into expected format
            response_content = completion.choices[0].message.content
            
            # Try to extract fields and create JSON
            from modules.utils import extract_invalid_response
            extracted_data = extract_invalid_response(response_content, expected_fields)
            
            # Convert to JSON string
            return json.dumps(extracted_data), token_info

    def apply_prompt_to_transcripts(self, prompt_name, transcriptids):
        """
        Applies a prompt to a list of transcripts.

        :param prompt_name: The key of the prompt in the JSON file.
        :param transcriptids: List of transcript IDs to process.
        :return: Dictionary mapping transcript IDs to their JSON string responses.
        """
        print(f"\nStarting to process {len(transcriptids)} transcripts with prompt '{prompt_name}'...")
        transcript_texts = capiq.get_transcripts(transcriptids)
        results = {}
        failed_transcripts = []

        for i, transcriptid in enumerate(transcriptids, 1):
            print(f"\nProcessing transcript {i}/{len(transcriptids)} (ID: {transcriptid})...")
            try:
                response, token_info = self.generate_response(prompt_name, transcript_texts[transcriptid])
                results[transcriptid] = response
                
                # Save to database with metadata
                insert_query_result(
                    prompt_name=prompt_name,
                    transcriptid=transcriptid,
                    response=response,
                    llm_provider=self.provider,
                    model_name=self.model,
                    call_type="single",
                    temperature=self.temperature,
                    max_response=self.max_tokens,
                    input_tokens=token_info['input_tokens'],
                    output_tokens=token_info['output_tokens']
                )
                print(f"✓ Saved response to database")
            except Exception as e:
                error_type = type(e).__name__
                print(f"✗ Failed to process transcript {transcriptid}: {error_type}: {str(e)}")
                failed_transcripts.append((transcriptid, str(e)))
                
                # Special handling for length limit errors
                if error_type == "LengthFinishReasonError":
                    print(f"  → Response exceeded max_tokens limit ({self.max_tokens}). Consider increasing max_tokens.")

        # Summary
        successful_count = len(results)
        failed_count = len(failed_transcripts)
        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"  ✓ Successfully processed: {successful_count}/{len(transcriptids)} transcripts")
        if failed_count > 0:
            print(f"  ✗ Failed: {failed_count} transcripts")
            print(f"\nFailed transcript IDs:")
            for tid, error in failed_transcripts:
                print(f"    - {tid}: {error}")
        print(f"{'='*60}\n")
        
        return results


### Pydantic Response Format Models (consolidated)
class Score(BaseModel):
    score: int


class ScoreReasoning(BaseModel):
    score: int
    reasoning: str


class ScoreReasoningExcerpts(BaseModel):
    score: int
    reasoning: str
    excerpts: list[str]


class SignalReasoning(BaseModel):
    signal: str
    reasoning: str


class SignalScoreReasoning(BaseModel):
    signal: str
    score: int
    reasoning: str


class FlagReasoning(BaseModel):
    signal: bool
    reasoning: str


class FlagScoreReasoning(BaseModel):
    signal: bool
    score: int
    reasoning: str


class IndicatorExcerpts(BaseModel):
    indicator: bool
    excerpts: list[str]


class IndicatorExcerptsScore(BaseModel):
    indicator: bool
    excerpts: list[str]
    severity_score: int


class OverallSignalSeverity(BaseModel):
    overall_indicator: bool
    signal: str
    excerpts: list[str]
    severity_score: int
    reasoning: str


class OverallIndicatorsConfidence(BaseModel):
    overall_indicator: bool
    indicators: list[str]
    confidence_score: int
    excerpts: list[str]


# Map response format names to Pydantic models
RESPONSE_FORMAT_CLASSES = {
    "Score": Score,
    "ScoreReasoning": ScoreReasoning,
    "ScoreReasoningExcerpts": ScoreReasoningExcerpts,
    "SignalReasoning": SignalReasoning,
    "SignalScoreReasoning": SignalScoreReasoning,
    "FlagReasoning": FlagReasoning,
    "FlagScoreReasoning": FlagScoreReasoning,
    "IndicatorExcerpts": IndicatorExcerpts,
    "IndicatorExcerptsScore": IndicatorExcerptsScore,
    "OverallSignalSeverity": OverallSignalSeverity,
    "OverallIndicatorsConfidence": OverallIndicatorsConfidence,
}
