import config
import sqlite3
from modules.db_manager import check_remote_database_exists

def initialize_db():
    """Create the database and table if it doesn't exist."""
    # Check if database exists in Google Drive
    if check_remote_database_exists():
        print("\nWarning: Database already exists in Google Drive!")
        print("To avoid losing data, please download the existing database using:")
        print("bash ./src/bash/manage_db.sh download")
        print("\nIf you're sure you want to create a new database, delete the existing one from Google Drive first.")
        return False

    print("\nCreating new database...")
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                transcript_id INTEGER NOT NULL,
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
        conn.commit()
    print("Database created successfully!")
    return True

if __name__ == "__main__":
    initialize_db()
