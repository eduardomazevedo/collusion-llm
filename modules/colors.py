"""
Color palette for figure generation.

This module defines the Ghibli-inspired color palette to be used consistently
across all figure generation scripts in the project.
"""

# Ghibli color palette as specified in AGENTS.md
# Deep teal and warm red are the first two colors to be used
GHIBLI_PALETTE = {
    "deep_teal": "#3b6978",      # Deep Teal (blue-gray tone)
    "warm_red": "#f28482",       # Warm Red (muted red-orange)
    "red": "#FF5C5C",            # Kiki's Delivery Red (strong red)
    "cream": "#f9f5e3",          # Soft Cream (lightest background)
    "light_gray": "#DADADA",     # Whispering Wind (light gray)
    "gray": "#6C7A8E",           # Totoro Gray (darker gray)
    "blue": "#8FB1E9",           # Castle Sky (soft blue)
    "green": "#A6D784",          # Spirited Meadow (soft green)
    "muted_green": "#84a59d",    # Muted Green (gray-green tone)
    "gold": "#FFD700",           # Howl's Moving Castle Gold (strong yellow)
}

# List format for easy iteration (in order of priority)
GHIBLI_COLORS = [
    GHIBLI_PALETTE["deep_teal"],
    GHIBLI_PALETTE["warm_red"],
    GHIBLI_PALETTE["red"],
    GHIBLI_PALETTE["blue"],
    GHIBLI_PALETTE["green"],
    GHIBLI_PALETTE["muted_green"],
    GHIBLI_PALETTE["gray"],
    GHIBLI_PALETTE["gold"],
    GHIBLI_PALETTE["cream"],
    GHIBLI_PALETTE["light_gray"],
]