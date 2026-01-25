"""
Create airline capacity figure for the case study.

Input:
- data/datasets/ask_airline_year.csv

Outputs:
- data/outputs/figures/ask_by_airline_2011_2016_1x1.(png|pdf)
- data/outputs/figures/ask_by_airline_2011_2016_16x9.(png|pdf)
- data/outputs/figures/ask_by_airline_2011_2016.txt
"""

#%%
import os

import pandas as pd
import matplotlib.pyplot as plt

import config
from modules.colors import GHIBLI_COLORS, apply_ghibli_theme

#%%
# Apply Ghibli theme
apply_ghibli_theme()

#%%
# Paths
DATA_PATH = os.path.join(config.DATA_DIR, "datasets", "ask_airline_year.csv")
FIG_DIR = os.path.join(config.DATA_DIR, "outputs", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

FIG_NAME = "ask_by_airline_2011_2016"

#%%
# Load data
print(f"Loading data from {DATA_PATH}...")
df = pd.read_csv(DATA_PATH)
print(f"Rows: {len(df):,}")

#%%
# Prepare data
df_plot = df.dropna(subset=["empresa_sigla", "ano", "ask_billion"]).copy()
df_plot = df_plot.sort_values(["empresa_sigla", "ano"])

airline_labels = {
    "AZU": "Azul",
    "GLO": "GOL",
    "ONE": "Avianca",
    "TAM": "LATAM"
}
airline_order = ["GLO", "TAM", "ONE", "AZU"]
color_map = {
    code: GHIBLI_COLORS[i % len(GHIBLI_COLORS)]
    for i, code in enumerate(airline_order)
}

#%%
# Plot
fig, ax = plt.subplots()
for airline in airline_order:
    g = df_plot[df_plot["empresa_sigla"].eq(airline)]
    if g.empty:
        print(f"Warning: no data for airline {airline}")
        continue
    ax.plot(
        g["ano"],
        g["ask_billion"],
        label=airline_labels.get(airline, airline),
        color=color_map[airline],
        marker="o"
    )

ax.set_xlabel("Year")
ax.set_ylabel("Available seat kilometers (billions)")
ax.legend(frameon=False)
fig.tight_layout()

#%%
# Save figures
for aspect, size in {"1x1": (6, 6), "16x9": (12, 6.75)}.items():
    fig.set_size_inches(*size)
    png_path = os.path.join(FIG_DIR, f"{FIG_NAME}_{aspect}.png")
    pdf_path = os.path.join(FIG_DIR, f"{FIG_NAME}_{aspect}.pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")

txt_path = os.path.join(FIG_DIR, f"{FIG_NAME}.txt")
with open(txt_path, "w") as f:
    f.write(
        "Line chart of available seat kilometers (ASK) by airline for 2011-2016 "
        "using ANAC domestic regular flights. Produced by "
        "src/post_query/analysis/case_airlines_capacities_analysis.py."
    )
print(f"Wrote {txt_path}")

plt.close(fig)
