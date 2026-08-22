"""Open/close cashier shifts and record cash drawer movements."""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.domain.exceptions import ConflictError, DomainError, NotFoundError
from core.domain.pricing import money
from core.domain.shifts import CASH_IN, CASH_OUT, CLOSED, OPEN


class ShiftService:
    def current_shift(self, *, cashier_id: int, branch_id: int | None = None):
        from apps.shifts.models import CashierShift

        queryset = CashierShift.objects.filter(cashier_id=cashier_id, status=OPEN)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset.select_related("cashier", "branch").first()

    def open_shift(
        self,
        *,
        cashier_id: int,
        branch_id: int,
        opening_cash: Decimal,
        notes: str = "",
    ):
        from apps.shifts.models import CashierShift

        opening = money(opening_cash)
        if opening < 0:
            raise DomainError("Opening cash cannot be negative.")
        if self.current_shift(cashier_id=cashier_id):
            raise ConflictError("Cashier already has an open shift.")
        try:
            shift = CashierShift.objects.create(
                cashier_id=cashier_id,
                branch_id=branch_id,
                opening_cash=opening,
                notes=notes,
                status=OPEN,
            )
        except IntegrityError as exc:
            raise ConflictError("Cashier already has an open shift.") from exc
        self._audit("shift.open", shift, {"opening_cash": str(opening)})
        return shift

    def add_cash(
        self,
        *,
        shift_id: int,
        amount: Decimal,
        reason: str = "",
        performed_by_id: int | None = None,
        transaction_type: str = CASH_IN,
    ):
        from apps.shifts.models import CashTransaction

        if transaction_type not in {CASH_IN, CASH_OUT}:
            raise DomainError("Invalid cash transaction type.")
        value = money(amount)
        if value <= 0:
            raise DomainError("Amount must be greater than zero.")
        with transaction.atomic():
            shift = self._lock_open(shift_id)
            txn = CashTransaction.objects.create(
                shift=shift,
                branch_id=shift.branch_id,
                transaction_type=transaction_type,
                amount=value,
                reason=reason,
                performed_by_id=performed_by_id,
            )
        self._audit(
            f"shift.{transaction_type}",
            shift,
            {"amount": str(value), "reason": reason},
        )
        return txn

    def close_shift(
        self,
        *,
        shift_id: int,
        actual_cash: Decimal,
        notes: str = "",
    ):
        with transaction.atomic():
            shift = self._lock_open(shift_id)
            expected = self.expected_cash(shift)
            actual = money(actual_cash)
            if actual < 0:
                raise DomainError("Actual cash cannot be negative.")
            shift.status = CLOSED
            shift.expected_cash = expected
            shift.actual_cash = actual
            shift.over_short = money(actual - expected)
            if notes:
                shift.notes = notes
            shift.closed_at = timezone.now()
            shift.save(
                update_fields=[
                    "status",
                    "expected_cash",
                    "actual_cash",
                    "over_short",
                    "notes",
                    "closed_at",
                ]
            )
        self._audit(
            "shift.close",
            shift,
            {
                "expected_cash": str(shift.expected_cash),
                "actual_cash": str(shift.actual_cash),
                "over_short": str(shift.over_short),
            },
        )
        return shift

    def expected_cash(self, shift) -> Decimal:
        from django.db.models import Sum

        from apps.shifts.models import CashTransaction

        cash_in = shift.cash_transactions.filter(transaction_type=CASH_IN).aggregate(total=Sum("amount"))["total"] or 0
        cash_out = shift.cash_transactions.filter(transaction_type=CASH_OUT).aggregate(total=Sum("amount"))["total"] or 0
        tendered, change, refunded = self._sale_cash_totals(shift.id)
        return money(shift.opening_cash + cash_in - cash_out + tendered - change - refunded)

    def _sale_cash_totals(self, shift_id: int) -> tuple[Decimal, Decimal, Decimal]:
        from django.db.models import Sum

        from apps.sales.models import Payment, Refund, Sale

        completed = Sale.objects.filter(shift_id=shift_id, status=Sale.Status.COMPLETED)
        tendered = (
            Payment.objects.filter(sale__in=completed, method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        change = completed.aggregate(total=Sum("change_amount"))["total"] or 0
        refunded = (
            Refund.objects.filter(shift_id=shift_id, method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        return money(tendered), money(change), money(refunded)

    def _lock_open(self, shift_id: int):
        from apps.shifts.models import CashierShift

        shift = CashierShift.objects.select_for_update().select_related("cashier", "branch").filter(pk=shift_id).first()
        if shift is None:
            raise NotFoundError("Shift not found.")
        if shift.status != OPEN:
            raise DomainError("Shift is not open.")
        return shift

    def _audit(self, action: str, shift, extra: dict):
        from apps.audit.middleware import write_audit_log

        write_audit_log(
            action=action,
            entity_type="cashier_shift",
            entity_id=str(shift.id),
            new_values={"cashier_id": shift.cashier_id, **extra},
        )
