#!/bin/bash

# Activate virtual environment
source venv/bin/activate
echo "Virtual environment activated."

# Run the Python script
python3 ./src/py/make/format_human_ratings.py