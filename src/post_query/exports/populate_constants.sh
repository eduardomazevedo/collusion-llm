#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (three levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv"
    echo "Please run setup.sh first to create the virtual environment"
    exit 1
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "=== Populating LaTeX Constants ==="

# Step 1: Generate transcript statistics YAML
echo "[1/2] Generating transcript statistics..."
python3 src/post_query/analysis/transcript_data_stats.py
if [ $? -eq 0 ]; then
    echo "✓ Transcript statistics generated successfully"
else
    echo "Error: Failed to generate transcript statistics"
    exit 1
fi

# Step 2: Convert YAML files to LaTeX constants
echo "[2/2] Converting YAML to LaTeX constants..."
python3 src/post_query/exports/populate_constants.py
if [ $? -eq 0 ]; then
    echo "✓ LaTeX constants created successfully"
else
    echo "Error: Failed to create LaTeX constants"
    exit 1
fi

echo "All constants populated successfully!"
echo "LaTeX constants are ready in: data/constants/"