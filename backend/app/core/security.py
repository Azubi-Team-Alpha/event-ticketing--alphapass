"""
Ticket Hub – shared security helpers (password hashing, JWT).
"""
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt
from app.core.config import settings


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    subject_id: str,
    role: str,          # "admin" | "organizer"
    extra: dict | None = None,
    expires_minutes: int | None = None,
) -> str:
    expire = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {
        "sub":  subject_id,
        "role": role,
        "exp":  datetime.now(timezone.utc) + timedelta(minutes=expire),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodes and returns the payload. Raises jose.JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
