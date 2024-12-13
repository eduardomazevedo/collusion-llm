#!/bin/bash

# Navigate to the project root directory
cd "$(dirname "$0")/../.."

# Find all Jupyter notebooks in the src/notebooks directory and run them
for notebook in ./src/notebooks/*.ipynb; do
    echo "Running $notebook..."
    jupyter nbconvert --to notebook --execute "$notebook" --inplace
done

echo "All notebooks have been executed."