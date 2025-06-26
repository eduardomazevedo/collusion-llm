#!/bin/bash

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

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Function to print usage
print_usage() {
    echo "Usage: $0 <original_prompt_name> <analysis_prompt_name> [options]"
    echo ""
    echo "Arguments:"
    echo "  original_prompt_name    Name of the original prompt used to create entries"
    echo "  analysis_prompt_name    Name of the analysis prompt to use for analyzing outputs"
    echo ""
    echo "Options:"
    echo "  -t, --threshold N       Score threshold (default: 75)"
    echo "  -e, --export           Export results to CSV after analysis"
    echo "  -o, --output PATH      Custom path for CSV export"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 SimpleCapacityV8.1.1 SimpleExcerptAnalyzer"
    echo "  $0 SimpleCapacityV8.1.1 SimpleExcerptAnalyzer --threshold 80 --export"
    echo "  $0 SimpleCapacityV8.1.1 SimpleExcerptAnalyzer -t 75 -e -o output/my_analysis.csv"
}

# Check if we have the required arguments
if [ $# -lt 2 ]; then
    echo "Error: Missing required arguments"
    print_usage
    exit 1
fi

ORIGINAL_PROMPT="$1"
ANALYSIS_PROMPT="$2"
shift 2

# Default values
THRESHOLD=75
EXPORT=false
OUTPUT_PATH=""

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        -e|--export)
            EXPORT=true
            shift
            ;;
        -o|--output)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Build the Python command
PYTHON_CMD="python src/py/analyze_high_scores.py \"$ORIGINAL_PROMPT\" \"$ANALYSIS_PROMPT\" --threshold $THRESHOLD"

if [ "$EXPORT" = true ]; then
    PYTHON_CMD="$PYTHON_CMD --export"
fi

if [ ! -z "$OUTPUT_PATH" ]; then
    PYTHON_CMD="$PYTHON_CMD --export-path \"$OUTPUT_PATH\""
fi

# Execute the Python script
echo "Starting analysis of queries with score >= $THRESHOLD"
echo "Original prompt: $ORIGINAL_PROMPT"
echo "Analysis prompt: $ANALYSIS_PROMPT"
echo "-" * 50

eval $PYTHON_CMD

echo "Analysis complete!" 