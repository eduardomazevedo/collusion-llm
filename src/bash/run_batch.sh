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

# Check if company IDs and prompt name are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <company_ids> <prompt_name> [--operation <operation>] [--batch-id <batch_id>] [--input-file <input_file>]"
    echo "  company_ids: Company ID(s) to process (comma-separated if multiple)"
    echo "  prompt_name: Name of the prompt to use"
    echo "  --operation: Operation to perform (create, submit, status, process, error, models)"
    echo "  --batch-id: Batch ID for status/process operations"
    echo "  --input-file: Input file path for submit operation"
    exit 1
fi

# Get company IDs and prompt name from arguments
COMPANY_IDS=$1
PROMPT_NAME=$2
shift 2

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Run the Python script
python src/py/batch_processor_runner.py "$COMPANY_IDS" "$PROMPT_NAME" "$@"

echo "Batch processing complete!" 