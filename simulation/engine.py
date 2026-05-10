"""
engine.py - 20-step simulation engine.

Orchestrates all 5 challenges and runs the integrated simulation loop.
Each step: random floods  update risks  re-evaluate ambulances  re-route emergencies.
"""

import random
import config as cfg
from challenges import ch1_layout, ch2_roads, ch3_ambulance, ch4_routing, ch5_crime


class SimulationEngine:
    """Manages the full CityMind simulation lifecycle."""

    def __init__(self, graph):
        self.graph = graph
        self.current_step = 0
        self.max_steps = cfg.SIM_STEPS
        self.is_running = False
        self.is_initialized = False

        # Emergency routing state
        self.remaining_targets = []
        self.team_position = None
        self.reached_targets = []

    def reset(self):
        """Reset the simulation state for re-initialization."""
        self.current_step = 0
        self.is_running = False
        self.is_initialized = False
        self.remaining_targets = []
        self.team_position = None
        self.reached_targets = []
        self.graph.reset()

    def initialize(self):
        """
        Run all one-time setup phases:
        1. City layout (CSP)
        2. Road network (GA)
        3. Crime prediction (K-Means + KNN)
        4. Ambulance placement (SA)
        5. Set up emergency scenario
        """
        self.reset()
        self.graph.log("=== INITIALIZING CITYMIND ===")

        # Phase 1: Layout
        self.graph.log("-- Phase 1: City Layout Planning --")
        ch1_layout.solve_layout(self.graph)

        # Phase 2: Road Network
        self.graph.log("-- Phase 2: Road Network Optimization --")
        ch2_roads.optimize_roads(self.graph)

        # Phase 3: Crime Prediction (before ambulance placement, as it affects costs)
        self.graph.log("-- Phase 3: Crime Risk Prediction --")
        ch5_crime.predict_crime(self.graph)

        # Phase 4: Ambulance Placement
        self.graph.log("-- Phase 4: Ambulance Placement --")
        ch3_ambulance.place_ambulances(self.graph)

        # Phase 5: Set up emergency scenario
        self.graph.log("-- Phase 5: Emergency Scenario Setup --")
        self._setup_emergency()
        
        # Calculate initial accessibility
        reachable = self.graph.bfs_reachable(self.team_position)
        for pos, node in self.graph.nodes.items():
            node.accessible = (pos in reachable)

        self.is_initialized = True
        self.graph.log("=== INITIALIZATION COMPLETE ===")

    def _setup_emergency(self):
        """Place trapped civilians and plan initial route."""
        # Team starts at the ambulance depot
        depots = self.graph.get_nodes_by_type("ambulance_depot")
        self.team_position = depots[0] if depots else (0, 0)

        # Pick random residential cells as civilian locations
        residential = self.graph.get_nodes_by_type("residential")
        
        # FILTER: Only pick residential nodes reachable from the depot
        reachable_from_depot = self.graph.bfs_reachable(self.team_position)
        reachable_residential = [p for p in residential if p in reachable_from_depot]
        
        if len(reachable_residential) < len(residential):
            stranded = len(residential) - len(reachable_residential)
            self.graph.log(f"Ch4: WARNING - {stranded} residential nodes are unreachable from depot!")
            
        num_civilians = min(cfg.NUM_CIVILIANS, len(reachable_residential))
        if num_civilians == 0:
            self.graph.log("Ch4: ERROR - No reachable residential zones found!")
            self.remaining_targets = []
        else:
            self.remaining_targets = random.sample(reachable_residential, num_civilians)

        self.graph.emergency_targets = list(self.remaining_targets)
        self.graph.emergency_current = self.team_position

        # Plan initial route
        if self.remaining_targets:
            ch4_routing.plan_emergency_route(
                self.graph, self.team_position, self.remaining_targets
            )
        self.graph.log(f"Emergency: {num_civilians} civilians at {self.remaining_targets}")

    def step(self):
        """
        Execute one simulation step.
        Returns True if simulation should continue, False if complete.
        """
        if not self.is_initialized:
            return False

        if self.current_step >= self.max_steps:
            self.graph.log("=== SIMULATION COMPLETE ===")
            self.is_running = False
            return False

        self.current_step += 1
        
        # Calculate mission stats for logging
        targets_left = len(self.remaining_targets)
        path_len = len(self.graph.emergency_path) - 1 if self.graph.emergency_path else 0
        
        self.graph.log(f"--- Step {self.current_step}/{self.max_steps} ---")
        self.graph.log(f"  Status: Team @ {self.team_position}, Targets: {targets_left}, Dist: {path_len} hops")

        # 1. Move emergency team along path (advance a few steps)
        self._advance_team()

        # 3. Every 5 steps: re-run crime prediction and re-evaluate ambulances
        if self.current_step % 5 == 0:
            self.graph.log("Re-evaluating crime risk and ambulance positions...")
            ch5_crime.predict_crime(self.graph)
            ch3_ambulance.place_ambulances(self.graph)

        return True

    def cause_manual_flood(self):
        """Randomly flood 1 road edge ON THE CURRENT PATH to force a reroute."""
        if not self.graph.emergency_path or len(self.graph.emergency_path) < 2:
            self.graph.log("FLOOD FAILED: No active path to block.")
            return

        path = self.graph.emergency_path
        
        # Pick a random edge from the current path
        idx = random.randint(0, len(path) - 2)
        u, v = path[idx], path[idx+1]
        
        # Block it
        self.graph.block_edge(u, v)
        self.graph.log(f"FLOOD: Road {u}-{v} blocked manually!")
        
        # Update accessibility map globally
        reachable = self.graph.bfs_reachable(self.team_position)
        for pos, node in self.graph.nodes.items():
            node.accessible = (pos in reachable)
        
        # Re-route
        if self.remaining_targets:
            self.graph.log("WARNING: Flood affects current route - re-routing!")
            ch4_routing.reroute_from(
                self.graph, self.team_position, self.remaining_targets
            )

    def _advance_team(self):
        """Move the emergency team 2 steps along the planned path."""
        path = self.graph.emergency_path
        if not path or len(path) <= 1:
            return

        steps_to_move = min(2, len(path) - 1)

        for _ in range(steps_to_move):
            if len(path) <= 1:
                break

            path.pop(0)
            self.team_position = path[0]
            self.graph.emergency_current = self.team_position
            self.graph.log(f"    Moving... now at {self.team_position}")

            # Check if we reached a target
            if self.team_position in self.remaining_targets:
                self.remaining_targets.remove(self.team_position)
                self.reached_targets.append(self.team_position)
                self.graph.log(f"SUCCESS: Civilian at {self.team_position} REACHED!")
                self.graph.log(f"    Remaining targets: {len(self.remaining_targets)}")

        self.graph.emergency_path = path
