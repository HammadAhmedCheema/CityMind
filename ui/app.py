"""
app.py - Main Pygame application loop for CityMind.
Ties together the renderer, sidebar, simulation engine, and event handling.
"""

import pygame
import sys
import config as cfg
from ui import colors as clr
from ui.renderer import GridRenderer
from ui.sidebar import Sidebar
from city_graph import CityGraph
from simulation.engine import SimulationEngine


class CityMindApp:
    """The main application window."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CityMind - Urban Intelligence System")

        self.screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), pygame.RESIZABLE | pygame.WINDOWMAXIMIZED)
        cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT = self.screen.get_size()
        
        # Calculate cell size and center the grid properly
        self._recalculate_grid()

        self.clock = pygame.time.Clock()

        # Load fonts (try system font, fallback to default)
        try:
            self.font_sm = pygame.font.SysFont("inter", cfg.FONT_SIZE_SM)
            self.font_md = pygame.font.SysFont("inter", cfg.FONT_SIZE_MD)
            self.font_lg = pygame.font.SysFont("inter", cfg.FONT_SIZE_LG)
            self.font_xl = pygame.font.SysFont("inter", cfg.FONT_SIZE_XL)
            self.font_title = pygame.font.SysFont("inter", cfg.FONT_SIZE_TITLE)
        except Exception:
            self.font_sm = pygame.font.Font(None, cfg.FONT_SIZE_SM + 4)
            self.font_md = pygame.font.Font(None, cfg.FONT_SIZE_MD + 4)
            self.font_lg = pygame.font.Font(None, cfg.FONT_SIZE_LG + 4)
            self.font_xl = pygame.font.Font(None, cfg.FONT_SIZE_XL + 4)
            self.font_title = pygame.font.Font(None, cfg.FONT_SIZE_TITLE + 4)

        # Core objects
        self.graph = CityGraph()
        self.sim = SimulationEngine(self.graph)
        self.renderer = GridRenderer(self.graph, self.font_sm, self.font_md)
        self.sidebar = Sidebar(self.font_sm, self.font_md, self.font_lg,
                               self.font_xl, self.sim)

        self.running = True

    def _recalculate_grid(self):
        """Calculates optimal CELL_W and CELL_H to perfectly fit and stretch the grid."""
        # Available area excluding the sidebar
        avail_w = cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH
        # Leave 50px for header and 60px for the legend at the bottom
        avail_h = cfg.WINDOW_HEIGHT - 50 - 60
        
        # Minimum margin to prevent the grid from touching the very edge
        margin_x = 40
        margin_y = 20
        safe_w = avail_w - margin_x
        safe_h = avail_h - margin_y
        
        # Calculate independent cell size for width and height to allow stretching
        cfg.CELL_W = max(10, (safe_w // cfg.GRID_COLS) - cfg.CELL_PADDING)
        cfg.CELL_H = max(10, (safe_h // cfg.GRID_ROWS) - cfg.CELL_PADDING)
        
        # Fallback for old references
        cfg.CELL_SIZE = min(cfg.CELL_W, cfg.CELL_H)
        
        # Calculate the exact pixel width and height of the fully built grid
        actual_grid_w = cfg.GRID_COLS * (cfg.CELL_W + cfg.CELL_PADDING)
        actual_grid_h = cfg.GRID_ROWS * (cfg.CELL_H + cfg.CELL_PADDING)
        
        # Update offsets to center the grid exactly in the available space
        cfg.GRID_AREA_X = max(0, (avail_w - actual_grid_w) // 2)
        cfg.GRID_AREA_Y = 50 + max(0, (avail_h - actual_grid_h) // 2)



    def run(self):
        """Main application loop."""
        while self.running:
            dt = self.clock.tick(cfg.FPS)

            self._handle_events()
            self._update(dt)
            self._draw()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _handle_events(self):
        """Process Pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.sidebar._on_play()
                elif event.key == pygame.K_RIGHT:
                    self.sidebar._on_step()
                elif event.key == pygame.K_i:
                    self.sidebar._on_init()
            elif event.type == pygame.VIDEORESIZE:
                cfg.WINDOW_WIDTH = event.w
                cfg.WINDOW_HEIGHT = event.h
                self.screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), pygame.RESIZABLE)
                
                # Recalculate cell size and center it to fit available space
                self._recalculate_grid()
                
                if hasattr(self.sidebar, 'on_resize'):
                    self.sidebar.on_resize()
                if hasattr(self.renderer, 'on_resize'):
                    self.renderer.on_resize()

            self.sidebar.handle_event(event)

    def _update(self, dt_ms):
        """Update animation and simulation state."""
        self.renderer.update()
        self.sidebar.update(dt_ms)

    def _draw(self):
        """Render the entire frame."""
        # Clear background
        self.screen.fill(clr.BG_DARK)

        # Draw subtle background grid pattern
        self._draw_bg_pattern()

        # Draw header
        self._draw_header()

        # -- Grid layers (order matters) ---------------------─

        # 1. Roads
        self.renderer.draw_roads(self.screen,
                                 show_roads=self.sidebar.show_roads)

        # 2. Cells
        self.renderer.draw_cells(self.screen,
                                 show_heatmap=self.sidebar.show_heatmap)

        # 3. Heatmap overlay (if enabled and not already showing as cell color)
        if self.sidebar.show_heatmap:
            self.renderer.draw_heatmap_overlay(self.screen)

        # 4. Flooded edges
        self.renderer.draw_flooded_edges(self.screen)

        # 5. Ambulance coverage circles
        if self.sidebar.show_ambulances:
            self.renderer.draw_ambulance_coverage(self.screen)

        # 6. Emergency path
        if self.sidebar.show_path:
            self.renderer.draw_emergency_path(self.screen)

        # 7. Ambulance markers
        self.renderer.draw_ambulances(self.screen,
                                      show_ambulances=self.sidebar.show_ambulances)

        # 8. Civilian markers
        self.renderer.draw_civilians(self.screen,
                                     self.sim.remaining_targets,
                                     self.sim.reached_targets)

        # 9. Cell tooltip
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] < self.sidebar.x:
            self.renderer.draw_tooltip(self.screen, mouse_pos)

        # Draw legend
        self._draw_legend()

        # -- Sidebar ------------------------------------------
        self.sidebar.draw(self.screen)

    def _draw_header(self):
        """Draw the top header bar."""
        header_rect = pygame.Rect(0, 0, cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH, 50)
        pygame.draw.rect(self.screen, clr.BG_HEADER, header_rect)
        pygame.draw.line(self.screen, clr.DIVIDER,
                         (0, 50), (cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH, 50))

        title = self.font_lg.render("City Grid  -  Simulation View", True, clr.TEXT_PRIMARY)
        self.screen.blit(title, (20, 14))

        # FPS counter
        fps = int(self.clock.get_fps())
        fps_text = self.font_sm.render(f"FPS: {fps}", True, clr.TEXT_SECONDARY)
        self.screen.blit(fps_text, (cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH - 70, 18))

    def _draw_legend(self):
        """Draw a compact zone color legend below the grid."""
        legend_y = cfg.GRID_AREA_Y + cfg.GRID_ROWS * (cfg.CELL_H + cfg.CELL_PADDING) + 15
        legend_x = cfg.GRID_AREA_X

        zones = [
            ("R", "Residential", "residential"),
            ("H", "Hospital", "hospital"),
            ("S", "School", "school"),
            ("I", "Industrial", "industrial"),
            ("PP", "Power Plant", "power_plant"),
            ("AD", "Amb. Depot", "ambulance_depot"),
        ]

        x = legend_x
        for abbrev, name, zone_type in zones:
            color = clr.ZONE_COLORS[zone_type]

            # Color swatch
            pygame.draw.rect(self.screen, color,
                             pygame.Rect(x, legend_y, 14, 14),
                             border_radius=3)

            # Label
            label = self.font_sm.render(name, True, clr.TEXT_SECONDARY)
            self.screen.blit(label, (x + 18, legend_y))

            x += label.get_width() + 32

    def _draw_bg_pattern(self):
        """Draw a subtle dot-grid pattern on the background."""
        for x in range(0, cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH, 30):
            for y in range(55, cfg.WINDOW_HEIGHT, 30):
                self.screen.set_at((x, y), (35, 35, 55))
