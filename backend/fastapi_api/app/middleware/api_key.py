"""Require the POS pairing key on mobile API routes once one exists."""

from asgiref.sync import sync_to_async
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.services.pairing_service import HEADER, PairingService, keys_match

_SKIP_PREFIXES = ("/health", "/api/docs", "/api/openapi.json", "/api/redoc")


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path == prefix or path.startswith(prefix + "/") for prefix in _SKIP_PREFIXES):
            return await call_next(request)

        expected = await sync_to_async(PairingService().current_key, thread_sensitive=True)()
        if not expected:
            return await call_next(request)

        provided = request.headers.get(HEADER) or request.headers.get("x-api-key")
        if not keys_match(provided, expected):
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required. Scan the pairing QR in System Settings."},
            )
        return await call_next(request)
