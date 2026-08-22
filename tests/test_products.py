from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

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
        name="Sports Drink 500ml",
        selling_price=Decimal("45.00"),
        cost_price=Decimal("22.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
        track_inventory=True,
        reorder_level=Decimal("20"),
    )


@pytest.mark.django_db
def test_category_unique_per_branch(branch, category):
    with pytest.raises(IntegrityError):
        Category.objects.create(branch=branch, name="Drinks")


@pytest.mark.django_db
def test_product_sku_unique_per_branch(branch, category, product):
    with pytest.raises(IntegrityError):
        Product.objects.create(
            branch=branch,
            category=category,
            sku="BEV-SD-500",
            name="Duplicate SKU",
            selling_price=Decimal("10.00"),
        )


@pytest.mark.django_db
def test_product_rejects_category_from_other_branch(branch, category):
    from apps.branches.models import Branch

    other = Branch.objects.create(code="B2", name="Second Branch")
    other_category = Category.objects.create(branch=other, name="Other Drinks")
    item = Product(
        branch=branch,
        category=other_category,
        sku="X-1",
        name="Mismatched",
        selling_price=Decimal("10.00"),
    )
    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_category_list_requires_login(django_client):
    response = django_client.get(reverse("products:category_list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_create_category_and_product(django_client, user, branch):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.post(
        reverse("products:category_create"),
        {"branch": branch.id, "name": "Snacks", "sort_order": 20, "is_active": "on"},
    )
    assert response.status_code == 302
    category = Category.objects.get(name="Snacks", branch=branch)

    response = django_client.post(
        reverse("products:product_create"),
        {
            "branch": branch.id,
            "category": category.id,
            "sku": "SNK-BAR-01",
            "name": "Energy Bar",
            "selling_price": "35.00",
            "cost_price": "15.00",
            "unit": ProductUnit.PIECE,
            "tax_status": TaxStatus.TAXABLE,
            "track_inventory": "on",
            "reorder_level": "15",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    product = Product.objects.get(sku="SNK-BAR-01")
    assert product.selling_price == Decimal("35.00")
    assert product.category == category


@pytest.mark.django_db
def test_product_list_search(django_client, user, product):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("products:product_list"), {"q": "Sports"})
    assert response.status_code == 200
    assert b"Sports Drink 500ml" in response.content
    assert b'aria-label="Edit"' in response.content
    assert b'aria-label="Deactivate"' in response.content
    assert b'aria-label="Status"' in response.content
    response = django_client.get(reverse("products:product_list"), {"q": "NOPE"})
    assert b"Sports Drink 500ml" not in response.content


@pytest.mark.django_db
def test_deactivate_product(django_client, user, product):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.post(reverse("products:product_toggle", args=[product.pk]))
    assert response.status_code == 302
    product.refresh_from_db()
    assert product.is_active is False


@pytest.mark.django_db
def test_create_form_loads_as_partial(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("products:product_create"), {"partial": "1"})
    assert response.status_code == 200
    assert b"data-modal-form" in response.content
    assert b"catalog-form" in response.content


@pytest.mark.django_db
def test_create_page_redirects_to_list_modal(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("products:product_create"))
    assert response.status_code == 302
    assert "modal=create" in response.url
