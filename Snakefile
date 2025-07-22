# Snakefile for Collusion LLM project
# This workflow manages the data processing pipeline

rule all:
    input:
        "data/raw/compustat/compustat_us.csv",
        "data/raw/compustat/compustat_global.csv",
        "data/raw/compustat/readme.md",
        "data/intermediaries/gvkey_table.feather",
        "data/intermediaries/gvkey_list.txt",
        "data/datasets/company_year_compustat.parquet",
        "data/datasets/main_analysis_dataset.feather",
        "data/outputs/top_transcripts_data.csv",
        "data/yaml/transcript_stats.yaml",
        "data/constants/.populated"

rule download_compustat:
    """
    Download Compustat data files from remote storage using rclone.
    Downloads US and global Compustat data in CSV format plus readme.
    """
    output:
        us_csv="data/raw/compustat/compustat_us.csv",
        global_csv="data/raw/compustat/compustat_global.csv",
        readme="data/raw/compustat/readme.md"
    shell:
        "bash src/pre_query/compustat/download_compustat.sh"

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
    shell:
        "python src/pre_query/compustat/get_gvkey.py"

rule company_year_dataset:
    """
    Create combined company-year dataset from US and Global Compustat data.
    Merges both datasets, adds location info, and maps gvkeys to company IDs.
    """
    input:
        us_csv="data/raw/compustat/compustat_us.csv",
        global_csv="data/raw/compustat/compustat_global.csv",
        gvkey_table="data/intermediaries/gvkey_table.feather"
    output:
        "data/datasets/company_year_compustat.parquet"
    shell:
        "python src/pre_query/compustat/company_year_dataset.py"

rule create_top_transcripts:
    """
    Extract top transcript list from queries database.
    Queries SimpleCapacityV8.1.1 prompts, keeps earliest query per transcript,
    filters by LLM_SCORE_THRESHOLD, and saves transcriptids to CSV.
    """
    input:
        "data/datasets/queries.sqlite"
    output:
        "data/intermediaries/top_transcripts.csv"
    shell:
        "python src/post_query/analysis/top_transcript_list.py"

rule main_dataset:
    """
    Create the main analysis dataset at the transcript level.
    Combines transcript details, human ratings, LLM flags, and Compustat data.
    Creates binary flags for human and LLM collusion detection.
    """
    input:
        transcript_detail="data/datasets/transcript_detail.feather",
        compustat="data/datasets/company_year_compustat.parquet",
        human_ratings="data/datasets/human_ratings.csv",
        top_transcripts="data/intermediaries/top_transcripts.csv",
        queries_db="data/datasets/queries.sqlite"
    output:
        "data/datasets/main_analysis_dataset.feather"
    shell:
        "python src/post_query/analysis/main_dataset.py"

rule top_transcript_data:
    """
    Create top_transcripts_data.csv with aggregated query data and follow-up analysis.
    Aggregates SimpleCapacityV8.1.1 prompt results by transcriptid with follow-up scores.
    Includes company names, dates, and excerpt data for detailed analysis.
    """
    input:
        top_transcripts="data/intermediaries/top_transcripts.csv",
        queries_db="data/datasets/queries.sqlite",
        transcript_detail="data/datasets/transcript_detail.feather"
    output:
        "data/outputs/top_transcripts_data.csv"
    shell:
        "python src/post_query/analysis/top_transcript_data.py"

rule transcript_data_stats:
    """
    Generate summary statistics for transcript data.
    Analyzes transcript details and creates YAML output with key metrics.
    """
    input:
        transcript_detail="data/datasets/transcript_detail.feather",
        queries_db="data/datasets/queries.sqlite"
    output:
        "data/yaml/transcript_stats.yaml"
    shell:
        "python src/post_query/analysis/transcript_data_stats.py"

rule populate_constants:
    """
    Convert YAML statistics files to LaTeX-friendly constant files.
    Creates multiple format versions (int, float, percentage, etc.) for use in manuscripts.
    """
    input:
        "data/yaml/transcript_stats.yaml"
    output:
        "data/constants/.populated"
    shell:
        "python src/post_query/exports/populate_constants.py && touch data/constants/.populated"
