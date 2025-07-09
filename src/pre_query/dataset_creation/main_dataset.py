"""
Creates the main analysis dataset.
This is at the level of the transcript.
Start with transcript-detail data.
Keep only transcripts that are also in the queries database.
We create dummies for:
    - benchmark_human_flag (whether transcript was tagged as collusion by humans)
    - llm_flag (whether tagged as collution in the main LLM run)
Merge in compustat data at the company-year level.
"""
#%%
import config
import pandas as pd

# Load datasets
compustat_df = pd.read_parquet('data/company-year-compustat.parquet')
human_ratings_df = pd.read_csv('data/human-ratings.csv')
top_transcripts_df = pd.read_csv('data/top_transcripts.csv')
df = pd.read_feather('data/transcript-detail.feather')

# Load transcript_id from queries database
queried_transcript_ids = pd.read_sql('SELECT transcript_id FROM queries', 'sqlite:///data/queries.sqlite')['transcript_id'].unique()


#%% Filter only queried transcripts
df = df[df['transcriptid'].isin(queried_transcript_ids)]

# %% Create collusion flag in human ratings
# Note: current defintion of binary joe is score >= 75. Only ONE example in the test data has a Joe score >= 75.
# Default to False
human_ratings_df['collusion'] = False
# Set to True if joe_score >= 75 (ignoring NaN values)
human_ratings_df.loc[human_ratings_df['joe_score'] >= 75, 'collusion'] = True
# Set to True if acl_manual_flag = 1 (ignoring NaN values)
human_ratings_df.loc[human_ratings_df['acl_manual_flag'] == 1, 'collusion'] = True

transcript_ids_flagged_by_humans = human_ratings_df[human_ratings_df['collusion']]['transcriptid'].unique()


#%% List of llm flagged transcripts
transcript_ids_flagged_by_llm = top_transcripts_df['transcript_id'].unique()

#%% Create dummies for collusion flags
df['benchmark_human_flag'] = df['transcriptid'].isin(transcript_ids_flagged_by_humans).astype(int)
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
df.to_feather('data/main-analysis-dataset.feather')