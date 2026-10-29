"""Chronological timeline of sealing and unlock events."""
from __future__ import annotations

import customtkinter as ctk

from ui import theme
from ui.components import Card, EmptyState, PageHeader, button, label, muted, segmented
from ui.pages.base import Page
from utils import dates


class TimelinePage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        pad = theme.PAD
        PageHeader(self, "Memory timeline",
                   "Every capsule you sealed and every unlock to come, in order. Upcoming unlocks are highlighted."
                   ).grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, 10))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=pad)
        self.order = segmented(bar, ["Upcoming first", "Oldest first"], command=lambda _v: self.refresh())
        self.order.set("Upcoming first")
        self.order.pack(side="left")
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=(pad - 8, pad - 14), pady=(8, pad - 8))
        self.body.grid_columnconfigure(0, weight=1)

    def on_show(self, **kwargs) -> None:
        self.refresh()

    def clear_sensitive(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def refresh(self) -> None:
        self.clear_sensitive()
        caps = self.app.capsules
        now = caps.now()
        summaries = caps.list_capsules()
        if not summaries:
            EmptyState(self.body, "Your timeline is empty", "Sealed capsules and their unlock dates will appear here.",
                       ("Write a capsule", lambda: self.app.show_page("write"), "primary")
                       ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            return
        events = []
        for s in summaries:
            events.append((s.created_at, "created", s))
            events.append((s.unlock_at, "unlock", s))
        events.append((now, "now", None))
        events.sort(key=lambda e: e[0], reverse=self.order.get() == "Upcoming first")

        for row, (moment, kind, s) in enumerate(events):
            frame = ctk.CTkFrame(self.body, fg_color="transparent")
            frame.grid(row=row, column=0, sticky="ew")
            frame.grid_columnconfigure(2, weight=1)
            muted(frame, dates.format_date(moment), style="small", anchor="e", width=96).grid(
                row=0, column=0, sticky="ne", padx=(4, 8), pady=(14, 0))
            rail = ctk.CTkFrame(frame, fg_color="transparent", width=18)
            rail.grid(row=0, column=1, sticky="ns")
            ctk.CTkFrame(rail, width=2, fg_color=theme.BORDER, corner_radius=0).place(relx=0.5, rely=0, relheight=1, anchor="n")
            upcoming = kind == "unlock" and moment > now
            milestone = s is not None and s.category == "Milestone"
            dot_color = theme.CYAN if upcoming or kind == "now" else (theme.ACCENT if milestone else theme.MUTED)
            ctk.CTkFrame(rail, width=12, height=12, corner_radius=6, fg_color=dot_color).place(relx=0.5, y=20, anchor="center")

            if kind == "now":
                label(frame, "Today", style="bold", color=theme.CYAN).grid(row=0, column=2, sticky="w", padx=12, pady=(12, 0))
                continue
            card = Card(frame, border_color=theme.CYAN if upcoming else theme.BORDER)
            card.grid(row=0, column=2, sticky="ew", padx=(8, 8), pady=6)
            card.grid_columnconfigure(0, weight=1)
            verb = "Sealed" if kind == "created" else ("Unlocks" if upcoming else "Unlocked")
            tag = f"{verb}  ·  {s.category}" + ("  ·  Milestone" if milestone and s.category != "Milestone" else "")
            muted(card, tag.upper(), style="caption").grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))
            label(card, s.title, style="bold", wraplength=520).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
            eligible = kind == "unlock" and not upcoming
            button(card, "Open" if eligible else "View", lambda sid=s.id: self.app.show_page("detail", capsule_id=sid, back="timeline"),
                   kind="primary" if eligible else "secondary", width=80, height=30).grid(row=0, column=1, rowspan=2, padx=12)
