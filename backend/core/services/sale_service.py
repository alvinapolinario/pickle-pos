"""POS sales: server-priced tickets, payments, inventory, void, and refund."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from core.domain.exceptions import ConflictError, DomainError, NotFoundError
from core.domain.inventory import QTY, RETURN, SALE
from core.domain.pricing import money
from core.services.document_numbers import next_document_number
from core.services.inventory_service import InventoryService
from core.services.pricing_service import PricingService, QuoteLineInput
from core.services.shift_service import ShiftService


@dataclass(frozen=True)
class SaleLineInput:
    product_id: int
    quantity: Decimal
    modifier_total: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class PaymentInput:
    method: str
    amount: Decimal
    reference: str = ""


@dataclass(frozen=True)
class RefundLineInput:
    sale_item_id: int
    quantity: Decimal


class SaleService:
    def create_sale(
        self,
        *,
        shift_id: int,
        cashier_id: int,
        lines: list[SaleLineInput],
        payments: list[PaymentInput],
        discount_amount: Decimal = Decimal("0.00"),
        notes: str = "",
        device_id: int | None = None,
        client_sale_uuid: UUID | str | None = None,
        hold: bool = False,
        customer_id: int | None = None,
    ):
        from apps.sales.models import HeldOrder, Payment, Sale, SaleItem

        uuid_value = UUID(str(client_sale_uuid)) if client_sale_uuid else uuid4()
        with transaction.atomic():
            existing = Sale.objects.select_for_update().filter(client_sale_uuid=uuid_value).first()
            if existing:
                return existing

            shift = ShiftService()._lock_open(shift_id)
            if shift.cashier_id != cashier_id:
                raise DomainError("Shift does not belong to this cashier.")
            if device_id:
                self._assert_device(device_id, shift.branch_id)
            customer = self._resolve_customer(customer_id, shift.branch_id)

            quote = PricingService().quote(
                branch_id=shift.branch_id,
                lines=[
                    QuoteLineInput(line.product_id, line.quantity, line.modifier_total) for line in lines
                ],
                discount_amount=discount_amount,
                customer_id=customer.id if customer else None,
            )

            change = money(0)
            payment_status = Sale.PaymentStatus.UNPAID
            receipt_number = ""
            status = Sale.Status.HELD if hold else Sale.Status.COMPLETED
            if hold:
                if payments:
                    raise DomainError("Held orders cannot take payment yet.")
            else:
                change, payment_status = self._settle_payments(quote.net_amount, payments)
                receipt_number = next_document_number(Sale, shift.branch_id, "receipt_number", "R")

            sale = Sale.objects.create(
                branch_id=shift.branch_id,
                shift=shift,
                cashier_id=cashier_id,
                device_id=device_id,
                customer=customer,
                transaction_number=next_document_number(Sale, shift.branch_id, "transaction_number", shift.branch.code),
                receipt_number=receipt_number,
                client_sale_uuid=uuid_value,
                gross_amount=quote.gross_amount,
                discount_amount=quote.discount_amount,
                tax_amount=quote.tax_amount,
                net_amount=quote.net_amount,
                change_amount=change,
                status=status,
                payment_status=payment_status,
                notes=notes,
            )
            inventory = InventoryService()
            for line in quote.lines:
                item = SaleItem.objects.create(
                    sale=sale,
                    product_id=line.product_id,
                    sku=line.sku,
                    name=line.name,
                    quantity=line.quantity.quantize(QTY),
                    unit_price=line.unit_price,
                    line_gross=line.line_gross,
                    line_discount=line.line_discount,
                    line_tax=line.line_tax,
                    line_net=line.line_net,
                )
                if not hold and line.track_inventory:
                    movement = inventory.apply_movement(
                        branch_id=shift.branch_id,
                        product_id=line.product_id,
                        movement_type=SALE,
                        quantity=line.quantity,
                        unit_cost=line.cost_price,
                        reference_type="sale",
                        reference_id=sale.id,
                        performed_by_id=cashier_id,
                        notes=sale.transaction_number,
                    )
                    item.inventory_movement_id = movement.movement_id
                    item.save(update_fields=["inventory_movement_id"])
            if hold:
                HeldOrder.objects.create(sale=sale, branch_id=shift.branch_id, notes=notes)
            else:
                for payment in payments:
                    Payment.objects.create(
                        sale=sale,
                        method=payment.method,
                        amount=money(payment.amount),
                        reference=payment.reference,
                    )
            self._audit("sale.create" if not hold else "sale.hold", sale, {"status": sale.status})
            if not hold and customer:
                from core.services.membership_service import MembershipService

                MembershipService().award_points(
                    customer_id=customer.id,
                    branch_id=shift.branch_id,
                    amount=quote.net_amount,
                    source_type="sale",
                    source_id=sale.id,
                    notes=sale.transaction_number,
                )
            return sale

    def resume_sale(
        self,
        *,
        sale_id: int,
        cashier_id: int,
        payments: list[PaymentInput],
    ):
        from apps.sales.models import HeldOrder, Payment, Sale

        with transaction.atomic():
            sale = self._lock_sale(sale_id)
            if sale.status != Sale.Status.HELD:
                raise DomainError("Only held orders can be resumed.")
            shift = ShiftService()._lock_open(sale.shift_id)
            if shift.cashier_id != cashier_id:
                raise DomainError("Shift does not belong to this cashier.")
            change, payment_status = self._settle_payments(sale.net_amount, payments)
            inventory = InventoryService()
            for item in sale.items.select_related("product"):
                if item.product.track_inventory:
                    movement = inventory.apply_movement(
                        branch_id=sale.branch_id,
                        product_id=item.product_id,
                        movement_type=SALE,
                        quantity=item.quantity,
                        unit_cost=item.product.cost_price,
                        reference_type="sale",
                        reference_id=sale.id,
                        performed_by_id=cashier_id,
                        notes=sale.transaction_number,
                    )
                    item.inventory_movement_id = movement.movement_id
                    item.save(update_fields=["inventory_movement_id"])
            for payment in payments:
                Payment.objects.create(
                    sale=sale,
                    method=payment.method,
                    amount=money(payment.amount),
                    reference=payment.reference,
                )
            sale.status = Sale.Status.COMPLETED
            sale.payment_status = payment_status
            sale.change_amount = change
            sale.receipt_number = next_document_number(Sale, sale.branch_id, "receipt_number", "R")
            sale.save(
                update_fields=["status", "payment_status", "change_amount", "receipt_number", "updated_at"]
            )
            HeldOrder.objects.filter(sale=sale).delete()
            self._audit("sale.resume", sale, {"status": sale.status})
            if sale.customer_id:
                from core.services.membership_service import MembershipService

                MembershipService().award_points(
                    customer_id=sale.customer_id,
                    branch_id=sale.branch_id,
                    amount=sale.net_amount,
                    source_type="sale",
                    source_id=sale.id,
                    notes=sale.transaction_number,
                )
            return sale

    @staticmethod
    def set_void_passcode(branch, passcode: str) -> None:
        raw = (passcode or "").strip()
        if len(raw) < 4:
            raise DomainError("Void passcode must be at least 4 characters.")
        branch.void_passcode_hash = make_password(raw)
        branch.save(update_fields=["void_passcode_hash", "updated_at"])

    @staticmethod
    def verify_void_passcode(branch, passcode: str) -> None:
        if not getattr(branch, "void_passcode_hash", ""):
            raise DomainError("Void passcode is not set in System Settings.")
        if not passcode or not check_password(passcode, branch.void_passcode_hash):
            raise DomainError("Invalid void passcode.")

    def void_sale(self, *, sale_id: int, cashier_id: int, reason: str = ""):
        from apps.sales.models import Sale

        with transaction.atomic():
            sale = self._lock_sale(sale_id)
            if sale.status == Sale.Status.VOID:
                raise DomainError("Sale is already voided.")
            if sale.refunds.exists():
                raise DomainError("Cannot void a sale that has refunds.")
            shift = ShiftService()._lock_open(sale.shift_id)
            if shift.cashier_id != cashier_id:
                raise DomainError("Void this sale from the cashier's open shift.")
            inventory = InventoryService()
            if sale.status == Sale.Status.COMPLETED:
                for item in sale.items.select_related("product"):
                    if item.product.track_inventory:
                        inventory.apply_movement(
                            branch_id=sale.branch_id,
                            product_id=item.product_id,
                            movement_type=RETURN,
                            quantity=item.quantity,
                            unit_cost=item.product.cost_price,
                            reference_type="sale_void",
                            reference_id=sale.id,
                            performed_by_id=cashier_id,
                            notes=reason or sale.transaction_number,
                        )
            sale.status = Sale.Status.VOID
            sale.payment_status = Sale.PaymentStatus.UNPAID
            sale.void_reason = reason
            sale.voided_at = timezone.now()
            sale.save(update_fields=["status", "payment_status", "void_reason", "voided_at", "updated_at"])
            from apps.sales.models import HeldOrder

            HeldOrder.objects.filter(sale=sale).delete()
            self._audit("sale.void", sale, {"reason": reason})
            from core.services.membership_service import MembershipService

            MembershipService().reverse_points(source_type="sale", source_id=sale.id, notes=reason)
            return sale

    def refund_sale(
        self,
        *,
        sale_id: int,
        shift_id: int,
        cashier_id: int,
        lines: list[RefundLineInput],
        method: str = "cash",
        reason: str = "",
    ):
        from apps.sales.models import Payment, Refund, RefundItem, Sale, SaleItem

        with transaction.atomic():
            sale = self._lock_sale(sale_id)
            if sale.status != Sale.Status.COMPLETED:
                raise DomainError("Only completed sales can be refunded.")
            shift = ShiftService()._lock_open(shift_id)
            if shift.cashier_id != cashier_id:
                raise DomainError("Shift does not belong to this cashier.")
            if shift.branch_id != sale.branch_id:
                raise DomainError("Refund must be on the same branch as the sale.")
            if method not in Payment.Method.values:
                raise DomainError("Invalid refund method.")

            inventory = InventoryService()
            refund = Refund(
                sale=sale,
                shift=shift,
                branch_id=sale.branch_id,
                method=method,
                reason=reason,
                created_by_id=cashier_id,
                amount=money(0),
            )
            refund.refund_number = next_document_number(Refund, sale.branch_id, "refund_number", "RF")
            refund.save()

            posted = 0
            total = money(0)
            for line in lines:
                qty = Decimal(line.quantity).quantize(QTY)
                if qty <= 0:
                    continue
                item = SaleItem.objects.select_for_update().select_related("product").get(
                    pk=line.sale_item_id,
                    sale=sale,
                )
                if qty > item.quantity_refundable:
                    raise DomainError(f"Cannot refund {qty} of {item.name}; {item.quantity_refundable} remaining.")
                amount = money(item.line_net * qty / item.quantity)
                if item.product.track_inventory:
                    movement = inventory.apply_movement(
                        branch_id=sale.branch_id,
                        product_id=item.product_id,
                        movement_type=RETURN,
                        quantity=qty,
                        unit_cost=item.product.cost_price,
                        reference_type="refund",
                        reference_id=refund.id,
                        performed_by_id=cashier_id,
                        notes=refund.refund_number,
                    )
                else:
                    movement = None
                RefundItem.objects.create(
                    refund=refund,
                    sale_item=item,
                    quantity=qty,
                    amount=amount,
                    inventory_movement_id=movement.movement_id if movement else None,
                )
                item.quantity_refunded = (item.quantity_refunded + qty).quantize(QTY)
                item.save(update_fields=["quantity_refunded"])
                total = money(total + amount)
                posted += 1

            if posted == 0:
                raise DomainError("Enter a quantity to refund.")
            refund.amount = total
            refund.save(update_fields=["amount"])
            self._audit("sale.refund", sale, {"refund": refund.refund_number, "amount": str(total)})
            if sale.customer_id:
                from core.services.membership_service import MembershipService

                MembershipService().clawback_points(
                    customer_id=sale.customer_id,
                    branch_id=sale.branch_id,
                    amount=total,
                    source_type="sale_refund",
                    source_id=refund.id,
                    notes=refund.refund_number,
                )
            return refund

    def _settle_payments(self, net: Decimal, payments: list[PaymentInput]) -> tuple[Decimal, str]:
        from apps.sales.models import Payment, Sale

        if not payments:
            raise DomainError("Add at least one payment.")
        cash = money(0)
        non_cash = money(0)
        for payment in payments:
            if payment.method not in Payment.Method.values:
                raise DomainError(f"Unsupported payment method: {payment.method}")
            amount = money(payment.amount)
            if amount <= 0:
                raise DomainError("Payment amount must be greater than zero.")
            if payment.method == Payment.Method.CASH:
                cash = money(cash + amount)
            else:
                non_cash = money(non_cash + amount)
        if non_cash > net:
            raise DomainError("Non-cash payments cannot exceed the amount due.")
        due = money(net - non_cash)
        if cash < due:
            raise DomainError("Payment does not cover the amount due.")
        change = money(cash - due)
        status = Sale.PaymentStatus.PAID if money(cash + non_cash) >= net else Sale.PaymentStatus.PARTIAL
        return change, status

    def _lock_sale(self, sale_id: int):
        from apps.sales.models import Sale

        sale = Sale.objects.select_for_update().select_related("shift", "branch").filter(pk=sale_id).first()
        if sale is None:
            raise NotFoundError("Sale not found.")
        return sale

    def _assert_device(self, device_id: int, branch_id: int):
        from apps.accounts.models import Device

        device = Device.objects.filter(pk=device_id, is_active=True).first()
        if device is None:
            raise DomainError("Device is not registered or inactive.")
        if device.branch_id != branch_id:
            raise DomainError("Device is not authorized for this branch.")

    def _resolve_customer(self, customer_id: int | None, branch_id: int):
        if not customer_id:
            return None
        from apps.customers.models import Customer

        customer = Customer.objects.filter(pk=customer_id, is_active=True).first()
        if customer is None:
            raise DomainError("Customer not found.")
        if customer.branch_id != branch_id:
            raise DomainError("Customer is not on this branch.")
        return customer

    def _audit(self, action: str, sale, extra: dict):
        from apps.audit.middleware import write_audit_log

        write_audit_log(
            action=action,
            entity_type="sale",
            entity_id=str(sale.id),
            new_values={"transaction_number": sale.transaction_number, **extra},
        )
