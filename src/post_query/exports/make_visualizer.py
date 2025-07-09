#%%
import config
import pandas as pd
import modules.capiq as capiq
import json
from tqdm import tqdm

# Load the high_scores.csv file
print("Loading high_scores.csv...")
df = pd.read_csv(config.DATA_DIR + "/high_scores.csv")

# Load the companies_transcripts.csv file for metadata
print("Loading companies_transcripts.csv for metadata...")
companies_df = pd.read_csv(config.DATA_DIR + "/companies_transcripts.csv")

# Prepare output Excel file path
output_file = config.DATA_DIR + "/high_scores_transcripts.xlsx"

# Get unique transcript IDs
unique_transcript_ids = df['transcriptid'].unique()
print(f"Found {len(unique_transcript_ids)} unique transcript IDs")

# Fetch all transcripts at once (in batches for robustness)
transcript_json_map = {}
batch_size = 100
total_batches = (len(unique_transcript_ids) + batch_size - 1) // batch_size

for batch_idx in range(total_batches):
    start_idx = batch_idx * batch_size
    end_idx = min((batch_idx + 1) * batch_size, len(unique_transcript_ids))
    batch_ids = unique_transcript_ids[start_idx:end_idx]
    print(f"Processing batch {batch_idx + 1}/{total_batches} (IDs {start_idx + 1}-{end_idx})...")
    try:
        transcript_dict = capiq.get_transcripts(batch_ids.tolist())
        for transcriptid in batch_ids:
            transcript_json_map[transcriptid] = transcript_dict.get(transcriptid, None)
    except Exception as e:
        print(f"Error fetching batch {batch_idx + 1}: {e}")
        print("Attempting to fetch each transcript in this batch individually...")
        for transcriptid in batch_ids:
            try:
                single_dict = capiq.get_transcripts([transcriptid])
                transcript_json_map[transcriptid] = single_dict.get(transcriptid, None)
            except Exception as e2:
                print(f"  Could not fetch transcript {transcriptid}: {e2}")
                transcript_json_map[transcriptid] = None

# Add the transcript_json column to the dataframe
print("Adding transcript_json column to dataframe...")
df['transcript_json'] = df['transcriptid'].map(transcript_json_map)

# Add company name, company id, and headline from companies_transcripts.csv
print("Adding company_name, company_id, and headline columns from companies_transcripts.csv...")
meta_map = companies_df.set_index('transcriptid')[['companyname', 'companyid', 'headline']].to_dict(orient='index')

def get_meta(transcriptid, key):
    meta = meta_map.get(transcriptid, {})
    return meta.get(key, None)

df['company_name_from_transcript'] = df['transcriptid'].apply(lambda tid: get_meta(tid, 'companyname'))
df['company_id_from_transcript'] = df['transcriptid'].apply(lambda tid: get_meta(tid, 'companyid'))
df['headline_from_transcript'] = df['transcriptid'].apply(lambda tid: get_meta(tid, 'headline'))

# Save as Excel file
print(f"Saving to {output_file} ...")
df.to_excel(output_file, index=False)
print("Done!") 