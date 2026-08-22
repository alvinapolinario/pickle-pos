from fastapi import APIRouter, Depends, HTTPException, status

from apps.branches.models import Branch
from core.domain.auth import AuthenticatedUser
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.settings import BranchSettingsResponse, BranchSettingsUpdate

router = APIRouter()


def _branch_for(user: AuthenticatedUser) -> Branch:
    if user.branch_id:
        branch = Branch.objects.filter(pk=user.branch_id).first()
    else:
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
    if branch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return branch


def _response(branch: Branch) -> BranchSettingsResponse:
    return BranchSettingsResponse(
        branch_id=branch.id,
        branch_name=branch.name,
        vat_registered=branch.vat_registered,
        tax_rate=branch.tax_rate,
        memberships_enabled=branch.memberships_enabled,
    )


@router.get("/settings", response_model=BranchSettingsResponse)
def get_settings(current_user: AuthenticatedUser = Depends(get_current_user)):
    return _response(_branch_for(current_user))


@router.patch("/settings", response_model=BranchSettingsResponse)
def update_settings(
    payload: BranchSettingsUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    branch = _branch_for(current_user)
    if payload.vat_registered is not None:
        branch.vat_registered = payload.vat_registered
    if payload.tax_rate is not None:
        branch.tax_rate = payload.tax_rate
    if payload.memberships_enabled is not None:
        branch.memberships_enabled = payload.memberships_enabled
    branch.save(update_fields=["vat_registered", "tax_rate", "memberships_enabled", "updated_at"])
    return _response(branch)
