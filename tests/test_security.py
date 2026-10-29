import unittest

from database import Database
from services.security_service import AuthenticationError, SecurityError, SecurityService, VaultLockedError
from utils.validation import ValidationError


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.sec = SecurityService(self.db, kdf_n=2**10)

    def test_setup_then_unlock(self):
        self.assertFalse(self.sec.is_initialized)
        self.sec.setup("a very good password")
        self.assertTrue(self.sec.is_unlocked)
        self.sec.lock()
        self.assertFalse(self.sec.is_unlocked)
        self.sec.unlock("a very good password")
        self.assertTrue(self.sec.is_unlocked)

    def test_password_not_stored_in_plaintext(self):
        self.sec.setup("a very good password")
        self.assertNotIn("a very good password", self.db.get_setting("key_envelope"))

    def test_each_vault_gets_unique_salt(self):
        other_db = Database(":memory:")
        other = SecurityService(other_db, kdf_n=2**10)
        self.sec.setup("a very good password")
        other.setup("a very good password")
        self.assertNotEqual(self.sec.export_envelope()["salt"], other.export_envelope()["salt"])

    def test_wrong_password_rejected(self):
        self.sec.setup("a very good password")
        self.sec.lock()
        with self.assertRaises(AuthenticationError):
            self.sec.unlock("not the password")
        self.assertFalse(self.sec.is_unlocked)

    def test_lockout_after_repeated_failures(self):
        self.sec.setup("a very good password")
        self.sec.lock()
        for _ in range(3):
            with self.assertRaises(AuthenticationError):
                self.sec.unlock("wrong wrong wrong")
        with self.assertRaises(AuthenticationError) as ctx:
            self.sec.unlock("a very good password")
        self.assertIn("Too many attempts", str(ctx.exception))

    def test_weak_password_rejected(self):
        with self.assertRaises(ValidationError):
            self.sec.setup("short")

    def test_encrypt_round_trip_and_aad_binding(self):
        self.sec.setup("a very good password")
        blob = self.sec.encrypt(b"hello", b"aad-1")
        self.assertEqual(self.sec.decrypt(blob, b"aad-1"), b"hello")
        with self.assertRaises(SecurityError):
            self.sec.decrypt(blob, b"aad-2")
        tampered = blob[:-1] + bytes([blob[-1] ^ 1])
        with self.assertRaises(SecurityError):
            self.sec.decrypt(tampered, b"aad-1")

    def test_locked_vault_cannot_encrypt_or_decrypt(self):
        self.sec.setup("a very good password")
        blob = self.sec.encrypt(b"x", b"a")
        self.sec.lock()
        with self.assertRaises(VaultLockedError):
            self.sec.encrypt(b"x", b"a")
        with self.assertRaises(VaultLockedError):
            self.sec.decrypt(blob, b"a")

    def test_change_password_keeps_data_readable(self):
        self.sec.setup("a very good password")
        blob = self.sec.encrypt(b"keep me", b"a")
        with self.assertRaises(AuthenticationError):
            self.sec.change_password("wrong password!!", "another good password")
        self.sec.change_password("a very good password", "another good password")
        self.sec.lock()
        with self.assertRaises(AuthenticationError):
            self.sec.unlock("a very good password")
        self.sec._failures = 0
        self.sec._blocked_until = 0
        self.sec.unlock("another good password")
        self.assertEqual(self.sec.decrypt(blob, b"a"), b"keep me")

    def test_envelope_validation(self):
        for bad in (None, {}, {"version": 2}, {"version": 1, "kdf": "scrypt", "n": 3, "r": 8, "p": 1}):
            with self.assertRaises(SecurityError):
                SecurityService.validate_envelope(bad)


if __name__ == "__main__":
    unittest.main()
