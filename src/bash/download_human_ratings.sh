#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Download the file from rclone remote
rclone copyto collusion-llm:/raw-data/joe_scores.csv data/raw/joe_scores.csv
rclone copyto collusion-llm:/raw-data/acl_scores.csv data/raw/acl_scores.csv

echo "Downloaded human ratings from rclone remote to data/raw/"