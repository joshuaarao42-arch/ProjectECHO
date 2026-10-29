"""Reflection: rule-based statistics and side-by-side comparison."""
from __future__ import annotations

import customtkinter as ctk

from models import CapsuleFilter
from services.capsule_service import CapsuleLockedError
from ui import theme
from ui.components import Card, PageHeader, StatCard, button, label, muted, option_menu
from ui.pages.base import Page
from utils import dates


class ReflectionPage(Page):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        pad = theme.PAD
        PageHeader(self, "Reflection",
                   "Simple, transparent statistics from what you have saved. Counts only, never conclusions."
                   ).grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, 8))
        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_selected_color=theme.ACCENT,
                                   segmented_button_selected_hover_color=theme.ACCENT_HOVER,
                                   segmented_button_unselected_color=theme.INPUT,
                                   segmented_button_unselected_hover_color=theme.CARD_HOVER,
                                   text_color=theme.TEXT)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=pad - 6, pady=(0, pad - 6))
        self.insights = self.tabs.add("Insights")
        self.compare_tab = self.tabs.add("Compare entries")
        self.insights.grid_columnconfigure(0, weight=1)
        self.insights.grid_rowconfigure(0, weight=1)
        self.scroll = ctk.CTkScrollableFrame(self.insights, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure((0, 1, 2), weight=1, uniform="s")
        self._build_compare()
        self._choices: dict[str, int] = {}

    def on_show(self, **kwargs) -> None:
        self._render_insights()
        self._load_options()

    def _render_insights(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        report = self.app.capsules.reflection_report()
        for col, (caption, value) in enumerate((
                ("Capsules", str(report.total)),
                ("Avg days between", "-" if report.average_gap_days is None else f"{report.average_gap_days:.1f}"),
                ("Active months", str(len(report.by_month))))):
            StatCard(self.scroll, caption, value).grid(row=0, column=col, sticky="nsew", padx=6, pady=6)

        summary = Card(self.scroll)
        summary.grid(row=1, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        label(summary, "Summary", style="heading").pack(anchor="w", padx=18, pady=(14, 6))
        for line in report.summary_lines:
            label(summary, "•  " + line, style="body", wraplength=760).pack(anchor="w", padx=18, pady=2)
        muted(summary, report.disclaimer, style="caption", wraplength=760).pack(anchor="w", padx=18, pady=(8, 14))

        self._bars("Writing frequency (capsules per month)", report.by_month, 2, 0)
        self._bars("Categories", report.by_category, 2, 1)
        self._bars("Most used tags (unlocked entries)", dict(report.top_tags), 2, 2)

    def _bars(self, title: str, data: dict[str, int], row: int, col: int) -> None:
        card = Card(self.scroll)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        label(card, title, style="bold", wraplength=230).pack(anchor="w", padx=14, pady=(12, 6))
        if not data:
            muted(card, "Nothing to show yet.").pack(anchor="w", padx=14, pady=(0, 14))
            return
        peak = max(data.values())
        for name, count in list(data.items())[-8:] if title.startswith("Writing") else list(data.items()):
            row_frame = ctk.CTkFrame(card, fg_color="transparent")
            row_frame.pack(fill="x", padx=14, pady=2)
            top = ctk.CTkFrame(row_frame, fg_color="transparent")
            top.pack(fill="x")
            muted(top, name, wraplength=170).pack(side="left")
            muted(top, str(count)).pack(side="right")
            bar = ctk.CTkProgressBar(row_frame, height=6, progress_color=theme.CYAN, fg_color=theme.INPUT)
            bar.set(count / peak)
            bar.pack(fill="x")
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    def _build_compare(self) -> None:
        tab = self.compare_tab
        tab.grid_columnconfigure((0, 1), weight=1, uniform="c")
        tab.grid_rowconfigure(2, weight=1)
        muted(tab, "Choose two unlocked entries to read side by side.", style="body").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(4, 6))
        self.pick_a = option_menu(tab, ["(none)"])
        self.pick_b = option_menu(tab, ["(none)"])
        self.pick_a.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.pick_b.grid(row=1, column=1, sticky="ew", padx=(6, 0))
        self.boxes = []
        for col in range(2):
            box = ctk.CTkTextbox(tab, wrap="word", font=theme.fonts.editor, fg_color=theme.CARD,
                                 text_color=theme.TEXT, border_width=1, border_color=theme.BORDER,
                                 corner_radius=theme.RADIUS, state="disabled")
            box.grid(row=2, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0), pady=8)
            self.boxes.append(box)
        foot = ctk.CTkFrame(tab, fg_color="transparent")
        foot.grid(row=3, column=0, columnspan=2, sticky="ew")
        foot.grid_columnconfigure(1, weight=1)
        button(foot, "Compare", self._compare, width=120).grid(row=0, column=0)
        self.result = label(foot, "", style="body")
        self.result.grid(row=0, column=1, sticky="w", padx=12)

    def _load_options(self) -> None:
        summaries = self.app.capsules.list_capsules(CapsuleFilter(view="unlocked", sort_by="created", descending=False))
        self._choices = {f"{s.title}  ·  {dates.format_date(s.created_at)}  ·  #{s.id}": s.id for s in summaries}
        names = list(self._choices) or ["(no unlocked entries)"]
        for menu, default in ((self.pick_a, names[0]), (self.pick_b, names[-1])):
            menu.configure(values=names)
            menu.set(default)

    def _set_box(self, box: ctk.CTkTextbox, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _compare(self) -> None:
        a, b = self._choices.get(self.pick_a.get()), self._choices.get(self.pick_b.get())
        if a is None or b is None:
            self.result.configure(text="You need at least two unlocked entries.", text_color=theme.DANGER)
            return
        try:
            cmp = self.app.capsules.compare(a, b)
        except ValueError as exc:
            self.result.configure(text=str(exc), text_color=theme.DANGER)
            return
        except CapsuleLockedError as exc:
            self.result.configure(text=str(exc), text_color=theme.DANGER)
            return
        for box, detail in zip(self.boxes, (cmp.first, cmp.second)):
            s = detail.summary
            header = f"{s.title}\n{dates.format_datetime(s.created_at)}  ·  {len(detail.body.split())} words\n\n"
            self._set_box(box, header + detail.body)
        self.result.configure(text=f"Written {cmp.elapsed_text} apart.", text_color=theme.TEXT)

    def clear_sensitive(self) -> None:
        for box in self.boxes:
            self._set_box(box, "")
        self.result.configure(text="")
        for child in self.scroll.winfo_children():
            child.destroy()
        self._choices = {}
