"""Master-password handling and authenticated encryption."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import time
import unicodedata

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from database import Database
from utils.validation import validate_password

ENVELOPE_KEY = "key_envelope"
_ENVELOPE_AAD = b"echo:v1:key-envelope"
_NONCE_BYTES = 12
_SALT_BYTES = 16
_WRAPPED_BYTES = 32 + 16  # key + GCM tag
_MAX_MEMORY = 256 * 1024 * 1024


class SecurityError(Exception):
    """Base class for security failures."""


class AuthenticationError(SecurityError):
    """The master password was wrong or attempts are temporarily blocked."""


class VaultLockedError(SecurityError):
    """An operation needed the data key while the vault was locked."""


def record_aad(capsule_uuid: str, field: str) -> bytes:
    """Bind ciphertext to its capsule and field so blobs cannot be swapped."""
    return f"echo:v1:{capsule_uuid}:{field}".encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class SecurityService:
    """Owns the in-memory data key and all cryptographic operations."""

    def __init__(self, db: Database, *, kdf_n: int = 2**15) -> None:
        self._db = db
        self._kdf_n = kdf_n
        self._dek: bytes | None = None
        self._failures = 0
        self._blocked_until = 0.0

    @property
    def is_initialized(self) -> bool:
        return self._db.get_setting(ENVELOPE_KEY) is not None

    @property
    def is_unlocked(self) -> bool:
        return self._dek is not None

    def lock(self) -> None:
        """Drop the data key. (Python cannot guarantee the bytes are wiped.)"""
        self._dek = None

    @staticmethod
    def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
        secret = unicodedata.normalize("NFKC", password).encode("utf-8")
        return hashlib.scrypt(secret, salt=salt, n=n, r=r, p=p, maxmem=_MAX_MEMORY, dklen=32)

    def _make_envelope(self, password: str, dek: bytes) -> dict:
        salt, nonce = os.urandom(_SALT_BYTES), os.urandom(_NONCE_BYTES)
        n, r, p = self._kdf_n, 8, 1
        kek = self._derive(password, salt, n, r, p)
        wrapped = AESGCM(kek).encrypt(nonce, dek, _ENVELOPE_AAD)
        return {
            "version": 1, "kdf": "scrypt", "n": n, "r": r, "p": p,
            "salt": _b64(salt), "nonce": _b64(nonce), "wrapped_key": _b64(wrapped),
        }

    @staticmethod
    def validate_envelope(data: object) -> dict:
        """Check an envelope's structure and parameter bounds."""
        if not isinstance(data, dict):
            raise SecurityError("Key envelope is not an object.")
        try:
            if data["version"] != 1 or data["kdf"] != "scrypt":
                raise SecurityError("Unsupported key envelope version.")
            n, r, p = int(data["n"]), int(data["r"]), int(data["p"])
            if not (2**10 <= n <= 2**20 and n & (n - 1) == 0 and 1 <= r <= 16 and 1 <= p <= 4):
                raise SecurityError("Key derivation parameters are out of range.")
            salt = base64.b64decode(data["salt"], validate=True)
            nonce = base64.b64decode(data["nonce"], validate=True)
            wrapped = base64.b64decode(data["wrapped_key"], validate=True)
        except (KeyError, TypeError, ValueError) as exc:
            raise SecurityError("Key envelope is malformed.") from exc
        if (len(salt), len(nonce), len(wrapped)) != (_SALT_BYTES, _NONCE_BYTES, _WRAPPED_BYTES):
            raise SecurityError("Key envelope has unexpected field sizes.")
        return data

    def _load_envelope(self) -> dict:
        raw = self._db.get_setting(ENVELOPE_KEY)
        if raw is None:
            raise SecurityError("The vault has not been set up.")
        try:
            return self.validate_envelope(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SecurityError("Stored key envelope is corrupt.") from exc

    def _unwrap(self, password: str, envelope: dict) -> bytes:
        kek = self._derive(
            password, base64.b64decode(envelope["salt"]),
            int(envelope["n"]), int(envelope["r"]), int(envelope["p"]),
        )
        return AESGCM(kek).decrypt(
            base64.b64decode(envelope["nonce"]),
            base64.b64decode(envelope["wrapped_key"]),
            _ENVELOPE_AAD,
        )


    def setup(self, password: str) -> None:
        """Create the vault. Raises ValidationError for weak passwords."""
        if self.is_initialized:
            raise SecurityError("The vault is already set up.")
        validate_password(password)
        dek = AESGCM.generate_key(bit_length=256)
        self._db.set_setting(ENVELOPE_KEY, json.dumps(self._make_envelope(password, dek)))
        self._dek = dek

    def unlock(self, password: str) -> None:
        """Unlock with the master password, with back-off after repeated failures."""
        remaining = self._blocked_until - time.monotonic()
        if remaining > 0:
            raise AuthenticationError(f"Too many attempts. Try again in {math.ceil(remaining)}s.")
        envelope = self._load_envelope()
        try:
            dek = self._unwrap(password, envelope)
        except InvalidTag:
            self._failures += 1
            if self._failures >= 3:
                self._blocked_until = time.monotonic() + min(2 ** (self._failures - 2), 60)
            raise AuthenticationError("That password is not correct.") from None
        self._failures = 0
        self._dek = dek

    def change_password(self, old_password: str, new_password: str) -> None:
        """Re-wrap the data key under a new password."""
        validate_password(new_password)
        try:
            dek = self._unwrap(old_password, self._load_envelope())
        except InvalidTag:
            raise AuthenticationError("The current password is not correct.") from None
        self._db.set_setting(ENVELOPE_KEY, json.dumps(self._make_envelope(new_password, dek)))

    def export_envelope(self) -> dict:
        """Return the password-wrapped key envelope (safe to store; contains no plaintext key)."""
        return self._load_envelope()

    def install_envelope(self, envelope: object) -> None:
        """Adopt an envelope from a backup. Only allowed on an empty, uninitialised vault."""
        if self.is_initialized:
            raise SecurityError("This vault already has a password.")
        self._db.set_setting(ENVELOPE_KEY, json.dumps(self.validate_envelope(envelope)))


    def _key(self) -> bytes:
        if self._dek is None:
            raise VaultLockedError("The vault is locked.")
        return self._dek

    def encrypt(self, plaintext: bytes, aad: bytes) -> bytes:
        """Return nonce || ciphertext||tag."""
        nonce = os.urandom(_NONCE_BYTES)
        return nonce + AESGCM(self._key()).encrypt(nonce, plaintext, aad)

    def decrypt(self, blob: bytes, aad: bytes) -> bytes:
        key = self._key()
        if len(blob) < _NONCE_BYTES + 16:
            raise SecurityError("Stored data is too short to be valid.")
        try:
            return AESGCM(key).decrypt(blob[:_NONCE_BYTES], blob[_NONCE_BYTES:], aad)
        except InvalidTag:
            raise SecurityError("Stored data failed its integrity check.") from None

    def can_decrypt(self, blob: bytes, aad: bytes) -> bool:
        try:
            self.decrypt(blob, aad)
            return True
        except SecurityError:
            return False
