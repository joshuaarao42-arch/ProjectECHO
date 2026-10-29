import unittest

from database import Database


def fields(uuid="u1"):
    return dict(uuid=uuid, category="Memory", created_at="2026-01-01T09:00:00",
                unlock_at="2026-02-01T09:00:00", favorite=False, archived=False,
                opened_at=None, meta_blob=b"m", body_blob=b"b")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def test_insert_get_list_delete(self):
        row_id = self.db.insert_capsule(**fields())
        self.assertEqual(self.db.get_capsule(row_id).uuid, "u1")
        self.assertEqual(len(self.db.list_capsules()), 1)
        self.db.delete_capsule(row_id)
        self.assertIsNone(self.db.get_capsule(row_id))

    def test_unique_uuid(self):
        self.db.insert_capsule(**fields())
        with self.assertRaises(Exception):
            self.db.insert_capsule(**fields())

    def test_flags_and_opened_only_set_once(self):
        row_id = self.db.insert_capsule(**fields())
        self.db.set_flags(row_id, favorite=True, archived=True)
        row = self.db.get_capsule(row_id)
        self.assertTrue(row.favorite and row.archived)
        self.db.mark_opened(row_id, "2026-03-01T00:00:00")
        self.db.mark_opened(row_id, "2026-04-01T00:00:00")
        self.assertEqual(self.db.get_capsule(row_id).opened_at, "2026-03-01T00:00:00")

    def test_transaction_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with self.db.transaction():
                self.db.insert_capsule(**fields())
                raise RuntimeError("boom")
        self.assertEqual(self.db.list_capsules(), [])

    def test_nested_transaction_commits_once(self):
        with self.db.transaction():
            with self.db.transaction():
                self.db.insert_capsule(**fields())
        self.assertEqual(len(self.db.list_capsules()), 1)

    def test_settings_upsert(self):
        self.db.set_setting("k", "1")
        self.db.set_setting("k", "2")
        self.assertEqual(self.db.get_setting("k"), "2")
        self.assertIsNone(self.db.get_setting("missing"))

    def test_sql_injection_text_is_inert(self):
        self.db.set_setting("x'; DROP TABLE capsules;--", "v")
        self.db.insert_capsule(**fields())
        self.assertEqual(len(self.db.list_capsules()), 1)


if __name__ == "__main__":
    unittest.main()
