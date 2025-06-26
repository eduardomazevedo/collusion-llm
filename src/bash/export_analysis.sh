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
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --analysis-prompt NAME  Analysis prompt name to filter by"
    echo "  -o, --output PATH          Custom output path for CSV file"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --analysis-prompt SimpleExcerptAnalyzer"
    echo "  $0 --analysis-prompt SimpleExcerptAnalyzer --output output/my_results.csv"
    echo "  $0  # Export all analysis results"
}

# Default values
ANALYSIS_PROMPT=""
OUTPUT_PATH=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--analysis-prompt)
            ANALYSIS_PROMPT="$2"
            shift 2
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
PYTHON_CMD="python src/py/export_analysis.py"

if [ ! -z "$ANALYSIS_PROMPT" ]; then
    PYTHON_CMD="$PYTHON_CMD --analysis-prompt \"$ANALYSIS_PROMPT\""
fi

if [ ! -z "$OUTPUT_PATH" ]; then
    PYTHON_CMD="$PYTHON_CMD --output \"$OUTPUT_PATH\""
fi

# Execute the Python script
echo "Exporting analysis results to CSV..."
eval $PYTHON_CMD

echo "Export complete!" 