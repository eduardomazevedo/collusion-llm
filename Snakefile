# Snakefile for Collusion LLM project
# This workflow manages the data processing pipeline

rule all:
    input:
        "data/raw/compustat/compustat_us.feather",
        "data/raw/compustat/compustat_global.feather",
        "data/intermediaries/gvkey_table.feather",
        "data/intermediaries/gvkey_list.txt",
        "data/datasets/company_year_compustat.feather",
        "data/intermediaries/gics_classifications.feather",
        "data/intermediaries/naics_classifications.feather",
        "data/intermediaries/sic_classifications.feather",
        "data/datasets/main_analysis_dataset.feather",
        "data/datasets/top_transcripts_data.csv",
        "data/outputs/top_transcript_data_for_joe.csv",
        "data/yaml/summary_stats.yaml",
        "data/yaml/correlates_collusive_communication.yaml",
        "data/yaml/benchmarking.yaml",
        "data/outputs/tables/detailed_industry_results.csv",
        # LLM flag outputs
        "data/outputs/tables/market_value_deciles_llm.csv",
        "data/outputs/tables/segment_tag_rates_llm.csv", 
        "data/outputs/tables/year_tag_rates_llm.csv",
        "data/outputs/figures/market_value_deciles_llm_1x1.png",
        "data/outputs/figures/segment_tag_rates_llm.png",
        "data/outputs/figures/year_tag_rates_llm_1x1.png",
        # LLM validation flag outputs (market value and year only, no sectors)
        "data/outputs/tables/market_value_deciles_llm_validation.csv",
        "data/outputs/tables/year_tag_rates_llm_validation.csv",
        "data/outputs/figures/market_value_deciles_llm_validation_1x1.png",
        "data/outputs/figures/year_tag_rates_llm_validation_1x1.png",
        # Human audit flag outputs (market value and year only, no sectors)
        "data/outputs/tables/market_value_deciles_human_audit.csv",
        "data/outputs/tables/year_tag_rates_human_audit.csv",
        "data/outputs/figures/market_value_deciles_human_audit_1x1.png",
        "data/outputs/figures/year_tag_rates_human_audit_1x1.png",
        # Benchmarking outputs
        "data/outputs/tables/benchmarking_combined.csv",
        "data/outputs/tables/summary_stats_dataset.csv",
        "data/outputs/tables/summary_stats_results.csv",
        # Score distribution figures
        "data/outputs/figures/original_score_entire_sample_16x9.pdf",
        "data/outputs/figures/mean_score_validated_samples_16x9.pdf",
        "data/outputs/figures/scatter_scores_original_vs_mean_16x9.pdf",
        "data/constants/.populated"

rule download_compustat_us:
    """
    Download US Compustat data from WRDS database.
    Creates feather file with US company financial data.
    """
    output:
        "data/raw/compustat/compustat_us.feather"
    resources:
        wrds=1
    shell:
        "PYTHONPATH={workflow.basedir}:$PYTHONPATH python src/pre_query/compustat/download_compustat_us.py"

rule download_compustat_global:
    """
    Download Global Compustat data from WRDS database.
    Creates feather file with global company financial data.
    """
    output:
        "data/raw/compustat/compustat_global.feather"
    resources:
        wrds=1
    shell:
        "PYTHONPATH={workflow.basedir}:$PYTHONPATH python src/pre_query/compustat/download_compustat_global.py"

rule get_gvkey:
    """
    Get gvkeys for company IDs from transcript_detail.feather using WRDS database.
    Creates mapping table and list of gvkeys for further processing.
    """
    input:
        "data/datasets/transcript_detail.feather"
    output:
        table="data/intermediaries/gvkey_table.feather",
        list_file="data/intermediaries/gvkey_list.txt"
    resources:
        wrds=1
    shell:
        "PYTHONPATH={workflow.basedir}:$PYTHONPATH python src/pre_query/compustat/get_gvkey.py"

rule company_year_dataset:
    """
    Create combined company-year dataset from US and Global Compustat data.
    Merges both datasets, adds location info, and maps gvkeys to company IDs.
    """
    input:
        us_feather="data/raw/compustat/compustat_us.feather",
        global_feather="data/raw/compustat/compustat_global.feather",
        gvkey_table="data/intermediaries/gvkey_table.feather"
    output:
        "data/datasets/company_year_compustat.feather"
    shell:
        "PYTHONPATH={workflow.basedir}:$PYTHONPATH python src/pre_query/compustat/company_year_dataset.py"

rule download_industry_classifications:
    """
    Download industry classification titles from WRDS database.
    Downloads complete mappings of GICS, NAICS, and SIC codes to their descriptive titles.
    Creates feather files for each classification system in data/intermediaries/.
    """
    output:
        gics="data/intermediaries/gics_classifications.feather",
        naics="data/intermediaries/naics_classifications.feather",
        sic="data/intermediaries/sic_classifications.feather"
    resources:
        wrds=1
    shell:
        "python src/post_query/analysis/download_industry_classifications.py"

