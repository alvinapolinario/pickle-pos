from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.urls import reverse

from apps.inventory.models import InventoryBalance, InventoryMovement
from apps.products.models import Category, Product, ProductUnit, TaxStatus
from core.domain.exceptions import DomainError, InsufficientStockError
from core.domain.inventory import SALE, STOCK_IN, STOCK_OUT, signed_quantity
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
        cost_price=Decimal("22.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
        track_inventory=True,
        reorder_level=Decimal("20"),
    )


@pytest.fixture
def untracked(branch, category):
    return Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-COF-HOT",
        name="Hot Coffee",
        selling_price=Decimal("60.00"),
        unit=ProductUnit.SERVING,
        track_inventory=False,
    )


def test_signed_quantity_normalizes_in_and_out():
    assert signed_quantity(STOCK_IN, Decimal("-4")) == Decimal("4.000")
    assert signed_quantity(STOCK_OUT, Decimal("3")) == Decimal("-3.000")
    assert signed_quantity(SALE, Decimal("1")) == Decimal("-1.000")
    with pytest.raises(DomainError):
        signed_quantity(STOCK_IN, Decimal("0"))


@pytest.mark.django_db
def test_stock_in_updates_balance(product, branch):
    service = InventoryService()
    result = service.apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        reference_type="opening",
    )
    assert result.quantity == Decimal("10.000")
    assert result.balance_after == Decimal("10.000")
    assert service.get_on_hand(branch_id=branch.id, product_id=product.id) == Decimal("10.000")
    assert InventoryMovement.objects.filter(product=product).count() == 1


@pytest.mark.django_db
def test_oversell_is_rejected(product, branch):
    service = InventoryService()
    service.apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("1"),
    )
    with pytest.raises(InsufficientStockError):
        service.apply_movement(
            branch_id=branch.id,
            product_id=product.id,
            movement_type=SALE,
            quantity=Decimal("2"),
        )
    assert service.get_on_hand(branch_id=branch.id, product_id=product.id) == Decimal("1.000")
    assert InventoryMovement.objects.filter(product=product).count() == 1


@pytest.mark.django_db
def test_second_sale_fails_when_one_unit_remains(product, branch):
    service = InventoryService()
    service.apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("1"),
    )
    service.apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=SALE,
        quantity=Decimal("1"),
    )
    with pytest.raises(InsufficientStockError):
        service.apply_movement(
            branch_id=branch.id,
            product_id=product.id,
            movement_type=SALE,
            quantity=Decimal("1"),
        )
    assert service.get_on_hand(branch_id=branch.id, product_id=product.id) == Decimal("0.000")


@pytest.mark.django_db
def test_stock_count_writes_adjustment(product, branch):
    service = InventoryService()
    service.apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("8"),
    )
    result = service.set_counted_quantity(
        branch_id=branch.id,
        product_id=product.id,
        counted_quantity=Decimal("5"),
    )
    assert result.quantity == Decimal("-3.000")
    assert result.balance_after == Decimal("5.000")
    movement = InventoryMovement.objects.get(pk=result.movement_id)
    assert movement.movement_type == "adjustment"
    assert movement.reference_type == "count"


@pytest.mark.django_db
def test_untracked_product_cannot_move(untracked, branch):
    with pytest.raises(DomainError):
        InventoryService().apply_movement(
            branch_id=branch.id,
            product_id=untracked.id,
            movement_type=STOCK_IN,
            quantity=Decimal("1"),
        )


@pytest.mark.django_db
def test_movements_are_append_only(product, branch):
    result = InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("4"),
    )
    movement = InventoryMovement.objects.get(pk=result.movement_id)
    with pytest.raises(ValidationError):
        movement.notes = "changed"
        movement.save()
    with pytest.raises(ValidationError):
        movement.delete()


@pytest.mark.django_db
def test_stock_list_and_movement_modal(django_client, user, product, branch):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("12"),
    )
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("inventory:stock_list"))
    assert response.status_code == 200
    assert b"Sports Drink 500ml" in response.content
    assert b'aria-label="Count"' in response.content
    assert b"Record movement" in response.content

    partial = django_client.get(reverse("inventory:movement_create"), {"partial": "1"})
    assert partial.status_code == 200
    assert b"data-modal-form" in partial.content

    create = django_client.post(
        reverse("inventory:movement_create"),
        {
            "product": product.id,
            "movement_type": STOCK_OUT,
            "quantity": "2",
            "unit_cost": "22.00",
            "notes": "Damaged case",
        },
    )
    assert create.status_code == 302
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id) == Decimal("10.000")


@pytest.mark.django_db
def test_stock_count_form_posts(django_client, user, product, branch):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("6"),
    )
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.post(
        reverse("inventory:stock_count"),
        {"product": product.id, "counted_quantity": "9", "notes": "Shelf count"},
    )
    assert response.status_code == 302
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id) == Decimal("9.000")


@pytest.mark.django_db
def test_movement_list_is_ledger(django_client, user, product, branch):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("3"),
        notes="Opening",
    )
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("inventory:movement_list"))
    assert response.status_code == 200
    assert b"Sports Drink 500ml" in response.content
    assert b"Stock In" in response.content


@pytest.mark.django_db(transaction=True)
def test_concurrent_deduction_requires_postgres(product, branch):
    if connection.vendor != "postgresql":
        pytest.skip("SELECT FOR UPDATE concurrency requires PostgreSQL")

    from concurrent.futures import ThreadPoolExecutor

    service = InventoryService()
    service.apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("1"),
    )

    def deduct():
        try:
            InventoryService().apply_movement(
                branch_id=branch.id,
                product_id=product.id,
                movement_type=SALE,
                quantity=Decimal("1"),
            )
            return "ok"
        except InsufficientStockError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: deduct(), range(2)))

    assert results.count("ok") == 1
    assert results.count("rejected") == 1
    assert InventoryBalance.objects.get(product=product, branch=branch).quantity == Decimal("0.000")
