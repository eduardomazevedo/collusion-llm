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
    - human_audit_flag (whether transcript was flagged as collusive in human audit, T=True, F/U=False, NA if not audited)
Merge in compustat data at the company-year level.
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
human_audit_df = pd.read_csv(os.path.join('assets', 'human_audit_top_transcripts.csv'))
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

#%% Human audit sample transcripts
transcript_ids_in_human_audit_sample = human_audit_df['transcript_id'].unique()

#%% Process human audit data
# Assert that human_audit_rating has not NAs and is one of T/F/U
assert human_audit_df['human_audit_rating'].notna().all(), "human_audit_rating contains NaN values"
assert set(human_audit_df['human_audit_rating'].unique()).issubset({'T', 'F', 'U'}), "human_audit_rating contains values other than T, F, U"

# Create boolean from T/F/U categorical: T=True, F and U=False
human_audit_df['human_audit_flag'] = human_audit_df['human_audit_rating'] == 'T'

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


# %% Merge compustat
# Create transcript_year from mostimportantdateutc
df['transcript_year'] = pd.to_datetime(df['mostimportantdateutc']).dt.year

# Assert that compustat data has unique rows by (companyid, fyear)
compustat_duplicates = compustat_df.groupby(['companyid', 'fyear']).size()
duplicate_pairs = compustat_duplicates[compustat_duplicates > 1]
assert len(duplicate_pairs) == 0, f"Compustat data contains {len(duplicate_pairs)} duplicate (companyid, fyear) combinations. Expected unique rows. First few duplicates: {duplicate_pairs.head().to_dict()}"

df = df.merge(
    compustat_df,
    left_on=['companyid', 'transcript_year'],
    right_on=['companyid', 'fyear'],
    how='left'
)


#%% Save
df.to_feather(os.path.join(config.DATA_DIR, 'datasets', 'main_analysis_dataset.feather'))