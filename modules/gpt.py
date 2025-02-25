"""
Module to make Chat GPT queries
"""

import config
import json
from openai import OpenAI
from pydantic import BaseModel
import modules.capiq as capiq

_client = None
_model = "gpt-4o-mini"

def get_client():
    """
    Returns a singleton OpenAI client. Initializes it if not already created.
    :param api_key: Optional API key to initialize the client.
    """
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

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

class CheckResponseSignals(BaseModel):
    match_score: int
    explanation: str

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

# Define response formats
response_format_classes = {
    "ResponseBinary": ResponseBinary,
    "ResponseScore": ResponseScore,
    "ResponseSignals": ResponseSignals,
    "CheckResponseSignals": CheckResponseSignals,
    "ResponseIndicators2": ResponseIndicators2,
    "SimpleScore": SimpleScore,
    "SimpleSignal": SimpleSignal,
    "SignalScore": SignalScore,
    "SimplePrice": SimplePrice,
    "LeadPrice": LeadPrice,
    "LeadPriceCert": LeadPriceCert,
    "SimplePriceScore": SimplePriceScore,
    "CapacityScore": CapacityScore,
    "CapacityScoreReasoning": CapacityScoreReasoning
}


def run_completion(prompt_name, transcript_text):
    # First load the prompts
    prompts_path = f'{config.ROOT}/data/prompts.json'
    with open(prompts_path, 'r') as file:
        prompts = json.load(file)

    completion = get_client().beta.chat.completions.parse(
        model = _model,
        messages=[
            {"role": "system", "content": prompts[prompt_name]['system_message']},
            {"role": "user", "content": transcript_text}
        ],
        response_format = response_format_classes[prompts[prompt_name]['response_format']],
        temperature=0,
        max_completion_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return json.loads(completion.choices[0].message.content)


def get_responses(prompt_name, transcript_ids):
    transcript_text = capiq.get_transcripts(transcript_ids)
    results = {}
    for transcript_id in transcript_ids:
        results[transcript_id] = run_completion(prompt_name, transcript_text[transcript_id])
    return results

def check_signal(signal, excerpts_list):
    completion = get_client().beta.chat.completions.parse(
        model = _model,
        messages=[
            {"role": "system", "content": (
                "A researcher analyzed an earnings call transcript for signs of collusive intent. \n"
                "They found the following collusion signal supported by some excerpts from the transcript: \n"
                f"signal: {signal} \n"
                f"excerpts: {excerpts_list} \n"
            )},
            {"role": "user", "content": "You have to check if the signal matches the excerpts. Provide a match score between 0 and 5, where 0 means the signal doesn't match the content of the excerpts, and 5 means you fully agree the signal matches the excerpts. Also provide a short explanation of your match score."}
        ],
        response_format = CheckResponseSignals,
        temperature=0,
        max_completion_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return json.loads(completion.choices[0].message.content)