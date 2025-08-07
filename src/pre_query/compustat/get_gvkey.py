"""
Get gvkeys for the company IDs in the transcript_detail.feather file and save them to data/intermediaries/gvkey_table.feather and data/intermediaries/gvkey_list.txt.
"""
#%%
import config
import wrds
import pandas as pd

print(f"Connecting to WRDS with username: {config.WRDS_USERNAME}")

# Establish connection
conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
print("WRDS connection established!")


#%% Get list of unique companyid in the table data/transcript_detail.feather
transcript_detail_path = config.TRANSCRIPT_DETAIL_PATH
transcript_detail_data = pd.read_feather(transcript_detail_path, columns=["companyid"])
unique_company_ids = transcript_detail_data["companyid"].dropna().unique()
print(f"Found {len(unique_company_ids)} unique company IDs in transcript_detail.feather")


#%% Get rows from ciq.wrds_gvkey table for matching company IDs
company_id_list = ', '.join(map(str, unique_company_ids))
query = f"SELECT DISTINCT companyid, gvkey FROM ciq.wrds_gvkey WHERE companyid IN ({company_id_list})"
gvkey_data = conn.raw_sql(query)
print(f"Matched {len(gvkey_data)} company IDs with gvkeys from WRDS database")


#%% Print number of duplicate pairs, duplicate gvkeys, and duplicate company IDs
duplicate_pairs = gvkey_data.duplicated(subset=["companyid", "gvkey"], keep=False)
num_duplicate_pairs = duplicate_pairs.sum()
print(f"Number of duplicate (companyid, gvkey) pairs: {num_duplicate_pairs}")

assert num_duplicate_pairs == 0, f"Found {num_duplicate_pairs} duplicate (companyid, gvkey) pairs in gvkey_data"

duplicate_gvkeys = gvkey_data.duplicated(subset=["gvkey"], keep=False)
num_duplicate_gvkeys = duplicate_gvkeys.sum()
print(f"Number of duplicate gvkeys: {num_duplicate_gvkeys}")

duplicate_company_ids = gvkey_data.duplicated(subset=["companyid"], keep=False)
num_duplicate_company_ids = duplicate_company_ids.sum()
print(f"Number of duplicate company IDs: {num_duplicate_company_ids}")

# Print how many companyid have multiple gvkey
companyid_counts = gvkey_data.groupby("companyid")["gvkey"].nunique()
num_companyid_multiple_gvkey = (companyid_counts > 1).sum()
print(f"Number of company IDs with multiple gvkeys: {num_companyid_multiple_gvkey}")

# Print how many gvkey have multiple companyid
gvkey_counts = gvkey_data.groupby("gvkey")["companyid"].nunique()
num_gvkey_multiple_companyid = (gvkey_counts > 1).sum()
print(f"Number of gvkeys with multiple company IDs: {num_gvkey_multiple_companyid}")


#%% Save gvkey_table.feather and gvkey_list.txt one id per row
gvkey_table_path = "data/intermediaries/gvkey_table.feather"
gvkey_data.to_feather(gvkey_table_path)
print(f"Saved gvkey data to {gvkey_table_path}")

gvkey_list_path = "data/intermediaries/gvkey_list.txt"
gvkey_list_data = gvkey_data['gvkey'].dropna()
gvkey_list_data.to_csv(gvkey_list_path, index=False, header=False)
print(f"Saved {len(gvkey_list_data)} gvkeys to {gvkey_list_path}")


#%%
# Close connection
conn.close()
print("\nWRDS connection closed.")