rule create_top_transcripts:
    """
    Extract top transcript list from queries database.
    Queries SimpleCapacityV8.1.1 prompts, keeps earliest query per transcript,
    filters by LLM_SCORE_THRESHOLD, and saves transcriptids to CSV.
    Also saves original_score.csv with scores for all transcripts.
    """
    input:
        "data/datasets/queries.sqlite"
    output:
        top_transcripts="data/intermediaries/top_transcripts.csv",
        original_score="data/intermediaries/original_score.csv"
    shell:
        "python src/post_query/analysis/top_transcript_list.py"

rule main_dataset:
    """
    Create the main analysis dataset at the transcript level.
    Combines transcript details, human ratings, LLM flags, and Compustat data.
    Creates binary flags for human and LLM collusion detection and for whether it is in human benchmark sample.
    Includes original_score from the initial LLM run for all transcripts.
    """
    input:
        transcript_detail="data/datasets/transcript_detail.feather",
        compustat="data/datasets/company_year_compustat.feather",
        human_ratings="data/datasets/human_ratings.csv",
        top_transcripts_data="data/datasets/top_transcripts_data.csv",
        original_score="data/intermediaries/original_score.csv",
        queries_db="data/datasets/queries.sqlite"
    output:
        "data/datasets/main_analysis_dataset.feather"
    shell:
        "python src/post_query/analysis/main_dataset.py"

rule top_transcript_data:
    """
    Create top_transcript_data_for_joe.csv with aggregated query data and follow-up analysis.
    Also creates top_transcripts_data.csv core dataset with essential score variables only.
    Aggregates SimpleCapacityV8.1.1 prompt results by transcriptid with follow-up scores.
    Includes company names, dates, and excerpt data for detailed analysis in full version.
    """
    input:
        top_transcripts="data/intermediaries/top_transcripts.csv",
        queries_db="data/datasets/queries.sqlite",
        transcript_detail="data/datasets/transcript_detail.feather"
    output:
        full="data/outputs/top_transcript_data_for_joe.csv",
        core="data/datasets/top_transcripts_data.csv"
    shell:
        "python src/post_query/analysis/top_transcript_data.py"

rule summary_stats:
    """
    Generate comprehensive summary statistics for the main analysis dataset.
    Creates organized YAML statistics covering dataset overview,
    temporal coverage, audio characteristics, company characteristics, and tagging performance.
    """
    input:
        "data/datasets/main_analysis_dataset.feather"
    output:
        yaml="data/yaml/summary_stats.yaml"
    shell:
        "python src/post_query/analysis/summary_stats.py"

rule detailed_industry_results:
    """
    Generate detailed industry-level breakdown of LLM flagging results.
    Creates comprehensive breakdown by GICS, NAICS, and SIC at all hierarchy levels.
    Outputs CSV table with classification system, level, code, name, and flagging statistics.
    """
    input:
        dataset="data/datasets/main_analysis_dataset.feather",
        gics="data/intermediaries/gics_classifications.feather",
        naics="data/intermediaries/naics_classifications.feather",
        sic="data/intermediaries/sic_classifications.feather"
    output:
        "data/outputs/tables/detailed_industry_results.csv"
    shell:
        "python src/post_query/analysis/detailed_industry_results.py"

rule correlates_segments:
    """
    Analyze LLM collusion tagging patterns by sector (GICS) and high collusion segments.
    Uses detailed_industry_results.csv to create combined tables and figures with both groups.
    Outputs CSV/LaTeX tables and PNG/PDF figures in 1:1 and 16:9 formats.
    Note: Requires detailed_industry_results and correlates_others to run first.
    """
    input:
        "data/outputs/tables/detailed_industry_results.csv",
        yaml="data/yaml/correlates_collusive_communication.yaml"
    output:
        # Combined LLM flag outputs for sectors and segments
        # Note: Figure uses custom format (10x9), not standard 1x1/16x9
        segment_table_llm="data/outputs/tables/segment_tag_rates_llm.csv",
        segment_fig_llm="data/outputs/figures/segment_tag_rates_llm.png"
    shell:
        "python src/post_query/analysis/correlates_segments.py"

