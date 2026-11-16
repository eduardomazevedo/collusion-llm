"""Estimate the false-negative rate from the stratified expert audit.

Outputs:
- data/outputs/tables/false_negative_rate_estimates.csv
- data/outputs/tables/false_negative_rate_estimates.tex
- data/outputs/tables/false_negative_rate_estimates.txt
- data/yaml/false_negative_rate.yaml
"""

#%%
import os
import sys

import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm
from statsmodels.stats.proportion import proportion_confint

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(ROOT_DIR)

import config

#%%
SAMPLE_PATH = os.path.join(config.ROOT, "assets", "false_negative_audit_sample.csv")
RESULTS_PATH = os.path.join(config.ROOT, "assets", "false_negative_audit_results.csv")
OUTPUT_DIR = os.path.join(config.DATA_DIR, "outputs", "tables")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "false_negative_rate_estimates.csv")
TEX_PATH = os.path.join(OUTPUT_DIR, "false_negative_rate_estimates.tex")
NOTE_PATH = os.path.join(OUTPUT_DIR, "false_negative_rate_estimates.txt")
YAML_PATH = os.path.join(config.DATA_DIR, "yaml", "false_negative_rate.yaml")
CONFIDENCE_LEVEL = 0.95

STRATA = [
    "Originally flagged but not validated",
    "Original score 70--74",
    "Original score 65--69",
    "Original score 50--64",
    "Original score 0--49",
]

POPULATION_SIZES = {
    "Originally flagged but not validated": 3_760,
    "Original score 70--74": 3_270,
    "Original score 65--69": 4_233,
    "Original score 50--64": 7_289,
    "Original score 0--49": 479_439,
}

#%%
print(f"Loading fixed audit sample: {SAMPLE_PATH}")
sample_df = pd.read_csv(SAMPLE_PATH)
print(f"Loading completed audit results: {RESULTS_PATH}")
results_df = pd.read_csv(RESULTS_PATH)

required_sample_columns = {"transcriptid", "stratum"}
required_result_columns = {"transcriptid", "expert_rating"}
if missing := required_sample_columns - set(sample_df.columns):
    raise ValueError(f"Audit sample is missing columns: {sorted(missing)}")
if missing := required_result_columns - set(results_df.columns):
    raise ValueError(f"Audit results are missing columns: {sorted(missing)}")
if sample_df["transcriptid"].duplicated().any():
    raise ValueError("Audit sample contains duplicate transcript IDs")
if results_df["transcriptid"].duplicated().any():
    raise ValueError("Audit results contain duplicate transcript IDs")

sample_ids = set(sample_df["transcriptid"])
result_ids = set(results_df["transcriptid"])
if sample_ids != result_ids:
    raise ValueError(
        "Audit sample and results contain different transcript IDs: "
        f"{len(sample_ids - result_ids)} missing results and "
        f"{len(result_ids - sample_ids)} unexpected results"
    )

unexpected_strata = set(sample_df["stratum"]) - set(STRATA)
if unexpected_strata:
    raise ValueError(f"Unexpected audit strata: {sorted(unexpected_strata)}")
if set(sample_df["stratum"]) != set(STRATA):
    raise ValueError("At least one expected audit stratum is absent from the sample")

audit_df = sample_df[["transcriptid", "stratum"]].merge(
    results_df[["transcriptid", "expert_rating"]],
    on="transcriptid",
    how="left",
    validate="one_to_one",
)
audit_df["expert_rating"] = (
    audit_df["expert_rating"].astype("string").str.strip().str.upper()
)
if not audit_df["expert_rating"].isin(["T", "F"]).all():
    invalid_ratings = sorted(
        audit_df.loc[~audit_df["expert_rating"].isin(["T", "F"]), "expert_rating"]
        .dropna()
        .unique()
    )
    raise ValueError(
        "The false-negative estimator requires every audit to have a binary T/F "
        f"rating. Invalid ratings: {invalid_ratings}"
    )

#%%
alpha = 1 - CONFIDENCE_LEVEL
population_total = sum(POPULATION_SIZES.values())
rows = []
aggregate_variance = 0.0

