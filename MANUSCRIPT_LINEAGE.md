# Manuscript Asset Lineage

This file maps the current manuscript and online appendix assets to the files and scripts that produce them.

Scope:
- Main paper: `manuscript/manuscript.tex` and the `.tex` files it inputs
- Online appendix: `manuscript/online_appendix.tex` and the `.tex` files it inputs
- Included tables and figures from `data/outputs/`
- Constants inserted through `\data{...}` from `data/constants/`

Conventions:
- "Displayed asset" means a figure or table directly included in the paper or online appendix.
- "Constant family" means a group of `\data{...}` constants coming from one YAML file.
- "Immediate upstream" means the files directly read by the generating script.

## Backbone datasets and generators

These are the main reusable intermediate files that most manuscript assets depend on.

### `data/datasets/queries.sqlite`
- Purpose: stores raw LLM query responses and follow-up analysis responses
- Written by:
  - query runners in `src/query_submission/`
  - DB insertion logic in `modules/queries_db.py`
  - LLM calling logic in `modules/llm.py`
- Used downstream by:
  - `src/post_query/analysis/top_transcript_list.py`
  - `src/post_query/analysis/top_transcript_data.py`
  - `src/post_query/benchmarking/prompts_benchmark.py`
  - `src/post_query/benchmarking/models_benchmark.py`
  - `src/post_query/exports/quoted_excerpt_labels.py`
  - indirectly by `src/post_query/analysis/main_dataset.py`

### `data/datasets/transcript_detail.feather`
- Purpose: transcript-level Capital IQ metadata
- Written by: `src/pre_query/data_preparation/download_capiq_details.py`
- Immediate upstream:
  - WRDS `ciq.wrds_transcript_detail`
  - optional transcript preferences from `data/datasets/queries.sqlite`
- Used downstream by:
  - `src/pre_query/data_preparation/export_companies.py`
  - `src/pre_query/compustat/get_gvkey.py`
  - `src/post_query/analysis/top_transcript_data.py`
  - `src/post_query/analysis/main_dataset.py`
  - `src/post_query/exports/quoted_excerpt_labels.py`

### `data/datasets/human_ratings.csv`
- Purpose: combined benchmark human labels
- Written by: `src/pre_query/data_preparation/format_human_ratings.py`
- Immediate upstream:
  - `data/raw/human_ratings/joe_scores.csv`
  - `data/raw/human_ratings/acl_scores.csv`
- Used downstream by:
  - `src/post_query/analysis/main_dataset.py`
  - `src/post_query/analysis/summary_stats.py`
  - `src/post_query/benchmarking/prompts_benchmark.py`
  - `src/post_query/benchmarking/models_benchmark.py`

### `data/intermediaries/top_transcripts.csv`
- Purpose: transcript IDs flagged by the main production prompt/model
- Written by: `src/post_query/analysis/top_transcript_list.py`
- Immediate upstream:
  - `data/datasets/queries.sqlite`
- Used downstream by:
  - `src/post_query/analysis/top_transcript_data.py`

### `data/intermediaries/original_score.csv`
- Purpose: original score from the first production-run query for each transcript
- Written by: `src/post_query/analysis/top_transcript_list.py`
- Immediate upstream:
  - `data/datasets/queries.sqlite`
- Used downstream by:
  - `src/post_query/analysis/main_dataset.py`

### `data/datasets/top_transcripts_data.csv`
- Purpose: core transcript-level follow-up score dataset for flagged transcripts
- Written by: `src/post_query/analysis/top_transcript_data.py`
- Immediate upstream:
  - `data/intermediaries/top_transcripts.csv`
  - `data/datasets/queries.sqlite`
  - `data/datasets/transcript_detail.feather`
- Used downstream by:
  - `src/post_query/analysis/main_dataset.py`
  - `src/post_query/analysis/summary_stats_results.py`
  - `src/post_query/analysis/fig_scores_histogram.py`
  - `src/post_query/analysis/fig_scatter_scores.py`
  - `src/post_query/analysis/correlates_others.py`

