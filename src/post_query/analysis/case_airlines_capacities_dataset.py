"""
Build airline-year ASK dataset for the case study using ANAC raw files.

Inputs:
- data/raw/anac/2011.csv ... 2016.csv (semicolon-delimited, latin1 encoding)

Output:
- data/datasets/ask_airline_year.csv
"""

#%%
import os
import unicodedata

import pandas as pd

import config

#%%
# Configuration

RAW_DIR = os.path.join(config.DATA_DIR, "raw", "anac")
OUT_DIR = os.path.join(config.DATA_DIR, "datasets")
OUT_PATH = os.path.join(OUT_DIR, "ask_airline_year.csv")

YEARS = list(range(2011, 2017))
AIRLINES_KEEP = ["GLO", "TAM", "ONE", "AZU"]

#%%
# Helpers

def clean_columns(cols: pd.Index) -> pd.Index:
    return (
        cols
        .str.strip()
        .str.lower()
        .map(lambda x: unicodedata.normalize("NFKD", x)
             .encode("ascii", "ignore")
             .decode("utf-8"))
        .str.replace(" ", "_")
        .str.replace("[()]", "", regex=True)
    )

def normalize_value(series: pd.Series) -> pd.Series:
    return (
        series
        .astype(str)
        .str.strip()
        .str.upper()
        .map(lambda x: unicodedata.normalize("NFKD", x)
             .encode("ascii", "ignore")
             .decode("utf-8"))
    )

#%%
# Load raw files

dfs = {}
for year in YEARS:
    file_path = os.path.join(RAW_DIR, f"{year}.csv")
    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path, sep=";", encoding="latin1")
    df.columns = clean_columns(df.columns)
    dfs[year] = df
    print(f"  rows: {len(df):,}")

#%%
# Filter to airlines and routes of interest

for year, df in dfs.items():
    df["empresa_sigla"] = df["empresa_sigla"].astype(str).str.strip().str.upper()
    df = df[df["empresa_sigla"].isin(AIRLINES_KEEP)].copy()

    natureza_norm = normalize_value(df["natureza"])
    df = df[natureza_norm.eq("DOMESTICA")].copy()

    grupo_norm = normalize_value(df["grupo_de_voo"])
    df = df[grupo_norm.eq("REGULAR")].copy()

    df["ask"] = pd.to_numeric(df["ask"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["ask"])
    dropped = before - len(df)
    if dropped:
        print(f"  {year}: dropped {dropped:,} rows with missing ask")

    dfs[year] = df
    print(f"  {year}: kept {len(df):,} rows after filters")

print("Airlines per year after filters:")
for year, df in dfs.items():
    print(f"  {year}: {sorted(df['empresa_sigla'].unique())}")

#%%
# Aggregate to airline-year ASK

airline_ask_year = []
for year, df in dfs.items():
    df_agg = (
        df
        .groupby("empresa_sigla", as_index=False)
        .agg(ask=("ask", "sum"))
    )
    df_agg["ano"] = year
    airline_ask_year.append(df_agg)

ask_airline_year = pd.concat(airline_ask_year, ignore_index=True)
ask_airline_year["ask_billion"] = ask_airline_year["ask"] / 1e9

#%%
# Save dataset

os.makedirs(OUT_DIR, exist_ok=True)
ask_airline_year.to_csv(OUT_PATH, index=False)

print("ASK airline-year dataset written to:")
print(f"  {OUT_PATH}")
print(f"Rows: {len(ask_airline_year):,}")
print("Preview:")
print(ask_airline_year.head())
