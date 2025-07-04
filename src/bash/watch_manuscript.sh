#!/bin/bash

# Watch for changes in manuscript files and auto-compile
# This script monitors .tex, .bib, and .sty files in the manuscript directory

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

# Check if fswatch is installed
if ! command -v fswatch &> /dev/null; then
    print_error "fswatch is not installed. Installing with Homebrew..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        print_error "Homebrew is not installed. Please install Homebrew first:"
        echo "Visit https://brew.sh for installation instructions"
        exit 1
    fi
    
    # Install fswatch
    print_info "Installing fswatch..."
    brew install fswatch
    
    if ! command -v fswatch &> /dev/null; then
        print_error "Failed to install fswatch"
        exit 1
    fi
fi

# Check if manuscript directory exists
if [ ! -d "$MANUSCRIPT_DIR" ]; then
    print_error "Manuscript directory not found: $MANUSCRIPT_DIR"
    exit 1
fi

# Check if compile script exists
if [ ! -f "$COMPILE_SCRIPT" ]; then
    print_error "Compile script not found: $COMPILE_SCRIPT"
    exit 1
fi

# Trap Ctrl+C to exit cleanly
trap 'echo -e "\n${GREEN}[WATCHER]${NC} Stopping manuscript watcher..."; exit' INT

print_status "Starting manuscript watcher..."
print_info "Watching for changes in: $MANUSCRIPT_DIR"
print_info "Files monitored: *.tex, *.bib, *.sty"
print_info "Press Ctrl+C to stop"
echo ""

# Variable to track if we're currently compiling
COMPILING=false

# Function to compile manuscript
compile_manuscript() {
    if [ "$COMPILING" = true ]; then
        print_info "Compilation already in progress, skipping..."
        return
    fi
    
    COMPILING=true
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
    COMPILING=false
}

# Initial compilation
print_info "Running initial compilation..."
compile_manuscript

# Watch for changes
# -r: recursive
# -e: exclude patterns
# -i: include patterns
fswatch -r \
    -e ".*" \
    -i "\\.tex$" \
    -i "\\.bib$" \
    -i "\\.sty$" \
    --event Created \
    --event Updated \
    --event Removed \
    --event Renamed \
    --event MovedFrom \
    --event MovedTo \
    "$MANUSCRIPT_DIR" | while read file event; do
    
    # Skip auxiliary files that might be created during compilation
    if [[ "$file" =~ \.(aux|bbl|bcf|blg|log|out|run\.xml|synctex\.gz|fdb_latexmk|fls)$ ]]; then
        continue
    fi
    
    # Extract just the filename for display
    filename=$(basename "$file")
    
    print_info "Change detected: $filename"
    compile_manuscript
done