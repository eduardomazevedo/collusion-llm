#%%
import config
import pandas as pd

# Load the human rating scores
acl_scores = pd.read_csv(config.ACL_SCORES_PATH)

# Load data/transcript-detail.feather
transcript_detail = pd.read_feather(config.TRANSCRIPT_DETAIL_PATH)


#%%
# Drop 'call quarter' and 'call year' columns from acl_scores
acl_scores = acl_scores.drop(['call quarter', 'call year'], axis=1)


# %%
# Create a mapping dictionary for carrier to company name
carrier_to_company = {
    'AA': 'American Airlines Group Inc.',
    'AS': 'Alaska Air Group, Inc.',
    'B6': 'JetBlue Airways Corporation',
    'CO': None,
    'DL': 'Delta Air Lines, Inc.',
    'FL': 'AirTran Holdings, LLC',
    'NK': 'Spirit Airlines, Inc.',
    'NW': 'Northwest Airlines Corporation',
    'OO': 'SkyWest, Inc.',
    'UA': 'United Airlines Holdings, Inc.',
    'US': 'US Airways Group, Inc.',
    'WN': 'Southwest Airlines Co.'
}

# Get list of company names, excluding None values
list_of_companies = [company for company in carrier_to_company.values() if company is not None]


#%%
# Map carrier codes to company names in acl_scores
acl_scores['companyname'] = acl_scores['carrier'].map(carrier_to_company)


# %%
# Filter transcript_detail to only include companies in carrier_to_company
filtered_transcripts = transcript_detail[
    (transcript_detail['companyname'].isin(list_of_companies)) &
    (transcript_detail['keydeveventtypename'] == 'Earnings Calls')
].copy()


# %%
from modules.utils import get_quarter_year_from_headline

# Apply the function to the headline column
filtered_transcripts['quarter'], filtered_transcripts['year'] = zip(*filtered_transcripts['headline'].apply(get_quarter_year_from_headline))
# Convert quarter and year to integers
filtered_transcripts['quarter'] = filtered_transcripts['quarter'].astype('Int64')
filtered_transcripts['year'] = filtered_transcripts['year'].astype('Int64')


# %%
# Merge transcriptid from filtered_transcripts into acl_scores
acl_scores = acl_scores.merge(
    filtered_transcripts[['companyname', 'quarter', 'year', 'transcriptid']],
    on=['companyname', 'quarter', 'year'],
    how='left'
)

# %%
acl_scores.columns
# %%
# Reorder and drop columns
# Get all columns except the ones we want to drop
cols_to_keep = ['manual_capacity_discipline_count', 'auto_capacity_discipline_count']

# Reorder with transcriptid first, followed by remaining columns
acl_scores = acl_scores[['transcriptid'] + cols_to_keep]

# Rename columns
acl_scores = acl_scores.rename(columns={
    'manual_capacity_discipline_count': 'acl_manual_flag',
    'auto_capacity_discipline_count': 'acl_auto_flag'
})

# Drop rows with any NA values
acl_scores = acl_scores.dropna()


# %%
# Load Joe's manual ratings
joe_scores = pd.read_csv(config.JOE_SCORES_PATH)


# %%
# Ensure both DataFrames have the same columns by adding missing ones with NaN values
all_columns = list(set(joe_scores.columns) | set(acl_scores.columns))
for col in all_columns:
    if col not in joe_scores.columns:
        joe_scores[col] = pd.NA
    if col not in acl_scores.columns:
        acl_scores[col] = pd.NA

# Stack the DataFrames
combined_scores = pd.concat([joe_scores, acl_scores], axis=0, ignore_index=True)

# %%
# Save to CSV
combined_scores.to_csv(config.HUMAN_RATINGS_PATH, index=False)