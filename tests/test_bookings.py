from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.courts.models import Booking, Court, CourtRate
from core.domain.exceptions import ConflictError, DomainError
from core.services.booking_service import BookingService


@pytest.fixture
def court(branch):
    return Court.objects.create(
        branch=branch,
        code="C1",
        name="Court 1",
        hourly_rate=Decimal("350.00"),
    )


def _slot(hours=10, days=1, duration=1):
    start = (timezone.localtime() + timedelta(days=days)).replace(hour=hours, minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=duration)


@pytest.mark.django_db
def test_quote_uses_hourly_rate(court):
    start, end = _slot()
    quoted = BookingService().quote(court_id=court.id, start_at=start, end_at=end)
    assert quoted["amount"] == Decimal("350.00")
    assert quoted["hourly_rate"] == Decimal("350.00")


@pytest.mark.django_db
def test_weekday_rate_overrides_default(court):
    start, end = _slot()
    CourtRate.objects.create(court=court, weekday=start.weekday(), hourly_rate=Decimal("500.00"))
    quoted = BookingService().quote(court_id=court.id, start_at=start, end_at=end)
    assert quoted["amount"] == Decimal("500.00")


@pytest.mark.django_db
def test_create_booking_and_prevent_overlap(court, user):
    start, end = _slot()
    service = BookingService()
    booking = service.create_booking(
        court_id=court.id,
        booked_by_id=user.id,
        start_at=start,
        end_at=end,
        payment_method="cash",
    )
    assert booking.booking_number.startswith("BK-")
    assert booking.amount == Decimal("350.00")
    assert booking.payment_status == "paid"
    with pytest.raises(ConflictError):
        service.create_booking(
            court_id=court.id,
            booked_by_id=user.id,
            start_at=start + timedelta(minutes=30),
            end_at=end + timedelta(minutes=30),
        )


@pytest.mark.django_db
def test_cancel_frees_slot(court, user):
    start, end = _slot()
    service = BookingService()
    booking = service.create_booking(court_id=court.id, booked_by_id=user.id, start_at=start, end_at=end)
    service.cancel_booking(booking_id=booking.id)
    again = service.create_booking(court_id=court.id, booked_by_id=user.id, start_at=start, end_at=end)
    assert again.id != booking.id


@pytest.mark.django_db
def test_maintenance_blocks_booking(court, user):
    court.status = Court.Status.MAINTENANCE
    court.save(update_fields=["status"])
    start, end = _slot()
    with pytest.raises(DomainError, match="maintenance"):
        BookingService().create_booking(court_id=court.id, booked_by_id=user.id, start_at=start, end_at=end)


@pytest.mark.django_db
def test_past_slot_rejected(court, user):
    start = timezone.now() - timedelta(hours=2)
    with pytest.raises(DomainError, match="already ended"):
        BookingService().create_booking(
            court_id=court.id,
            booked_by_id=user.id,
            start_at=start,
            end_at=start + timedelta(hours=1),
        )


@pytest.mark.django_db
def test_refund_paid_booking_frees_slot(court, user):
    start, end = _slot()
    service = BookingService()
    booking = service.create_booking(
        court_id=court.id,
        booked_by_id=user.id,
        start_at=start,
        end_at=end,
        payment_method="gcash",
    )
    refund = service.refund_booking(booking_id=booking.id, refunded_by_id=user.id, method="gcash", reason="Rain")
    booking.refresh_from_db()
    assert refund.amount == Decimal("350.00")
    assert refund.refund_number.startswith("BKR-")
    assert booking.status == Booking.Status.CANCELLED
    assert booking.payment_status == Booking.PaymentStatus.REFUNDED
    again = service.create_booking(court_id=court.id, booked_by_id=user.id, start_at=start, end_at=end)
    assert again.id != booking.id
    with pytest.raises(DomainError, match="already refunded"):
        service.refund_booking(booking_id=booking.id, refunded_by_id=user.id)


@pytest.mark.django_db
def test_cannot_refund_unpaid_booking(court, user):
    start, end = _slot(hours=11)
    booking = BookingService().create_booking(
        court_id=court.id,
        booked_by_id=user.id,
        start_at=start,
        end_at=end,
        payment_method="",
    )
    assert booking.payment_status == Booking.PaymentStatus.UNPAID
    with pytest.raises(DomainError, match="paid"):
        BookingService().refund_booking(booking_id=booking.id, refunded_by_id=user.id)


@pytest.mark.django_db
def test_refund_after_cancel_without_refund(court, user):
    start, end = _slot(hours=14)
    service = BookingService()
    booking = service.create_booking(court_id=court.id, booked_by_id=user.id, start_at=start, end_at=end)
    service.cancel_booking(booking_id=booking.id)
    refund = service.refund_booking(booking_id=booking.id, refunded_by_id=user.id, method="cash")
    booking.refresh_from_db()
    assert refund.amount == booking.amount
    assert booking.payment_status == Booking.PaymentStatus.REFUNDED
