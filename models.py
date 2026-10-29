"""Data models shared across Project ECHO."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

CATEGORIES: tuple[str, ...] = (
    "Letter to Future Self",
    "Journal Entry",
    "Milestone",
    "Memory",
    "Goal",
)

VIEWS: tuple[str, ...] = ("all", "locked", "unlocked", "favorites", "archived")


@dataclass(frozen=True)
class CapsuleSummary:
    """Everything about a capsule except its body. Safe to show while locked."""

    id: int
    uuid: str
    title: str
    tags: tuple[str, ...]
    category: str
    created_at: datetime
    unlock_at: datetime
    favorite: bool
    archived: bool
    opened_at: datetime | None

    def is_locked(self, now: datetime) -> bool:
        return now < self.unlock_at

    def time_remaining(self, now: datetime) -> timedelta:
        return max(self.unlock_at - now, timedelta(0))


@dataclass(frozen=True)
class CapsuleDetail:
    """A capsule whose body has been released because it is unlocked."""

    summary: CapsuleSummary
    body: str


@dataclass
class CapsuleFilter:
    query: str = ""
    category: str | None = None
    view: str = "all"
    date_from: datetime | None = None  # inclusive, compared with the unlock date
    date_to: datetime | None = None  # inclusive
    sort_by: str = "created"  # "created" | "unlock"
    descending: bool = True


@dataclass(frozen=True)
class ActivityItem:
    timestamp: datetime
    event: str
    title: str | None


@dataclass(frozen=True)
class DashboardStats:
    total: int
    locked: int
    unlocked: int
    favorites: int
    opened: int
    next_unlock: CapsuleSummary | None
    days_since_first: int | None


@dataclass(frozen=True)
class Comparison:
    first: CapsuleDetail
    second: CapsuleDetail
    elapsed_text: str
    days_apart: int


@dataclass(frozen=True)
class ReflectionReport:
    total: int
    by_month: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    average_gap_days: float | None = None
    summary_lines: list[str] = field(default_factory=list)
    disclaimer: str = (
        "These figures only count saved metadata. They are not an assessment of "
        "your wellbeing, and they say nothing definitive about personal growth."
    )


@dataclass(frozen=True)
class AppSettings:
    inactivity_minutes: int = 5
    appearance: str = "light"
