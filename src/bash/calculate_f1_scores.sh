#!/bin/bash

# Calculate F1 scores for different LLM approaches
# Usage: bash calculate_f1_scores.sh [--prompt PROMPT_NAME] [--threshold THRESHOLD] [--output OUTPUT_PATH]

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Please run setup.sh first"
    exit 1
fi

# Activate virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Default values
PROMPT=""
THRESHOLD="75.0"
JOE_THRESHOLD="50.0"
ANALYSIS_THRESHOLD="75.0"
OUTPUT="$PROJECT_ROOT/data/f1_scores.csv"
DETAILED=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)
            PROMPT="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --joe-threshold)
            JOE_THRESHOLD="$2"
            shift 2
            ;;
        --analysis-threshold)
            ANALYSIS_THRESHOLD="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --detailed)
            DETAILED="--detailed"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --prompt PROMPT_NAME           Specific prompt name to analyze (default: all prompts)"
            echo "  --threshold THRESHOLD          Threshold for LLM score binary conversion (default: 75.0)"
            echo "  --joe-threshold THRESH         Threshold for Joe's score binary conversion (default: 50.0)"
            echo "  --analysis-threshold THRESHOLD Threshold for analysis score validation (default: 75.0)"
            echo "  --output OUTPUT_PATH           Output CSV file path (default: data/f1_scores.csv)"
            echo "  --detailed                     Print detailed metrics including confusion matrices"
            echo "  --help, -h                     Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Calculate F1 scores for all prompts"
            echo "  $0"
            echo ""
            echo "  # Calculate F1 scores for a specific prompt"
            echo "  $0 --prompt SimpleCapacityV8.1.1"
            echo ""
            echo "  # Use a different threshold"
            echo "  $0 --threshold 65.0"
            echo ""
            echo "  # Save to a different file"
            echo "  $0 --output output/custom_f1_scores.csv"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Calculating F1 scores..."
echo "Project root: $PROJECT_ROOT"
echo "LLM threshold: $THRESHOLD"
echo "Joe's threshold: $JOE_THRESHOLD"
echo "Analysis threshold: $ANALYSIS_THRESHOLD"
echo "Output file: $OUTPUT"

if [ -n "$PROMPT" ]; then
    echo "Prompt filter: $PROMPT"
fi

# Build command
CMD="python \"$PROJECT_ROOT/src/py/calculate_f1_scores.py\""
CMD="$CMD --threshold $THRESHOLD"
CMD="$CMD --joe-threshold $JOE_THRESHOLD"
CMD="$CMD --analysis-threshold $ANALYSIS_THRESHOLD"
CMD="$CMD --output \"$OUTPUT\""

if [ -n "$PROMPT" ]; then
    CMD="$CMD --prompt \"$PROMPT\""
fi

if [ -n "$DETAILED" ]; then
    CMD="$CMD $DETAILED"
fi

# Run the command
eval $CMD

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "F1 scores successfully calculated!"
    echo "Results saved to: $OUTPUT"
else
    echo ""
    echo "Error: Failed to calculate F1 scores"
    exit 1
fi