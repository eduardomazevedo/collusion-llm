#!/bin/bash

# Default sorting metric
SORT_METRIC="combined_accuracy"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --sort-by)
      SORT_METRIC="$2"
      shift 2
      ;;
    *)
      echo "Unknown parameter: $1"
      echo "Usage: $0 [--sort-by <metric>]"
      echo "Available metrics: combined_accuracy, joe_accuracy, acl_accuracy, joe_pos_precision, joe_pos_recall, joe_neg_precision, joe_neg_recall, acl_pos_precision, acl_pos_recall, acl_neg_precision, acl_neg_recall"
      exit 1
      ;;
  esac
done

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

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

# Update the leaderboard
echo "Updating leaderboard..."
python3 src/py/make/create_leaderboard.py --sort "$SORT_METRIC"

echo "Leaderboard updated!" 