"""Input validation for capsules and passwords."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from models import CATEGORIES

MAX_TITLE = 120
MAX_BODY = 200_000
MAX_TAGS = 12
MAX_TAG_LENGTH = 32
MIN_PASSWORD = 10
MAX_UNLOCK_YEARS = 100


class ValidationError(ValueError):
    """Raised with a mapping of field name to human-readable message."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors.values()))


def normalize_tags(raw: str | Iterable[str]) -> list[str]:
    """Lower-case, de-duplicate and strip '#' from comma-separated tags."""
    parts = raw.replace(";", ",").split(",") if isinstance(raw, str) else list(raw)
    tags: list[str] = []
    for part in parts:
        tag = part.strip().lstrip("#").strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def validate_capsule_input(
    *,
    title: str,
    body: str,
    category: str,
    tags: str | Iterable[str],
    unlock_at: datetime,
    created_at: datetime,
) -> dict:
    """Validate and clean capsule fields. Raises ValidationError on failure."""
    errors: dict[str, str] = {}
    clean_title = (title or "").strip()
    clean_body = (body or "").strip()
    clean_tags = normalize_tags(tags)

    if not clean_title:
        errors["title"] = "Give your capsule a title."
    elif len(clean_title) > MAX_TITLE:
        errors["title"] = f"Titles can be at most {MAX_TITLE} characters."
    if not clean_body:
        errors["body"] = "Write something to preserve."
    elif len(clean_body) > MAX_BODY:
        errors["body"] = f"Capsules can hold at most {MAX_BODY:,} characters."
    if category not in CATEGORIES:
        errors["category"] = "Choose a category from the list."
    if len(clean_tags) > MAX_TAGS:
        errors["tags"] = f"Use at most {MAX_TAGS} tags."
    elif any(len(t) > MAX_TAG_LENGTH for t in clean_tags):
        errors["tags"] = f"Each tag can be at most {MAX_TAG_LENGTH} characters."
    if unlock_at <= created_at:
        errors["unlock_at"] = "The unlock date must be in the future."
    elif unlock_at > created_at + timedelta(days=365 * MAX_UNLOCK_YEARS):
        errors["unlock_at"] = f"The unlock date must be within {MAX_UNLOCK_YEARS} years."

    if errors:
        raise ValidationError(errors)
    return {
        "title": clean_title,
        "body": clean_body,
        "category": category,
        "tags": clean_tags,
        "unlock_at": unlock_at,
    }


def validate_password(password: str) -> None:
    """Enforce a minimum master-password length."""
    if len(password or "") < MIN_PASSWORD:
        raise ValidationError({"password": f"Use at least {MIN_PASSWORD} characters."})
