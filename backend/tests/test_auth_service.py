"""Unit tests for password hashing and verification."""

from __future__ import annotations

import unicodedata
import unittest

from backend.services.auth_service import hash_password, verify_password


class TestAuthPasswordUnicode(unittest.TestCase):
    """Passwords with Polish diacritics must hash and verify reliably."""

    def test_polish_password_roundtrip(self) -> None:
        plain = "zażółć gęślą jaźń"
        hashed = hash_password(plain)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("zazólc gesla jazn", hashed))

    def test_polish_password_longer_than_bcrypt_byte_limit(self) -> None:
        # 40 x 'ą' = 80 bajtów UTF-8 — samo bcrypt by odrzuciło ten sekret
        plain = "ą" * 40
        self.assertGreater(len(plain.encode("utf-8")), 72)
        hashed = hash_password(plain)
        self.assertTrue(verify_password(plain, hashed))

    def test_nfc_and_nfd_forms_verify_the_same_hash(self) -> None:
        plain_nfc = unicodedata.normalize("NFC", "zażółć")
        plain_nfd = unicodedata.normalize("NFD", "zażółć")
        self.assertNotEqual(plain_nfc, plain_nfd)
        hashed = hash_password(plain_nfc)
        self.assertTrue(verify_password(plain_nfd, hashed))


if __name__ == "__main__":
    unittest.main()
