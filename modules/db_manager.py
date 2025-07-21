import os
import sqlite3
import subprocess
import config
from modules.queries_db import export_to_csv, export_analysis_to_csv

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
        expected_queries_columns = {
            'query_id', 'prompt_name', 'transcriptid', 'date', 'response',
            'LLM_provider', 'model_name', 'call_type', 'temperature',
            'max_response', 'input_tokens', 'output_tokens'
        }
        
        if not all(col in columns for col in expected_queries_columns):
            return False
        
        # Check if analysis_queries table exists and has expected columns
        cursor.execute("PRAGMA table_info(analysis_queries)")
        columns = [col[1] for col in cursor.fetchall()]
        expected_analysis_columns = {
            'analysis_query_id', 'reference_query_id', 'prompt_name', 'date', 
            'response', 'LLM_provider', 'model_name', 'call_type', 
            'temperature', 'max_response', 'input_tokens', 'output_tokens'
        }
        
        if columns and not all(col in columns for col in expected_analysis_columns):
            return False
            
        # Check if queries table has any data
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
        print("1. Create a new database: bash ./src/cli/db_manager.sh init")
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

def initialize_database() -> bool:
    """
    Create the database and tables if they don't exist.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    # Check if database exists in Google Drive
    if check_remote_database_exists():
        print("\nWarning: Database already exists in Google Drive!")
        print("To avoid losing data, please download the existing database using:")
        print("bash ./src/cli/db_manager.sh download")
        print("\nIf you're sure you want to create a new database, delete the existing one from Google Drive first.")
        return False

    print("\nCreating new database...")
    try:
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Create queries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queries (
                    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_name TEXT NOT NULL,
                    transcriptid INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    response TEXT NOT NULL,
                    LLM_provider TEXT,
                    model_name TEXT,
                    call_type TEXT,
                    temperature REAL,
                    max_response INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER
                )
            ''')
            
            # Create analysis_queries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_queries (
                    analysis_query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference_query_id INTEGER NOT NULL,
                    prompt_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    response TEXT NOT NULL,
                    LLM_provider TEXT,
                    model_name TEXT,
                    call_type TEXT,
                    temperature REAL,
                    max_response INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    FOREIGN KEY (reference_query_id) REFERENCES queries (query_id)
                )
            ''')
            
            conn.commit()
            
        print("Database created successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"Error creating database: {e}")
        return False

def export_queries(output_path=None, prompt_names=None, latest_only=False):
    """
    Export queries database to CSV.
    
    Args:
        output_path: Optional custom output path for CSV file
        prompt_names: Optional list of prompt names to filter by
        latest_only: If True, only export the latest query result for each transcript
        
    Returns:
        str: Path to the exported CSV file
    """
    try:
        export_path = export_to_csv(
            output_path=output_path,
            prompt_names=prompt_names,
            latest_only=latest_only
        )
        print(f"Queries exported successfully to: {export_path}")
        return export_path
    except Exception as e:
        print(f"Error exporting queries: {e}")
        return None

def export_analysis(output_path=None, analysis_prompt_name=None, include_original=True):
    """
    Export analysis results to CSV.
    
    Args:
        output_path: Optional custom output path for CSV file
        analysis_prompt_name: Optional analysis prompt name to filter by
        include_original: If True, include original query data in export
        
    Returns:
        str: Path to the exported CSV file
    """
    try:
        export_path = export_analysis_to_csv(
            output_path=output_path,
            analysis_prompt_name=analysis_prompt_name,
            include_original=include_original
        )
        print(f"Analysis results exported successfully to: {export_path}")
        return export_path
    except Exception as e:
        print(f"Error exporting analysis: {e}")
        return None

def get_database_info():
    """
    Get information about the database.
    
    Returns:
        dict: Dictionary with database statistics or None if error
    """
    if not verify_database(config.DATABASE_PATH):
        print("Database not found or invalid.")
        return None
        
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()
        
        info = {}
        
        # Get queries count
        cursor.execute("SELECT COUNT(*) FROM queries")
        info['total_queries'] = cursor.fetchone()[0]
        
        # Get unique transcripts count
        cursor.execute("SELECT COUNT(DISTINCT transcriptid) FROM queries")
        info['unique_transcripts'] = cursor.fetchone()[0]
        
        # Get unique prompts
        cursor.execute("SELECT DISTINCT prompt_name FROM queries")
        info['prompts'] = [row[0] for row in cursor.fetchall()]
        
        # Get latest query date
        cursor.execute("SELECT MAX(date) FROM queries")
        info['latest_query_date'] = cursor.fetchone()[0]
        
        # Get analysis queries count
        cursor.execute("SELECT COUNT(*) FROM analysis_queries")
        info['total_analysis_queries'] = cursor.fetchone()[0]
        
        # Get unique analysis prompts
        cursor.execute("SELECT DISTINCT prompt_name FROM analysis_queries")
        info['analysis_prompts'] = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return info
        
    except sqlite3.Error as e:
        print(f"Error getting database info: {e}")
        return None 