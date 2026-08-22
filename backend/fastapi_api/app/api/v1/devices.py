from django.utils import timezone
from fastapi import APIRouter, Depends, HTTPException, status

from apps.accounts.models import Device
from core.domain.auth import AuthenticatedUser
from fastapi_api.app.dependencies.auth import get_current_user
from fastapi_api.app.schemas.devices import DeviceRegisterRequest, DeviceResponse

router = APIRouter()


def _to_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        device_code=device.device_code,
        name=device.name,
        branch_id=device.branch_id,
        is_active=device.is_active,
        last_seen_at=device.last_seen_at,
    )


@router.get("/devices", response_model=list[DeviceResponse])
def list_devices(current_user: AuthenticatedUser = Depends(get_current_user)):
    queryset = Device.objects.filter(is_active=True)
    if current_user.branch_id:
        queryset = queryset.filter(branch_id=current_user.branch_id)
    return [_to_response(device) for device in queryset.order_by("name")]


@router.post("/devices/register", response_model=DeviceResponse)
def register_device(
    payload: DeviceRegisterRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    branch_id = current_user.branch_id
    if not branch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required to register a device.")
    code = payload.device_code.strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device code is required.")
    existing = Device.objects.filter(device_code=code).first()
    if existing:
        if existing.branch_id != branch_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device code is registered to another branch.")
        existing.name = payload.name or existing.name
        existing.is_active = True
        existing.last_seen_at = timezone.now()
        existing.save(update_fields=["name", "is_active", "last_seen_at", "updated_at"])
        return _to_response(existing)
    device = Device.objects.create(
        device_code=code,
        name=payload.name or code,
        branch_id=branch_id,
        registered_by_id=current_user.user_id,
        last_seen_at=timezone.now(),
    )
    return _to_response(device)
