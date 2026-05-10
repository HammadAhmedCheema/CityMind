"""
sidebar.py - Right-side panel with simulation controls, overlay toggles,
event log, and statistics.
"""

import pygame
import config as cfg
from ui import colors as clr
from ui.button import Button
from ui.toggle import Toggle


class Sidebar:
    """The control panel and event log sidebar."""

    def __init__(self, font_sm, font_md, font_lg, font_xl, sim_engine):
        self.sim = sim_engine
        self.font_sm = font_sm
        self.font_md = font_md
        self.font_lg = font_lg
        self.font_xl = font_xl

        # Panel position
        self.x = cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH
        self.y = 0
        self.w = cfg.SIDEBAR_WIDTH
        self.h = cfg.WINDOW_HEIGHT

        # -- Buttons ------------------------------------------
        btn_y = 120
        btn_w = 90
        btn_h = 36
        btn_gap = 8

        self.btn_init = Button(self.x + 20, btn_y, btn_w, btn_h,
                               "Init", font_md, on_click=self._on_init)
        self.btn_play = Button(self.x + 20 + btn_w + btn_gap, btn_y, btn_w, btn_h,
                               "Play", font_md, on_click=self._on_play)
        self.btn_step = Button(self.x + 20 + 2 * (btn_w + btn_gap), btn_y, btn_w, btn_h,
                               "Step", font_md, on_click=self._on_step)
                               
        btn_y_flood = btn_y + btn_h + 8
        self.btn_flood = Button(self.x + 20, btn_y_flood, btn_w * 3 + btn_gap * 2, btn_h,
                                "Cause Flood", font_md, on_click=self._on_flood)

        self.buttons = [self.btn_init, self.btn_play, self.btn_step, self.btn_flood]

        # -- Toggles ------------------------------------------
        toggle_x = self.x + 20
        toggle_y_start = 225

        self.toggle_roads = Toggle(toggle_x, toggle_y_start, "Roads", font_sm, True)
        self.toggle_ambulance = Toggle(toggle_x, toggle_y_start + 40, "Ambulance Coverage", font_sm, True)
        self.toggle_heatmap = Toggle(toggle_x, toggle_y_start + 80, "Crime Heatmap", font_sm, False)
        self.toggle_path = Toggle(toggle_x, toggle_y_start + 120, "Emergency Path", font_sm, True)

        self.toggles = [self.toggle_roads, self.toggle_ambulance,
                        self.toggle_heatmap, self.toggle_path]

        # -- Event log scroll ---------------------------------
        self.log_scroll_offset = 0

        # Auto-play timer
        self.auto_play = False
        self.auto_play_timer = 0
        self.auto_play_interval = 1500  # ms between steps

    def on_resize(self):
        """Update sidebar layout when the window is resized."""
        self.x = cfg.WINDOW_WIDTH - cfg.SIDEBAR_WIDTH
        self.h = cfg.WINDOW_HEIGHT
        
        btn_w = 90
        btn_gap = 8
        self.btn_init.rect.x = self.x + 20
        self.btn_play.rect.x = self.x + 20 + btn_w + btn_gap
        self.btn_step.rect.x = self.x + 20 + 2 * (btn_w + btn_gap)
        self.btn_flood.rect.x = self.x + 20
        
        toggle_x = self.x + 20
        for toggle in self.toggles:
            if hasattr(toggle, 'set_x'):
                toggle.set_x(toggle_x)
            else:
                toggle.x = toggle_x
                toggle.rect.x = toggle_x

    # -- Overlay state ---------------------------------------─

    @property
    def show_roads(self):
        return self.toggle_roads.state

    @property
    def show_ambulances(self):
        return self.toggle_ambulance.state

    @property
    def show_heatmap(self):
        return self.toggle_heatmap.state

    @property
    def show_path(self):
        return self.toggle_path.state

    # -- Button callbacks ------------------------------------─

    def _on_init(self):
        self.sim.initialize()

    def _on_play(self):
        if self.sim.is_initialized:
            self.auto_play = not self.auto_play
            self.sim.is_running = self.auto_play
            self.btn_play.text = "Pause" if self.auto_play else "Play"

    def _on_step(self):
        if self.sim.is_initialized:
            self.auto_play = False
            self.sim.is_running = False
            self.btn_play.text = "Play"
            self.sim.step()
            
    def _on_flood(self):
        if self.sim.is_initialized:
            self.sim.cause_manual_flood()

    # -- Event handling ---------------------------------------

    def handle_event(self, event):
        """Forward events to buttons and toggles."""
        for btn in self.buttons:
            btn.handle_event(event)
        for toggle in self.toggles:
            toggle.handle_event(event)

        # Log scrolling
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if mouse_pos[0] >= self.x:
                self.log_scroll_offset = max(0, self.log_scroll_offset - event.y * 3)

    # -- Update -----------------------------------------------

    def update(self, dt_ms):
        """Handle auto-play timing."""
        if self.auto_play and self.sim.is_initialized:
            self.auto_play_timer += dt_ms
            if self.auto_play_timer >= self.auto_play_interval:
                self.auto_play_timer = 0
                if not self.sim.step():
                    self.auto_play = False
                    self.btn_play.text = "Play"

    # -- Drawing ---------------------------------------------─

    def draw(self, surface):
        """Render the complete sidebar."""
        # Semi-transparent panel background
        panel = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        panel.fill((22, 33, 62, 230))
        surface.blit(panel, (self.x, self.y))

        # Left border line
        pygame.draw.line(surface, clr.DIVIDER, (self.x, 0), (self.x, self.h), 1)

        # -- Title --------------------------------------------
        title = self.font_xl.render("CITYMIND", True, clr.TEXT_ACCENT)
        surface.blit(title, (self.x + 20, 20))

        subtitle = self.font_sm.render("Urban Intelligence System", True, clr.TEXT_SECONDARY)
        surface.blit(subtitle, (self.x + 20, 55))

        # Step counter
        step_text = f"Step: {self.sim.current_step}/{self.sim.max_steps}"
        step_color = clr.TEXT_SUCCESS if self.sim.is_initialized else clr.TEXT_SECONDARY
        step_surface = self.font_md.render(step_text, True, step_color)
        surface.blit(step_surface, (self.x + 20, 82))

        # Status indicator
        if not self.sim.is_initialized:
            status = "Not Initialized"
            status_color = clr.TEXT_SECONDARY
        elif self.auto_play:
            status = "Running"
            status_color = clr.TEXT_SUCCESS
        else:
            status = "Paused"
            status_color = clr.TEXT_WARNING
        status_surf = self.font_sm.render(status, True, status_color)
        surface.blit(status_surf, (self.x + 180, 85))

        # -- Buttons ------------------------------------------
        for btn in self.buttons:
            btn.draw(surface)

        # -- Section: Overlays --------------------------------
        divider_y = 205
        pygame.draw.line(surface, clr.DIVIDER,
                         (self.x + 15, divider_y), (self.x + self.w - 15, divider_y))
        section_label = self.font_sm.render("OVERLAYS", True, clr.TEXT_SECONDARY)
        surface.blit(section_label, (self.x + 20, divider_y + 5))

        for toggle in self.toggles:
            toggle.draw(surface)

        # -- Section: Statistics ------------------------------
        stats_y = 371
        pygame.draw.line(surface, clr.DIVIDER,
                         (self.x + 15, stats_y), (self.x + self.w - 15, stats_y))
        section_label = self.font_sm.render("STATISTICS", True, clr.TEXT_SECONDARY)
        surface.blit(section_label, (self.x + 20, stats_y + 6))

        self._draw_stats(surface, stats_y + 22)

        # -- Section: Event Log ------------------------------─
        log_y = 580
        pygame.draw.line(surface, clr.DIVIDER,
                         (self.x + 15, log_y), (self.x + self.w - 15, log_y))
        section_label = self.font_sm.render("EVENT LOG", True, clr.TEXT_SECONDARY)
        surface.blit(section_label, (self.x + 20, log_y + 5))

        self._draw_event_log(surface, log_y + 22)

    def _draw_stats(self, surface, y):
        """Draw summary statistics."""
        graph = self.sim.graph
        stats = [
            ("Grid Size", f"{graph.rows}x{graph.cols}"),
            ("Roads Built", str(len(graph.get_all_built_roads()))),
            ("Flooded Roads", str(len(graph.flooded_edges))),
            ("Ambulances", str(len(graph.ambulances))),
            ("Civilians Left", str(len(self.sim.remaining_targets))),
        ]

        # Count risk distribution
        risk_counts = {"High": 0, "Medium": 0, "Low": 0}
        for node in graph.nodes.values():
            if node.crime_risk in risk_counts:
                risk_counts[node.crime_risk] += 1

        stats.append(("Risk H/M/L", f"{risk_counts['High']}/{risk_counts['Medium']}/{risk_counts['Low']}"))

        for i, (label, value) in enumerate(stats):
            ly = y + i * 32
            label_surf = self.font_sm.render(label, True, clr.TEXT_SECONDARY)
            value_surf = self.font_sm.render(value, True, clr.TEXT_PRIMARY)
            surface.blit(label_surf, (self.x + 20, ly))
            surface.blit(value_surf, (self.x + self.w - 20 - value_surf.get_width(), ly))

    def _draw_event_log(self, surface, y):
        """Draw scrollable event log with text wrapping."""
        log = self.sim.graph.event_log
        
        # Cache wrapped lines to avoid re-wrapping every frame
        if not hasattr(self, '_wrapped_log') or len(log) < getattr(self, '_last_log_len', 0):
            self._wrapped_log = []
            self._last_log_len = 0
            
        if len(log) > self._last_log_len:
            max_w = self.w - 30
            for i in range(self._last_log_len, len(log)):
                line = log[i]
                
                # Determine color once for the whole message
                if "ERROR" in line or "WARNING" in line:
                    color = clr.TEXT_DANGER
                elif "FLOOD" in line:
                    color = (30, 144, 255)
                elif "REACHED" in line:
                    color = clr.TEXT_SUCCESS
                elif "===" in line or "---" in line:
                    color = clr.TEXT_ACCENT
                else:
                    color = clr.TEXT_SECONDARY
                
                # Wrap text
                words = line.split(' ')
                current_line = words[0] if words else ""
                for word in words[1:]:
                    # Check if adding the word exceeds max width
                    if self.font_sm.size(current_line + ' ' + word)[0] <= max_w:
                        current_line += ' ' + word
                    else:
                        self._wrapped_log.append((current_line, color))
                        # Indent wrapped lines slightly for readability
                        current_line = '  ' + word
                        
                if current_line:
                    self._wrapped_log.append((current_line, color))
                    
            self._last_log_len = len(log)

        line_height = 24  # slightly tighter spacing for wrapped text
        visible_height = self.h - y - 15
        max_visible_lines = visible_height // line_height

        total_lines = len(self._wrapped_log)
        
        # Track wrapped log length to auto-scroll only when new lines are added
        if not hasattr(self, '_prev_wrapped_len') or total_lines < getattr(self, '_prev_wrapped_len', 0):
            self._prev_wrapped_len = 0
            
        if total_lines > self._prev_wrapped_len:
            # New logs arrived, snap to bottom
            self.log_scroll_offset = max(0, total_lines - max_visible_lines)
            self._prev_wrapped_len = total_lines

        # Clamp scroll offset to valid bounds
        max_offset = max(0, total_lines - max_visible_lines)
        self.log_scroll_offset = max(0, min(self.log_scroll_offset, max_offset))

        # Clip region
        clip_rect = pygame.Rect(self.x + 10, y, self.w - 20, visible_height)
        surface.set_clip(clip_rect)

        start_idx = max(0, self.log_scroll_offset)
        for i in range(start_idx, min(total_lines, start_idx + max_visible_lines)):
            text_str, color = self._wrapped_log[i]
            text = self.font_sm.render(text_str, True, color)
            surface.blit(text, (self.x + 15, y + (i - start_idx) * line_height))

        surface.set_clip(None)
