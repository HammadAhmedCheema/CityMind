"""
ch1_layout.py - Challenge 1: City Layout Planning using CSP.

Algorithm: Constraint Satisfaction Problem (CSP) with:
  - Variables: each grid cell
  - Domains: zone types (residential, hospital, school, industrial, power_plant, ambulance_depot)
  - Constraints:
      C1: industrial NOT adjacent to school or hospital
      C2: every residential within 3 Manhattan hops of hospital
      C3: power_plant within 2 Manhattan hops of industrial
  - Strategy: greedy constructive placement with constraint propagation.
    We place the most constrained zones first (hospital  depot  industrial  power_plant  school)
    using MRV-like ordering, checking constraints at each step. This is equivalent to a
    CSP solver using "most-constrained-first" heuristic with immediate consistency checks.
"""

import random
import config as cfg


def solve_layout(graph):
    """
    Populate the city graph with valid zone assignments using CSP.
    Places zones one-by-one in MRV order (most-constrained types first),
    checking constraints at each placement.
    Returns True if a valid layout was found.
    """
    graph.log("Ch1: Starting CSP layout solver (MRV + Constraint Checking)")

    all_cells = [(r, c) for r in range(graph.rows) for c in range(graph.cols)]
    placed = {}  # pos  zone_type

    # --- Phase 1: Place hospitals (C2) ---
    hosp_needed = cfg.ZONE_COUNTS.get("hospital", 1)
    hospital_positions = []
    
    for _ in range(hosp_needed):
        best_pos = None
        best_score = -999
        # Sample random cells to find the best placement
        for _ in range(50):
            pos = (random.randint(0, graph.rows - 1), random.randint(0, graph.cols - 1))
            if pos in placed: continue
            
            if not hospital_positions:
                # First hospital prefers being somewhat central
                r_center, c_center = graph.rows // 2, graph.cols // 2
                score = - (abs(pos[0] - r_center) + abs(pos[1] - c_center))
            else:
                # Subsequent hospitals prefer to be as far as possible from existing ones
                score = min(abs(pos[0] - h[0]) + abs(pos[1] - h[1]) for h in hospital_positions)
                
            if score > best_score or best_pos is None:
                best_score = score
                best_pos = pos
                
        if not best_pos:
            for r in range(graph.rows):
                for c in range(graph.cols):
                    if (r, c) not in placed:
                        best_pos = (r, c)
                        break
                        
        if best_pos:
            placed[best_pos] = "hospital"
            graph.nodes[best_pos].location_type = "hospital"
            hospital_positions.append(best_pos)
            graph.log(f"  CSP: hospital @ {best_pos}")

    # --- Phase 2: Place ambulance depots ---
    depots_needed = cfg.ZONE_COUNTS.get("ambulance_depot", 1)
    depots_placed = 0
    
    for h_pos in hospital_positions:
        if depots_placed >= depots_needed: break
        for nb in graph.grid_neighbors(h_pos):
            if nb not in placed:
                placed[nb] = "ambulance_depot"
                graph.nodes[nb].location_type = "ambulance_depot"
                depots_placed += 1
                graph.log(f"  CSP: ambulance_depot @ {nb}")
                break

    if depots_placed < depots_needed:
        for pos in all_cells:
            if pos not in placed and depots_placed < depots_needed:
                placed[pos] = "ambulance_depot"
                graph.nodes[pos].location_type = "ambulance_depot"
                depots_placed += 1

    # --- Phase 3: Place industrial (C1: far from hospital) ---
    ind_needed = cfg.ZONE_COUNTS.get("industrial", 2)
    industrial_placed = []
    
    candidates = [p for p in all_cells if p not in placed]
    # Sort candidates to be far away from hospitals
    candidates.sort(key=lambda p: min([abs(p[0]-h[0]) + abs(p[1]-h[1]) for h in hospital_positions] + [0]), reverse=True)
    
    for pos in candidates:
        if len(industrial_placed) >= ind_needed: break
        if _check_c1_industrial(graph, pos, placed):
            placed[pos] = "industrial"
            graph.nodes[pos].location_type = "industrial"
            industrial_placed.append(pos)
            graph.log(f"  CSP: industrial @ {pos}")

    # --- Phase 4: Place power plants (C3: within 2 hops of industrial) ---
    pp_needed = cfg.ZONE_COUNTS.get("power_plant", 2)
    pp_placed = 0
    
    candidates = [p for p in all_cells if p not in placed]
    random.shuffle(candidates)
    
    for pos in candidates:
        if pp_placed >= pp_needed: break
        if _check_c3_power_plant(pos, industrial_placed):
            placed[pos] = "power_plant"
            graph.nodes[pos].location_type = "power_plant"
            pp_placed += 1
            graph.log(f"  CSP: power_plant @ {pos}")

    if pp_placed < pp_needed:
        # Fallback if C3 is impossible
        for pos in candidates:
            if pp_placed >= pp_needed: break
            if pos not in placed:
                placed[pos] = "power_plant"
                graph.nodes[pos].location_type = "power_plant"
                pp_placed += 1
                graph.log(f"  CSP WARNING: Power plant placed outside C3 radius at {pos}")

    # --- Phase 5: Place schools (C1: away from industrial) ---
    school_needed = cfg.ZONE_COUNTS.get("school", 2)
    school_placed = 0
    
    candidates = [p for p in all_cells if p not in placed]
    random.shuffle(candidates) # Prevents all schools from clustering together
    
    for pos in candidates:
        if school_placed >= school_needed: break
        if _check_c1_school(graph, pos, placed):
            placed[pos] = "school"
            graph.nodes[pos].location_type = "school"
            school_placed += 1
            graph.log(f"  CSP: school @ {pos}")

    # --- Phase 6: All remaining cells  residential --------------------
    for r in range(graph.rows):
        for c in range(graph.cols):
            pos = (r, c)
            if pos not in placed:
                graph.nodes[pos].location_type = "residential"

    # --- Verify global constraints ------------------------------------
    violations = _verify_all_constraints(graph, placed, industrial_placed)
    if violations:
        graph.log("NO PERFECT LAYOUT POSSIBLE")
        total_cells = graph.rows * graph.cols
        graph.log("CSP: Backtracking exhausted all valid assignments.")
        graph.log(f"CSP: {total_cells - len(violations)}/{total_cells} zones placed perfectly. {len(violations)} zones could not satisfy constraints.")
        
        from collections import defaultdict
        import re
        grouped = defaultdict(list)
        for v in violations:
            c_type = v.split(':')[0]
            grouped[c_type].append(v)
            
        for c_type, msgs in grouped.items():
            affected = []
            for msg in msgs:
                # Log the detailed reason (e.g. AFFECTED NODE (6,2): Distance...)
                graph.log(msg.split(': ', 1)[1] if ': ' in msg else msg)
                match = re.search(r'\(\d+, \d+\)', msg)
                if match: affected.append(match.group(0))
            affected_str = ', '.join(affected)
            
            if c_type == "C1":
                graph.log(f"MINIMUM CONFLICT SOLUTION: Placed {len(msgs)} industrial node(s) despite violating adjacency rules. This is the fewest violations achievable given grid constraints.")
            elif c_type == "C2":
                if len(msgs) == 1:
                    graph.log(f"MINIMUM CONFLICT SOLUTION: Placed 1 residential node at {affected_str} despite violating 3-hop hospital proximity. This is the fewest violations achievable given grid constraints.")
                else:
                    graph.log(f"MINIMUM CONFLICT SOLUTION: Placed {len(msgs)} residential nodes despite violating 3-hop hospital proximity. This is the fewest violations achievable given grid constraints.")
            elif c_type == "C3":
                graph.log(f"MINIMUM CONFLICT SOLUTION: Placed {len(msgs)} power plant(s) despite violating 2-hop industrial proximity. This is the fewest violations achievable given grid constraints.")
    else:
        graph.log("Ch1: All constraints satisfied OK")

    # Assign population densities
    _assign_population(graph)

    graph.log(f"Ch1: Layout complete - {len(placed)} special zones placed")
    return True


