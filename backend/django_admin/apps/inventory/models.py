from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.domain.inventory import ADJUSTMENT, EXPIRED, RETURN, SALE, STOCK_IN, STOCK_OUT, TRANSFER, WASTAGE


class MovementType(models.TextChoices):
    STOCK_IN = STOCK_IN, "Stock In"
    STOCK_OUT = STOCK_OUT, "Stock Out"
    ADJUSTMENT = ADJUSTMENT, "Adjustment"
    TRANSFER = TRANSFER, "Transfer"
    SALE = SALE, "Sale"
    RETURN = RETURN, "Return"
    WASTAGE = WASTAGE, "Wastage"
    EXPIRED = EXPIRED, "Expired"


class InventoryMovement(models.Model):
    """Append-only stock ledger. Quantity is signed (negative = out)."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.BigIntegerField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "branch"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(quantity=0), name="movement_qty_nonzero"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Inventory movements are append-only and cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Inventory movements are append-only and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} {self.quantity} {self.product_id}"


class InventoryBalance(models.Model):
    """Materialized on-hand quantity per branch and product."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="inventory_balances",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="inventory_balances",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "product"], name="uniq_inventory_balance_branch_product"),
        ]
        indexes = [
            models.Index(fields=["branch", "quantity"]),
        ]

    def __str__(self) -> str:
        return f"{self.branch_id}:{self.product_id} = {self.quantity}"
