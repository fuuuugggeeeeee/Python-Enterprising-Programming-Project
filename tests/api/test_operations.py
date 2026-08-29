from fastapi.testclient import TestClient


def test_liveness_readiness_and_documentation_are_public(client: TestClient) -> None:
    assert client.get("/health/live").json()["status"] == "ok"
    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["database"] == "up"
    assert client.get("/docs").status_code == 200

    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == "2.0.0"
    assert "HTTPBearer" in schema["components"]["securitySchemes"]


def test_request_metadata_and_metrics_are_exposed(client: TestClient) -> None:
    response = client.get("/", headers={"X-Request-ID": "portfolio-test-request"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "portfolio-test-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-RateLimit-Limit"] == "1000"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "epp_http_requests_total" in metrics.text
    assert "epp_http_request_duration_seconds" in metrics.text


def test_unknown_routes_use_stable_error_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_readiness_reports_database_failure(client: TestClient) -> None:
    database = client.app.state.database
    original_check = database.is_ready
    database.is_ready = lambda: False
    try:
        response = client.get("/health/ready")
    finally:
        database.is_ready = original_check
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["database"] == "down"
