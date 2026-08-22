from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CourtResponse(BaseModel):
    id: int
    branch_id: int
    code: str
    name: str
    status: str
    hourly_rate: Decimal
    sort_order: int
    is_active: bool


class BookingResponse(BaseModel):
    id: int
    booking_number: str
    branch_id: int
    court_id: int
    court_name: str
    customer_id: int | None = None
    start_at: datetime
    end_at: datetime
    status: str
    amount: Decimal
    payment_method: str = ""
    payment_status: str
    notes: str = ""


class BookingCreateRequest(BaseModel):
    court_id: int
    start_at: datetime
    end_at: datetime
    customer_id: int | None = None
    payment_method: str = "cash"
    notes: str = ""


class BookingQuoteRequest(BaseModel):
    court_id: int
    start_at: datetime
    end_at: datetime


class BookingQuoteResponse(BaseModel):
    court_id: int
    court_name: str
    hourly_rate: Decimal
    amount: Decimal


class OccupancyResponse(BaseModel):
    total: int
    available: int
    occupied: int
    maintenance: int


class BookingRefundRequest(BaseModel):
    method: str = "cash"
    reason: str = ""


class BookingRefundResponse(BaseModel):
    id: int
    refund_number: str
    booking_id: int
    booking_number: str
    amount: Decimal
    method: str
    reason: str = ""
    payment_status: str
    status: str
