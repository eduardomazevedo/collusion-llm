#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if virtual environment directory exists
if [ ! -d ".venv" ]; then
    # Create virtual environment with Python 3
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
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
