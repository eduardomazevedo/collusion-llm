#%%
import config
import pandas as pd
import modules.capiq as capiq
import json
from tqdm import tqdm

# Load the high_scores.csv file
print("Loading high_scores.csv...")
df = pd.read_csv(config.DATA_DIR + "/high_scores.csv")

# Load the companies-transcripts.csv file for metadata
print("Loading companies-transcripts.csv for metadata...")
companies_df = pd.read_csv(config.DATA_DIR + "/companies-transcripts.csv")

# Prepare output Excel file path
output_file = config.DATA_DIR + "/high_scores_transcripts.xlsx"

# Get unique transcript IDs
unique_transcript_ids = df['transcript_id'].unique()
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
        for transcript_id in batch_ids:
            transcript_json_map[transcript_id] = transcript_dict.get(transcript_id, None)
    except Exception as e:
        print(f"Error fetching batch {batch_idx + 1}: {e}")
        print("Attempting to fetch each transcript in this batch individually...")
        for transcript_id in batch_ids:
            try:
                single_dict = capiq.get_transcripts([transcript_id])
                transcript_json_map[transcript_id] = single_dict.get(transcript_id, None)
            except Exception as e2:
                print(f"  Could not fetch transcript {transcript_id}: {e2}")
                transcript_json_map[transcript_id] = None

# Add the transcript_json column to the dataframe
print("Adding transcript_json column to dataframe...")
df['transcript_json'] = df['transcript_id'].map(transcript_json_map)

# Add company name, company id, and headline from companies-transcripts.csv
print("Adding company_name, company_id, and headline columns from companies-transcripts.csv...")
meta_map = companies_df.set_index('transcriptid')[['companyname', 'companyid', 'headline']].to_dict(orient='index')

def get_meta(transcript_id, key):
    meta = meta_map.get(transcript_id, {})
    return meta.get(key, None)

df['company_name_from_transcript'] = df['transcript_id'].apply(lambda tid: get_meta(tid, 'companyname'))
df['company_id_from_transcript'] = df['transcript_id'].apply(lambda tid: get_meta(tid, 'companyid'))
df['headline_from_transcript'] = df['transcript_id'].apply(lambda tid: get_meta(tid, 'headline'))

# Save as Excel file
print(f"Saving to {output_file} ...")
df.to_excel(output_file, index=False)
print("Done!") 