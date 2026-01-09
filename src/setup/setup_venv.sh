#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if virtual environment directory exists and is valid
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo "Virtual environment already exists."
else
    if [ -d ".venv" ]; then
        echo "Existing .venv is missing bin/activate; recreating..."
        rm -rf .venv
    fi
    # Create virtual environment with Python 3
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Error: python3 not found. Please install Python 3 and retry."
        exit 1
    fi
    python3 -m venv .venv
    echo "Virtual environment created."
fi

# Activate virtual environment
source .venv/bin/activate
echo "Virtual environment activated."

# Install requirements
pip install --upgrade pip
pip install uv
uv sync
echo "Requirements installed."

# Install wrds without prerequisites
uv pip install wrds==3.3.0
