"""Authentication routes."""

from fastapi import APIRouter, Depends

from ..config import Settings
from ..dependencies import get_current_user, get_service, get_settings
from ..models import UserRecord
from ..schemas import LoginRequest, TokenResponse, UserResponse
from ..security import create_access_token
from ..services import ApiService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    service: ApiService = Depends(get_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = service.authenticate(payload.username, payload.password)
    token = create_access_token(user, settings)
    return TokenResponse(access_token=token.token, expires_in=token.expires_in)


@router.get("/me", response_model=UserResponse)
def current_user(user: UserRecord = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
