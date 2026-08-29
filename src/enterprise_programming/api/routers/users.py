"""Administrator-managed API users."""

from typing import List

from fastapi import APIRouter, Depends, status

from ..dependencies import get_service, require_admin
from ..models import UserRecord
from ..schemas import UserCreate, UserResponse, UserUpdate
from ..services import ApiService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserResponse])
def list_users(
    service: ApiService = Depends(get_service),
    _: UserRecord = Depends(require_admin),
) -> List[UserResponse]:
    return [UserResponse.model_validate(user) for user in service.list_users()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    service: ApiService = Depends(get_service),
    administrator: UserRecord = Depends(require_admin),
) -> UserResponse:
    user = service.create_user(payload, actor=administrator.username)
    return UserResponse.model_validate(user)


@router.patch("/{username}", response_model=UserResponse)
def update_user(
    username: str,
    payload: UserUpdate,
    service: ApiService = Depends(get_service),
    administrator: UserRecord = Depends(require_admin),
) -> UserResponse:
    user = service.update_user(username, payload, administrator)
    return UserResponse.model_validate(user)
