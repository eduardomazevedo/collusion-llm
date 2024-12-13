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

prompts = {
    'binary': {
        'system_message': "Analyze the following earnings call transcript for signs of collusion or invitations to collude. Identify statements where the company’s actions depend on competitors’ behavior, suggestions or encouragements to competitors regarding pricing or supply, or any indications of coordinated behavior. Respond whether there is evidence of collusion, and if so give the relevant excerpts.",
        'response_format': ResponseBinary},
    'score': {
        'system_message': "Analyze the following earnings call transcript for signs of collusion or invitations to collude. Identify statements where the company’s actions depend on competitors’ behavior, suggestions or encouragements to competitors regarding pricing or supply, or any indications of coordinated behavior. Respond whether there is evidence of collusion, and if so give the relevant excerpts and a severity score from 0 to 100.",
        'response_format': ResponseScore}
}


def run_completion(prompt_name, transcript_text):
    completion = get_client().beta.chat.completions.parse(
        model = _model,
        messages=[
            {"role": "system", "content": prompts[prompt_name]['system_message']},
            {"role": "user", "content": transcript_text}
        ],
        response_format = prompts[prompt_name]['response_format'],
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