from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings


password_hasher = PasswordHasher()
phone_re = re.compile(r"^\+?[1-9]\d{7,14}$")


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def validate_password_policy(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    raw = value.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if raw.startswith("8") and len(raw) == 11:
        raw = "+7" + raw[1:]
    if not raw.startswith("+"):
        raw = "+" + raw
    if not phone_re.match(raw):
        raise ValueError("Invalid phone format")
    return raw


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, session_id: int) -> str:
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_access_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_access_secret, algorithms=["HS256"])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_email_token() -> str:
    return secrets.token_urlsafe(40)


def generate_phone_code() -> str:
    return str(secrets.randbelow(900000) + 100000)

