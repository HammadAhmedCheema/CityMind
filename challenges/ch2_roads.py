"""
ch2_roads.py - Challenge 2: Road Network Optimization using Genetic Algorithm.

Chromosome: binary array (1=road built, 0=not built) for each possible grid edge.
Fitness: minimize total cost, penalize disconnected graphs, penalize missing
         two independent paths between hospital and ambulance depot.
"""

import random
from collections import deque
import config as cfg


def optimize_roads(graph):
    """
    Run the Genetic Algorithm to find the optimal road network.
    Updates graph edges in-place with the best solution found.
    """
    possible_edges = graph.all_possible_edges()
    num_edges = len(possible_edges)

    graph.log(f"Ch2: Starting GA road optimization ({num_edges} possible edges)")

    # Get hospital and depot positions for two-path constraint
    hospitals = graph.get_nodes_by_type("hospital")
    depots = graph.get_nodes_by_type("ambulance_depot")

    if not hospitals or not depots:
        graph.log("Ch2: ERROR - no hospital or depot found. Skipping.")
        return

    # Find the farthest pair where NEITHER is a corner (corners are 2-neighbor nodes)
    # This makes the two-path constraint more testable and robust.
    best_pair = None
    best_dist = -1
    
    for h in hospitals:
        if len(graph.grid_neighbors(h)) <= 2: continue # skip corners
        for d in depots:
            if len(graph.grid_neighbors(d)) <= 2: continue # skip corners
            dist = abs(h[0]-d[0]) + abs(h[1]-d[1])
            if dist > best_dist:
                best_dist = dist
                best_pair = (h, d)

    # Fallback: allow one edge node, but never corners
    if not best_pair:
        for h in hospitals:
            if len(graph.grid_neighbors(h)) <= 2: continue
            for d in depots:
                dist = abs(h[0]-d[0]) + abs(h[1]-d[1])
                if dist > best_dist:
                    best_dist = dist
                    best_pair = (h, d)

    # Last resort fallback
    if not best_pair:
        best_pair = (hospitals[0], depots[0])
        best_dist = abs(best_pair[0][0]-best_pair[1][0]) + abs(best_pair[0][1]-best_pair[1][1])
    
    primary_hospital, primary_depot = best_pair
    graph.log(f"Ch2: PRIMARY_HOSPITAL @ {primary_hospital}")
    graph.log(f"Ch2: PRIMARY_DEPOT @ {primary_depot} (Distance: {best_dist} hops)")

    # Precompute values used in every fitness evaluation (avoid repeated work)
    all_positions = set((r, c) for r in range(graph.rows) for c in range(graph.cols))
    total_positions = len(all_positions)

    # Precompute edge costs for each possible edge index
    edge_costs = []
    for a, b in possible_edges:
        type_a = graph.nodes[a].location_type
        type_b = graph.nodes[b].location_type
        cost = cfg.COST_RESIDENTIAL if (type_a == "residential" or type_b == "residential") else cfg.COST_STANDARD
        edge_costs.append(cost)

    # --- GA Parameters ---
    MAX_RETRIES = 3
    has_two_paths = False
    
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            graph.log(f"Ch2: Retry {attempt}/{MAX_RETRIES-1} - Increasing population to {cfg.GA_POPULATION}")

        # Initialize population
        population = []
        for i in range(cfg.GA_POPULATION):
            if i < cfg.GA_POPULATION // 2:
                population.append(_seeded_chromosome(num_edges))
            else:
                population.append(_random_chromosome(num_edges))

        best_fitness = float("-inf")
        best_chromosome = None
        stale_count = 0

        for gen in range(cfg.GA_GENERATIONS):
            fitness_scores = []
            for chromo in population:
                f = _fitness(chromo, possible_edges, edge_costs,
                             all_positions, total_positions,
                             primary_hospital, primary_depot)
                fitness_scores.append(f)

            gen_best_idx = max(range(len(fitness_scores)), key=lambda i: fitness_scores[i])
            gen_best_fitness = fitness_scores[gen_best_idx]

            if gen_best_fitness > best_fitness:
                best_fitness = gen_best_fitness
                best_chromosome = population[gen_best_idx][:]
                stale_count = 0
            else:
                stale_count += 1

            if gen % 20 == 0:
                graph.log(f"  Attempt {attempt}, Gen {gen}: Best Fitness = {gen_best_fitness:.1f}")

            if stale_count >= cfg.GA_EARLY_STOP:
                break

            # Next generation
            new_population = [best_chromosome[:]]
            while len(new_population) < cfg.GA_POPULATION:
                parent_a = _tournament_select(population, fitness_scores)
                parent_b = _tournament_select(population, fitness_scores)
                child = _mutate(_crossover(parent_a, parent_b))
                new_population.append(child)
            population = new_population

        # Apply and verify
        if best_chromosome:
            _apply_chromosome(graph, best_chromosome, possible_edges)
            has_two_paths = verify_2_edge_connectivity(graph, primary_hospital, primary_depot)
            
            if has_two_paths:
                break
            else:
                graph.log(f"Ch2: Attempt {attempt} failed redundancy check (Fitness: {best_fitness:.1f}).")
                cfg.GA_POPULATION += 10
        else:
            graph.log(f"Ch2: Attempt {attempt} failed to find solution.")
            cfg.GA_POPULATION += 10

    # Final reporting
    if best_chromosome:
        total_roads = sum(best_chromosome)
        total_cost = sum(edge_costs[i] for i, gene in enumerate(best_chromosome) if gene == 1)
        
        graph.log(f"Ch2: 2-edge-connectivity {primary_hospital} <-> {primary_depot}: {'PASS' if has_two_paths else 'FAIL'}")
        
        if not has_two_paths:
            graph.log("Ch2: CRITICAL - Could not satisfy two-path constraint after retries.")
            graph.log("Ch2: Building all roads as emergency fallback to ensure connectivity.")
            for a, b in possible_edges:
                graph.set_edge(a, b, graph._default_edge_cost(a, b))
            total_roads = len(possible_edges)
            total_cost = sum(edge_costs)

        graph.log(f"Ch2: Final GA Results:")
        graph.log(f"  - Total Roads: {total_roads}")
        graph.log(f"  - Total Road Cost: {total_cost:.1f}")
        graph.log(f"  - Best Fitness: {best_fitness:.1f}")
    else:
        graph.log("Ch2: GA CRITICAL FAILURE - No chromosome found. Building all roads.")
        for a, b in possible_edges:
            graph.set_edge(a, b, graph._default_edge_cost(a, b))