rule correlates_others:
    """
    Analyze LLM collusion tagging patterns by market value, year, and industry samples across three flag variables.
    Creates summary statistics, tables by market value/year, industry sample analyses, and score histograms.
    Outputs YAML summary stats, CSV/LaTeX tables, and PNG/PDF figures in 1:1 and 16:9 formats.
    """
    input:
        "data/datasets/main_analysis_dataset.feather"
    output:
        yaml="data/yaml/correlates_collusive_communication.yaml",
        # LLM flag outputs
        mv_table_llm="data/outputs/tables/market_value_deciles_llm.csv",
        year_table_llm="data/outputs/tables/year_tag_rates_llm.csv",
        mv_fig_llm="data/outputs/figures/market_value_deciles_llm_1x1.png",
        year_fig_llm="data/outputs/figures/year_tag_rates_llm_1x1.png",
        # LLM validation flag outputs
        mv_table_validation="data/outputs/tables/market_value_deciles_llm_validation.csv",
        year_table_validation="data/outputs/tables/year_tag_rates_llm_validation.csv",
        mv_fig_validation="data/outputs/figures/market_value_deciles_llm_validation_1x1.png",
        year_fig_validation="data/outputs/figures/year_tag_rates_llm_validation_1x1.png",
        # Human audit flag outputs
        mv_table_audit="data/outputs/tables/market_value_deciles_human_audit.csv",
        year_table_audit="data/outputs/tables/year_tag_rates_human_audit.csv",
        mv_fig_audit="data/outputs/figures/market_value_deciles_human_audit_1x1.png",
        year_fig_audit="data/outputs/figures/year_tag_rates_human_audit_1x1.png"
    shell:
        "python src/post_query/analysis/correlates_others.py"

rule benchmarking_analysis:
    """
    Evaluate LLM performance on human-rated benchmark datasets.
    Compares different approaches (single query, repeated queries, follow-up validation)
    and different models on Joe's ratings, ACL's ratings, and human audit data.
    Outputs combined table with two panels and YAML statistics.
    """
    input:
        "data/datasets/queries.sqlite",
        "data/datasets/human_ratings.csv",
        "assets/human_audit_top_transcripts.csv"
    output:
        combined_csv="data/outputs/tables/benchmarking_combined.csv",
        combined_tex="data/outputs/tables/benchmarking_combined.tex",
        approach_csv="data/outputs/tables/approach_comparison.csv",
        audit_csv="data/outputs/tables/human_audit_validation.csv",
        yaml="data/yaml/benchmarking.yaml"
    shell:
        "python src/post_query/analysis/benchmarking_analysis.py"

rule summary_stats_dataset:
    """
    Generate publication-ready summary statistics table for dataset characteristics.
    Reports mean, median, min, max, N for continuous variables (market value, employees, audio length, transcript year).
    Outputs CSV, LaTeX, and description files for manuscript use.
    """
    input:
        "data/datasets/main_analysis_dataset.feather"
    output:
        csv="data/outputs/tables/summary_stats_dataset.csv",
        tex="data/outputs/tables/summary_stats_dataset.tex",
        txt="data/outputs/tables/summary_stats_dataset.txt"
    shell:
        "python src/post_query/analysis/summary_stats_dataset.py"

rule summary_stats_results:
    """
    Generate publication-ready summary statistics table for classification results.
    Reports N, count=TRUE, percent=TRUE for boolean classification flags (LLM flags, validation flags, human audit flags, benchmark flags).
    Outputs CSV, LaTeX, and description files for manuscript use.
    """
    input:
        "data/datasets/main_analysis_dataset.feather"
    output:
        csv="data/outputs/tables/summary_stats_results.csv",
        tex="data/outputs/tables/summary_stats_results.tex",
        txt="data/outputs/tables/summary_stats_results.txt"
    shell:
        "python src/post_query/analysis/summary_stats_results.py"

rule score_histogram_figures:
    """
    Generate histogram figures for LLM score distributions.
    Creates histograms of original scores for entire sample and mean scores for validated samples.
    Outputs both 1x1 and 16x9 formats in PNG and PDF.
    """
    input:
        "data/datasets/main_analysis_dataset.feather",
        "data/datasets/top_transcripts_data.csv"
    output:
        original_16x9="data/outputs/figures/original_score_entire_sample_16x9.pdf",
        mean_16x9="data/outputs/figures/mean_score_validated_samples_16x9.pdf"
    shell:
        "PYTHONPATH={workflow.basedir}:$PYTHONPATH python src/post_query/analysis/fig_scores_histogram.py"

rule scatter_scores_figure:
    """
    Generate scatter plot comparing original LLM scores to mean scores from 11 queries.
    Outputs both 1x1 and 16x9 formats in PNG and PDF.
    """
    input:
        "data/datasets/main_analysis_dataset.feather",
        "data/datasets/top_transcripts_data.csv"
    output:
        scatter_16x9="data/outputs/figures/scatter_scores_original_vs_mean_16x9.pdf"
    shell:
        "PYTHONPATH={workflow.basedir}:$PYTHONPATH python src/post_query/analysis/fig_scatter_scores.py"

rule populate_constants:
    """
    Convert YAML statistics files to LaTeX-friendly constant files.
    Creates multiple format versions (int, float, percentage, etc.) for use in manuscripts.
    """
    input:
        "data/yaml/summary_stats.yaml",
        "data/yaml/correlates_collusive_communication.yaml",
        "data/yaml/benchmarking.yaml"
    output:
        "data/constants/.populated"
    shell:
        "python src/post_query/exports/populate_constants.py && touch data/constants/.populated"
