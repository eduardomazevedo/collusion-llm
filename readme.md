# Replication code for Azevedo, Harrington and Rusu "Collusive Content in Corporate Communications"
 
This paper uses Large Language Models (LLMs) to detect potential collusive behavior in corporate earnings call transcripts. The repo is organized around a Snakemake file that replicates the analysis after downloading the data on queries we ran. The repo can be modified to create a new query database.

Requirements: WRDS credentials, uv. Additional requirements to run queries: rclone to sync database, and OpenAI api key.

# Replication Instructions

## 1. Create python virtual environment 
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
OPENAI_API_KEY=your_openai_api_key_here (optional)
WRDS_USERNAME=your_wrds_username_here
WRDS_PASSWORD=your_wrds_password_here
ROOT=/absolute/path/to/collusion-llm
```

Some steps will not work without a properly configured `.env`, especially WRDS- and OpenAI-dependent workflows.

## Public data download links
Readers who just want the paper data inputs can download them directly from Google Drive without running the code.

### Core replication files
- `queries.sqlite`: https://drive.google.com/file/d/1MTFPFwWTLjIkeHrs7EsHo6uQ0gyEy-fV/view?usp=sharing
- `joe_scores.csv`: https://drive.google.com/file/d/1z2eddx34O1f9M2JFJP-cvtYf7qzQ0qzj/view?usp=sharing
- `acl_scores.csv`: https://drive.google.com/file/d/1oOQ9TZ8odcFrpZmbZ0a1ykNoBLdqtl-a/view?usp=sharing

### ANAC raw files
- `2011.csv`: https://drive.google.com/file/d/1SpcX-fQeWMU0EkFsAbcmggKuc8ADqiAp/view?usp=sharing
- `2012.csv`: https://drive.google.com/file/d/1VMm6qPJT7rEi6TaWAFeo42Z-sKggK7mj/view?usp=sharing
- `2013.csv`: https://drive.google.com/file/d/1qjPAh6sNkaHOAGV-cVmx06Xi9780F7IY/view?usp=sharing
- `2014.csv`: https://drive.google.com/file/d/1AJLFJVSy1TwCgNxyt8G9DeJtYQ3Y6Jo1/view?usp=sharing
- `2015.csv`: https://drive.google.com/file/d/1_-aq0U2K1wVnZ1s9_wWRJ1PKcEH0LeW8/view?usp=sharing
- `2016.csv`: https://drive.google.com/file/d/1_WtLC6d-f8bmTijt9KDuGj95pSiZy7YL/view?usp=sharing

Note: `data/datasets/transcript_detail.feather` is rebuilt from WRDS and is therefore not included in the public Google Drive bundle above.

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