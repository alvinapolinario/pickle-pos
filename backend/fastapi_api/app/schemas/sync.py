from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from fastapi_api.app.schemas.sales import PaymentIn, SaleItemIn


class SyncSaleIn(BaseModel):
    client_sale_uuid: UUID
    shift_id: int
    items: list[SaleItemIn]
    payments: list[PaymentIn] = Field(default_factory=list)
    discount_amount: Decimal = Decimal("0.00")
    notes: str = ""
    hold: bool = False
    customer_id: int | None = None
    client_created_at: datetime | None = None


class SyncPushRequest(BaseModel):
    device_id: int
    sales: list[SyncSaleIn] = Field(default_factory=list)


class SyncSaleResult(BaseModel):
    client_sale_uuid: str
    status: str
    sale_id: int | None = None
    message: str = ""


class SyncPushResponse(BaseModel):
    results: list[SyncSaleResult]


class SyncPullResponse(BaseModel):
    cursor: str
    categories: list[dict]
    products: list[dict]
    prices: list[dict]
    payment_methods: list[str]
    tax: dict
