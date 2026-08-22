from fastapi import APIRouter, Depends

from apps.membership.models import MembershipTier
from core.domain.auth import AuthenticatedUser
from core.services.membership_service import MembershipService
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.membership import MembershipBenefitsResponse, MembershipTierResponse

router = APIRouter()


@router.get("/membership/tiers", response_model=list[MembershipTierResponse])
def list_tiers(current_user: AuthenticatedUser = Depends(get_current_user)):
    queryset = MembershipTier.objects.filter(is_active=True)
    if current_user.branch_id:
        queryset = queryset.filter(branch_id=current_user.branch_id)
    return [
        MembershipTierResponse(
            id=tier.id,
            code=tier.code,
            name=tier.name,
            court_discount_pct=tier.court_discount_pct,
            canteen_discount_pct=tier.canteen_discount_pct,
            priority_booking=tier.priority_booking,
            points_per_peso=tier.points_per_peso,
        )
        for tier in queryset
    ]


@router.get("/membership/customers/{customer_id}", response_model=MembershipBenefitsResponse | None)
def customer_benefits(customer_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    benefits = MembershipService().benefits_for(branch_id=current_user.branch_id, customer_id=customer_id)
    if benefits is None:
        return None
    return MembershipBenefitsResponse(
        tier_code=benefits.tier_code,
        tier_name=benefits.tier_name,
        court_discount_pct=benefits.court_discount_pct,
        canteen_discount_pct=benefits.canteen_discount_pct,
        priority_booking=benefits.priority_booking,
        loyalty_points=benefits.loyalty_points,
    )
