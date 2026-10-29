"""Capsule business logic: creation, locking rules, search and statistics."""
from __future__ import annotations

import json
import logging
import uuid as uuid_lib
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Callable

from database import CapsuleRow, Database
from models import (
    ActivityItem, CapsuleDetail, CapsuleFilter, CapsuleSummary, Comparison,
    DashboardStats, ReflectionReport,
)
from services.security_service import SecurityService, record_aad
from utils import dates
from utils.validation import validate_capsule_input

log = logging.getLogger("echo.capsules")

DAILY_QUESTIONS: tuple[str, ...] = (
    "What is one small thing you are quietly proud of this week?",
    "Which habit would you like your future self to thank you for?",
    "What did you learn recently that changed how you see something?",
    "Who made a difference to you lately, and have you told them?",
    "What are you carrying that you could set down?",
    "What does a good ordinary day look like for you right now?",
    "What question are you living with at the moment?",
    "Which moment from the past year would you relive?",
    "What would you tell yourself from five years ago?",
    "What are you looking forward to, however small?",
    "What does rest mean to you at the moment?",
    "Which of your values showed up in a recent decision?",
    "What would you like to remember about this season of life?",
    "What is something you want to get better at, and why?",
    "Where did you feel most like yourself recently?",
    "What are three things you are grateful for today?",
    "What would you attempt if you knew you could not embarrass yourself?",
    "What conversation are you putting off?",
    "How have your priorities shifted over the last few years?",
    "What is a risk you are glad you took?",
    "What do you want your next chapter to include?",
    "What is a kindness you received that you still think about?",
    "What does success look like to you this year?",
    "Which part of your routine gives you the most energy?",
    "What would you like to forgive yourself for?",
    "What is something you have outgrown?",
    "What is a place that feels like home to you, and why?",
    "What advice would you give someone just starting where you are?",
    "What do you hope is still true about you in ten years?",
    "What did you notice today that you usually overlook?",
)


class CapsuleLockedError(Exception):
    """Raised when someone tries to open a capsule before its unlock time."""

    def __init__(self, unlock_at: datetime) -> None:
        self.unlock_at = unlock_at
        super().__init__(f"This capsule unlocks on {dates.format_datetime(unlock_at)}.")


class CapsuleNotFoundError(LookupError):
    """Raised when a capsule id does not exist."""


