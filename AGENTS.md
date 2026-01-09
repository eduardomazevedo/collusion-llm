# Repository Guidelines

## Project Structure & Modules
- `modules/` for LLM, batch, and DB helpers; `src/` staged as `setup/` (env/data), `pre_query/` (WRDS pulls), `query_submission/` (single/batch prompts), `post_query/` (analysis/exports), and `cli/` (DB wrappers). `Snakefile` wires the pipeline. Prompts/config live in `assets/`. Data sits under `data/`; manuscripts in `manuscript/`; dataset codebooks mirror `data/` in `data_codebook/`.

## Build, Run & Data Commands
- Bootstrap + venv: `bash ./src/setup/setup.sh` then `source .venv/bin/activate`.
- Configure Drive sync: `rclone config` (remote `collusion-llm`).
- DB ops: `bash ./src/cli/db_manager.sh download|init|--export-queries|--export-analysis`.
- Pipeline: `snakemake --cores 2`.
- Prompt benchmarking: `bash ./src/query_submission/single_queries/run_benchmark.sh <prompt_name> [--source joe --balanced 50]`.
- Batching: `bash ./src/query_submission/batch_queries/run_batch.sh <company_ids> <prompt_name> --operation create|submit|status` or `run_big_batch.sh <prompt_name> create|submit|all`.

