#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if virtual environment directory exists
if [ ! -d "venv311" ]; then
    # Create virtual environment with Python 3.11
    /opt/homebrew/bin/python3.11 -m venv venv311
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source venv311/bin/activate
echo "Virtual environment activated."

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    # Install requirements
    pip install -r requirements.txt
    echo "Requirements installed."
else
    echo "requirements.txt not found."
fi

# Install wrds without prerequisites
pip install wrds==3.2.0 --no-deps

# Install openai
pip install openai