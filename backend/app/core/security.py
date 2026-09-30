"""Security primitives: Argon2id password hashing and PyJWT session tokens."""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Set
import uuid
import argon2
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
import jwt

from app.core.config import settings

_password_hasher = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

COMMON_PASSWORDS: Set[str] = {
    "password",
    "password123",
    "1234567890",
    "123456789",
    "12345678",
    "qwerty1234",
    "admin12345",
    "welcome123",
    "letmein123",
    "iloveyou123",
    "lifelink123",
}


def hash_password(password: str) -> str:
    """Hash password using memory-hard Argon2id."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored Argon2id hash using constant-time comparison."""
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def validate_password_strength(password: str) -> None:
    """Validate minimum 10 characters and check common password denylist (T-02-02)."""
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common or easily guessed")


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    demo_session_id: Optional[uuid.UUID] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate signed HS256 JWT access token with 12h expiration (AUTH-02)."""
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + (expires_delta or timedelta(hours=12))
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "demo_session_id": str(demo_session_id) if demo_session_id else None,
        "iat": int(now_utc.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and cryptographically verify HS256 JWT access token."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
