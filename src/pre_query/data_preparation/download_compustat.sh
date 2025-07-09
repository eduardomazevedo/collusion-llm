#!/bin/bash
# Downloads compustat data from google drive.

# Create output directory if it doesn't exist
mkdir -p ./data/raw/compustat/

# Download and process compustat-us.csv.zip
echo "Downloading compustat-us.csv.zip..."
rclone copyto collusion-llm:/data/compustat/compustat-us.csv.zip ./data/raw/compustat/compustat-us.csv.zip

echo "Extracting compustat-us.csv..."
unzip -j ./data/raw/compustat/compustat-us.csv.zip -d ./data/raw/compustat/
# Find and rename the extracted CSV file to match the zip file name
find ./data/raw/compustat/ -name "*.csv" -not -name "compustat-*.csv" -exec mv {} ./data/raw/compustat/compustat-us.csv \;

# Clean up zip file
rm ./data/raw/compustat/compustat-us.csv.zip

# Download and process compustat-global.csv.zip
echo "Downloading compustat-global.csv.zip..."
rclone copyto collusion-llm:/data/compustat/compustat-global.csv.zip ./data/raw/compustat/compustat-global.csv.zip

echo "Extracting compustat-global.csv..."
unzip -j ./data/raw/compustat/compustat-global.csv.zip -d ./data/raw/compustat/
# Find and rename the extracted CSV file to match the zip file name
find ./data/raw/compustat/ -name "*.csv" -not -name "compustat-*.csv" -exec mv {} ./data/raw/compustat/compustat-global.csv \;

# Clean up zip file
rm ./data/raw/compustat/compustat-global.csv.zip

echo "Download and extraction complete!"

# Download readme file
echo "Downloading readme..."
rclone copyto collusion-llm:/data/compustat/readme.md ./data/raw/compustat/readme.md