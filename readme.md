# Setup
  - `rclone config` to set rclone remote `collusion-llm` pointing to Google drive folder.
  - `bash ./src/bash/setup.sh` 

# Example .env file
OPENAI_API_KEY = abc123
WRDS_USERNAME = sauron
WRDS_PASSWORD = mordor123
ROOT=/Users/sauron/projects/collusion-llm

# Pipeline
  - Setup: `bash ./src/bash/setup.sh`
  - Database management:
    - Initialize new database: `bash ./src/bash/manage_db.sh init`
    - Or get latest: `bash ./src/bash/manage_db.sh download`
    - Check status: `bash ./src/bash/manage_db.sh status`
  - Run prompts on transcripts: `bash ./src/bash/run_benchmark.sh <prompt_name> [--source <joe|acl>] [--balanced <size>]`
    - Assess prompt performance: "data/leaderboard.csv" updates every time `run_benchmark.sh` runs
  - Upload database: `bash ./src/bash/manage_db.sh upload`

### Updating Leaderboard with New Threshold
To update the leaderboard with a new threshold value:
1. Change the `binary_threshold` default value in `src/py/make/create_leaderboard.py`
2. Run: `bash ./src/bash/update_leaderboard.sh`
