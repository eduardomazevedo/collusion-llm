"""
Creates the main analysis dataset.
This is at the level of the transcript.
Start with transcript-detail data.
Keep only transcripts that are also in the queries database.
We create dummies for:
    - benchmark_sample (whether transcript is in the benchmark sample)
    - benchmark_human_flag (whether transcript was tagged as collusion by humans)
    - llm_flag (whether tagged as collution in the main LLM run)
Merge in compustat data at the company-year level.
"""
#%%
import config
import pandas as pd
import numpy as np
import os

# Load datasets
compustat_df = pd.read_parquet(os.path.join(config.DATA_DIR, 'datasets', 'company_year_compustat.parquet'))
human_ratings_df = pd.read_csv(config.HUMAN_RATINGS_PATH)
top_transcripts_df = pd.read_csv(os.path.join(config.DATA_DIR, 'intermediaries', 'top_transcripts.csv'))
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
transcript_ids_flagged_by_llm = top_transcripts_df['transcriptid'].unique()

#%% Create dummies for collusion flags
# Create benchmark_sample flag for whether transcript is in the benchmark sample
df['benchmark_sample'] = df['transcriptid'].isin(transcript_ids_in_benchmark).astype(int)

# Create benchmark_human_flag: 1 if flagged as collusion, 0 if in benchmark but not flagged, NA if not in benchmark
df['benchmark_human_flag'] = df['transcriptid'].isin(transcript_ids_flagged_by_humans).astype(int)
# Set to NA for transcripts not in benchmark sample
df.loc[~df['transcriptid'].isin(transcript_ids_in_benchmark), 'benchmark_human_flag'] = pd.NA
df['llm_flag'] = df['transcriptid'].isin(transcript_ids_flagged_by_llm).astype(int)


# %% Merge compustat
# Create transcript_year from mostimportantdateutc
df['transcript_year'] = pd.to_datetime(df['mostimportantdateutc']).dt.year

df = df.merge(
    compustat_df,
    left_on=['companyid', 'transcript_year'],
    right_on=['companyid', 'fyear'],
    how='left'
)


#%% Save
df.to_feather(os.path.join(config.DATA_DIR, 'datasets', 'main_analysis_dataset.feather'))