# Snakefile for Collusion LLM project
# This workflow manages the data processing pipeline

rule all:
    input:
        "data/raw/compustat/compustat-us.csv",
        "data/raw/compustat/compustat-global.csv",
        "data/raw/compustat/readme.md",
        "data/gvkey_table.feather",
        "data/gvkey_list.txt",
        "data/company-year-compustat.parquet",
        "output/yaml/transcript-stats.yaml",
        "output/constants/.populated"

rule download_compustat:
    """
    Download Compustat data files from remote storage using rclone.
    Downloads US and global Compustat data in CSV format plus readme.
    """
    output:
        us_csv="data/raw/compustat/compustat-us.csv",
        global_csv="data/raw/compustat/compustat-global.csv",
        readme="data/raw/compustat/readme.md"
    shell:
        "bash src/bash/download_compustat.sh"

rule get_gvkey:
    """
    Get gvkeys for company IDs from transcript-detail.feather using WRDS database.
    Creates mapping table and list of gvkeys for further processing.
    """
    input:
        "data/transcript-detail.feather"
    output:
        table="data/gvkey_table.feather",
        list_file="data/gvkey_list.txt"
    shell:
        "python src/py/make/get_gvkey.py"

rule company_year_dataset:
    """
    Create combined company-year dataset from US and Global Compustat data.
    Merges both datasets, adds location info, and maps gvkeys to company IDs.
    """
    input:
        us_csv="data/raw/compustat/compustat-us.csv",
        global_csv="data/raw/compustat/compustat-global.csv",
        gvkey_table="data/gvkey_table.feather"
    output:
        "data/company-year-compustat.parquet"
    shell:
        "python src/py/make/company-year-dataset.py"

rule transcript_data_stats:
    """
    Generate summary statistics for transcript data.
    Analyzes transcript details and creates YAML output with key metrics.
    """
    input:
        transcript_detail="data/transcript-detail.feather",
        queries_db="data/queries.sqlite"
    output:
        "output/yaml/transcript-stats.yaml"
    shell:
        "python src/py/transcript_data_stats.py"

rule populate_constants:
    """
    Convert YAML statistics files to LaTeX-friendly constant files.
    Creates multiple format versions (int, float, percentage, etc.) for use in manuscripts.
    """
    input:
        "output/yaml/transcript-stats.yaml"
    output:
        "output/constants/.populated"
    shell:
        "python src/py/make/populate_constants.py && touch output/constants/.populated"
