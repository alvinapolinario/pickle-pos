from decimal import Decimal

import pytest

from apps.products.models import Category, Product, ProductUnit, TaxStatus


@pytest.fixture
def category(branch):
    return Category.objects.create(branch=branch, name="Drinks", sort_order=10)


@pytest.fixture
def product(branch, category):
    return Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-SD-500",
        barcode="4801234560001",
        name="Sports Drink 500ml",
        selling_price=Decimal("45.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
    )


def _auth_headers(api_client, user):
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.django_db(transaction=True)
def test_catalog_endpoints_require_auth(api_client):
    assert api_client.get("/api/v1/products").status_code == 401
    assert api_client.get("/api/v1/categories").status_code == 401


@pytest.mark.django_db(transaction=True)
def test_list_categories_and_products(api_client, user, category, product):
    headers = _auth_headers(api_client, user)
    categories = api_client.get("/api/v1/categories", headers=headers)
    assert categories.status_code == 200
    assert categories.json()[0]["name"] == "Drinks"

    products = api_client.get("/api/v1/products", headers=headers)
    assert products.status_code == 200
    assert products.json()[0]["sku"] == "BEV-SD-500"
    assert products.json()[0]["selling_price"] in ("45.00", "45.0", 45.0)

    detail = api_client.get(f"/api/v1/products/{product.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Sports Drink 500ml"


@pytest.mark.django_db(transaction=True)
def test_product_detail_not_found(api_client, user):
    headers = _auth_headers(api_client, user)
    response = api_client.get("/api/v1/products/99999", headers=headers)
    assert response.status_code == 404


@pytest.mark.django_db(transaction=True)
def test_lookup_product_by_barcode_and_sku(api_client, user, product):
    headers = _auth_headers(api_client, user)
    by_barcode = api_client.get("/api/v1/products/lookup", params={"code": "4801234560001"}, headers=headers)
    assert by_barcode.status_code == 200
    assert by_barcode.json()["sku"] == "BEV-SD-500"

    by_sku = api_client.get("/api/v1/products/lookup", params={"code": "bev-sd-500"}, headers=headers)
    assert by_sku.status_code == 200
    assert by_sku.json()["name"] == "Sports Drink 500ml"

    missing = api_client.get("/api/v1/products/lookup", params={"code": "0000000000000"}, headers=headers)
    assert missing.status_code == 404
