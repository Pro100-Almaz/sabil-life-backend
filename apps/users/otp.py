"""
Email-verification OTP flow for self-service registration.

The registration is a two-step handshake and no account exists until the code
is verified:

1. ``start_pending_registration`` validates-then-stashes the (already hashed)
   registration payload plus a fresh code in the cache, keyed by email, with a
   short TTL. It returns the plaintext code so the caller can email it.
2. ``verify_and_pop`` checks a submitted code, and on success deletes and
   returns the pending payload so the view can create the account.

Everything lives in the cache (Redis in prod), so entries self-expire and no
cleanup job is needed. Passwords are hashed at rest; codes are hashed too.
"""

import hashlib
import secrets

from django.contrib.auth.hashers import make_password
from django.core.cache import cache

CODE_TTL = 60 * 10  # 10 minutes
MAX_ATTEMPTS = 5
CODE_LENGTH = 6


class VerificationError(Exception):
    """Raised when a verify attempt fails. ``reason`` drives the API message."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _key(email: str) -> str:
    return f"reg:{email.strip().lower()}"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def generate_code() -> str:
    # secrets, not random — this is a security token. Zero-padded to CODE_LENGTH.
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def start_pending_registration(
    *, email: str, password: str, full_name: str, phone: str
) -> str:
    """Store the (validated) registration + a fresh code, return the plaintext
    code for the caller to email. Overwrites any prior pending entry, which is
    what a "resend" does."""
    code = generate_code()
    cache.set(
        _key(email),
        {
            "password": make_password(password),  # never store plaintext
            "full_name": full_name,
            "phone": phone,
            "code_hash": _hash_code(code),
            "attempts": 0,
        },
        timeout=CODE_TTL,
    )
    return code


def verify_and_pop(*, email: str, code: str) -> dict:
    """Check the code. On success, delete + return the pending payload.
    On failure, raise VerificationError with a ``reason``."""
    key = _key(email)
    data = cache.get(key)
    if data is None:
        raise VerificationError("expired")

    if data["attempts"] >= MAX_ATTEMPTS:
        cache.delete(key)
        raise VerificationError("too_many_attempts")

    if _hash_code(code) != data["code_hash"]:
        data["attempts"] += 1
        # Re-store WITHOUT resetting the TTL, else each wrong guess would
        # extend the window. cache.ttl is a django_redis extension; the test
        # cache (LocMemCache) lacks it, so fall back to the full TTL there.
        try:
            remaining = cache.ttl(key)
        except (AttributeError, NotImplementedError):
            remaining = CODE_TTL
        cache.set(key, data, timeout=remaining)
        raise VerificationError("invalid")

    cache.delete(key)  # single-use
    return data
