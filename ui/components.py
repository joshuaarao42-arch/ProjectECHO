from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from typing import Callable, Sequence

import customtkinter as ctk

from models import CapsuleSummary
from ui import theme
from ui.theme import fonts
from utils import dates

ActionSpec = tuple[str, Callable[[], None], str]


class Card(ctk.CTkFrame):
    """A rounded, bordered surface."""

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", theme.CARD)
        kwargs.setdefault("corner_radius", theme.RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.BORDER)
        super().__init__(master, **kwargs)


def label(master, text: str = "", *, style: str = "body", color=None, **kwargs) -> ctk.CTkLabel:
    """A label using one of the theme font styles."""
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    return ctk.CTkLabel(master, text=text, font=getattr(fonts, style),
                        text_color=color or theme.TEXT, **kwargs)


def muted(master, text: str = "", *, style: str = "small", **kwargs) -> ctk.CTkLabel:
    return label(master, text, style=style, color=theme.MUTED, **kwargs)


def button(master, text: str, command: Callable[[], None] | None = None, *,
           kind: str = "primary", width: int = 120, **kwargs) -> ctk.CTkButton:
    """Primary, secondary, danger or ghost button."""
    styles = {
        "primary": dict(fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                        text_color=theme.ON_ACCENT, border_width=0),
        "danger": dict(fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER,
                       text_color=theme.ON_ACCENT, border_width=0),
        "secondary": dict(fg_color="transparent", hover_color=theme.CARD_HOVER,
                          text_color=theme.TEXT, border_width=1, border_color=theme.BORDER),
        "ghost": dict(fg_color="transparent", hover_color=theme.CARD_HOVER,
                      text_color=theme.MUTED, border_width=0),
    }
    opts = {**styles[kind], "font": fonts.bold, "corner_radius": 10, "height": 36, "width": width}
    opts.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **opts)


def entry(master, placeholder: str = "", **kwargs) -> ctk.CTkEntry:
    kwargs.setdefault("fg_color", theme.INPUT)
    kwargs.setdefault("border_color", theme.BORDER)
    kwargs.setdefault("text_color", theme.TEXT)
    kwargs.setdefault("corner_radius", 10)
    kwargs.setdefault("height", 38)
    kwargs.setdefault("font", fonts.body)
    return ctk.CTkEntry(master, placeholder_text=placeholder, **kwargs)


def option_menu(master, values: Sequence[str], command=None, **kwargs) -> ctk.CTkOptionMenu:
    kwargs.setdefault("fg_color", theme.INPUT)
    kwargs.setdefault("button_color", theme.ACCENT)
    kwargs.setdefault("button_hover_color", theme.ACCENT_HOVER)
    kwargs.setdefault("text_color", theme.TEXT)
    kwargs.setdefault("dropdown_fg_color", theme.CARD)
    kwargs.setdefault("dropdown_text_color", theme.TEXT)
    kwargs.setdefault("dropdown_hover_color", theme.CARD_HOVER)
    kwargs.setdefault("corner_radius", 10)
    kwargs.setdefault("height", 38)
    kwargs.setdefault("font", fonts.body)
    kwargs.setdefault("dropdown_font", fonts.body)
    return ctk.CTkOptionMenu(master, values=list(values), command=command, **kwargs)


def segmented(master, values: Sequence[str], command=None, **kwargs) -> ctk.CTkSegmentedButton:
    kwargs.setdefault("fg_color", theme.INPUT)
    kwargs.setdefault("selected_color", theme.ACCENT)
    kwargs.setdefault("selected_hover_color", theme.ACCENT_HOVER)
    kwargs.setdefault("unselected_color", theme.INPUT)
    kwargs.setdefault("unselected_hover_color", theme.CARD_HOVER)
    kwargs.setdefault("text_color", theme.TEXT)
    kwargs.setdefault("font", fonts.small)
    return ctk.CTkSegmentedButton(master, values=list(values), command=command, **kwargs)


class PageHeader(ctk.CTkFrame):
    """Page title, description and primary actions."""

    def __init__(self, master, title: str, subtitle: str = "",
                 actions: Sequence[ActionSpec] = ()) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        label(self, title, style="title").grid(row=0, column=0, sticky="w")
        self.subtitle = muted(self, subtitle, style="body", wraplength=620)
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))
        if actions:
            box = ctk.CTkFrame(self, fg_color="transparent")
            box.grid(row=0, column=1, rowspan=2, sticky="e")
            for text, command, kind in actions:
                button(box, text, command, kind=kind, width=130).pack(side="left", padx=(8, 0))


