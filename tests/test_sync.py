from decimal import Decimal
from uuid import uuid4

import pytest

from apps.accounts.models import Device
from apps.products.models import Category, Product, ProductUnit
from apps.sync.models import SyncTransaction
from core.domain.inventory import STOCK_IN
from core.services.inventory_service import InventoryService
from core.services.sale_service import SaleLineInput, PaymentInput
from core.services.shift_service import ShiftService
from core.services.sync_service import SyncSaleInput, SyncService


@pytest.fixture
def product(branch):
    category = Category.objects.create(branch=branch, name="Drinks")
    item = Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-SD-500",
        name="Sports Drink 500ml",
        selling_price=Decimal("45.00"),
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
def test_sync_push_is_idempotent(branch, user, product):
    device = Device.objects.create(device_code="POS-001", name="Counter 1", branch=branch)
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100"))
    uuid = uuid4()
    payload = SyncSaleInput(
        client_sale_uuid=uuid,
        shift_id=shift.id,
        items=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("45.00"))],
    )
    first = SyncService().push_sales(cashier_id=user.id, device_id=device.id, sales=[payload])
    second = SyncService().push_sales(cashier_id=user.id, device_id=device.id, sales=[payload])
    assert first[0].status == "synced"
    assert second[0].status == "synced"
    assert first[0].sale_id == second[0].sale_id
    assert SyncTransaction.objects.filter(device=device, client_uuid=uuid).count() == 1


@pytest.mark.django_db
def test_sync_pull_returns_catalog(branch, product):
    payload = SyncService().pull(branch_id=branch.id)
    assert payload["products"][0]["sku"] == "BEV-SD-500"
    assert "cash" in payload["payment_methods"]
    assert payload["tax"]["inclusive"] is True
