import os
from uuid import uuid4

import pytest
from sqlalchemy import delete

from enterprise_programming.api.database import Database
from enterprise_programming.api.models import AuditRecord, StudentRecord, UserRecord
from enterprise_programming.api.schemas import StudentCreate
from enterprise_programming.api.services import ApiService


@pytest.mark.integration
def test_postgresql_round_trip_and_json_audit() -> None:
    database_url = os.environ.get("EPP_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("EPP_TEST_POSTGRES_URL is not configured")

    suffix = uuid4().hex[:10]
    username = "admin-{}".format(suffix)
    student_id = "S-{}".format(suffix)
    database = Database(database_url)
    assert database.engine.dialect.name == "postgresql"

    try:
        with database.session() as session:
            service = ApiService(session)
            admin = service.create_bootstrap_admin(username, "integration-password-value")
            student = service.create_student(
                StudentCreate(
                    student_id=student_id,
                    name="PostgreSQL Test Student",
                    course="Database Engineering",
                ),
                admin,
            )
            assert service.get_student(student_id).student_id == student.student_id
            events, _ = service.list_audit_events(100, 0)
            event = next(item for item in events if item.resource_id == student_id)
            assert event.details == {}
    finally:
        with database.session() as session:
            session.execute(delete(AuditRecord).where(AuditRecord.resource_id == student_id))
            session.execute(delete(StudentRecord).where(StudentRecord.student_id == student_id))
            session.execute(delete(UserRecord).where(UserRecord.username == username))
            session.commit()
        database.dispose()