class StatCard(Card):
    """A single headline figure."""

    def __init__(self, master, caption: str, value: str = "0") -> None:
        super().__init__(master)
        muted(self, caption.upper(), style="caption").pack(anchor="w", padx=18, pady=(16, 0))
        self.value = label(self, value, style="stat")
        self.value.pack(anchor="w", padx=18, pady=(0, 14))

    def set(self, value: str) -> None:
        self.value.configure(text=value)


class EmptyState(Card):
    def __init__(self, master, title: str, message: str,
                 action: ActionSpec | None = None) -> None:
        super().__init__(master)
        label(self, title, style="heading", anchor="center", justify="center").pack(pady=(36, 4), padx=24)
        muted(self, message, style="body", anchor="center", justify="center",
              wraplength=420).pack(padx=24, pady=(0, 18 if action else 36))
        if action:
            button(self, action[0], action[1], kind=action[2], width=160).pack(pady=(0, 32))


def bind_recursive(widget: tk.Misc, sequence: str, callback, *, skip=(ctk.CTkButton,)) -> None:
    """Bind an event on a widget and all of its descendants (except skipped types)."""
    if not isinstance(widget, skip):
        try:
            widget.bind(sequence, callback, add="+")
        except (tk.TclError, ValueError, NotImplementedError):
            pass
    for child in widget.winfo_children():
        bind_recursive(child, sequence, callback, skip=skip)


class CapsuleCard(Card):
    """A library card. Locked capsules show only metadata, never content."""

    def __init__(self, master, summary: CapsuleSummary, now: datetime,
                 on_open: Callable[[int], None], on_favorite: Callable[[int, bool], None]) -> None:
        super().__init__(master, cursor="hand2")
        self.grid_columnconfigure(0, weight=1)
        locked = summary.is_locked(now)

        label(self, summary.category.upper(), style="caption", color=theme.CYAN).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 0))
        badge = ctk.CTkLabel(
            self, text="LOCKED" if locked else ("OPENED" if summary.opened_at else "READY"),
            font=fonts.caption, width=64, height=22, corner_radius=8,
            fg_color=theme.ACCENT if locked else theme.ACCENT_SOFT,
            text_color=theme.ON_ACCENT if locked else theme.TEXT)
        badge.grid(row=0, column=1, padx=(0, 14), pady=(14, 0), sticky="e")

        label(self, summary.title, style="heading", wraplength=250).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 2))
        if locked:
            when = f"Unlocks {dates.format_date(summary.unlock_at)}  ·  {dates.humanize_remaining(summary.time_remaining(now))}"
        else:
            when = f"Unlocked {dates.format_date(summary.unlock_at)}"
        muted(self, when).grid(row=2, column=0, columnspan=2, sticky="w", padx=16)
        tags = "  ".join(f"#{t}" for t in summary.tags[:4])
        muted(self, tags or "No tags", style="caption").grid(
            row=3, column=0, sticky="w", padx=16, pady=(8, 14))
        star = ctk.CTkButton(
            self, text="★" if summary.favorite else "☆", width=32, height=28,
            fg_color="transparent", hover_color=theme.CARD_HOVER,
            text_color=theme.CYAN if summary.favorite else theme.MUTED, font=fonts.heading,
            command=lambda: on_favorite(summary.id, not summary.favorite))
        star.grid(row=3, column=1, padx=(0, 10), pady=(4, 10), sticky="e")

        bind_recursive(self, "<Button-1>", lambda _e: on_open(summary.id))
        bind_recursive(self, "<Enter>", lambda _e: self.configure(fg_color=theme.CARD_HOVER))
        bind_recursive(self, "<Leave>", lambda _e: self.configure(fg_color=theme.CARD))


