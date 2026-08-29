"""Password hashing and signed access tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from .config import Settings
from .errors import AuthenticationError
from .models import UserRecord

PASSWORD_HASH = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"


@dataclass(frozen=True)
class Principal:
    user_id: str
    username: str
    role: str


@dataclass(frozen=True)
class TokenResponseData:
    token: str
    expires_in: int


def hash_password(password: str) -> str:
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, encoded_password: str) -> bool:
    return PASSWORD_HASH.verify(password, encoded_password)


def create_access_token(user: UserRecord, settings: Settings) -> TokenResponseData:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_minutes)
    claims: Dict[str, Any] = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    return TokenResponseData(
        token=jwt.encode(claims, settings.jwt_secret, algorithm=JWT_ALGORITHM),
        expires_in=settings.access_token_minutes * 60,
    )


def decode_access_token(token: str, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
        user_id = claims["sub"]
        username = claims["username"]
        role = claims["role"]
        if not all(isinstance(value, str) for value in (user_id, username, role)):
            raise AuthenticationError("Invalid access token")
        return Principal(user_id=user_id, username=username, role=role)
    except (InvalidTokenError, KeyError) as error:
        raise AuthenticationError("Invalid or expired access token") from error