## Coding Style & Analysis Scripting
- Python 3.13; PEP8, 4-space indents, snake_case, PascalCase for classes; lean on helpers in `modules/utils.py`.
- Version prompt keys (e.g., `SimpleCapacityV8.1.1`) and keep schemas aligned with `modules/llm.py`. Run scripts from `ROOT` set in `.env`.
- Analysis scripts should be linear/notebook-friendly (#%%), with a top docstring and minimal boilerplate. Use `.venv` for execution. For ad-hoc analysis, use `scratch.py`, print results only, and delete afterward.
- No repo-wide test suite is checked in; add `pytest` cases under `tests/` when introducing new logic.

## Data & Artifacts
- Key data dirs: `datasets/` (core inputs), `intermediaries/`, `outputs/` (tables/figures), `raw/`, `yaml/`, `cache/`. Use rclone for heavy artifacts.
- When accessing data files in scripts, use os.path.join instead of writing out the full path (this ensures code can be run from Windows and Mac machines using different file path convetions)
- Maintain codebooks in `data_codebook/` matching dataset paths (description, generating script, variable notes).
- Outputs: tables usually CSV + LaTeX; large exploratory tables may be CSV-only. Figures should ship as PDF and PNG in 1:1 and 16:9 without titles. Place a sibling `.txt` note describing each table/figure and its producing script. Misc stats go to `data/yaml/`.

## Prompt Workflow
- Add a prompt to `assets/prompts.json`, benchmark it, review outputs, then scale via batch scripts. Current thresholds (`config.py`): `JOE_SCORE_THRESHOLD=50`, `LLM_SCORE_THRESHOLD=75`, `ANALYSIS_SCORE_THRESHOLD=75`.

## Commit & PR Guidelines
- Small, focused commits with sentence-style subjects; avoid committing generated outputs unless reviewed. Do not credit the assistant in commit messages.
- PRs should note scope, commands run, data/remote/model dependencies, and sample output paths; call out schema or prompt-version changes and regenerated tables/figures.

## Security & Configuration
- Keep secrets in `.env` (`OPENAI_API_KEY`, `WRDS_USERNAME`, `WRDS_PASSWORD`, `ROOT`); confirm `ROOT` before running scripts that touch remote paths. Do not commit databases or raw transcripts; sanitise company identifiers in shared logs.

## General Guidelines
- usually we need to set current directory appropriately and activate venv before running scripts
- if a user asks something about a dataset, run a quick code that is necessary to get the information
- if a user wants to do a quick analysis and wants to hold on to the code, see if a scratch directory exists (make one if there isn't one already) and write the new analysis script in there; if you're not sure whether the user wants this as a scratch script based on the user request, ask the user to confirm; if anything there's any dataset that would be produced by the a scratch script, it should be placed in another directory scratch_outputs (again, if this dones't exist it should be created); such outputs should be named intuitively but concisely so that the user finds them easily in the scratch_outputs directory
- if something is not clear from the user input regarding the code style, use the style of other scripts already present in the repository
- if something you need to run looks like it will take too long and the command would time out, ask the user if he prefers to run the command himself in the terminal and provide relevant output
- generally, when creating any script or updating a script with some new functionality, there should be relevant print statements so that when the code is run in the terminal the user can see what is happening (the most clear example here would be a script that would do a repetitive action over a larger dataset; in this case the user needs to see as print statements some sort of progress out of total steps, and this can be either step by step or every 5 or 10 or whatever amount of steps)
- when creating a script that runs over a larger dataset to produce output for many observations of a dataset, the script logic should ensure that the file where the output is placed would be saved either every sep or every 5 or 10 or some number of steps so that if the code breaks for some reason, that output is not lost; ask the user if unsure whether this should be done
- if you try to do something as Codex like running a script or command and you keep failing for some reason, explain what is happenin to the user and see if there is something the user can do immediately to help (e.g. grant some permissions, run something himself in the terminal, etc)

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
- Figures should use the Ghibli color palette defined in `modules/colors.py`. Import and use the module as follows:
  - Use `from modules.colors import GHIBLI_COLORS, ghibli_palette, apply_ghibli_theme, STYLE_CONFIG`
  - **Always call `apply_ghibli_theme()` at the start of figure generation** to set matplotlib defaults (grid, colors, fonts, etc.)
  - **Avoid overriding theme settings** - the theme handles grid, fonts, colors, and other styling centrally
  - For categorical plots, use `GHIBLI_COLORS` which provides a standard sequence: Red (primary), Deep Teal (secondary), Gold (highlight), Blue, Green, Gray
  - For full palette access, use `ghibli_palette` dictionary
  - Use `STYLE_CONFIG` for standard styling elements: error bars, annotation lines, and text should use black (`STYLE_CONFIG["error_color"]`, `STYLE_CONFIG["line_color"]`, `STYLE_CONFIG["text_color"]`)
  - **For histograms and bar charts**: Explicitly add black borders using `edgecolor=STYLE_CONFIG["edge_color"], linewidth=STYLE_CONFIG["edge_width"]` in the plotting call (e.g., `ax.hist(data, edgecolor=STYLE_CONFIG["edge_color"], linewidth=STYLE_CONFIG["edge_width"])`)
  - **For scatter plots**: Do not add borders (no edgecolor parameter)
  - Grid color uses light gray from the palette (`STYLE_CONFIG["grid_color"]`) and appears behind plot elements automatically
  - Background is white for standard scientific paper style
- Make exceptions when these colors do not work well, such as with a continuous scale.
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

**For numerical values**, the script creates multiple file formats with precision options:
- `_int.txt`: Integer with thousands separators (e.g., "1,234")
- `_float0.txt`, `_float1.txt`, `_float2.txt`: Float with 0, 1, or 2 decimal places and commas (e.g., "1,235", "1,234.6", "1,234.56")
- `_float.txt`: Backward-compatible alias for `_float2.txt` (2 decimals)
- `_percentage0.txt`, `_percentage1.txt`, `_percentage2.txt`: Percentage with 0, 1, or 2 decimal places and escaped % (e.g., "12\%", "12.3\%", "12.34\%")
- `_percentage.txt`: Backward-compatible alias for `_percentage2.txt` (2 decimals)
- `_scientific.txt`: Scientific notation (e.g., "1.23e+03")

**For date strings** (YYYY-MM-DD format):
- `.txt`: Original date string (e.g., "2023-05-15")
- `_date.txt`: Formatted date (e.g., "May 15th, 2023")

**For regular strings and other types**: Saved as `.txt` with literal content.

**Usage Examples:**
"Our analysis includes \data{summary_stats/total_transcripts_int} earnings call transcripts spanning \data{summary_stats/time_period_years_int} years."
"The LLM identified potential collusive communication in \data{correlates_collusive_communication/collusion_rate_percentage1} of all transcripts."
"The average market value was \$\data{correlates_collusive_communication/avg_market_value_float1} million, with a standard deviation of \data{correlates_collusive_communication/std_market_value_scientific}."

**Choosing Precision:**
- Use `_float0`, `_float1`, or `_float2` to control decimal places for floats (0, 1, or 2 decimals)
- Use `_percentage0`, `_percentage1`, or `_percentage2` to control decimal places for percentages (0, 1, or 2 decimals)
- The base `_float.txt` and `_percentage.txt` files default to 2 decimals for backward compatibility

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

