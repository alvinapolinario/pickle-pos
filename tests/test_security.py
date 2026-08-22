from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Permission, Role, User
from apps.audit.middleware import write_audit_log
from apps.audit.models import AuditLog
from apps.audit.tasks import prune_audit_logs
from apps.products.models import Category, Product, ProductUnit, TaxStatus
from core.domain.auth import require_permission
from core.domain.exceptions import AuthenticationError, AuthorizationError
from core.domain.inventory import STOCK_IN
from core.services.auth_service import AuthService
from core.services.inventory_service import InventoryService
from core.services.security import RateLimiter, reset_security_counters
from core.services.shift_service import ShiftService


@pytest.fixture
def product(branch):
    category = Category.objects.create(branch=branch, name="Drinks", sort_order=10)
    return Product.objects.create(
        branch=branch,
        category=category,
        sku="SEC-SD-500",
        name="Security Drink",
        selling_price=Decimal("45.00"),
        cost_price=Decimal("22.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
        track_inventory=True,
    )


def _headers(api_client, username="cashier1", password="secure-pass-123"):
    login = api_client.post("/api/v1/auth/login", json={"username": username, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_rate_limiter_blocks_after_limit():
    reset_security_counters()
    limiter = RateLimiter()
    key = "rl:test:unit"
    for _ in range(3):
        allowed, _ = limiter.hit(key, limit=3, window_seconds=60)
        assert allowed
    allowed, retry = limiter.hit(key, limit=3, window_seconds=60)
    assert not allowed
    assert retry >= 0


@pytest.mark.django_db
def test_login_lockout_after_failed_attempts(branch):
    reset_security_counters()
    User.objects.create_user(username="lockme", password="secure-pass-123", branch=branch)
    service = AuthService()
    service.lockout.max_attempts = 3
    service.lockout.window_seconds = 900
    for _ in range(3):
        with pytest.raises(AuthenticationError):
            service.authenticate_user(username="lockme", password="wrong")
    with pytest.raises(AuthenticationError, match="locked"):
        service.authenticate_user(username="lockme", password="secure-pass-123")
    reset_security_counters()


@pytest.mark.django_db
def test_successful_login_clears_lockout(user):
    reset_security_counters()
    service = AuthService()
    with pytest.raises(AuthenticationError):
        service.authenticate_user(username="cashier1", password="wrong")
    authenticated = service.authenticate_user(username="cashier1", password="secure-pass-123")
    assert authenticated.id == user.id
    reset_security_counters()


def test_require_permission_raises_authorization_error():
    with pytest.raises(AuthorizationError):
        require_permission(frozenset({"sales.create"}), "sales.discount")
    require_permission(frozenset({"sales.*"}), "sales.discount")


@pytest.mark.django_db(transaction=True)
def test_cashier_cannot_apply_discount(api_client, user, branch, product):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        reference_type="opening",
    )
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    headers = _headers(api_client)
    response = api_client.post(
        "/api/v1/sales",
        json={
            "shift_id": shift.id,
            "items": [{"product_id": product.id, "quantity": "1"}],
            "payments": [{"method": "cash", "amount": "40.00"}],
            "discount_amount": "5.00",
        },
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_discount_permission_allows_sale(api_client, user, branch, product, cashier_role):
    perm, _ = Permission.objects.get_or_create(
        code="sales.discount", defaults={"name": "Apply sale discounts", "module": "sales"}
    )
    cashier_role.permissions.add(perm)
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        reference_type="opening",
    )
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    headers = _headers(api_client)
    response = api_client.post(
        "/api/v1/sales",
        json={
            "shift_id": shift.id,
            "items": [{"product_id": product.id, "quantity": "1"}],
            "payments": [{"method": "cash", "amount": "40.00"}],
            "discount_amount": "5.00",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["discount_amount"] in ("5.00", "5.0", 5)


@pytest.mark.django_db
def test_audit_viewer_requires_permission(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("console:audit_list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_audit_viewer_lists_filtered_logs(django_client, user, cashier_role):
    perm, _ = Permission.objects.get_or_create(
        code="audit.view", defaults={"name": "View audit logs", "module": "audit"}
    )
    cashier_role.permissions.add(perm)
    write_audit_log(action="auth.login", entity_type="user", entity_id=str(user.id), user=user)
    write_audit_log(action="sale.void", entity_type="sale", entity_id="99", user=user, reason="test")
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("console:audit_list"), {"action": "sale.void"})
    assert response.status_code == 200
    assert b"sale.void" in response.content
    assert b"auth.login" not in response.content


@pytest.mark.django_db
def test_console_login_writes_audit(django_client, user):
    response = django_client.post(
        reverse("console:login"),
        {"username": "cashier1", "password": "secure-pass-123"},
    )
    assert response.status_code == 302
    assert AuditLog.objects.filter(action="auth.login", entity_id=str(user.id)).exists()


@pytest.mark.django_db
def test_prune_audit_logs_respects_retention():
    keep = AuditLog.objects.create(action="keep", entity_type="sale", entity_id="1")
    old = AuditLog.objects.create(action="drop", entity_type="sale", entity_id="2")
    AuditLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=400))
    deleted = prune_audit_logs(days=365)
    assert deleted == 1
    assert AuditLog.objects.filter(pk=keep.pk).exists()
    assert not AuditLog.objects.filter(pk=old.pk).exists()


@pytest.mark.django_db
def test_staff_permissions_wildcard_for_auditor(db, branch):
    role = Role.objects.create(code="auditor-test", name="Auditor Test")
    perm, _ = Permission.objects.get_or_create(
        code="audit.view", defaults={"name": "View audit logs", "module": "audit"}
    )
    role.permissions.add(perm)
    user = User.objects.create_user(username="auditor1", password="secure-pass-123", branch=branch)
    user.roles.add(role)
    from apps.console.views import _staff_permissions
    from core.domain.auth import user_has_permission

    assert user_has_permission(_staff_permissions(user), "audit.view")
