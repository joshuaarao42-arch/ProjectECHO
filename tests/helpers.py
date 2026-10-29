"""Shared test fixtures."""
from __future__ import annotations

from datetime import datetime, timedelta

from database import Database
from services.backup_service import BackupService
from services.capsule_service import CapsuleService
from services.security_service import SecurityService

PASSWORD = "correct horse battery"


class FakeClock:
    """A controllable clock so unlock rules can be tested deterministically."""

    def __init__(self, start: datetime = datetime(2026, 1, 1, 9, 0, 0)) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **kwargs: int) -> None:
        self.current += timedelta(**kwargs)


class Vault:
    """An in-memory database with unlocked services."""

    def __init__(self, db: Database | None = None, *, setup: bool = True) -> None:
        self.clock = FakeClock()
        self.db = db or Database(":memory:")
        self.security = SecurityService(self.db, kdf_n=2**10)  # fast KDF for tests
        if setup:
            self.security.setup(PASSWORD)
        self.capsules = CapsuleService(self.db, self.security, clock=self.clock)
        self.backup = BackupService(self.db, self.security)

    def make(self, title="Hello", days=30, category="Letter to Future Self", tags="a, b", body="Secret body text"):
        return self.capsules.create_capsule(
            title=title, body=body, category=category, tags=tags,
            unlock_at=self.clock.current + timedelta(days=days))
