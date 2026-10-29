"""Export and validate encrypted JSON backups."""
from __future__ import annotations

import base64
import json
import logging
import uuid as uuid_lib
from dataclasses import dataclass, field
from pathlib import Path

from database import Database
from models import CATEGORIES
from services.security_service import SecurityError, SecurityService, record_aad
from utils import dates

log = logging.getLogger("echo.backup")

FORMAT = "echo-backup"
VERSION = 1
MAX_BYTES = 200 * 1024 * 1024
MAX_RECORDS = 100_000


class BackupError(Exception):
    """Raised when a backup cannot be read or fails validation."""


@dataclass
class BackupReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    total: int = 0
    new: int = 0
    duplicates: int = 0


@dataclass(frozen=True)
class ImportResult:
    added: int
    skipped: int
    overwritten: int


class BackupService:
    def __init__(self, db: Database, security: SecurityService) -> None:
        self._db = db
        self._security = security

    def export_backup(self, path: Path | str) -> int:
        """Write all capsules (still encrypted) to a JSON file. Returns the count."""
        target = Path(path)
        records = [
            {
                "uuid": r.uuid, "category": r.category, "created_at": r.created_at,
                "unlock_at": r.unlock_at, "favorite": r.favorite, "archived": r.archived,
                "opened_at": r.opened_at,
                "meta": base64.b64encode(r.meta_blob).decode("ascii"),
                "body": base64.b64encode(r.body_blob).decode("ascii"),
            }
            for r in self._db.list_capsules()
        ]
        document = {
            "format": FORMAT, "version": VERSION,
            "exported_at": dates.to_iso(dates.now()),
            "key_envelope": self._security.export_envelope(),
            "capsules": records,
        }
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(json.dumps(document, indent=2), encoding="utf-8")
        temp.replace(target)
        log.info("Exported %d capsules", len(records))
        return len(records)

    @staticmethod
    def _read(path: Path | str) -> dict:
        source = Path(path)
        try:
            if source.stat().st_size > MAX_BYTES:
                raise BackupError("The file is too large to be an ECHO backup.")
            data = json.loads(source.read_text(encoding="utf-8"))
        except BackupError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackupError("The file could not be read as JSON.") from exc
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise BackupError("This is not an ECHO backup file.")
        if data.get("version") != VERSION:
            raise BackupError("This backup was made by an unsupported version.")
        if not isinstance(data.get("capsules"), list):
            raise BackupError("The backup has no capsule list.")
        if len(data["capsules"]) > MAX_RECORDS:
            raise BackupError("The backup contains too many records.")
        return data

    def _check_record(self, index: int, rec: object) -> tuple[list[str], bytes, bytes]:
        problems: list[str] = []
        label = f"Record {index + 1}"
        if not isinstance(rec, dict):
            return [f"{label}: not an object."], b"", b""
        try:
            uuid_lib.UUID(str(rec.get("uuid")))
        except ValueError:
            problems.append(f"{label}: invalid id.")
        if rec.get("category") not in CATEGORIES:
            problems.append(f"{label}: unknown category.")
        parsed = {}
        for key in ("created_at", "unlock_at"):
            try:
                parsed[key] = dates.from_iso(rec.get(key))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                problems.append(f"{label}: invalid {key}.")
        if len(parsed) == 2 and parsed["unlock_at"] < parsed["created_at"]:
            problems.append(f"{label}: unlock date is before creation date.")
        opened = rec.get("opened_at")
        if opened is not None:
            try:
                dates.from_iso(opened)
            except (TypeError, ValueError):
                problems.append(f"{label}: invalid opened_at.")
        for key in ("favorite", "archived"):
            if not isinstance(rec.get(key), bool):
                problems.append(f"{label}: {key} must be true or false.")
        blobs = []
        for key in ("meta", "body"):
            try:
                blobs.append(base64.b64decode(rec.get(key), validate=True))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                problems.append(f"{label}: {key} is not valid base64.")
                blobs.append(b"")
        if not problems:
            rid = rec["uuid"]
            if not self._security.can_decrypt(blobs[0], record_aad(rid, "meta")) or \
               not self._security.can_decrypt(blobs[1], record_aad(rid, "body")):
                problems.append(f"{label}: could not be decrypted with this vault's key or was altered.")
        return problems, blobs[0], blobs[1]

    def inspect_backup(self, path: Path | str) -> BackupReport:
        """Validate a backup without touching the database."""
        try:
            data = self._read(path)
        except BackupError as exc:
            return BackupReport(valid=False, errors=[str(exc)])
        if not self._security.is_unlocked:
            return BackupReport(valid=False, errors=["Unlock the vault before importing."])
        errors: list[str] = []
        seen: set[str] = set()
        duplicates = 0
        for i, rec in enumerate(data["capsules"]):
            problems, _, _ = self._check_record(i, rec)
            errors.extend(problems)
            if not problems:
                if rec["uuid"] in seen:
                    errors.append(f"Record {i + 1}: appears twice in the file.")
                seen.add(rec["uuid"])
                if self._db.uuid_exists(rec["uuid"]):
                    duplicates += 1
        total = len(data["capsules"])
        return BackupReport(valid=not errors, errors=errors[:20], total=total,
                            new=total - duplicates, duplicates=duplicates)

    def import_backup(self, path: Path | str, *, overwrite: bool = False) -> ImportResult:
        """Import after full validation. Either everything is applied or nothing is."""
        report = self.inspect_backup(path)
        if not report.valid:
            raise BackupError(report.errors[0] if report.errors else "Backup is invalid.")
        data = self._read(path)
        added = skipped = overwritten = 0
        with self._db.transaction():
            for rec in data["capsules"]:
                fields = dict(
                    uuid=rec["uuid"], category=rec["category"], created_at=rec["created_at"],
                    unlock_at=rec["unlock_at"], favorite=rec["favorite"], archived=rec["archived"],
                    opened_at=rec["opened_at"],
                    meta_blob=base64.b64decode(rec["meta"]), body_blob=base64.b64decode(rec["body"]),
                )
                if self._db.uuid_exists(rec["uuid"]):
                    if overwrite:
                        self._db.replace_capsule(**fields)
                        overwritten += 1
                    else:
                        skipped += 1
                else:
                    self._db.insert_capsule(**fields)
                    added += 1
            self._db.log_activity(dates.to_iso(dates.now()), "imported", None)
        log.info("Imported backup: %d added, %d skipped, %d overwritten", added, skipped, overwritten)
        return ImportResult(added, skipped, overwritten)

    def restore_key_envelope(self, path: Path | str) -> None:
        """For a fresh install: adopt the backup's key so its capsules can be decrypted."""
        data = self._read(path)
        try:
            self._security.install_envelope(data.get("key_envelope"))
        except SecurityError as exc:
            raise BackupError(str(exc)) from exc
