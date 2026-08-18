from functools import lru_cache

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config.settings import get_settings
from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import AuthenticationError
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
