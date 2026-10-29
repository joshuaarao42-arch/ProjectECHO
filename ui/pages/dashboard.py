from __future__ import annotations

import customtkinter as ctk

from ui import theme
from ui.components import Card, PageHeader, StatCard, button, label, muted
from ui.pages.base import Page
from utils import dates

EVENT_TEXT = {"created": "Sealed", "opened": "Opened", "deleted": "Deleted", "imported": "Imported backup"}


class DashboardPage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="col")
        self.body = body
        pad = theme.PAD

        PageHeader(body, "Dashboard", "A quiet overview of the memories you are keeping.",
                   actions=[("New capsule", lambda: app.show_page("write"), "primary")]
                   ).grid(row=0, column=0, columnspan=4, sticky="ew", padx=pad, pady=(pad, 14))

        self.stat_cards = {}
        for col, (key, caption) in enumerate((("total", "Capsules"), ("locked", "Locked"),
                                              ("unlocked", "Unlocked"), ("favorites", "Favorites"))):
            card = StatCard(body, caption)
            card.grid(row=1, column=col, sticky="nsew", padx=(pad if col == 0 else 6, pad if col == 3 else 6), pady=6)
            self.stat_cards[key] = card

        # Next unlock
        self.next_card = Card(body)
        self.next_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(pad, 6), pady=6)
        muted(self.next_card, "NEXT TO UNLOCK", style="caption").pack(anchor="w", padx=20, pady=(18, 0))
        self.next_title = label(self.next_card, "", style="heading", wraplength=380)
        self.next_title.pack(anchor="w", padx=20, pady=(6, 0))
        self.next_date = muted(self.next_card, "")
        self.next_date.pack(anchor="w", padx=20)
        self.next_countdown = label(self.next_card, "", style="countdown", color=theme.CYAN)
        self.next_countdown.pack(anchor="w", padx=20, pady=(10, 16))
        self.next_button = button(self.next_card, "Write a capsule", lambda: app.show_page("write"), kind="secondary", width=150)
        self.next_button.pack(anchor="w", padx=20, pady=(4, 18))

        # Daily reflection
        question = Card(body)
        question.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(6, pad), pady=6)
        muted(question, "TODAY'S REFLECTION", style="caption").pack(anchor="w", padx=20, pady=(18, 0))
        self.question = label(question, "", style="heading", wraplength=380)
        self.question.pack(anchor="w", padx=20, pady=(8, 10))
        button(question, "Write about it", self._write_about_it, kind="secondary", width=150).pack(anchor="w", padx=20, pady=(0, 18))

        # Journey stats
        journey = Card(body)
        journey.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(pad, 6), pady=(6, pad))
        label(journey, "Your journey", style="heading").pack(anchor="w", padx=20, pady=(18, 8))
        self.days_since = self._stat_row(journey, "Days since your first memory")
        self.opened = self._stat_row(journey, "Capsules opened")
        ctk.CTkFrame(journey, height=10, fg_color="transparent").pack()

        # Recent activity
        self.activity_card = Card(body)
        self.activity_card.grid(row=3, column=2, columnspan=2, sticky="nsew", padx=(6, pad), pady=(6, pad))
        label(self.activity_card, "Recent activity", style="heading").pack(anchor="w", padx=20, pady=(18, 8))
        self.activity_box = ctk.CTkFrame(self.activity_card, fg_color="transparent")
        self.activity_box.pack(fill="x", padx=20, pady=(0, 16))
        self._next_unlock = None

    @staticmethod
    def _stat_row(parent, caption: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=3)
        muted(row, caption, style="body").pack(side="left")
        value = label(row, "-", style="bold")
        value.pack(side="right")
        return value

    def _write_about_it(self) -> None:
        self.app.show_page("write", prompt=self.question.cget("text"))

    def on_show(self, **kwargs) -> None:
        caps = self.app.capsules
        stats = caps.dashboard_stats()
        for key in ("total", "locked", "unlocked", "favorites"):
            self.stat_cards[key].set(str(getattr(stats, key)))
        self._next_unlock = stats.next_unlock
        if stats.next_unlock:
            self.next_title.configure(text=stats.next_unlock.title)
            self.next_date.configure(text=f"Opens {dates.format_datetime(stats.next_unlock.unlock_at)}")
            self.next_button.pack_forget()
        else:
            self.next_title.configure(text="Nothing is waiting to unlock")
            self.next_date.configure(text="Seal a letter to your future self to start a countdown.")
            self.next_countdown.configure(text="")
            self.next_button.pack(anchor="w", padx=20, pady=(4, 18))
        self.question.configure(text=caps.daily_question())
        self.days_since.configure(text="-" if stats.days_since_first is None else str(stats.days_since_first))
        self.opened.configure(text=str(stats.opened))

        for child in self.activity_box.winfo_children():
            child.destroy()
        items = caps.recent_activity(6)
        if not items:
            muted(self.activity_box, "Nothing yet. Activity appears here as you write and open capsules.",
                  style="body", wraplength=360).pack(anchor="w")
        for item in items:
            row = ctk.CTkFrame(self.activity_box, fg_color="transparent")
            row.pack(fill="x", pady=2)
            text = EVENT_TEXT.get(item.event, item.event.title())
            title = item.title if item.title else ("a deleted capsule" if item.event == "deleted" else "")
            label(row, f"{text}  {title}".strip(), style="small", wraplength=300).pack(side="left")
            muted(row, dates.format_date(item.timestamp), style="caption").pack(side="right")
        self._tick()
        self.start_ticking(self._tick)

    def _tick(self) -> None:
        target = self._next_unlock
        if not target:
            return
        remaining = target.time_remaining(self.app.capsules.now())
        if remaining.total_seconds() <= 0:
            self.on_show()  # it just unlocked; refresh the whole page
            return
        self.next_countdown.configure(text=dates.format_countdown(remaining))

    def clear_sensitive(self) -> None:
        self.next_title.configure(text="")
        self.next_date.configure(text="")
        self.next_countdown.configure(text="")
        for child in self.activity_box.winfo_children():
            child.destroy()
        self._next_unlock = None
