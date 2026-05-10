"""
config.py - All constants, colors, grid settings, and UI dimensions for CityMind.
This is the single place to tweak any global parameter.
"""

# -- Grid Settings ---------------------------------------------─
GRID_ROWS = 12
GRID_COLS = 12
CELL_SIZE = 60         # pixels per cell on screen
CELL_PADDING = 20     # gap between cells
CELL_RADIUS = 10        # rounded corner radius

# -- Zone Counts (what CSP must place) ------------------------─
ZONE_COUNTS = {
    "hospital":       10,
    "ambulance_depot": 5,
    "school":         5,
    "industrial":     5,
    "power_plant":    5,
    # remaining cells  residential
}

# -- Edge Costs ------------------------------------------------─
COST_STANDARD     = 1.0
COST_RESIDENTIAL  = 0.8
COST_BLOCKED      = float("inf")   # flooded / impassable

# -- GA (Challenge 2) ------------------------------------------
GA_POPULATION     = 30
GA_GENERATIONS    = 50
GA_MUTATION_RATE  = 0.05
GA_TOURNAMENT_K   = 3
GA_EARLY_STOP     = 15    # plateau generations before stopping

# -- Simulated Annealing (Challenge 3) ------------------------─
SA_T_INITIAL      = 50.0
SA_T_MIN          = 0.1
SA_COOLING_RATE   = 0.99
NUM_AMBULANCES    = 3

# -- A* (Challenge 4) ------------------------------------------
NUM_CIVILIANS     = 4    # trapped civilians to rescue sequentially

# -- K-Means (Challenge 5) ------------------------------------─
KMEANS_K          = 3
KMEANS_MAX_ITER   = 100
KMEANS_TOL        = 0.001
KNN_K             = 5
CRIME_RISK_MULTIPLIER = {"High": 1.5, "Medium": 1.2, "Low": 1.0}

# -- Simulation ------------------------------------------------─
SIM_STEPS         = 20
FLOOD_CHANCE      = 0.10   # probability per step

# -- Window Layout ---------------------------------------------─
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 520
GRID_AREA_X   = 40                       # left margin for grid
GRID_AREA_Y   = 60                       # top margin for grid
FPS           = 60

# -- Font ------------------------------------------------------─
FONT_NAME     = None   # will try to load Inter; fallback to pygame default
FONT_SIZE_SM  = 22
FONT_SIZE_MD  = 28
FONT_SIZE_LG  = 34
FONT_SIZE_XL  = 44
FONT_SIZE_TITLE = 56
