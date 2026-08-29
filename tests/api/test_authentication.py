from fastapi.testclient import TestClient

from .conftest import ADMIN_PASSWORD


def test_login_and_current_user(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == 1800

    current = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer {}".format(login.json()["access_token"])},
    )
    assert current.status_code == 200
    assert current.json()["username"] == "admin"
    assert current.json()["role"] == "admin"
    assert "password_hash" not in current.json()


def test_invalid_credentials_and_tokens_are_rejected(client: TestClient) -> None:
    wrong_password = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "incorrect-password-value"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.headers["WWW-Authenticate"] == "Bearer"
    assert wrong_password.json()["error"]["code"] == "authentication_required"

    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401

    invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer definitely-not-a-token"},
    )
    assert invalid.status_code == 401


def test_reader_role_cannot_write(
    client: TestClient,
    admin_headers: dict,
) -> None:
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "reviewer",
            "password": "reader-password-value",
            "role": "reader",
        },
    )
    assert created.status_code == 201

    login = client.post(
        "/api/v1/auth/token",
        json={"username": "reviewer", "password": "reader-password-value"},
    )
    reader_headers = {"Authorization": "Bearer {}".format(login.json()["access_token"])}

    can_read = client.get("/api/v1/students", headers=reader_headers)
    assert can_read.status_code == 200

    cannot_write = client.post(
        "/api/v1/students",
        headers=reader_headers,
        json={"student_id": "S001", "name": "Amina Patel", "course": "Computing"},
    )
    assert cannot_write.status_code == 403
    assert cannot_write.json()["error"]["code"] == "forbidden"


def test_duplicate_user_returns_conflict(client: TestClient, admin_headers: dict) -> None:
    payload = {
        "username": "reviewer",
        "password": "reader-password-value",
        "role": "reader",
    }
    assert client.post("/api/v1/users", headers=admin_headers, json=payload).status_code == 201
    duplicate = client.post("/api/v1/users", headers=admin_headers, json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"
    users = client.get("/api/v1/users", headers=admin_headers)
    assert users.status_code == 200
    assert {user["username"] for user in users.json()} == {"admin", "reviewer"}


def test_disabling_user_invalidates_existing_token(
    client: TestClient,
    admin_headers: dict,
) -> None:
    client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "temporary-reader",
            "password": "reader-password-value",
            "role": "reader",
        },
    )
    login = client.post(
        "/api/v1/auth/token",
        json={"username": "temporary-reader", "password": "reader-password-value"},
    )
    reader_headers = {"Authorization": "Bearer {}".format(login.json()["access_token"])}
    assert client.get("/api/v1/auth/me", headers=reader_headers).status_code == 200

    disabled = client.patch(
        "/api/v1/users/temporary-reader",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=reader_headers).status_code == 401


def test_admin_cannot_disable_itself(client: TestClient, admin_headers: dict) -> None:
    response = client.patch(
        "/api/v1/users/admin",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert response.status_code == 409


def test_admin_can_reset_user_password(client: TestClient, admin_headers: dict) -> None:
    client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "password-reset-user",
            "password": "original-password-value",
            "role": "reader",
        },
    )
    updated = client.patch(
        "/api/v1/users/password-reset-user",
        headers=admin_headers,
        json={"new_password": "replacement-password-value"},
    )
    assert updated.status_code == 200
    assert "new_password" not in updated.json()

    old_login = client.post(
        "/api/v1/auth/token",
        json={"username": "password-reset-user", "password": "original-password-value"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/token",
        json={"username": "password-reset-user", "password": "replacement-password-value"},
    )
    assert new_login.status_code == 200


def test_user_update_requires_a_change(client: TestClient, admin_headers: dict) -> None:
    response = client.patch("/api/v1/users/admin", headers=admin_headers, json={})
    assert response.status_code == 422


def test_unknown_user_update_returns_not_found(client: TestClient, admin_headers: dict) -> None:
    response = client.patch(
        "/api/v1/users/missing",
        headers=admin_headers,
        json={"role": "reader"},
    )
    assert response.status_code == 404
