"""Project ECHO entry point."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def data_directory() -> Path:
    """Per-user application data folder (%LOCALAPPDATA%\\ProjectECHO on Windows)."""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) / "ProjectECHO" if base else Path.home() / ".project_echo"
    if os.environ.get("ECHO_DATA_DIR"):
        root = Path(os.environ["ECHO_DATA_DIR"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def configure_logging(folder: Path) -> None:
    """Log events and errors only. Capsule titles and text are never logged."""
    logging.basicConfig(
        filename=folder / "echo.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    folder = data_directory()
    configure_logging(folder)
    try:
        from database import Database
        from services.backup_service import BackupService
        from services.capsule_service import CapsuleService
        from services.security_service import SecurityService
        from services.settings_service import SettingsService
        from ui.app import EchoApp
    except ImportError as exc:
        print(f"Missing dependency: {exc}\nRun: pip install -r requirements.txt", file=sys.stderr)
        return 1

    db = Database(folder / "echo.db")
    security = SecurityService(db)
    app = EchoApp(security, CapsuleService(db, security), BackupService(db, security), SettingsService(db))
    try:
        app.mainloop()
    finally:
        security.lock()
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
