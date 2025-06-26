import pandas as pd
import re
import json
import tiktoken
from typing import List, Dict
import modules.capiq as capiq

def eliminate_duplicate_transcripts(df):
    """
    Given a DataFrame of transcripts that may include multiple revisions
    for the same event (same keydevid), keep only the most recent version
    based on transcriptcreationdate_utc and transcriptcreationtime_utc.
    """
    # Ensure the date and time columns are in string format
    df['transcriptcreationdate_utc'] = df['transcriptcreationdate_utc'].astype(str)
    df['transcriptcreationtime_utc'] = df['transcriptcreationtime_utc'].astype(str)

    # Create a single datetime column from date + time
    df['creation_datetime'] = pd.to_datetime(
        df['transcriptcreationdate_utc'] + " " + df['transcriptcreationtime_utc'],
        format="%Y-%m-%d %H:%M:%S"
    )

    # Sort by the new datetime so that the last occurrence for each keydevid is the most recent
    df = df.sort_values(by="creation_datetime")

    # Drop duplicates on keydevid, keeping only the most recent (i.e., last) version
    df = df.drop_duplicates(subset="keydevid", keep="last")

    # Optionally drop the helper column if you don't need it anymore
    df.drop(columns="creation_datetime", inplace=True)

    return df


def get_quarter_year_from_headline(headline: str):
    """
    Extract the fiscal quarter (1/2/3/4) and year (4-digit integer) 
    from an earnings call headline string.

    Example headline:
        "Alaska Air Group, Inc., Q3 2023 Earnings Call, Oct 19, 2023"
    Returns:
        (quarter, year) e.g. (3, 2023) 
        or (None, None) if not found.
    """
    match = re.search(r'(Q[1-4])\s+(\d{4})', headline)
    if match:
        quarter = int(match.group(1)[1])  # Convert "Q1" to 1, "Q2" to 2, etc.
        year = int(match.group(2))        # Convert year to integer
        return (quarter, year)
    else:
        return (None, None)
    
def prep_transcript_for_review(transcript: List[Dict]) -> str:
    """
    Takes one transcript (from JSON object from capiq) and formats it for human review.
    e.g. Answers from Executives: Text of answer.
    """
    formatted_components = []
    for entry in transcript:
        component_type = entry.get("transcriptcomponenttypename", "Comment")
        speaker_type = entry.get("speakertypename", "Call Participant")
        component_text = entry.get("componenttext", "")
        formatted = f"{component_type} from {speaker_type}: {component_text.strip()}"
        formatted_components.append(formatted + "\n")

    formatted_transcript = "\n".join(formatted_components)

    # Replace double backslashes with a single backslash in case of escaped characters
    formatted_transcript = formatted_transcript.replace('\\\\', '\\')

    # Remove control characters except newline (\n) and tab (\t)
    formatted_transcript = re.sub(r'[^\x20-\x7E\n\t\u00A0-\uFFFF]', '', formatted_transcript)

    return formatted_transcript

def transcript_token_size(transcript_id: int) -> int:
    """
    Get the token size of a transcript after formatting it for review.
    
    Args:
        transcript_id: The ID of the transcript to process
        
    Returns:
        int: The number of tokens in the formatted transcript
    """
    # Get the raw transcript from capiq
    transcript_dict = capiq.get_transcripts([transcript_id])
    transcript_json = transcript_dict[transcript_id]
    transcript_data = json.loads(transcript_json)
    
    # Format the transcript for review
    formatted_transcript = prep_transcript_for_review(transcript_data)
    
    return token_size(formatted_transcript)

def token_size(text: str) -> int:
    """
    Get the token size of a text string.
    """
    encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(text))

def extract_invalid_response(response_string: str, keys: List[str]) -> Dict:
    """
    Extract data from a badly formatted JSON string that can't be parsed as JSON.
    
    Args:
        response_string: The badly formatted JSON string
        keys: List of known keys that should be present in the response
        
    Returns:
        Dict: Dictionary with extracted key-value pairs
    """
    # Reduce any existing spaces to a single space
    response_string = re.sub(r'\s+', ' ', response_string)
    
    # Eliminate any backslash
    response_string = response_string.replace('\\', '')
    
    # Split response using the known keys (including their double quotes)
    parts = []
    current_pos = 0
    
    for key in keys:
        key_with_quotes = f'"{key}"'
        pos = response_string.find(key_with_quotes, current_pos)
        if pos != -1:
            parts.append((key, pos))
            current_pos = pos + len(key_with_quotes)
    
    # Sort parts by position
    parts.sort(key=lambda x: x[1])
    
    result = {}
    
    # Process each part
    for i, (key, pos) in enumerate(parts):
        if key == "score":
            # Extract the first integer found between "score" and the next key or end
            start_pos = pos + len(f'"{key}"')
            if i + 1 < len(parts):
                end_pos = parts[i + 1][1]
            else:
                end_pos = len(response_string)
            
            text_between = response_string[start_pos:end_pos]
            # Find the first integer
            match = re.search(r'\d+', text_between)
            if match:
                result[key] = int(match.group())
            else:
                result[key] = None
                
        elif key == "reasoning":
            # Extract everything after the first colon, clean up the string
            start_pos = pos + len(f'"{key}"')
            if i + 1 < len(parts):
                end_pos = parts[i + 1][1]
            else:
                end_pos = len(response_string)
            
            text_between = response_string[start_pos:end_pos]
            # Find everything after the first colon
            colon_pos = text_between.find(':')
            if colon_pos != -1:
                reasoning_text = text_between[colon_pos + 1:]
                # Remove all symbols and spaces before the first letter character
                first_letter_pos = -1
                for j, char in enumerate(reasoning_text):
                    if char.isalpha():
                        first_letter_pos = j
                        break
                
                if first_letter_pos != -1:
                    reasoning_text = reasoning_text[first_letter_pos:]
                    # Remove everything from the end after the last letter character
                    last_letter_pos = -1
                    for j in range(len(reasoning_text) - 1, -1, -1):
                        if reasoning_text[j].isalpha():
                            last_letter_pos = j
                            break
                    
                    if last_letter_pos != -1:
                        reasoning_text = reasoning_text[:last_letter_pos + 1]
                    
                    result[key] = reasoning_text.strip()
                else:
                    result[key] = ""
            else:
                result[key] = ""
                
        elif key == "excerpts":
            # Extract everything after the first colon
            start_pos = pos + len(f'"{key}"')
            if i + 1 < len(parts):
                end_pos = parts[i + 1][1]
            else:
                end_pos = len(response_string)
            
            text_between = response_string[start_pos:end_pos]
            colon_pos = text_between.find(':')
            if colon_pos != -1:
                excerpts_text = text_between[colon_pos + 1:]
                
                # Check if there are square brackets
                open_bracket = excerpts_text.find('[')
                close_bracket = excerpts_text.find(']')
                
                if open_bracket != -1:
                    if close_bracket != -1:
                        # Take text between brackets
                        excerpts_text = excerpts_text[open_bracket + 1:close_bracket]
                    else:
                        # Take everything after open bracket
                        excerpts_text = excerpts_text[open_bracket + 1:]
                
                result[key] = excerpts_text.strip()
            else:
                result[key] = ""
    
    return result
