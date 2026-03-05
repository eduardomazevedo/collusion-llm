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

# Set PYTHONPATH to include the project root
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the Python script with all passed arguments
echo "Calculating comprehensive benchmark metrics..."
python3 src/post_query/benchmarking/calculate_benchmark.py "$@"

# Check if the command succeeded
if [ $? -eq 0 ]; then
    echo "Benchmark calculation complete!"
else
    echo "Error: Benchmark calculation failed"
    exit 1
fi