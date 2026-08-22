from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse

from apps.customers.models import Customer
from apps.sales.models import Sale
from core.services.sale_service import PaymentInput, SaleLineInput, SaleService
from core.services.shift_service import ShiftService
from core.domain.inventory import STOCK_IN
from core.services.inventory_service import InventoryService
from apps.products.models import Category, Product, ProductUnit


@pytest.fixture
def category(branch):
    return Category.objects.create(branch=branch, name="Drinks", sort_order=10)


@pytest.fixture
def product(branch, category):
    item = Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-SD-500",
        name="Sports Drink 500ml",
        selling_price=Decimal("45.00"),
        cost_price=Decimal("22.00"),
        unit=ProductUnit.BOTTLE,
        track_inventory=True,
    )
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=item.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        reference_type="opening",
    )
    return item


@pytest.mark.django_db
def test_customer_mobile_unique_per_branch(branch):
    Customer.objects.create(branch=branch, name="Ana Cruz", mobile="09171234567")
    with pytest.raises(IntegrityError):
        Customer.objects.create(branch=branch, name="Other", mobile="09171234567")


@pytest.mark.django_db
def test_optional_customer_on_sale(branch, user, product):
    customer = Customer.objects.create(branch=branch, name="Ana Cruz", mobile="09170001111")
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100"))
    sale = SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("45.00"))],
        customer_id=customer.id,
    )
    sale.refresh_from_db()
    assert sale.customer_id == customer.id
    assert customer.sales.count() == 1


@pytest.mark.django_db
def test_walk_in_sale_has_no_customer(branch, user, product):
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100"))
    sale = SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("45.00"))],
    )
    assert sale.customer_id is None


@pytest.mark.django_db
def test_customer_list_renders(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("customers:customer_list"))
    assert response.status_code == 200
    assert b"Add customer" in response.content
