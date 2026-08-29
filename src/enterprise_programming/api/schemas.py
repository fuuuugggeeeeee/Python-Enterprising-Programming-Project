"""Validated HTTP request and response models."""

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(ApiModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserCreate(ApiModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "reader"] = "reader"

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "username may contain letters, numbers, dots, underscores, and hyphens"
            )
        return value.lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class UserUpdate(ApiModel):
    role: Optional[Literal["admin", "reader"]] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = Field(default=None, min_length=12, max_length=128)

    @model_validator(mode="after")
    def require_change(self) -> "UserUpdate":
        if self.role is None and self.is_active is None and self.new_password is None:
            raise ValueError("at least one user field must be supplied")
        return self


class StudentCreate(ApiModel):
    student_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    course: str = Field(min_length=1, max_length=128)

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, value: str) -> str:
        if not STUDENT_ID_PATTERN.fullmatch(value):
            raise ValueError(
                "student_id may contain letters, numbers, dots, underscores, and hyphens"
            )
        return value


class StudentUpdate(ApiModel):
    name: str = Field(min_length=1, max_length=128)
    course: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: str
    name: str
    course: str
    version: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


class StudentListResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    limit: int
    offset: int


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_username: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    occurred_at: datetime


class AuditListResponse(BaseModel):
    items: List[AuditResponse]
    total: int
    limit: int
    offset: int


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    version: str
    database: Literal["up", "down"]
