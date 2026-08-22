from functools import lru_cache

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config.settings import get_settings
from core.domain.auth import AuthenticatedUser, require_permission, user_has_permission
from core.domain.exceptions import AuthenticationError, AuthorizationError
from core.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_redis_client() -> redis.Redis | None:
    settings = get_settings()
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def get_auth_service() -> AuthService:
    return AuthService(settings=get_settings(), redis_client=get_redis_client())


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        return auth_service.decode_access_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc


def require_any_permission(*codes: str):
    def _dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if any(user_has_permission(current_user.permissions, code) for code in codes):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    return _dependency


def enforce_permission(current_user: AuthenticatedUser, required: str) -> None:
    try:
        require_permission(current_user.permissions, required)
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc


def enforce_any_permission(current_user: AuthenticatedUser, *codes: str) -> None:
    if any(user_has_permission(current_user.permissions, code) for code in codes):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def enforce_discount(current_user: AuthenticatedUser, discount_amount) -> None:
    if discount_amount and discount_amount > 0:
        enforce_permission(current_user, "sales.discount")
