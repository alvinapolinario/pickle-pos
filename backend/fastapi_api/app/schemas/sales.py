from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SaleItemIn(BaseModel):
    product_id: int
    quantity: Decimal
    modifier_total: Decimal = Decimal("0.00")


class PaymentIn(BaseModel):
    method: str
    amount: Decimal
    reference: str = ""


class SaleCreateRequest(BaseModel):
    shift_id: int
    items: list[SaleItemIn]
    payments: list[PaymentIn] = Field(default_factory=list)
    discount_amount: Decimal = Decimal("0.00")
    notes: str = ""
    device_id: int | None = None
    client_sale_uuid: UUID | None = None
    customer_id: int | None = None


class HoldSaleRequest(BaseModel):
    shift_id: int
    items: list[SaleItemIn]
    discount_amount: Decimal = Decimal("0.00")
    notes: str = ""
    device_id: int | None = None
    client_sale_uuid: UUID | None = None
    customer_id: int | None = None


class ResumeSaleRequest(BaseModel):
    payments: list[PaymentIn]


class VoidSaleRequest(BaseModel):
    reason: str = ""


class RefundLineIn(BaseModel):
    sale_item_id: int
    quantity: Decimal


class RefundRequest(BaseModel):
    shift_id: int
    lines: list[RefundLineIn]
    method: str = "cash"
    reason: str = ""


class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    sku: str
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_gross: Decimal
    line_discount: Decimal
    line_tax: Decimal
    line_net: Decimal
    quantity_refundable: Decimal | None = None


class PaymentResponse(BaseModel):
    method: str
    amount: Decimal
    reference: str = ""


class SaleResponse(BaseModel):
    id: int
    branch_id: int
    shift_id: int
    cashier_id: int
    transaction_number: str
    receipt_number: str
    client_sale_uuid: UUID
    status: str
    payment_status: str
    gross_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    change_amount: Decimal
    notes: str = ""
    customer_id: int | None = None
    items: list[SaleItemResponse]
    payments: list[PaymentResponse]
    created_at: datetime


class RefundItemResponse(BaseModel):
    sale_item_id: int
    quantity: Decimal
    amount: Decimal


class QuoteRequest(BaseModel):
    items: list[SaleItemIn]
    discount_amount: Decimal = Decimal("0.00")
    branch_id: int | None = None


class QuoteLineResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_gross: Decimal
    line_discount: Decimal
    line_tax: Decimal
    line_net: Decimal


class QuoteResponse(BaseModel):
    gross_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    vat_registered: bool = True
    lines: list[QuoteLineResponse]


class ReceiptLineResponse(BaseModel):
    quantity: Decimal
    name: str
    unit_price: Decimal
    line_net: Decimal


class ReceiptResponse(BaseModel):
    transaction_number: str
    receipt_number: str
    branch_name: str
    cashier: str
    customer: str
    sold_at: str
    net_amount: Decimal
    tax_amount: Decimal
    change_amount: Decimal
    vat_registered: bool = True
    text: str
    lines: list[ReceiptLineResponse]


class RefundResponse(BaseModel):
    id: int
    refund_number: str
    sale_id: int
    amount: Decimal
    method: str
    reason: str = ""
    items: list[RefundItemResponse]
