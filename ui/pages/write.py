"""Distraction-free writing page."""
from __future__ import annotations

import logging
from datetime import date, timedelta

import customtkinter as ctk

from models import CATEGORIES
from ui import theme
from ui.components import (Card, DateField, PageHeader, ask_confirm, button, entry, label,
                           muted, option_menu)
from ui.pages.base import Page
from utils import dates
from utils.validation import ValidationError, validate_capsule_input

log = logging.getLogger("echo.ui.write")
PRESETS = (("1 month", 1), ("6 months", 6), ("1 year", 12), ("5 years", 60))


class WritePage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        pad = theme.PAD
        PageHeader(self, "New capsule",
                   "Write to the person you will become. Once sealed, a capsule cannot be edited or opened early."
                   ).grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, 10))

        meta = Card(self)
        meta.grid(row=1, column=0, sticky="ew", padx=pad, pady=6)
        meta.grid_columnconfigure(0, weight=3, uniform="m")
        meta.grid_columnconfigure(1, weight=2, uniform="m")
        meta.grid_columnconfigure(2, weight=2, uniform="m")
        muted(meta, "Title").grid(row=0, column=0, sticky="w", padx=16, pady=(14, 0))
        self.title_entry = entry(meta, "A short, memorable title")
        self.title_entry.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(2, 8))
        muted(meta, "Category").grid(row=2, column=0, sticky="w", padx=16)
        muted(meta, "Tags (comma separated)").grid(row=2, column=1, columnspan=2, sticky="w", padx=(8, 16))
        self.category = option_menu(meta, CATEGORIES)
        self.category.grid(row=3, column=0, sticky="ew", padx=16, pady=(2, 8))
        self.tags_entry = entry(meta, "family, goals, spring")
        self.tags_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 16), pady=(2, 8))

        when = ctk.CTkFrame(meta, fg_color="transparent")
        when.grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))
        muted(when, "Unlock date").grid(row=0, column=0, sticky="w")
        muted(when, "Time").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.date_field = DateField(when, min_date=date.today() + timedelta(days=0))
        self.date_field.grid(row=1, column=0, sticky="w")
        self.time_entry = entry(when, "HH:MM", width=80)
        self.time_entry.grid(row=1, column=1, padx=(12, 0))
        presets = ctk.CTkFrame(when, fg_color="transparent")
        presets.grid(row=1, column=2, padx=(16, 0))
        muted(presets, "Quick:").pack(side="left", padx=(0, 6))
        for text, months in PRESETS:
            button(presets, text, lambda m=months: self._preset(m), kind="ghost", width=70, height=30).pack(side="left")

        editor_card = Card(self)
        editor_card.grid(row=2, column=0, sticky="nsew", padx=pad, pady=6)
        editor_card.grid_columnconfigure(0, weight=1)
        editor_card.grid_rowconfigure(0, weight=1)
        self.editor = ctk.CTkTextbox(
            editor_card, wrap="word", font=theme.fonts.editor, fg_color=theme.INPUT,
            text_color=theme.TEXT, border_width=0, corner_radius=10, spacing3=6)
        self.editor.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))
        self.count = muted(editor_card, "0 words", style="caption")
        self.count.grid(row=1, column=0, sticky="e", padx=16, pady=(0, 8))
        self.editor.bind("<KeyRelease>", lambda _e: self._update_count())

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=3, column=0, sticky="ew", padx=pad, pady=(6, pad))
        foot.grid_columnconfigure(0, weight=1)
        self.error = label(foot, "", color=theme.DANGER, wraplength=620)
        self.error.grid(row=0, column=0, sticky="w")
        button(foot, "Clear", self.clear_form, kind="secondary", width=90).grid(row=0, column=1, padx=6)
        button(foot, "Seal capsule  (Ctrl+S)", self.save, width=190).grid(row=0, column=2)
        self.clear_form()

    def on_show(self, prompt: str | None = None, **kwargs) -> None:
        if prompt and not self.editor.get("1.0", "end-1c").strip():
            self.category.set("Journal Entry")
            self.editor.insert("1.0", prompt + "\n\n")
            self._update_count()
        self.title_entry.focus_set()

    def _preset(self, months: int) -> None:
        self.date_field.set_date(dates.add_months(date.today(), months))
        if not self.time_entry.get().strip():
            self.time_entry.insert(0, "09:00")

    def _update_count(self) -> None:
        words = len(self.editor.get("1.0", "end-1c").split())
        self.count.configure(text=f"{words} word{'s' if words != 1 else ''}")

    def clear_form(self) -> None:
        self.title_entry.delete(0, "end")
        self.tags_entry.delete(0, "end")
        self.editor.delete("1.0", "end")
        self.category.set(CATEGORIES[0])
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, "09:00")
        self.date_field.set_date(dates.add_months(date.today(), 1))
        self.error.configure(text="")
        self._update_count()

    clear_sensitive = clear_form

    def save(self) -> None:
        self.error.configure(text="")
        try:
            unlock_at = dates.combine_date_time(self.date_field.get_text(), self.time_entry.get() or "09:00")
        except ValueError as exc:
            self.error.configure(text=str(exc))
            return
        fields = dict(title=self.title_entry.get(), body=self.editor.get("1.0", "end-1c"),
                      category=self.category.get(), tags=self.tags_entry.get(), unlock_at=unlock_at)
        try:  # validate first so the confirmation only appears for sealable input
            validate_capsule_input(**fields, created_at=self.app.capsules.now())
        except ValidationError as exc:
            self.error.configure(text="\n".join(exc.errors.values()))
            return
        if not ask_confirm(self, "Seal this capsule?",
                           f"It will stay closed until {dates.format_datetime(unlock_at)}. "
                           "Sealed capsules cannot be edited.", "Seal capsule"):
            return
        try:
            self.app.capsules.create_capsule(**fields)
        except ValidationError as exc:
            self.error.configure(text="\n".join(exc.errors.values()))
            return
        except Exception:
            log.exception("Saving a capsule failed")
            self.error.configure(text="Something went wrong while saving. Your text is still here.")
            return
        self.clear_form()
        self.app.notify("Capsule sealed.", "success")
        self.app.show_page("library")
