import sqlite3
import pandas as pd
import config
import argparse
from datetime import datetime

def analyze_duplicates():
    """Analyze duplicate entries in the database."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Show database columns
    cursor.execute("PRAGMA table_info(queries)")
    columns = cursor.fetchall()
    print("\nDatabase columns:")
    for col in columns:
        print(f"- {col[1]}")
    
    # Get all entries
    df = pd.read_sql_query("SELECT * FROM queries", conn)
    
    # Find duplicates (same prompt_name, transcriptid, and response, but different query_id and date)
    duplicates = df.duplicated(subset=['prompt_name', 'transcriptid', 'response'], keep=False)
    duplicate_entries = df[duplicates]
    
    if len(duplicate_entries) == 0:
        print("\nNo duplicates found!")
        conn.close()
        return False
    
    # Show duplicate statistics
    total_entries = len(df)
    unique_entries = df.drop_duplicates(subset=['prompt_name', 'transcriptid', 'response'], keep='last')
    print(f"\nTotal entries: {total_entries}")
    print(f"Entries after deduplication: {len(unique_entries)}")
    print(f"Entries to be removed: {total_entries - len(unique_entries)}")
    
    conn.close()
    return True

def remove_duplicates():
    """Remove duplicate entries, keeping the most recent one."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    
    # Create a temporary table with deduplicated data
    conn.execute("""
        CREATE TEMPORARY TABLE temp_queries AS
        SELECT * FROM queries
        WHERE query_id IN (
            SELECT MAX(query_id)
            FROM queries
            GROUP BY prompt_name, transcriptid, response
        )
    """)
    
    # Count entries before deletion
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM queries")
    before_count = cursor.fetchone()[0]
    
    # Delete all entries from original table
    conn.execute("DELETE FROM queries")
    
    # Insert deduplicated data back
    conn.execute("""
        INSERT INTO queries
        SELECT * FROM temp_queries
    """)
    
    # Count entries after deletion
    cursor.execute("SELECT COUNT(*) FROM queries")
    after_count = cursor.fetchone()[0]
    
    # Drop temporary table
    conn.execute("DROP TABLE temp_queries")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\nRemoved {before_count - after_count} duplicate entries")
    print(f"Remaining entries: {after_count}")

def add_metadata_columns():
    """Add new metadata columns to the database and backfill with default values where possible."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Add new columns
    new_columns = [
        ('LLM_provider', 'TEXT'),
        ('model_name', 'TEXT'),
        ('call_type', 'TEXT'),
        ('temperature', 'REAL'),
        ('max_response', 'INTEGER'),
        ('input_tokens', 'INTEGER'),
        ('output_tokens', 'INTEGER')
    ]
    
    # Add each column if it doesn't exist
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE queries ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists")
            else:
                raise e
    
    # Backfill default values where possible
    cursor.execute("""
        UPDATE queries 
        SET LLM_provider = 'openai',
            model_name = 'gpt-4o-mini'
        WHERE LLM_provider IS NULL
    """)
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("\nAdded new metadata columns and backfilled default values where possible")

def main():
    parser = argparse.ArgumentParser(description='Analyze and fix duplicate entries in the database.')
    parser.add_argument('--fix', action='store_true', help='Remove duplicates after analysis')
    parser.add_argument('--add-metadata', action='store_true', help='Add new metadata columns and backfill default values')
    args = parser.parse_args()
    
    if args.add_metadata:
        add_metadata_columns()
        return
    
    # First analyze duplicates
    has_duplicates = analyze_duplicates()
    
    # If --fix flag is provided and duplicates were found, remove them
    if args.fix and has_duplicates:
        print("\nRemoving duplicates...")
        remove_duplicates()
    elif args.fix and not has_duplicates:
        print("\nNo duplicates to remove.")
    elif has_duplicates:
        print("\nTo remove duplicates, run the script with --fix flag")

if __name__ == "__main__":
    main() 