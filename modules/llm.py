"""
Module for processing transcripts with LLMs

Example usage:
    from modules.llm import LLMQuery
    
    # Initialize LLM query object (default provider is OpenAI)
    llm_query = LLMQuery()
    
    # Define transcript IDs
    transcript_ids = [23993]
    
    # Apply a prompt to transcripts
    responses = llm_query.apply_prompt_to_transcripts("SimpleCapacityV8", transcript_ids)
"""

from openai import OpenAI
from pydantic import BaseModel
import json
import config
import modules.capiq as capiq


class LLMQuery:
    """Class to manage LLM queries across multiple providers."""

    def __init__(self, provider="openai", model=None, prompts_path=None):
        """
        Initializes the LLMQuery class.

        :param provider: The LLM provider (default: "openai").
        :param model: LLM model name, defaults to OpenAI's model or config.OPENAI_MODEL.
        :param prompts_path: Path to JSON file containing system prompts.
        """
        self.provider = provider.lower()
        self.model = model or getattr(config, "OPENAI_MODEL", "gpt-4o-mini")
        self.prompts_path = prompts_path or config.PROMPTS_PATH
        self.prompts = self._load_prompts()
        self.client = OpenAI()

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
        :return: JSON string from the parsed response from OpenAI using a Pydantic model.
        """
        prompt_config = self._get_prompt(prompt_name)
        response_model = RESPONSE_FORMAT_CLASSES.get(prompt_config["response_format"])
        if response_model is None:
            raise ValueError(f"Invalid response format: {prompt_config['response_format']}")

        messages = [
            {"role": "system", "content": prompt_config["system_message"]},
            {"role": "user", "content": user_input},
        ]

        # Use OpenAI's `.parse()` method with a Pydantic model
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_model,  # Directly pass Pydantic model
        )

        return completion.choices[0].message.parsed.model_dump_json()  # Automatically parsed into Pydantic model

    def apply_prompt_to_transcripts(self, prompt_name, transcript_ids):
        """
        Applies a prompt to a list of transcripts.

        :param prompt_name: The key of the prompt in the JSON file.
        :param transcript_ids: List of transcript IDs to process.
        :return: Dictionary mapping transcript IDs to their JSON string responses.
        """
        transcript_texts = capiq.get_transcripts(transcript_ids)
        results = {}

        for transcript_id in transcript_ids:
            results[transcript_id] = self.generate_response(prompt_name, transcript_texts[transcript_id])

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

# Map response format names to Pydantic models
RESPONSE_FORMAT_CLASSES = {
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
}
