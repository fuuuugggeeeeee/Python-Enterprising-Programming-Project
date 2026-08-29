"""Database access isolated from HTTP concerns."""

from typing import List, Optional, Tuple

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from .models import AuditRecord, StudentRecord, UserRecord, utc_now


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: str) -> Optional[UserRecord]:
        return self.session.get(UserRecord, user_id)

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        return self.session.scalar(select(UserRecord).where(UserRecord.username == username))

    def list_all(self) -> List[UserRecord]:
        statement = select(UserRecord).order_by(UserRecord.username)
        return list(self.session.scalars(statement))

    def add(self, user: UserRecord) -> None:
        self.session.add(user)


class StudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, student_id: str) -> Optional[StudentRecord]:
        return self.session.get(StudentRecord, student_id)

    def list_page(
        self,
        limit: int,
        offset: int,
        query: Optional[str] = None,
    ) -> Tuple[List[StudentRecord], int]:
        filters = []
        if query:
            pattern = "%{}%".format(query)
            filters.append(
                or_(
                    StudentRecord.student_id.ilike(pattern),
                    StudentRecord.name.ilike(pattern),
                    StudentRecord.course.ilike(pattern),
                )
            )
        count_statement = select(func.count()).select_from(StudentRecord).where(*filters)
        items_statement = (
            select(StudentRecord)
            .where(*filters)
            .order_by(StudentRecord.student_id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(items_statement)), int(
            self.session.scalar(count_statement) or 0
        )

    def add(self, student: StudentRecord) -> None:
        self.session.add(student)

    def update_if_version(
        self,
        student_id: str,
        expected_version: int,
        name: str,
        course: str,
    ) -> Optional[StudentRecord]:
        statement = (
            update(StudentRecord)
            .where(
                StudentRecord.student_id == student_id,
                StudentRecord.version == expected_version,
            )
            .values(
                name=name,
                course=course,
                version=expected_version + 1,
                updated_at=utc_now(),
            )
            .returning(StudentRecord)
        )
        return self.session.execute(statement).scalar_one_or_none()

    def delete_if_version(self, student_id: str, expected_version: int) -> bool:
        statement = (
            delete(StudentRecord)
            .where(
                StudentRecord.student_id == student_id,
                StudentRecord.version == expected_version,
            )
            .returning(StudentRecord.student_id)
        )
        return self.session.execute(statement).scalar_one_or_none() is not None


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: AuditRecord) -> None:
        self.session.add(event)

    def list_page(self, limit: int, offset: int) -> Tuple[List[AuditRecord], int]:
        count = int(self.session.scalar(select(func.count()).select_from(AuditRecord)) or 0)
        statement = (
            select(AuditRecord)
            .order_by(AuditRecord.occurred_at.desc(), AuditRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement)), count
