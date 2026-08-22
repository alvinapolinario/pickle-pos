from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class MembershipTier(models.Model):
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="membership_tiers")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=80)
    court_discount_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    canteen_discount_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    priority_booking = models.BooleanField(default=False)
    points_per_peso = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Loyalty points earned per peso spent.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="uniq_membership_tier_branch_code"),
        ]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="memberships")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="memberships")
    tier = models.ForeignKey(MembershipTier, on_delete=models.PROTECT, related_name="memberships")
    started_on = models.DateField()
    expires_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_on", "-id"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["customer", "status"]),
        ]

    def is_current(self, on_date=None) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        today = on_date or timezone.localdate()
        if self.started_on > today:
            return False
        if self.expires_on and self.expires_on < today:
            return False
        return True

    def __str__(self) -> str:
        return f"{self.customer} · {self.tier}"


class LoyaltyTransaction(models.Model):
    class Kind(models.TextChoices):
        EARN = "earn", "Earn"
        REVERSE = "reverse", "Reverse"

    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="loyalty_transactions")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="loyalty_transactions")
    points = models.IntegerField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    source_type = models.CharField(max_length=40)
    source_id = models.BigIntegerField()
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.points} · {self.customer}"
