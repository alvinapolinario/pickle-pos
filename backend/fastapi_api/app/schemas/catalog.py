from decimal import Decimal

from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: int
    branch_id: int
    name: str
    sort_order: int
    is_active: bool


class ProductResponse(BaseModel):
    id: int
    branch_id: int
    category_id: int
    category_name: str
    sku: str
    barcode: str
    name: str
    description: str
    selling_price: Decimal
    cost_price: Decimal
    unit: str
    tax_status: str
    track_inventory: bool
    reorder_level: Decimal
    image_url: str | None = None
    is_active: bool
