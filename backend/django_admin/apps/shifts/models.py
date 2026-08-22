from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.domain.shifts import CASH_IN, CASH_OUT, CLOSED, OPEN


class ShiftStatus(models.TextChoices):
    OPEN = OPEN, "Open"
    CLOSED = CLOSED, "Closed"


class CashTransactionType(models.TextChoices):
    CASH_IN = CASH_IN, "Cash In"
    CASH_OUT = CASH_OUT, "Cash Out"


class CashierShift(models.Model):
    """One open shift per cashier. Expected cash is computed at close."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="cashier_shifts",
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cashier_shifts",
    )
    status = models.CharField(max_length=20, choices=ShiftStatus.choices, default=ShiftStatus.OPEN)
    opening_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    expected_cash = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    actual_cash = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    over_short = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cashier"],
                condition=models.Q(status="open"),
                name="uniq_open_shift_per_cashier",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["cashier", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.cashier_id} {self.status} {self.opened_at:%Y-%m-%d}"


class CashTransaction(models.Model):
    shift = models.ForeignKey(CashierShift, on_delete=models.PROTECT, related_name="cash_transactions")
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="cash_transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=CashTransactionType.choices)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reason = models.CharField(max_length=200, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} {self.amount}"
