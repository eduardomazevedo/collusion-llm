#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Function to display usage
show_usage() {
    echo "Usage: $0 <command>"
    echo "Commands:"
    echo "  init      - Initialize a new database (if none exists in Google Drive)"
    echo "  download  - Download the latest database from Google Drive"
    echo "  upload    - Upload the current database to Google Drive"
    echo "  status    - Show the current database status"
    echo "  help      - Show this help message"
    exit 1
}

# Function to show database status
show_status() {
    echo "Checking database status..."
    python3 -c "
import os
import sqlite3
import config

try:
    if not os.path.exists(config.DATABASE_PATH):
        print('Database file does not exist at:', config.DATABASE_PATH)
        exit(1)
        
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if queries table exists
    cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='queries'\")
    if not cursor.fetchone():
        print('Database exists but queries table is missing')
        conn.close()
        exit(1)
        
    cursor.execute('SELECT COUNT(*) FROM queries')
    count = cursor.fetchone()[0]
    print(f'Current database has {count} entries')
    
    # Get most recent entry date
    cursor.execute('SELECT MAX(date) FROM queries')
    latest_date = cursor.fetchone()[0]
    if latest_date:
        print(f'Most recent entry: {latest_date}')
    
    conn.close()
except Exception as e:
    print(f'Error checking database: {e}')
    exit(1)
"
}

# Main command handling
case "$1" in
    "init")
        echo "Initializing new database..."
        python3 -c "from modules.db_manager import initialize_database; initialize_database()"
        ;;
    "download")
        echo "Downloading database from Google Drive..."
        python3 -c "from modules.db_manager import download_database; download_database()"
        show_status
        ;;
    "upload")
        echo "Uploading database to Google Drive..."
        python3 -c "from modules.db_manager import upload_database; upload_database()"
        show_status
        ;;
    "status")
        show_status
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    *)
        echo "Unknown command: $1"
        show_usage
        ;;
esac

# Deactivate virtual environment
deactivate 