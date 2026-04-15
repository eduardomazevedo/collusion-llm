#!/bin/bash
set -euo pipefail

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (three levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

DOWNLOAD_HELPER="$PROJECT_ROOT/src/cli/download_public_google_drive.sh"

# Queries database
bash "$DOWNLOAD_HELPER" \
    "1MTFPFwWTLjIkeHrs7EsHo6uQ0gyEy-fV" \
    "$PROJECT_ROOT/data/datasets/queries.sqlite" \
    "queries.sqlite"

# Human ratings
bash "$DOWNLOAD_HELPER" \
    "1z2eddx34O1f9M2JFJP-cvtYf7qzQ0qzj" \
    "$PROJECT_ROOT/data/raw/human_ratings/joe_scores.csv" \
    "Joe scores"

bash "$DOWNLOAD_HELPER" \
    "1oOQ9TZ8odcFrpZmbZ0a1ykNoBLdqtl-a" \
    "$PROJECT_ROOT/data/raw/human_ratings/acl_scores.csv" \
    "ACL scores"

# ANAC raw files
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

    bash "$DOWNLOAD_HELPER" \
        "$file_id" \
        "$PROJECT_ROOT/data/raw/anac/${year}.csv" \
        "ANAC ${year}.csv"
done

echo "Replication data download complete."
