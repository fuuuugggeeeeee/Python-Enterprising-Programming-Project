"""FastAPI dependencies for database sessions and authorization."""

from typing import Iterator, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import Settings
from .database import Database
from .errors import AuthenticationError, AuthorizationError
from .models import UserRecord
from .repositories import UserRepository
from .security import decode_access_token
from .services import ApiService

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_session(request: Request) -> Iterator[Session]:
    database = cast(Database, request.app.state.database)
    with database.session() as session:
        yield session


def get_service(session: Session = Depends(get_session)) -> ApiService:
    return ApiService(session)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    principal = decode_access_token(credentials.credentials, settings)
    user = UserRepository(session).get_by_id(principal.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User is inactive or no longer exists")
    return user


def require_admin(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if user.role != "admin":
        raise AuthorizationError()
    return user
