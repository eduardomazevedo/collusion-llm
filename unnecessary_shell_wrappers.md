# Unnecessary Shell Wrappers Analysis

## Shell Scripts That Can Be Safely Removed

The following shell scripts are simple wrappers that only activate the virtual environment and run Python scripts that already have proper argparse CLI interfaces:

### 1. **src/post_query/analysis_queries/analyze_high_scores.sh**
- Python script: `src/post_query/analysis/analyze_high_scores.py`
- Has full argparse with all the same options the shell script provides
- Shell script just duplicates the argument parsing logic

### 2. **src/query_submission/batch_queries/run_batch.sh**
- Python script: `src/query_submission/batch_queries/batch_processor_runner.py`
- Has full argparse CLI interface
- Shell script only activates venv and passes arguments through

### 3. **src/query_submission/single_queries/run_benchmark.sh**
- Python script: `src/query_submission/single_queries/populate_benchmarking_data.py`
- Has full argparse CLI interface
- Shell script adds an extra step (updating leaderboard) but this could be done in the Python script

### 4. **src/post_query/exports/export_db.sh**
- Python script: `src/post_query/exports/export_queries.py`
- Has full argparse with all options
- Shell script duplicates argument parsing

### 5. **src/post_query/benchmarking/calculate_f1_scores.sh**
- Python script: `src/post_query/benchmarking/calculate_f1_scores.py`
- Has full argparse CLI interface
- Shell script duplicates all the argument parsing logic

### 6. **src/post_query/benchmarking/update_leaderboard.sh**
- Python script: `src/post_query/benchmarking/create_leaderboard.py`
- Has argparse for the --sort option
- Shell script only adds venv activation

### 7. **src/post_query/exports/export_analysis.sh**
- Python script: `src/post_query/exports/export_analysis.py`
- Has full argparse CLI interface
- Shell script duplicates argument parsing

### 8. **src/query_submission/batch_queries/run_big_batch.sh**
- Python script: `src/query_submission/batch_queries/big_batch_runner.py`
- Has full argparse CLI interface
- Shell script adds some validation and logging, but this could be moved to the Python script

## Shell Scripts That Should Be Kept

The following shell scripts should be kept because their Python counterparts don't have argparse or the shell scripts add significant logic:

### Keep These:
1. **src/post_query/exports/export_token_sizes.sh** - Python script has no argparse
2. **src/post_query/exports/export_companies.sh** - Python script has no argparse
3. **src/post_query/exports/make_visualizer.sh** - Python script has no argparse
4. **src/pre_query/data_preparation/download_*.sh** - These perform file operations with rclone, not just Python calls
5. **src/setup/*.sh** - Setup scripts with complex logic
6. **src/tex_scripts/*.sh** - LaTeX compilation scripts with complex logic
7. **src/cli/db_manager.sh** - Complex database management with multiple operations

## Recommendation

To safely remove the unnecessary wrappers:

1. Update any documentation or scripts that reference the shell wrappers to use the Python scripts directly
2. Add shebang lines to Python scripts if not present: `#!/usr/bin/env python3`
3. Make Python scripts executable: `chmod +x script.py`
4. Users can then run directly: `python src/path/to/script.py [args]` or `./src/path/to/script.py [args]`

For virtual environment activation, users can:
- Manually activate before running: `source .venv/bin/activate`
- Or create a simple alias/function in their shell profile
- Or use a Python runner script that handles venv activation