### `data/datasets/company_year_compustat.feather`
- Purpose: company-year Compustat panel merged across US and Global datasets
- Written by: `src/pre_query/compustat/company_year_dataset.py`
- Immediate upstream:
  - `data/raw/compustat/compustat_us.feather`
  - `data/raw/compustat/compustat_global.feather`
  - `data/intermediaries/gvkey_table.feather`
- Upstream to those:
  - `src/pre_query/compustat/download_compustat_us.py`
  - `src/pre_query/compustat/download_compustat_global.py`
  - `src/pre_query/compustat/get_gvkey.py`
- Used downstream by:
  - `src/post_query/analysis/main_dataset.py`

### `data/datasets/main_analysis_dataset.feather`
- Purpose: main transcript-level analysis dataset used by most paper outputs
- Written by: `src/post_query/analysis/main_dataset.py`
- Immediate upstream:
  - `data/datasets/transcript_detail.feather`
  - `data/datasets/company_year_compustat.feather`
  - `data/datasets/human_ratings.csv`
  - `data/datasets/top_transcripts_data.csv`
  - `data/intermediaries/original_score.csv`
  - `data/datasets/queries.sqlite`
  - `assets/human_audit_final.xlsx`
- Used downstream by:
  - `src/post_query/analysis/summary_stats.py`
  - `src/post_query/analysis/summary_stats_dataset.py`
  - `src/post_query/analysis/summary_stats_results.py`
  - `src/post_query/analysis/fig_scores_histogram.py`
  - `src/post_query/analysis/fig_scatter_scores.py`
  - `src/post_query/analysis/audit_analysis.py`
  - `src/post_query/analysis/correlates_others.py`
  - `src/post_query/analysis/detailed_industry_results.py`

## Displayed assets in the main paper

