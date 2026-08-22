from decimal import Decimal

import pytest

from apps.products.models import Category, Product, ProductUnit, TaxStatus
from core.domain.inventory import STOCK_IN
from core.services.inventory_service import InventoryService
from core.services.shift_service import ShiftService


@pytest.fixture
def category(branch):
    return Category.objects.create(branch=branch, name="Drinks", sort_order=10)


@pytest.fixture
def product(branch, category):
    return Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-SD-500",
        name="Sports Drink 500ml",
        selling_price=Decimal("45.00"),
        cost_price=Decimal("22.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
        track_inventory=True,
    )


def _auth_headers(api_client):
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.django_db(transaction=True)
def test_shift_endpoints_require_auth(api_client):
    assert api_client.get("/api/v1/shifts/current").status_code == 401
    assert api_client.post("/api/v1/shifts/open", json={"opening_cash": "100.00"}).status_code == 401


@pytest.mark.django_db(transaction=True)
def test_open_cash_and_close_shift(api_client, user, branch):
    headers = _auth_headers(api_client)
    opened = api_client.post("/api/v1/shifts/open", json={"opening_cash": "100.00"}, headers=headers)
    assert opened.status_code == 200
    shift_id = opened.json()["id"]

    current = api_client.get("/api/v1/shifts/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == shift_id

    duplicate = api_client.post("/api/v1/shifts/open", json={"opening_cash": "10.00"}, headers=headers)
    assert duplicate.status_code == 409

    cash_in = api_client.post(
        f"/api/v1/shifts/{shift_id}/cash-in",
        json={"amount": "20.00", "reason": "float"},
        headers=headers,
    )
    assert cash_in.status_code == 200

    closed = api_client.post(
        "/api/v1/shifts/close",
        json={"shift_id": shift_id, "actual_cash": "120.00"},
        headers=headers,
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert closed.json()["over_short"] in ("0.00", "0.0", 0)


@pytest.mark.django_db(transaction=True)
def test_create_sale_void_and_refund_via_api(api_client, user, branch, product):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        reference_type="opening",
    )
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    headers = _auth_headers(api_client)

    created = api_client.post(
        "/api/v1/sales",
        json={
            "shift_id": shift.id,
            "items": [{"product_id": product.id, "quantity": "1", "unit_price": "1.00"}],
            "payments": [{"method": "cash", "amount": "50.00"}],
        },
        headers=headers,
    )
    assert created.status_code == 200
    body = created.json()
    assert body["net_amount"] in ("45.00", "45.0", 45)
    assert body["status"] == "completed"
    sale_id = body["id"]
    item_id = body["items"][0]["id"]

    detail = api_client.get(f"/api/v1/sales/{sale_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["transaction_number"] == body["transaction_number"]

    refunded = api_client.post(
        f"/api/v1/sales/{sale_id}/refund",
        json={"shift_id": shift.id, "lines": [{"sale_item_id": item_id, "quantity": "1"}], "method": "cash"},
        headers=headers,
    )
    assert refunded.status_code == 200
    assert refunded.json()["amount"] in ("45.00", "45.0", 45)

    held = api_client.post(
        "/api/v1/sales/hold",
        json={"shift_id": shift.id, "items": [{"product_id": product.id, "quantity": "1"}]},
        headers=headers,
    )
    assert held.status_code == 200
    assert held.json()["status"] == "held"

    resumed = api_client.post(
        f"/api/v1/sales/hold/{held.json()['id']}/resume",
        json={"payments": [{"method": "maya", "amount": "45.00"}]},
        headers=headers,
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"

    voided = api_client.post(
        f"/api/v1/sales/{resumed.json()['id']}/void",
        json={"reason": "test"},
        headers=headers,
    )
    assert voided.status_code == 200
    assert voided.json()["status"] == "void"


@pytest.mark.django_db(transaction=True)
def test_quote_receipt_device_and_sync(api_client, user, branch, product):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        reference_type="opening",
    )
    headers = _auth_headers(api_client)
    quoted = api_client.post(
        "/api/v1/sales/quote",
        json={"items": [{"product_id": product.id, "quantity": "2"}]},
        headers=headers,
    )
    assert quoted.status_code == 200
    assert quoted.json()["net_amount"] in ("90.00", "90.0", 90)

    device = api_client.post(
        "/api/v1/devices/register",
        json={"device_code": "POS-COUNTER-1", "name": "Counter 1"},
        headers=headers,
    )
    assert device.status_code == 200
    device_id = device.json()["id"]

    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    pushed = api_client.post(
        "/api/v1/sync/push",
        json={
            "device_id": device_id,
            "sales": [
                {
                    "client_sale_uuid": uuid,
                    "shift_id": shift.id,
                    "items": [{"product_id": product.id, "quantity": "1"}],
                    "payments": [{"method": "cash", "amount": "45.00"}],
                }
            ],
        },
        headers=headers,
    )
    assert pushed.status_code == 200
    assert pushed.json()["results"][0]["status"] == "synced"
    sale_id = pushed.json()["results"][0]["sale_id"]

    receipt = api_client.get(f"/api/v1/sales/{sale_id}/receipt", headers=headers)
    assert receipt.status_code == 200
    assert "TOTAL" in receipt.json()["text"]

    pulled = api_client.get("/api/v1/sync/pull", headers=headers)
    assert pulled.status_code == 200
    assert pulled.json()["products"]
