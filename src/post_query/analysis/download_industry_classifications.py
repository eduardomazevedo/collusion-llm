#!/usr/bin/env python3
"""
Download industry classification titles from WRDS.

This script downloads the full hierarchy of industry classification codes and their
descriptive titles from WRDS for GICS (Global Industry Classification Standard),
NAICS (North American Industry Classification System), and SIC (Standard Industrial Classification).

Both active and inactive codes are downloaded for each classification system.

The data is saved as separate feather files in data/intermediaries/ for each classification system.

Files produced:
- gics_classifications.feather: GICS codes with descriptions and type (Sector, Group, Industry, Sub-Industry)
- naics_classifications.feather: NAICS codes with descriptions
- sic_classifications.feather: SIC codes with descriptions
"""

#%%
import config
import wrds
import pandas as pd
import os

# Ensure we're running from root
config.ensure_running_from_root()

print(f"Connecting to WRDS with username: {config.WRDS_USERNAME}")

# Connect to WRDS
conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
print("WRDS connection established!")

#%%
# Create output directory if it doesn't exist
output_dir = "data/intermediaries"
os.makedirs(output_dir, exist_ok=True)

# ---------------------------------------------------------
# 1. GICS (Global Industry Classification Standard)
# Table: comp.r_giccd
# ---------------------------------------------------------
print("\n" + "="*60)
print("Downloading GICS classifications...")
print("="*60)

gics_query = """
SELECT giccd, gicdesc, gictype 
FROM comp.r_giccd
ORDER BY giccd
"""
df_gics = conn.raw_sql(gics_query)
print(f"Found {len(df_gics)} GICS classifications")

# Convert giccd to string to preserve leading zeros and pad to 8 digits
df_gics['giccd'] = df_gics['giccd'].astype(str).str.zfill(8)

# Add level based on code length (number of significant digits)
# GICS codes are length 2 (Sector), 4 (Group), 6 (Industry), 8 (Sub-Industry)
df_gics['level'] = df_gics['giccd'].apply(lambda x: len(str(x).lstrip('0')) if str(x).lstrip('0') else 0)

# Print summary by level
print("\nGICS classifications by level:")
for level in sorted(df_gics['level'].unique()):
    count = (df_gics['level'] == level).sum()
    level_name = {2: "Sector", 4: "Group", 6: "Industry", 8: "Sub-Industry"}.get(level, f"Level {level}")
    print(f"  {level_name} ({level} digits): {count}")

# Save GICS data
gics_path = os.path.join(output_dir, "gics_classifications.feather")
print(f"\nSaving GICS classifications to {gics_path}")
df_gics.to_feather(gics_path)
print("GICS data saved successfully!")

#%%
# ---------------------------------------------------------
# 2. NAICS (North American Industry Classification System)
# Table: comp.r_naiccd
# ---------------------------------------------------------
print("\n" + "="*60)
print("Downloading NAICS classifications...")
print("="*60)

naics_query = """
SELECT naicscd, naicsdesc
FROM comp.r_naiccd
ORDER BY naicscd
"""
df_naics = conn.raw_sql(naics_query)
print(f"Found {len(df_naics)} NAICS classifications")

# Rename columns to match expected names (naicscd -> naics)
df_naics = df_naics.rename(columns={'naicscd': 'naics'})

# Convert naics to string to preserve leading zeros and pad to 6 digits
df_naics['naics'] = df_naics['naics'].astype(str).str.zfill(6)

# Add level based on code length (NAICS has 2, 3, 4, 5, 6 digit codes)
df_naics['level'] = df_naics['naics'].apply(lambda x: len(str(x).lstrip('0')) if str(x).lstrip('0') else 0)

# Print summary by level
print("\nNAICS classifications by level:")
for level in sorted(df_naics['level'].unique()):
    count = (df_naics['level'] == level).sum()
    level_name = {2: "Sector", 3: "Subsector", 4: "Industry Group", 5: "Industry", 6: "National Industry"}.get(level, f"Level {level}")
    print(f"  {level_name} ({level} digits): {count}")

# Save NAICS data
naics_path = os.path.join(output_dir, "naics_classifications.feather")
print(f"\nSaving NAICS classifications to {naics_path}")
df_naics.to_feather(naics_path)
print("NAICS data saved successfully!")

#%%
# ---------------------------------------------------------
# 3. SIC (Standard Industrial Classification)
# Table: comp.r_siccd
# ---------------------------------------------------------
print("\n" + "="*60)
print("Downloading SIC classifications...")
print("="*60)

sic_query = """
SELECT siccd, sicdesc
FROM comp.r_siccd
ORDER BY siccd
"""
df_sic = conn.raw_sql(sic_query)
print(f"Found {len(df_sic)} SIC classifications")

# Rename columns to match expected names (siccd -> sic)
df_sic = df_sic.rename(columns={'siccd': 'sic'})

# Convert sic to string to preserve leading zeros and pad to 4 digits
df_sic['sic'] = df_sic['sic'].astype(str).str.zfill(4)

# Add level based on code length
# SIC codes can be 2 digits (Major Group), 3 digits (Industry Group), 4 digits (Industry)
df_sic['level'] = df_sic['sic'].apply(lambda x: len(str(x).lstrip('0')) if str(x).lstrip('0') else 0)

# Print summary by level
print("\nSIC classifications by level:")
for level in sorted(df_sic['level'].unique()):
    count = (df_sic['level'] == level).sum()
    level_name = {2: "Major Group", 3: "Industry Group", 4: "Industry"}.get(level, f"Level {level}")
    print(f"  {level_name} ({level} digits): {count}")

# Save SIC data
sic_path = os.path.join(output_dir, "sic_classifications.feather")
print(f"\nSaving SIC classifications to {sic_path}")
df_sic.to_feather(sic_path)
print("SIC data saved successfully!")

#%%
# Close connection
conn.close()
print("\nWRDS connection closed.")

print("\n" + "="*60)
print("Download completed successfully!")
print("="*60)
print(f"\nFiles saved to {output_dir}/:")
print(f"  - gics_classifications.feather ({len(df_gics)} records)")
print(f"  - naics_classifications.feather ({len(df_naics)} records)")
print(f"  - sic_classifications.feather ({len(df_sic)} records)")
