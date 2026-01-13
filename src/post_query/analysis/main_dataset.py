"""
Creates the main analysis dataset.
This is at the level of the transcript.
Start with transcript-detail data.
Keep only transcripts that are also in the queries database.
We create dummies for:
    - benchmark_sample (whether transcript is in the benchmark sample)
    - benchmark_human_flag (whether transcript was tagged as collusion by humans in th benchmark sample)
    - llm_flag (whether tagged as collution in the main LLM run)
    - llm_validation_flag (whether transcript was tagged as collusion in the LLM validation run with 10 repeats)
    - human_audit_sample (whether transcript was audited after being flagged in the llm validation run)
    - human_audit_flag (whether transcript was flagged as collusive in human audit, T=True, F=False, NA if not audited)
Merge in compustat data at the company-year level.
Apply data cleaning rules before saving:
    - market_value_total_mil: set to NA if 0
    - employees_thousands: set to NA if 0 or > 3,000 (indicating coding errors)
    - audiolengthsec: set to NA if 0, < 120 seconds, or > 18,000 seconds (5 hours)

Variables in the final dataset:
Core identifiers:
    - companyid: Capital IQ company identifier
    - companyname: Company name from transcript data
    - transcriptid: Unique transcript identifier
    - keydevid: Key development identifier
    - transcript_year: Year of the transcript (extracted from mostimportantdateutc)
    - headline: Transcript headline/title

Classification variables (our constructions):
    - benchmark_sample: Boolean, whether transcript is in the benchmark sample
    - benchmark_human_flag: Boolean/NA, whether flagged as collusion by humans (NA if not in benchmark)
    - llm_flag: Boolean, whether tagged as collusion in the main LLM run
    - llm_validation_flag: Boolean/NA, whether flagged in LLM validation run (NA if no validation)
    - human_audit_sample: Boolean, whether transcript was audited after LLM validation flagging
    - human_audit_flag: Boolean/NA, whether flagged as collusive in human audit (NA if not audited)

LLM score variables:
    - original_score: Float/NA, original LLM score from the first query of SimpleCapacityV8.1.1 prompt (NA if no query result)

Capital IQ transcript variables:
    - mostimportantdateutc: Date of the transcript
    - mostimportanttimeutc: Time of the transcript
    - keydeveventtypeid: Event type identifier
    - keydeveventtypename: Event type name
    - transcriptcollectiontypeid: Collection type identifier
    - transcriptcollectiontypename: Collection type name
    - transcriptpresentationtypeid: Presentation type identifier
    - transcriptpresentationtypename: Presentation type name
    - transcriptcreationdate_utc: Creation date of transcript
    - transcriptcreationtime_utc: Creation time of transcript
    - audiolengthsec: Audio length in seconds

Compustat variables (nice names):
    - market_value_total_mil: Market value of total capital in millions USD
    - employees_thousands: Number of employees in thousands
    - gics_sector: GICS sector code
    - gics_industry: GICS industry code
    - gics_group: GICS industry group code
    - gics_subindustry: GICS sub-industry code
    - incorporation_country: Country of incorporation code
    - domicile_country: Location/domicile country code

Dataset is sorted by: companyid, mostimportantdateutc, transcriptid
"""

#%%
import config
import pandas as pd
import numpy as np
import os

# Load datasets
compustat_df = pd.read_feather(os.path.join(config.DATA_DIR, 'datasets', 'company_year_compustat.feather'))
human_ratings_df = pd.read_csv(config.HUMAN_RATINGS_PATH)
top_transcripts_data_df = pd.read_csv(os.path.join(config.DATA_DIR, 'datasets', 'top_transcripts_data.csv'))
original_score_df = pd.read_csv(os.path.join(config.DATA_DIR, 'intermediaries', 'original_score.csv'))
human_audit_df = pd.read_excel(config.HUMAN_AUDIT_PATH)
df = pd.read_feather(config.TRANSCRIPT_DETAIL_PATH)

# Load transcriptid from queries database
queried_transcript_ids = pd.read_sql('SELECT transcriptid FROM queries', f'sqlite:///{config.DATABASE_PATH}')['transcriptid'].unique()


#%% Filter only queried transcripts
df = df[df['transcriptid'].isin(queried_transcript_ids)]

