#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# List of scripts to run
#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

# List of scripts to run
SCRIPTS=(
    "setup_venv.sh"
    "download_credentials.sh"
    "download_capiq.sh"
    "download_human_ratings.sh"
)

# Iterate over the scripts and execute each one
for script in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="$SCRIPT_DIR/$script"
    if [ -f "$SCRIPT_PATH" ]; then
        echo "Running $script..."
        bash "$SCRIPT_PATH"
    else
        echo "Script $script not found in $SCRIPT_DIR"
    fi
done

# Iterate over the scripts and execute each one
for script in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="$SCRIPT_DIR/$script"
    if [ -f "$SCRIPT_PATH" ]; then
        echo "Running $script..."
        bash "$SCRIPT_PATH"
    else
        echo "Script $script not found in $SCRIPT_DIR"
    fi
done

# Format human ratings
echo "Formatting human ratings..."
source .venv/bin/activate
export PYTHONPATH="$PROJECT_ROOT"
python3 src/py/make/format_human_ratings.py