print("\nCalculating stratum estimates:")
for stratum in STRATA:
    stratum_df = audit_df[audit_df["stratum"] == stratum]
    population_size = POPULATION_SIZES[stratum]
    audit_sample_size = len(stratum_df)
    audited_false_negatives = int(stratum_df["expert_rating"].eq("T").sum())
    false_negative_rate = audited_false_negatives / audit_sample_size

    ci_lower, ci_upper = proportion_confint(
        audited_false_negatives,
        audit_sample_size,
        alpha=alpha,
        method="wilson",
    )

    population_weight = population_size / population_total
    finite_population_correction = 1 - audit_sample_size / population_size
    stratum_variance = (
        finite_population_correction
        * false_negative_rate
        * (1 - false_negative_rate)
        / (audit_sample_size - 1)
    )
    aggregate_variance += population_weight**2 * stratum_variance

    rows.append(
        {
            "stratum": stratum,
            "population_size": population_size,
            "population_weight": population_weight,
            "audit_sample_size": audit_sample_size,
            "audited_false_negatives": audited_false_negatives,
            "false_negative_rate": false_negative_rate,
            "false_negative_rate_ci_lower": ci_lower,
            "false_negative_rate_ci_upper": ci_upper,
            "implied_false_negatives": population_size * false_negative_rate,
            "implied_false_negatives_ci_lower": population_size * ci_lower,
            "implied_false_negatives_ci_upper": population_size * ci_upper,
        }
    )
    print(
        f"  {stratum}: {audited_false_negatives}/{audit_sample_size} = "
        f"{false_negative_rate:.2%}"
    )

#%%
estimates_df = pd.DataFrame(rows)
aggregate_rate = float(
    (estimates_df["population_weight"] * estimates_df["false_negative_rate"]).sum()
)
aggregate_standard_error = np.sqrt(aggregate_variance)
critical_value = norm.ppf(1 - alpha / 2)
aggregate_ci_lower = max(0.0, aggregate_rate - critical_value * aggregate_standard_error)
aggregate_ci_upper = min(1.0, aggregate_rate + critical_value * aggregate_standard_error)

aggregate_row = pd.DataFrame(
    [
        {
            "stratum": "Aggregate",
            "population_size": population_total,
            "population_weight": 1.0,
            "audit_sample_size": len(audit_df),
            "audited_false_negatives": int(audit_df["expert_rating"].eq("T").sum()),
            "false_negative_rate": aggregate_rate,
            "false_negative_rate_ci_lower": aggregate_ci_lower,
            "false_negative_rate_ci_upper": aggregate_ci_upper,
            "implied_false_negatives": population_total * aggregate_rate,
            "implied_false_negatives_ci_lower": population_total * aggregate_ci_lower,
            "implied_false_negatives_ci_upper": population_total * aggregate_ci_upper,
        }
    ]
)
estimates_df = pd.concat([estimates_df, aggregate_row], ignore_index=True)

#%%
stratum_yaml_keys = {
    "Originally flagged but not validated": "flagged_not_validated",
    "Original score 70--74": "score_70_74",
    "Original score 65--69": "score_65_69",
    "Original score 50--64": "score_50_64",
    "Original score 0--49": "score_0_49",
}
yaml_data = {"strata": {}}
for _, row in estimates_df.iloc[:-1].iterrows():
    yaml_data["strata"][stratum_yaml_keys[row["stratum"]]] = {
        "false_negative_rate_pct": float(row["false_negative_rate"] * 100),
        "implied_false_negatives_int": int(round(row["implied_false_negatives"])),
    }
yaml_data["aggregate"] = {
    "false_negative_rate_pct": aggregate_rate * 100,
    "implied_false_negatives_int": int(round(population_total * aggregate_rate)),
    "population_size_int": population_total,
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(YAML_PATH), exist_ok=True)
estimates_df.to_csv(OUTPUT_PATH, index=False)
with open(YAML_PATH, "w", encoding="utf-8") as yaml_file:
    yaml.safe_dump(yaml_data, yaml_file, sort_keys=False)

