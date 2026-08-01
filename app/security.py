import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Tuple

import jwt

from app.config import settings

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> Tuple[str, str]:
    """Returns (password_hash, salt), both base64-encoded."""
    salt = base64.b64encode(os.urandom(16)).decode()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return base64.b64encode(digest).decode(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return hmac.compare_digest(base64.b64encode(digest).decode(), password_hash)


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRES_HOURS)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
