from decimal import Decimal

import pytest

from core.domain.exceptions import ConflictError, DomainError
from core.domain.shifts import CLOSED, OPEN
from core.services.shift_service import ShiftService


@pytest.mark.django_db
def test_open_shift_and_reject_duplicate(branch, user):
    service = ShiftService()
    shift = service.open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    assert shift.status == OPEN
    assert shift.opening_cash == Decimal("100.00")
    with pytest.raises(ConflictError):
        service.open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("50.00"))


@pytest.mark.django_db
def test_cash_in_out_and_close_over_short(branch, user):
    service = ShiftService()
    shift = service.open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    service.add_cash(shift_id=shift.id, amount=Decimal("50.00"), reason="float", performed_by_id=user.id)
    service.add_cash(
        shift_id=shift.id,
        amount=Decimal("20.00"),
        reason="drop",
        performed_by_id=user.id,
        transaction_type="cash_out",
    )
    assert service.expected_cash(shift) == Decimal("130.00")
    closed = service.close_shift(shift_id=shift.id, actual_cash=Decimal("125.00"))
    assert closed.status == CLOSED
    assert closed.expected_cash == Decimal("130.00")
    assert closed.actual_cash == Decimal("125.00")
    assert closed.over_short == Decimal("-5.00")


@pytest.mark.django_db
def test_cannot_close_twice(branch, user):
    service = ShiftService()
    shift = service.open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("10.00"))
    service.close_shift(shift_id=shift.id, actual_cash=Decimal("10.00"))
    with pytest.raises(DomainError):
        service.close_shift(shift_id=shift.id, actual_cash=Decimal("10.00"))
