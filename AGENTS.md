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

## Latex
- Figures should usually take up 100% of text width. Figures should have clear title, and detailed notes in a footnotesize minipage. Figure notes should make the paper skimmable, by having the context needed to understand them without reading the whole paper.
\begin{figure}[ht]
\centering
\includegraphics[width=\textwidth]{../data/outputs/figures/market_value_deciles_llm_16x9.pdf}
\caption{LLM Tag Rate by Market Value Decile}
\label{fig:market_value_deciles}
\begin{minipage}{\textwidth}
\vspace{1em}
\footnotesize
\textit{Notes:} This figure shows the fraction of communications tagged as collusive by the LLM across market value deciles, representing firm size. The chart displays how collusive communication detection varies with company size. Data includes \data{correlates_collusive_communication/mkvalt_valid_observations_int} firms in the size analysis.
\end{minipage}
\end{figure}