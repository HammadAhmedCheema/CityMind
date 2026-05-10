"""
ch3_ambulance.py - Challenge 3: Ambulance Placement using Simulated Annealing.

Objective: place N ambulances to minimize the worst-case response time
(minimax: minimize the maximum BFS distance from any citizen to the
nearest ambulance).
"""

import random
import math
from collections import deque
import config as cfg


def place_ambulances(graph):
    """
    Use Simulated Annealing to find optimal ambulance positions.
    Updates graph.ambulances in-place.
    """
    graph.log(f"Ch3: Starting Simulated Annealing for {cfg.NUM_AMBULANCES} ambulances")

    # Get all valid positions (cells with roads - reachable)
    all_positions = list(graph.nodes.keys())
    # Filter to positions that have at least one road neighbor
    valid_positions = [p for p in all_positions if len(graph.road_neighbors(p)) > 0]

    if len(valid_positions) < cfg.NUM_AMBULANCES:
        graph.log("Ch3: Not enough valid positions for ambulances")
        graph.ambulances = valid_positions[:cfg.NUM_AMBULANCES]
        return

    # Precompute BFS distances from every valid node to every other (all-pairs shortest path)
    # This is a one-time cost that makes SA iterations incredibly fast
    citizen_positions = [p for p in all_positions
                        if graph.nodes[p].location_type == "residential"]

    dist_cache = _precompute_distances(graph, valid_positions)

    # Filter out citizens who are unreachable from all potential ambulance spots
    reachable_citizens = []
    stranded_count = 0
    for c_pos in citizen_positions:
        # A citizen is reachable if there's a path to AT LEAST ONE valid road node
        if any((c_pos, a_pos) in dist_cache for a_pos in valid_positions):
            reachable_citizens.append(c_pos)
        else:
            stranded_count += 1
            
    if stranded_count > 0:
        graph.log(f"Ch3: WARNING - {stranded_count} residential nodes are stranded (disconnected from road network)")

    # Initial random placement
    current_state = random.sample(valid_positions, cfg.NUM_AMBULANCES)
    current_cost = _evaluate_placement(current_state, reachable_citizens, dist_cache)

    best_state = current_state[:]
    best_cost = current_cost

    temperature = cfg.SA_T_INITIAL
    iteration = 0

    while temperature > cfg.SA_T_MIN:
        # Generate neighbor: move one random ambulance to an adjacent cell
        neighbor_state = _get_neighbor(graph, current_state, valid_positions)
        neighbor_cost = _evaluate_placement(neighbor_state, reachable_citizens, dist_cache)

        # Acceptance criterion
        delta = neighbor_cost - current_cost

        if delta < 0:
            # Better solution - always accept
            current_state = neighbor_state
            current_cost = neighbor_cost
        else:
            # Worse solution - accept with probability exp(-delta/T)
            acceptance_prob = math.exp(-delta / temperature)
            if random.random() < acceptance_prob:
                current_state = neighbor_state
                current_cost = neighbor_cost

        # Track global best
        if current_cost < best_cost:
            best_cost = current_cost
            best_state = current_state[:]

        # Cool down
        temperature *= cfg.SA_COOLING_RATE
        iteration += 1

    graph.ambulances = best_state
    
    # Identify the specific farthest node for verification (among reachable ones)
    farthest_citizen = None
    max_dist = -1
    for c_pos in reachable_citizens:
        min_d = min(dist_cache.get((c_pos, amb_pos), 9999) for amb_pos in best_state)
        if min_d > max_dist:
            max_dist = min_d
            farthest_citizen = c_pos

    graph.log(f"Ch3: Worst-case response distance: {best_cost} hops")
    graph.log(f"Ch3: Farthest citizen @ {farthest_citizen}")
    graph.log(f"Ch3: Ambulances placed at {best_state} (iterations: {iteration})")


def _evaluate_placement(ambulance_positions, citizen_positions, dist_cache):
    """
    Minimax objective: compute the maximum of the minimum BFS distance
    from each citizen to the nearest ambulance.
    Lower is better.
    """
    max_min_dist = 0

    for citizen_pos in citizen_positions:
        min_dist = float("inf")
        for amb_pos in ambulance_positions:
            dist = dist_cache.get((citizen_pos, amb_pos), 9999)
            if dist < min_dist:
                min_dist = dist
        if min_dist > max_min_dist:
            max_min_dist = min_dist

    return max_min_dist


def _precompute_distances(graph, valid_positions):
    """Precompute all-pairs shortest paths using BFS."""
    cache = {}
    for start in valid_positions:
        visited = {start: 0}
        queue = deque([(start, 0)])
        while queue:
            current, dist = queue.popleft()
            for nb, _cost in graph.road_neighbors(current):
                if nb not in visited:
                    visited[nb] = dist + 1
                    queue.append((nb, dist + 1))
        
        for goal in valid_positions:
            cache[(start, goal)] = visited.get(goal, 9999)
            
    return cache


def _get_neighbor(graph, current_state, valid_positions):
    """
    Generate a neighbor state by moving one randomly chosen ambulance
    to an adjacent valid cell.
    """
    new_state = current_state[:]
    idx = random.randint(0, len(new_state) - 1)

    # Get adjacent cells of the chosen ambulance
    current_pos = new_state[idx]
    adj_cells = [nb for nb, _cost in graph.road_neighbors(current_pos)]

    if adj_cells:
        # Move to a random adjacent cell (that isn't already occupied by another ambulance)
        available = [c for c in adj_cells if c not in new_state]
        if available:
            new_state[idx] = random.choice(available)
        else:
            # All adjacent cells occupied - pick a random valid position
            new_state[idx] = random.choice(valid_positions)
    else:
        new_state[idx] = random.choice(valid_positions)

    return new_state
