# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research project that uses LLMs to detect potential collusive behavior in corporate earnings call transcripts. The system analyzes public company communications to identify signs of price-fixing or capacity limitation coordination between competitors.

## Architecture

The project follows a pipeline architecture organized by workflow stages:

### Directory Structure
```
src/
├── cli/              # Command-line interfaces (db_manager.sh)
├── setup/            # Setup and initialization scripts
├── pre_query/        # Data preparation and prompt testing
│   ├── data_preparation/
│   ├── dataset_creation/
│   └── prompt_testing/
├── query_submission/ # LLM query execution
│   ├── single_queries/
│   ├── batch_queries/
│   └── analysis_queries/
└── post_query/       # Analysis and exports
    ├── benchmarking/
    ├── analysis/
    └── exports/

data/
├── datasets/         # Core datasets and databases
├── intermediaries/   # Generated intermediate files
├── outputs/          # Analysis results
├── cache/           # Temporary files and batches
└── metadata/        # Data documentation
```

### Processing Pipeline
- Data ingestion from Capital IQ (earnings call transcripts)
- LLM-based analysis using various prompts (40+ variations)
- Results storage in SQLite database (data/datasets/queries.sqlite)
- Performance evaluation against human expert ratings
- Batch processing capabilities for large-scale analysis

## Common Commands

### Setup and Environment
```bash
# Initial setup (runs all setup scripts)
bash ./src/setup/setup.sh

# Activate virtual environment
source .venv/bin/activate

# Note: Many Python scripts can now be run directly after activating the virtual environment
# Example: python src/post_query/benchmarking/calculate_f1_scores.py --help
```

### Database Management
```bash
# Initialize new database
bash ./src/cli/db_manager.sh init

# Download latest database from Google Drive
bash ./src/cli/db_manager.sh download

# Upload database to Google Drive
bash ./src/cli/db_manager.sh upload

# Export database to CSV  
python ./src/post_query/exports/export_queries.py [--output output_path] [--prompts prompt1 prompt2] [--latest-only]
```

### Running Analysis
```bash
# Run benchmark on test transcripts
bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name> [--source <joe|acl>] [--balanced <size>]
# Or run Python script directly:
# python ./src/query_submission/single_queries/populate_benchmarking_data.py <prompt_name> [options]

# Process batch of companies
bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> [options]

# Run large-scale batch processing
bash ./src/query_submission/batch_queries/run_big_batch.sh <prompt_name> <operation>  # operation: create, submit, or all

# Update leaderboard
bash ./src/post_query/benchmarking/update_leaderboard.sh [--sort <metric>]

# Calculate F1 scores and comprehensive metrics
python ./src/post_query/benchmarking/calculate_f1_scores.py [options]
# Options:
#   --prompt <name>           Specific prompt to analyze
#   --threshold <value>       LLM score threshold (default: 75.0)
#   --joe-threshold <value>   Joe's score threshold (default: 50.0)
#   --analysis-threshold <val> Analysis validation threshold (default: 75.0)
#   --detailed               Show detailed metrics
# Example:
python ./src/post_query/benchmarking/calculate_f1_scores.py --prompt SimpleCapacityV8.1.1 --threshold 50 --joe-threshold 50 --analysis-threshold 75 --detailed

# Unified data export (NEW)
bash ./src/post_query/exports/unified_export.sh --type <type> [options]
# Types: queries, analysis, companies, tokens, visualizer, all
# Examples:
#   Export all queries as CSV:
#   bash ./src/post_query/exports/unified_export.sh --type queries
#
#   Export analysis with specific prompt as Excel:
#   bash ./src/post_query/exports/unified_export.sh --type analysis --analysis-prompt SimpleExcerptAnalyzer --format excel
#
#   Export everything except slow operations:
#   bash ./src/post_query/exports/unified_export.sh --type all --output-dir exports/batch_export/
#
#   Create visualization Excel for high scores:
#   bash ./src/post_query/exports/unified_export.sh --type visualizer
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

### LaTeX Manuscript Compilation
```bash
# Compile the manuscript with bibliography
bash ./src/tex_scripts/compile_manuscript.sh

# The script handles the full pdflatex + biber workflow automatically
# Output PDF: manuscript/manuscript.pdf

# Auto-compile on file changes (watches .tex, .bib, .sty files)
bash ./src/tex_scripts/watch_manuscript.sh      # Uses fswatch (more efficient)
# OR
bash ./src/tex_scripts/watch_manuscript_simple.sh  # Simple polling method

# The watcher will:
# - Run initial compilation
# - Monitor for changes every 2 seconds
# - Auto-recompile when files are saved
# - Show colored status messages
# - Press Ctrl+C to stop
```

## Key Modules and Their Purposes

- **`modules/llm.py`**: Core LLM interface for OpenAI API calls
- **`modules/batch_processor.py`**: Handles OpenAI batch API operations
- **`modules/queries_db.py`**: Database operations and query management
- **`modules/capiq.py`**: Capital IQ data interface
- **`modules/utils.py`**: Utility functions for data processing (includes `extract_score_from_unstructured_response`)
- **`modules/db_manager.py`**: High-level database management

## Important Patterns

### Configuration
- Environment variables loaded from `.env` file (OPENAI_API_KEY, WRDS_USERNAME, WRDS_PASSWORD, ROOT)
- `config.py` ensures working directory is always project root
- Prompts stored in `assets/prompts.json`
- LLM model specifications in `assets/llm_config.json`

### Database Schema
- **queries table**: Stores LLM analysis results for transcripts
- **analysis_queries table**: Stores follow-up analysis on high-scoring transcripts
- Foreign key relationships maintained between tables

### Naming Conventions
- **File naming**: Use underscores in file names (e.g., `calculate_f1_scores.py`, not `calculate-f1-scores.py`)
- **Database fields**: Use `transcriptid` and `companyid` (no underscore) to match WRDS/CapIQ naming conventions
- **Python variables**: Use snake_case (e.g., `transcript_id`, `company_id`) when working within Python code

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
- Use `python ./src/post_query/exports/export_token_sizes.py` to analyze token usage

## Common Workflows

### Adding a New Prompt
1. Add prompt definition to `assets/prompts.json`
2. Test with benchmark: `bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name>`
3. Review leaderboard results
4. If satisfactory, run batch processing

### Analyzing Results
1. Export results: `python ./src/post_query/exports/export_analysis.py`
2. High score analysis: `python ./src/query_submission/analysis_queries/analyze_high_scores.py`
3. Use notebooks in `src/notebooks/` for custom analysis

### Debugging Failed Batches
1. Check batch status in data/intermediaries/batch-tracker.csv
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
