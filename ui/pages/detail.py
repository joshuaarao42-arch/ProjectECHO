"""Capsule detail view."""
from __future__ import annotations

import customtkinter as ctk

from services.capsule_service import CapsuleLockedError, CapsuleNotFoundError
from ui import theme
from ui.components import Card, ask_confirm, button, label, muted
from ui.pages.base import Page
from utils import dates


class DetailPage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.capsule_id: int | None = None
        self.back = "library"
        self._unlock_at = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=0, sticky="nsew", padx=theme.PAD, pady=theme.PAD)
        self.content.grid_columnconfigure(0, weight=1)
        self._countdown: ctk.CTkLabel | None = None

    def on_show(self, capsule_id: int | None = None, back: str | None = None, **kwargs) -> None:
        if capsule_id is not None:
            self.capsule_id = capsule_id
        if back:
            self.back = back
        self.render()

    def _go_back(self) -> None:
        self.app.show_page(self.back)

    def clear_sensitive(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self._countdown = None

    def render(self) -> None:
        self.stop_ticking()
        self.clear_sensitive()
        self.content.grid_rowconfigure(2, weight=0)
        caps = self.app.capsules
        try:
            summary = caps.get_summary(self.capsule_id)
        except CapsuleNotFoundError:
            self._go_back()
            return
        now = caps.now()
        locked = summary.is_locked(now)

        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        button(top, "‹ Back", self._go_back, kind="ghost", width=70).grid(row=0, column=0, padx=(0, 8))
        label(top, summary.title, style="title", wraplength=640).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(top, text="LOCKED" if locked else ("OPENED" if summary.opened_at else "READY TO OPEN"),
                     font=theme.fonts.caption, height=24, width=96, corner_radius=8,
                     fg_color=theme.ACCENT if locked else theme.ACCENT_SOFT,
                     text_color=theme.ON_ACCENT if locked else theme.TEXT).grid(row=0, column=2, padx=(8, 0))

        meta = Card(self.content)
        meta.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        for col in range(4):
            meta.grid_columnconfigure(col, weight=1, uniform="meta")
        facts = [("Category", summary.category), ("Sealed", dates.format_datetime(summary.created_at)),
                 ("Unlocks", dates.format_datetime(summary.unlock_at)),
                 ("Tags", "  ".join(f"#{t}" for t in summary.tags) or "None")]
        for col, (name, value) in enumerate(facts):
            muted(meta, name.upper(), style="caption").grid(row=0, column=col, sticky="w", padx=16, pady=(12, 0))
            label(meta, value, style="body", wraplength=200).grid(row=1, column=col, sticky="w", padx=16, pady=(0, 12))

        if locked:
            panel = Card(self.content)
            panel.grid(row=2, column=0, sticky="ew", pady=8)
            label(panel, "This capsule is sealed", style="heading", anchor="center", justify="center").pack(pady=(28, 4))
            muted(panel, f"Its contents stay hidden until {dates.format_datetime(summary.unlock_at)}.",
                  style="body", anchor="center", justify="center").pack()
            self._countdown = label(panel, "", style="countdown", color=theme.CYAN, anchor="center", justify="center")
            self._countdown.pack(pady=(14, 30))
            self._unlock_at = summary.unlock_at
            self._tick()
            self.start_ticking(self._tick)
        elif summary.opened_at is None:
            panel = Card(self.content)
            panel.grid(row=2, column=0, sticky="ew", pady=8)
            label(panel, "Ready to open", style="heading", anchor="center", justify="center").pack(pady=(28, 4))
            muted(panel, "Take a moment. When you are ready, open the capsule and read what you wrote.",
                  style="body", anchor="center", justify="center").pack()
            button(panel, "Open capsule", self._open, width=170).pack(pady=(16, 30))
        else:
            self._show_body()

        actions = ctk.CTkFrame(self.content, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        button(actions, "Remove favorite" if summary.favorite else "Add to favorites",
               lambda: self._toggle("favorite", summary), kind="secondary", width=150).pack(side="left")
        button(actions, "Unarchive" if summary.archived else "Archive",
               lambda: self._toggle("archived", summary), kind="secondary", width=110).pack(side="left", padx=8)
        button(actions, "Delete", self._delete, kind="danger", width=100).pack(side="right")

    def _show_body(self) -> None:
        try:
            detail = self.app.capsules.open_capsule(self.capsule_id)
        except CapsuleLockedError:
            self.render()
            return
        self.content.grid_rowconfigure(2, weight=1)
        self.content.grid_rowconfigure(3, weight=0)
        box = ctk.CTkTextbox(self.content, wrap="word", font=theme.fonts.editor, fg_color=theme.CARD,
                             text_color=theme.TEXT, border_width=1, border_color=theme.BORDER,
                             corner_radius=theme.RADIUS, spacing3=6)
        box.grid(row=2, column=0, sticky="nsew", pady=8)
        box.insert("1.0", detail.body)
        box.configure(state="disabled")

    def _open(self) -> None:
        self.render()
        try:
            self.app.capsules.open_capsule(self.capsule_id)
        except CapsuleLockedError:
            return
        self.render()

    def _tick(self) -> None:
        if self._countdown is None or self._unlock_at is None:
            return
        remaining = self._unlock_at - self.app.capsules.now()
        if remaining.total_seconds() <= 0:
            self.render()
            return
        self._countdown.configure(text=dates.format_countdown(remaining))

    def _toggle(self, field: str, summary) -> None:
        if field == "favorite":
            self.app.capsules.set_favorite(summary.id, not summary.favorite)
        else:
            self.app.capsules.set_archived(summary.id, not summary.archived)
        self.render()

    def _delete(self) -> None:
        if ask_confirm(self, "Delete this capsule?", "It will be permanently removed from this device. "
                       "This cannot be undone.", "Delete", danger=True):
            self.app.capsules.delete_capsule(self.capsule_id)
            self.app.notify("Capsule deleted.")
            self._go_back()
