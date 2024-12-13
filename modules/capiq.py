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


def ciqtranscriptcomponenttype():
    """
    Returns dataframe with the table ciqtranscriptcomponenttype.
    """
    global _ciqtranscriptcomponenttype
    if _ciqtranscriptcomponenttype is None:
        query = "SELECT * FROM ciq.ciqtranscriptcomponenttype"
        _ciqtranscriptcomponenttype = _conn.raw_sql(query)
    return _ciqtranscriptcomponenttype


def dl_transcripts(transcriptids, limit=1000):
    """
    Fetch transcript data and associated person data based on a list of IDs.

    Args:
        transcriptids (list of int): A list of transcript IDs.
        limit (int): Maximum number of rows to fetch. Defaults to 1000.

    Returns:
        tuple: A tuple containing two pandas.DataFrames:
               - The first DataFrame contains all transcript data for the provided IDs.
               - The second DataFrame contains associated person data.
    """
    # Ensure transcriptids is a list of integers
    transcriptids = [int(tid) for tid in transcriptids]  # Ensure all IDs are integers

    # Query to check if all IDs exist in the database
    id_list = ', '.join(map(str, transcriptids))
    check_query = f"""
    SELECT DISTINCT transcriptid FROM ciq.ciqtranscriptcomponent
    WHERE transcriptid IN ({id_list})
    """
    existing_ids_df = _conn.raw_sql(check_query)
    existing_ids = set(existing_ids_df['transcriptid'])

    # Check if any IDs are missing
    missing_ids = set(transcriptids) - existing_ids
    if missing_ids:
        raise ValueError(f"No matching data found for the following transcript IDs: {missing_ids}")

    # Query to fetch transcript data for the valid IDs
    transcript_query = f"""
    SELECT * FROM ciq.ciqtranscriptcomponent
    WHERE transcriptid IN ({id_list})
    LIMIT {limit}
    """
    transcript_df = _conn.raw_sql(transcript_query)

    # Query to fetch person data for the valid IDs
    person_query = f"""
    SELECT transcriptcomponentid, transcriptid, transcriptpersonname, companyofperson, speakertypename
    FROM ciq.wrds_transcript_person
    WHERE transcriptid IN ({id_list})
    LIMIT {limit}
    """
    person_df = _conn.raw_sql(person_query)

    # Sort transcript data by transcriptid and componentorder
    transcript_df = transcript_df.sort_values(by=['transcriptid', 'componentorder'])

    return transcript_df, person_df


def format_transcript(transcript_df, person_df):
    # Merge ciqtranscriptcomponenttype_df to get component name instead of id.
    transcript_df = transcript_df.merge(ciqtranscriptcomponenttype(), on='transcriptcomponenttypeid', how='left')
    transcript_df = transcript_df.drop(columns=['transcriptcomponenttypeid'])

    # Merge person data    
    transcript_df = transcript_df.merge(person_df, on=['transcriptid', 'transcriptcomponentid'], how='left')
    transcript_df = transcript_df.drop(columns=['transcriptpersonid'])

    # Move 'componenttext' column to the end
    componenttext = transcript_df.pop('componenttext')
    transcript_df['componenttext'] = componenttext

    def make_text(transcriptid):
        df = transcript_df[transcript_df['transcriptid'] == transcriptid]
        df = df.drop(columns=['transcriptcomponentid', 'transcriptid', 'componentorder'])
        return df.to_json(orient='records', indent=1)
    
    transcript_texts = {}
    for transcriptid in transcript_df['transcriptid'].unique():
        text = make_text(transcriptid)
        transcript_texts[transcriptid] = text

    return transcript_texts

def get_transcripts(transcriptids, limit=1000):
    transcript_df, person_df = dl_transcripts(transcriptids, limit)
    formatted_transcripts = format_transcript(transcript_df, person_df)
    return formatted_transcripts