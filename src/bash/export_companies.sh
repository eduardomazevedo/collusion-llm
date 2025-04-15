#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Run the export script
python3 src/py/export_companies.py

# Deactivate virtual environment
deactivate 