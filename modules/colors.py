"""
Color palette for figure generation.

This module defines the Ghibli-inspired color palette to be used consistently
across all figure generation scripts in the project.
"""

import matplotlib.pyplot as plt

# --- 1. DEFINITIONS ---

# The full Ghibli palette
ghibli_palette = {
    "deep_teal": "#3b6978",   # Deep Teal (blue-gray tone)
    "warm_red": "#f28482",    # Warm Red (muted red-orange)
    "red": "#FF5C5C",         # Kiki's Delivery Red (strong red)
    "cream": "#f9f5e3",       # Soft Cream (lightest background)
    "light_gray": "#DADADA",  # Whispering Wind (light gray)
    "gray": "#6C7A8E",        # Totoro Gray (darker gray)
    "blue": "#8FB1E9",        # Castle Sky (soft blue)
    "green": "#A6D784",       # Spirited Meadow (soft green)
    "muted_green": "#84a59d", # Muted Green (gray-green tone)
    "gold": "#FFD700",        # Howl's Moving Castle Gold (strong yellow)
}

# Standard categorical sequence (User pref: Teal, then Red, then Gold)
# This sequence ensures high contrast between adjacent categories.
GHIBLI_COLORS = [
    ghibli_palette["deep_teal"],  # 1. Primary Category
    ghibli_palette["red"],        # 2. Secondary Category
    ghibli_palette["gold"],       # 3. Highlight/Contrast
    ghibli_palette["blue"],       # 4. Cool tone
    ghibli_palette["green"],      # 5. Nature tone
    ghibli_palette["gray"]        # 6. Neutral
]

# Standard Styles
# "Plain black for basic things like error bars and annotation lines"
STYLE_CONFIG = {
    "error_color": "black",
    "line_color": "black",
    "text_color": "black",
    "grid_color": ghibli_palette["light_gray"],
    "background_color": "white",  # Standard scientific paper background
    "default_alpha": 0.8,  # Default alpha for bars/histograms
    "line_alpha": 0.7,  # Default alpha for reference lines
    "edge_color": "black",  # Border color for bars/histograms (must be set explicitly in calls)
    "edge_width": 0.5  # Border width for bars/histograms (must be set explicitly in calls)
}

# --- 2. PLOTTING FUNCTION ---

def apply_ghibli_theme():
    """Applies the Ghibli theme to the current matplotlib environment.
    
    This sets up the Ghibli color palette, grid styling, and ensures that
    grid lines appear behind plot elements (bars, histograms, etc.) for
    a cleaner appearance. All styling is centralized here to ensure consistency.
    """
    plt.rcParams.update({
        'axes.prop_cycle': plt.cycler(color=GHIBLI_COLORS),
        'axes.grid': True,
        'axes.axisbelow': True,  # Put grid and axes behind plot elements
        'grid.color': STYLE_CONFIG["grid_color"],
        'grid.linestyle': '-',
        'grid.linewidth': 0.8,
        'grid.alpha': 0.5,
        'lines.linewidth': 2,
        'errorbar.capsize': 4,  # Default capsize for error bars
        'figure.facecolor': STYLE_CONFIG["background_color"],
        'axes.facecolor': STYLE_CONFIG["background_color"],
        'text.color': STYLE_CONFIG["text_color"],
        'axes.labelcolor': STYLE_CONFIG["text_color"],
        'xtick.color': STYLE_CONFIG["text_color"],
        'ytick.color': STYLE_CONFIG["text_color"],
        'font.size': 11,  # Default font size
        'font.family': 'sans-serif'  # Default font family
    })


def ensure_grid_behind(ax):
    """Ensure grid appears behind plot elements for a specific axes object.
    
    This is useful if you need to explicitly set grid behind for an axes
    that was created before apply_ghibli_theme() was called, or to
    ensure it's set for a specific axes.
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes object to configure
    """
    ax.set_axisbelow(True)

# For backward compatibility, export the palette with the old name
GHIBLI_PALETTE = ghibli_palette