class ChoiceDialog(ctk.CTkToplevel):
    """A modal dialog with a message and a row of buttons."""

    def __init__(self, parent: tk.Misc, title: str, message: str,
                 buttons: Sequence[tuple[str, str, str]]) -> None:
        super().__init__(parent)
        self.result: str | None = None
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=theme.BG)
        self.transient(parent.winfo_toplevel())
        card = Card(self)
        card.pack(padx=16, pady=16)
        label(card, title, style="heading").pack(anchor="w", padx=22, pady=(20, 6))
        label(card, message, style="body", wraplength=400).pack(anchor="w", padx=22, pady=(0, 18))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="e", padx=22, pady=(0, 20))
        for text, value, kind in buttons:
            button(row, text, lambda v=value: self._choose(v), kind=kind, width=110).pack(side="left", padx=(8, 0))
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose(None))
        self.bind("<Escape>", lambda _e: self._choose(None))
        self.update_idletasks()
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_reqwidth()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.after(80, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
            self.focus_set()
        except tk.TclError:
            pass

    def _choose(self, value: str | None) -> None:
        self.result = value
        self.destroy()

    def show(self) -> str | None:
        self.wait_window(self)
        return self.result


def ask_confirm(parent: tk.Misc, title: str, message: str, confirm_text: str = "Confirm",
                danger: bool = False) -> bool:
    return ChoiceDialog(parent, title, message, [
        ("Cancel", "cancel", "secondary"),
        (confirm_text, "ok", "danger" if danger else "primary"),
    ]).show() == "ok"


def show_message(parent: tk.Misc, title: str, message: str) -> None:
    ChoiceDialog(parent, title, message, [("OK", "ok", "primary")]).show()


class DatePickerDialog(ctk.CTkToplevel):
    """A small month-grid calendar built from CustomTkinter widgets."""

    def __init__(self, parent: tk.Misc, initial: date | None = None,
                 min_date: date | None = None) -> None:
        super().__init__(parent)
        self.result: date | None = None
        self._selected = initial
        self._min = min_date
        self._shown = (initial or date.today()).replace(day=1)
        self.title("Choose a date")
        self.resizable(False, False)
        self.configure(fg_color=theme.BG)
        self.transient(parent.winfo_toplevel())

        card = Card(self)
        card.pack(padx=14, pady=14)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 6))
        head.grid_columnconfigure(1, weight=1)
        button(head, "‹", lambda: self._shift(-1), kind="ghost", width=36).grid(row=0, column=0)
        self.month_label = label(head, "", style="bold", anchor="center")
        self.month_label.grid(row=0, column=1, sticky="ew")
        button(head, "›", lambda: self._shift(1), kind="ghost", width=36).grid(row=0, column=2)

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(padx=14, pady=(0, 14))
        for col, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            muted(grid, name, style="caption", anchor="center", width=38).grid(row=0, column=col, pady=(0, 4))
        self._cells: list[ctk.CTkButton] = []
        for r in range(6):
            for c in range(7):
                cell = ctk.CTkButton(grid, text="", width=38, height=32, corner_radius=8,
                                     fg_color="transparent", hover_color=theme.CARD_HOVER,
                                     text_color=theme.TEXT, font=fonts.small)
                cell.grid(row=r + 1, column=c, padx=1, pady=1)
                self._cells.append(cell)
        self._render()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        top = parent.winfo_toplevel()
        self.geometry(f"+{top.winfo_rootx() + 120}+{top.winfo_rooty() + 120}")
        self.after(80, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _shift(self, months: int) -> None:
        self._shown = dates.add_months(self._shown, months).replace(day=1)
        self._render()

    def _render(self) -> None:
        self.month_label.configure(text=f"{calendar.month_name[self._shown.month]} {self._shown.year}")
        weeks = calendar.monthcalendar(self._shown.year, self._shown.month)
        today = date.today()
        for index, cell in enumerate(self._cells):
            r, c = divmod(index, 7)
            day = weeks[r][c] if r < len(weeks) else 0
            if not day:
                cell.configure(text="", state="disabled", fg_color="transparent", command=lambda: None)
                continue
            value = date(self._shown.year, self._shown.month, day)
            blocked = self._min is not None and value < self._min
            is_selected = value == self._selected
            cell.configure(
                text=str(day), state="disabled" if blocked else "normal",
                fg_color=theme.ACCENT if is_selected else "transparent",
                text_color=theme.ON_ACCENT if is_selected else (theme.MUTED if blocked else theme.TEXT),
                border_width=1 if value == today else 0, border_color=theme.CYAN,
                command=lambda v=value: self._pick(v))

    def _pick(self, value: date) -> None:
        self.result = value
        self.destroy()

    def show(self) -> date | None:
        self.wait_window(self)
        return self.result


class DateField(ctk.CTkFrame):
    """A date entry (YYYY-MM-DD) with a calendar button."""

    def __init__(self, master, *, min_date: date | None = None, width: int = 130,
                 on_change: Callable[[], None] | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        self._min = min_date
        self._on_change = on_change
        self.entry = entry(self, "YYYY-MM-DD", width=width)
        self.entry.pack(side="left")
        button(self, "Pick", self._pick, kind="secondary", width=52).pack(side="left", padx=(6, 0))
        if on_change:
            self.entry.bind("<Return>", lambda _e: on_change())
            self.entry.bind("<FocusOut>", lambda _e: on_change())

    def get_text(self) -> str:
        return self.entry.get().strip()

    def get_date(self) -> date | None:
        """Return the entered date, None if empty. Raises ValueError if malformed."""
        text = self.get_text()
        return dates.parse_date_input(text) if text else None

    def set_date(self, value: date | None) -> None:
        self.entry.delete(0, "end")
        if value:
            self.entry.insert(0, value.isoformat())

    def _pick(self) -> None:
        try:
            current = self.get_date()
        except ValueError:
            current = None
        chosen = DatePickerDialog(self, current, self._min).show()
        if chosen:
            self.set_date(chosen)
            if self._on_change:
                self._on_change()
