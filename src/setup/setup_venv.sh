#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check that uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv not found. Please install uv and retry."
    exit 1
fi

PYTHON_VERSION="$(tr -d '[:space:]' < .python-version)"

# Check if virtual environment directory exists and is valid
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo "Virtual environment already exists."
else
    if [ -d ".venv" ]; then
        echo "Existing .venv is missing bin/activate; recreating..."
        rm -rf .venv
    fi

    uv venv .venv --python "$PYTHON_VERSION"
    echo "Virtual environment created with uv."
fi

# Activate virtual environment
source .venv/bin/activate
echo "Virtual environment activated."

# Install project dependencies
uv sync
echo "Requirements installed."
