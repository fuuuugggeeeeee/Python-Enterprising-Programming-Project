"""Business operations and transaction boundaries."""

from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .errors import AuthenticationError, ConflictError, NotFoundError
from .models import AuditRecord, StudentRecord, UserRecord
from .repositories import AuditRepository, StudentRepository, UserRepository
from .schemas import StudentCreate, StudentUpdate, UserCreate, UserUpdate
from .security import hash_password, verify_password


class ApiService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.students = StudentRepository(session)
        self.audit = AuditRepository(session)

    def authenticate(self, username: str, password: str) -> UserRecord:
        user = self.users.get_by_username(username.lower())
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        return user

    def create_user(self, payload: UserCreate, actor: str) -> UserRecord:
        user = UserRecord(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        self.users.add(user)
        self.audit.add(
            AuditRecord(
                actor_username=actor,
                action="user.created",
                resource_type="user",
                resource_id=payload.username,
                details={"role": payload.role},
            )
        )
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ConflictError("Username already exists") from error
        self.session.refresh(user)
        return user

    def create_bootstrap_admin(self, username: str, password: str) -> UserRecord:
        existing = self.users.get_by_username(username.lower())
        if existing is not None:
            return existing
        user = UserRecord(
            username=username.lower(),
            password_hash=hash_password(password),
            role="admin",
        )
        self.users.add(user)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.users.get_by_username(username.lower())
            if existing is None:
                raise
            return existing
        self.session.refresh(user)
        return user

    def list_users(self) -> List[UserRecord]:
        return self.users.list_all()

    def update_user(
        self,
        username: str,
        payload: UserUpdate,
        actor: UserRecord,
    ) -> UserRecord:
        user = self.users.get_by_username(username.lower())
        if user is None:
            raise NotFoundError("User")
        if user.id == actor.id and (payload.role == "reader" or payload.is_active is False):
            raise ConflictError("Administrators cannot remove their own access")
        if payload.role is not None:
            user.role = payload.role
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.new_password is not None:
            user.password_hash = hash_password(payload.new_password)
        self.audit.add(
            AuditRecord(
                actor_username=actor.username,
                action="user.updated",
                resource_type="user",
                resource_id=user.username,
                details={
                    "role": user.role,
                    "is_active": user.is_active,
                    "password_reset": payload.new_password is not None,
                },
            )
        )
        self.session.commit()
        self.session.refresh(user)
        return user

    def create_student(self, payload: StudentCreate, actor: UserRecord) -> StudentRecord:
        student = StudentRecord(
            student_id=payload.student_id,
            name=payload.name,
            course=payload.course,
            created_by=actor.id,
        )
        self.students.add(student)
        self._audit_student(actor.username, "student.created", student.student_id, {})
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ConflictError("Student ID already exists") from error
        self.session.refresh(student)
        return student

    def get_student(self, student_id: str) -> StudentRecord:
        student = self.students.get(student_id)
        if student is None:
            raise NotFoundError("Student")
        return student

    def list_students(
        self,
        limit: int,
        offset: int,
        query: Optional[str],
    ) -> Tuple[List[StudentRecord], int]:
        return self.students.list_page(limit, offset, query)

    def update_student(
        self,
        student_id: str,
        payload: StudentUpdate,
        actor: UserRecord,
    ) -> StudentRecord:
        if self.students.get(student_id) is None:
            raise NotFoundError("Student")
        student = self.students.update_if_version(
            student_id,
            payload.expected_version,
            payload.name,
            payload.course,
        )
        if student is None:
            self.session.rollback()
            raise ConflictError(
                "Student was modified; refresh it and retry with the current version"
            )
        self._audit_student(
            actor.username,
            "student.updated",
            student_id,
            {"version": student.version},
        )
        self.session.commit()
        return student

    def delete_student(self, student_id: str, expected_version: int, actor: UserRecord) -> None:
        if self.students.get(student_id) is None:
            raise NotFoundError("Student")
        if not self.students.delete_if_version(student_id, expected_version):
            self.session.rollback()
            raise ConflictError(
                "Student was modified; refresh it and retry with the current version"
            )
        self._audit_student(
            actor.username,
            "student.deleted",
            student_id,
            {"version": expected_version},
        )
        self.session.commit()

    def list_audit_events(self, limit: int, offset: int) -> Tuple[List[AuditRecord], int]:
        return self.audit.list_page(limit, offset)

    def _audit_student(
        self,
        actor: str,
        action: str,
        student_id: str,
        details: dict,
    ) -> None:
        self.audit.add(
            AuditRecord(
                actor_username=actor,
                action=action,
                resource_type="student",
                resource_id=student_id,
                details=details,
            )
        )
