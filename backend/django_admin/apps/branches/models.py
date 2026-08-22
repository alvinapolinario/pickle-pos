from decimal import Decimal

from django.db import models


class Branch(models.Model):
    """Physical location — supports future multi-branch expansion."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    receipt_store_name = models.CharField(max_length=150, blank=True)
    receipt_address = models.TextField(blank=True)
    timezone = models.CharField(max_length=50, default="Asia/Manila")
    vat_registered = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.1200"))
    memberships_enabled = models.BooleanField(default=True)
    void_passcode_hash = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    @property
    def printed_store_name(self) -> str:
        return (self.receipt_store_name or "").strip() or self.name

    @property
    def printed_address(self) -> str:
        custom = (self.receipt_address or "").strip()
        if custom:
            return custom
        return " ".join(part for part in [self.address, self.city] if part)

    @property
    def void_passcode_set(self) -> bool:
        return bool(self.void_passcode_hash)
