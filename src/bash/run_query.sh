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

# Check if prompt name and company IDs are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <prompt_name> <company_id1> [company_id2 ...] [--transcripts <transcript_id1> <transcript_id2> ...]"
    echo "  prompt_name: Name of the prompt to run"
    echo "  company_id1, company_id2, ...: One or more company IDs to process"
    echo "  --transcripts: Optional list of specific transcript IDs to process"
    exit 1
fi

# Get prompt name from first argument
PROMPT_NAME=$1
shift

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Run the Python script with remaining arguments
python src/py/query_processor.py "$PROMPT_NAME" "$@"

echo "Query processing complete!" 