### Table: `summary_stats_dataset.tex`
- Manuscript location: `manuscript/data.tex`
- Included file: `data/outputs/tables/summary_stats_dataset.tex`
- Written by: `src/post_query/analysis/summary_stats_dataset.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
- Extended chain:
  - `main_analysis_dataset.feather` <- `src/post_query/analysis/main_dataset.py`
  - upstream listed in the backbone section above

### Table: `summary_stats_results.tex`
- Manuscript location: `manuscript/basic_results_stats.tex`
- Included file: `data/outputs/tables/summary_stats_results.tex`
- Written by: `src/post_query/analysis/summary_stats_results.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/top_transcripts_data.csv`

### Figure: `original_score_entire_sample_16x9.pdf`
- Manuscript location: `manuscript/basic_results_stats.tex`
- Included file: `data/outputs/figures/original_score_entire_sample_16x9.pdf`
- Written by: `src/post_query/analysis/fig_scores_histogram.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`

### Figure: `mean_score_validated_samples_16x9.pdf`
- Manuscript location: `manuscript/basic_results_stats.tex`
- Included file: `data/outputs/figures/mean_score_validated_samples_16x9.pdf`
- Written by: `src/post_query/analysis/fig_scores_histogram.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/top_transcripts_data.csv`

### Figure: `scatter_scores_original_vs_mean_16x9.pdf`
- Manuscript location: `manuscript/basic_results_stats.tex`
- Included file: `data/outputs/figures/scatter_scores_original_vs_mean_16x9.pdf`
- Written by: `src/post_query/analysis/fig_scatter_scores.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/top_transcripts_data.csv`

### Table: `human_audit_summary_stats.tex`
- Manuscript location: `manuscript/audit_description.tex`
- Included file: `data/outputs/tables/human_audit_summary_stats.tex`
- Written by: `src/post_query/analysis/audit_analysis.py`
- Immediate upstream:
  - `assets/human_audit_final.xlsx`
  - `data/datasets/main_analysis_dataset.feather`

### Figure: `human_audit_score_histogram_10bins_16x9.pdf`
- Manuscript location: `manuscript/audit_description.tex`
- Included file: `data/outputs/figures/human_audit_score_histogram_10bins_16x9.pdf`
- Written by: `src/post_query/analysis/audit_analysis.py`
- Immediate upstream:
  - `assets/human_audit_final.xlsx`
  - `data/datasets/main_analysis_dataset.feather`

### Table: `human_audit_performance_bins.tex`
- Manuscript location: `manuscript/audit_performance.tex`
- Included file: `data/outputs/tables/human_audit_performance_bins.tex`
- Written by: `src/post_query/analysis/audit_analysis.py`
- Immediate upstream:
  - `assets/human_audit_final.xlsx`
  - `data/datasets/main_analysis_dataset.feather`

### Figure: `gics_sector_tag_rates_llm.pdf`
- Manuscript location: `manuscript/correlates.tex`
- Included file: `data/outputs/figures/gics_sector_tag_rates_llm.pdf`
- Written by: `src/post_query/analysis/correlates_segments.py`
- Immediate upstream:
  - `data/outputs/tables/detailed_industry_results.csv`
  - `data/yaml/correlates_collusive_communication.yaml`
- Extended chain:
  - `detailed_industry_results.csv` <- `src/post_query/analysis/detailed_industry_results.py`
  - immediate upstream of that:
    - `data/datasets/main_analysis_dataset.feather`
    - `data/intermediaries/gics_classifications.feather`
    - `data/intermediaries/naics_classifications.feather`
    - `data/intermediaries/sic_classifications.feather`

### Figure: `high_collusion_sic_tag_rates_llm.pdf`
- Manuscript location: `manuscript/correlates.tex`
- Included file: `data/outputs/figures/high_collusion_sic_tag_rates_llm.pdf`
- Written by: `src/post_query/analysis/correlates_segments.py`
- Immediate upstream:
  - `data/outputs/tables/detailed_industry_results.csv`
  - `data/yaml/correlates_collusive_communication.yaml`

### Figure: `market_value_deciles_llm_16x9.pdf`
- Manuscript location: `manuscript/correlates.tex`
- Included file: `data/outputs/figures/market_value_deciles_llm_16x9.pdf`
- Written by: `src/post_query/analysis/correlates_others.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/top_transcripts_data.csv`
  - `assets/human_audit_final.xlsx`

### Figure: `year_tag_rates_llm_16x9.pdf`
- Manuscript location: `manuscript/correlates.tex`
- Included file: `data/outputs/figures/year_tag_rates_llm_16x9.pdf`
- Written by: `src/post_query/analysis/correlates_others.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/top_transcripts_data.csv`
  - `assets/human_audit_final.xlsx`

### Figure: `ask_by_airline_2011_2016_16x9.pdf`
- Manuscript location: `manuscript/case.tex`
- Included file: `data/outputs/figures/ask_by_airline_2011_2016_16x9.pdf`
- Written by: `src/post_query/analysis/case_airlines_capacities_analysis.py`
- Immediate upstream:
  - `data/datasets/ask_airline_year.csv`
- Extended chain:
  - `ask_airline_year.csv` <- `src/post_query/analysis/case_airlines_capacities_dataset.py`
  - immediate upstream of that:
    - `data/raw/anac/2011.csv`
    - `data/raw/anac/2012.csv`
    - `data/raw/anac/2013.csv`
    - `data/raw/anac/2014.csv`
    - `data/raw/anac/2015.csv`
    - `data/raw/anac/2016.csv`

### Figure: `analysis_flowchart.tex`
- Manuscript location: `manuscript/methods.tex` via `manuscript/floats/analysis_flowchart.tex`
- Status: manuscript-local TeX figure, not produced by a Python script
- Dependencies:
  - uses `\data{...}` constants from the `summary_stats` family

### Section: synthesis of collusive content
- Manuscript location: `manuscript/audit_types.tex`
- Status: manuscript-local TeX content, maintained directly in TeX
- Dependencies:
  - `audit` constants from `data/constants/audit/...`
  - `quoted_excerpt_labels` constants from `data/constants/quoted_excerpt_labels/audit_types/...`

## Displayed assets in the online appendix

### Table: `prompt_benchmark_first_run.tex`
- Appendix location: `manuscript/si_prompts_llms_comparisons.tex`
- Included file: `data/outputs/tables/prompt_benchmark_first_run.tex`
- Written by: `src/post_query/benchmarking/prompts_benchmark.py`
- Immediate upstream:
  - `data/datasets/queries.sqlite`
  - `data/datasets/human_ratings.csv`
- Notes:
  - the same script also writes `data/benchmarking/prompt_transcript_scores.csv`
  - and `data/benchmarking/prompt_metrics.csv`

### Table: `prompt_benchmark_avg11.tex`
- Appendix location: `manuscript/si_prompts_llms_comparisons.tex`
- Included file: `data/outputs/tables/prompt_benchmark_avg11.tex`
- Written by: `src/post_query/benchmarking/prompts_benchmark.py`
- Immediate upstream:
  - `data/datasets/queries.sqlite`
  - `data/datasets/human_ratings.csv`
- Notes:
  - the same script also writes `data/benchmarking/prompt_transcript_scores_avg11.csv`
  - and `data/benchmarking/prompt_metrics_avg11.csv`

### Table: `model_benchmark_first_run.tex`
- Appendix location: `manuscript/si_prompts_llms_comparisons.tex`
- Included file: `data/outputs/tables/model_benchmark_first_run.tex`
- Written by: `src/post_query/benchmarking/models_benchmark.py`
- Immediate upstream:
  - `data/datasets/queries.sqlite`
  - `data/datasets/human_ratings.csv`
  - `assets/llm_config.json`
- Notes:
  - the same script also writes `data/benchmarking/model_transcript_scores.csv`
  - and `data/benchmarking/model_metrics.csv`

### Table: companies with collusive content
- Appendix location: `manuscript/si_companies_human_audit.tex`
- Status: manuscript-local longtable, maintained directly in TeX
- No producing script found in this repo

### Section: categorization of collusive content
- Appendix location: `manuscript/si_categorization_collusive_content.tex`
- Status: manuscript-local appendix content, maintained directly in TeX
- No producing script found in this repo

### Section: content analysis of false positives
- Appendix location: `manuscript/si_content_analysis_false_positives.tex`
- Content comes from: `manuscript/audit_errors.tex`
- Dependencies:
  - `audit` constants from `data/constants/audit/...`
  - `quoted_excerpt_labels` constants from `data/constants/quoted_excerpt_labels/...`
- See the constant family sections below

## Constants and their lineage

All current manuscript and appendix constants are inserted through:
- `\data{...}` in TeX
- which resolves to `data/constants/...`
- which is generated by `src/post_query/exports/populate_constants.py`
- from YAML files in `data/yaml/`

### `summary_stats` constants
- YAML source: `data/yaml/summary_stats.yaml`
- YAML written by: `src/post_query/analysis/summary_stats.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/human_ratings.csv`
  - `data/raw/human_ratings/acl_scores.csv`
  - `data/datasets/top_transcripts_data.csv`
  - `assets/human_audit_final.xlsx`

Constants currently used in the manuscript:
- `summary_stats/dataset_overview/first_date`
- `summary_stats/dataset_overview/last_date`
- `summary_stats/dataset_overview/unique_companies_int`
- `summary_stats/dataset_overview/total_transcripts_int`
- `summary_stats/audio_characteristics/mean_length_description`
- `summary_stats/audio_characteristics/total_audio_years_int`
- `summary_stats/tagging_performance/aryal_total_transcripts_int`
- `summary_stats/tagging_performance/aryal_collusive_rate_pct_percentage0`
- `summary_stats/tagging_performance/aryal_transcripts_in_ciq_int`
- `summary_stats/tagging_performance/benchmark_sample_count_int`
- `summary_stats/tagging_performance/llm_tagged_count_int`
- `summary_stats/tagging_performance/llm_validation_tagged_int`
- `summary_stats/tagging_performance/human_audit_sample_count_int`
- `summary_stats/tagging_performance/llm_tag_rate_pct_percentage1`
- `summary_stats/tagging_performance/original_score_mean_float1`
- `summary_stats/tagging_performance/llm_validation_rate_pct_percentage0`
- `summary_stats/tagging_performance/human_benchmark_tagged_count_int`
- `summary_stats/tagging_performance/benchmark_collusive_flagged_count_int`
- `summary_stats/tagging_performance/benchmark_collusive_flagged_pct_percentage0`
- `summary_stats/tagging_performance/benchmark_collusive_validated_count_int`
- `summary_stats/tagging_performance/benchmark_collusive_validated_pct_percentage0`
- `summary_stats/tagging_performance/benchmark_not_collusive_count_int`
- `summary_stats/tagging_performance/benchmark_not_collusive_flagged_count_int`
- `summary_stats/tagging_performance/benchmark_not_collusive_flagged_pct_percentage1`
- `summary_stats/tagging_performance/benchmark_not_collusive_validated_count_int`
- `summary_stats/tagging_performance/benchmark_not_collusive_validated_pct_percentage1`
- `summary_stats/tagging_performance/benchmark_validation_odds_ratio_int`

### `audit` constants
- YAML source: `data/yaml/audit.yaml`
- YAML written by: `src/post_query/analysis/audit_analysis.py`
- Immediate upstream:
  - `assets/human_audit_final.xlsx`
  - `data/datasets/main_analysis_dataset.feather`

Constants currently used in the manuscript and appendix:
- `audit/sample_count_int`
- `audit/score_min_float2`
- `audit/score_max_float2`
- `audit/true_positive_count_int`
- `audit/false_positive_count_int`
- `audit/true_positive_rate_pct_percentage1`
- `audit/top_bin/count_int`
- `audit/top_bin/true_positive_rate_pct_percentage1`
- `audit/bottom_bin/count_int`
- `audit/bottom_bin/true_positive_rate_pct_percentage1`

### `correlates_collusive_communication` constants
- YAML source: `data/yaml/correlates_collusive_communication.yaml`
- YAML written by: `src/post_query/analysis/correlates_others.py`
- Immediate upstream:
  - `data/datasets/main_analysis_dataset.feather`
  - `data/datasets/top_transcripts_data.csv`
  - `assets/human_audit_final.xlsx`

Constants currently used in the manuscript:
- `correlates_collusive_communication/llm_tagged_collusive_pct_percentage1`
- `correlates_collusive_communication/sector_healthcare_rate_percentage1`
- `correlates_collusive_communication/sector_materials_rate_percentage1`
- `correlates_collusive_communication/mkvalt_valid_observations_int`
- `correlates_collusive_communication/year_valid_observations_int`

### `quoted_excerpt_labels` constants
- YAML source: `data/yaml/quoted_excerpt_labels.yaml`
- YAML written by: `src/post_query/exports/quoted_excerpt_labels.py`
- Immediate upstream:
  - `data/datasets/queries.sqlite`
  - `data/datasets/transcript_detail.feather`
  - `manuscript/audit_types.tex`
  - `manuscript/audit_errors.tex`
- Mechanism:
  - the script parses query IDs already referenced in `audit_types.tex` and `audit_errors.tex`
  - looks up `query_id -> transcriptid` in `queries.sqlite`
  - looks up company/event/date in `transcript_detail.feather`
  - writes label strings into YAML
  - `populate_constants.py` turns those labels into `data/constants/quoted_excerpt_labels/...`

Constants currently used in the manuscript and appendix:

`audit_types` labels:
- `quoted_excerpt_labels/audit_types/q508027`
- `quoted_excerpt_labels/audit_types/q597966`
- `quoted_excerpt_labels/audit_types/q419393`
- `quoted_excerpt_labels/audit_types/q185218`
- `quoted_excerpt_labels/audit_types/q260640`
- `quoted_excerpt_labels/audit_types/q389910`
- `quoted_excerpt_labels/audit_types/q419394`
- `quoted_excerpt_labels/audit_types/q597969`
- `quoted_excerpt_labels/audit_types/q617313`
- `quoted_excerpt_labels/audit_types/q381391`
- `quoted_excerpt_labels/audit_types/q261028`
- `quoted_excerpt_labels/audit_types/q348864`
- `quoted_excerpt_labels/audit_types/q569063`
- `quoted_excerpt_labels/audit_types/q406151`
- `quoted_excerpt_labels/audit_types/q325885`
- `quoted_excerpt_labels/audit_types/q228511`
- `quoted_excerpt_labels/audit_types/q494779`
- `quoted_excerpt_labels/audit_types/q260628`
- `quoted_excerpt_labels/audit_types/q199854`
- `quoted_excerpt_labels/audit_types/q519067`
- `quoted_excerpt_labels/audit_types/q508184`
- `quoted_excerpt_labels/audit_types/q381486`
- `quoted_excerpt_labels/audit_types/q327069`
- `quoted_excerpt_labels/audit_types/q396666`
- `quoted_excerpt_labels/audit_types/q396668`
- `quoted_excerpt_labels/audit_types/q196851`
- `quoted_excerpt_labels/audit_types/q445959`
- `quoted_excerpt_labels/audit_types/q558080`
- `quoted_excerpt_labels/audit_types/q309604`
- `quoted_excerpt_labels/audit_types/q250287`
- `quoted_excerpt_labels/audit_types/q408614`
- `quoted_excerpt_labels/audit_types/q215003`
- `quoted_excerpt_labels/audit_types/q375388`
- `quoted_excerpt_labels/audit_types/q305524`
- `quoted_excerpt_labels/audit_types/q309638`
- `quoted_excerpt_labels/audit_types/q223177`
- `quoted_excerpt_labels/audit_types/q526439`
- `quoted_excerpt_labels/audit_types/q631460`
- `quoted_excerpt_labels/audit_types/q408622`
- `quoted_excerpt_labels/audit_types/q325064`
- `quoted_excerpt_labels/audit_types/q548932`

`audit_errors` labels:
- `quoted_excerpt_labels/audit_errors/q298141`
- `quoted_excerpt_labels/audit_errors/q445982`
- `quoted_excerpt_labels/audit_errors/q458895`
- `quoted_excerpt_labels/audit_errors/q198201`
- `quoted_excerpt_labels/audit_errors/q252936`
- `quoted_excerpt_labels/audit_errors/q452530`
- `quoted_excerpt_labels/audit_errors/q654876`
- `quoted_excerpt_labels/audit_errors/q638665`
- `quoted_excerpt_labels/audit_errors/q422806`
- `quoted_excerpt_labels/audit_errors/q320434`
- `quoted_excerpt_labels/audit_errors/q215021`
- `quoted_excerpt_labels/audit_errors/q375619`
- `quoted_excerpt_labels/audit_errors/q257163`
- `quoted_excerpt_labels/audit_errors/q662160`
- `quoted_excerpt_labels/audit_errors/q631021`
- `quoted_excerpt_labels/audit_errors/q190678`
- `quoted_excerpt_labels/audit_errors/q604617`
- `quoted_excerpt_labels/audit_errors/q643679`
- `quoted_excerpt_labels/audit_errors/q320228`
- `quoted_excerpt_labels/audit_errors/q550676`
- `quoted_excerpt_labels/audit_errors/q401404`
- `quoted_excerpt_labels/audit_errors/q651762`
- `quoted_excerpt_labels/audit_errors/q593253`
- `quoted_excerpt_labels/audit_errors/q481706`
- `quoted_excerpt_labels/audit_errors/q327107`
- `quoted_excerpt_labels/audit_errors/q321900`
- `quoted_excerpt_labels/audit_errors/q414209`

## Assets that are manuscript-local rather than script-generated

These items are part of the current paper/appendix but are maintained directly in TeX, not produced by a script in this repo.

- `manuscript/floats/analysis_flowchart.tex`
- `manuscript/si_companies_human_audit.tex`
- `manuscript/si_categorization_collusive_content.tex`
- the prose and quoted passages in:
  - `manuscript/audit_types.tex`
  - `manuscript/audit_errors.tex`
  - `manuscript/case.tex`

The two audit appendix prose files do, however, depend on generated `quoted_excerpt_labels` constants as documented above.
