import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_register_user(client):
    email = f"test-{uuid.uuid4()}@example.com"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Test User"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    email = f"duplicate-{uuid.uuid4()}@example.com"

    # First registration
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Test User"
        }
    )

    assert response.status_code == 201

    # Second registration with the same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Another User"
        }
    )

    assert response.status_code == 409

def test_login_user(client):
    email = f"login-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    # Register user first
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Login User"
        }
    )

    assert response.status_code == 201

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    email = f"wrong-password-{uuid.uuid4()}@example.com"
    correct_password = "testpassword123"

    # Register user
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": correct_password,
            "full_name": "Wrong Password User"
        }
    )

    assert response.status_code == 201

    # Try logging in with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "wrongpassword123"
        }
    )

    assert response.status_code == 401

def test_login_nonexistent_user(client):
    email = f"nonexistent-{uuid.uuid4()}@example.com"

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "testpassword123"
        }
    )

    assert response.status_code == 401


def test_refresh_token(client):
    email = f"refresh-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Refresh User"
        }
    )

    assert response.status_code == 201

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 200

    tokens = response.json()

    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh_token = tokens["refresh_token"]

    # Get a new access token
    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token
        }
    )

    assert response.status_code == 200

    new_tokens = response.json()

    assert "access_token" in new_tokens
    assert new_tokens["refresh_token"] == refresh_token
    assert new_tokens["token_type"] == "bearer"


def test_invalid_refresh_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": "this-is-not-a-valid-refresh-token"
        }
    )

    assert response.status_code == 401


def test_logout_revokes_refresh_token(client):
    email = f"logout-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Logout User"
        }
    )

    assert response.status_code == 201

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 200

    refresh_token = response.json()["refresh_token"]

    # Logout
    response = client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token
        }
    )

    assert response.status_code == 200

    # Try to use the revoked refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token
        }
    )

    assert response.status_code == 401


def test_get_current_user(client):
    email = f"me-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Current User"
        }
    )

    assert response.status_code == 201

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    # Access protected endpoint
    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["full_name"] == "Current User"
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data

def test_get_current_user_without_token(client):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401



def test_malformed_refresh_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": ""
        }
    )

    assert response.status_code == 401

def test_logout_invalid_refresh_token(client):
    response = client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": "invalid-refresh-token"
        }
    )

    assert response.status_code == 401


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "testpassword123",
            "full_name": "Invalid Email"
        }
    )

    assert response.status_code == 422


def test_register_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"short-password-{uuid.uuid4()}@example.com",
            "password": "123",
            "full_name": "Short Password"
        }
    )

    assert response.status_code == 422


def test_register_short_name(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"short-name-{uuid.uuid4()}@example.com",
            "password": "testpassword123",
            "full_name": "A"
        }
    )

    assert response.status_code == 422


def test_get_current_user_invalid_token(client):
    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": "Bearer this-is-not-a-valid-jwt"
        }
    )

    assert response.status_code == 401

def test_update_current_user(client):
    email = f"update-{uuid.uuid4()}@example.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Original Name"
        }
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "testpassword123"
        }
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        json={
            "full_name": "Updated Name"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["full_name"] == "Updated Name"


def test_update_current_user_without_token(client):
    response = client.patch(
        "/api/v1/users/me",
        json={
            "full_name": "Updated Name"
        }
    )

    assert response.status_code == 401


def test_update_current_user_invalid_name(client):
    email = f"invalid-name-{uuid.uuid4()}@example.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Original Name"
        }
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "testpassword123"
        }
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.patch(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        json={
            "full_name": "A"
        }
    )

    assert response.status_code == 422


def test_update_current_user_then_get_profile(client):
    email = f"profile-{uuid.uuid4()}@example.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
            "full_name": "Before Update"
        }
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "testpassword123"
        }
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    update_response = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "full_name": "After Update"
        }
    )

    assert update_response.status_code == 200

    get_response = client.get(
        "/api/v1/users/me",
        headers=headers
    )

    assert get_response.status_code == 200
    assert get_response.json()["full_name"] == "After Update"