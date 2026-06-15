from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from jose import jwt

from app.core.config import settings

SECRET_KEY = settings.final_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

def _build_expiration(expires_delta: Optional[timedelta], *, default_delta: timedelta) -> datetime:
    delta = expires_delta or default_delta
    return datetime.now(timezone.utc) + delta


def _create_token(
    subject: Union[str, Any],
    token_type: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    default_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if token_type == "refresh":
        default_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    expire = _build_expiration(expires_delta, default_delta=default_delta)
    payload = {
        "exp": expire,
        "sub": str(subject),
        "token_type": token_type,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    token, _ = _create_token(subject, "access", expires_delta)
    return token


def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    token, _ = _create_token(subject, "refresh", expires_delta)
    return token


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def create_token_pair(subject: Union[str, Any]) -> dict[str, Any]:
    access_token, access_expires_at = _create_token(
        subject,
        "access",
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token, refresh_expires_at = _create_token(
        subject,
        "refresh",
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "access_token_expires_at": access_expires_at,
        "refresh_token_expires_at": refresh_expires_at,
    }
