"""
toggle.py - Toggle switch component for overlay controls.
"""

import pygame
from ui import colors as clr


class Toggle:
    """An animated on/off toggle switch with a label."""

    def __init__(self, x, y, label, font, initial_state=True):
        self.x = x
        self.y = y
        self.label = label
        self.font = font
        self.state = initial_state

        # Track dimensions
        self.track_width = 40
        self.track_height = 20
        self.knob_radius = 8

        # Click area
        self.rect = pygame.Rect(x, y, self.track_width + 10 + 200, self.track_height + 4)

        # Animation
        self.knob_x = self.x + self.track_width - self.knob_radius - 2 if initial_state else self.x + self.knob_radius + 2
        self.target_x = self.knob_x

    def handle_event(self, event):
        """Toggle state on click."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                if self.state:
                    self.target_x = self.x + self.track_width - self.knob_radius - 2
                else:
                    self.target_x = self.x + self.knob_radius + 2

    def set_x(self, new_x):
        """Update x position of the toggle and animations."""
        delta = new_x - self.x
        self.x = new_x
        self.rect.x = new_x
        self.knob_x += delta
        self.target_x += delta

    def draw(self, surface):
        """Render the toggle switch and label."""
        # Animate knob position
        if abs(self.knob_x - self.target_x) > 1:
            self.knob_x += (self.target_x - self.knob_x) * 0.3

        # Draw track
        track_rect = pygame.Rect(self.x, self.y + 2, self.track_width, self.track_height)
        track_color = clr.TOGGLE_ON if self.state else clr.TOGGLE_OFF
        pygame.draw.rect(surface, track_color, track_rect,
                         border_radius=self.track_height // 2)

        # Draw knob
        knob_center = (int(self.knob_x), self.y + 2 + self.track_height // 2)
        pygame.draw.circle(surface, clr.TOGGLE_KNOB, knob_center, self.knob_radius)

        # Draw label
        label_surface = self.font.render(self.label, True, clr.TEXT_PRIMARY)
        surface.blit(label_surface, (self.x + self.track_width + 10, self.y + 2))
