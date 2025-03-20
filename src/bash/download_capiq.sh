#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source .venv/bin/activate
echo "Virtual environment activated."

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Run the Python script
python3 src/py/make/download_capiq_details.py