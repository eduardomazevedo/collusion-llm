import os
import sqlite3
import subprocess
import config
import shutil

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
        expected_columns = {'query_id', 'prompt_name', 'transcript_id', 'date', 'response'}
        
        if not all(col in columns for col in expected_columns):
            return False
            
        # Check if table has any data
        cursor.execute("SELECT COUNT(*) FROM queries")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
        
    except sqlite3.Error:
        return False

def download_database() -> bool:
    """
    Download the database from Google Drive with safety checks.
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    
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
    Upload the database to Google Drive with safety checks.
    
    Returns:
        bool: True if upload was successful, False otherwise
    """
    # Verify local database before uploading
    if not verify_database(config.DATABASE_PATH):
        print("Local database failed verification. Aborting upload.")
        return False
        
    remote_path = f"{config.RCLONE_REMOTE}:{config.RCLONE_REMOTE_DATABASE_PATH}"
    
    try:
        # First download the remote database to a temporary location
        temp_path = f"{config.DATABASE_PATH}.temp"
        subprocess.run(["rclone", "copy", remote_path, temp_path], check=True)
        
        # Verify the remote database
        if not verify_database(temp_path):
            print("Remote database failed verification. Aborting upload.")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
            
        # Get row counts
        local_conn = sqlite3.connect(config.DATABASE_PATH)
        remote_conn = sqlite3.connect(temp_path)
        local_count = local_conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        remote_count = remote_conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        local_conn.close()
        remote_conn.close()
        
        # Safety check: local database should not be smaller
        if local_count < remote_count:
            print(f"Warning: Local database ({local_count} rows) is smaller than remote ({remote_count} rows).")
            print("This could indicate data loss. Aborting upload.")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
            
        # If we get here, it's safe to upload
        subprocess.run(["rclone", "copy", config.DATABASE_PATH, remote_path], check=True)
        print(f"Database uploaded successfully. Local: {local_count} rows, Remote: {remote_count} rows")
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error uploading database: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False 