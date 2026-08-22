"""Inventory ledger rules — pure Python, no ORM."""

from decimal import Decimal

from core.domain.exceptions import DomainError

STOCK_IN = "stock_in"
STOCK_OUT = "stock_out"
ADJUSTMENT = "adjustment"
TRANSFER = "transfer"
SALE = "sale"
RETURN = "return"
WASTAGE = "wastage"
EXPIRED = "expired"

MOVEMENT_TYPES = (
    STOCK_IN,
    STOCK_OUT,
    ADJUSTMENT,
    TRANSFER,
    SALE,
    RETURN,
    WASTAGE,
    EXPIRED,
)

IN_TYPES = frozenset({STOCK_IN, RETURN})
OUT_TYPES = frozenset({STOCK_OUT, SALE, WASTAGE, EXPIRED, TRANSFER})

QTY = Decimal("0.001")


def signed_quantity(movement_type: str, quantity: Decimal) -> Decimal:
    """Return the ledger delta. In/out types are normalized; adjustments stay signed."""
    qty = Decimal(quantity)
    if qty == 0:
        raise DomainError("Quantity cannot be zero.")
    if movement_type in IN_TYPES:
        return abs(qty).quantize(QTY)
    if movement_type in OUT_TYPES:
        return (-abs(qty)).quantize(QTY)
    if movement_type == ADJUSTMENT:
        return qty.quantize(QTY)
    raise DomainError(f"Unknown movement type: {movement_type}")
