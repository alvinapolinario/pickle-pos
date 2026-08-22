from decimal import Decimal

from pydantic import BaseModel, Field


class CustomerResponse(BaseModel):
    id: int
    branch_id: int
    name: str
    mobile: str = ""
    email: str = ""
    notes: str = ""
    is_active: bool
