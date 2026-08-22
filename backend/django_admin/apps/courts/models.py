from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Court(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        MAINTENANCE = "maintenance", "Maintenance"

    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="courts")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    hourly_rate = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("350.00"))
    sort_order = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], name="uniq_court_code_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class CourtRate(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name="rates")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    hourly_rate = models.DecimalField(max_digits=14, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["court", "weekday"]
        constraints = [
            models.UniqueConstraint(fields=["court", "weekday"], name="uniq_court_rate_weekday"),
        ]

    def __str__(self) -> str:
        return f"{self.court} · {self.get_weekday_display()}"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        GCASH = "gcash", "GCash"
        MAYA = "maya", "Maya"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        OTHER = "other", "Other"

    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="bookings")
    court = models.ForeignKey(Court, on_delete=models.PROTECT, related_name="bookings")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="court_bookings",
    )
    booking_number = models.CharField(max_length=50)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "booking_number"], name="uniq_booking_number_branch"),
            models.CheckConstraint(condition=models.Q(end_at__gt=models.F("start_at")), name="booking_end_after_start"),
        ]
        indexes = [
            models.Index(fields=["branch", "start_at"]),
            models.Index(fields=["court", "start_at"]),
        ]

    def __str__(self) -> str:
        return self.booking_number


class BookingRefund(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="refunds")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="booking_refunds")
    refund_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    method = models.CharField(max_length=20, choices=Booking.PaymentMethod.choices, default=Booking.PaymentMethod.CASH)
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_refunds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "refund_number"], name="uniq_booking_refund_branch_number"),
        ]

    def __str__(self) -> str:
        return self.refund_number
