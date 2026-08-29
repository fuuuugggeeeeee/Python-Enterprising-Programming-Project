from fastapi.testclient import TestClient

from enterprise_programming.api.app import create_app
from enterprise_programming.api.config import Settings
from enterprise_programming.api.database import Base, Database


def test_rate_limit_returns_429() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-that-is-long-enough-for-tests",
        rate_limit_per_minute=2,
        json_logs=False,
    )
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    with TestClient(create_app(settings, database)) as client:
        assert client.get("/").status_code == 200
        assert client.get("/docs").status_code == 200
        limited = client.get("/openapi.json")
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "rate_limit_exceeded"
        assert "Retry-After" in limited.headers
        assert client.get("/health/live").status_code == 200
