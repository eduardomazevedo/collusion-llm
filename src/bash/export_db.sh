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

# Parse command line arguments
OUTPUT_PATH=""
PROMPTS=()
LATEST_ONLY=false

# Function to print usage
print_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -o, --output PATH    Specify output path for the CSV file"
    echo "  -p, --prompts P1 P2  List of prompt names to filter by"
    echo "  -l, --latest-only    Only export the latest query result for each transcript"
    echo "  -h, --help          Show this help message"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        -p|--prompts)
            shift
            while [[ $# -gt 0 && ! $1 =~ ^- ]]; do
                PROMPTS+=("$1")
                shift
            done
            ;;
        -l|--latest-only)
            LATEST_ONLY=true
            shift
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
PYTHON_CMD="python src/py/export_queries.py"

if [ ! -z "$OUTPUT_PATH" ]; then
    PYTHON_CMD="$PYTHON_CMD --output $OUTPUT_PATH"
fi

if [ ${#PROMPTS[@]} -gt 0 ]; then
    PYTHON_CMD="$PYTHON_CMD --prompts ${PROMPTS[*]}"
fi

if [ "$LATEST_ONLY" = true ]; then
    PYTHON_CMD="$PYTHON_CMD --latest-only"
fi

# Execute the Python script
echo "Exporting database to CSV..."
eval $PYTHON_CMD

echo "Export complete!" 