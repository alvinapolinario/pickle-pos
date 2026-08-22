from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse

from apps.inventory.models import InventoryMovement
from apps.products.models import Category, Product, ProductUnit
from apps.purchasing.models import PurchaseOrder, PurchaseReceipt, Supplier
from core.domain.exceptions import DomainError
from core.domain.inventory import STOCK_IN, STOCK_OUT
from core.services.inventory_service import InventoryService
from core.services.purchasing_service import PurchaseLine, PurchasingService, ReceiveLine


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
        track_inventory=True,
        reorder_level=Decimal("20"),
    )


@pytest.fixture
def water(branch, category):
    return Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-WTR-500",
        name="Bottled Water 500ml",
        selling_price=Decimal("25.00"),
        cost_price=Decimal("10.00"),
        unit=ProductUnit.BOTTLE,
        track_inventory=True,
    )


@pytest.fixture
def supplier(branch):
    return Supplier.objects.create(branch=branch, name="Metro Beverage Dist.", contact_name="Ana Cruz")


def _ordered_po(branch, supplier, product, qty=Decimal("10"), cost=None, user=None):
    return PurchasingService().create_order(
        branch_id=branch.id,
        supplier_id=supplier.id,
        created_by_id=getattr(user, "id", None),
        items=[PurchaseLine(product.id, qty, cost if cost is not None else product.cost_price)],
        submit=True,
    )


@pytest.mark.django_db
def test_supplier_unique_per_branch(branch, supplier):
    with pytest.raises(IntegrityError):
        Supplier.objects.create(branch=branch, name="Metro Beverage Dist.")


@pytest.mark.django_db
def test_create_submit_and_cannot_edit_items(branch, supplier, product):
    service = PurchasingService()
    po = service.create_order(
        branch_id=branch.id,
        supplier_id=supplier.id,
        created_by_id=None,
        items=[PurchaseLine(product.id, Decimal("5"), Decimal("22.00"))],
    )
    assert po.status == "draft"
    assert po.items.count() == 1
    service.submit_order(po_id=po.id)
    po.refresh_from_db()
    assert po.status == "ordered"
    with pytest.raises(DomainError):
        service.update_draft(
            po_id=po.id,
            supplier_id=supplier.id,
            items=[PurchaseLine(product.id, Decimal("8"), Decimal("22.00"))],
        )


@pytest.mark.django_db
def test_cannot_receive_draft(branch, supplier, product):
    po = PurchasingService().create_order(
        branch_id=branch.id,
        supplier_id=supplier.id,
        created_by_id=None,
        items=[PurchaseLine(product.id, Decimal("5"), Decimal("22.00"))],
    )
    with pytest.raises(DomainError):
        PurchasingService().receive(
            po_id=po.id,
            lines=[ReceiveLine(po.items.get().id, Decimal("1"))],
            received_by_id=None,
        )


@pytest.mark.django_db
def test_receive_posts_stock_in(branch, supplier, product):
    po = _ordered_po(branch, supplier, product, Decimal("10"))
    item = po.items.get()
    before = InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id)
    receipt = PurchasingService().receive(
        po_id=po.id,
        lines=[ReceiveLine(item.id, Decimal("4"), Decimal("22.00"))],
        received_by_id=None,
        notes="Partial delivery",
    )
    po.refresh_from_db()
    item.refresh_from_db()
    assert receipt.receipt_number.startswith("GRN-")
    assert po.status == "partial"
    assert item.quantity_received == Decimal("4.000")
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id) == before + Decimal("4.000")
    movement = InventoryMovement.objects.get(pk=receipt.items.get().inventory_movement_id)
    assert movement.movement_type == STOCK_IN
    assert movement.reference_type == "purchase_receipt"


@pytest.mark.django_db
def test_cannot_over_receive(branch, supplier, product):
    po = _ordered_po(branch, supplier, product, Decimal("3"))
    with pytest.raises(DomainError):
        PurchasingService().receive(
            po_id=po.id,
            lines=[ReceiveLine(po.items.get().id, Decimal("4"))],
            received_by_id=None,
        )


@pytest.mark.django_db
def test_full_receive_marks_received(branch, supplier, product):
    po = _ordered_po(branch, supplier, product, Decimal("6"))
    PurchasingService().receive(
        po_id=po.id,
        lines=[ReceiveLine(po.items.get().id, Decimal("6"))],
        received_by_id=None,
    )
    po.refresh_from_db()
    assert po.status == "received"


