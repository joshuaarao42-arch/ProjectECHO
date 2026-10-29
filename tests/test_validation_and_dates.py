import unittest
from datetime import date, datetime, timedelta

from utils import dates
from utils.validation import ValidationError, normalize_tags, validate_capsule_input, validate_password

NOW = datetime(2026, 1, 1, 9, 0, 0)


def valid(**over):
    args = dict(title="T", body="B", category="Memory", tags="x", unlock_at=NOW + timedelta(days=1), created_at=NOW)
    args.update(over)
    return validate_capsule_input(**args)


class ValidationTests(unittest.TestCase):
    def test_accepts_valid_input(self):
        self.assertEqual(valid()["title"], "T")

    def test_rejects_past_and_equal_unlock_dates(self):
        for unlock in (NOW - timedelta(days=1), NOW):
            with self.assertRaises(ValidationError) as ctx:
                valid(unlock_at=unlock)
            self.assertIn("unlock_at", ctx.exception.errors)

    def test_rejects_unlock_dates_too_far_away(self):
        with self.assertRaises(ValidationError):
            valid(unlock_at=NOW + timedelta(days=365 * 101))

    def test_required_fields(self):
        with self.assertRaises(ValidationError) as ctx:
            valid(title="  ", body="", category="Nope")
        self.assertEqual(set(ctx.exception.errors), {"title", "body", "category"})

    def test_tag_normalisation(self):
        self.assertEqual(normalize_tags("#Work, work ;  Life ,,"), ["work", "life"])

    def test_too_many_tags(self):
        with self.assertRaises(ValidationError):
            valid(tags=",".join(f"t{i}" for i in range(20)))

    def test_password_length(self):
        with self.assertRaises(ValidationError):
            validate_password("short")
        validate_password("long enough pw")


class DateTests(unittest.TestCase):
    def test_countdown_format(self):
        self.assertEqual(dates.format_countdown(timedelta(days=2, hours=3, minutes=4, seconds=5)), "2d 03h 04m 05s")
        self.assertEqual(dates.format_countdown(timedelta(hours=1)), "01h 00m 00s")
        self.assertEqual(dates.format_countdown(timedelta(seconds=-5)), "00h 00m 00s")

    def test_add_months_clamps(self):
        self.assertEqual(dates.add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(dates.add_months(date(2026, 11, 15), 3), date(2027, 2, 15))

    def test_input_parsing(self):
        self.assertEqual(dates.combine_date_time("2026-05-04", "07:30"), datetime(2026, 5, 4, 7, 30))
        with self.assertRaises(ValueError):
            dates.parse_date_input("04/05/2026")
        with self.assertRaises(ValueError):
            dates.parse_time_input("25:00")

    def test_elapsed(self):
        text = dates.elapsed_description(datetime(2024, 1, 1), datetime(2026, 3, 5))
        self.assertIn("2 years", text)


if __name__ == "__main__":
    unittest.main()
