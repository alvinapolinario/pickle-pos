from fastapi import APIRouter, Depends, Query

from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import DomainError
from core.services.sale_service import PaymentInput, SaleLineInput
from core.services.sync_service import SyncSaleInput, SyncService
from fastapi_api.app.api.errors import raise_domain
from fastapi_api.app.dependencies.auth import enforce_discount, enforce_permission, get_current_user
from fastapi_api.app.schemas.sync import SyncPushRequest, SyncPushResponse, SyncPullResponse, SyncSaleResult

router = APIRouter()


@router.post("/sync/push", response_model=SyncPushResponse)
def sync_push(
    payload: SyncPushRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    enforce_permission(current_user, "sales.create")
    for item in payload.sales:
        enforce_discount(current_user, item.discount_amount)
    sales = [
        SyncSaleInput(
            client_sale_uuid=item.client_sale_uuid,
            shift_id=item.shift_id,
            items=[
                SaleLineInput(line.product_id, line.quantity, line.modifier_total) for line in item.items
            ],
            payments=[PaymentInput(pay.method, pay.amount, pay.reference) for pay in item.payments],
            discount_amount=item.discount_amount,
            notes=item.notes,
            hold=item.hold,
            customer_id=item.customer_id,
        )
        for item in payload.sales
    ]
    results = SyncService().push_sales(
        cashier_id=current_user.user_id,
        device_id=payload.device_id,
        sales=sales,
    )
    return SyncPushResponse(
        results=[
            SyncSaleResult(
                client_sale_uuid=row.client_sale_uuid,
                status=row.status,
                sale_id=row.sale_id,
                message=row.message,
            )
            for row in results
        ]
    )


@router.get("/sync/pull", response_model=SyncPullResponse)
def sync_pull(
    since: str | None = Query(default=None),
    branch_id: int | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        payload = SyncService().pull(branch_id=branch_id or current_user.branch_id, since=since)
    except DomainError as exc:
        raise_domain(exc)
    return payload
