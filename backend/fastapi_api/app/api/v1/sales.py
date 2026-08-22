from fastapi import APIRouter, Depends, Query

from apps.sales.models import Sale
from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import DomainError, NotFoundError
from core.services.pricing_service import PricingService, QuoteLineInput
from core.services.receipt_service import ReceiptService
from core.services.sale_service import PaymentInput, RefundLineInput, SaleLineInput, SaleService
from fastapi_api.app.api.errors import raise_domain
from fastapi_api.app.dependencies.auth import (
    enforce_any_permission,
    enforce_discount,
    enforce_permission,
    get_current_user,
)
from fastapi_api.app.schemas.sales import (
    HoldSaleRequest,
    QuoteRequest,
    QuoteResponse,
    ReceiptResponse,
    RefundRequest,
    RefundResponse,
    ResumeSaleRequest,
    SaleCreateRequest,
    SaleItemResponse,
    SaleResponse,
    VoidSaleRequest,
)

router = APIRouter()


def _sale_response(sale) -> SaleResponse:
    return SaleResponse(
        id=sale.id,
        branch_id=sale.branch_id,
        shift_id=sale.shift_id,
        cashier_id=sale.cashier_id,
        transaction_number=sale.transaction_number,
        receipt_number=sale.receipt_number,
        client_sale_uuid=sale.client_sale_uuid,
        status=sale.status,
        payment_status=sale.payment_status,
        gross_amount=sale.gross_amount,
        discount_amount=sale.discount_amount,
        tax_amount=sale.tax_amount,
        net_amount=sale.net_amount,
        change_amount=sale.change_amount,
        notes=sale.notes,
        customer_id=sale.customer_id,
        items=[
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                sku=item.sku,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_gross=item.line_gross,
                line_discount=item.line_discount,
                line_tax=item.line_tax,
                line_net=item.line_net,
                quantity_refundable=item.quantity_refundable,
            )
            for item in sale.items.all()
        ],
        payments=[
            {"method": payment.method, "amount": payment.amount, "reference": payment.reference}
            for payment in sale.payments.all()
        ],
        created_at=sale.created_at,
    )


def _lines(items) -> list[SaleLineInput]:
    return [
        SaleLineInput(item.product_id, item.quantity, item.modifier_total) for item in items
    ]


def _payments(payments) -> list[PaymentInput]:
    return [PaymentInput(payment.method, payment.amount, payment.reference) for payment in payments]


