"""
button.py - Reusable Pygame button with hover/press states and rounded corners.
"""

import pygame
from ui import colors as clr


class Button:
    """A styled, interactive button for the CityMind UI."""

    def __init__(self, x, y, width, height, text, font,
                 on_click=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.on_click = on_click

        self.is_hovered = False
        self.is_pressed = False
        self.radius = 8

    def handle_event(self, event):
        """Process mouse events. Call this from the main event loop."""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
            self.is_pressed = False

    def draw(self, surface):
        """Render the button with appropriate visual state."""
        # Choose color based on state
        if self.is_pressed:
            bg = clr.BUTTON_ACTIVE
        elif self.is_hovered:
            bg = clr.BUTTON_HOVER
        else:
            bg = clr.BUTTON_BG

        # Draw rounded rectangle
        pygame.draw.rect(surface, bg, self.rect, border_radius=self.radius)

        # Subtle border on hover
        if self.is_hovered:
            pygame.draw.rect(surface, clr.TEXT_ACCENT, self.rect,
                             width=1, border_radius=self.radius)

        # Render text
        text_surface = self.font.render(self.text, True, clr.BUTTON_TEXT)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
