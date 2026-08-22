"""Court bookings with overlap locking. Server-authoritative rates."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.domain.exceptions import ConflictError, DomainError, NotFoundError
from core.domain.pricing import money
from core.services.document_numbers import next_document_number


def _aware(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


class BookingService:
    def hourly_rate_for(self, court, start_at: datetime) -> Decimal:
        weekday = timezone.localtime(_aware(start_at)).weekday()
        rate = court.rates.filter(is_active=True, weekday=weekday).first()
        return money(rate.hourly_rate if rate else court.hourly_rate)

    def quote_amount(self, court, start_at: datetime, end_at: datetime) -> Decimal:
        start_at = _aware(start_at)
        end_at = _aware(end_at)
        minutes = max((end_at - start_at).total_seconds() / 60, 0)
        hours = Decimal(str(minutes / 60))
        return money(self.hourly_rate_for(court, start_at) * hours)

    def quote(self, *, court_id: int, start_at: datetime, end_at: datetime) -> dict:
        from apps.courts.models import Court

        court = Court.objects.filter(pk=court_id, is_active=True).first()
        if court is None:
            raise NotFoundError("Court not found.")
        start_at = _aware(start_at)
        end_at = _aware(end_at)
        if end_at <= start_at:
            raise DomainError("Booking end must be after start.")
        return {
            "court": court,
            "hourly_rate": self.hourly_rate_for(court, start_at),
            "amount": self.quote_amount(court, start_at, end_at),
        }

    def list_courts(self, *, branch_id: int | None):
        from apps.courts.models import Court

        queryset = Court.objects.filter(is_active=True).select_related("branch")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset

    def list_bookings(
        self,
        *,
        branch_id: int | None,
        on_date: date | None = None,
        court_id: int | None = None,
        include_cancelled: bool = False,
    ):
        from apps.courts.models import Booking

        queryset = Booking.objects.select_related("court", "customer", "booked_by")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if court_id:
            queryset = queryset.filter(court_id=court_id)
        if not include_cancelled:
            queryset = queryset.exclude(status=Booking.Status.CANCELLED)
        if on_date:
            start = timezone.make_aware(datetime.combine(on_date, time.min))
            end = start + timedelta(days=1)
            queryset = queryset.filter(start_at__lt=end, end_at__gt=start)
        return queryset

    def create_booking(
        self,
        *,
        court_id: int,
        booked_by_id: int,
        start_at: datetime,
        end_at: datetime,
        customer_id: int | None = None,
        payment_method: str = "cash",
        notes: str = "",
    ):
        from apps.courts.models import Booking, Court

        start_at = _aware(start_at)
        end_at = _aware(end_at)
        if end_at <= start_at:
            raise DomainError("Booking end must be after start.")
        now = timezone.now()
        if end_at <= now:
            raise DomainError("Cannot book a slot that has already ended.")

        with transaction.atomic():
            court = Court.objects.select_for_update().filter(pk=court_id, is_active=True).first()
            if court is None:
                raise NotFoundError("Court not found.")
            if court.status == Court.Status.MAINTENANCE:
                raise DomainError("Court is under maintenance.")
            overlap = (
                Booking.objects.select_for_update()
                .filter(
                    court=court,
                    status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
                    start_at__lt=end_at,
                    end_at__gt=start_at,
                )
                .exists()
            )
            if overlap:
                raise ConflictError("That court slot is already booked.")
            amount = self.quote_amount(court, start_at, end_at)
            paid = bool(payment_method)
            booking = Booking(
                branch_id=court.branch_id,
                court=court,
                customer_id=customer_id,
                booked_by_id=booked_by_id,
                start_at=start_at,
                end_at=end_at,
                amount=amount,
                payment_method=payment_method,
                payment_status=Booking.PaymentStatus.PAID if paid else Booking.PaymentStatus.UNPAID,
                notes=notes,
            )
            booking.booking_number = next_document_number(Booking, court.branch_id, "booking_number", "BK")
            booking.save()
        self._audit("booking.create", booking, booked_by_id, {"amount": str(booking.amount)})
        return booking

    def cancel_booking(self, *, booking_id: int, booked_by_id: int | None = None):
        from apps.courts.models import Booking

        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
            if booking is None:
                raise NotFoundError("Booking not found.")
            if booking.status == Booking.Status.CANCELLED:
                raise DomainError("Booking is already cancelled.")
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status", "updated_at"])
        self._audit("booking.cancel", booking, booked_by_id)
        return booking

    def refund_booking(
        self,
        *,
        booking_id: int,
        refunded_by_id: int | None = None,
        method: str = "cash",
        reason: str = "",
    ):
        from apps.courts.models import Booking, BookingRefund

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("court")
                .filter(pk=booking_id)
                .first()
            )
            if booking is None:
                raise NotFoundError("Booking not found.")
            if booking.payment_status == Booking.PaymentStatus.REFUNDED or booking.refunds.exists():
                raise DomainError("Booking is already refunded.")
            if booking.payment_status != Booking.PaymentStatus.PAID:
                raise DomainError("Only paid bookings can be refunded.")
            if method and method not in Booking.PaymentMethod.values:
                raise DomainError("Invalid refund method.")
            refund = BookingRefund(
                booking=booking,
                branch_id=booking.branch_id,
                amount=booking.amount,
                method=method or booking.payment_method or Booking.PaymentMethod.CASH,
                reason=reason,
                created_by_id=refunded_by_id,
            )
            refund.refund_number = next_document_number(BookingRefund, booking.branch_id, "refund_number", "BKR")
            refund.save()
            booking.payment_status = Booking.PaymentStatus.REFUNDED
            if booking.status != Booking.Status.CANCELLED:
                booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["payment_status", "status", "updated_at"])
        self._audit("booking.refund", booking, refunded_by_id, {"amount": str(refund.amount), "reason": reason})
        return refund

    def occupancy(self, *, branch_id: int | None, at: datetime | None = None) -> dict:
        from apps.courts.models import Booking, Court

        at = _aware(at or timezone.now())
        courts = Court.objects.filter(is_active=True)
        if branch_id:
            courts = courts.filter(branch_id=branch_id)
        total = courts.count()
        maintenance = courts.filter(status=Court.Status.MAINTENANCE).count()
        occupied_ids = set(
            Booking.objects.filter(
                Q(court__in=courts),
                status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
                start_at__lte=at,
                end_at__gt=at,
            ).values_list("court_id", flat=True)
        )
        occupied = len(occupied_ids)
        available = max(total - maintenance - occupied, 0)
        return {
            "total": total,
            "available": available,
            "occupied": occupied,
            "maintenance": maintenance,
        }

    @staticmethod
    def _audit(action: str, booking, user_id: int | None, extra: dict | None = None) -> None:
        from apps.accounts.models import User
        from apps.audit.middleware import write_audit_log

        user = User.objects.filter(pk=user_id).first() if user_id else None
        write_audit_log(
            action=action,
            entity_type="booking",
            entity_id=str(booking.id),
            user=user,
            new_values={"booking_number": booking.booking_number, **(extra or {})},
        )
