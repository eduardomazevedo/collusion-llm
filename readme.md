# Collusion Detection with LLMs

This project uses Large Language Models (LLMs) to detect potential collusive behavior in corporate earnings call transcripts. The system analyzes public company communications to identify signs of price-fixing or capacity limitation coordination between competitors.

# Quick Start
Steps 1-4 can be run upon cloning the repo.

## 1. Create the environment with `uv`
Assumes `uv` is installed.
```
uv sync
```

## 2. Create and fill in `.env`
Copy `.env.example` to `.env` and fill in any needed credentials:
```
cp .env.example .env
```

Then edit `.env` so it includes:
```
OPENAI_API_KEY=your_openai_api_key_here
WRDS_USERNAME=your_wrds_username_here
WRDS_PASSWORD=your_wrds_password_here
ROOT=/absolute/path/to/collusion-llm
```

Some steps will not work without a properly configured `.env`, especially WRDS- and OpenAI-dependent workflows.

## 3. Run analysis pipeline
```
uv run snakemake --cores 2
```

For paper replication, Snakemake now handles the key upstream inputs in the intended order:
1. download the public replication data bundle inputs (`queries.sqlite`, human ratings, and ANAC raw files) from Google Drive
2. rebuild `data/datasets/transcript_detail.feather` from WRDS
3. deduplicate transcript versions using the downloaded queries DB as the preferred transcript-version source
4. run the downstream analysis pipeline

## Optional: configure rclone for active query workflows
You do not need `rclone` for paper replication.

`rclone` is only needed if you want to use the repo for manual database management or for running and syncing your own query database. If running for the first time, create remote named `collusion-llm`.
```
rclone config
```

## Manual database operations
These commands are still available for inspection and maintenance, but they require `rclone` and are not needed for standard replication:
```
bash ./src/cli/db_manager.sh download  # Get latest database manually
bash ./src/cli/db_manager.sh init      # Initialize queries database with two tables; don't use if database already exists
bash ./src/cli/db_manager.sh status    # Show local database status
```

# Testing and Running New Prompts

## Adding a New Prompt
1. Edit `assets/prompts.json` to add your new prompt with:
   - A unique prompt name (e.g., "MyNewPromptV1")
   - The system_message containing your prompt instructions
   - The response_format (this corresponds to a a class defined in the llm module)

## Testing on Benchmark Dataset
First test your prompt against human-labeled transcripts to evaluate performance:
```
# Basic usage
bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name>

# With options
bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name> --source joe --balanced 50
```

This script first calls populate_benchmarking data.py which:
- Selects transcripts with human ratings from the database
- Queries the LLM with your prompt for each of those transcripts
- Saves results to the queries database
Then calls calculate_benchmark.py which:
- Updates the performance leaderboard comparing LLM vs human scores
- Outputs a csv file at BENCHMARKING_PATH (it updates and rewrites the file if it already exists)

Notes:
- benchmarking uses thresholds for LLM provided scores, Joe's scores, and if available follow up analysis scores according to threshold values set in config.py

## Batch Processing Options

### Individual Batch Processing
For processing specific companies:
```
# Create and submit batch for specific companies
bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> --operation create
bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> --operation submit --input-file <path>

# Check status
bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> --operation status --batch-id <id>
```

What happens:
- Fetches transcripts for specified companies from database
- Creates batch request file for OpenAI API
- Submits batch for async processing
- Saves results to the queries database

### Big Batch Processing
For processing all transcripts in the database:
```bash
# Option 1: Create batches only (for review before submission)
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> create

# Option 2: Submit existing batches
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> submit

# Option 3: Create and submit in one command
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> all
```

What happens:

**Batch Creation Phase:**
- Loads transcript-company mappings and pre-calculated token sizes
- Creates diagnostic CSV (`transcript_diagnostics.csv`) tracking each transcript's assignment
- Groups transcripts by company into JSONL batch files in `data/cache/{prompt_name}_batches/`
- Validates each batch stays within OpenAI limits (50K requests, 10M tokens)
- Reports missing transcripts and token usage statistics

**Submission and Monitoring Phase:**
- Creates/updates `data/cache/batch_tracker.csv` with batch status, estimated costs, and progress
- Monitors OpenAI's token queue limit (10M tokens max in flight)
- Submits batches when queue capacity allows, waiting when necessary (batch completion slows down after many consecutive batch jobs; best practice is to pause batch submission for a day if progress is deemed too slow)
- Long-running process (hours/days) with progress updates every 30 seconds
- Automatically falls back to individual API calls for failed batches (despite estimating the in-progress batch queue from transcript token sizes and prompt token sizes, the queue at OpenAI might fill up sooner than expected; if a submitted batch goes over the queue limit, it is returned as failed; best practice is to allow "cool down time" by switching to individual API requests, or pausing submissions for a day)
- Saves completed results directly to queries database
- Tracks completion status to avoid reprocessing (useful when breaking and resuming processing for "cool down time")


## Visualizing Data
For easy inspection of LLM output use the following:
```bash
# To export all queries (or a subset, using options)
bash src/cli/db_manager.sh --export-queries

# TO export follow up analysis queries (or a subset, using options)
bash src/cli/db_manager.sh --export-analysis
```

# Example .env file (used for config)
OPENAI_API_KEY=abc123
WRDS_USERNAME=sauron
WRDS_PASSWORD=mordor123
ROOT=/Users/sauron/projects/collusion-llm




