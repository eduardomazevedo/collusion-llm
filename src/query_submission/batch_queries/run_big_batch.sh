#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

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

# Check if prompt name and operation are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <prompt_name> <operation>"
    echo "  prompt_name: Name of the prompt to use"
    echo "  operation: One of the following:"
    echo "    - create: Create batches from transcripts"
    echo "    - submit: Submit and monitor batches"
    echo "    - all: Create and submit batches"
    exit 1
fi

# Get the prompt name and operation from command line arguments
PROMPT_NAME=$1
OPERATION=$2

# Validate operation
valid_operations=("create" "submit" "all")
if [[ ! " ${valid_operations[@]} " =~ " ${OPERATION} " ]]; then
    echo "Error: Invalid operation '$OPERATION'"
    echo "Valid operations are: ${valid_operations[*]}"
    exit 1
fi

# Set PYTHONPATH to the current directory
export PYTHONPATH="$PROJECT_ROOT"

# Function to check if batches exist for a prompt
check_batches_exist() {
    local prompt_name=$1
    local batches_dir="$PROJECT_ROOT/output/${prompt_name}_batches"
    echo "Checking directory: $batches_dir"
    if [ -d "$batches_dir" ] && [ -n "$(find "$batches_dir" -name "*.jsonl" -print -quit)" ]; then
        return 0  # Batches exist
    else
        return 1  # No batches found
    fi
}

# Function to check if tracking file exists
check_tracking_file() {
    local tracking_file="$PROJECT_ROOT/data/batch_tracker.csv"
    if [ -f "$tracking_file" ]; then
        return 0  # Tracking file exists
    else
        return 1  # No tracking file found
    fi
}

# Handle different operations
case "$OPERATION" in
    "create")
        echo "Creating batches for prompt: $PROMPT_NAME"
        python src/query_submission/batch_queries/big_batch_runner.py "$PROMPT_NAME" create
        if [ $? -eq 0 ]; then
            echo "Batch creation completed successfully"
            if check_batches_exist "$PROMPT_NAME"; then
                echo "Batches are ready in: output/${PROMPT_NAME}_batches"
            else
                echo "Warning: No batches were created"
            fi
        else
            echo "Error: Batch creation failed"
            exit 1
        fi
        ;;
    
    "submit")
        if ! check_batches_exist "$PROMPT_NAME"; then
            echo "Error: No batches found for prompt '$PROMPT_NAME'"
            echo "Please run 'create' operation first"
            exit 1
        fi
        
        echo "Submitting batches for prompt: $PROMPT_NAME"
        echo "Running Python script with arguments: $PROMPT_NAME submit"
        
        # Use a single log file
        LOG_FILE="submission.log"
        
        # Run the Python script and capture both stdout and stderr
        python -u src/query_submission/batch_queries/big_batch_runner.py "$PROMPT_NAME" submit 2>&1 | tee "$LOG_FILE"
        
        if [ $? -eq 0 ]; then
            echo "Batch submission completed successfully"
            if check_tracking_file; then
                echo "Progress is being tracked in: data/batch_tracker.csv"
            fi
            echo "Full submission log saved to: $LOG_FILE"
        else
            echo "Error: Batch submission failed"
            echo "Check $LOG_FILE for details"
            
            # Extract and display error information from the log
            echo -e "\nError Summary:"
            grep -i "error\|failed" "$LOG_FILE" | tail -n 10
            
            # Check for queue limit errors specifically
            if grep -i "queue.*limit\|token.*limit" "$LOG_FILE" > /dev/null; then
                echo -e "\nQueue Limit Errors Detected:"
                grep -i "queue.*limit\|token.*limit" "$LOG_FILE"
            fi
            
            exit 1
        fi
        ;;
    
    "all")
        echo "Creating and submitting batches for prompt: $PROMPT_NAME"
        
        # First create batches
        echo "Step 1: Creating batches..."
        python src/query_submission/batch_queries/big_batch_runner.py "$PROMPT_NAME" create
        if [ $? -ne 0 ]; then
            echo "Error: Batch creation failed"
            exit 1
        fi
        
        if ! check_batches_exist "$PROMPT_NAME"; then
            echo "Error: No batches were created"
            exit 1
        fi
        
        # Then submit batches
        echo "Step 2: Submitting batches..."
        python src/query_submission/batch_queries/big_batch_runner.py "$PROMPT_NAME" submit
        if [ $? -eq 0 ]; then
            echo "Batch submission completed successfully"
            if check_tracking_file; then
                echo "Progress is being tracked in: data/batch_tracker.csv"
            fi
        else
            echo "Error: Batch submission failed"
            exit 1
        fi
        ;;
esac

# Make the script executable
chmod +x src/bash/run_big_batch.sh

