#%%
"""
LLM Collusion Tagging Analysis - Sector Correlates

This script analyzes collusion tagging behavior by sector (GICS) across three flag variables:
- Creating tables of tag rates by sector for each flag variable
- Generating corresponding figures (PDF + PNG, 1:1 and 16:9) for each flag variable
- Saving sector-specific statistics to YAML
"""

#%%
import config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportion_confint
from pathlib import Path
import yaml

#%%
# Paths
output_dir = Path("data/outputs")
figure_dir = output_dir / "figures"
table_dir = output_dir / "tables"
yaml_dir = Path("data/yaml")
for path in [figure_dir, table_dir, yaml_dir]:
    path.mkdir(parents=True, exist_ok=True)

#%%
def proportion_ci(count, nobs, alpha=0.05):
    low, high = proportion_confint(count, nobs, alpha=alpha, method='wilson')
    return low * 100, high * 100

def save_figure(name, description, fig=None):
    fig = fig or plt.gcf()
    for aspect, size in {"1x1": (6, 6), "16x9": (12, 6.75)}.items():
        fig.set_size_inches(*size)
        path = figure_dir / f"{name}_{aspect}"
        fig.savefig(f"{path}.png", dpi=300)
        fig.savefig(f"{path}.pdf")
    with open(figure_dir / f"{name}.txt", "w") as f:
        f.write(description)
    plt.close(fig)

def save_table(
    df,
    name,
    description,
    latex_column_rename=None,
    escape=True,
    latex_cell_transform=None
):
    csv_path = table_dir / f"{name}.csv"
    tex_path = table_dir / f"{name}.tex"
    df.to_csv(csv_path, index=False)
    if latex_cell_transform:
        latex_df = df.copy()
        for col, fn in latex_cell_transform.items():
            if col in latex_df.columns:
                latex_df[col] = latex_df[col].map(fn)
    else:
        latex_df = df.copy()
    if latex_column_rename:
        latex_df = latex_df.rename(columns=latex_column_rename)
    latex_df.to_latex(
        tex_path,
        index=False,
        float_format="%.2f",
        longtable=True,
        escape=escape
    )
    with open(table_dir / f"{name}.txt", "w") as f:
        f.write(description)

def analyze_flag_by_sector(df, flag_col, flag_name, gics_sectors):
    """Generate sector analysis for a flag variable"""
    # Create descriptive x-axis label based on flag type
    if flag_name == 'llm':
        xlabel = "LLM Flagged as Collusive (%)"
    elif flag_name == 'llm_validation':
        xlabel = "LLM Flagged and Validated as Collusive (%)"
    elif flag_name == 'human_audit':
        xlabel = "LLM Flagged, Validated, and Human Audited as Collusive (%)"
    else:
        xlabel = "Tagged as Collusive (%)"
    
    sector_valid = df[df['gics_sector'].notna()]
    sector_stats = (
        sector_valid.groupby('gics_sector', observed=True)[flag_col]
        .agg(['mean', 'count', 'sum'])
        .rename(columns={'mean': 'tag_pct', 'count': 'n', 'sum': 'num_hits'})
        .reset_index()
    )
    sector_stats['tag_pct'] *= 100
    # Map sector codes to names - convert string sector codes to integers for mapping
    sector_stats['gics_sector_int'] = sector_stats['gics_sector'].astype(int)
    sector_stats['sector_name'] = sector_stats['gics_sector_int'].map(gics_sectors)
    sector_stats[['ci_low', 'ci_high']] = sector_stats.apply(
        lambda r: proportion_ci(r['num_hits'], r['n']), axis=1, result_type='expand'
    )
    # Sort from most to least collusive
    sector_sorted = sector_stats.sort_values("tag_pct", ascending=False)
    save_table(
        sector_sorted[['sector_name', 'tag_pct', 'ci_low', 'ci_high', 'n']],
        f"sector_tag_rates_{flag_name}",
        f"{flag_name} tagging rate by sector with 95% CI. Produced by correlates_sectors.py"
    )
    
    fig, ax = plt.subplots()
    # Calculate error bars, ensuring they're non-negative
    xerr_low = np.maximum(0, sector_sorted['tag_pct'] - sector_sorted['ci_low'])
    xerr_high = np.maximum(0, sector_sorted['ci_high'] - sector_sorted['tag_pct'])
    ax.barh(
        y=np.arange(len(sector_sorted)),
        width=sector_sorted['tag_pct'],
        xerr=[xerr_low, xerr_high],
        capsize=4, color='skyblue'
    )
    # Add vertical line for sample average
    sector_sample_avg = sector_valid[flag_col].mean() * 100
    ax.axvline(x=sector_sample_avg, color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax.set_yticks(np.arange(len(sector_sorted)))
    ax.set_yticklabels(sector_sorted['sector_name'])
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, None)
    plt.tight_layout()
    save_figure(f"sector_tag_rates_{flag_name}", f"{flag_name} tag rate by sector (horizontal bar chart). Produced by correlates_sectors.py", fig)
    
    return len(sector_valid), float(sector_valid[flag_col].mean() * 100)

#%%
# Load and prepare data
data_path = Path("data/datasets/main_analysis_dataset.feather")
df = pd.read_feather(data_path)

# Create clean flag variables (treat NAs as False)
df['llm_flag_clean'] = df['llm_flag']  # Already clean
df['llm_validation_flag_clean'] = df['llm_validation_flag'].fillna(False).astype(bool)
df['human_audit_flag_clean'] = df['human_audit_flag'].fillna(False).astype(bool)

# Load GICS sector mapping
with open(Path("assets/gics_sectors.yaml"), "r") as f:
    gics_sectors = yaml.safe_load(f)

#%%
# Define flag variables to analyze
flag_configs = [
    {'col': 'llm_flag_clean', 'name': 'llm', 'display_name': 'LLM'},
    {'col': 'llm_validation_flag_clean', 'name': 'llm_validation', 'display_name': 'LLM Validation'},
    {'col': 'human_audit_flag_clean', 'name': 'human_audit', 'display_name': 'Human Audit'}
]

#%%
# Sector analysis for each flag variable
sector_stats = {}

for flag_config in flag_configs:
    col = flag_config['col']
    name = flag_config['name']
    display_name = flag_config['display_name']
    
    print(f"\nAnalyzing {display_name} flag by sector ({col})...")
    
    n_sector, tag_rate = analyze_flag_by_sector(df, col, name, gics_sectors)
    sector_stats[f'sector_valid_{name}_tag_rate'] = float(tag_rate)
    sector_stats[f'sector_valid_observations'] = int(n_sector)
    
    print(f"Completed sector analysis for {display_name} flag")

# Add sector statistics to YAML
yaml_path = yaml_dir / "correlates_collusive_communication.yaml"
if yaml_path.exists():
    with open(yaml_path, "r") as f:
        existing_stats = yaml.safe_load(f) or {}
else:
    existing_stats = {}

# Merge sector stats
existing_stats.update(sector_stats)

# Save updated YAML
with open(yaml_path, "w") as f:
    yaml.dump(existing_stats, f)

print(f"\nSaved sector statistics to {yaml_path}")
print("\n" + "="*60)
print("Completed sector analysis")
print("="*60)
