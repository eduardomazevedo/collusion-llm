# Setup
  - `rclone config` to set rclone remote `collusion-llm` pointing to Google drive folder.
  - `bash ./src/bash/setup.sh` sets up Python environment, downloads credentials, wrds data, raw data.

# Example .env file
OPENAI_API_KEY = abc123
WRDS_USERNAME = sauron
WRDS_PASSWORD = mordor123
ROOT=/Users/sauron/projects/collusion-llm

# Pipeline
  - `bash ./src/bash/run.sh` runs the pipeline.
