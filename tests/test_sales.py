from decimal import Decimal
from uuid import uuid4

import pytest

from apps.inventory.models import InventoryMovement
from apps.products.models import Category, Product, ProductUnit, TaxStatus
from apps.sales.models import Sale
from core.domain.exceptions import DomainError, InsufficientStockError, NotFoundError
from core.domain.inventory import RETURN, SALE, STOCK_IN
from core.services.inventory_service import InventoryService
from core.services.sale_service import PaymentInput, RefundLineInput, SaleLineInput, SaleService
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


@pytest.fixture
def stocked(product, branch):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        unit_cost=product.cost_price,
        reference_type="opening",
    )
    return product


@pytest.fixture
def open_shift(branch, user):
    return ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("200.00"))


def _cash_sale(shift, user, product, qty=Decimal("1"), payments=None, **kwargs):
    return SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, qty)],
        payments=payments or [PaymentInput("cash", Decimal("10000.00"))],
        **kwargs,
    )


@pytest.mark.django_db
def test_sale_recalculates_totals_and_deducts_stock(open_shift, user, stocked, branch):
    sale = _cash_sale(open_shift, user, stocked, qty=Decimal("2"))
    assert sale.status == Sale.Status.COMPLETED
    assert sale.net_amount == Decimal("90.00")
    assert sale.tax_amount == Decimal("9.64")
    assert sale.change_amount == Decimal("9910.00")
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("8.000")
    assert InventoryMovement.objects.filter(movement_type=SALE, product=stocked).count() == 1


@pytest.mark.django_db
def test_insufficient_stock_rolls_back(open_shift, user, stocked, branch):
    with pytest.raises(InsufficientStockError):
        _cash_sale(open_shift, user, stocked, qty=Decimal("99"))
    assert Sale.objects.count() == 0
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("10.000")


@pytest.mark.django_db
def test_sale_uuid_is_idempotent(open_shift, user, stocked, branch):
    uuid = uuid4()
    first = _cash_sale(open_shift, user, stocked, client_sale_uuid=uuid)
    second = _cash_sale(open_shift, user, stocked, client_sale_uuid=uuid)
    assert first.id == second.id
    assert Sale.objects.count() == 1
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("9.000")


@pytest.mark.django_db
def test_cannot_sell_without_open_shift(user, stocked):
    with pytest.raises(NotFoundError):
        SaleService().create_sale(
            shift_id=99999,
            cashier_id=user.id,
            lines=[SaleLineInput(stocked.id, Decimal("1"))],
            payments=[PaymentInput("cash", Decimal("45.00"))],
        )


@pytest.mark.django_db
def test_payments_must_cover_net(open_shift, user, stocked):
    with pytest.raises(DomainError, match="does not cover"):
        _cash_sale(open_shift, user, stocked, payments=[PaymentInput("cash", Decimal("1.00"))])


@pytest.mark.django_db
def test_void_restocks(open_shift, user, stocked, branch):
    sale = _cash_sale(open_shift, user, stocked, qty=Decimal("3"))
    SaleService().void_sale(sale_id=sale.id, cashier_id=user.id, reason="Wrong item")
    sale.refresh_from_db()
    assert sale.status == Sale.Status.VOID
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("10.000")
    assert InventoryMovement.objects.filter(movement_type=RETURN, reference_type="sale_void").count() == 1


@pytest.mark.django_db
def test_refund_restocks(open_shift, user, stocked, branch):
    sale = _cash_sale(open_shift, user, stocked, qty=Decimal("2"))
    item = sale.items.get()
    refund = SaleService().refund_sale(
        sale_id=sale.id,
        shift_id=open_shift.id,
        cashier_id=user.id,
        lines=[RefundLineInput(item.id, Decimal("1"))],
        method="cash",
        reason="Customer return",
    )
    assert refund.amount == Decimal("45.00")
    item.refresh_from_db()
    assert item.quantity_refunded == Decimal("1.000")
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("9.000")


@pytest.mark.django_db
def test_hold_does_not_deduct_until_resume(open_shift, user, stocked, branch):
    held = SaleService().create_sale(
        shift_id=open_shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(stocked.id, Decimal("1"))],
        payments=[],
        hold=True,
    )
    assert held.status == Sale.Status.HELD
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("10.000")
    completed = SaleService().resume_sale(
        sale_id=held.id,
        cashier_id=user.id,
        payments=[PaymentInput("gcash", Decimal("45.00"))],
    )
    assert completed.status == Sale.Status.COMPLETED
    assert completed.change_amount == Decimal("0.00")
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("9.000")


@pytest.mark.django_db
def test_resume_applies_edited_held_items(open_shift, user, stocked, branch):
    held = SaleService().create_sale(
        shift_id=open_shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(stocked.id, Decimal("1"))],
        payments=[],
        hold=True,
    )
    completed = SaleService().resume_sale(
        sale_id=held.id,
        cashier_id=user.id,
        lines=[SaleLineInput(stocked.id, Decimal("2"))],
        payments=[PaymentInput("gcash", Decimal("90.00"))],
    )
    completed.refresh_from_db()
    assert completed.net_amount == Decimal("90.00")
    assert completed.items.get().quantity == Decimal("2.000")
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("8.000")


@pytest.mark.django_db
def test_void_after_original_shift_closed(open_shift, user, stocked, branch):
    sale = _cash_sale(open_shift, user, stocked, qty=Decimal("2"))
    ShiftService().close_shift(shift_id=open_shift.id, actual_cash=Decimal("290.00"))
    with pytest.raises(DomainError, match="Open a shift"):
        SaleService().void_sale(sale_id=sale.id, cashier_id=user.id, reason="After close")
    ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("200.00"))
    SaleService().void_sale(sale_id=sale.id, cashier_id=user.id, reason="After close")
    sale.refresh_from_db()
    assert sale.status == Sale.Status.VOID
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("10.000")


@pytest.mark.django_db
def test_void_from_another_cashiers_open_shift(open_shift, user, stocked, branch, cashier_role):
    from django.contrib.auth import get_user_model

    sale = _cash_sale(open_shift, user, stocked, qty=Decimal("1"))
    supervisor = get_user_model().objects.create_user(
        username="supervisor1",
        password="secure-pass-123",
        email="supervisor1@example.com",
        branch=branch,
    )
    supervisor.roles.add(cashier_role)
    ShiftService().open_shift(cashier_id=supervisor.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    SaleService().void_sale(sale_id=sale.id, cashier_id=supervisor.id, reason="Supervisor override")
    sale.refresh_from_db()
    assert sale.status == Sale.Status.VOID
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=stocked.id) == Decimal("10.000")
