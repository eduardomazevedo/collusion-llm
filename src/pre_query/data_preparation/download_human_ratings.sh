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

# Get the paths from config using a more robust Python script
ACL_SCORES_PATH=$(python -c "
import os
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from dotenv import load_dotenv
load_dotenv()
import config
print(config.ACL_SCORES_PATH)
" 2>/dev/null)

JOE_SCORES_PATH=$(python -c "
import os
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from dotenv import load_dotenv
load_dotenv()
import config
print(config.JOE_SCORES_PATH)
" 2>/dev/null)

# If Python approach failed, fall back to default paths
if [ -z "$ACL_SCORES_PATH" ] || [ -z "$JOE_SCORES_PATH" ]; then
    echo "Warning: Could not read paths from config.py, using default paths"
    ACL_SCORES_PATH="$PROJECT_ROOT/data/raw/human_ratings/acl_scores.csv"
    JOE_SCORES_PATH="$PROJECT_ROOT/data/raw/human_ratings/joe_scores.csv"
fi

# Create the directory if it doesn't exist
mkdir -p "$(dirname "$ACL_SCORES_PATH")"
mkdir -p "$(dirname "$JOE_SCORES_PATH")"

# Download the file from rclone remote
rclone copyto collusion-llm:/raw-data/joe_scores.csv "$JOE_SCORES_PATH"
rclone copyto collusion-llm:/raw-data/acl_scores.csv "$ACL_SCORES_PATH"

echo "Downloaded human ratings from rclone remote to:"
echo "  Joe scores: $JOE_SCORES_PATH"
echo "  ACL scores: $ACL_SCORES_PATH"