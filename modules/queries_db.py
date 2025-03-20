import config
import sqlite3
from datetime import datetime, timezone
import subprocess
import pandas as pd

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

def close_db():
    """Close the database connection. Call this when shutting down."""
    conn.close()

def upload_db():
    """Uploads the database to Google Drive using rclone."""
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    try:
        subprocess.run(["rclone", "copy", config.DATABASE_PATH, remote_path], check=True)
        print("Database uploaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error uploading database: {e}")

def download_db():
    """Downloads the latest database from Google Drive using rclone."""
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    try:
        subprocess.run(["rclone", "copy", remote_path, './data/'], check=True)
        print("Database downloaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading database: {e}")
