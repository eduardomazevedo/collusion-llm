# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research project that uses Large Language Models (LLMs) to detect potential collusive behavior in corporate earnings call transcripts. The system analyzes public company communications to identify signs of price-fixing or capacity limitation coordination between competitors.

## Code overview
- We mostly use python.
- Scripts are in subdirectories of `./src/`. Modules are in `./modules`. We always run all scripts from root, which is done in `config.py` to avoid boilerplate.
- The project has three parts.
- 1) Download basic data on the universe of corporate communication transcripts available from the capital iq dataset. This is handled by `./src/setup/setup.sh`.
  - The most important datasets here are `data/datasets/transcript_detail.feather` which has data on the transcripts in the WRDS capital IQ data and `data/datasets/human_ratings.csv` which has human ratings for a benchmark sample of transcripts.
- 2) Using that data, we interactively used our tools to run LLM queries that were saved to our database `data/datasets/queries.sqlite`. We occasionally use a project instance to make further queries and add to the database. But most of the time we just download the version of the database on our Google Drive storage remote `bash ./src/cli/db_manager.sh download` and perform downstream analysis.
- 3) The downstream analysis is reproducible using our `./Snakefile`
  - We use some rules to tag the top trasncripts according to the LLM collusion detection.
  - We download additional data on companies from WRDS.
  - Merge this to create an analysis dataset.
  - Perform an analysis of the correlates of collusive communication.
  - Will do basic stats and human validation of the results.
  - Save this downstream output to be used in the paper and slides.
  - Evaluate the performance of different models and query methodologies on the human benchmark sample.

## Common Development Commands

### Environment Setup
```bash
# Initial setup (creates venv, downloads basic transcript data from WRDS capital iq)
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

### Running Downstream Analysis Pipeline
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

### Prompt Database Schema
- Main database: `data/datasets/queries.sqlite`
- Tables: `queries` (LLM results), `follow_up_analysis` (additional analysis)
- Transcript details stored in `data/datasets/transcript_detail.feather`

## Data management
- All data is in `data/` always .gitignored.
- `data/constants/` has txt files with numbers that can be read in our latex.
- `data/datasets/` has datasets we construct / download that are used throughout the analysis.
- `data/intermediaries/` has data files that are more sporadically used.
- `data/outputs/` has processed output that we use to write the paper, make slides, and inspect.
- `data/raw/` has raw downloaded datasets.
- `data/yaml` has yaml files written by our analysis scripts. These keep track of important stats that do not fit neatly into a table (eg number of observations). These are used to produce the `data/constants/`.
- `data_codebook/` has markdown files documenting all datasets with same folder structure as `data/`. Each codebook should have: terse description of the data, which script generates it, and list of all variables with descriptions.
- We use a Google Drive remote for storage. Should be set up as rclone remote set in config.py `RCLONE_REMOTE = "collusion-llm"` for the user.

### Codebook Template
```markdown
# filename.csv

## Description
Terse description of what the dataset contains and its purpose.

## Generated by
`path/to/script.py` or manual process description

## Variables

### variable_name
Description of the variable, including data type, scale, and any special values (NA, etc.)
```

## Downstream analysis coding guidelines
- The downstream analysis produces the final assets that we use for the paper and human reading. Goes in `data/outputs/` with subfolders `tables/`, `figures/`.
- Most tables should be output as csv and latex. The exception are large tables like `data/outputs/top_transcript_data_for_joe.csv` which are only meant to be read in spreadsheets and not for publication.
- Figures should be output as .pdf and .png, in both 1:1 and 16:9 formats. Figures and tables should not have titles because we will add them in latex.
- The code producing each figure or table should also output a .txt file in the same location in `data/outputs` with same filename but txt extension with a terse description of the asset and what script produces it.
- Scripts that calculate stats that do not fit neatly into a table should output a yaml file in `data/yaml/`. These include basic stats like number of observations, etc.
- Analysis scripts should be written sequentially, without unecessary definitions of functions, without pointless main blocks. Instead it should be data science friendly, with #%% blocks that can be run interactively.
- Every script should have a docstring that explains what it does tersely at the top.
- If I ask you questions about the data that require analysis, create a file on root called scratch.py to do your analysis. Make it print useful output but not change any files. Delete after we are 100% done with the extra analysis.
- We always use our `.venv` virtual environment. Use it when running your own code.

## Latex
- The paper manuscript files are in `./manuscript/`.
- The main latex file defines command `\newcommand{\data}[1]{\input{../data/constants/#1.txt}\unskip}` to read the constants in `data/constants/`.

### Using the `\data{}` Command for Constants
The `\data{}` command automatically imports numerical and text constants from YAML files processed by `src/post_query/exports/populate_constants.py`. The script converts YAML data into multiple format variants for flexible LaTeX usage:

**For numerical values**, the script creates multiple file formats:
- `_int.txt`: Integer with thousands separators (e.g., "1,234")
- `_float.txt`: Float with 2 decimals and commas (e.g., "1,234.56")
- `_percentage.txt`: Percentage with escaped % (e.g., "12.34\%")
- `_scientific.txt`: Scientific notation (e.g., "1.23e+03")

**For date strings** (YYYY-MM-DD format):
- `.txt`: Original date string (e.g., "2023-05-15")
- `_date.txt`: Formatted date (e.g., "May 15th, 2023")

**For regular strings and other types**: Saved as `.txt` with literal content.

**Usage Examples:**
"Our analysis includes \data{summary_stats/total_transcripts_int} earnings call transcripts spanning \data{summary_stats/time_period_years_int} years."
"The LLM identified potential collusive communication in \data{correlates_collusive_communication/collusion_rate_percentage} of all transcripts."
"The average market value was \$\data{correlates_collusive_communication/avg_market_value_float} million, with a standard deviation of \data{correlates_collusive_communication/std_market_value_scientific}."

- Figures and table floats should include detailed notes in the bottom with footnote size, that make the latex skimmable. Here is an example:
```latex
\begin{figure}[ht]
    \centering
    \includegraphics[width=1\columnwidth]{../data/outputs/figures/market_value_deciles_16x9.pdf}
    \caption{LLM Tag Rate by Market Value Decile}
    \label{fig:market_value_deciles}
    \begin{minipage}{\textwidth}
        \vspace{1em}
        \footnotesize
        \textit{Notes:} This figure shows the fraction of communications tagged as collusive by the LLM across market value deciles, representing firm size. The chart displays how collusive communication detection varies with company size. Data includes \data{correlates_collusive_communication/mkvalt_valid_observations_int} firms in the size analysis.
    \end{minipage}
\end{figure}
```

### Snakemake Pipeline
The downstream analysis (once queries database is done) uses Snakemake for reproducible data processing:
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