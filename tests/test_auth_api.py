import pytest


@pytest.mark.django_db(transaction=True)
def test_api_login_success(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "cashier1"


@pytest.mark.django_db(transaction=True)
def test_api_login_invalid_credentials(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_api_me_requires_auth(api_client):
    response = api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_api_me_returns_current_user(api_client, user):
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    token = login.json()["access_token"]

    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "cashier1"


@pytest.mark.django_db(transaction=True)
def test_api_refresh_rotates_token(api_client, user):
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"] != refresh_token


@pytest.mark.django_db(transaction=True)
def test_api_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "fastapi"
