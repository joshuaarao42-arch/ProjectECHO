"""Date and time helpers using local ISO-8601 timestamps."""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"
DATE_INPUT_FORMAT = "%Y-%m-%d"
TIME_INPUT_FORMAT = "%H:%M"


def now() -> datetime:
    """Return the current local time without microseconds."""
    return datetime.now().replace(microsecond=0)


def to_iso(value: datetime) -> str:
    """Serialise a datetime for storage."""
    return value.strftime(ISO_FORMAT)


def from_iso(text: str) -> datetime:
    """Parse a stored timestamp. Raises ValueError for malformed input."""
    return datetime.strptime(text, ISO_FORMAT)


def parse_date_input(text: str) -> date:
    """Parse a user-entered date (YYYY-MM-DD)."""
    try:
        return datetime.strptime(text.strip(), DATE_INPUT_FORMAT).date()
    except ValueError as exc:
        raise ValueError("Use the date format YYYY-MM-DD.") from exc


def parse_time_input(text: str) -> time:
    """Parse a user-entered 24-hour time (HH:MM)."""
    try:
        return datetime.strptime(text.strip(), TIME_INPUT_FORMAT).time()
    except ValueError as exc:
        raise ValueError("Use the time format HH:MM (24-hour).") from exc


def combine_date_time(date_text: str, time_text: str) -> datetime:
    """Combine user-entered date and time strings into a datetime."""
    return datetime.combine(parse_date_input(date_text), parse_time_input(time_text))


def add_months(value: date, months: int) -> date:
    """Add calendar months, clamping the day to the target month length."""
    index = value.month - 1 + months
    year, month = value.year + index // 12, index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def split_countdown(delta: timedelta) -> tuple[int, int, int, int]:
    """Split a timedelta into (days, hours, minutes, seconds); never negative."""
    total = max(int(delta.total_seconds()), 0)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return days, hours, minutes, seconds


def format_countdown(delta: timedelta) -> str:
    """Format a countdown such as '12d 03h 22m 10s'."""
    d, h, m, s = split_countdown(delta)
    if d:
        return f"{d}d {h:02d}h {m:02d}m {s:02d}s"
    return f"{h:02d}h {m:02d}m {s:02d}s"


def humanize_remaining(delta: timedelta) -> str:
    """Return a short phrase such as 'in 12 days'."""
    d, h, m, _ = split_countdown(delta)
    if d >= 1:
        return f"in {d} day{'s' if d != 1 else ''}"
    if h >= 1:
        return f"in {h} hour{'s' if h != 1 else ''}"
    return f"in {max(m, 1)} minute{'s' if m != 1 else ''}"


def format_datetime(value: datetime) -> str:
    return value.strftime("%d %b %Y, %H:%M")


def format_date(value: datetime | date) -> str:
    return value.strftime("%d %b %Y")


def elapsed_description(start: datetime, end: datetime) -> str:
    """Describe the time between two moments in approximate years/months/days."""
    total = abs(end - start)
    days = total.days
    if days == 0:
        hours = total.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} apart"
    years, rem = divmod(days, 365)
    months, day_part = divmod(rem, 30)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if day_part or not parts:
        parts.append(f"{day_part} day{'s' if day_part != 1 else ''}")
    return f"{', '.join(parts)} (about {days} days in total)"
