from decimal import Decimal

from pydantic import BaseModel


class InventoryBalanceResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    track_inventory: bool
    on_hand: Decimal
    reorder_level: Decimal
    is_low: bool
    unit: str
