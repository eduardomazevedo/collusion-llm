import pandas as pd
import re

def keep_most_recent_transcripts(df):
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