#%%

latex_labels = {
    "Originally flagged but not validated": "Flagged, not validated",
    "Original score 70--74": "Original score 70--74",
    "Original score 65--69": "Original score 65--69",
    "Original score 50--64": "Original score 50--64",
    "Original score 0--49": "Original score 0--49",
    "Aggregate": "\\textbf{Aggregate}",
}
latex_rows = []
for _, row in estimates_df.iterrows():
    decimals = 2 if row["stratum"] == "Aggregate" else 1
    rate_with_ci = (
        f'{row["false_negative_rate"] * 100:.{decimals}f}\\% '
        f'[{row["false_negative_rate_ci_lower"] * 100:.{decimals}f}\\%, '
        f'{row["false_negative_rate_ci_upper"] * 100:.{decimals}f}\\%]'
    )
    latex_rows.append(
        f'{latex_labels[row["stratum"]]} & '
        f'{row["population_size"]:,.0f} & '
        f'{row["audit_sample_size"]:,.0f} & {rate_with_ci} & '
        f'{row["implied_false_negatives"]:,.0f} \\\\'
    )

latex_table = "\n".join(
    [
        "\\begin{table}[ht]",
        "    \\centering",
        "    \\caption{False Negative Audit and Estimates}",
        "    \\label{tab:false_negative_audit_strata}",
        "    \\begin{tabularx}{\\textwidth}{Xrrrr}",
        "        \\toprule",
        "        Stratum & Transcripts & Audits & \\shortstack{False negative rate\\\\(95\\% CI)} & \\shortstack{Estimated\\\\false negatives} \\\\",
        "        \\midrule",
        *[f"        {row}" for row in latex_rows[:-1]],
        "        \\midrule",
        f"        {latex_rows[-1]}",
        "        \\bottomrule",
        "    \\end{tabularx}",
        "    \\begin{minipage}{\\textwidth}",
        "        \\vspace{1em}",
        "        \\footnotesize",
        "        \\textit{Notes:} The population consists of transcripts that were not LLM-validated. ``Flagged, not validated'' denotes transcripts with an original score of at least 75 whose average score after validation was below 75. A false negative is a transcript judged by the expert to contain collusive content despite not being LLM-validated. Stratum confidence intervals are Wilson intervals. The aggregate estimate weights strata by their population shares; its confidence interval uses the stratified-sampling variance estimator with finite-population corrections. Estimated counts equal the point estimate multiplied by the number of transcripts in the stratum.",
        "    \\end{minipage}",
        "\\end{table}",
        "",
    ]
)
with open(TEX_PATH, "w", encoding="utf-8") as tex_file:
    tex_file.write(latex_table)

with open(NOTE_PATH, "w", encoding="utf-8") as note_file:
    note_file.write(
        "False-negative rate estimates from the stratified expert audit, produced "
        "by src/post_query/analysis/false_negative_rate_analysis.py. Rates are "
        "reported as proportions. Stratum confidence intervals are 95% Wilson "
        "intervals. The aggregate point estimate uses population stratum weights; "
        "its 95% confidence interval uses the standard stratified-sampling variance "
        "estimator with finite-population corrections and normal critical values. "
        "Implied counts equal the relevant population size multiplied by the rate "
        "estimate or confidence bound. An expert rating of T is treated as a false "
        "negative because the transcript contains collusive content despite not "
        "being LLM-validated.\n"
    )

print(f"\nAggregate false-negative rate: {aggregate_rate:.3%}")
print(
    f"95% CI: [{aggregate_ci_lower:.3%}, {aggregate_ci_upper:.3%}]"
)
print(
    "Implied false negatives: "
    f"{population_total * aggregate_rate:,.1f} "
    f"[{population_total * aggregate_ci_lower:,.1f}, "
    f"{population_total * aggregate_ci_upper:,.1f}]"
)
print(f"Saved estimates: {OUTPUT_PATH}")
print(f"Saved LaTeX table: {TEX_PATH}")
print(f"Saved description: {NOTE_PATH}")
print(f"Saved constants data: {YAML_PATH}")
