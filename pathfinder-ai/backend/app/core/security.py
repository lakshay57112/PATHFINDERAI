"""Password hashing, JWT and field/file encryption."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

ALGORITHM = "HS256"
COOKIE_NAME = "pf_session"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str, *, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes),
        "typ": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    return payload.get("sub")


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().fernet_key)


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _fernet().decrypt(token)


def encrypt_str(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_str(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        # Value stored before encryption was enabled, or with a rotated key.
        return value
