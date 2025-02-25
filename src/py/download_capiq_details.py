#%%
import config
import wrds
import pandas as pd

# Connect
conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
ciq_tables = conn.list_tables(library='ciq')
transcript_tables = [table for table in ciq_tables if 'transcript' in table]

# Download
query = f"SELECT * FROM ciq.wrds_transcript_detail"
df = conn.raw_sql(query)
conn.close()

# Formatting
## Factors
df['keydeveventtypeid'] = df['keydeveventtypeid'].astype('category')
df['keydeveventtypename'] = df['keydeveventtypename'].astype('category')
df['transcriptcollectiontypeid'] = df['transcriptcollectiontypeid'].astype('category')
df['transcriptcollectiontypename'] = df['transcriptcollectiontypename'].astype('category')
df['transcriptpresentationtypeid'] = df['transcriptpresentationtypeid'].astype('category')
df['transcriptpresentationtypename'] = df['transcriptpresentationtypename'].astype('category')

# Convert transcriptcreationdate_utc to date
df['transcriptcreationdate_utc'] = pd.to_datetime(df['transcriptcreationdate_utc']).dt.date

# Convert transcriptcreationtime_utc to time
df['transcriptcreationtime_utc'] = pd.to_datetime(df['transcriptcreationtime_utc'], format='%H:%M:%S').dt.time

# Convert mostimportantdateutc to date
df['mostimportantdateutc'] = pd.to_datetime(df['mostimportantdateutc']).dt.date

# Convert mostimportanttimeutc to time
df['mostimportanttimeutc'] = pd.to_datetime(df['mostimportanttimeutc'], format='%H:%M:%S').dt.time

# Integers
df['companyid'] = df['companyid'].astype('Int64')
df['transcriptid'] = df['transcriptid'].astype('Int64')
df['keydevid'] = df['keydevid'].astype('Int64')

#%%
from modules.utils import eliminate_duplicate_transcripts
df = eliminate_duplicate_transcripts(df)


#%%
# Save
df.to_feather('./data/transcript-detail.feather')