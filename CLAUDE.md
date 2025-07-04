# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research project that uses LLMs to detect potential collusive behavior in corporate earnings call transcripts. The system analyzes public company communications to identify signs of price-fixing or capacity limitation coordination between competitors.

## Architecture

The project follows a pipeline architecture:
- Data ingestion from Capital IQ (earnings call transcripts)
- LLM-based analysis using various prompts (40+ variations)
- Results storage in SQLite database
- Performance evaluation against human expert ratings
- Batch processing capabilities for large-scale analysis

## Common Commands

### Setup and Environment
```bash
# Initial setup (runs all setup scripts)
bash ./src/bash/setup.sh

# Activate virtual environment
source .venv/bin/activate
```

### Database Management
```bash
# Initialize new database
bash ./src/bash/manage_db.sh init

# Download latest database from Google Drive
bash ./src/bash/manage_db.sh download

# Upload database to Google Drive
bash ./src/bash/manage_db.sh upload

# Export database to CSV
bash ./src/bash/export_db.sh [output_path]
```

### Running Analysis
```bash
# Run benchmark on test transcripts
bash ./src/bash/run_benchmark.sh <prompt_name> [--source <joe|acl>] [--balanced <size>]

# Process batch of companies
bash ./src/bash/run_batch.sh <company_ids> <prompt_name> [options]

# Run large-scale batch processing
bash ./src/bash/run_big_batch.sh <prompt_name> <operation>  # operation: create, submit, or all

# Update leaderboard
bash ./src/bash/update_leaderboard.sh [--sort <metric>]

# Calculate F1 scores and comprehensive metrics
bash ./src/bash/calculate_f1_scores.sh [options]
# Options:
#   --prompt <name>           Specific prompt to analyze
#   --threshold <value>       LLM score threshold (default: 75.0)
#   --joe-threshold <value>   Joe's score threshold (default: 50.0)
#   --analysis-threshold <val> Analysis validation threshold (default: 75.0)
#   --detailed               Show detailed metrics
# Example:
bash ./src/bash/calculate_f1_scores.sh --prompt SimpleCapacityV8.1.1 --threshold 50 --joe-threshold 50 --analysis-threshold 75 --detailed
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/modules/test_llm.py

# Run tests with coverage
pytest --cov=modules tests/
```

## Key Modules and Their Purposes

- **`modules/llm.py`**: Core LLM interface for OpenAI API calls
- **`modules/batch_processor.py`**: Handles OpenAI batch API operations
- **`modules/queries_db.py`**: Database operations and query management
- **`modules/capiq.py`**: Capital IQ data interface
- **`modules/utils.py`**: Utility functions for data processing
- **`modules/db_manager.py`**: High-level database management

## Important Patterns

### Configuration
- Environment variables loaded from `.env` file (OPENAI_API_KEY, WRDS_USERNAME, WRDS_PASSWORD, ROOT)
- `config.py` ensures working directory is always project root
- Prompts stored in `assets/prompts.json`

### Database Schema
- **queries table**: Stores LLM analysis results for transcripts
- **analysis_queries table**: Stores follow-up analysis on high-scoring transcripts
- Foreign key relationships maintained between tables

### LLM Integration
- Responses use Pydantic models for structured output
- Batch processing handles OpenAI rate limits automatically
- Token tracking for cost management
- Fallback parsing for malformed responses

### Error Handling
- Graceful handling of invalid JSON responses
- Database verification before operations
- Batch status checking with retry capabilities
- Comprehensive logging throughout

## Development Tips

1. **Always activate the virtual environment** before running Python scripts
2. **Check prompt versions** in `assets/prompts.json` before creating new ones
3. **Use batch processing** for large-scale operations to manage costs
4. **Sync database** with Google Drive before and after major changes
5. **Monitor token usage** - limits are 50K requests and 40M input tokens per batch
6. **Test prompts** on benchmark set before running large batches

## Cost Considerations
- Input tokens: $0.075 per 1M tokens
- Output tokens: $0.3 per 1M tokens
- Average transcript: ~10K tokens
- Use `bash ./src/bash/export_token_sizes.sh` to analyze token usage

