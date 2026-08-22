from django.db.models import Q
from fastapi import APIRouter, Depends, Query

from apps.customers.models import Customer
from core.domain.auth import AuthenticatedUser
from core.services.membership_service import MembershipService
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.customers import CustomerResponse

router = APIRouter()


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(
    q: str | None = Query(default=None, min_length=1),
    branch_id: int | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    queryset = Customer.objects.filter(is_active=True).order_by("name")
    resolved = branch_id or current_user.branch_id
    if resolved:
        queryset = queryset.filter(branch_id=resolved)
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(mobile__icontains=q) | Q(email__icontains=q))
    service = MembershipService()
    payload = []
    for customer in queryset[:100]:
        benefits = service.benefits_for(branch_id=customer.branch_id, customer_id=customer.id)
        payload.append(
            CustomerResponse(
                id=customer.id,
                branch_id=customer.branch_id,
                name=customer.name,
                mobile=customer.mobile,
                email=customer.email,
                notes=customer.notes,
                is_active=customer.is_active,
                loyalty_points=customer.loyalty_points,
                membership_tier=benefits.tier_code if benefits else "",
                canteen_discount_pct=benefits.canteen_discount_pct if benefits else 0,
                court_discount_pct=benefits.court_discount_pct if benefits else 0,
            )
        )
    return payload
