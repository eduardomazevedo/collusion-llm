#!/bin/bash

# Script to sync manuscript, constants, and outputs to Dropbox directory
# Usage: bash ./src/cli/ul_joe.sh

TARGET_DIR="/Users/eduaze/Library/CloudStorage/Dropbox-Penn/Eduardo Azevedo/working/2025-collusion-manuscript"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Check if target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Target directory does not exist: $TARGET_DIR"
    echo "Please create the directory first."
    exit 1
fi

echo "Target directory exists: $TARGET_DIR"
echo "Clearing contents..."
rm -rf "${TARGET_DIR:?}"/*
echo "Contents cleared."

# Copy directories (cp -r recursively copies all subdirectories)
echo "Copying ./manuscript/ to $TARGET_DIR/manuscript/..."
cp -r ./manuscript "$TARGET_DIR/"

echo "Copying ./data/constants/ to $TARGET_DIR/data/constants/..."
mkdir -p "$TARGET_DIR/data"
cp -r ./data/constants "$TARGET_DIR/data/"

echo "Copying ./data/outputs/ to $TARGET_DIR/data/outputs/..."
cp -r ./data/outputs "$TARGET_DIR/data/"

echo "Sync complete! Files are ready for editing in $TARGET_DIR"

