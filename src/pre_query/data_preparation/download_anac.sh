#!/bin/bash
set -euo pipefail

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

ANAC_DIR="$PROJECT_ROOT/data/raw/anac"
mkdir -p "$ANAC_DIR"

YEARS=(2011 2012 2013 2014 2015 2016)
FILE_IDS=(
    "1SpcX-fQeWMU0EkFsAbcmggKuc8ADqiAp"
    "1VMm6qPJT7rEi6TaWAFeo42Z-sKggK7mj"
    "1qjPAh6sNkaHOAGV-cVmx06Xi9780F7IY"
    "1AJLFJVSy1TwCgNxyt8G9DeJtYQ3Y6Jo1"
    "1_-aq0U2K1wVnZ1s9_wWRJ1PKcEH0LeW8"
    "1_WtLC6d-f8bmTijt9KDuGj95pSiZy7YL"
)

for i in "${!YEARS[@]}"; do
    year="${YEARS[$i]}"
    file_id="${FILE_IDS[$i]}"
    local_path="$ANAC_DIR/${year}.csv"

    bash "$PROJECT_ROOT/src/cli/download_public_google_drive.sh" \
        "$file_id" \
        "$local_path" \
        "ANAC ${year}.csv"
done

echo "Downloaded ANAC files to: $ANAC_DIR"
