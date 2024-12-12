#!/bin/bash

# Define the directory containing the scripts
SCRIPT_DIR="./src/bash"

# List of scripts to run
SCRIPTS=("setup_venv.sh" "download_credentials.sh" "download_capiq.sh")

# Iterate over the scripts and execute each one
for script in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="$SCRIPT_DIR/$script"
    if [ -f "$SCRIPT_PATH" ]; then
        echo "Running $script..."
        bash "$SCRIPT_PATH"
    else
        echo "Script $script not found in $SCRIPT_DIR"
    fi
done