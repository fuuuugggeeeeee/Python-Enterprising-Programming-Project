from typing import Dict, Iterator

import pytest
from fastapi.testclient import TestClient

from enterprise_programming.api.app import create_app
from enterprise_programming.api.config import Settings
from enterprise_programming.api.database import Base, Database

ADMIN_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-that-is-long-enough-for-tests",
        bootstrap_admin_username="admin",
        bootstrap_admin_password=ADMIN_PASSWORD,
        json_logs=False,
        rate_limit_per_minute=1_000,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    app = create_app(settings=settings, database=database)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> Dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer {}".format(response.json()["access_token"])}
