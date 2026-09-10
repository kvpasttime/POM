# -*- coding: utf-8 -*-
"""安全原语：PBKDF2 密码哈希（R-AUTH-01）+ JWT（ADR-004）"""
import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

_PBKDF2_ITERATIONS = 600_000
_ALGO = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{_ALGO}${_PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


def generate_random_password(length: int = 10) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789#@$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_token(user_id: int, jti: str, expires_at: datetime) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def new_jti() -> str:
    return uuid.uuid4().hex


def session_expiry() -> datetime:
    settings = get_settings()
    return datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def random_hex(n: int = 16) -> str:
    return secrets.token_hex(n)


__all__ = [
    "hash_password", "verify_password", "generate_random_password",
    "create_token", "decode_token", "new_jti", "session_expiry",
    "sha256_bytes", "random_hex", "os",
]
