from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OpenShiftRequest(BaseModel):
    opening_cash: Decimal
    notes: str = ""
    branch_id: int | None = None


class CloseShiftRequest(BaseModel):
    shift_id: int
    actual_cash: Decimal
    notes: str = ""


class CashMoveRequest(BaseModel):
    amount: Decimal
    reason: str = ""


class ShiftResponse(BaseModel):
    id: int
    branch_id: int
    cashier_id: int
    status: str
    opening_cash: Decimal
    expected_cash: Decimal | None = None
    actual_cash: Decimal | None = None
    over_short: Decimal | None = None
    notes: str = ""
    opened_at: datetime
    closed_at: datetime | None = None


class CashTransactionResponse(BaseModel):
    id: int
    shift_id: int
    transaction_type: str
    amount: Decimal
    reason: str = ""
