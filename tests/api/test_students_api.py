from fastapi.testclient import TestClient

STUDENT = {
    "student_id": "S001",
    "name": "Amina Patel",
    "course": "Computer Science",
}


def test_full_student_lifecycle_with_optimistic_concurrency(
    client: TestClient,
    admin_headers: dict,
) -> None:
    created = client.post("/api/v1/students", headers=admin_headers, json=STUDENT)
    assert created.status_code == 201
    assert created.json()["version"] == 1
    assert created.json()["created_by"]

    retrieved = client.get("/api/v1/students/S001", headers=admin_headers)
    assert retrieved.status_code == 200

    listing = client.get("/api/v1/students?q=amina&limit=10&offset=0", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["student_id"] == "S001"

    updated = client.put(
        "/api/v1/students/S001",
        headers=admin_headers,
        json={"name": "Amina Patel", "course": "Data Science", "expected_version": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["course"] == "Data Science"
    assert updated.json()["version"] == 2

    stale_update = client.put(
        "/api/v1/students/S001",
        headers=admin_headers,
        json={"name": "Stale", "course": "Stale", "expected_version": 1},
    )
    assert stale_update.status_code == 409

    stale_delete = client.delete(
        "/api/v1/students/S001?expected_version=1",
        headers=admin_headers,
    )
    assert stale_delete.status_code == 409

    deleted = client.delete(
        "/api/v1/students/S001?expected_version=2",
        headers=admin_headers,
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/students/S001", headers=admin_headers).status_code == 404


def test_duplicate_and_validation_errors_are_structured(
    client: TestClient,
    admin_headers: dict,
) -> None:
    assert client.post("/api/v1/students", headers=admin_headers, json=STUDENT).status_code == 201
    duplicate = client.post("/api/v1/students", headers=admin_headers, json=STUDENT)
    assert duplicate.status_code == 409

    invalid = client.post(
        "/api/v1/students",
        headers=admin_headers,
        json={"student_id": "bad id!", "name": "", "course": "Computing"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["details"]


def test_mutations_create_audit_events(client: TestClient, admin_headers: dict) -> None:
    client.post("/api/v1/students", headers=admin_headers, json=STUDENT)
    client.put(
        "/api/v1/students/S001",
        headers=admin_headers,
        json={"name": "Amina Patel", "course": "Data Science", "expected_version": 1},
    )

    audit = client.get("/api/v1/audit-events", headers=admin_headers)
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"student.created", "student.updated"}.issubset(actions)
    assert all(item["actor_username"] == "admin" for item in audit.json()["items"])
