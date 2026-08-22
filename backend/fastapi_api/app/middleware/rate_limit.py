"""Redis-backed request limits. Off in development unless RATE_LIMIT_ENABLED=true."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config.settings import get_settings
from core.services.security import RateLimiter
from fastapi_api.app.dependencies.auth import get_redis_client

_SKIP_PREFIXES = ("/health", "/api/docs", "/api/openapi.json", "/api/redoc")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.rate_limits_on:
            return await call_next(request)
        path = request.url.path
        if any(path == prefix or path.startswith(prefix + "/") for prefix in _SKIP_PREFIXES):
            return await call_next(request)

        limiter = RateLimiter(get_redis_client())
        ip = _client_ip(request)
        if path.endswith("/login"):
            key, limit = f"rl:login:{ip}", settings.login_rate_limit
        else:
            key, limit = f"rl:api:{ip}", settings.api_rate_limit
        allowed, retry_after = limiter.hit(key, limit=limit, window_seconds=60)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again shortly."},
                headers={"Retry-After": str(retry_after or 60)},
            )
        return await call_next(request)