## Common Workflows

### Adding a New Prompt
1. Add prompt definition to `assets/prompts.json`
2. Test with benchmark: `bash ./src/bash/run_benchmark.sh <prompt_name>`
3. Review leaderboard results
4. If satisfactory, run batch processing

### Analyzing Results
1. Export results: `bash ./src/bash/export_analysis.sh`
2. High score analysis: `bash ./src/bash/analyze_high_scores.sh`
3. Use notebooks in `src/notebooks/` for custom analysis

### Debugging Failed Batches
1. Check batch status in output/batch-tracker.csv
2. Retrieve error file if batch failed
3. Resume processing with same command - it will skip completed batches

## Description of functionalities, for implementation

### Reporting performance of a prompt

We want to assess LLM performance based on how well responses match the human reviewed sample. Human reviewed sample "joe" has joe's scores between 0-100, another one called "acl" has 0/1 identifier for whether there's collusive intent in airlines public calls. The LLM response contains a score 0-100 that reflects the severity of collusive intent. 

**Threshold Configuration:**
- Joe's scores: Converted to binary using `joe_threshold` (default: 50)
- LLM scores: Converted to binary using `threshold` (default: 75)
- Analysis validation: Uses `analysis_threshold` (default: 75)

The system calculates comprehensive metrics including precision, recall, F1 score, and specificity for three subsamples: Joe's subsample, ACL's subsample, and a pooled sample. 

There are a few important notes here:
- we're really only interested in the prompt named SimpleCapacityV8.1.1 (which asked the LLM based on a transcript for a score, a reasoning and a set of excerpts from the transcript), but I want the possibility to change it to something else when I run the assessment in the future
- with the base model "gpt-4o-mini" we ran all transcripts multiple times on purpose so we can look at average scores extracted form the responses
- we also ran a follow up analysis prompt for the transcripts where the original response score was >=75, asking to get an analysis score 0-100 just based on the excerpts identified in the original response, without showing the LLM the full transcript
- as it's clear from the database structure, original prompt responses and analysis prompt responses are stored in separate tables and linked through origianl query id

Performance metric: F1 score between the human review sample ("joe" score turned to 1/0 using threshold >=75 and "acl" using their 0/1 identifier) and the following:
"non-interactive approaches":
- one off no repetition response (for a given prompt-model-transcript take score from the earliest entry); convert to 1/0 based on threshold
- average scores from all responses of a given repeated prompt-model-transcript; convert to 1/0 based on threshold
"agentic approaches":
- **agentic-repeated-high**: average scores from all responses of a given repeated prompt-transcript but only for those that were over threshold the first time (do this for model that starts with "gpt-4o-mini" because only this was run multiple times for this reason)
- **agentic-analysis**: uses corrected scores where:
  - If original score ≥ threshold AND analysis score < analysis_threshold: corrected_score = 0 (false positive)
  - Otherwise: corrected_score = original score
  - **Important**: Transcripts that scored above threshold but have no analysis score keep their original score (they are not penalized)
- **agentic-analysis-filtered**: uses original query scores but only for transcripts where analysis score ≥ analysis_threshold

We want to export a table (CSV form) with comprehensive metrics:
model | prompt | approach | followup | joe_n | joe_precision | joe_recall | joe_f1 | joe_specificity | acl_n | acl_precision | acl_recall | acl_f1 | acl_specificity | pooled_n | pooled_precision | pooled_recall | pooled_f1 | pooled_specificity

Where:
- **approach**: non-interactive-single, non-interactive-average, agentic-repeated-high, agentic-analysis, agentic-analysis-filtered
- **followup**: analysis prompt name or "none"
- Metrics calculated separately for Joe's subsample, ACL's subsample, and pooled sample


Note here: Even though we focus on the prompt called SimpleCapacityV8.1.1, when we report the "benchmark" table, we want to calculate the F1 score and show all prompts that were used on the joe and acl sample (they won't have the multiple model-prompt runs for the same transcript and they won't have follow up analysis prompts, but if they produced scores in the response, they should be coverted to 0/1 given the threshold and then used to compute F1 score versus joe and acl scores and reported in the benchmark top)