def _random_chromosome(length):
    """Generate a random binary chromosome with ~40% roads built."""
    return [1 if random.random() < 0.4 else 0 for _ in range(length)]


def _seeded_chromosome(length):
    """
    Start with ALL roads built, then randomly remove ~30%.
    This ensures the initial solution is likely connected, so
    the GA can focus on cost optimization instead of discovering connectivity.
    """
    chromo = [1] * length
    for i in range(length):
        if random.random() < 0.30:
            chromo[i] = 0
    return chromo


def _fitness(chromosome, possible_edges, edge_costs,
             all_positions, total_positions,
             hospital_pos, depot_pos):
    """
    Evaluate a chromosome's fitness.
    Higher = better.  Penalties are large negatives.
    Uses Union-Find for O(n·α(n)) connectivity check instead of BFS.
    """
    # Union-Find for fast connectivity
    parent = {}
    rank = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1

    # Initialize Union-Find for all positions
    for pos in all_positions:
        parent[pos] = pos
        rank[pos] = 0

    # Build temporary adjacency AND union-find simultaneously
    adj = {}
    total_cost = 0.0

    for i, gene in enumerate(chromosome):
        if gene == 1:
            a, b = possible_edges[i]
            total_cost += edge_costs[i]
            union(a, b)

            if a not in adj:
                adj[a] = []
            if b not in adj:
                adj[b] = []
            adj[a].append(b)
            adj[b].append(a)

    # Penalty 1: Disconnected graph (Union-Find: count unique roots)
    hospital_root = find(hospital_pos)
    disconnected_count = sum(1 for pos in all_positions if find(pos) != hospital_root)
    disconnect_penalty = -100 * disconnected_count

    # Penalty 2: Two independent paths (only check if graph is connected)
    two_path_penalty = 0
    if disconnected_count == 0:
        if not _has_two_edge_disjoint_paths(hospital_pos, depot_pos, adj,
                                            possible_edges, chromosome):
            two_path_penalty = -2000
    else:
        two_path_penalty = -2000  # definitely no two paths if disconnected

    fitness = -total_cost + disconnect_penalty + two_path_penalty
    return fitness


