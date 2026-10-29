from __future__ import annotations

import logging
import time

import customtkinter as ctk

from services.backup_service import BackupError, BackupService
from services.capsule_service import CapsuleService
from services.security_service import SecurityService
from services.settings_service import SettingsService
from ui import theme
from ui.components import button, label
from ui.login import LoginView
from ui.pages.base import Page
from ui.pages.dashboard import DashboardPage
from ui.pages.detail import DetailPage
from ui.pages.library import LibraryPage
from ui.pages.reflection import ReflectionPage
from ui.pages.settings import SettingsPage
from ui.pages.timeline import TimelinePage
from ui.pages.write import WritePage

log = logging.getLogger("echo.ui")

NAV = (
    ("dashboard", "Dashboard", "◈"), ("write", "New capsule", "✎"), ("library", "Library", "▤"),
    ("timeline", "Timeline", "≣"), ("reflection", "Reflection", "◐"), ("settings", "Settings", "⚙"),
)
SIDEBAR_OPEN, SIDEBAR_CLOSED = 224, 72


class EchoApp(ctk.CTk):
    def __init__(self, security: SecurityService, capsules: CapsuleService,
                 backup: BackupService, settings: SettingsService) -> None:
        super().__init__()
        self.security, self.capsules, self.backup, self.settings = security, capsules, backup, settings
        self.pending_restore: str | None = None
        self.current: str | None = None
        self._last_activity = time.monotonic()
        self._toast_job: str | None = None
        self._sidebar_open = True

        ctk.set_appearance_mode(settings.load().appearance)
        theme.init_fonts()
        self.title("Project ECHO")
        self.minsize(980, 660)
        width, height = 1220, 780
        self.geometry(f"{width}x{height}+{max((self.winfo_screenwidth() - width) // 2, 0)}+"
                      f"{max((self.winfo_screenheight() - height) // 3, 0)}")
        self.configure(fg_color=theme.BG)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self.host = ctk.CTkFrame(self.main, fg_color=theme.BG, corner_radius=0)
        self.host.grid(row=0, column=1, sticky="nsew")
        self.host.grid_rowconfigure(0, weight=1)
        self.host.grid_columnconfigure(0, weight=1)
        self.pages: dict[str, Page] = {
            "dashboard": DashboardPage(self.host, self), "write": WritePage(self.host, self),
            "library": LibraryPage(self.host, self), "timeline": TimelinePage(self.host, self),
            "reflection": ReflectionPage(self.host, self), "settings": SettingsPage(self.host, self),
            "detail": DetailPage(self.host, self),
        }
        self.toast = ctk.CTkLabel(self.host, text="", font=theme.fonts.bold, corner_radius=10,
                                  text_color=theme.ON_ACCENT, height=36)

        self.auth = LoginView(self, self)
        self.auth.grid(row=0, column=0, sticky="nsew")

        for sequence in ("<Key>", "<Button>", "<Motion>"):
            self.bind_all(sequence, self._touch, add="+")
        self._bind_shortcuts()
        self.after(5000, self._check_idle)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self.main, fg_color=theme.SIDEBAR, corner_radius=0, width=SIDEBAR_OPEN)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.logo = label(self.sidebar, "E C H O", style="logo", color=theme.CYAN)
        self.logo.pack(anchor="w", padx=22, pady=(26, 22))
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for key, text, glyph in NAV:
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {glyph}   {text}", anchor="w", height=42, corner_radius=10,
                fg_color="transparent", hover_color=theme.CARD_HOVER, text_color=theme.TEXT,
                font=theme.fonts.body, command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = btn
        self.collapse_btn = button(self.sidebar, "« Collapse", self.toggle_sidebar, kind="ghost", width=100, anchor="w")
        self.collapse_btn.pack(side="bottom", fill="x", padx=12, pady=(0, 18))
        self.lock_btn = button(self.sidebar, "Lock  (Ctrl+L)", self.lock, kind="secondary", width=100)
        self.lock_btn.pack(side="bottom", fill="x", padx=12, pady=6)

    def toggle_sidebar(self) -> None:
        self._sidebar_open = not self._sidebar_open
        self.sidebar.configure(width=SIDEBAR_OPEN if self._sidebar_open else SIDEBAR_CLOSED)
        self.logo.configure(text="E C H O" if self._sidebar_open else "E")
        for key, text, glyph in NAV:
            self.nav_buttons[key].configure(text=f"  {glyph}   {text}" if self._sidebar_open else f" {glyph}")
        self.collapse_btn.configure(text="« Collapse" if self._sidebar_open else "»")
        self.lock_btn.configure(text="Lock  (Ctrl+L)" if self._sidebar_open else "Lock")

    def show_page(self, name: str, **kwargs) -> None:
        if not self.security.is_unlocked:
            return
        if self.current:
            self.pages[self.current].on_hide()
            self.pages[self.current].grid_remove()
        self.current = name
        page = self.pages[name]
        page.grid(row=0, column=0, sticky="nsew")
        highlight = kwargs.get("back", "library") if name == "detail" else name
        for key, btn in self.nav_buttons.items():
            btn.configure(fg_color=theme.ACCENT_SOFT if key == highlight else "transparent")
        try:
            page.on_show(**kwargs)
        except Exception:
            log.exception("Page %s failed to load", name)
            self.notify("Something went wrong loading that page.", "error")

    def notify(self, message: str, kind: str = "info") -> None:
        """Show a brief message. Never pass capsule content here."""
        color = {"success": theme.SUCCESS, "error": theme.DANGER}.get(kind, theme.ACCENT)
        self.toast.configure(text=f"  {message}  ", fg_color=color)
        self.toast.place(relx=1.0, rely=1.0, anchor="se", x=-24, y=-24)
        self.toast.lift()
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(3500, self.toast.place_forget)

    def focus_search(self) -> None:
        self.show_page("library")
        self.pages["library"].focus_search()

    def on_unlocked(self) -> None:
        self.auth.grid_remove()
        self.main.grid(row=0, column=0, sticky="nsew")
        self._touch()
        self.show_page("dashboard")
        if self.pending_restore:
            path, self.pending_restore = self.pending_restore, None
            try:
                result = self.backup.import_backup(path)
                self.notify(f"Backup restored: {result.added} capsule(s) added.", "success")
                self.show_page("dashboard")
            except BackupError as exc:
                self.notify(f"Backup not imported: {exc}", "error")

    def lock(self) -> None:
        """Lock the vault and wipe decrypted content from the interface."""
        if not self.security.is_unlocked:
            return
        for page in self.pages.values():
            page.on_hide()
            page.clear_sensitive()
        self.security.lock()
        self.current = None
        self.toast.place_forget()
        for page in self.pages.values():
            page.grid_remove()
        self.main.grid_remove()
        self.auth.grid(row=0, column=0, sticky="nsew")
        self.auth.refresh_mode()

    def _touch(self, _event=None) -> None:
        self._last_activity = time.monotonic()

    def _check_idle(self) -> None:
        if self.security.is_unlocked:
            limit = self.settings.load().inactivity_minutes * 60
            if time.monotonic() - self._last_activity >= limit:
                self.lock()
        self.after(5000, self._check_idle)

    def _close(self) -> None:
        self.security.lock()
        self.destroy()

    def _bind_shortcuts(self) -> None:
        def guarded(action):
            def handler(_event=None):
                if self.security.is_unlocked:
                    action()
                return "break"
            return handler

        for sequence, action in {
            "<Control-n>": lambda: self.show_page("write"),
            "<Control-f>": self.focus_search,
            "<Control-l>": self.lock,
            "<Control-b>": self.toggle_sidebar,
            "<Control-s>": lambda: self.pages["write"].save() if self.current == "write" else None,
            **{f"<Control-Key-{i + 1}>": (lambda k=k: self.show_page(k)) for i, (k, _t, _g) in enumerate(NAV)},
        }.items():
            self.bind_all(sequence, guarded(action))