# %% Create collusion flag in human ratings
# Note: current defintion of binary joe is score >= JOE_SCORE_THRESHOLD. Only ONE example in the test data has a Joe score >= 75.
# Default to False
human_ratings_df['collusion'] = False
# Set to True if joe_score >= JOE_SCORE_THRESHOLD (ignoring NaN values)
human_ratings_df.loc[human_ratings_df['joe_score'] >= config.JOE_SCORE_THRESHOLD, 'collusion'] = True
# Set to True if acl_manual_flag = 1 (ignoring NaN values)
human_ratings_df.loc[human_ratings_df['acl_manual_flag'] == 1, 'collusion'] = True

transcript_ids_flagged_by_humans = human_ratings_df[human_ratings_df['collusion']]['transcriptid'].unique()
transcript_ids_in_benchmark = human_ratings_df['transcriptid'].unique()


#%% List of llm flagged transcripts
transcript_ids_flagged_by_llm = top_transcripts_data_df['transcriptid'].unique()

#%% List of validation run transcripts  
# Transcripts that went through validation runs (have mean_score_ten_repeats)
transcript_ids_with_validation = top_transcripts_data_df[top_transcripts_data_df['mean_score_ten_repeats'].notna()]['transcriptid'].unique()

# Check if any transcripts in top_transcripts_data do not have validation
transcripts_without_validation = top_transcripts_data_df[top_transcripts_data_df['mean_score_ten_repeats'].isna()]
if len(transcripts_without_validation) > 0:
    print(f"WARNING: {len(transcripts_without_validation)} transcripts in top_transcripts_data do not have validation runs (mean_score_ten_repeats is NA)")
    print(f"First few transcript IDs without validation: {transcripts_without_validation['transcriptid'].head().tolist()}")

# Transcripts flagged in validation runs (mean_score_ten_repeats >= LLM_SCORE_THRESHOLD)
transcript_ids_flagged_in_validation = top_transcripts_data_df[
    top_transcripts_data_df['mean_score_ten_repeats'] >= config.LLM_SCORE_THRESHOLD
]['transcriptid'].unique()

#%% Process human audit data
# Clean audit ratings, dropping blanks and excluding N (not in the audit sample)
audit_col = "T/F/N"
human_audit_df[audit_col] = (
    human_audit_df[audit_col].astype("string").str.strip().str.upper().replace("", pd.NA)
)
human_audit_df = human_audit_df[human_audit_df[audit_col].notna()].copy()
human_audit_df = human_audit_df[human_audit_df[audit_col].isin(["T", "F"])].copy()
assert set(human_audit_df[audit_col].unique()).issubset({'T', 'F'}), "T/F/N contains values other than T, F"

# Create boolean from T/F categorical: T=True, F=False
human_audit_df['human_audit_flag'] = human_audit_df[audit_col] == 'T'

# Human audit sample transcripts (exclude blanks)
transcript_ids_in_human_audit_sample = human_audit_df['transcript_id'].unique()

#%% Create dummies for collusion flags
# Create benchmark_sample flag for whether transcript is in the benchmark sample
df['benchmark_sample'] = df['transcriptid'].isin(transcript_ids_in_benchmark)

# Create benchmark_human_flag: True if flagged as collusion, False if in benchmark but not flagged, NA if not in benchmark
df['benchmark_human_flag'] = df['transcriptid'].isin(transcript_ids_flagged_by_humans)
# Set to NA for transcripts not in benchmark sample
df.loc[~df['transcriptid'].isin(transcript_ids_in_benchmark), 'benchmark_human_flag'] = pd.NA

# Create llm_flag (whether tagged as collusion in the main LLM run)
df['llm_flag'] = df['transcriptid'].isin(transcript_ids_flagged_by_llm)

# Create llm_validation_flag (whether transcript was tagged as collusion in the LLM validation run with 10 repeats)
# First, set all to NA
df['llm_validation_flag'] = pd.NA
# Set to True/False only for transcripts that had validation runs
df.loc[df['transcriptid'].isin(transcript_ids_with_validation), 'llm_validation_flag'] = df.loc[df['transcriptid'].isin(transcript_ids_with_validation), 'transcriptid'].isin(transcript_ids_flagged_in_validation)

