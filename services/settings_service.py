"""Persistent application settings."""
from __future__ import annotations

from database import Database
from models import AppSettings

INACTIVITY_CHOICES = (1, 5, 10, 15, 30, 60)
APPEARANCE_CHOICES = ("dark", "light", "system")


class SettingsService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def load(self) -> AppSettings:
        try:
            minutes = int(self._db.get_setting("inactivity_minutes", "5") or 5)
        except ValueError:
            minutes = 5
        if minutes not in INACTIVITY_CHOICES:
            minutes = 5
        appearance = self._db.get_setting("appearance", "light")
        if appearance not in APPEARANCE_CHOICES:
            appearance = "light"
        return AppSettings(inactivity_minutes=minutes, appearance=appearance)

    def set_inactivity_minutes(self, minutes: int) -> None:
        if minutes not in INACTIVITY_CHOICES:
            raise ValueError("Unsupported timeout.")
        self._db.set_setting("inactivity_minutes", str(minutes))

    def set_appearance(self, mode: str) -> None:
        if mode not in APPEARANCE_CHOICES:
            raise ValueError("Unsupported appearance mode.")
        self._db.set_setting("appearance", mode)
