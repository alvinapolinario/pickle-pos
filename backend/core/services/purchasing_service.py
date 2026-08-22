"""Purchase orders, receiving, and supplier returns — writes stock only through InventoryService."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.domain.exceptions import DomainError, NotFoundError
from core.domain.inventory import STOCK_IN, STOCK_OUT, QTY
from core.domain.purchasing import CANCELLED, DRAFT, ORDERED, PARTIAL, RECEIVED, RECEIVABLE_STATUSES
from core.services.inventory_service import InventoryService

MONEY = Decimal("0.01")


@dataclass(frozen=True)
class PurchaseLine:
    product_id: int
    quantity_ordered: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class ReceiveLine:
    purchase_item_id: int
    quantity: Decimal
    unit_cost: Decimal | None = None


class PurchasingService:
    def create_order(
        self,
        *,
        branch_id: int,
        supplier_id: int,
        created_by_id: int | None,
        items: list[PurchaseLine],
        expected_date: date | None = None,
        notes: str = "",
        submit: bool = False,
    ):
        with transaction.atomic():
            po = self._new_order(
                branch_id=branch_id,
                supplier_id=supplier_id,
                created_by_id=created_by_id,
                expected_date=expected_date,
                notes=notes,
            )
            self._replace_items(po, items)
            if submit:
                self._submit_locked(po)
            return po

    def update_draft(
        self,
        *,
        po_id: int,
        supplier_id: int,
        items: list[PurchaseLine],
        expected_date: date | None = None,
        notes: str = "",
        submit: bool = False,
    ):
        with transaction.atomic():
            po = self._lock_order(po_id)
            if po.status != DRAFT:
                raise DomainError("Only draft purchase orders can be edited.")
            self._assert_supplier(supplier_id, po.branch_id)
            po.supplier_id = supplier_id
            po.expected_date = expected_date
            po.notes = notes
            po.save(update_fields=["supplier", "expected_date", "notes", "updated_at"])
            self._replace_items(po, items)
            if submit:
                self._submit_locked(po)
            return po

    def submit_order(self, *, po_id: int):
        with transaction.atomic():
            po = self._lock_order(po_id)
            self._submit_locked(po)
            return po

    def cancel_order(self, *, po_id: int):
        with transaction.atomic():
            po = self._lock_order(po_id)
            if po.status == CANCELLED:
                raise DomainError("Purchase order is already cancelled.")
            if po.status not in {DRAFT, ORDERED}:
                raise DomainError("Only draft or unreceived purchase orders can be cancelled.")
            if po.status == ORDERED and po.items.filter(quantity_received__gt=0).exists():
                raise DomainError("Cannot cancel a purchase order that already has receipts.")
            po.status = CANCELLED
            po.save(update_fields=["status", "updated_at"])
            self._audit("purchasing.cancel", po, {"status": CANCELLED})
            return po

    def receive(
        self,
        *,
        po_id: int,
        lines: list[ReceiveLine],
        received_by_id: int | None,
        notes: str = "",
    ):
        from apps.purchasing.models import PurchaseItem, PurchaseReceipt, PurchaseReceiptItem

        with transaction.atomic():
            po = self._lock_order(po_id)
            if po.status not in RECEIVABLE_STATUSES:
                raise DomainError("Only ordered purchase orders can be received.")

            receipt = PurchaseReceipt(
                purchase_order=po,
                branch_id=po.branch_id,
                received_by_id=received_by_id,
                notes=notes,
            )
            receipt.receipt_number = self._next_number(
                PurchaseReceipt, po.branch_id, "receipt_number", "GRN"
            )
            receipt.save()

            inventory = InventoryService()
            posted = 0
            for line in lines:
                qty = Decimal(line.quantity).quantize(QTY)
                if qty <= 0:
                    continue
                item = PurchaseItem.objects.select_for_update().select_related("product").get(
                    pk=line.purchase_item_id,
                    purchase_order=po,
                )
                outstanding = (item.quantity_ordered - item.quantity_received).quantize(QTY)
                if qty > outstanding:
                    raise DomainError(
                        f"Cannot receive {qty} of {item.product.name}; {outstanding} outstanding."
                    )
                unit_cost = Decimal(line.unit_cost if line.unit_cost is not None else item.unit_cost).quantize(MONEY)
                movement = inventory.apply_movement(
                    branch_id=po.branch_id,
                    product_id=item.product_id,
                    movement_type=STOCK_IN,
                    quantity=qty,
                    unit_cost=unit_cost,
                    reference_type="purchase_receipt",
                    reference_id=receipt.id,
                    performed_by_id=received_by_id,
                    notes=notes or f"Received {po.po_number}",
                )
                PurchaseReceiptItem.objects.create(
                    receipt=receipt,
                    purchase_item=item,
                    product_id=item.product_id,
                    quantity=qty,
                    unit_cost=unit_cost,
                    inventory_movement_id=movement.movement_id,
                )
                item.quantity_received = (item.quantity_received + qty).quantize(QTY)
                item.save(update_fields=["quantity_received"])
                posted += 1

            if posted == 0:
                raise DomainError("Enter a quantity to receive.")

            self._refresh_status(po)
            self._audit(
                "purchasing.receive",
                po,
                {"receipt": receipt.receipt_number, "status": po.status},
            )
            return receipt

    def return_to_supplier(
        self,
        *,
        po_id: int,
        lines: list[ReceiveLine],
        returned_by_id: int | None,
        notes: str = "",
    ):
        from apps.purchasing.models import PurchaseItem, PurchaseReturn, PurchaseReturnItem

        with transaction.atomic():
            po = self._lock_order(po_id)
            if po.status in {DRAFT, CANCELLED}:
                raise DomainError("This purchase order cannot be returned.")

            ret = PurchaseReturn(
                purchase_order=po,
                branch_id=po.branch_id,
                returned_by_id=returned_by_id,
                notes=notes,
            )
            ret.return_number = self._next_number(PurchaseReturn, po.branch_id, "return_number", "PRN")
            ret.save()

            inventory = InventoryService()
            posted = 0
            for line in lines:
                qty = Decimal(line.quantity).quantize(QTY)
                if qty <= 0:
                    continue
                item = PurchaseItem.objects.select_for_update().select_related("product").get(
                    pk=line.purchase_item_id,
                    purchase_order=po,
                )
                if qty > item.quantity_received:
                    raise DomainError(
                        f"Cannot return {qty} of {item.product.name}; "
                        f"{item.quantity_received} received remains."
                    )
                unit_cost = Decimal(line.unit_cost if line.unit_cost is not None else item.unit_cost).quantize(MONEY)
                movement = inventory.apply_movement(
                    branch_id=po.branch_id,
                    product_id=item.product_id,
                    movement_type=STOCK_OUT,
                    quantity=qty,
                    unit_cost=unit_cost,
                    reference_type="purchase_return",
                    reference_id=ret.id,
                    performed_by_id=returned_by_id,
                    notes=notes or f"Return {po.po_number}",
                )
                PurchaseReturnItem.objects.create(
                    purchase_return=ret,
                    purchase_item=item,
                    product_id=item.product_id,
                    quantity=qty,
                    unit_cost=unit_cost,
                    inventory_movement_id=movement.movement_id,
                )
                item.quantity_received = (item.quantity_received - qty).quantize(QTY)
                item.save(update_fields=["quantity_received"])
                posted += 1

            if posted == 0:
                raise DomainError("Enter a quantity to return.")

            self._refresh_status(po)
            self._audit(
                "purchasing.return",
                po,
                {"return": ret.return_number, "status": po.status},
            )
            return ret

    def _new_order(self, *, branch_id, supplier_id, created_by_id, expected_date, notes):
        from apps.purchasing.models import PurchaseOrder

        self._assert_supplier(supplier_id, branch_id)
        po = PurchaseOrder(
            branch_id=branch_id,
            supplier_id=supplier_id,
            expected_date=expected_date,
            notes=notes,
            created_by_id=created_by_id,
            status=DRAFT,
        )
        po.po_number = self._next_number(PurchaseOrder, branch_id, "po_number", "PO")
        try:
            po.save()
        except IntegrityError as exc:
            raise DomainError("Could not allocate a purchase order number. Try again.") from exc
        return po

    def _replace_items(self, po, items: list[PurchaseLine]):
        from apps.products.models import Product
        from apps.purchasing.models import PurchaseItem

        cleaned: list[PurchaseLine] = []
        seen: set[int] = set()
        for line in items:
            qty = Decimal(line.quantity_ordered).quantize(QTY)
            cost = Decimal(line.unit_cost).quantize(MONEY)
            if qty <= 0:
                continue
            if line.product_id in seen:
                raise DomainError("Each product can appear only once on a purchase order.")
            seen.add(line.product_id)
            product = Product.objects.filter(pk=line.product_id, branch_id=po.branch_id).first()
            if product is None:
                raise NotFoundError("Product not found for this branch.")
            if not product.track_inventory:
                raise DomainError(f"{product.name} does not track inventory.")
            if not product.is_active:
                raise DomainError(f"{product.name} is inactive.")
            cleaned.append(PurchaseLine(product.id, qty, cost))

        if not cleaned:
            raise DomainError("Add at least one purchase item.")

        po.items.all().delete()
        PurchaseItem.objects.bulk_create(
            [
                PurchaseItem(
                    purchase_order=po,
                    product_id=line.product_id,
                    quantity_ordered=line.quantity_ordered,
                    unit_cost=line.unit_cost,
                )
                for line in cleaned
            ]
        )

    def _submit_locked(self, po):
        if po.status != DRAFT:
            raise DomainError("Only draft purchase orders can be submitted.")
        if not po.items.exists():
            raise DomainError("Add at least one purchase item before submitting.")
        po.status = ORDERED
        po.ordered_at = timezone.now()
        po.save(update_fields=["status", "ordered_at", "updated_at"])
        self._audit("purchasing.submit", po, {"status": ORDERED})

    def _refresh_status(self, po):
        items = list(po.items.all())
        if not items:
            status = ORDERED
        elif all(item.quantity_received <= 0 for item in items):
            status = ORDERED
        elif all(item.quantity_received >= item.quantity_ordered for item in items):
            status = RECEIVED
        else:
            status = PARTIAL
        if po.status != status:
            po.status = status
            po.save(update_fields=["status", "updated_at"])

    def _lock_order(self, po_id: int):
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.select_for_update().select_related("supplier", "branch").filter(pk=po_id).first()
        if po is None:
            raise NotFoundError("Purchase order not found.")
        return po

    def _assert_supplier(self, supplier_id: int, branch_id: int):
        from apps.purchasing.models import Supplier

        supplier = Supplier.objects.filter(pk=supplier_id, branch_id=branch_id).first()
        if supplier is None:
            raise NotFoundError("Supplier not found for this branch.")
        if not supplier.is_active:
            raise DomainError("Supplier is inactive.")
        return supplier

    def _next_number(self, model, branch_id: int, field: str, prefix: str) -> str:
        stem = f"{prefix}-{timezone.localdate().strftime('%Y%m%d')}-"
        last = (
            model.objects.select_for_update()
            .filter(branch_id=branch_id, **{f"{field}__startswith": stem})
            .order_by(f"-{field}")
            .values_list(field, flat=True)
            .first()
        )
        seq = int(last.rsplit("-", 1)[-1]) + 1 if last else 1
        return f"{stem}{seq:04d}"

    def _audit(self, action: str, po, extra: dict):
        from apps.audit.middleware import write_audit_log

        write_audit_log(
            action=action,
            entity_type="purchase_order",
            entity_id=str(po.id),
            new_values={"po_number": po.po_number, **extra},
        )
