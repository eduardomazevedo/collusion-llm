#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (three levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

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

# Check if prompt name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <prompt_name> [--source <source>] [--balanced <n>]"
    echo "  prompt_name: Name of the prompt to run"
    echo "  --source: Source of transcripts (joe or acl)"
    echo "  --balanced: Number of balanced transcripts to select"
    exit 1
fi

# Get prompt name from first argument
PROMPT_NAME=$1
shift

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Run the Python script
python src/query_submission/single_queries/populate_benchmarking_data.py "$PROMPT_NAME" "$@"

# Update the leaderboard
echo "Updating leaderboard..."
python src/post_query/benchmarking/create_leaderboard.py

echo "Benchmark complete and leaderboard updated!" 