import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.accounts.models import Permission, Role
from apps.branches.models import Branch
from core.services.auth_service import AuthService

User = get_user_model()


@pytest.fixture
def branch(db):
    return Branch.objects.create(code="HQ", name="Main Branch", city="Manila")


@pytest.fixture
def cashier_role(db):
    role = Role.objects.create(code="cashier", name="Cashier")
    codes = [
        ("sales.create", "Create sales"),
        ("sales.refund", "Process refunds"),
    ]
    permissions = [
        Permission.objects.get_or_create(code=code, defaults={"name": name, "module": "sales"})[0]
        for code, name in codes
    ]
    role.permissions.set(permissions)
    return role


@pytest.fixture
def user(db, branch, cashier_role):
    user = User.objects.create_user(
        username="cashier1",
        password="secure-pass-123",
        email="cashier1@example.com",
        branch=branch,
    )
    user.roles.add(cashier_role)
    return user


@pytest.fixture
def auth_service():
    return AuthService()


@pytest.fixture
def django_client():
    return Client()


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient

    from fastapi_api.main import app

    return TestClient(app, backend="asyncio")
