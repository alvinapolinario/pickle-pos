"""Pickle POS FastAPI mobile API."""

from core.django_setup import setup_django

setup_django()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config.settings import get_settings
from fastapi_api.app.api.v1.router import api_v1_router
from fastapi_api.app.middleware.rate_limit import RateLimitMiddleware

settings = get_settings()

app = FastAPI(
    title="Pickle POS API",
    description="Mobile POS and sync API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    payload = {"status": "ok", "service": "fastapi", "database": "ok"}
    try:
        from django.db import connection

        connection.ensure_connection()
    except Exception:
        payload["status"] = "degraded"
        payload["database"] = "error"
        return JSONResponse(payload, status_code=503)
    return payload
