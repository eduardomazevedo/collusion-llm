#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Source the Python environment to get config paths
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

ANAC_DIR="$PROJECT_ROOT/data/raw/anac"
mkdir -p "$ANAC_DIR"

YEARS=(2011 2012 2013 2014 2015 2016)

for year in "${YEARS[@]}"; do
    remote_path="collusion-llm:/raw-data/${year}.csv"
    local_path="$ANAC_DIR/${year}.csv"
    echo "Downloading ${year}.csv..."
    rclone copyto "$remote_path" "$local_path"
done

echo "Downloaded ANAC files to: $ANAC_DIR"