def _bfs_reachable_temp(start, adj):
    """BFS on temporary adjacency dict. Returns set of reachable nodes."""
    if start not in adj:
        return {start}
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nb in adj.get(node, []):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited


def _bfs_path_temp(start, goal, adj):
    """BFS shortest path on temporary adjacency. Returns path list or []."""
    if start == goal:
        return [start]
    if start not in adj:
        return []
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for nb in adj.get(node, []):
            if nb not in visited:
                visited.add(nb)
                new_path = path + [nb]
                if nb == goal:
                    return new_path
                queue.append((nb, new_path))
    return []


def verify_2_edge_connectivity(graph, start, goal):
    """
    Public verification function for 2-edge connectivity on the actual graph.
    Used for final reporting.
    """
    # 1. Find first path via road network
    path1 = graph.bfs_shortest_path(start, goal)
    if not path1:
        return False

    # 2. Block edges of path1 temporarily
    blocked_edges = []
    for i in range(len(path1) - 1):
        a, b = path1[i], path1[i + 1]
        cost = graph.get_edge_cost(a, b)
        blocked_edges.append((a, b, cost))
        graph.set_edge(a, b, float('inf'))

    # 3. Check for second path
    path2 = graph.bfs_shortest_path(start, goal)

    # 4. Restore edges
    for a, b, cost in blocked_edges:
        graph.set_edge(a, b, cost)

    return len(path2) > 0


def _has_two_edge_disjoint_paths(start, goal, adj, possible_edges, chromosome):
    """
    Check if there are at least two edge-disjoint paths from start to goal.
    Method: find first path via BFS, remove its edges, find second path.
    """
    # Find first path
    path1 = _bfs_path_temp(start, goal, adj)
    if not path1:
        return False

    # Build adjacency without the edges of path1
    path1_edges = set()
    for i in range(len(path1) - 1):
        a, b = path1[i], path1[i + 1]
        path1_edges.add((min(a, b), max(a, b)))

    adj2 = {}
    for i, gene in enumerate(chromosome):
        if gene == 1:
            a, b = possible_edges[i]
            edge_key = (min(a, b), max(a, b))
            if edge_key in path1_edges:
                continue
            if a not in adj2:
                adj2[a] = []
            if b not in adj2:
                adj2[b] = []
            adj2[a].append(b)
            adj2[b].append(a)

    # Find second path
    path2 = _bfs_path_temp(start, goal, adj2)
    return len(path2) > 0


def _tournament_select(population, fitness_scores):
    """Tournament selection: pick best from k random individuals."""
    indices = random.sample(range(len(population)), min(cfg.GA_TOURNAMENT_K, len(population)))
    best_idx = max(indices, key=lambda i: fitness_scores[i])
    return population[best_idx][:]


def _crossover(parent_a, parent_b):
    """Single-point crossover."""
    point = random.randint(1, len(parent_a) - 1)
    return parent_a[:point] + parent_b[point:]


def _mutate(chromosome):
    """Flip random bits with mutation rate."""
    return [
        (1 - gene) if random.random() < cfg.GA_MUTATION_RATE else gene
        for gene in chromosome
    ]


def _apply_chromosome(graph, chromosome, possible_edges):
    """Apply the best chromosome to the actual graph edges."""
    for i, gene in enumerate(chromosome):
        a, b = possible_edges[i]
        if gene == 1:
            cost = graph._default_edge_cost(a, b)
            graph.set_edge(a, b, cost)
        else:
            # Explicitly set to inf to ensure no stale roads remain
            graph.set_edge(a, b, float("inf"))
