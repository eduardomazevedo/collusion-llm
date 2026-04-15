#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# List of scripts to run with their locations.
# NOTE: transcript_detail.feather is created later by Snakemake (WRDS step),
# so scripts that depend on transcript_detail should not run during bootstrap.
SCRIPTS=(
    "$SCRIPT_DIR/setup_venv.sh"
    "$SCRIPT_DIR/init_env.sh"
    "$PROJECT_ROOT/src/pre_query/data_preparation/download_human_ratings.sh"
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

echo "Setup bootstrap complete."
echo "If needed, edit .env to add your credentials."
echo "Next step: run 'snakemake --cores 2' to download/build transcript_detail and downstream datasets."