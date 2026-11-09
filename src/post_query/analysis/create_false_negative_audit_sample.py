"""Create the fixed stratified sample for the false-negative human audit.

The resulting manifest is a research-design input and is committed under
assets/ so that the audit sample does not depend only on reproducing an RNG
sequence.
"""

#%%
import argparse
import os

import numpy as np
import pandas as pd

import config

#%%
SAMPLE_SEED = 42
OUTPUT_PATH = os.path.join(config.ROOT, "assets", "false_negative_audit_sample.csv")

STRATA = [
    ("Originally flagged but not validated", 80),
    ("Original score 70--74", 50),
    ("Original score 65--69", 35),
    ("Original score 50--64", 20),
    ("Original score 0--49", 15),
]

EXPECTED_POPULATIONS = {
    "Originally flagged but not validated": 3_760,
    "Original score 70--74": 3_270,
    "Original score 65--69": 4_233,
    "Original score 50--64": 7_289,
    "Original score 0--49": 479_439,
}

#%%
parser = argparse.ArgumentParser(
    description="Create the fixed stratified false-negative audit sample."
)
parser.add_argument(
    "--output",
    default=OUTPUT_PATH,
    help="Path for the committed sample manifest.",
)
parser.add_argument(
    "--seed",
    type=int,
    default=SAMPLE_SEED,
    help="Random seed used for sampling.",
)
parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Replace an existing sample manifest.",
)
args = parser.parse_args()

if os.path.exists(args.output) and not args.overwrite:
    raise FileExistsError(
        f"Sample manifest already exists: {args.output}. "
        "Use --overwrite only when intentionally drawing a new audit sample."
    )

#%%
input_path = os.path.join(config.DATA_DIR, "datasets", "main_analysis_dataset.feather")
print(f"Loading audit universe: {input_path}")
df = pd.read_feather(
    input_path,
    columns=[
        "transcriptid",
        "original_score",
        "llm_flag",
        "llm_validation_flag",
        "human_audit_sample",
    ],
)
print(f"Loaded {len(df):,} transcripts")

if df["transcriptid"].duplicated().any():
    duplicate_count = int(df["transcriptid"].duplicated().sum())
    raise ValueError(f"Audit universe contains {duplicate_count:,} duplicate transcript IDs")
if df["original_score"].isna().any():
    missing_count = int(df["original_score"].isna().sum())
    raise ValueError(f"Audit universe contains {missing_count:,} missing original scores")

#%%
stratum_masks = {
    "Originally flagged but not validated": (
        df["llm_flag"].eq(True) & df["llm_validation_flag"].eq(False)
    ),
    "Original score 70--74": df["original_score"].between(
        70, 75, inclusive="left"
    ),
    "Original score 65--69": df["original_score"].between(
        65, 70, inclusive="left"
    ),
    "Original score 50--64": df["original_score"].between(
        50, 65, inclusive="left"
    ),
    "Original score 0--49": df["original_score"].between(
        0, 50, inclusive="left"
    ),
}

membership_count = sum(mask.astype(int) for mask in stratum_masks.values())
non_validated = ~df["llm_validation_flag"].eq(True)
if not membership_count.loc[non_validated].eq(1).all():
    raise ValueError("The proposed strata are not exhaustive and mutually exclusive")
if membership_count.loc[~non_validated].ne(0).any():
    raise ValueError("At least one LLM-validated transcript entered the audit strata")

print("\nAudit universe by stratum:")
for stratum, _ in STRATA:
    observed = int(stratum_masks[stratum].sum())
    expected = EXPECTED_POPULATIONS[stratum]
    print(f"  {stratum}: {observed:,}")
    if observed != expected:
        raise ValueError(
            f"Population mismatch for '{stratum}': expected {expected:,}, "
            f"found {observed:,}"
        )

population_total = sum(int(mask.sum()) for mask in stratum_masks.values())
if population_total != int(non_validated.sum()):
    raise ValueError("Stratum counts do not sum to the non-validated population")
print(f"  Total: {population_total:,}")

#%%
rng = np.random.default_rng(args.seed)
sampled_frames = []

print(f"\nDrawing audit sample with seed {args.seed}:")
for stratum, sample_size in STRATA:
    candidates = (
        df.loc[stratum_masks[stratum], ["transcriptid", "original_score"]]
        .sort_values("transcriptid")
        .reset_index(drop=True)
    )
    selected_positions = rng.choice(len(candidates), size=sample_size, replace=False)
    sampled = candidates.iloc[selected_positions].copy()
    sampled["stratum"] = stratum
    sampled_frames.append(sampled)
    print(f"  {stratum}: selected {len(sampled):,} of {len(candidates):,}")

sample = pd.concat(sampled_frames, ignore_index=True)
sample = sample[["transcriptid", "stratum", "original_score"]]
sample["transcriptid"] = sample["transcriptid"].astype("int64")

if len(sample) != 200:
    raise RuntimeError(f"Expected 200 sampled transcripts, found {len(sample):,}")
if sample["transcriptid"].duplicated().any():
    raise RuntimeError("The audit sample contains duplicate transcript IDs")
prior_audit_ids = set(
    df.loc[df["human_audit_sample"].eq(True), "transcriptid"].astype(int)
)
overlap = set(sample["transcriptid"].astype(int)) & prior_audit_ids
if overlap:
    raise RuntimeError(f"The new sample overlaps the prior audit by {len(overlap):,} rows")

#%%
os.makedirs(os.path.dirname(args.output), exist_ok=True)
temporary_path = f"{args.output}.tmp.{os.getpid()}"
sample.to_csv(temporary_path, index=False)
os.replace(temporary_path, args.output)

print(f"\nSaved fixed audit sample: {args.output}")
print(f"Rows: {len(sample):,}")
print("Sample counts:")
print(sample["stratum"].value_counts(sort=False).to_string())
