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
    echo "Usage: $0 <command> [options]"
    echo "Commands:"
    echo "  init            - Initialize a new database (if none exists in Google Drive)"
    echo "  download        - Download the latest database from Google Drive"
    echo "  upload          - Upload the current database to Google Drive"
    echo "  status          - Show the current database status"
    echo "  info            - Show detailed database information"
    echo "  export-queries  - Export queries to CSV"
    echo "  export-analysis - Export analysis results to CSV"
    echo "  help            - Show this help message"
    echo ""
    echo "Export options:"
    echo "  export-queries [--output PATH] [--prompts PROMPT1 PROMPT2 ...] [--latest-only]"
    echo "  export-analysis [--output PATH] [--analysis-prompt NAME] [--no-original]"
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

# Function to show database info
show_info() {
    echo "Getting database information..."
    python3 -c "
from modules.db_manager import get_database_info
import json

info = get_database_info()
if info:
    print(f\"\\nDatabase Statistics:\")
    print(f\"  Total queries: {info['total_queries']:,}\")
    print(f\"  Unique transcripts: {info['unique_transcripts']:,}\")
    print(f\"  Total analysis queries: {info['total_analysis_queries']:,}\")
    print(f\"  Latest query date: {info['latest_query_date']}\")
    print(f\"\\nPrompts ({len(info['prompts'])}):\")
    for prompt in info['prompts']:
        print(f\"    - {prompt}\")
    if info['analysis_prompts']:
        print(f\"\\nAnalysis prompts ({len(info['analysis_prompts'])}):\")
        for prompt in info['analysis_prompts']:
            print(f\"    - {prompt}\")
"
}

# Function to handle export-queries command
export_queries() {
    shift # Remove 'export-queries' from arguments
    
    # Build Python command with arguments
    python_cmd="from modules.db_manager import export_queries; export_queries("
    args=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output)
                args+=("output_path='$2'")
                shift 2
                ;;
            --prompts)
                shift
                prompts="["
                while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                    prompts+="'$1',"
                    shift
                done
                prompts="${prompts%,}]"
                args+=("prompt_names=$prompts")
                ;;
            --latest-only)
                args+=("latest_only=True")
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                ;;
        esac
    done
    
    # Join arguments with commas
    arg_string=$(IFS=,; echo "${args[*]}")
    python_cmd+="$arg_string)"
    
    echo "Exporting queries to CSV..."
    python3 -c "$python_cmd"
}

# Function to handle export-analysis command
export_analysis() {
    shift # Remove 'export-analysis' from arguments
    
    # Build Python command with arguments
    python_cmd="from modules.db_manager import export_analysis; export_analysis("
    args=()
    include_original="True"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output)
                args+=("output_path='$2'")
                shift 2
                ;;
            --analysis-prompt)
                args+=("analysis_prompt_name='$2'")
                shift 2
                ;;
            --no-original)
                include_original="False"
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                ;;
        esac
    done
    
    args+=("include_original=$include_original")
    
    # Join arguments with commas
    arg_string=$(IFS=,; echo "${args[*]}")
    python_cmd+="$arg_string)"
    
    echo "Exporting analysis results to CSV..."
    python3 -c "$python_cmd"
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
    "info")
        show_info
        ;;
    "export-queries")
        export_queries "$@"
        ;;
    "export-analysis")
        export_analysis "$@"
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