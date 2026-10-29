import base64
import json
import tempfile
import unittest
from pathlib import Path

from database import Database
from services.backup_service import BackupError
from services.security_service import SecurityService
from tests.helpers import PASSWORD, Vault


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "backup.json"
        self.v = Vault()
        self.v.make(title="One", body="Body one")
        self.v.make(title="Two", body="Body two", days=3)

    def edit(self, fn):
        data = json.loads(self.path.read_text())
        fn(data)
        self.path.write_text(json.dumps(data))

    def test_export_contains_no_plaintext_or_raw_key(self):
        self.assertEqual(self.v.backup.export_backup(self.path), 2)
        text = self.path.read_text()
        for needle in ("Body one", "Body two", "One", PASSWORD):
            self.assertNotIn(needle, text)
        data = json.loads(text)
        self.assertEqual(set(data["key_envelope"]), {"version", "kdf", "n", "r", "p", "salt", "nonce", "wrapped_key"})

    def test_round_trip_into_fresh_install(self):
        self.v.backup.export_backup(self.path)
        fresh = Vault(setup=False)
        fresh.backup.restore_key_envelope(self.path)
        fresh.security.unlock(PASSWORD)
        result = fresh.backup.import_backup(self.path)
        self.assertEqual((result.added, result.skipped), (2, 0))
        titles = {s.title for s in fresh.capsules.list_capsules()}
        self.assertEqual(titles, {"One", "Two"})

    def test_duplicates_reported_and_skipped_by_default(self):
        self.v.backup.export_backup(self.path)
        report = self.v.backup.inspect_backup(self.path)
        self.assertTrue(report.valid)
        self.assertEqual((report.total, report.duplicates, report.new), (2, 2, 0))
        result = self.v.backup.import_backup(self.path)
        self.assertEqual((result.added, result.skipped, result.overwritten), (0, 2, 0))
        self.assertEqual(len(self.v.db.list_capsules()), 2)

    def test_overwrite_replaces_flags(self):
        self.v.backup.export_backup(self.path)
        first = self.v.db.list_capsules()[0]
        self.v.capsules.set_favorite(first.id, True)
        result = self.v.backup.import_backup(self.path, overwrite=True)
        self.assertEqual(result.overwritten, 2)
        self.assertFalse(self.v.db.get_capsule(first.id).favorite)

    def test_invalid_files_are_rejected_before_any_change(self):
        cases = {
            "not json": lambda: self.path.write_text("{nope"),
            "wrong format": lambda: self.path.write_text(json.dumps({"format": "other"})),
        }
        for name, write in cases.items():
            with self.subTest(name):
                write()
                self.assertFalse(self.v.backup.inspect_backup(self.path).valid)
                with self.assertRaises(BackupError):
                    self.v.backup.import_backup(self.path)

    def test_tampered_record_blocks_whole_import(self):
        self.v.backup.export_backup(self.path)
        target = Vault(db=Database(":memory:"), setup=False)
        target.backup.restore_key_envelope(self.path)
        target.security.unlock(PASSWORD)

        def tamper(data):
            blob = bytearray(base64.b64decode(data["capsules"][1]["body"]))
            blob[-1] ^= 1
            data["capsules"][1]["body"] = base64.b64encode(bytes(blob)).decode()
        self.edit(tamper)
        with self.assertRaises(BackupError):
            target.backup.import_backup(self.path)
        self.assertEqual(target.db.list_capsules(), [])  # nothing was applied

    def test_field_validation(self):
        self.v.backup.export_backup(self.path)
        mutations = [
            lambda d: d["capsules"][0].update(unlock_at="not a date"),
            lambda d: d["capsules"][0].update(category="Hacking"),
            lambda d: d["capsules"][0].update(favorite="yes"),
            lambda d: d["capsules"][0].update(uuid="not-a-uuid"),
            lambda d: d["capsules"][0].update(meta="***"),
            lambda d: d["capsules"].append(dict(d["capsules"][0])),  # duplicate inside file
            lambda d: d.update(version=99),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(i):
                self.v.backup.export_backup(self.path)
                self.edit(mutate)
                self.assertFalse(self.v.backup.inspect_backup(self.path).valid)

    def test_import_requires_unlocked_vault(self):
        self.v.backup.export_backup(self.path)
        self.v.security.lock()
        self.assertFalse(self.v.backup.inspect_backup(self.path).valid)

    def test_backup_from_other_vault_cannot_be_imported(self):
        self.v.backup.export_backup(self.path)
        other = Vault()  # different random key
        self.assertFalse(other.backup.inspect_backup(self.path).valid)

    def test_envelope_restore_only_on_uninitialised_vault(self):
        self.v.backup.export_backup(self.path)
        with self.assertRaises(BackupError):
            self.v.backup.restore_key_envelope(self.path)


if __name__ == "__main__":
    unittest.main()
