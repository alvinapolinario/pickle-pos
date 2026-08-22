"""Atomic inventory ledger — append a movement and update the balance in one transaction."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import IntegrityError, transaction

from core.domain.exceptions import DomainError, InsufficientStockError, NotFoundError
from core.domain.inventory import ADJUSTMENT, QTY, signed_quantity


@dataclass(frozen=True)
class MovementResult:
    movement_id: int
    product_id: int
    branch_id: int
    quantity: Decimal
    balance_after: Decimal


class InventoryService:
    """Single write path for stock. Never update product.stock or balances directly."""

    def get_on_hand(self, *, branch_id: int, product_id: int) -> Decimal:
        from apps.inventory.models import InventoryBalance

        balance = InventoryBalance.objects.filter(branch_id=branch_id, product_id=product_id).first()
        return balance.quantity if balance else Decimal("0.000")

    def apply_movement(
        self,
        *,
        branch_id: int,
        product_id: int,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal = Decimal("0.00"),
        reference_type: str = "",
        reference_id: int | None = None,
        performed_by_id: int | None = None,
        notes: str = "",
        allow_negative_stock: bool = False,
    ) -> MovementResult:
        delta = signed_quantity(movement_type, quantity)
        unit_cost = Decimal(unit_cost or 0).quantize(Decimal("0.01"))

        with transaction.atomic():
            product = self._lock_product(product_id, branch_id)
            balance = self._lock_balance(branch_id, product_id)
            new_qty = (balance.quantity + delta).quantize(QTY)
            if new_qty < 0 and not allow_negative_stock:
                raise InsufficientStockError(
                    f"Insufficient stock for {product.name}. "
                    f"On hand {balance.quantity}, requested {abs(delta)}."
                )

            from apps.inventory.models import InventoryMovement

            movement = InventoryMovement.objects.create(
                branch_id=branch_id,
                product_id=product_id,
                movement_type=movement_type,
                quantity=delta,
                unit_cost=unit_cost,
                reference_type=reference_type,
                reference_id=reference_id,
                performed_by_id=performed_by_id,
                notes=notes,
            )
            balance.quantity = new_qty
            balance.save(update_fields=["quantity", "updated_at"])

            from apps.accounts.models import User
            from apps.audit.middleware import write_audit_log

            actor = User.objects.filter(pk=performed_by_id).first() if performed_by_id else None
            write_audit_log(
                action="inventory.movement",
                entity_type="inventory_movement",
                entity_id=str(movement.id),
                user=actor,
                new_values={
                    "product_id": product_id,
                    "branch_id": branch_id,
                    "movement_type": movement_type,
                    "quantity": str(delta),
                    "balance_after": str(new_qty),
                    "reference_type": reference_type,
                    "reference_id": reference_id,
                },
                reason=notes,
            )

        return MovementResult(
            movement_id=movement.id,
            product_id=product_id,
            branch_id=branch_id,
            quantity=delta,
            balance_after=new_qty,
        )

    def set_counted_quantity(
        self,
        *,
        branch_id: int,
        product_id: int,
        counted_quantity: Decimal,
        performed_by_id: int | None = None,
        notes: str = "",
        allow_negative_stock: bool = False,
    ) -> MovementResult:
        counted = Decimal(counted_quantity).quantize(QTY)
        if counted < 0:
            raise DomainError("Counted quantity cannot be negative.")
        current = self.get_on_hand(branch_id=branch_id, product_id=product_id)
        delta = (counted - current).quantize(QTY)
        if delta == 0:
            raise DomainError("Counted quantity matches on-hand stock.")
        return self.apply_movement(
            branch_id=branch_id,
            product_id=product_id,
            movement_type=ADJUSTMENT,
            quantity=delta,
            reference_type="count",
            performed_by_id=performed_by_id,
            notes=notes or f"Stock count set to {counted}",
            allow_negative_stock=allow_negative_stock,
        )

    def _lock_product(self, product_id: int, branch_id: int):
        from apps.products.models import Product

        product = Product.objects.select_for_update().filter(pk=product_id).first()
        if product is None:
            raise NotFoundError("Product not found.")
        if product.branch_id != branch_id:
            raise DomainError("Product does not belong to this branch.")
        if not product.track_inventory:
            raise DomainError("This product does not track inventory.")
        return product

    def _lock_balance(self, branch_id: int, product_id: int):
        from apps.inventory.models import InventoryBalance

        locked = InventoryBalance.objects.select_for_update().filter(
            branch_id=branch_id,
            product_id=product_id,
        ).first()
        if locked:
            return locked
        try:
            with transaction.atomic():
                InventoryBalance.objects.create(
                    branch_id=branch_id,
                    product_id=product_id,
                    quantity=Decimal("0.000"),
                )
        except IntegrityError:
            pass
        return InventoryBalance.objects.select_for_update().get(
            branch_id=branch_id,
            product_id=product_id,
        )
