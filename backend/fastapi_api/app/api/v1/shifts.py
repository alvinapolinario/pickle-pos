from fastapi import APIRouter, Depends, HTTPException, status

from apps.shifts.models import CashierShift
from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import DomainError, NotFoundError
from core.domain.shifts import CASH_IN, CASH_OUT
from core.services.shift_service import ShiftService
from fastapi_api.app.api.errors import raise_domain
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.shifts import (
    CashMoveRequest,
    CashTransactionResponse,
    CloseShiftRequest,
    OpenShiftRequest,
    ShiftResponse,
)

router = APIRouter()


def _shift_response(shift, expected_cash=None) -> ShiftResponse:
    return ShiftResponse(
        id=shift.id,
        branch_id=shift.branch_id,
        cashier_id=shift.cashier_id,
        status=shift.status,
        opening_cash=shift.opening_cash,
        expected_cash=shift.expected_cash if shift.expected_cash is not None else expected_cash,
        actual_cash=shift.actual_cash,
        over_short=shift.over_short,
        notes=shift.notes,
        opened_at=shift.opened_at,
        closed_at=shift.closed_at,
    )


def _owned_shift(shift_id: int, cashier_id: int) -> CashierShift:
    shift = CashierShift.objects.filter(pk=shift_id).first()
    if shift is None:
        raise_domain(NotFoundError("Shift not found."))
    if shift.cashier_id != cashier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shift does not belong to this cashier.",
        )
    return shift


@router.post("/shifts/open", response_model=ShiftResponse)
def open_shift(
    payload: OpenShiftRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    branch_id = payload.branch_id or current_user.branch_id
    if not branch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required.")
    try:
        shift = ShiftService().open_shift(
            cashier_id=current_user.user_id,
            branch_id=branch_id,
            opening_cash=payload.opening_cash,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _shift_response(shift)


@router.post("/shifts/close", response_model=ShiftResponse)
def close_shift(
    payload: CloseShiftRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    _owned_shift(payload.shift_id, current_user.user_id)
    try:
        shift = ShiftService().close_shift(
            shift_id=payload.shift_id,
            actual_cash=payload.actual_cash,
            notes=payload.notes,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _shift_response(shift)


@router.post("/shifts/{shift_id}/cash-in", response_model=CashTransactionResponse)
def cash_in(
    shift_id: int,
    payload: CashMoveRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return _cash_move(shift_id, payload, CASH_IN, current_user.user_id)


@router.post("/shifts/{shift_id}/cash-out", response_model=CashTransactionResponse)
def cash_out(
    shift_id: int,
    payload: CashMoveRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return _cash_move(shift_id, payload, CASH_OUT, current_user.user_id)


def _cash_move(shift_id: int, payload: CashMoveRequest, transaction_type: str, user_id: int):
    _owned_shift(shift_id, user_id)
    try:
        txn = ShiftService().add_cash(
            shift_id=shift_id,
            amount=payload.amount,
            reason=payload.reason,
            performed_by_id=user_id,
            transaction_type=transaction_type,
        )
    except DomainError as exc:
        raise_domain(exc)
    return CashTransactionResponse(
        id=txn.id,
        shift_id=txn.shift_id,
        transaction_type=txn.transaction_type,
        amount=txn.amount,
        reason=txn.reason,
    )


@router.get("/shifts/current", response_model=ShiftResponse)
def current_shift(current_user: AuthenticatedUser = Depends(get_current_user)):
    service = ShiftService()
    shift = service.current_shift(cashier_id=current_user.user_id, branch_id=current_user.branch_id)
    if shift is None:
        raise_domain(NotFoundError("No open shift."))
    return _shift_response(shift, expected_cash=service.expected_cash(shift))
