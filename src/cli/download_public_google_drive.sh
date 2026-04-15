#!/bin/bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: $0 <google_drive_file_id> <output_path> [label]"
    exit 1
fi

FILE_ID="$1"
OUTPUT_PATH="$2"
LABEL="${3:-$(basename "$OUTPUT_PATH")}"
TMP_PATH="${OUTPUT_PATH}.tmp"

mkdir -p "$(dirname "$OUTPUT_PATH")"

echo "Downloading ${LABEL} from public Google Drive..."

if curl -L --fail --retry 3 \
    "https://drive.usercontent.google.com/download?id=${FILE_ID}&export=download&confirm=t" \
    -o "$TMP_PATH"; then
    mv "$TMP_PATH" "$OUTPUT_PATH"
    echo "Saved ${LABEL} to ${OUTPUT_PATH}"
    exit 0
fi

echo "Primary download URL failed for ${LABEL}; trying fallback URL..."

curl -L --fail --retry 3 \
    "https://drive.google.com/uc?export=download&id=${FILE_ID}" \
    -o "$TMP_PATH"

mv "$TMP_PATH" "$OUTPUT_PATH"
echo "Saved ${LABEL} to ${OUTPUT_PATH}"
