# Source Code Directory Structure

This directory contains all source code for the collusion detection project, organized by workflow stages.

## Directory Overview

### setup/
Initial setup and configuration scripts:
- `setup.sh` - Master setup script that runs all initialization
- `setup_venv.sh` - Creates and configures Python virtual environment
- `download_credentials.sh` - Downloads credentials from cloud storage
- `initialize_db.py` - Creates empty SQLite database with schema

### pre_query/
Data preparation and dataset creation before LLM queries:
- **data_preparation/** - Scripts to download and format raw data
  - Capital IQ transcript data
  - Human ratings (Joe's scores, ACL flags)
  - Compustat financial data
- **dataset_creation/** - Scripts to create derived datasets
  - Company-year financial datasets
  - Main analysis dataset combining all sources
  - GVKEY mappings for company identification

### query_submission/
LLM query execution and batch processing:
- **single_queries/** - Run prompts on specific transcripts
  - Benchmarking on human-rated test sets
- **batch_queries/** - Large-scale batch processing
  - Process specific company lists
  - Process entire dataset in batches
  - Handle API rate limits and failures

### post_query/
Analysis and export of query results:
- **analysis/** - Statistical analysis and insights
  - High-score analysis
  - Correlation studies
  - Performance metrics
- **benchmarking/** - Evaluate prompt performance
  - F1 score calculations
  - Leaderboard generation
- **exports/** - Export data in various formats
  - Unified export script for all data types
  - CSV and Excel output options
- **analysis_queries/** - Follow-up analysis on high-scoring results

### Other Directories

- **cli/** - Command-line interfaces (database management)
- **tex_scripts/** - LaTeX manuscript compilation
- **archive/** - Deprecated or historical scripts

## Common Workflows

1. **Setup New Environment**
   ```bash
   bash src/setup/setup.sh
   ```

2. **Run Benchmark Test**
   ```bash
   source .venv/bin/activate
   python src/query_submission/single_queries/populate_benchmarking_data.py SimpleCapacityV8.1.1 --source joe
   ```

3. **Export Results**
   ```bash
   bash src/post_query/exports/unified_export.sh --type all
   ```

## Python Script Usage

Most Python scripts have built-in help:
```bash
source .venv/bin/activate
python <script_name> --help
```

Shell wrappers are provided for complex workflows that require multiple steps or environment setup.