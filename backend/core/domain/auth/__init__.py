"""Authentication domain services."""

from dataclasses import dataclass

from core.domain.exceptions import AuthorizationError


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    username: str
    email: str
    branch_id: int | None
    roles: tuple[str, ...]
    permissions: frozenset[str]


TABLET_ONLY_ROLE_CODES = frozenset({"cashier"})


def user_can_use_console(user) -> bool:
    """Cashiers use the POS tablet. Owner/Administrator/Manager and staff use the web console."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    codes = set(user.roles.values_list("code", flat=True))
    if not codes:
        return False
    return bool(codes - TABLET_ONLY_ROLE_CODES)


def user_has_permission(user_permissions: frozenset[str], required: str) -> bool:
    if "*" in user_permissions:
        return True
    if required in user_permissions:
        return True
    module = required.split(".")[0]
    return f"{module}.*" in user_permissions


def require_permission(user_permissions: frozenset[str], required: str) -> None:
    if not user_has_permission(user_permissions, required):
        raise AuthorizationError("Permission denied for this operation")