@pytest.mark.django_db
def test_return_to_supplier_posts_stock_out(branch, supplier, product):
    po = _ordered_po(branch, supplier, product, Decimal("8"))
    item = po.items.get()
    PurchasingService().receive(
        po_id=po.id,
        lines=[ReceiveLine(item.id, Decimal("8"))],
        received_by_id=None,
    )
    before = InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id)
    ret = PurchasingService().return_to_supplier(
        po_id=po.id,
        lines=[ReceiveLine(item.id, Decimal("2"))],
        returned_by_id=None,
    )
    po.refresh_from_db()
    item.refresh_from_db()
    assert ret.return_number.startswith("PRN-")
    assert po.status == "partial"
    assert item.quantity_received == Decimal("6.000")
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id) == before - Decimal("2.000")
    movement = InventoryMovement.objects.get(pk=ret.items.get().inventory_movement_id)
    assert movement.movement_type == STOCK_OUT
    assert movement.reference_type == "purchase_return"


@pytest.mark.django_db
def test_cannot_return_more_than_received(branch, supplier, product):
    po = _ordered_po(branch, supplier, product, Decimal("5"))
    PurchasingService().receive(
        po_id=po.id,
        lines=[ReceiveLine(po.items.get().id, Decimal("2"))],
        received_by_id=None,
    )
    with pytest.raises(DomainError):
        PurchasingService().return_to_supplier(
            po_id=po.id,
            lines=[ReceiveLine(po.items.get().id, Decimal("3"))],
            returned_by_id=None,
        )


@pytest.mark.django_db
def test_cancel_draft_and_block_after_receive(branch, supplier, product):
    service = PurchasingService()
    draft = service.create_order(
        branch_id=branch.id,
        supplier_id=supplier.id,
        created_by_id=None,
        items=[PurchaseLine(product.id, Decimal("1"), Decimal("10.00"))],
    )
    service.cancel_order(po_id=draft.id)
    draft.refresh_from_db()
    assert draft.status == "cancelled"

    po = _ordered_po(branch, supplier, product, Decimal("2"))
    service.receive(po_id=po.id, lines=[ReceiveLine(po.items.get().id, Decimal("1"))], received_by_id=None)
    with pytest.raises(DomainError):
        service.cancel_order(po_id=po.id)


@pytest.mark.django_db
def test_supplier_list_and_create(django_client, user, branch):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.post(
        reverse("purchasing:supplier_create"),
        {
            "branch": branch.id,
            "name": "Court Gear Inc.",
            "contact_name": "Rico",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    listing = django_client.get(reverse("purchasing:supplier_list"))
    assert listing.status_code == 200
    assert b"Court Gear Inc." in listing.content
    assert b'aria-label="Edit"' in listing.content


@pytest.mark.django_db
def test_po_and_receive_from_console(django_client, user, branch, supplier, product):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    create = django_client.post(
        reverse("purchasing:purchase_order_create"),
        {
            "supplier": supplier.id,
            "notes": "Restock drinks",
            "intent": "submit",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-product": str(product.id),
            "items-0-quantity_ordered": "12",
            "items-0-unit_cost": "22.00",
        },
    )
    assert create.status_code == 302
    po = PurchaseOrder.objects.get(supplier=supplier)
    assert po.status == "ordered"
    listing = django_client.get(reverse("purchasing:purchase_order_list"))
    assert po.po_number.encode() in listing.content
    assert b'aria-label="Receive"' in listing.content

    before = InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id)
    receive = django_client.post(
        reverse("purchasing:purchase_order_receive", args=[po.pk]),
        {
            "purchase_order": po.id,
            "notes": "Truck 1",
            "lines-TOTAL_FORMS": "1",
            "lines-INITIAL_FORMS": "1",
            "lines-MIN_NUM_FORMS": "0",
            "lines-MAX_NUM_FORMS": "1000",
            "lines-0-purchase_item_id": str(po.items.get().id),
            "lines-0-quantity": "5",
            "lines-0-unit_cost": "22.00",
        },
    )
    assert receive.status_code == 302
    assert PurchaseReceipt.objects.filter(purchase_order=po).exists()
    assert InventoryService().get_on_hand(branch_id=branch.id, product_id=product.id) == before + Decimal("5.000")

    receiving = django_client.get(reverse("purchasing:receiving_list"))
    assert receiving.status_code == 200
    assert b"GRN-" in receiving.content
