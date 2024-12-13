"""
Module to load Capital IQ transcripts from WRDS.

Functions:
    load_transcripts(file_path: str) -> pd.DataFrame
        Loads Capital IQ transcripts from the specified file path and returns a pandas DataFrame.

    process_transcripts(df: pd.DataFrame) -> pd.DataFrame
        Processes the loaded transcripts DataFrame by cleaning and structuring the data.

    save_transcripts(df: pd.DataFrame, output_path: str) -> None
        Saves the processed transcripts DataFrame to the specified output path.

    connect() -> None
        Establishes a WRDS connection if not already open.

    disconnect() -> None
        Closes the WRDS connection if open.

    is_connection_open() -> bool
        Checks if the WRDS connection is active.
"""

import config
import wrds
import pandas as pd
import json

_conn = None  # Global variable to manage WRDS connection
_ciqtranscriptcomponenttype = None # Global for the component type descriptions

def is_connection_open():
    """
    Checks if the WRDS connection is active.

    Returns:
        bool: True if the connection is active, False otherwise.
    """
    global _conn
    if _conn is None:
        return False
    try:
        _conn.list_tables(library='ciq')
        return True
    except Exception:
        return False

def connect():
    """
    Establishes a WRDS connection if not already open.
    """
    global _conn
    if not is_connection_open():
        try:
            _conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
            print("WRDS connection established.")
        except Exception as e:
            print(f"Failed to establish WRDS connection: {e}")
    else:
        print("Already connected")

def disconnect():
    """
    Closes the WRDS connection if open.
    """
    global _conn
    if _conn is not None:
        try:
            _conn.close()
            _conn = None
            print("WRDS connection closed.")
        except Exception as e:
            print(f"Failed to close WRDS connection: {e}")

def dl_transcript(transcriptid):
    transcriptid = int(transcriptid)  # Convert transcriptid to an integer
    query = f"""
    SELECT * FROM ciq.ciqtranscriptcomponent
    WHERE transcriptid = {transcriptid}
    LIMIT 10000
    """
    df = _conn.raw_sql(query)
    
    if df.empty:
        raise ValueError(f"No matching transcript found for transcriptid: {transcriptid}")
    
    df = df.sort_values(by='componentorder')  # Sort by componentorder

    return df

def format_transcript(transcript_df):
    # _ciqtranscriptcomponenttype
    global _ciqtranscriptcomponenttype
    if _ciqtranscriptcomponenttype is None:
        query = "SELECT * FROM ciq.ciqtranscriptcomponenttype"
        _ciqtranscriptcomponenttype = _conn.raw_sql(query)

    # Merge ciqtranscriptcomponenttype_df name.
    transcript_df = transcript_df.merge(_ciqtranscriptcomponenttype, on='transcriptcomponenttypeid', how='left')
    transcript_df = transcript_df.drop(columns=['transcriptcomponenttypeid'])

    # Download wrds_transcript_person matching transcriptcomponentid. Columns to get: transcriptpersonname companyofperson speakertypename
    person_query = f"""
    SELECT transcriptcomponentid, transcriptpersonname, companyofperson, speakertypename
    FROM ciq.wrds_transcript_person
    WHERE transcriptid = {transcript_df['transcriptid'].iloc[0]}
    """
    person_df = _conn.raw_sql(person_query)
    
    transcript_df = transcript_df.merge(person_df, on='transcriptcomponentid', how='left')

    # Drop specified columns
    transcript_df = transcript_df.drop(columns=['transcriptcomponentid', 'transcriptid', 'componentorder', 'transcriptpersonid'])
    
    # Move 'componenttext' column to the end
    componenttext = transcript_df.pop('componenttext')
    transcript_df['componenttext'] = componenttext
    return transcript_df.to_json(orient='records', indent=1)

def get_transcript(transcriptid):
    df = dl_transcript(transcriptid)
    df = format_transcript(df)
    return df

