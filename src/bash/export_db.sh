#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv"
    echo "Please run setup.sh first to create the virtual environment"
    exit 1
fi

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Export to CSV
if [ -z "$1" ]; then
    # No output path specified, use default
    echo "Exporting local database to CSV (default path)..."
    python src/py/export_queries.py
else
    # Use specified output path
    echo "Exporting local database to $1..."
    python src/py/export_queries.py "$1"
fi

echo "Export complete!" 