#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Download the file from rclone remote
rclone copyto collusion-llm:/credentials/env-file .env

echo "Downloaded credentials from rclone remote to .env"

# Add ROOT variable with path for the root to .env:
echo "" >> .env
echo "# Root folder" >> .env
echo "ROOT=$PROJECT_ROOT" >> .env

echo "Added ROOT variable with path for the root to .env"