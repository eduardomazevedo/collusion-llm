#!/bin/bash

# Simple file watcher for manuscript compilation
# Uses a while loop to check for changes every few seconds

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
MANUSCRIPT_DIR="$PROJECT_ROOT/manuscript"
COMPILE_SCRIPT="$SCRIPT_DIR/compile_manuscript.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check interval in seconds
CHECK_INTERVAL=2

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[WATCHER]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to get modification time of all tex/bib/sty files
get_mod_time() {
    find "$MANUSCRIPT_DIR" -name "*.tex" -o -name "*.bib" -o -name "*.sty" 2>/dev/null | \
    xargs stat -f "%m" 2>/dev/null | sort -n | tail -1
}

# Check if manuscript directory exists
if [ ! -d "$MANUSCRIPT_DIR" ]; then
    print_error "Manuscript directory not found: $MANUSCRIPT_DIR"
    exit 1
fi

# Trap Ctrl+C to exit cleanly
trap 'echo -e "\n${GREEN}[WATCHER]${NC} Stopping manuscript watcher..."; exit' INT

print_status "Starting simple manuscript watcher..."
print_info "Watching for changes in: $MANUSCRIPT_DIR"
print_info "Files monitored: *.tex, *.bib, *.sty"
print_info "Check interval: ${CHECK_INTERVAL} seconds"
print_info "Press Ctrl+C to stop"
echo ""

# Get initial modification time
LAST_MOD=$(get_mod_time)
COMPILING=false

# Initial compilation
print_info "Running initial compilation..."
bash "$COMPILE_SCRIPT"
echo -e "${BLUE}[WATCHER]${NC} Waiting for changes...\n"

# Main watching loop
while true; do
    sleep $CHECK_INTERVAL
    
    # Get current modification time
    CURRENT_MOD=$(get_mod_time)
    
    # Check if files have been modified
    if [ "$CURRENT_MOD" != "$LAST_MOD" ] && [ "$COMPILING" = false ]; then
        COMPILING=true
        LAST_MOD=$CURRENT_MOD
        
        local timestamp=$(date '+%H:%M:%S')
        echo -e "\n${YELLOW}[$timestamp]${NC} File change detected, compiling..."
        
        # Run the compile script
        bash "$COMPILE_SCRIPT"
        
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_status "Compilation successful!"
        else
            print_error "Compilation failed with exit code $exit_code"
        fi
        
        echo -e "${BLUE}[WATCHER]${NC} Waiting for changes...\n"
        
        # Update modification time after compilation
        LAST_MOD=$(get_mod_time)
        COMPILING=false
    fi
done