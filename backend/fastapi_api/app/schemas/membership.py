from decimal import Decimal

from pydantic import BaseModel


class MembershipTierResponse(BaseModel):
    id: int
    code: str
    name: str
    court_discount_pct: Decimal
    canteen_discount_pct: Decimal
    priority_booking: bool
    points_per_peso: Decimal


class MembershipBenefitsResponse(BaseModel):
    tier_code: str
    tier_name: str
    court_discount_pct: Decimal
    canteen_discount_pct: Decimal
    priority_booking: bool
    loyalty_points: int
