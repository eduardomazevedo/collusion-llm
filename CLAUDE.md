# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research project that uses Large Language Models to detect potential collusive behavior in corporate earnings call transcripts. The system analyzes public company communications to identify signs of price-fixing or capacity limitation coordination between competitors.

## Key Commands

### Setup and Environment
```bash
# Initial project setup
bash ./src/setup/setup.sh

# Activate virtual environment
source .venv/bin/activate

# Database management
bash ./src/cli/db_manager.sh init      # Initialize new database
bash ./src/cli/db_manager.sh download  # Get latest from Google Drive
bash ./src/cli/db_manager.sh upload    # Upload to Google Drive
bash ./src/cli/db_manager.sh status    # Check sync status
```

### Running Analysis
```bash
# Test prompt on benchmark dataset
bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name>

# Run batch processing (operations: test, run, check, download)
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> <operation>

# Calculate performance metrics
python ./src/post_query/benchmarking/calculate_benchmark.py --prompt <prompt_name>

# Run full analysis pipeline
snakemake --cores 2
```

### Development and Testing
```bash
# Run tests (using pytest)
pytest

# No specific linting command configured - check with user if needed
```

## Architecture and Code Structure

### Directory Organization
- `src/cli/` - Command-line interfaces and database management
- `src/setup/` - Project initialization and configuration
- `src/pre_query/` - Data preparation and preprocessing
- `src/query_submission/` - LLM query execution (single and batch)
- `src/post_query/` - Analysis, benchmarking, and exports
- `data/datasets/` - SQLite databases (queries.sqlite, company_transcript_data.sqlite)
- `data/outputs/` - Analysis results and exports
- `assets/prompts.json` - All prompt variations for testing

### Key Technical Details
- **Primary Model**: OpenAI gpt-4o-mini via batch API
- **Database**: SQLite with two main tables: `queries` and `analysis_queries`
- **Package Manager**: UV (not pip) - always use `uv add` for new dependencies
- **Python Version**: 3.13+
- **Config**: Central `config.py` file manages all paths and settings
- **Environment**: Requires `.env` file with OPENAI_API_KEY and WRDS credentials

### Important Patterns
1. **Naming Conventions**:
   - Python files: Use underscores (`calculate_benchmark.py`)
   - Database fields: No underscores (`transcriptid`, not `transcript_id`)
   - Variables in code: Snake case (`transcript_id`)

2. **LLM Integration**:
   - Uses Pydantic models for structured responses
   - Batch API for cost efficiency (~$0.075 per 1M input tokens)
   - Automatic chunking for 50K request limit
   - Token tracking in database

3. **Error Handling**:
   - Fallback parsing for malformed LLM responses
   - Retry logic for API failures
   - Comprehensive logging throughout

### Common Development Tasks

When modifying prompts:
1. Edit `assets/prompts.json` to add/modify prompts
2. Test with `run_benchmark.sh` against human benchmarks
3. Calculate metrics with `calculate_benchmark.py`
4. Update leaderboard to compare performance

When processing new transcripts:
1. Ensure transcript data is in the SQLite database
2. Use batch runner for large-scale processing
3. Monitor token usage and costs
4. Run downstream analysis with Snakemake

When analyzing results:
1. Use tools in `src/post_query/analysis/` for deep dives
2. Export data using scripts in `src/post_query/exports/`
3. Generate LaTeX tables/figures for manuscript