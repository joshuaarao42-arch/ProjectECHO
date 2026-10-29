"""Colours, fonts and layout constants. Colours are (light, dark) pairs."""
from __future__ import annotations

from types import SimpleNamespace

import customtkinter as ctk

BG = ("#F4F7FF", "#101522")
SIDEBAR = ("#E9EEFA", "#151C2D")
CARD = ("#FFFFFF", "#1B2438")
CARD_HOVER = ("#EDF2FF", "#252F48")
BORDER = ("#D5DDF0", "#35415C")
INPUT = ("#F4F6FC", "#171F32")
ACCENT = ("#3858D6", "#5268CE")
ACCENT_HOVER = ("#2E49BF", "#4358B6")
ACCENT_SOFT = ("#E2E9FF", "#27345B")
CYAN = ("#2863B6", "#8FB5FF")
TEXT = ("#19243A", "#EEF2FF")
MUTED = ("#59657C", "#A9B6D0")
DANGER = ("#B42338", "#F17B86")
DANGER_HOVER = ("#951B2D", "#D96573")
SUCCESS = ("#287A56", "#6BCB9A")
ON_ACCENT = "#FFFFFF"

RADIUS = 14
PAD = 24

fonts = SimpleNamespace()


def init_fonts() -> None:
    """Create fonts. Must be called after the root window exists."""
    family = "Segoe UI"
    fonts.title = ctk.CTkFont(family=family, size=28, weight="bold")
    fonts.heading = ctk.CTkFont(family=family, size=18, weight="bold")
    fonts.body = ctk.CTkFont(family=family, size=14)
    fonts.bold = ctk.CTkFont(family=family, size=14, weight="bold")
    fonts.small = ctk.CTkFont(family=family, size=13)
    fonts.caption = ctk.CTkFont(family=family, size=12, weight="bold")
    fonts.stat = ctk.CTkFont(family=family, size=34, weight="bold")
    fonts.countdown = ctk.CTkFont(family="Consolas", size=28, weight="bold")
    fonts.editor = ctk.CTkFont(family="Georgia", size=16)
    fonts.logo = ctk.CTkFont(family=family, size=22, weight="bold")
    fonts.logo_big = ctk.CTkFont(family=family, size=40, weight="bold")
