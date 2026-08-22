from decimal import Decimal

from pydantic import BaseModel, Field


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    mobile: str = ""
    email: str = ""
    notes: str = ""


class CustomerResponse(BaseModel):
    id: int
    branch_id: int
    name: str
    mobile: str = ""
    email: str = ""
    notes: str = ""
    is_active: bool
    loyalty_points: int = 0
    membership_tier: str = ""
    canteen_discount_pct: Decimal = Decimal("0")
    court_discount_pct: Decimal = Decimal("0")
