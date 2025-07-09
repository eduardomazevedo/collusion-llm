#!/bin/bash
# Downloads compustat data from google drive.

# Create output directory if it doesn't exist
mkdir -p ./data/raw/compustat/

# Download and process compustat_us.csv.zip
echo "Downloading compustat_us.csv.zip..."
rclone copyto collusion-llm:/data/compustat/compustat_us.csv.zip ./data/raw/compustat/compustat_us.csv.zip

echo "Extracting compustat_us.csv..."
unzip -j ./data/raw/compustat/compustat_us.csv.zip -d ./data/raw/compustat/
# Find and rename the extracted CSV file to match the zip file name
find ./data/raw/compustat/ -name "*.csv" -not -name "compustat_*.csv" -exec mv {} ./data/raw/compustat/compustat_us.csv \;

# Clean up zip file
rm ./data/raw/compustat/compustat_us.csv.zip

# Download and process compustat_global.csv.zip
echo "Downloading compustat_global.csv.zip..."
rclone copyto collusion-llm:/data/compustat/compustat_global.csv.zip ./data/raw/compustat/compustat_global.csv.zip

echo "Extracting compustat_global.csv..."
unzip -j ./data/raw/compustat/compustat_global.csv.zip -d ./data/raw/compustat/
# Find and rename the extracted CSV file to match the zip file name
find ./data/raw/compustat/ -name "*.csv" -not -name "compustat_*.csv" -exec mv {} ./data/raw/compustat/compustat_global.csv \;

# Clean up zip file
rm ./data/raw/compustat/compustat_global.csv.zip

echo "Download and extraction complete!"

# Download readme file
echo "Downloading readme..."
rclone copyto collusion-llm:/data/compustat/readme.md ./data/raw/compustat/readme.md