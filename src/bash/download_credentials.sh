#!/bin/bash
# Download the file from rclone remote
rclone copyto collusion-llm:/credentials/env-file ./.env

echo "Downloaded credentials from rclone remote to ./.env"
