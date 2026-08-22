from decimal import Decimal

from django.db.models import DecimalField, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from fastapi import APIRouter, Depends, HTTPException, status

from apps.inventory.models import InventoryBalance
from apps.products.models import Product
from core.domain.auth import AuthenticatedUser
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.inventory import InventoryBalanceResponse

router = APIRouter()


def _balances_queryset(branch_id: int | None):
    balance = InventoryBalance.objects.filter(
        branch_id=OuterRef("branch_id"),
        product_id=OuterRef("pk"),
    ).values("quantity")[:1]
    queryset = Product.objects.filter(track_inventory=True, is_active=True).select_related("category")
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    return queryset.annotate(
        on_hand=Coalesce(
            Subquery(balance),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        )
    ).order_by("name")


def _to_response(product: Product) -> InventoryBalanceResponse:
    on_hand = product.on_hand
    reorder = product.reorder_level
    return InventoryBalanceResponse(
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        track_inventory=product.track_inventory,
        on_hand=on_hand,
        reorder_level=reorder,
        is_low=reorder > 0 and on_hand <= reorder,
        unit=product.unit,
    )


@router.get("/inventory/balances", response_model=list[InventoryBalanceResponse])
def list_balances(
    branch_id: int | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    resolved_branch = branch_id or current_user.branch_id
    return [_to_response(product) for product in _balances_queryset(resolved_branch)]


@router.get("/inventory/balances/{product_id}", response_model=InventoryBalanceResponse)
def get_balance(
    product_id: int,
    branch_id: int | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    resolved_branch = branch_id or current_user.branch_id
    product = _balances_queryset(resolved_branch).filter(pk=product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Balance not found")
    return _to_response(product)
