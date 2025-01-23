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

prompts = {
    'SimpleScore': {
        'system_message': (
            "Analyze the following earnings call transcript and rate on a scale of 0 to 100 the extent to which the company shows signs of collusive intent."
            "Also provide a brief reasoning for your score."
        ),
        'response_format': SimpleScore
    },
    'binary': {
        'system_message': (
            "Analyze the following earnings call transcript for signs of collusion or invitations to collude. "
            "Identify statements where the company’s actions depend on competitors’ behavior, suggestions or "
            "encouragements to competitors regarding pricing or supply, or any indications of coordinated behavior. "
            "Respond whether there is evidence of collusion, and if so give the relevant excerpts."
        ),
        'response_format': ResponseBinary
    },
    'score': {
        'system_message': "",
        'response_format': ResponseScore
    },
    'signals': {
        'system_message': (
            "Analyze this earnings call transcript of a public company and identify signs of potential collusive intent.\n"
            "\n"
            "In general, collusive actions involve at least one of the following outcomes:\n"
            " - increasing prices\n"
            " - limiting supply\n"
            " - other more particular coordinated profit-increasing actions\n"
            "\n"
            "A weak collusion signal can be:\n"
            " - company states or implies pursuing one of the actions is desirable\n"
            " - company states or implies competitors pursuing one of the actions is desirable\n"
            "\n"
            "A strong collusion signal can be:\n"
            " - company mentions pursuing one of the actions AND that other companies should follow\n"
            " - company mentions IF other companies pursue one of the actions, this company will ALSO pursue the action\n"
            "\n"
            "Notes: \n"
            "Collusion intent is often implied, so it is important to look for any variations of language that may indicate the collusive actions or signals.\n"
            "Discussions of normal industry dynamics, such as price matching, competitive responses to market conditions, or general observations about the market, do not necessarily indicate collusion. Pay close attention to whether the company explicitly suggests coordinated actions or conditions its actions on competitors' behavior.\n"
            "\n"
            "Provide the following information:\n"
            " - overall collusion intent indicator (boolean)\n"
            " - collusion signal (none/weak/strong)\n"
            " - excerpts that show the most relevant examples of collusive intent\n"
            " - a severity score from 0 to 5 based on the following scale:\n"
            "    - 0: No indications of collusive intent in the transcript.\n"
            "    - 1: Statements that are largely ambiguous but are related to one of the collusive actions listed earlier.\n"
            "    - 2: Subtle or weak signals suggesting possible collusive behavior intent, though not very clear.\n"
            "    - 3: Clearer references to collusive actions or multiple weak signals about any of the potentially collusive outcomes.\n"
            "    - 4: Strong signals, including clear intention to coordinate with competitors.\n"
            "    - 5: Repeated or clear endorsements of coordinated action to achieve one of the collusive outcomes.\n"
            " - a very brief reasoning for the score you chose\n"
        ),
        'response_format': ResponseSignals
    },
    'indicators': {
        'system_message': (
            "Analyze the following earnings call transcript to determine if it indicates collusive intent. Specifically, consider the following indicators: \n\n"
            "1. Capacity Discipline: Does the transcript discuss reducing capacity or limiting supply? \n"
            "2. Price Leadership: Does the transcript mention intentions to raise prices or encourage others to follow a similar pricing strategy? \n"
            "3. Anticipating Competitor Reactions: Are there statements about expected competitor responses to specific actions (e.g., price increases)? \n"
            "4. Contingent Conduct Announcements: Does the transcript outline actions the firm will take contingent on competitor behavior? \n"
            "5. Recommendations for Industry Behavior: Does the firm publicly suggest how competitors should behave? \n"
            "6. Forecasts of Industry Conduct: Does the transcript include predictions about competitor actions that could influence coordination? \n"
            "7. Vague References to Collusive Outcomes: Does the firm speak generally about limiting production, capacity, or competition? \n"
            "8. Statements About Industry-Wide Changes: Are there remarks about industry-wide changes, such as capacity discipline, to reduce competition? \n"
            "9. Statements Regarding Market Share: Does the transcript mention maintaining prices if market share remains stable? \n"
            "10. Discontent with Competition: Are there expressions of dissatisfaction with low prices or excessive competition? \n\n"
            "Provide an overall assessment of whether the transcript contains evidence of collusive intent:\n"
            "- Whether there is any evidence of collusive intent (True/False)\n"
            "- If you found evidence, list which of the indicators you found \n"
            "- Provide a score (0-100) indicating your confidence in the assessment \n"
            "- Provide excerpts supporting your evidence."
        ),
        'response_format': ResponseIndicators2
    }
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