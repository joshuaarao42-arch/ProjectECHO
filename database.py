"""SQLite persistence layer. All SQL is parameterised."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS capsules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid       TEXT NOT NULL UNIQUE,
    category   TEXT NOT NULL,
    created_at TEXT NOT NULL,
    unlock_at  TEXT NOT NULL,
    favorite   INTEGER NOT NULL DEFAULT 0,
    archived   INTEGER NOT NULL DEFAULT 0,
    opened_at  TEXT,
    meta_blob  BLOB NOT NULL,
    body_blob  BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_capsules_unlock ON capsules (unlock_at);
CREATE TABLE IF NOT EXISTS activity (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    event        TEXT NOT NULL,
    capsule_uuid TEXT
);
"""


@dataclass(frozen=True)
class CapsuleRow:
    """A capsule exactly as stored. Title, tags and body are ciphertext."""

    id: int
    uuid: str
    category: str
    created_at: str
    unlock_at: str
    favorite: bool
    archived: bool
    opened_at: str | None
    meta_blob: bytes
    body_blob: bytes


@dataclass(frozen=True)
class ActivityRow:
    ts: str
    event: str
    capsule_uuid: str | None


class Database:
    """Thin wrapper around a sqlite3 connection."""

    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        self._conn.isolation_level = None  # explicit transactions below
        self._depth = 0
        self._conn.execute("PRAGMA secure_delete = ON")
        if self._path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run a block atomically. Nested use joins the outer transaction."""
        outermost = self._depth == 0
        if outermost:
            self._conn.execute("BEGIN")
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if outermost:
                self._conn.execute("ROLLBACK")
            raise
        else:
            self._depth -= 1
            if outermost:
                self._conn.execute("COMMIT")

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    @staticmethod
    def _to_row(row: sqlite3.Row) -> CapsuleRow:
        return CapsuleRow(
            id=row["id"], uuid=row["uuid"], category=row["category"],
            created_at=row["created_at"], unlock_at=row["unlock_at"],
            favorite=bool(row["favorite"]), archived=bool(row["archived"]),
            opened_at=row["opened_at"], meta_blob=bytes(row["meta_blob"]),
            body_blob=bytes(row["body_blob"]),
        )

    def insert_capsule(
        self, *, uuid: str, category: str, created_at: str, unlock_at: str,
        favorite: bool, archived: bool, opened_at: str | None,
        meta_blob: bytes, body_blob: bytes,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO capsules (uuid, category, created_at, unlock_at, favorite, "
            "archived, opened_at, meta_blob, body_blob) VALUES (?,?,?,?,?,?,?,?,?)",
            (uuid, category, created_at, unlock_at, int(favorite), int(archived),
             opened_at, meta_blob, body_blob),
        )
        return int(cur.lastrowid)

    def replace_capsule(
        self, *, uuid: str, category: str, created_at: str, unlock_at: str,
        favorite: bool, archived: bool, opened_at: str | None,
        meta_blob: bytes, body_blob: bytes,
    ) -> None:
        self._conn.execute(
            "UPDATE capsules SET category=?, created_at=?, unlock_at=?, favorite=?, "
            "archived=?, opened_at=?, meta_blob=?, body_blob=? WHERE uuid=?",
            (category, created_at, unlock_at, int(favorite), int(archived),
             opened_at, meta_blob, body_blob, uuid),
        )

    def get_capsule(self, capsule_id: int) -> CapsuleRow | None:
        row = self._conn.execute("SELECT * FROM capsules WHERE id = ?", (capsule_id,)).fetchone()
        return self._to_row(row) if row else None

    def get_capsule_by_uuid(self, uuid: str) -> CapsuleRow | None:
        row = self._conn.execute("SELECT * FROM capsules WHERE uuid = ?", (uuid,)).fetchone()
        return self._to_row(row) if row else None

    def uuid_exists(self, uuid: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM capsules WHERE uuid = ?", (uuid,)
        ).fetchone() is not None

    def list_capsules(self) -> list[CapsuleRow]:
        rows = self._conn.execute("SELECT * FROM capsules ORDER BY id").fetchall()
        return [self._to_row(r) for r in rows]

    def set_flags(self, capsule_id: int, *, favorite: bool | None = None,
                  archived: bool | None = None) -> None:
        if favorite is not None:
            self._conn.execute("UPDATE capsules SET favorite = ? WHERE id = ?",
                               (int(favorite), capsule_id))
        if archived is not None:
            self._conn.execute("UPDATE capsules SET archived = ? WHERE id = ?",
                               (int(archived), capsule_id))

    def mark_opened(self, capsule_id: int, timestamp: str) -> None:
        self._conn.execute(
            "UPDATE capsules SET opened_at = ? WHERE id = ? AND opened_at IS NULL",
            (timestamp, capsule_id),
        )

    def delete_capsule(self, capsule_id: int) -> None:
        self._conn.execute("DELETE FROM capsules WHERE id = ?", (capsule_id,))

    def log_activity(self, timestamp: str, event: str, capsule_uuid: str | None) -> None:
        self._conn.execute(
            "INSERT INTO activity (ts, event, capsule_uuid) VALUES (?,?,?)",
            (timestamp, event, capsule_uuid),
        )

    def recent_activity(self, limit: int) -> list[ActivityRow]:
        rows = self._conn.execute(
            "SELECT ts, event, capsule_uuid FROM activity ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [ActivityRow(r["ts"], r["event"], r["capsule_uuid"]) for r in rows]
