#!/bin/bash

# Compile LaTeX manuscript with full bibliography processing
# This script handles the complete pdflatex + biber workflow

# Exit on error
set -e

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
MANUSCRIPT_DIR="$PROJECT_ROOT/manuscript"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if manuscript directory exists
if [ ! -d "$MANUSCRIPT_DIR" ]; then
    print_error "Manuscript directory not found: $MANUSCRIPT_DIR"
    exit 1
fi

# Change to manuscript directory
cd "$MANUSCRIPT_DIR"
print_status "Working in: $MANUSCRIPT_DIR"

# Check if manuscript.tex exists
if [ ! -f "manuscript.tex" ]; then
    print_error "manuscript.tex not found in $MANUSCRIPT_DIR"
    exit 1
fi

# Clean up auxiliary files from previous runs (optional)
print_status "Cleaning up old auxiliary files..."
rm -f manuscript.aux manuscript.bbl manuscript.blg manuscript.bcf manuscript.run.xml manuscript.log

# First pdflatex run
print_status "Running pdflatex (1st pass)..."
if ! /Library/TeX/texbin/pdflatex -interaction=nonstopmode manuscript.tex; then
    print_warning "First pdflatex run had errors (this is normal if references are undefined)"
fi

# Check if .bcf file was created (needed for biber)
if [ ! -f "manuscript.bcf" ]; then
    print_error "No .bcf file created. Bibliography processing may not be configured correctly."
    exit 1
fi

# Run biber
print_status "Running biber to process bibliography..."
if ! /Library/TeX/texbin/biber manuscript; then
    print_error "Biber failed. Check manuscript.blg for details."
    exit 1
fi

# Second pdflatex run
print_status "Running pdflatex (2nd pass)..."
if ! /Library/TeX/texbin/pdflatex -interaction=nonstopmode manuscript.tex; then
    print_warning "Second pdflatex run had errors"
fi

# Third pdflatex run (to resolve all references)
print_status "Running pdflatex (3rd pass)..."
if ! /Library/TeX/texbin/pdflatex -interaction=nonstopmode manuscript.tex; then
    print_error "Final pdflatex run failed"
    exit 1
fi

# Check if PDF was created
if [ -f "manuscript.pdf" ]; then
    print_status "Success! Manuscript compiled to: $MANUSCRIPT_DIR/manuscript.pdf"
    
    # Check for warnings in log
    if grep -q "Warning" manuscript.log; then
        print_warning "There were warnings during compilation. Check manuscript.log for details."
    fi
else
    print_error "PDF file was not created"
    exit 1
fi

# Optional: Show summary of warnings
echo ""
print_status "Compilation summary:"
echo "  - PDF location: $MANUSCRIPT_DIR/manuscript.pdf"
echo "  - Log file: $MANUSCRIPT_DIR/manuscript.log"

# Check for common issues
if grep -q "Missing character" manuscript.log; then
    print_warning "Some characters might be missing from fonts"
fi

if grep -q "Undefined control sequence" manuscript.log; then
    print_warning "There are undefined LaTeX commands"
fi

print_status "Compilation complete!"