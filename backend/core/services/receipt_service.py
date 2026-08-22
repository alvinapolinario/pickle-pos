"""Server-side receipt payload for reprint (console + thermal POS)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.domain.pricing import money


WIDTH = 32


@dataclass(frozen=True)
class ReceiptLine:
    quantity: Decimal
    name: str
    unit_price: Decimal
    line_net: Decimal


@dataclass(frozen=True)
class ReceiptPayment:
    method: str
    amount: Decimal
    reference: str = ""


@dataclass(frozen=True)
class Receipt:
    branch_name: str
    branch_address: str
    branch_phone: str
    transaction_number: str
    receipt_number: str
    cashier: str
    customer: str
    sold_at: str
    lines: tuple[ReceiptLine, ...]
    gross_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    change_amount: Decimal
    payments: tuple[ReceiptPayment, ...]
    status: str
    notes: str
    vat_registered: bool
    text: str


def _money(value: Decimal) -> str:
    return f"P {money(value):.2f}"


def _row(left: str, right: str, width: int = WIDTH) -> str:
    space = width - len(left) - len(right)
    if space < 1:
        return f"{left[: width - len(right) - 1]} {right}"
    return f"{left}{' ' * space}{right}"


class ReceiptService:
    def build(self, sale) -> Receipt:
        branch = sale.branch
        lines = tuple(
            ReceiptLine(item.quantity, item.name, item.unit_price, item.line_net) for item in sale.items.all()
        )
        payments = tuple(
            ReceiptPayment(payment.get_method_display(), payment.amount, payment.reference)
            for payment in sale.payments.all()
        )
        sold_at = sale.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
        vat_registered = bool(getattr(branch, "vat_registered", True))
        receipt = Receipt(
            branch_name=branch.name,
            branch_address=" ".join(part for part in [branch.address, branch.city] if part),
            branch_phone=branch.phone,
            transaction_number=sale.transaction_number,
            receipt_number=sale.receipt_number or sale.transaction_number,
            cashier=str(sale.cashier),
            customer=sale.customer.name if getattr(sale, "customer_id", None) else "Walk-in",
            sold_at=sold_at,
            lines=lines,
            gross_amount=sale.gross_amount,
            discount_amount=sale.discount_amount,
            tax_amount=sale.tax_amount,
            net_amount=sale.net_amount,
            change_amount=sale.change_amount,
            payments=payments,
            status=sale.status,
            notes=sale.notes,
            vat_registered=vat_registered,
            text="",
        )
        return Receipt(**{**receipt.__dict__, "text": self.render_text(receipt)})

    def render_text(self, receipt: Receipt) -> str:
        parts = [
            receipt.branch_name.center(WIDTH),
            "PICKLEBALL POS".center(WIDTH),
        ]
        if receipt.branch_address:
            parts.append(receipt.branch_address[:WIDTH].center(WIDTH))
        if receipt.branch_phone:
            parts.append(receipt.branch_phone.center(WIDTH))
        parts.extend(
            [
                "-" * WIDTH,
                _row("Txn", receipt.transaction_number[-18:]),
                _row("Rcpt", receipt.receipt_number[-18:]),
                _row("Cashier", receipt.cashier[:18]),
                _row("Customer", receipt.customer[:18]),
                _row("When", receipt.sold_at),
                "-" * WIDTH,
            ]
        )
        for line in receipt.lines:
            qty = f"{line.quantity.normalize()} x {line.name}"
            parts.append(qty[:WIDTH])
            parts.append(_row(f"  @ {_money(line.unit_price)}", _money(line.line_net)))
        parts.append("-" * WIDTH)
        parts.append(_row("Gross", _money(receipt.gross_amount)))
        if receipt.discount_amount:
            parts.append(_row("Discount", f"-{_money(receipt.discount_amount)[2:]}"))
        if receipt.vat_registered:
            parts.append(_row("VAT", _money(receipt.tax_amount)))
        parts.append(_row("TOTAL", _money(receipt.net_amount)))
        for payment in receipt.payments:
            label = payment.method.upper()
            parts.append(_row(label, _money(payment.amount)))
        if receipt.change_amount:
            parts.append(_row("CHANGE", _money(receipt.change_amount)))
        footer = "Thank you. Prices include VAT." if receipt.vat_registered else "Thank you."
        parts.extend(["-" * WIDTH, footer.center(WIDTH)])
        if receipt.status != "completed":
            parts.append(receipt.status.upper().center(WIDTH))
        return "\n".join(parts)