class CapsuleService:
    def __init__(self, db: Database, security: SecurityService,
                 clock: Callable[[], datetime] = dates.now) -> None:
        self._db = db
        self._security = security
        self._clock = clock

    def now(self) -> datetime:
        return self._clock()

    def _row(self, capsule_id: int) -> CapsuleRow:
        row = self._db.get_capsule(capsule_id)
        if row is None:
            raise CapsuleNotFoundError(f"Capsule {capsule_id} does not exist.")
        return row

    def _summary(self, row: CapsuleRow) -> CapsuleSummary:
        meta = json.loads(self._security.decrypt(row.meta_blob, record_aad(row.uuid, "meta")))
        return CapsuleSummary(
            id=row.id, uuid=row.uuid, title=meta["title"], tags=tuple(meta["tags"]),
            category=row.category, created_at=dates.from_iso(row.created_at),
            unlock_at=dates.from_iso(row.unlock_at), favorite=row.favorite,
            archived=row.archived,
            opened_at=dates.from_iso(row.opened_at) if row.opened_at else None,
        )

    def _store(self, clean: dict, created_at: datetime, *, opened_at: datetime | None = None) -> CapsuleSummary:
        capsule_uuid = str(uuid_lib.uuid4())
        meta = json.dumps({"title": clean["title"], "tags": clean["tags"]}).encode("utf-8")
        with self._db.transaction():
            row_id = self._db.insert_capsule(
                uuid=capsule_uuid, category=clean["category"],
                created_at=dates.to_iso(created_at), unlock_at=dates.to_iso(clean["unlock_at"]),
                favorite=False, archived=False,
                opened_at=dates.to_iso(opened_at) if opened_at else None,
                meta_blob=self._security.encrypt(meta, record_aad(capsule_uuid, "meta")),
                body_blob=self._security.encrypt(
                    clean["body"].encode("utf-8"), record_aad(capsule_uuid, "body")),
            )
            self._db.log_activity(dates.to_iso(created_at), "created", capsule_uuid)
        log.info("Capsule %s created", row_id)
        return self.get_summary(row_id)

    def create_capsule(self, *, title: str, body: str, category: str,
                       tags: str | list[str], unlock_at: datetime) -> CapsuleSummary:
        """Validate and store a new sealed capsule."""
        created = self._clock()
        clean = validate_capsule_input(
            title=title, body=body, category=category, tags=tags,
            unlock_at=unlock_at, created_at=created)
        return self._store(clean, created)

    def get_summary(self, capsule_id: int) -> CapsuleSummary:
        return self._summary(self._row(capsule_id))

    def open_capsule(self, capsule_id: int) -> CapsuleDetail:
        """Release a capsule's body. Refuses while the capsule is locked."""
        row = self._row(capsule_id)
        summary = self._summary(row)
        if summary.is_locked(self._clock()):
            raise CapsuleLockedError(summary.unlock_at)
        body = self._security.decrypt(row.body_blob, record_aad(row.uuid, "body")).decode("utf-8")
        if row.opened_at is None:
            opened = self._clock()
            with self._db.transaction():
                self._db.mark_opened(row.id, dates.to_iso(opened))
                self._db.log_activity(dates.to_iso(opened), "opened", row.uuid)
            summary = replace(summary, opened_at=opened)
        return CapsuleDetail(summary=summary, body=body)

    def set_favorite(self, capsule_id: int, value: bool) -> None:
        self._row(capsule_id)
        self._db.set_flags(capsule_id, favorite=value)

    def set_archived(self, capsule_id: int, value: bool) -> None:
        self._row(capsule_id)
        self._db.set_flags(capsule_id, archived=value)

    def delete_capsule(self, capsule_id: int) -> None:
        row = self._row(capsule_id)
        with self._db.transaction():
            self._db.delete_capsule(capsule_id)
            self._db.log_activity(dates.to_iso(self._clock()), "deleted", row.uuid)

    def list_capsules(self, flt: CapsuleFilter | None = None) -> list[CapsuleSummary]:
        flt = flt or CapsuleFilter()
        now = self._clock()
        query = flt.query.strip().lower().lstrip("#")
        result: list[CapsuleSummary] = []
        for row in self._db.list_capsules():
            s = self._summary(row)
            locked = s.is_locked(now)
            if flt.view == "archived":
                ok = s.archived
            else:
                ok = not s.archived and (
                    flt.view == "all"
                    or (flt.view == "locked" and locked)
                    or (flt.view == "unlocked" and not locked)
                    or (flt.view == "favorites" and s.favorite))
            if not ok:
                continue
            if flt.category and s.category != flt.category:
                continue
            if query and query not in s.title.lower() and not any(query in t for t in s.tags):
                continue
            if flt.date_from and s.unlock_at.date() < flt.date_from.date():
                continue
            if flt.date_to and s.unlock_at.date() > flt.date_to.date():
                continue
            result.append(s)
        key = (lambda s: s.unlock_at) if flt.sort_by == "unlock" else (lambda s: s.created_at)
        result.sort(key=key, reverse=flt.descending)
        return result

    def recent_activity(self, limit: int = 6) -> list[ActivityItem]:
        items: list[ActivityItem] = []
        for entry in self._db.recent_activity(limit):
            title = None
            row = self._db.get_capsule_by_uuid(entry.capsule_uuid) if entry.capsule_uuid else None
            if row is not None:
                title = self._summary(row).title
            items.append(ActivityItem(dates.from_iso(entry.ts), entry.event, title))
        return items

    def dashboard_stats(self) -> DashboardStats:
        now = self._clock()
        summaries = [self._summary(r) for r in self._db.list_capsules()]
        active = [s for s in summaries if not s.archived]
        locked = [s for s in active if s.is_locked(now)]
        next_unlock = min(locked, key=lambda s: s.unlock_at, default=None)
        first = min((s.created_at for s in summaries), default=None)
        return DashboardStats(
            total=len(active), locked=len(locked), unlocked=len(active) - len(locked),
            favorites=sum(1 for s in active if s.favorite),
            opened=sum(1 for s in summaries if s.opened_at),
            next_unlock=next_unlock,
            days_since_first=(now - first).days if first else None,
        )

    @staticmethod
    def daily_question(today: date | None = None) -> str:
        today = today or date.today()
        return DAILY_QUESTIONS[today.toordinal() % len(DAILY_QUESTIONS)]

    def compare(self, first_id: int, second_id: int) -> Comparison:
        """Open two unlocked capsules for side-by-side reading."""
        if first_id == second_id:
            raise ValueError("Choose two different entries.")
        a, b = self.open_capsule(first_id), self.open_capsule(second_id)
        if b.summary.created_at < a.summary.created_at:
            a, b = b, a
        return Comparison(
            first=a, second=b,
            elapsed_text=dates.elapsed_description(a.summary.created_at, b.summary.created_at),
            days_apart=(b.summary.created_at - a.summary.created_at).days,
        )

    def reflection_report(self) -> ReflectionReport:
        """Rule-based statistics from saved metadata. No AI, no inference."""
        now = self._clock()
        summaries = [s for s in (self._summary(r) for r in self._db.list_capsules()) if not s.archived]
        if not summaries:
            return ReflectionReport(total=0, summary_lines=["No capsules yet. Statistics appear once you start writing."])
        by_month = Counter(s.created_at.strftime("%Y-%m") for s in summaries)
        by_category = Counter(s.category for s in summaries)
        # Tags of locked capsules are not used, so sealed metadata stays sealed.
        tag_counts = Counter(t for s in summaries if not s.is_locked(now) for t in s.tags)
        top_tags = tag_counts.most_common(8)
        created = sorted(s.created_at for s in summaries)
        gap = None
        if len(created) > 1:
            gap = (created[-1] - created[0]).total_seconds() / 86400 / (len(created) - 1)

        lines = [f"You have saved {len(summaries)} capsule{'s' if len(summaries) != 1 else ''} "
                 f"since {dates.format_date(created[0])}."]
        month, count = by_month.most_common(1)[0]
        lines.append(f"Your busiest month for writing was {month}, with {count} capsule{'s' if count != 1 else ''}.")
        cat, cat_count = by_category.most_common(1)[0]
        lines.append(f"Your most used category is {cat} ({cat_count}).")
        if top_tags:
            lines.append(f"The tag you use most in unlocked entries is '{top_tags[0][0]}' ({top_tags[0][1]}).")
        if gap is not None:
            lines.append(f"On average there are {gap:.1f} days between the capsules you create.")
        return ReflectionReport(
            total=len(summaries), by_month=dict(sorted(by_month.items())),
            by_category=dict(by_category), top_tags=top_tags,
            average_gap_days=gap, summary_lines=lines)

    def load_demo_data(self) -> int:
        """Insert fictional sample capsules. Only runs when explicitly requested."""
        if self._db.get_setting("demo_loaded") == "1":
            raise ValueError("Demonstration data is already loaded.")
        now = self._clock()
        samples = [
            (-400, -300, "Journal Entry", "First week at the new desk",
             "Fictional sample entry. The office smells like fresh coffee and I am still learning where everything is.", ["work", "beginnings"]),
            (-200, -20, "Letter to Future Self", "Dear me, a few months from now",
             "Fictional sample letter. I hope you finished the project and kept walking in the mornings.", ["letters", "habits"]),
            (-90, -5, "Milestone", "Finished the first big project",
             "Fictional sample milestone. It took longer than planned, and it was worth it.", ["work", "milestone"]),
            (-30, 45, "Letter to Future Self", "Open when the weather turns",
             "Fictional sample letter. Hold on to the plan for the garden.", ["letters", "garden"]),
            (-10, 200, "Goal", "Where I want to be next year",
             "Fictional sample goal list. Read more, travel once, learn to bake bread.", ["goals"]),
            (-2, 0, "Memory", "A quiet Sunday",
             "Fictional sample memory. Rain on the window, music on low, nowhere to be.", ["memory"]),
        ]
        added = 0
        for created_off, unlock_off, category, title, body, tags in samples:
            created = now + timedelta(days=created_off)
            unlock = now + timedelta(days=unlock_off, minutes=2 if unlock_off == 0 else 0)
            clean = {"title": title, "body": body, "category": category,
                     "tags": tags + ["demo"], "unlock_at": unlock}
            self._store(clean, created, opened_at=created + timedelta(days=1) if unlock_off < -250 else None)
            added += 1
        self._db.set_setting("demo_loaded", "1")
        return added

    def remove_demo_data(self) -> int:
        removed = 0
        for row in self._db.list_capsules():
            if "demo" in self._summary(row).tags:
                self.delete_capsule(row.id)
                removed += 1
        self._db.set_setting("demo_loaded", "0")
        return removed

    @property
    def demo_loaded(self) -> bool:
        return self._db.get_setting("demo_loaded") == "1"
