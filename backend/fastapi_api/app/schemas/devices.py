from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DeviceRegisterRequest(BaseModel):
    device_code: str
    name: str = ""


class DeviceResponse(BaseModel):
    id: int
    device_code: str
    name: str
    branch_id: int
    is_active: bool
    last_seen_at: datetime | None = None
