import pytest
from django.urls import reverse

from core.domain.exceptions import AuthenticationError
from core.services.auth_service import AuthService


@pytest.mark.django_db
def test_authenticate_user_with_password(user, auth_service: AuthService):
    authenticated = auth_service.authenticate_user(username="cashier1", password="secure-pass-123")
    assert authenticated.id == user.id


@pytest.mark.django_db
def test_authenticate_user_invalid_password(user, auth_service: AuthService):
    with pytest.raises(AuthenticationError):
        auth_service.authenticate_user(username="cashier1", password="wrong")


@pytest.mark.django_db
def test_authenticate_user_with_pin(user, auth_service: AuthService):
    user.pin_hash = AuthService.hash_pin("1234")
    user.save(update_fields=["pin_hash"])

    authenticated = auth_service.authenticate_user(username="cashier1", pin="1234")
    assert authenticated.id == user.id


@pytest.mark.django_db
def test_build_authenticated_user_includes_roles(user, auth_service: AuthService):
    auth_user = auth_service.build_authenticated_user(user)
    assert auth_user.username == "cashier1"
    assert "cashier" in auth_user.roles


@pytest.mark.django_db
def test_health_endpoint(django_client):
    response = django_client.get("/health/")
    assert response.status_code == 200
    assert response.json()["service"] == "django"
