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
    echo "Usage: $0 [--fix] [--add-metadata]"
    echo "Options:"
    echo "  --fix         Remove duplicates after analysis"
    echo "  --add-metadata Add new metadata columns and backfill default values"
    echo "  --help        Show this help message"
    exit 1
}

# Parse arguments
FIX_FLAG=""
ADD_METADATA_FLAG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_FLAG="--fix"
            shift
            ;;
        --add-metadata)
            ADD_METADATA_FLAG="--add-metadata"
            shift
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Run the Python script
python3 src/archive/fix_db.py $FIX_FLAG $ADD_METADATA_FLAG 