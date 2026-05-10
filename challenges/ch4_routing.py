"""
ch4_routing.py - Challenge 4: Emergency Routing using A* with dynamic re-triggering.

A* guarantees shortest path when the heuristic is admissible.
We use scaled Manhattan distance: h(n) = 0.8 * manhattan(n, goal).
This is admissible because the minimum edge cost is 0.8 (residential roads).

When a flood blocks an edge on the current path, we re-run A* from the
team's current position to the next target.
"""

import heapq
import config as cfg


def plan_emergency_route(graph, start, targets):
    """
    Plan a sequential route through all targets using A*.
    Stores the full path in graph.emergency_path.

    Args:
        start: (r, c) starting position of the emergency team
        targets: list of (r, c) civilian positions to reach in order

    Returns:
        full_path: list of (r,c) nodes from start through all targets
    """
    graph.log(f"Ch4: Planning emergency route from {start} through {len(targets)} targets")
    graph.emergency_targets = list(targets)
    graph.emergency_current = start

    # Order targets by nearest-first (greedy)
    ordered_targets = _order_targets_greedy(graph, start, targets)

    full_path = [start]
    current = start

    for target in ordered_targets:
        segment = a_star(graph, current, target)
        if segment and len(segment) > 1:
            full_path.extend(segment[1:])  # skip duplicate start node
            current = target
            graph.log(f"Ch4: Route segment to {target} found ({len(segment)} steps)")
        else:
            graph.log(f"Ch4: WARNING - no path to {target}!")

    graph.emergency_path = full_path
    return full_path


def reroute_from(graph, current_pos, remaining_targets):
    """
    Re-plan the route when a flood event occurs.
    Called dynamically during simulation when an edge on the path is blocked.
    """
    graph.log(f"Ch4: Re-routing from {current_pos} to {len(remaining_targets)} remaining targets")
    graph.emergency_current = current_pos

    ordered = _order_targets_greedy(graph, current_pos, remaining_targets)

    full_path = [current_pos]
    current = current_pos

    for target in ordered:
        segment = a_star(graph, current, target)
        if segment and len(segment) > 1:
            full_path.extend(segment[1:])
            current = target
            graph.log(f"Ch4: Re-routed segment to {target} ({len(segment)} steps)")
        else:
            graph.log(f"Ch4: WARNING - target {target} unreachable after flood!")

    graph.emergency_path = full_path
    return full_path


def a_star(graph, start, goal):
    """
    A* search on the city road network.

    Uses a priority queue ordered by f(n) = g(n) + h(n).
    - g(n): actual cost from start to n (sum of edge costs)
    - h(n): admissible heuristic estimate from n to goal

    Heuristic: 0.8 * Manhattan distance.
    This is admissible because the minimum edge cost in the graph is 0.8
    (residential roads), so h(n) never overestimates the true cost.

    Returns:
        path: list of (r,c) from start to goal, or [] if unreachable.
    """
    if start == goal:
        return [start]

    # Priority queue: (f_score, counter, node)
    # Counter breaks ties to avoid comparing tuples
    open_set = []
    counter = 0
    heapq.heappush(open_set, (_heuristic(start, goal), counter, start))

    # g_score: cheapest cost from start to each node
    g_score = {start: 0.0}

    # came_from: for path reconstruction
    came_from = {}

    # closed set: already fully explored
    closed_set = set()

    while open_set:
        f, _, current = heapq.heappop(open_set)

        if current == goal:
            return _reconstruct_path(came_from, current)

        if current in closed_set:
            continue
        closed_set.add(current)

        for neighbor, edge_cost in graph.road_neighbors(current):
            if neighbor in closed_set:
                continue

            # Apply crime risk multiplier to edge cost
            risk_label = graph.nodes[neighbor].crime_risk
            multiplier = cfg.CRIME_RISK_MULTIPLIER.get(risk_label, 1.0)
            adjusted_cost = edge_cost * multiplier

            tentative_g = g_score[current] + adjusted_cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _heuristic(neighbor, goal)
                counter += 1
                heapq.heappush(open_set, (f_score, counter, neighbor))

    return []  # no path found


def _heuristic(node, goal):
    """
    Admissible heuristic: scaled Manhattan distance.
    Scaled by 0.8 (minimum possible edge cost) to ensure admissibility.
    h(n) = 0.8 * (|row_n - row_goal| + |col_n - col_goal|)
    """
    return 0.8 * (abs(node[0] - goal[0]) + abs(node[1] - goal[1]))


def _reconstruct_path(came_from, current):
    """Walk back through came_from to build the full path."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _order_targets_greedy(graph, start, targets):
    """
    Order targets by nearest-first greedy heuristic.
    For each step, pick the closest unvisited target by Manhattan distance.
    """
    remaining = list(targets)
    ordered = []
    current = start

    while remaining:
        nearest = min(remaining,
                      key=lambda t: abs(t[0] - current[0]) + abs(t[1] - current[1]))
        ordered.append(nearest)
        remaining.remove(nearest)
        current = nearest

    return ordered
