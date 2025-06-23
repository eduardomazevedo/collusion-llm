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

You can also sort the leaderboard by any available metric using the `--sort` option:
```bash
bash ./src/bash/update_leaderboard.sh --sort <metric>
```

Available metrics for sorting:
- `combined_accuracy` (default)
- `joe_accuracy`
- `acl_accuracy`
- `joe_pos_precision`
- `joe_pos_recall`
- `joe_neg_precision`
- `joe_neg_recall`
- `acl_pos_precision`
- `acl_pos_recall`
- `acl_neg_precision`
- `acl_neg_recall`

For example, to sort by ACL positive precision:
```bash
bash ./src/bash/update_leaderboard.sh --sort acl_pos_precision
```

## Leaderboard Interpretation

### Overall Metrics
- `combined_accuracy`: Weighted average of Joe's accuracy (50%) and ACL accuracy (50%)
- `joe_accuracy`: Accuracy on Joe's dataset (continuous scores 0-100)
- `acl_accuracy`: Accuracy on ACL dataset (binary classification)

### Dataset Metrics
- `_pos_precision`: How many of the predicted positive cases (score ≥ threshold) are actually positive
- `_pos_recall`: How many of the actual positive cases were correctly identified
- `_neg_precision`: How many of the predicted negative cases (score < threshold) are actually negative
- `_neg_recall`: How many of the actual negative cases were correctly identified

### Interpreting the Metrics
- A prompt with high positive precision but low positive recall is conservative in identifying collusion
- A prompt with high positive recall but low positive precision tends to over-predict collusion
- The same principles apply to negative cases (non-collusion)

The leaderboard is sorted by `combined_accuracy` in descending order by default, but you can sort by any other metric using the `--sort` option. For example, if false positives are more costly than false negatives, you might want to sort by precision metrics.

## Database Export (for review)
The project uses SQLite for storing query results. The database is stored in `data/queries.db`. To export the database to CSV:

```bash
./src/bash/export_db.sh [output_path]
```
If no output path is specified, it will create a timestamped file in the `output` directory.

## Running Batches
`bash ./src/bash/run_batch.sh <company_ids> <prompt_name> [options]`

### Required Arguments
- `company_ids`: Single company ID or comma-separated list (e.g., "12345" or "12345,67890")
- `prompt_name`: Name of the prompt from prompts config (e.g., "ComprehensiveV1")

### Operations
Use `--operation` flag with:
- `create`: Generate batch input file
- `submit`: Submit batch to OpenAI
- `status`: Check batch progress
- `process`: Save completed results to database
- `error`: Check batch error information
- `models`: List available OpenAI models

### Optional Arguments
- `--batch-id <id>`: Required for `status`, `process`, and `error` operations
- `--input-file <path>`: Custom input (relative) file path for `submit` operation (default: `output/batch_inputs/<prompt_name>_input.jsonl`)

## Running Big Batches (All Companies)
`bash ./src/bash/run_big_batch.sh <prompt_name> <operation>`

Process all companies in the Capital IQ sample using the big batch runner. This handles OpenAI's size limits automatically and provides robust error handling with fallback to individual API calls.

### Required Arguments
- `prompt_name`: Name of the prompt from prompts config (e.g., "ComprehensiveV1")
- `operation`: One of the following:
  - `create`: Create batch files for all companies
  - `submit`: Submit and monitor all batches
  - `all`: Create and submit batches in sequence

### Features
- **Automatic batching**: Creates one batch per company to stay within OpenAI limits
- **Token management**: Tracks queue usage and waits when limits are reached
- **Error recovery**: Falls back to individual API calls if batch API fails
- **Progress tracking**: Monitors all batches and saves results to database
- **Resume capability**: Can restart from where it left off if interrupted

### Example Usage
```bash
# Create batches for all companies
bash ./src/bash/run_big_batch.sh SimpleCapacityV8.1.1 create

# Submit and monitor all batches
bash ./src/bash/run_big_batch.sh SimpleCapacityV8.1.1 submit

# Create and submit in one command
bash ./src/bash/run_big_batch.sh SimpleCapacityV8.1.1 all
```

Progress is tracked in `data/batch-tracker.csv` and results are automatically saved to the database as batches complete.

Recommentations:
- Run the create procedure individually first, and then the submission.
- Resume submit procedure if necessary to accommodate rate limitations in batch or individual API submissions