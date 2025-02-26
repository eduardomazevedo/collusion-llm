import config
import sqlite3

def initialize_db():
    """Create the database and table if it doesn't exist."""
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                transcript_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                response TEXT NOT NULL
            )
        ''')
        conn.commit()

if __name__ == "__main__":
    initialize_db()
    print(f"Database initialized at {config.DATABASE_PATH}")
