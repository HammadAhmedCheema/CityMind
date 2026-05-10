"""
city_graph.py - The shared city graph: single source of truth for the entire system.
Every module reads and writes to the same CityGraph instance.
"""

from collections import deque
import config as cfg


class NodeData:
    """Stores all attributes for a single grid cell."""

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.location_type = "empty"          # residential, hospital, school, industrial, power_plant, ambulance_depot, empty
        self.population_density = 0.0         # 0.0–1.0 (normalized)
        self.risk_index = 0.0                 # updated by crime prediction
        self.accessible = True                # False if flooded
        self.crime_risk = "Low"               # High / Medium / Low

    def __repr__(self):
        return f"Node({self.row},{self.col} | {self.location_type})"


class CityGraph:
    """
    Grid-based graph.  Nodes are (row, col) tuples.
    Edges connect 4-neighbors (up, down, left, right).
    Edge cost = float('inf') means no road / blocked.
    """

    def __init__(self, rows=None, cols=None):
        self.rows = rows or cfg.GRID_ROWS
        self.cols = cols or cfg.GRID_COLS
        self.reset()

    def reset(self):
        """Reset the graph to a blank slate for re-initialization."""
        # Create all nodes
        self.nodes = {}
        for r in range(self.rows):
            for c in range(self.cols):
                self.nodes[(r, c)] = NodeData(r, c)

        # Edges: keyed by frozenset so (a,b) == (b,a)
        # Store as dict: frozenset({pos_a, pos_b}) -> cost
        self.edges = {}

        # Ambulance positions (set by Challenge 3)
        self.ambulances = []

        # Emergency path (set by Challenge 4) - list of (r,c) for visualization
        self.emergency_path = []
        self.emergency_targets = []       # civilian positions
        self.emergency_current = None     # current team position

        # Live event log - list of strings
        self.event_log = []

        # Flooded edges for visual tracking
        self.flooded_edges = set()

    # -- Edge helpers ------------------------------------------─

    def _edge_key(self, a, b):
        """Canonical edge key so (a,b) and (b,a) map to the same entry."""
        return (min(a, b), max(a, b))

    def set_edge(self, a, b, cost):
        """Set the cost of the edge between nodes a and b."""
        self.edges[self._edge_key(a, b)] = cost

    def get_edge_cost(self, a, b):
        """Return edge cost, or inf if no road exists."""
        return self.edges.get(self._edge_key(a, b), float("inf"))

    def has_road(self, a, b):
        """True if a traversable road exists between a and b."""
        return self.get_edge_cost(a, b) < float("inf")

    def block_edge(self, a, b):
        """Block (flood) an edge - set cost to infinity."""
        self.set_edge(a, b, cfg.COST_BLOCKED)
        self.flooded_edges.add(self._edge_key(a, b))

    def unblock_edge(self, a, b):
        """Restore a flooded edge to its default cost."""
        key = self._edge_key(a, b)
        # Determine default cost based on node types
        cost = self._default_edge_cost(a, b)
        self.edges[key] = cost
        self.flooded_edges.discard(key)

    def _default_edge_cost(self, a, b):
        """Calculate default edge cost based on adjacent node types."""
        type_a = self.nodes[a].location_type
        type_b = self.nodes[b].location_type
        if type_a == "residential" or type_b == "residential":
            return cfg.COST_RESIDENTIAL
        return cfg.COST_STANDARD

    # -- Neighbor helpers ---------------------------------------

    def grid_neighbors(self, pos):
        """Return 4-directional neighbors within grid bounds (ignoring roads)."""
        r, c = pos
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                neighbors.append((nr, nc))
        return neighbors

    def road_neighbors(self, pos):
        """Return neighbors reachable via actual roads (cost < inf)."""
        result = []
        for nb in self.grid_neighbors(pos):
            cost = self.get_edge_cost(pos, nb)
            if cost < float("inf"):
                result.append((nb, cost))
        return result

    # -- Pathfinding helpers ------------------------------------

    def bfs_shortest_path(self, start, goal):
        """
        Simple BFS to find shortest path (by hop count) on road network.
        Returns list of nodes from start to goal, or [] if unreachable.
        """
        if start == goal:
            return [start]

        visited = {start}
        queue = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            for nb, _cost in self.road_neighbors(current):
                if nb in visited:
                    continue
                visited.add(nb)
                new_path = path + [nb]
                if nb == goal:
                    return new_path
                queue.append((nb, new_path))
        return []

    def bfs_distance(self, start, goal):
        """BFS hop distance on road network.  Returns int or float('inf')."""
        path = self.bfs_shortest_path(start, goal)
        return len(path) - 1 if path else float("inf")

    def bfs_reachable(self, start):
        """Return set of all nodes reachable from start via roads."""
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for nb, _ in self.road_neighbors(current):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        return visited

    def all_possible_edges(self):
        """Return list of all possible edges in the grid (4-connected)."""
        edges = []
        for r in range(self.rows):
            for c in range(self.cols):
                if c + 1 < self.cols:
                    edges.append(((r, c), (r, c + 1)))
                if r + 1 < self.rows:
                    edges.append(((r, c), (r + 1, c)))
        return edges

    # -- Logging ------------------------------------------------

    def log(self, message):
        """Append a timestamped message to the event log and print to terminal."""
        self.event_log.append(message)
        print(message)

    # -- State queries ------------------------------------------

    def get_nodes_by_type(self, location_type):
        """Return list of (r,c) positions matching the given type."""
        return [pos for pos, node in self.nodes.items()
                if node.location_type == location_type]

    def get_all_built_roads(self):
        """Return list of (pos_a, pos_b) for all built (non-inf) roads."""
        roads = []
        for key, cost in self.edges.items():
            if cost < float("inf"):
                roads.append(key)
        return roads
