from decimal import Decimal

import pytest

from apps.products.models import Category, Product, ProductUnit
from core.domain.inventory import STOCK_IN
from core.services.inventory_service import InventoryService
from core.services.receipt_service import ReceiptService
from core.services.sale_service import PaymentInput, SaleLineInput, SaleService
from core.services.shift_service import ShiftService


@pytest.mark.django_db
def test_receipt_includes_totals_and_branch(branch, user):
    category = Category.objects.create(branch=branch, name="Drinks")
    product = Product.objects.create(
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
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("5"),
        reference_type="opening",
    )
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("50"))
    sale = SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("50.00"))],
    )
    receipt = ReceiptService().build(sale)
    assert receipt.net_amount == Decimal("45.00")
    assert "TOTAL" in receipt.text
    assert branch.name in receipt.text
    assert sale.receipt_number in receipt.text
    assert "VAT" in receipt.text
    assert "PICKLEBALL POS" not in receipt.text


@pytest.mark.django_db
def test_receipt_uses_store_name_and_address_from_settings(branch, user):
    branch.receipt_store_name = "Pickleball West"
    branch.receipt_address = "123 Court Lane, Pasig City"
    branch.save(update_fields=["receipt_store_name", "receipt_address"])
    category = Category.objects.create(branch=branch, name="Drinks")
    product = Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-CUSTOM",
        name="Water",
        selling_price=Decimal("25.00"),
        unit=ProductUnit.BOTTLE,
        track_inventory=False,
    )
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("50"))
    sale = SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("25.00"))],
    )
    receipt = ReceiptService().build(sale)
    assert receipt.branch_name == "Pickleball West"
    assert receipt.branch_address == "123 Court Lane, Pasig City"
    assert "Pickleball West" in receipt.text
    assert "123 Court Lane" in receipt.text
    assert "Main Branch" not in receipt.text


@pytest.mark.django_db
def test_receipt_omits_vat_when_not_registered(branch, user):
    branch.vat_registered = False
    branch.save(update_fields=["vat_registered"])
    category = Category.objects.create(branch=branch, name="Drinks")
    product = Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-NVAT",
        name="Water",
        selling_price=Decimal("25.00"),
        unit=ProductUnit.BOTTLE,
        track_inventory=False,
    )
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("50"))
    sale = SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("25.00"))],
    )
    receipt = ReceiptService().build(sale)
    assert receipt.vat_registered is False
    assert receipt.tax_amount == Decimal("0.00")
    assert "VAT" not in receipt.text
    assert "Prices include VAT" not in receipt.text
