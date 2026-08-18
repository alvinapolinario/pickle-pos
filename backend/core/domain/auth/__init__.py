"""Authentication domain services."""

from dataclasses import dataclass

from core.domain.exceptions import AuthenticationError


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    username: str
    email: str
    branch_id: int | None
    roles: tuple[str, ...]
    permissions: frozenset[str]


def user_has_permission(user_permissions: frozenset[str], required: str) -> bool:
    if "*" in user_permissions:
        return True
    if required in user_permissions:
        return True
    module = required.split(".")[0]
    return f"{module}.*" in user_permissions


def require_permission(user_permissions: frozenset[str], required: str) -> None:
    if not user_has_permission(user_permissions, required):
        raise AuthenticationError("Permission denied for this operation")
