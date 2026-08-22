from fastapi import APIRouter

from fastapi_api.app.api.v1.auth import router as auth_router
from fastapi_api.app.api.v1.catalog import router as catalog_router
from fastapi_api.app.api.v1.courts import router as courts_router
from fastapi_api.app.api.v1.customers import router as customers_router
from fastapi_api.app.api.v1.devices import router as devices_router
from fastapi_api.app.api.v1.inventory import router as inventory_router
from fastapi_api.app.api.v1.sales import router as sales_router
from fastapi_api.app.api.v1.settings import router as settings_router
from fastapi_api.app.api.v1.shifts import router as shifts_router
from fastapi_api.app.api.v1.sync import router as sync_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(catalog_router, tags=["catalog"])
api_v1_router.include_router(customers_router, tags=["customers"])
api_v1_router.include_router(devices_router, tags=["devices"])
api_v1_router.include_router(inventory_router, tags=["inventory"])
api_v1_router.include_router(shifts_router, tags=["shifts"])
api_v1_router.include_router(sales_router, tags=["sales"])
api_v1_router.include_router(settings_router, tags=["settings"])
api_v1_router.include_router(courts_router, tags=["courts"])
api_v1_router.include_router(sync_router, tags=["sync"])
