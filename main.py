"""
CityMind - An Urban Intelligence System
Entry point. Launch the Pygame application.

Usage:
    python main.py
"""

from ui.app import CityMindApp


if __name__ == "__main__":
    app = CityMindApp()
    app.run()
