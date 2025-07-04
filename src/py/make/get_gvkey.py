"""
Get gvkeys for the company IDs in the transcript-detail.feather file and save them to data/gvkey_table.feather and data/gvkey_list.txt.
"""
#%%
import config
import wrds
import pandas as pd

print(f"Connecting to WRDS with username: {config.WRDS_USERNAME}")

# Establish connection
conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
print("WRDS connection established!")


#%% Get list of unique companyid in the table data/transcript-detail.feather
transcript_detail_path = "data/transcript-detail.feather"
transcript_detail_data = pd.read_feather(transcript_detail_path, columns=["companyid"])
unique_company_ids = transcript_detail_data["companyid"].dropna().unique()
print(f"Found {len(unique_company_ids)} unique company IDs in transcript-detail.feather")


#%% Get rows from ciq.wrds_gvkey table for matching company IDs
company_id_list = ', '.join(map(str, unique_company_ids))
query = f"SELECT companyid, gvkey FROM ciq.wrds_gvkey WHERE companyid IN ({company_id_list})"
gvkey_data = conn.raw_sql(query)
print(f"Matched {len(gvkey_data)} company IDs with gvkeys from WRDS database")


#%% Save gvkey_table.feather and gvkey_list.txt one id per row
gvkey_table_path = "data/gvkey_table.feather"
gvkey_data.to_feather(gvkey_table_path)
print(f"Saved gvkey data to {gvkey_table_path}")

gvkey_list_path = "data/gvkey_list.txt"
gvkey_list_data = gvkey_data['gvkey'].dropna()
gvkey_list_data.to_csv(gvkey_list_path, index=False, header=False)
print(f"Saved {len(gvkey_list_data)} gvkeys to {gvkey_list_path}")


#%%
# Close connection
conn.close()
print("\nWRDS connection closed.")
