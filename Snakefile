# Snakefile for Collusion LLM project
# This workflow manages the data processing pipeline

rule all:
    input:
        "data/cache/raw/compustat/compustat-us.csv",
        "data/cache/raw/compustat/compustat-global.csv",
        "data/cache/raw/compustat/readme.md",
        "data/datasets/gvkey_table.feather",
        "data/intermediaries/gvkey_list.txt",
        "data/datasets/company-year-compustat.parquet",
        "data/datasets/main-analysis-dataset.feather",
        "data/outputs/analysis/top_transcripts_data.csv",
        "data/outputs/yaml/transcript-stats.yaml",
        "data/outputs/constants/.populated"

rule download_compustat:
    """
    Download Compustat data files from remote storage using rclone.
    Downloads US and global Compustat data in CSV format plus readme.
    """
    output:
        us_csv="data/cache/raw/compustat/compustat-us.csv",
        global_csv="data/cache/raw/compustat/compustat-global.csv",
        readme="data/cache/raw/compustat/readme.md"
    shell:
        "bash src/pre_query/data_preparation/download_compustat.sh"

rule get_gvkey:
    """
    Get gvkeys for company IDs from transcript-detail.feather using WRDS database.
    Creates mapping table and list of gvkeys for further processing.
    """
    input:
        "data/datasets/transcript-detail.feather"
    output:
        table="data/datasets/gvkey_table.feather",
        list_file="data/intermediaries/gvkey_list.txt"
    shell:
        "python src/pre_query/dataset_creation/get_gvkey.py"

rule company_year_dataset:
    """
    Create combined company-year dataset from US and Global Compustat data.
    Merges both datasets, adds location info, and maps gvkeys to company IDs.
    """
    input:
        us_csv="data/cache/raw/compustat/compustat-us.csv",
        global_csv="data/cache/raw/compustat/compustat-global.csv",
        gvkey_table="data/datasets/gvkey_table.feather"
    output:
        "data/datasets/company-year-compustat.parquet"
    shell:
        "python src/pre_query/dataset_creation/company-year-dataset.py"

rule main_dataset:
    """
    Create the main analysis dataset at the transcript level.
    Combines transcript details, human ratings, LLM flags, and Compustat data.
    Creates binary flags for human and LLM collusion detection.
    """
    input:
        transcript_detail="data/datasets/transcript-detail.feather",
        compustat="data/datasets/company-year-compustat.parquet",
        human_ratings="data/datasets/human_ratings/human-ratings.csv",
        top_transcripts="data/outputs/analysis/top_transcripts.csv",
        queries_db="data/datasets/queries.sqlite"
    output:
        "data/datasets/main-analysis-dataset.feather"
    shell:
        "python src/pre_query/dataset_creation/main_dataset.py"

rule top_transcript_data:
    """
    Create top_transcripts_data.csv with aggregated query data and follow-up analysis.
    Aggregates SimpleCapacityV8.1.1 prompt results by transcript_id with follow-up scores.
    Includes company names, dates, and excerpt data for detailed analysis.
    """
    input:
        top_transcripts="data/outputs/analysis/top_transcripts.csv",
        queries_db="data/datasets/queries.sqlite",
        transcript_detail="data/datasets/transcript-detail.feather"
    output:
        "data/outputs/analysis/top_transcripts_data.csv"
    shell:
        "python src/post_query/analysis/top_transcript_data.py"

rule transcript_data_stats:
    """
    Generate summary statistics for transcript data.
    Analyzes transcript details and creates YAML output with key metrics.
    """
    input:
        transcript_detail="data/datasets/transcript-detail.feather",
        queries_db="data/datasets/queries.sqlite"
    output:
        "data/outputs/yaml/transcript-stats.yaml"
    shell:
        "python src/post_query/analysis/transcript_data_stats.py"

rule populate_constants:
    """
    Convert YAML statistics files to LaTeX-friendly constant files.
    Creates multiple format versions (int, float, percentage, etc.) for use in manuscripts.
    """
    input:
        "data/outputs/yaml/transcript-stats.yaml"
    output:
        "data/outputs/constants/.populated"
    shell:
        "python src/post_query/exports/populate_constants.py && touch data/outputs/constants/.populated"
