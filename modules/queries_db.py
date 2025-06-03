import config
import sqlite3
from datetime import datetime, timezone
import pandas as pd
from modules.db_manager import download_database as download_db, upload_database as upload_db

# Open a persistent connection when the module loads
conn = sqlite3.connect(config.DATABASE_PATH)
cursor = conn.cursor()

def insert_query_result(
    prompt_name: str,
    transcript_id: int,
    response: str,
    llm_provider: str = "openai",
    model_name: str = "gpt-4o-mini",
    call_type: str = "single",
    temperature: float = None,
    max_response: int = None,
    input_tokens: int = None,
    output_tokens: int = None
):
    """
    Insert a new query result into the database using an open connection.
    
    Args:
        prompt_name: Name of the prompt used
        transcript_id: ID of the transcript
        response: The LLM response
        llm_provider: The LLM provider (e.g. "openai")
        model_name: The model name (e.g. "gpt-4o-mini")
        call_type: Type of call ("single" or "batch")
        temperature: Temperature setting used
        max_response: Maximum response tokens
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """
    cursor.execute(
        """
        INSERT INTO queries (
            prompt_name, transcript_id, date, response,
            LLM_provider, model_name, call_type,
            temperature, max_response, input_tokens, output_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prompt_name, transcript_id, datetime.now(timezone.utc).isoformat(), response,
            llm_provider, model_name, call_type,
            temperature, max_response, input_tokens, output_tokens
        ),
    )
    conn.commit()

def fetch_all_queries():
    """Fetch all query results and return a pandas DataFrame."""
    cursor.execute("SELECT * FROM queries")
    
    rows = cursor.fetchall()
    columns = [
        'query_id', 'prompt_name', 'transcript_id', 'date', 'response',
        'LLM_provider', 'model_name', 'call_type',
        'temperature', 'max_response', 'input_tokens', 'output_tokens'
    ]
    return pd.DataFrame(rows, columns=columns)

def fetch_queries_by_prompts(prompt_names: list[str]):
    """
    Fetch query results for specific prompt names and return a pandas DataFrame.
    
    Args:
        prompt_names: List of prompt names to filter by
    """
    placeholders = ','.join(['?'] * len(prompt_names))
    cursor.execute(f"SELECT * FROM queries WHERE prompt_name IN ({placeholders})", prompt_names)
    
    rows = cursor.fetchall()
    columns = [
        'query_id', 'prompt_name', 'transcript_id', 'date', 'response',
        'LLM_provider', 'model_name', 'call_type',
        'temperature', 'max_response', 'input_tokens', 'output_tokens'
    ]
    return pd.DataFrame(rows, columns=columns)

def get_latest_queries(df: pd.DataFrame = None):
    """
    Get the latest query result for each transcript from the given DataFrame.
    If no DataFrame is provided, uses all queries.
    
    Args:
        df: Optional DataFrame to filter from. If None, uses all queries.
    """
    if df is None:
        df = fetch_all_queries()
    
    # Convert date column to datetime for proper sorting
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date in descending order and keep first occurrence (latest) for each transcript
    return df.sort_values('date', ascending=False).drop_duplicates(subset=['transcript_id', 'prompt_name'], keep='first')

def export_to_csv(output_path: str = None, prompt_names: list[str] = None, latest_only: bool = False):
    """
    Export the queries database to a CSV file with optional filtering.
    
    Args:
        output_path: Path where to save the CSV file. If None, uses a default path
                    in the output directory with timestamp.
        prompt_names: Optional list of prompt names to filter by. If None, exports all queries.
        latest_only: If True, only exports the latest query result for each transcript.
    
    Returns:
        Path to the exported CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/visualize_db_{timestamp}.csv"
    
    # Fetch queries based on filters
    if prompt_names:
        df = fetch_queries_by_prompts(prompt_names)
    else:
        df = fetch_all_queries()
    
    # Get latest entries if requested
    if latest_only:
        df = get_latest_queries(df)
    
    # Create output directory if it doesn't exist
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} queries to {output_path}")
    
    return output_path

def close_db():
    """Close the database connection. Call this when shutting down."""
    conn.close()

def upload_db():
    """Uploads the database to Google Drive using rclone with safety checks."""
    return upload_db()

def download_db():
    """Downloads the latest database from Google Drive using rclone with safety checks."""
    return download_db()
