"""Base class for application pages."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk


class Page(ctk.CTkFrame):
    """A page that is shown in the main content area."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._tick_job: str | None = None

    def on_show(self, **kwargs) -> None:
        """Called each time the page becomes visible."""

    def on_hide(self) -> None:
        self.stop_ticking()

    def clear_sensitive(self) -> None:
        """Remove any decrypted content from widgets. Called when the app locks."""

    def start_ticking(self, callback: Callable[[], None], interval_ms: int = 1000) -> None:
        self.stop_ticking()

        def run() -> None:
            callback()
            self._tick_job = self.after(interval_ms, run)

        self._tick_job = self.after(interval_ms, run)

    def stop_ticking(self) -> None:
        if self._tick_job is not None:
            try:
                self.after_cancel(self._tick_job)
            except Exception:  # widget may already be gone
                pass
            self._tick_job = None
