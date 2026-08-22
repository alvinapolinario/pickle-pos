from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.domain.purchasing import CANCELLED, DRAFT, ORDERED, PARTIAL, RECEIVED


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = DRAFT, "Draft"
    ORDERED = ORDERED, "Ordered"
    PARTIAL = PARTIAL, "Partial"
    RECEIVED = RECEIVED, "Received"
    CANCELLED = CANCELLED, "Cancelled"


class Supplier(models.Model):
    """Vendor that the branch buys inventory from."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="suppliers",
    )
    name = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="uniq_supplier_branch_name"),
        ]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class PurchaseOrder(models.Model):
    """Branch purchase order. Items are editable only while draft."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=40)
    status = models.CharField(
        max_length=20,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
    )
    expected_date = models.DateField(null=True, blank=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_purchase_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "po_number"], name="uniq_po_branch_number"),
        ]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["supplier", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.po_number

    @property
    def can_edit(self) -> bool:
        return self.status == PurchaseOrderStatus.DRAFT

    @property
    def can_receive(self) -> bool:
        return self.status in {PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.PARTIAL}

    @property
    def can_return(self) -> bool:
        return self.status in {
            PurchaseOrderStatus.PARTIAL,
            PurchaseOrderStatus.RECEIVED,
            PurchaseOrderStatus.ORDERED,
        }

    @property
    def can_cancel(self) -> bool:
        return self.status in {PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.ORDERED}


class PurchaseItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="purchase_items",
    )
    quantity_ordered = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["purchase_order", "product"], name="uniq_po_item_product"),
        ]

    def __str__(self) -> str:
        return f"{self.purchase_order_id} {self.product_id}"

    @property
    def quantity_outstanding(self) -> Decimal:
        return self.quantity_ordered - self.quantity_received

    @property
    def line_total(self) -> Decimal:
        return self.quantity_ordered * self.unit_cost


class PurchaseReceipt(models.Model):
    """Posted goods receipt. Stock-in movements are linked from line items."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="receipts",
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="purchase_receipts",
    )
    receipt_number = models.CharField(max_length=40)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_receipts",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "receipt_number"], name="uniq_grn_branch_number"),
        ]

    def __str__(self) -> str:
        return self.receipt_number


class PurchaseReceiptItem(models.Model):
    receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name="items")
    purchase_item = models.ForeignKey(PurchaseItem, on_delete=models.PROTECT, related_name="receipt_items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="receipt_items")
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    inventory_movement_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]


class PurchaseReturn(models.Model):
    """Return-to-supplier document. Stock-out movements are linked from line items."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="returns",
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="purchase_returns",
    )
    return_number = models.CharField(max_length=40)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_returns",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "return_number"], name="uniq_prn_branch_number"),
        ]

    def __str__(self) -> str:
        return self.return_number


class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name="items")
    purchase_item = models.ForeignKey(PurchaseItem, on_delete=models.PROTECT, related_name="return_items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="purchase_return_items")
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    inventory_movement_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
