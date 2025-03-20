#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if prompt name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <prompt_name> [--source <source>] [--balanced <n>] [--no-save]"
    echo "  prompt_name: Name of the prompt to run"
    echo "  --source: Source of transcripts (joe or acl)"
    echo "  --balanced: Number of balanced transcripts to select"
    echo "  --no-save: Don't save responses to database"
    exit 1
fi

# Get prompt name from first argument
PROMPT_NAME=$1
shift

# Run the Python script
python src/py/populate_benchmarking_data.py "$PROMPT_NAME" "$@"

# Update the leaderboard
echo "Updating leaderboard..."
python src/py/make/create_leaderboard.py

echo "Benchmark complete and leaderboard updated!" 