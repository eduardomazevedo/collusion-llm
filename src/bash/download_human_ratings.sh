#!/bin/bash
# Download the file from rclone remote
rclone copyto collusion-llm:/raw-data/joe_scores.csv ./data/raw/joe_scores.csv
rclone copyto collusion-llm:/raw-data/acl_scores.csv ./data/raw/acl_scores.csv


echo "Downloaded human ratings from rclone remote to ./data/raw/"