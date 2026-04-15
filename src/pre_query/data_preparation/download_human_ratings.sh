#!/bin/bash
set -euo pipefail

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (two levels up from the script)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Change to project root directory
cd "$PROJECT_ROOT"

JOE_SCORES_PATH="$PROJECT_ROOT/data/raw/human_ratings/joe_scores.csv"
ACL_SCORES_PATH="$PROJECT_ROOT/data/raw/human_ratings/acl_scores.csv"

bash "$PROJECT_ROOT/src/cli/download_public_google_drive.sh" \
    "1z2eddx34O1f9M2JFJP-cvtYf7qzQ0qzj" \
    "$JOE_SCORES_PATH" \
    "Joe scores"

bash "$PROJECT_ROOT/src/cli/download_public_google_drive.sh" \
    "1oOQ9TZ8odcFrpZmbZ0a1ykNoBLdqtl-a" \
    "$ACL_SCORES_PATH" \
    "ACL scores"

echo "Downloaded human ratings to:"
echo "  Joe scores: $JOE_SCORES_PATH"
echo "  ACL scores: $ACL_SCORES_PATH"
