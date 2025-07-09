import os
import sqlite3
import subprocess
import config

def verify_database(db_path: str) -> bool:
    """
    Verify that a database file exists and has the expected structure.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        bool: True if database is valid, False otherwise
    """
    if not os.path.exists(db_path):
        return False
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if queries table exists and has expected columns
        cursor.execute("PRAGMA table_info(queries)")
        columns = [col[1] for col in cursor.fetchall()]
        expected_columns = {
            'query_id', 'prompt_name', 'transcriptid', 'date', 'response',
            'LLM_provider', 'model_name', 'call_type', 'temperature',
            'max_response', 'input_tokens', 'output_tokens'
        }
        
        if not all(col in columns for col in expected_columns):
            return False
            
        # Check if table has any data
        cursor.execute("SELECT COUNT(*) FROM queries")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
        
    except sqlite3.Error:
        return False

def check_remote_database_exists() -> bool:
    """
    Check if the database exists in Google Drive.
    
    Returns:
        bool: True if database exists, False otherwise
    """
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    try:
        # Use rclone ls to check if file exists
        result = subprocess.run(["rclone", "ls", remote_path], capture_output=True, text=True)
        return result.returncode == 0 and config.DATABASE_PATH.split('/')[-1] in result.stdout
    except subprocess.CalledProcessError:
        return False

def download_database() -> bool:
    """
    Download the database from Google Drive.
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    
    # Check if database exists in Google Drive
    if not check_remote_database_exists():
        print("\nDatabase not found in Google Drive!")
        print("You have two options:")
        print("1. Create a new database: python ./src/py/make/initialize_db.py")
        print("2. Get the database from another team member")
        return False
    
    try:
        # Download the database
        subprocess.run(["rclone", "copy", remote_path, os.path.dirname(config.DATABASE_PATH)], check=True)
        
        # Verify the downloaded database
        if verify_database(config.DATABASE_PATH):
            print("Database downloaded and verified successfully.")
            return True
        else:
            print("Downloaded database failed verification.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error downloading database: {e}")
        return False

def upload_database() -> bool:
    """
    Upload the database to Google Drive.
    
    Returns:
        bool: True if upload was successful, False otherwise
    """
    # Verify local database before uploading
    if not verify_database(config.DATABASE_PATH):
        print("Local database failed verification. Aborting upload.")
        return False
        
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    
    try:
        # Upload the database
        subprocess.run(["rclone", "sync", config.DATABASE_PATH, remote_path], check=True)
        print("Database uploaded successfully.")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error uploading database: {e}")
        return False 