from decimal import Decimal

from pydantic import BaseModel, Field


class BranchSettingsResponse(BaseModel):
    branch_id: int
    branch_name: str
    vat_registered: bool
    tax_rate: Decimal


class BranchSettingsUpdate(BaseModel):
    vat_registered: bool | None = None
    tax_rate: Decimal | None = Field(default=None, ge=0, le=1)
