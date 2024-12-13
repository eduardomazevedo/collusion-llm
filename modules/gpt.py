"""
Module to make Chat GPT queries
"""

import config
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

prompts = {
    'binary': {
        'system_message': "Analyze the following earnings call transcript for signs of collusion or invitations to collude. Identify statements where the company’s actions depend on competitors’ behavior, suggestions or encouragements to competitors regarding pricing or supply, or any indications of coordinated behavior. Respond whether there is evidence of collusion, and if so give the relevant excerpts.",
        'response_format': ResponseBinary},
    'score': {
        'system_message': "Analyze the following earnings call transcript for signs of collusion or invitations to collude. Identify statements where the company’s actions depend on competitors’ behavior, suggestions or encouragements to competitors regarding pricing or supply, or any indications of coordinated behavior. Respond whether there is evidence of collusion, and if so give the relevant excerpts and a severity score from 0 to 100.",
        'response_format': ResponseScore}
}


def get_response(prompt_name, transcript_text):
    completion = get_client().beta.chat.completions.parse(
        model = _model,
        messages=[
            {"role": "system", "content": prompts[prompt_name]['system_message']},
            {"role": "user", "content": transcript_text}
        ],
        response_format = prompts[prompt_name]['response_format']
    )
    return completion