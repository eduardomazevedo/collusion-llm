#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# List of scripts to run with their locations
SCRIPTS=(
    "$SCRIPT_DIR/setup_venv.sh"
    "$SCRIPT_DIR/download_credentials.sh"
    "$PROJECT_ROOT/src/pre_query/data_preparation/download_capiq.sh"
    "$PROJECT_ROOT/src/pre_query/data_preparation/download_human_ratings.sh"
    "$PROJECT_ROOT/src/post_query/exports/export_companies.sh"
)

# Iterate over the scripts and execute each one
for SCRIPT_PATH in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPT_PATH" ]; then
        script_name=$(basename "$SCRIPT_PATH")
        echo "Running $script_name..."
        bash "$SCRIPT_PATH"
    else
        echo "Script $SCRIPT_PATH not found"
    fi
done

# Format human ratings
echo "Formatting human ratings..."
source .venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT"
python3 src/pre_query/data_preparation/format_human_ratings.py