@router.post("/sales", response_model=SaleResponse)
def create_sale(
    payload: SaleCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_permission(current_user, "sales.create")
    enforce_discount(current_user, payload.discount_amount)
    try:
        sale = SaleService().create_sale(
            shift_id=payload.shift_id,
            cashier_id=current_user.user_id,
            lines=_lines(payload.items),
            payments=_payments(payload.payments),
            discount_amount=payload.discount_amount,
            notes=payload.notes,
            device_id=payload.device_id,
            client_sale_uuid=payload.client_sale_uuid,
            customer_id=payload.customer_id,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _sale_response(sale)


@router.post("/sales/hold", response_model=SaleResponse)
def hold_sale(
    payload: HoldSaleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_permission(current_user, "sales.create")
    enforce_discount(current_user, payload.discount_amount)
    try:
        sale = SaleService().create_sale(
            shift_id=payload.shift_id,
            cashier_id=current_user.user_id,
            lines=_lines(payload.items),
            payments=[],
            discount_amount=payload.discount_amount,
            notes=payload.notes,
            device_id=payload.device_id,
            client_sale_uuid=payload.client_sale_uuid,
            hold=True,
            customer_id=payload.customer_id,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _sale_response(sale)


@router.post("/sales/hold/{sale_id}/resume", response_model=SaleResponse)
def resume_sale(
    sale_id: int,
    payload: ResumeSaleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_permission(current_user, "sales.create")
    if payload.discount_amount:
        enforce_discount(current_user, payload.discount_amount)
    try:
        sale = SaleService().resume_sale(
            sale_id=sale_id,
            cashier_id=current_user.user_id,
            payments=_payments(payload.payments),
            lines=_lines(payload.items) if payload.items is not None else None,
            discount_amount=payload.discount_amount,
            customer_id=payload.customer_id,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _sale_response(sale)


@router.post("/sales/quote", response_model=QuoteResponse)
def quote_sale(
    payload: QuoteRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_discount(current_user, payload.discount_amount)
    branch_id = payload.branch_id or current_user.branch_id
    if not branch_id:
        raise_domain(DomainError("Branch is required."))
    try:
        quote = PricingService().quote(
            branch_id=branch_id,
            lines=[QuoteLineInput(line.product_id, line.quantity, line.modifier_total) for line in payload.items],
            discount_amount=payload.discount_amount,
            customer_id=payload.customer_id,
        )
    except DomainError as exc:
        raise_domain(exc)
    return QuoteResponse(
        gross_amount=quote.gross_amount,
        discount_amount=quote.discount_amount,
        tax_amount=quote.tax_amount,
        net_amount=quote.net_amount,
        vat_registered=quote.config.vat_registered,
        lines=[
            {
                "product_id": line.product_id,
                "sku": line.sku,
                "name": line.name,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "line_gross": line.line_gross,
                "line_discount": line.line_discount,
                "line_tax": line.line_tax,
                "line_net": line.line_net,
            }
            for line in quote.lines
        ],
    )


@router.get("/sales", response_model=list[SaleResponse])
def list_sales(
    status: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    queryset = Sale.objects.prefetch_related("items", "payments").order_by("-created_at")
    if current_user.branch_id:
        queryset = queryset.filter(branch_id=current_user.branch_id)
    if status:
        queryset = queryset.filter(status=status)
    if q:
        queryset = queryset.filter(transaction_number__icontains=q)
    return [_sale_response(sale) for sale in queryset[:100]]


@router.get("/sales/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    sale = (
        Sale.objects.prefetch_related("items", "payments")
        .filter(pk=sale_id)
        .first()
    )
    if sale is None:
        raise_domain(NotFoundError("Sale not found."))
    if current_user.branch_id and sale.branch_id != current_user.branch_id:
        raise_domain(NotFoundError("Sale not found."))
    return _sale_response(sale)


@router.get("/sales/{sale_id}/receipt", response_model=ReceiptResponse)
def get_receipt(
    sale_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    sale = (
        Sale.objects.select_related("branch", "cashier", "customer")
        .prefetch_related("items", "payments")
        .filter(pk=sale_id)
        .first()
    )
    if sale is None or (current_user.branch_id and sale.branch_id != current_user.branch_id):
        raise_domain(NotFoundError("Sale not found."))
    receipt = ReceiptService().build(sale)
    return ReceiptResponse(
        transaction_number=receipt.transaction_number,
        receipt_number=receipt.receipt_number,
        branch_name=receipt.branch_name,
        branch_address=receipt.branch_address,
        cashier=receipt.cashier,
        customer=receipt.customer,
        sold_at=receipt.sold_at,
        net_amount=receipt.net_amount,
        tax_amount=receipt.tax_amount,
        change_amount=receipt.change_amount,
        vat_registered=receipt.vat_registered,
        status=receipt.status,
        text=receipt.text,
        qr_payload=receipt.receipt_number,
        lines=[
            {
                "quantity": line.quantity,
                "name": line.name,
                "unit_price": line.unit_price,
                "line_net": line.line_net,
            }
            for line in receipt.lines
        ],
    )


@router.post("/sales/{sale_id}/void", response_model=SaleResponse)
def void_sale(
    sale_id: int,
    payload: VoidSaleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_any_permission(current_user, "sales.void", "sales.create")
    try:
        sale = (
            Sale.objects.select_related("branch")
            .filter(pk=sale_id)
            .first()
        )
        if sale is None or (current_user.branch_id and sale.branch_id != current_user.branch_id):
            raise_domain(NotFoundError("Sale not found."))
        SaleService.verify_void_passcode(sale.branch, payload.passcode)
        sale = SaleService().void_sale(
            sale_id=sale_id,
            cashier_id=current_user.user_id,
            reason=payload.reason,
        )
    except DomainError as exc:
        raise_domain(exc)
    return _sale_response(sale)


@router.post("/sales/{sale_id}/refund", response_model=RefundResponse)
def refund_sale(
    sale_id: int,
    payload: RefundRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_permission(current_user, "sales.refund")
    try:
        sale = (
            Sale.objects.select_related("branch")
            .filter(pk=sale_id)
            .first()
        )
        if sale is None or (current_user.branch_id and sale.branch_id != current_user.branch_id):
            raise_domain(NotFoundError("Sale not found."))
        SaleService.verify_void_passcode(sale.branch, payload.passcode)
        refund = SaleService().refund_sale(
            sale_id=sale_id,
            shift_id=payload.shift_id,
            cashier_id=current_user.user_id,
            lines=[RefundLineInput(line.sale_item_id, line.quantity) for line in payload.lines],
            method=payload.method,
            reason=payload.reason,
        )
    except DomainError as exc:
        raise_domain(exc)
    return RefundResponse(
        id=refund.id,
        refund_number=refund.refund_number,
        sale_id=refund.sale_id,
        amount=refund.amount,
        method=refund.method,
        reason=refund.reason,
        items=[
            {"sale_item_id": item.sale_item_id, "quantity": item.quantity, "amount": item.amount}
            for item in refund.items.all()
        ],
    )
