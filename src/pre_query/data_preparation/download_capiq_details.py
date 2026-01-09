#%%
import config
import wrds
import pandas as pd
import os
import sqlite3

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
preferred_transcriptids = set()
if os.path.exists(config.DATABASE_PATH):
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        table_check = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='queries'",
            conn
        )
        if not table_check.empty:
            queries_df = pd.read_sql("SELECT DISTINCT transcriptid FROM queries", conn)
            preferred_transcriptids = set(queries_df['transcriptid'].dropna().astype(int))
            print(f"Loaded {len(preferred_transcriptids):,} transcript IDs from queries database.")
        else:
            print("Queries table not found; using most recent transcript versions only.")
        conn.close()
    except Exception as exc:
        print(f"WARNING: failed to load queries database transcript IDs: {exc}")
else:
    print("Queries database not found; using most recent transcript versions only.")

if preferred_transcriptids:
    available_preferred = df['transcriptid'].isin(preferred_transcriptids)
    n_available = int(available_preferred.sum())
    n_missing = len(preferred_transcriptids) - n_available
    n_override_events = df.loc[available_preferred, 'keydevid'].nunique()
    print(f"Preferred transcript IDs found in WRDS detail: {n_available:,}")
    print(f"Events with preferred transcript versions: {n_override_events:,}")
    if n_missing > 0:
        missing_ids = sorted(preferred_transcriptids - set(df['transcriptid'].dropna().astype(int)))
        print(f"WARNING: {n_missing:,} preferred transcript IDs not found in WRDS detail.")
        print(f"First few missing IDs: {missing_ids[:10]}")

df = eliminate_duplicate_transcripts(df, preferred_transcriptids=preferred_transcriptids)


#%%
# Save
os.makedirs(os.path.dirname(config.TRANSCRIPT_DETAIL_PATH), exist_ok=True)
df.to_feather(config.TRANSCRIPT_DETAIL_PATH)
