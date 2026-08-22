import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Sale(models.Model):
    class Status(models.TextChoices):
        HELD = "held", "Held"
        COMPLETED = "completed", "Completed"
        VOID = "void", "Void"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIAL = "partial", "Partial"
        PAID = "paid", "Paid"

    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="sales")
    shift = models.ForeignKey("shifts.CashierShift", on_delete=models.PROTECT, related_name="sales")
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
    )
    device = models.ForeignKey(
        "accounts.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    transaction_number = models.CharField(max_length=50)
    receipt_number = models.CharField(max_length=50, blank=True)
    client_sale_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    change_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    notes = models.TextField(blank=True)
    void_reason = models.CharField(max_length=200, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "transaction_number"], name="uniq_sale_txn_branch"),
            models.UniqueConstraint(
                fields=["branch", "receipt_number"],
                condition=~models.Q(receipt_number=""),
                name="uniq_sale_receipt_branch",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["shift", "status"]),
        ]

    def __str__(self) -> str:
        return self.transaction_number


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="sale_items")
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_gross = models.DecimalField(max_digits=14, decimal_places=2)
    line_discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_net = models.DecimalField(max_digits=14, decimal_places=2)
    quantity_refunded = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    inventory_movement_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    @property
    def quantity_refundable(self) -> Decimal:
        return self.quantity - self.quantity_refunded


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        GCASH = "gcash", "GCash"
        MAYA = "maya", "Maya"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        OTHER = "other", "Other"

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    reference = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class HeldOrder(models.Model):
    """Pointer to a sale parked as held until resume."""

    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name="hold")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="held_orders")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Refund(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="refunds")
    shift = models.ForeignKey("shifts.CashierShift", on_delete=models.PROTECT, related_name="refunds")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="refunds")
    refund_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=Payment.Method.choices, default=Payment.Method.CASH)
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refunds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "refund_number"], name="uniq_refund_branch_number"),
        ]

    def __str__(self) -> str:
        return self.refund_number


class RefundItem(models.Model):
    refund = models.ForeignKey(Refund, on_delete=models.CASCADE, related_name="items")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name="refund_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    inventory_movement_id = models.BigIntegerField(null=True, blank=True)
