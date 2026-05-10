"""
colors.py - Color palettes, gradients, and visual constants for the CityMind UI.
All colors are RGB tuples for Pygame.
"""

# -- Dark Theme Background ------------------------------------─
BG_DARK       = (26, 26, 46)       # #1a1a2e - main background
BG_PANEL      = (22, 33, 62)       # #16213e - sidebar panel
BG_CELL       = (45, 45, 68)       # #2d2d44 - empty cell
BG_HEADER     = (15, 22, 46)       # #0f162e - header bar

# -- Zone Colors ------------------------------------------------
ZONE_COLORS = {
    "residential":     (59, 130, 246),     # #3b82f6 - solid blue
    "hospital":        (225, 29, 72),      # #e11d48 - solid red/crimson
    "school":          (234, 179, 8),      # #eab308 - solid yellow/ochre
    "industrial":      (82, 82, 91),       # #52525b - solid dark gray
    "power_plant":     (194, 65, 12),      # #c2410c - solid rust/orange
    "ambulance_depot": (22, 163, 74),      # #16a34a - solid medium green
    "empty":           (45, 45, 68),       # #2d2d44 - dark
}

# -- Dimmed versions (for non-active overlays) ------------------
ZONE_COLORS_DIM = {
    k: (v[0] // 3, v[1] // 3, v[2] // 3)
    for k, v in ZONE_COLORS.items()
}

# -- Road Colors ------------------------------------------------
ROAD_COLOR        = (200, 200, 220)    # light gray
ROAD_COLOR_GLOW   = (255, 255, 255)    # white glow
ROAD_FLOODED      = (30, 144, 255)     # dodger blue

# -- Ambulance Colors ------------------------------------------
AMBULANCE_COLOR   = (225, 29, 72)      # solid crimson
AMBULANCE_GLOW    = (244, 63, 94)      # slightly lighter crimson

# -- Emergency Path ---------------------------------------------
PATH_COLOR        = (34, 197, 94)      # solid green
PATH_GLOW         = (74, 222, 128)

# -- Heatmap Gradient (crime risk) ------------------------------
HEATMAP_LOW    = (34, 197, 94)         # solid green
HEATMAP_MED    = (234, 179, 8)         # solid yellow
HEATMAP_HIGH   = (225, 29, 72)         # solid crimson

# -- UI Chrome --------------------------------------------------
TEXT_PRIMARY   = (230, 230, 245)       # near-white
TEXT_SECONDARY = (160, 160, 190)       # muted
TEXT_ACCENT    = (114, 137, 218)       # discord-blue accent
TEXT_SUCCESS   = (34, 197, 94)
TEXT_WARNING   = (234, 179, 8)
TEXT_DANGER    = (225, 29, 72)

BUTTON_BG      = (55, 55, 85)
BUTTON_HOVER   = (75, 75, 110)
BUTTON_ACTIVE  = (114, 137, 218)
BUTTON_TEXT    = (230, 230, 245)

TOGGLE_ON      = (114, 137, 218)
TOGGLE_OFF     = (70, 70, 100)
TOGGLE_KNOB    = (230, 230, 245)

DIVIDER        = (60, 60, 90)

# -- Civilian marker ------------------------------------------─
CIVILIAN_COLOR   = (255, 220, 50)      # yellow
CIVILIAN_REACHED = (100, 100, 100)     # gray

# -- Shadows ---------------------------------------------------─
SHADOW_COLOR   = (10, 10, 20, 120)     # semi-transparent black


def lerp_color(color_a, color_b, t):
    """Linearly interpolate between two RGB colors. t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


def risk_to_color(risk_value):
    """Map a risk value (0.0–1.0) to a heatmap color (green  yellow  red)."""
    if risk_value < 0.5:
        return lerp_color(HEATMAP_LOW, HEATMAP_MED, risk_value * 2)
    else:
        return lerp_color(HEATMAP_MED, HEATMAP_HIGH, (risk_value - 0.5) * 2)
