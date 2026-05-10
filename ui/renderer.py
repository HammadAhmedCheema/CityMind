"""
renderer.py - Renders the city grid, roads, overlays, animations on the main canvas.
"""

import math
import pygame
import config as cfg
from ui import colors as clr


class GridRenderer:
    """Draws the city grid with all visual layers."""

    def __init__(self, graph, font_sm, font_md):
        self.graph = graph
        self.font_sm = font_sm
        self.font_md = font_md

        # Compute grid pixel dimensions
        self.cell_w_total = cfg.CELL_W + cfg.CELL_PADDING
        self.cell_h_total = cfg.CELL_H + cfg.CELL_PADDING
        self.grid_pixel_w = cfg.GRID_COLS * self.cell_w_total
        self.grid_pixel_h = cfg.GRID_ROWS * self.cell_h_total

        # Animation counters
        self.tick = 0
        self.pulse_phase = 0.0

        # Tooltip state
        self.hover_cell = None

        # Load zone images
        self.zone_images = {}
        self.original_images = {}
        self.original_road_img = None
        self._load_images_from_disk()
        self._scale_images()

    def _load_images_from_disk(self):
        """Load images from disk once and cache them."""
        import os
        image_paths = {
            "residential": "assets/residential.png",
            "hospital": "assets/hospital.png",
            "school": "assets/school.png",
            "industrial": "assets/industrial.png",
            "power_plant": "assets/power_plant.png",
            "ambulance_depot": "assets/ambulance_depot.png"
        }
        for zone, path in image_paths.items():
            if os.path.exists(path):
                try:
                    self.original_images[zone] = pygame.image.load(path).convert_alpha()
                except Exception as e:
                    print(f"Failed to load {path}: {e}")
        
        # Load road texture
        road_path = "assets/road.png"
        if os.path.exists(road_path):
            try:
                self.original_road_img = pygame.image.load(road_path).convert_alpha()
            except Exception as e:
                print(f"Failed to load {road_path}: {e}")

    def _scale_images(self):
        """Scale cached images to the current cell size."""
        self.zone_images.clear()
        for zone, img in self.original_images.items():
            zoom = 0
            scaled = pygame.transform.smoothscale(img, (cfg.CELL_W + zoom, cfg.CELL_H + zoom))
            self.zone_images[zone] = scaled
            
        self.road_width = max(16, cfg.CELL_SIZE // 3)
        if self.original_road_img:
            # Vertical road image matches cell height
            img_v = pygame.transform.smoothscale(self.original_road_img, (self.road_width, self.cell_h_total))
            # Horizontal road image matches cell width (rotate then scale)
            rotated = pygame.transform.rotate(self.original_road_img, 90)
            img_h = pygame.transform.smoothscale(rotated, (self.cell_w_total, self.road_width))
            self.road_img_v = img_v
            self.road_img_h = img_h
        else:
            self.road_img_v = None
            self.road_img_h = None

    def on_resize(self):
        """Update renderer dimensions when window resizes."""
        self.cell_w_total = cfg.CELL_W + cfg.CELL_PADDING
        self.cell_h_total = cfg.CELL_H + cfg.CELL_PADDING
        self.grid_pixel_w = cfg.GRID_COLS * self.cell_w_total
        self.grid_pixel_h = cfg.GRID_ROWS * self.cell_h_total
        self._scale_images()

    def update(self):
        """Advance animation timers."""
        self.tick += 1
        self.pulse_phase = (self.tick % 60) / 60.0  # 0..1 every second at 60fps

    def cell_rect(self, row, col):
        """Get the pixel rect for a grid cell."""
        x = cfg.GRID_AREA_X + col * self.cell_w_total
        y = cfg.GRID_AREA_Y + row * self.cell_h_total
        return pygame.Rect(x, y, cfg.CELL_W, cfg.CELL_H)

    def cell_center(self, row, col):
        """Get the pixel center of a grid cell."""
        rect = self.cell_rect(row, col)
        return rect.centerx, rect.centery

    def get_cell_at(self, mouse_pos):
        """Return (row, col) of cell under mouse, or None."""
        mx, my = mouse_pos
        col = (mx - cfg.GRID_AREA_X) // self.cell_w_total
        row = (my - cfg.GRID_AREA_Y) // self.cell_h_total
        if 0 <= row < cfg.GRID_ROWS and 0 <= col < cfg.GRID_COLS:
            # Check we're inside the cell (not in padding)
            cell_r = self.cell_rect(row, col)
            if cell_r.collidepoint(mx, my):
                return (row, col)
        return None

    # -- Draw Layers ------------------------------------------

    def draw_cells(self, surface, show_heatmap=False):
        """Draw all grid cells with zone colors or heatmap."""
        for r in range(cfg.GRID_ROWS):
            for c in range(cfg.GRID_COLS):
                rect = self.cell_rect(r, c)
                node = self.graph.nodes[(r, c)]

                if show_heatmap and node.location_type != "empty":
                    color = clr.risk_to_color(node.risk_index)
                else:
                    color = clr.ZONE_COLORS.get(node.location_type, clr.BG_CELL)

                # Draw cell shadow
                shadow_rect = rect.move(2, 2)
                pygame.draw.rect(surface, (10, 10, 20), shadow_rect,
                                 border_radius=cfg.CELL_RADIUS)

                # Draw cell background
                pygame.draw.rect(surface, color, rect,
                                 border_radius=cfg.CELL_RADIUS)

                if node.location_type in self.zone_images:
                    # Draw image on top, centered to allow for slight zoom overflow
                    img = self.zone_images[node.location_type]
                    img_rect = img.get_rect(center=rect.center)
                    surface.blit(img, img_rect)
                else:
                    # Draw zone label abbreviation if no image
                    abbrev = _zone_abbrev(node.location_type)
                    if abbrev:
                        label = self.font_sm.render(abbrev, True, (255, 255, 255))
                        label_rect = label.get_rect(center=rect.center)
                        surface.blit(label, label_rect)

                # Draw cell border (subtle)
                border_color = tuple(min(255, c + 30) for c in color)
                pygame.draw.rect(surface, border_color, rect,
                                 width=1, border_radius=cfg.CELL_RADIUS)

    def draw_roads(self, surface, show_roads=True):
        """Draw road connections between cells."""
        if not show_roads:
            return

        for edge_key, cost in self.graph.edges.items():
            a, b = edge_key

            if cost >= float("inf"):
                continue  # no road or flooded

            cx_a, cy_a = self.cell_center(a[0], a[1])
            cx_b, cy_b = self.cell_center(b[0], b[1])

            # Check if flooded (draw differently)
            if edge_key in self.graph.flooded_edges:
                pygame.draw.line(surface, clr.ROAD_FLOODED,
                                 (cx_a, cy_a), (cx_b, cy_b), self.road_width)
                # Animated flood marker at midpoint
                mid_x = (cx_a + cx_b) // 2
                mid_y = (cy_a + cy_b) // 2
                flood_r = int(self.road_width//2 + 4 + 3 * math.sin(self.pulse_phase * math.pi * 2))
                pygame.draw.circle(surface, clr.ROAD_FLOODED,
                                   (mid_x, mid_y), flood_r, 2)
            else:
                if getattr(self, 'road_img_h', None) and getattr(self, 'road_img_v', None):
                    if a[0] == b[0]:  # same row -> horizontal road
                        x = min(cx_a, cx_b)
                        y = cy_a - self.road_width // 2
                        surface.blit(self.road_img_h, (x, y))
                    elif a[1] == b[1]:  # same col -> vertical road
                        x = cx_a - self.road_width // 2
                        y = min(cy_a, cy_b)
                        surface.blit(self.road_img_v, (x, y))
                else:
                    # Normal road fallback
                    pygame.draw.line(surface, clr.ROAD_COLOR,
                                     (cx_a, cy_a), (cx_b, cy_b), self.road_width)

    def draw_flooded_edges(self, surface):
        """Draw X markers on flooded road segments."""
        for edge_key in self.graph.flooded_edges:
            a, b = edge_key
            cx_a, cy_a = self.cell_center(a[0], a[1])
            cx_b, cy_b = self.cell_center(b[0], b[1])
            mid_x = (cx_a + cx_b) // 2
            mid_y = (cy_a + cy_b) // 2

            # Pulsing blue circle
            radius = int(8 + 4 * math.sin(self.pulse_phase * math.pi * 2))
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (30, 144, 255, 100), (radius, radius), radius)
            surface.blit(s, (mid_x - radius, mid_y - radius))

    def draw_ambulances(self, surface, show_ambulances=True):
        """Draw ambulance positions with pulsing animation."""
        if not show_ambulances:
            return

        for pos in self.graph.ambulances:
            cx, cy = self.cell_center(pos[0], pos[1])

            # Pulsing outer ring
            pulse_r = int(14 + 4 * math.sin(self.pulse_phase * math.pi * 2))
            s = pygame.Surface((pulse_r * 2 + 4, pulse_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 50, 50, 80),
                               (pulse_r + 2, pulse_r + 2), pulse_r)
            surface.blit(s, (cx - pulse_r - 2, cy - pulse_r - 2))

            # Solid center
            pygame.draw.circle(surface, clr.AMBULANCE_COLOR, (cx, cy), 8)

            # Cross icon
            pygame.draw.line(surface, (255, 255, 255), (cx - 4, cy), (cx + 4, cy), 2)
            pygame.draw.line(surface, (255, 255, 255), (cx, cy - 4), (cx, cy + 4), 2)

    def draw_emergency_path(self, surface):
        """Draw the planned emergency route with animated dashes."""
        path = self.graph.emergency_path
        if not path or len(path) < 2:
            return

        # Draw path segments with animated dash pattern
        dash_offset = self.tick % 20

        for i in range(len(path) - 1):
            cx_a, cy_a = self.cell_center(path[i][0], path[i][1])
            cx_b, cy_b = self.cell_center(path[i + 1][0], path[i + 1][1])

            # Glow effect
            pygame.draw.line(surface, clr.PATH_GLOW,
                             (cx_a, cy_a), (cx_b, cy_b), 4)
            # Solid line
            pygame.draw.line(surface, clr.PATH_COLOR,
                             (cx_a, cy_a), (cx_b, cy_b), 2)

        # Draw current team position
        if self.graph.emergency_current:
            tc = self.graph.emergency_current
            cx, cy = self.cell_center(tc[0], tc[1])
            pygame.draw.circle(surface, clr.PATH_COLOR, (cx, cy), 10, 2)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 5)

    def draw_civilians(self, surface, remaining, reached):
        """Draw civilian markers (yellow=waiting, gray=reached)."""
        for pos in reached:
            cx, cy = self.cell_center(pos[0], pos[1])
            pygame.draw.circle(surface, clr.CIVILIAN_REACHED, (cx, cy), 6)

        for pos in remaining:
            cx, cy = self.cell_center(pos[0], pos[1])
            # Pulsing yellow marker
            pulse = int(8 + 3 * math.sin(self.pulse_phase * math.pi * 2 + 1.0))
            s = pygame.Surface((pulse * 2, pulse * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 220, 50, 120), (pulse, pulse), pulse)
            surface.blit(s, (cx - pulse, cy - pulse))
            pygame.draw.circle(surface, clr.CIVILIAN_COLOR, (cx, cy), 5)

    def draw_heatmap_overlay(self, surface):
        """Draw a semi-transparent heatmap overlay based on crime risk."""
        s = pygame.Surface((cfg.CELL_W, cfg.CELL_H), pygame.SRCALPHA)

        for r in range(cfg.GRID_ROWS):
            for c in range(cfg.GRID_COLS):
                node = self.graph.nodes[(r, c)]
                if node.location_type == "empty":
                    continue

                color = clr.risk_to_color(node.risk_index)
                rect = self.cell_rect(r, c)

                s.fill((color[0], color[1], color[2], 100))
                surface.blit(s, rect.topleft)

    def draw_ambulance_coverage(self, surface):
        """Draw coverage circles around ambulances showing response range."""
        for pos in self.graph.ambulances:
            cx, cy = self.cell_center(pos[0], pos[1])
            # Coverage radius = 2 cells (use max dimension)
            radius = 2 * max(self.cell_w_total, self.cell_h_total)
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (6, 214, 160, 25), (radius, radius), radius)
            pygame.draw.circle(s, (6, 214, 160, 50), (radius, radius), radius, 2)
            surface.blit(s, (cx - radius, cy - radius))

    def draw_tooltip(self, surface, mouse_pos):
        """Draw info tooltip for the cell under the mouse."""
        cell = self.get_cell_at(mouse_pos)
        if cell is None:
            return

        node = self.graph.nodes[cell]
        lines = [
            f"Cell ({cell[0]}, {cell[1]})",
            f"Type: {node.location_type}",
            f"Density: {node.population_density:.2f}",
            f"Risk: {node.crime_risk} ({node.risk_index:.2f})",
            f"Accessible: {'Yes' if node.accessible else 'No'}",
        ]

        # Calculate tooltip size
        padding = 8
        line_height = 18
        max_width = max(self.font_sm.size(line)[0] for line in lines) + padding * 2
        height = len(lines) * line_height + padding * 2

        # Position tooltip near mouse
        tx = min(mouse_pos[0] + 15, cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH - max_width - 10)
        ty = min(mouse_pos[1] - 10, cfg.WINDOW_HEIGHT - height - 10)

        # Draw background
        tooltip_rect = pygame.Rect(tx, ty, max_width, height)
        s = pygame.Surface((max_width, height), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 20, 40, 220), s.get_rect(), border_radius=6)
        surface.blit(s, (tx, ty))
        pygame.draw.rect(surface, clr.TEXT_ACCENT, tooltip_rect, width=1, border_radius=6)

        # Draw text
        for i, line in enumerate(lines):
            color = clr.TEXT_PRIMARY if i == 0 else clr.TEXT_SECONDARY
            text = self.font_sm.render(line, True, color)
            surface.blit(text, (tx + padding, ty + padding + i * line_height))


def _zone_abbrev(zone_type):
    """Short 2-3 letter abbreviation for each zone type."""
    return {
        "residential":     "R",
        "hospital":        "H",
        "school":          "S",
        "industrial":      "I",
        "power_plant":     "PP",
        "ambulance_depot": "AD",
        "empty":           "",
    }.get(zone_type, "")