# Create human_audit_sample flag (whether transcript was audited after being flagged in the llm validation run)
df['human_audit_sample'] = df['transcriptid'].isin(transcript_ids_in_human_audit_sample)

# Merge human audit flag
df = df.merge(
    human_audit_df[['transcript_id', 'human_audit_flag']],
    left_on='transcriptid',
    right_on='transcript_id',
    how='left'
).drop('transcript_id', axis=1)

# Set human_audit_flag to NA for transcripts not in human audit sample
df.loc[~df['human_audit_sample'], 'human_audit_flag'] = pd.NA

#%% Merge original_score
# Merge original score from the initial LLM run for all transcripts
df = df.merge(
    original_score_df[['transcriptid', 'score']],
    on='transcriptid',
    how='left'
)
# Rename score to original_score for clarity
df = df.rename(columns={'score': 'original_score'})


# %% Merge compustat
# Create transcript_year from mostimportantdateutc
df['transcript_year'] = pd.to_datetime(df['mostimportantdateutc']).dt.year

# Assert that compustat data has unique rows by (companyid, fiscal_year)
compustat_duplicates = compustat_df.groupby(['companyid', 'fiscal_year']).size()
duplicate_pairs = compustat_duplicates[compustat_duplicates > 1]
assert len(duplicate_pairs) == 0, f"Compustat data contains {len(duplicate_pairs)} duplicate (companyid, fiscal_year) combinations. Expected unique rows. First few duplicates: {duplicate_pairs.head().to_dict()}"

df = df.merge(
    compustat_df,
    left_on=['companyid', 'transcript_year'],
    right_on=['companyid', 'fiscal_year'],
    how='left'
)

# Drop columns that are not needed for analysis
columns_to_drop = ['fiscal_year', 'company_name', 'company_status', 'gvkey', 'currency_code', 'data_date', 'industry_format']
# Only drop columns that exist in the dataframe
columns_to_drop = [col for col in columns_to_drop if col in df.columns]
df = df.drop(columns=columns_to_drop)

# Reorder columns for better organization
# 1. Core identifiers
core_columns = ['companyid', 'companyname', 'transcriptid', 'keydevid', 'transcript_year', 'headline']

# 2. Our constructed classification variables
classification_columns = ['benchmark_sample', 'benchmark_human_flag', 'llm_flag', 'llm_validation_flag', 'human_audit_sample', 'human_audit_flag']

# 2b. LLM score variables
llm_score_columns = ['original_score']

# 3. Other Capital IQ transcript variables
capiq_columns = [col for col in df.columns if col not in core_columns + classification_columns + llm_score_columns and col not in ['market_value_total_mil', 'employees_thousands', 'gics_sector', 'gics_industry', 'gics_group', 'gics_subindustry', 'sic', 'naics', 'incorporation_country', 'domicile_country']]

# 4. Compustat variables (the remaining ones after dropping)
compustat_columns = ['market_value_total_mil', 'employees_thousands', 'gics_sector', 'gics_industry', 'gics_group', 'gics_subindustry', 'sic', 'naics', 'incorporation_country', 'domicile_country']

# Reorder the dataframe
column_order = core_columns + classification_columns + llm_score_columns + capiq_columns + compustat_columns
df = df[column_order]

# Sort the dataframe
df = df.sort_values(['companyid', 'mostimportantdateutc', 'transcriptid'])

#%% Data cleaning
# Clean market value: set to NA if 0
df.loc[df['market_value_total_mil'] == 0, 'market_value_total_mil'] = pd.NA

# Clean employees: set to NA if 0 or > 3,000 thousands (3 million employees)
df.loc[df['employees_thousands'] == 0, 'employees_thousands'] = pd.NA
df.loc[df['employees_thousands'] > 3000, 'employees_thousands'] = pd.NA

# Clean audio length: set to NA if 0, < 120 seconds, or > 5 hours (18,000 seconds)
df.loc[df['audiolengthsec'] == 0, 'audiolengthsec'] = pd.NA
df.loc[df['audiolengthsec'] < 120, 'audiolengthsec'] = pd.NA
df.loc[df['audiolengthsec'] > 18000, 'audiolengthsec'] = pd.NA

#%% Save
df.to_feather(os.path.join(config.DATA_DIR, 'datasets', 'main_analysis_dataset.feather'))
# %%