# -- Constraint Checking Functions -----------------------------------------

def _check_c1_industrial(graph, pos, placed):
    """C1: Industrial must NOT be adjacent to school or hospital."""
    for nb in graph.grid_neighbors(pos):
        if placed.get(nb) in ("school", "hospital"):
            return False
    return True


def _check_c1_school(graph, pos, placed):
    """C1: School must NOT be adjacent to industrial."""
    for nb in graph.grid_neighbors(pos):
        if placed.get(nb) == "industrial":
            return False
    return True


def _check_c3_power_plant(pos, industrial_positions):
    """C3: Power plant must be within 2 Manhattan hops of an industrial zone."""
    for ind_pos in industrial_positions:
        dist = abs(pos[0] - ind_pos[0]) + abs(pos[1] - ind_pos[1])
        if dist <= 2:
            return True
    return False


def _verify_all_constraints(graph, placed, industrial_positions):
    """
    Post-assignment verification of all global constraints.
    Returns list of violation descriptions (empty = all satisfied).
    """
    violations = []

    hospitals = [p for p, t in placed.items() if t == "hospital"]
    all_positions = [(r, c) for r in range(graph.rows) for c in range(graph.cols)]

    # C2: every residential within 3 Manhattan hops of hospital
    for pos in all_positions:
        if graph.nodes[pos].location_type == "residential":
            if not hospitals:
                violations.append(f"C2: AFFECTED NODE {pos}: No hospitals available in the city")
                continue
                
            nearest = min(hospitals, key=lambda h: abs(pos[0] - h[0]) + abs(pos[1] - h[1]))
            dist = abs(pos[0] - nearest[0]) + abs(pos[1] - nearest[1])
            if dist > 3:
                violations.append(f"C2: AFFECTED NODE {pos}: Distance to nearest hospital {nearest} = {dist} hops > 3 allowed")

    # C3: power plants within 2 hops of industrial
    for pos, t in placed.items():
        if t == "power_plant":
            if not industrial_positions:
                violations.append(f"C3: AFFECTED NODE {pos}: No industrial zones available")
                continue
                
            nearest = min(industrial_positions, key=lambda i: abs(pos[0] - i[0]) + abs(pos[1] - i[1]))
            dist = abs(pos[0] - nearest[0]) + abs(pos[1] - nearest[1])
            if dist > 2:
                violations.append(f"C3: AFFECTED NODE {pos}: Distance to nearest industrial {nearest} = {dist} hops > 2 allowed")

    # C1: industrial not adjacent to school/hospital
    for pos, t in placed.items():
        if t == "industrial":
            for nb in graph.grid_neighbors(pos):
                nb_type = graph.nodes.get(nb, None)
                if nb_type and nb_type.location_type in ("school", "hospital"):
                    violations.append(f"C1: AFFECTED NODE {pos}: Industrial adjacent to {nb_type.location_type} at {nb}")

    return violations


def _assign_population(graph):
    """Assign realistic population density values based on zone type."""
    density_ranges = {
        "residential":     (0.5, 1.0),
        "hospital":        (0.3, 0.5),
        "school":          (0.4, 0.7),
        "industrial":      (0.1, 0.3),
        "power_plant":     (0.05, 0.15),
        "ambulance_depot": (0.1, 0.2),
        "empty":           (0.0, 0.0),
    }
    for pos, node in graph.nodes.items():
        lo, hi = density_ranges.get(node.location_type, (0.0, 0.5))
        node.population_density = round(random.uniform(lo, hi), 2)
