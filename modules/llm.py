"""
Module for processing transcripts with LLMs using synchronous response API calls.

Example usage:
    from modules.llm import LLMQuery
    
    # Initialize LLM query object (default provider is OpenAI)
    llm_query = LLMQuery()
    
    # Define transcript IDs
    transcript_ids = [23993]
    
    # Apply a prompt to transcripts and return responses
    responses = llm_query.apply_prompt_to_transcripts("SimpleCapacityV8", transcript_ids)

    # Save responses to database
    responses = llm_query.apply_prompt_to_transcripts("SimpleCapacityV8", transcript_ids, save_to_db=True)
"""

from openai import OpenAI
from pydantic import BaseModel
import json
import config
import modules.capiq as capiq
from modules.queries_db import insert_query_result


class LLMQuery:
    """Class to manage LLM queries across multiple providers."""

    def __init__(self, provider="openai", model=None, prompts_path=None, temperature=1.0, max_tokens=2000):
        """
        Initializes the LLMQuery class.

        :param provider: The LLM provider (default: "openai").
        :param model: LLM model name, defaults to OpenAI's model or config.OPENAI_MODEL.
        :param prompts_path: Path to JSON file containing system prompts.
        :param temperature: Temperature setting for the model (default: 1.0).
        :param max_tokens: Maximum number of tokens in the response (default: 500).
        """
        self.provider = provider.lower()
        self.model = model or getattr(config, "OPENAI_MODEL", "o4-mini-2025-04-16")
        self.prompts_path = prompts_path or config.PROMPTS_PATH
        self.prompts = self._load_prompts()
        self.client = OpenAI()
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _load_prompts(self):
        """Loads the prompts from the JSON file."""
        try:
            with open(self.prompts_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {self.prompts_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Error decoding JSON in {self.prompts_path}")

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

        messages = [
            {"role": "system", "content": prompt_config["system_message"]},
            {"role": "user", "content": user_input},
        ]

        # Determine which parameter to use based on model
        # Newer models (o1, o4, etc.) use max_completion_tokens
        completion_params = {
            "model": self.model,
            "messages": messages,
            "response_format": response_model,  # Directly pass Pydantic model
            "temperature": self.temperature,
        }
        
        # Check if this is a newer model that requires max_completion_tokens
        if self.model.startswith(('o1', 'o4', 'gpt-4o-2024-08-06')):
            completion_params["max_completion_tokens"] = self.max_tokens
        else:
            completion_params["max_tokens"] = self.max_tokens

        # Use OpenAI's `.parse()` method with a Pydantic model
        completion = self.client.beta.chat.completions.parse(**completion_params)

        # Extract token usage
        usage = completion.usage
        token_info = {
            'input_tokens': usage.prompt_tokens,
            'output_tokens': usage.completion_tokens
        }

        return completion.choices[0].message.parsed.model_dump_json(), token_info

    def apply_prompt_to_transcripts(self, prompt_name, transcript_ids):
        """
        Applies a prompt to a list of transcripts.

        :param prompt_name: The key of the prompt in the JSON file.
        :param transcript_ids: List of transcript IDs to process.
        :return: Dictionary mapping transcript IDs to their JSON string responses.
        """
        print(f"\nStarting to process {len(transcript_ids)} transcripts with prompt '{prompt_name}'...")
        transcript_texts = capiq.get_transcripts(transcript_ids)
        results = {}
        failed_transcripts = []

        for i, transcript_id in enumerate(transcript_ids, 1):
            print(f"\nProcessing transcript {i}/{len(transcript_ids)} (ID: {transcript_id})...")
            try:
                response, token_info = self.generate_response(prompt_name, transcript_texts[transcript_id])
                results[transcript_id] = response
                
                # Save to database with metadata
                insert_query_result(
                    prompt_name=prompt_name,
                    transcript_id=transcript_id,
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
                print(f"✗ Failed to process transcript {transcript_id}: {error_type}: {str(e)}")
                failed_transcripts.append((transcript_id, str(e)))
                
                # Special handling for length limit errors
                if error_type == "LengthFinishReasonError":
                    print(f"  → Response exceeded max_tokens limit ({self.max_tokens}). Consider increasing max_tokens.")

        # Summary
        successful_count = len(results)
        failed_count = len(failed_transcripts)
        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"  ✓ Successfully processed: {successful_count}/{len(transcript_ids)} transcripts")
        if failed_count > 0:
            print(f"  ✗ Failed: {failed_count} transcripts")
            print(f"\nFailed transcript IDs:")
            for tid, error in failed_transcripts:
                print(f"    - {tid}: {error}")
        print(f"{'='*60}\n")
        
        return results


### Pydantic Response Format Models
class ResponseBinary(BaseModel):
    indicator: bool
    excerpts: list[str]

class ResponseScore(BaseModel):
    indicator: bool
    excerpts: list[str]
    severity_score: int

class ResponseSignals(BaseModel):
    overall_indicator: bool
    signal: str
    excerpts: list[str]
    severity_score: int
    reasoning: str

class ResponseIndicators2(BaseModel):
    overall_indicator: bool
    indicators: list[str]
    confidence_score: int
    excerpts: list[str]

class SimpleScore(BaseModel):
    score: int
    reasoning: str

class SimpleSignal(BaseModel):
    signal: str
    reasoning: str

class SignalScore(BaseModel):
    signal: str
    score: int
    reasoning: str

class SimplePrice(BaseModel):
    score: int
    reasoning: str

class LeadPrice(BaseModel):
    signal: bool
    reasoning: str

class LeadPriceCert(BaseModel):
    signal: bool
    reasoning: str
    score: int

class SimplePriceScore(BaseModel):
    score: int

class CapacityScore(BaseModel):
    score: int

class CapacityScoreReasoning(BaseModel):
    score: int
    reasoning: str

class PriceCapacity(BaseModel):
    score: int
    reasoning: str

class ScoreReasonExcerpts(BaseModel):
    score: int
    reasoning: str
    excerpts: list[str]

class SimpleExcerptAnalyzer(BaseModel):
    score: int

# Map response format names to Pydantic models
RESPONSE_FORMAT_CLASSES = {
    "SimpleExcerptAnalyzer": SimpleExcerptAnalyzer,
    "ResponseBinary": ResponseBinary,
    "ResponseScore": ResponseScore,
    "ResponseSignals": ResponseSignals,
    "ResponseIndicators2": ResponseIndicators2,
    "SimpleScore": SimpleScore,
    "SimpleSignal": SimpleSignal,
    "SignalScore": SignalScore,
    "SimplePrice": SimplePrice,
    "LeadPrice": LeadPrice,
    "LeadPriceCert": LeadPriceCert,
    "SimplePriceScore": SimplePriceScore,
    "CapacityScore": CapacityScore,
    "CapacityScoreReasoning": CapacityScoreReasoning,
    "PriceCapacity": PriceCapacity,
    "ScoreReasonExcerpts": ScoreReasonExcerpts,
    "SimpleExcerptAnalyzer": SimpleExcerptAnalyzer,
}