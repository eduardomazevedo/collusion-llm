#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Run the Python script
python3 src/py/export_token_sizes.py

# Deactivate the virtual environment
deactivate 