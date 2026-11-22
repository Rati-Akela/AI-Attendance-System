"""Password hashing and credential helpers (standard library only)."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

_ITERATIONS = 200_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# No 0/O/1/I/L so codes are easy to read out or type from a slip of paper.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def hash_password(password: str, iterations: int = _ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def validate_password(password: str) -> str | None:
    """Return an error message, or None if the password is acceptable."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password.isdigit() or password.isalpha():
        return "Use a mix of letters and numbers."
    return None


def generate_access_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def generate_login_id() -> str:
    return "SC-" + "".join(secrets.choice(_ALPHABET) for _ in range(6))
