#!/bin/bash

# Check if virtual environment directory exists
if [ ! -d "venv" ]; then
    # Create virtual environment
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate
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