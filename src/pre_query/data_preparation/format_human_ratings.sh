#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (three levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Run the format human ratings script
python3 src/pre_query/data_preparation/format_human_ratings.py

# Deactivate virtual environment
deactivate