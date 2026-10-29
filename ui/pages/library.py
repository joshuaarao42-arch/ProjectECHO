"""Memory library: searchable, filterable card grid."""
from __future__ import annotations

from datetime import datetime, time

import customtkinter as ctk

from models import CATEGORIES, CapsuleFilter
from ui import theme
from ui.components import (CapsuleCard, DateField, EmptyState, PageHeader, button, entry, label,
                           muted, option_menu, segmented)
from ui.pages.base import Page

VIEWS = {"All": "all", "Locked": "locked", "Unlocked": "unlocked", "Favorites": "favorites", "Archived": "archived"}
SORTS = {
    "Newest created": ("created", True), "Oldest created": ("created", False),
    "Unlocks soonest": ("unlock", False), "Unlocks latest": ("unlock", True),
}
ALL_CATEGORIES = "All categories"


class LibraryPage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        pad = theme.PAD
        PageHeader(self, "Memory library", "Search, filter and revisit everything you have sealed.",
                   actions=[("New capsule", lambda: app.show_page("write"), "primary")]
                   ).grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, 10))

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=pad, pady=(0, 6))
        filters.grid_columnconfigure(0, weight=1)
        self.search = entry(filters, "Search titles and #tags")
        self.search.grid(row=0, column=0, sticky="ew")
        self.search.bind("<KeyRelease>", lambda _e: self._debounce())
        self.category = option_menu(filters, [ALL_CATEGORIES, *CATEGORIES], command=lambda _v: self.refresh(), width=190)
        self.category.grid(row=0, column=1, padx=(8, 0))
        self.sort = option_menu(filters, list(SORTS), command=lambda _v: self.refresh(), width=150)
        self.sort.grid(row=0, column=2, padx=(8, 0))
        self.view = segmented(filters, list(VIEWS), command=lambda _v: self.refresh(), height=34)
        self.view.set("All")
        self.view.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        dates_row = ctk.CTkFrame(filters, fg_color="transparent")
        dates_row.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        muted(dates_row, "Unlocks from").pack(side="left", padx=(0, 6))
        self.date_from = DateField(dates_row, width=110, on_change=self.refresh)
        self.date_from.pack(side="left")
        muted(dates_row, "to").pack(side="left", padx=8)
        self.date_to = DateField(dates_row, width=110, on_change=self.refresh)
        self.date_to.pack(side="left")
        button(dates_row, "Clear filters", self.reset_filters, kind="ghost", width=100).pack(side="left", padx=(10, 0))
        self.status = muted(dates_row, "")
        self.status.pack(side="left", padx=12)

        self.results = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results.grid(row=2, column=0, sticky="nsew", padx=(pad - 8, pad - 14), pady=(6, pad - 8))
        self._cards: list[CapsuleCard] = []
        self._cols = 0
        self._job: str | None = None
        self.bind("<Configure>", lambda _e: self._reflow())

    def focus_search(self) -> None:
        self.search.focus_set()

    def reset_filters(self) -> None:
        self.search.delete(0, "end")
        self.category.set(ALL_CATEGORIES)
        self.view.set("All")
        self.sort.set("Newest created")
        self.date_from.set_date(None)
        self.date_to.set_date(None)
        self.refresh()

    def _debounce(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self.refresh)

    def _current_filter(self) -> CapsuleFilter:
        sort_by, descending = SORTS[self.sort.get()]
        flt = CapsuleFilter(
            query=self.search.get(),
            category=None if self.category.get() == ALL_CATEGORIES else self.category.get(),
            view=VIEWS[self.view.get()], sort_by=sort_by, descending=descending)
        self.status.configure(text="")
        try:
            start, end = self.date_from.get_date(), self.date_to.get_date()
            flt.date_from = datetime.combine(start, time()) if start else None
            flt.date_to = datetime.combine(end, time()) if end else None
        except ValueError:
            self.status.configure(text="Date filter ignored: use YYYY-MM-DD.", text_color=theme.DANGER)
        return flt

    def on_show(self, **kwargs) -> None:
        self.refresh()

    def refresh(self) -> None:
        self._job = None
        for child in self.results.winfo_children():
            child.destroy()
        self._cards = []
        now = self.app.capsules.now()
        summaries = self.app.capsules.list_capsules(self._current_filter())
        if not summaries:
            empty = EmptyState(
                self.results, "Nothing here yet",
                "No capsules match these filters. Try clearing them, or seal a new one.",
                ("Write a capsule", lambda: self.app.show_page("write"), "primary"))
            empty.grid(row=0, column=0, sticky="ew", padx=8, pady=16)
            self.results.grid_columnconfigure(0, weight=1)
            self._cols = 0
            return
        for summary in summaries:
            self._cards.append(CapsuleCard(self.results, summary, now, self._open, self._favorite))
        self._cols = 0
        self._reflow()

    def _reflow(self) -> None:
        if not self._cards:
            return
        width = max(self.winfo_width() - 2 * theme.PAD, 300)
        cols = max(1, min(4, width // 320))
        if cols == self._cols:
            return
        self._cols = cols
        for index in range(5):
            self.results.grid_columnconfigure(index, weight=1 if index < cols else 0, uniform="cards" if index < cols else "")
        for index, card in enumerate(self._cards):
            card.grid(row=index // cols, column=index % cols, sticky="nsew", padx=8, pady=8)

    def _open(self, capsule_id: int) -> None:
        self.app.show_page("detail", capsule_id=capsule_id, back="library")

    def _favorite(self, capsule_id: int, value: bool) -> None:
        self.app.capsules.set_favorite(capsule_id, value)
        self.refresh()

    def clear_sensitive(self) -> None:
        for child in self.results.winfo_children():
            child.destroy()
        self._cards = []
        self._cols = 0
        self.search.delete(0, "end")
