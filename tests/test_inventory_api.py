from decimal import Decimal

import pytest

from apps.products.models import Category, Product, ProductUnit
from core.domain.inventory import STOCK_IN
from core.services.inventory_service import InventoryService


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
        unit=ProductUnit.BOTTLE,
        track_inventory=True,
        reorder_level=Decimal("20"),
    )


def _auth_headers(api_client):
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.django_db(transaction=True)
def test_inventory_balances_require_auth(api_client):
    assert api_client.get("/api/v1/inventory/balances").status_code == 401


@pytest.mark.django_db(transaction=True)
def test_list_and_get_balance(api_client, user, product, branch):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("15"),
    )
    headers = _auth_headers(api_client)
    listing = api_client.get("/api/v1/inventory/balances", headers=headers)
    assert listing.status_code == 200
    row = listing.json()[0]
    assert row["sku"] == "BEV-SD-500"
    assert Decimal(str(row["on_hand"])) == Decimal("15")
    assert row["is_low"] is True

    detail = api_client.get(f"/api/v1/inventory/balances/{product.id}", headers=headers)
    assert detail.status_code == 200
    assert Decimal(str(detail.json()["on_hand"])) == Decimal("15")
