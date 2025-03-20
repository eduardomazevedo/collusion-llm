# Setup
  - `rclone config` to set rclone remote `collusion-llm` pointing to Google drive folder.
  - `bash ./src/bash/setup.sh` sets up Python environment, downloads credentials, wrds data, raw data.

# Example .env file
OPENAI_API_KEY = abc123
WRDS_USERNAME = sauron
WRDS_PASSWORD = mordor123
ROOT=/Users/sauron/projects/collusion-llm

# Pipeline
  - Setup: `bash ./src/bash/setup.sh`
  - Format human ratings: `python ./src/py/make/format_human_ratings.py`
  - Either create or download prompt database:
    - Create: `python ./src/py/make/initialize_db.py`
    - Download: `python ./src/py/make/download_db.py`
  - Run prompts on transcripts: `bash ./src/bash/run_benchmark.sh <prompt_name> [--source <joe|acl>] [--balanced <size>] [--no-save]`
  

