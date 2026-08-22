from django.db import IntegrityError
from django.db.models import Q
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.customers.models import Customer
from core.domain.auth import AuthenticatedUser
from core.services.membership_service import MembershipService
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.customers import CustomerCreateRequest, CustomerResponse

router = APIRouter()


def _to_response(customer: Customer) -> CustomerResponse:
    benefits = MembershipService().benefits_for(branch_id=customer.branch_id, customer_id=customer.id)
    return CustomerResponse(
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


def _branch_queryset(current_user: AuthenticatedUser, branch_id: int | None = None):
    queryset = Customer.objects.filter(is_active=True).order_by("name")
    resolved = branch_id or current_user.branch_id
    if resolved:
        queryset = queryset.filter(branch_id=resolved)
    return queryset


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(
    q: str | None = Query(default=None, min_length=1),
    branch_id: int | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    queryset = _branch_queryset(current_user, branch_id)
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(mobile__icontains=q) | Q(email__icontains=q))
    return [_to_response(customer) for customer in queryset[:100]]


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    customer = _branch_queryset(current_user).filter(pk=customer_id).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return _to_response(customer)


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    branch_id = current_user.branch_id
    if not branch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required to add a customer.")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required.")
    mobile = payload.mobile.strip()
    try:
        customer = Customer.objects.create(
            branch_id=branch_id,
            name=name,
            mobile=mobile,
            email=payload.email.strip(),
            notes=payload.notes.strip(),
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with that mobile already exists on this branch.",
        ) from exc
    return _to_response(customer)
