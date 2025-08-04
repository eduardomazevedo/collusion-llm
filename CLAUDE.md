# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research project that uses Large Language Models (LLMs) to detect potential collusive behavior in corporate earnings call transcripts. The system analyzes public company communications to identify signs of price-fixing or capacity limitation coordination between competitors.

## Common Development Commands

### Environment Setup
```bash
# Initial setup (creates venv, downloads data, initializes database)
bash ./src/setup/setup.sh

# Activate virtual environment
source .venv/bin/activate
```

### Database Operations
```bash
# Download latest database from Google Drive
bash ./src/cli/db_manager.sh download

# Initialize new queries database (only if doesn't exist)
bash ./src/cli/db_manager.sh init

# Export query results for visualization
bash ./src/cli/db_manager.sh --export-queries
bash ./src/cli/db_manager.sh --export-analysis
```

### Running Analysis Pipeline
```bash
# Run downstream analysis with Snakemake
snakemake --cores 2
```

### Testing Prompts
```bash
# Test prompt on benchmark dataset
bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name>

# With options
bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name> --source joe --balanced 50
```

### Batch Processing
```bash
# Individual batch processing
bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> --operation create
bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> --operation submit --input-file <path>

# Big batch processing (all transcripts)
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> create
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> submit
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> all
```

## Architecture Overview

### Core Modules
- **modules/llm.py**: Main LLM interface for synchronous API calls. Handles prompt management and response parsing using Pydantic models.
- **modules/batch_processor.py**: Manages asynchronous batch processing with OpenAI's Batch API. Handles large-scale transcript processing.
- **modules/queries_db.py**: Database interface for storing and retrieving LLM query results.
- **modules/capiq.py**: Interface to Capital IQ data for fetching transcript content.
- **modules/db_manager.py**: Database management utilities for backup/restore operations.

### Data Flow
1. **Pre-query stage**: Download and prepare data (Compustat, human ratings, transcript details)
2. **Query submission**: Process transcripts through LLM using either synchronous or batch APIs
3. **Post-query analysis**: Generate analysis datasets, calculate benchmarks, export results

### Key Configuration
- All paths and settings are centralized in `config.py`
- Environment variables required: `OPENAI_API_KEY`, `WRDS_USERNAME`, `WRDS_PASSWORD`, `ROOT`
- Prompts are defined in `assets/prompts.json`
- Model configurations in `assets/llm_config.json`

### Database Schema
- Main database: `data/datasets/queries.sqlite`
- Tables: `queries` (LLM results), `follow_up_analysis` (additional analysis)
- Transcript details stored in `data/datasets/transcript_detail.feather`

### Snakemake Pipeline
The project uses Snakemake for reproducible data processing:
- Downloads Compustat data
- Maps company IDs to GVKEYs
- Creates analysis datasets
- Generates summary statistics
- All rules defined in `Snakefile`

### Prompt Development Workflow
1. Add new prompt to `assets/prompts.json` with unique name, system_message, and response_format
2. Test on benchmark dataset using `run_benchmark.sh`
3. Review performance metrics in benchmarking output
4. Run batch processing for full dataset once satisfied with performance

### Important Thresholds
- `JOE_SCORE_THRESHOLD`: 75
- `LLM_SCORE_THRESHOLD`: 75
- `ANALYSIS_SCORE_THRESHOLD`: 75
These thresholds are used for binary classification in benchmarking and analysis.

## Git preference
Whenever asking Claude to commit and push with a message of choice, we only want that message, without any credit to Claude Code.