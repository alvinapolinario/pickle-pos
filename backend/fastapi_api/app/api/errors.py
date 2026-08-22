from typing import NoReturn

from fastapi import HTTPException, status

from core.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainError,
    InsufficientStockError,
    NotFoundError,
)


def raise_domain(exc: DomainError) -> NoReturn:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, AuthorizationError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    if isinstance(exc, (ConflictError, InsufficientStockError)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
