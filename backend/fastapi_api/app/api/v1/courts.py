from datetime import date

from fastapi import APIRouter, Depends, Query

from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import DomainError
from core.services.booking_service import BookingService
from fastapi_api.app.api.errors import raise_domain
from fastapi_api.app.dependencies.auth import enforce_any_permission, get_current_user
from fastapi_api.app.schemas.courts import (
    BookingCreateRequest,
    BookingQuoteRequest,
    BookingQuoteResponse,
    BookingRefundRequest,
    BookingRefundResponse,
    BookingResponse,
    CourtResponse,
    OccupancyResponse,
)

router = APIRouter()
service = BookingService()


def _booking_response(booking) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        booking_number=booking.booking_number,
        branch_id=booking.branch_id,
        court_id=booking.court_id,
        court_name=booking.court.name,
        customer_id=booking.customer_id,
        start_at=booking.start_at,
        end_at=booking.end_at,
        status=booking.status,
        amount=booking.amount,
        payment_method=booking.payment_method,
        payment_status=booking.payment_status,
        notes=booking.notes,
    )


@router.get("/courts", response_model=list[CourtResponse])
def list_courts(current_user: AuthenticatedUser = Depends(get_current_user)):
    return [
        CourtResponse(
            id=court.id,
            branch_id=court.branch_id,
            code=court.code,
            name=court.name,
            status=court.status,
            hourly_rate=court.hourly_rate,
            sort_order=court.sort_order,
            is_active=court.is_active,
        )
        for court in service.list_courts(branch_id=current_user.branch_id)
    ]


@router.get("/bookings", response_model=list[BookingResponse])
def list_bookings(
    on_date: date | None = Query(default=None, alias="date"),
    court_id: int | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return [
        _booking_response(booking)
        for booking in service.list_bookings(
            branch_id=current_user.branch_id,
            on_date=on_date,
            court_id=court_id,
        )
    ]


@router.post("/bookings/quote", response_model=BookingQuoteResponse)
def quote_booking(payload: BookingQuoteRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        quoted = service.quote(court_id=payload.court_id, start_at=payload.start_at, end_at=payload.end_at)
    except DomainError as exc:
        raise_domain(exc)
    court = quoted["court"]
    return BookingQuoteResponse(
        court_id=court.id,
        court_name=court.name,
        hourly_rate=quoted["hourly_rate"],
        amount=quoted["amount"],
    )


@router.post("/bookings", response_model=BookingResponse)
def create_booking(payload: BookingCreateRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    enforce_any_permission(current_user, "courts.*", "sales.create")
    try:
        booking = service.create_booking(
            court_id=payload.court_id,
            booked_by_id=current_user.user_id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            customer_id=payload.customer_id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _booking_response(booking)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    enforce_any_permission(current_user, "courts.*", "sales.create")
    try:
        booking = service.cancel_booking(booking_id=booking_id, booked_by_id=current_user.user_id)
    except DomainError as exc:
        raise_domain(exc)
    return _booking_response(booking)


@router.post("/bookings/{booking_id}/refund", response_model=BookingRefundResponse)
def refund_booking(
    booking_id: int,
    payload: BookingRefundRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_any_permission(current_user, "courts.*", "sales.refund")
    try:
        refund = service.refund_booking(
            booking_id=booking_id,
            refunded_by_id=current_user.user_id,
            method=payload.method,
            reason=payload.reason,
        )
    except DomainError as exc:
        raise_domain(exc)
    booking = refund.booking
    return BookingRefundResponse(
        id=refund.id,
        refund_number=refund.refund_number,
        booking_id=booking.id,
        booking_number=booking.booking_number,
        amount=refund.amount,
        method=refund.method,
        reason=refund.reason,
        payment_status=booking.payment_status,
        status=booking.status,
    )


@router.get("/courts/occupancy", response_model=OccupancyResponse)
def court_occupancy(current_user: AuthenticatedUser = Depends(get_current_user)):
    return OccupancyResponse(**service.occupancy(branch_id=current_user.branch_id))
