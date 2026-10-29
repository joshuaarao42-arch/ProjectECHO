import unittest
from datetime import timedelta

from models import CapsuleFilter
from services.capsule_service import CapsuleLockedError, CapsuleNotFoundError
from services.security_service import VaultLockedError
from tests.helpers import Vault
from utils.validation import ValidationError


class SchedulingAndAccessTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()

    def test_new_capsule_is_locked_and_refuses_to_open(self):
        s = self.v.make(days=10)
        self.assertTrue(s.is_locked(self.v.clock()))
        with self.assertRaises(CapsuleLockedError):
            self.v.capsules.open_capsule(s.id)

    def test_cannot_open_one_second_before_unlock(self):
        s = self.v.make(days=1)
        self.v.clock.advance(days=1, seconds=-1)
        with self.assertRaises(CapsuleLockedError):
            self.v.capsules.open_capsule(s.id)

    def test_opens_exactly_at_unlock_time_and_records_first_open(self):
        s = self.v.make(days=1)
        self.v.clock.advance(days=1)
        detail = self.v.capsules.open_capsule(s.id)
        self.assertEqual(detail.body, "Secret body text")
        first_open = detail.summary.opened_at
        self.v.clock.advance(hours=5)
        again = self.v.capsules.open_capsule(s.id)
        self.assertEqual(again.summary.opened_at, first_open)
        self.assertEqual(self.v.capsules.dashboard_stats().opened, 1)

    def test_past_unlock_date_rejected(self):
        with self.assertRaises(ValidationError):
            self.v.capsules.create_capsule(
                title="x", body="y", category="Memory", tags="",
                unlock_at=self.v.clock.current - timedelta(days=1))

    def test_summaries_do_not_expose_body(self):
        s = self.v.make()
        self.assertFalse(hasattr(s, "body"))

    def test_missing_capsule(self):
        with self.assertRaises(CapsuleNotFoundError):
            self.v.capsules.open_capsule(999)

    def test_locked_vault_blocks_everything(self):
        s = self.v.make(days=1)
        self.v.security.lock()
        with self.assertRaises(VaultLockedError):
            self.v.capsules.list_capsules()
        self.v.clock.advance(days=2)
        with self.assertRaises(VaultLockedError):
            self.v.capsules.open_capsule(s.id)


class EncryptionAtRestTests(unittest.TestCase):
    def test_database_holds_no_plaintext(self):
        v = Vault()
        v.make(title="Very Private Title", body="Very private body", tags="secrettag")
        row = v.db.list_capsules()[0]
        raw = row.meta_blob + row.body_blob
        for needle in (b"Very Private Title", b"Very private body", b"secrettag"):
            self.assertNotIn(needle, raw)

    def test_swapping_blobs_between_capsules_is_detected(self):
        v = Vault()
        a, b = v.make(title="A"), v.make(title="B")
        row_a, row_b = v.db.get_capsule(a.id), v.db.get_capsule(b.id)
        v.db._conn.execute("UPDATE capsules SET meta_blob = ? WHERE id = ?", (row_b.meta_blob, a.id))
        from services.security_service import SecurityError
        with self.assertRaises(SecurityError):
            v.capsules.get_summary(a.id)


class BrowsingTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.a = self.v.make(title="Alpha letter", days=5, category="Letter to Future Self", tags="family")
        self.v.clock.advance(days=1)
        self.b = self.v.make(title="Beta goal", days=400, category="Goal", tags="career, plans")
        self.v.clock.advance(days=10)  # alpha is now unlocked

    def titles(self, **kw):
        return [s.title for s in self.v.capsules.list_capsules(CapsuleFilter(**kw))]

    def test_status_views(self):
        self.assertEqual(self.titles(view="locked"), ["Beta goal"])
        self.assertEqual(self.titles(view="unlocked"), ["Alpha letter"])

    def test_search_title_tag_and_category(self):
        self.assertEqual(self.titles(query="alph"), ["Alpha letter"])
        self.assertEqual(self.titles(query="#plans"), ["Beta goal"])
        self.assertEqual(self.titles(category="Goal"), ["Beta goal"])
        self.assertEqual(self.titles(query="zzz"), [])

    def test_sorting(self):
        self.assertEqual(self.titles(sort_by="created", descending=True), ["Beta goal", "Alpha letter"])
        self.assertEqual(self.titles(sort_by="unlock", descending=False), ["Alpha letter", "Beta goal"])

    def test_date_range_uses_unlock_date(self):
        start = self.v.clock.current + timedelta(days=100)
        self.assertEqual(self.titles(date_from=start), ["Beta goal"])

    def test_favorites_archive_and_delete(self):
        self.v.capsules.set_favorite(self.a.id, True)
        self.assertEqual(self.titles(view="favorites"), ["Alpha letter"])
        self.v.capsules.set_archived(self.a.id, True)
        self.assertEqual(self.titles(view="archived"), ["Alpha letter"])
        self.assertNotIn("Alpha letter", self.titles())
        self.v.capsules.delete_capsule(self.a.id)
        self.assertEqual(self.titles(view="archived"), [])
        with self.assertRaises(CapsuleNotFoundError):
            self.v.capsules.get_summary(self.a.id)

    def test_dashboard_stats(self):
        stats = self.v.capsules.dashboard_stats()
        self.assertEqual((stats.total, stats.locked, stats.unlocked), (2, 1, 1))
        self.assertEqual(stats.next_unlock.title, "Beta goal")
        self.assertEqual(stats.days_since_first, 11)

    def test_activity_log_has_no_content_in_database(self):
        items = self.v.capsules.recent_activity()
        self.assertEqual({i.event for i in items}, {"created"})
        dump = [tuple(r) for r in self.v.db._conn.execute("SELECT * FROM activity")]
        self.assertNotIn("Alpha", str(dump))

    def test_daily_question_is_stable_per_day(self):
        from datetime import date
        q = self.v.capsules.daily_question(date(2026, 5, 5))
        self.assertEqual(q, self.v.capsules.daily_question(date(2026, 5, 5)))


class ReflectionTests(unittest.TestCase):
    def test_compare_requires_unlocked(self):
        v = Vault()
        a, b = v.make(days=5), v.make(days=500)
        v.clock.advance(days=10)
        with self.assertRaises(CapsuleLockedError):
            v.capsules.compare(a.id, b.id)
        with self.assertRaises(ValueError):
            v.capsules.compare(a.id, a.id)

    def test_compare_orders_by_creation_and_reports_elapsed(self):
        v = Vault()
        a = v.make(title="Old", days=5)
        v.clock.advance(days=40)
        b = v.make(title="New", days=5)
        v.clock.advance(days=10)
        cmp = v.capsules.compare(b.id, a.id)
        self.assertEqual((cmp.first.summary.title, cmp.second.summary.title), ("Old", "New"))
        self.assertEqual(cmp.days_apart, 40)

    def test_report_is_rule_based_and_hides_locked_tags(self):
        v = Vault()
        v.make(title="One", days=1, tags="open")
        v.make(title="Two", days=900, tags="sealed")
        v.clock.advance(days=2)
        report = v.capsules.reflection_report()
        self.assertEqual(report.total, 2)
        self.assertEqual([t for t, _ in report.top_tags], ["open"])
        self.assertIn("not an assessment", report.disclaimer)

    def test_empty_report(self):
        self.assertEqual(Vault().capsules.reflection_report().total, 0)


class DemoDataTests(unittest.TestCase):
    def test_demo_is_opt_in_and_removable(self):
        v = Vault()
        self.assertEqual(v.capsules.list_capsules(), [])
        self.assertEqual(v.capsules.load_demo_data(), 6)
        with self.assertRaises(ValueError):
            v.capsules.load_demo_data()
        self.assertEqual(v.capsules.remove_demo_data(), 6)
        self.assertEqual(v.capsules.list_capsules(), [])


if __name__ == "__main__":
    unittest.main()
