#!/bin/bash
# Download the file from rclone remote
rclone copyto collusion-llm:/credentials/env-file ./.env

echo "Downloaded credentials from rclone remote to ./.env"

# Add ROOT variable with path for the root to .env:
PROJECT_ROOT=$(git rev-parse --show-toplevel)
echo "" >> .env
echo "# Root folder" >> .env
echo "ROOT=$PROJECT_ROOT" >> ./.env

echo "Added ROOT variable with path for the root to .env"