import config
import sqlite3
from datetime import datetime, timezone
import pandas as pd
from modules.db_manager import download_database as download_db, upload_database as upload_db

# Open a persistent connection when the module loads
conn = sqlite3.connect(config.DATABASE_PATH)
cursor = conn.cursor()

def insert_query_result(prompt_name: str, transcript_id: int, response: str):
    """
    Insert a new query result into the database using an open connection.
    
    Args:
        prompt_name: Name of the prompt used
        transcript_id: ID of the transcript
        response: The LLM response
    """
    cursor.execute(
        """
        INSERT INTO queries (prompt_name, transcript_id, date, response)
        VALUES (?, ?, ?, ?)
        """,
        (prompt_name, transcript_id, datetime.now(timezone.utc).isoformat(), response),
    )
    conn.commit()

def fetch_all_queries():
    """Fetch all query results and return a pandas DataFrame."""
    cursor.execute("SELECT * FROM queries")
    
    rows = cursor.fetchall()
    columns = ['query_id', 'prompt_name', 'transcript_id', 'date', 'response']
    return pd.DataFrame(rows, columns=columns)

def export_to_csv(output_path: str = None):
    """
    Export the queries database to a CSV file.
    
    Args:
        output_path: Path where to save the CSV file. If None, uses a default path
                    in the output directory with timestamp.
    
    Returns:
        Path to the exported CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/queries_export_{timestamp}.csv"
    
    # Fetch all queries
    df = fetch_all_queries()
    
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
