#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if prompt name is provided
if [ -z "$1" ]; then
    echo "Usage: ./run_benchmark.sh <prompt_name> [options]"
    echo "Options:"
    echo "  --source <joe|acl>     Filter transcripts by source"
    echo "  --balanced <size>      Run on balanced random subset of specified size"
    echo "  --no-save             Do not save responses to database"
    echo ""
    echo "Examples:"
    echo "  ./run_benchmark.sh SimpleCapacityV8"
    echo "  ./run_benchmark.sh SimpleCapacityV8 --source joe"
    echo "  ./run_benchmark.sh SimpleCapacityV8 --balanced 10"
    echo "  ./run_benchmark.sh SimpleCapacityV8 --source joe --balanced 10"
    echo "  ./run_benchmark.sh SimpleCapacityV8 --no-save"
    exit 1
fi

# Get the prompt name
PROMPT_NAME=$1
shift  # Remove the prompt name from arguments

# Run the Python script with all remaining arguments
python src/py/populate_benchmarking_data.py "$PROMPT_NAME" "$@" 