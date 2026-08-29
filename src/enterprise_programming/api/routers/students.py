"""Versioned student CRUD routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status

from ..dependencies import get_current_user, get_service, require_admin
from ..models import UserRecord
from ..schemas import StudentCreate, StudentListResponse, StudentResponse, StudentUpdate
from ..services import ApiService

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=StudentListResponse)
def list_students(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    query: Optional[str] = Query(default=None, alias="q", max_length=128),
    service: ApiService = Depends(get_service),
    _: UserRecord = Depends(get_current_user),
) -> StudentListResponse:
    items, total = service.list_students(limit, offset, query)
    return StudentListResponse(
        items=[StudentResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: str,
    service: ApiService = Depends(get_service),
    _: UserRecord = Depends(get_current_user),
) -> StudentResponse:
    return StudentResponse.model_validate(service.get_student(student_id))


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    service: ApiService = Depends(get_service),
    administrator: UserRecord = Depends(require_admin),
) -> StudentResponse:
    return StudentResponse.model_validate(service.create_student(payload, administrator))


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    service: ApiService = Depends(get_service),
    administrator: UserRecord = Depends(require_admin),
) -> StudentResponse:
    return StudentResponse.model_validate(
        service.update_student(student_id, payload, administrator)
    )


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: str,
    expected_version: int = Query(ge=1),
    service: ApiService = Depends(get_service),
    administrator: UserRecord = Depends(require_admin),
) -> Response:
    service.delete_student(student_id, expected_version, administrator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
