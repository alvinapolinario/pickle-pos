"""Authentication service — shared by Django admin helpers and FastAPI."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from jose import JWTError, jwt
from redis import Redis

from core.config.settings import Settings, get_settings
from core.domain.auth import AuthenticatedUser
from core.domain.exceptions import AuthenticationError
from core.services.security import LoginLockout

if TYPE_CHECKING:
    from apps.accounts.models import Device, RefreshToken, User


class AuthService:
    """Handles login, token issuance, and refresh token rotation."""

    REFRESH_TOKEN_PREFIX = "refresh_token:"

    def __init__(self, settings: Settings | None = None, redis_client: Redis | None = None) -> None:
        self.settings = settings or get_settings()
        self.redis = redis_client
        self.lockout = LoginLockout(
            redis_client,
            max_attempts=self.settings.login_max_attempts,
            window_seconds=self.settings.login_lockout_seconds,
        )

    def authenticate_user(
        self,
        username: str,
        password: str | None = None,
        pin: str | None = None,
        device_code: str | None = None,
    ) -> User:
        from apps.accounts.models import Device, User

        self.lockout.assert_unlocked(username)
        user = authenticate(username=username, password=password) if password else None

        if user is None and pin:
            try:
                candidate = User.objects.get(username=username, is_active=True)
            except User.DoesNotExist as exc:
                self.lockout.record_failure(username)
                raise AuthenticationError("Invalid credentials") from exc

            if not candidate.pin_hash or not check_password(pin, candidate.pin_hash):
                self.lockout.record_failure(username)
                raise AuthenticationError("Invalid credentials")
            user = candidate

        if user is None:
            self.lockout.record_failure(username)
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            raise AuthenticationError("Account is inactive")

        if device_code:
            device = Device.objects.filter(device_code=device_code, is_active=True).first()
            if device is None:
                raise AuthenticationError("Device is not registered or inactive")
            if device.branch_id and user.branch_id and device.branch_id != user.branch_id:
                raise AuthenticationError("Device is not authorized for this branch")
            from django.utils import timezone

            device.last_seen_at = timezone.now()
            device.save(update_fields=["last_seen_at", "updated_at"])

        self.lockout.clear(username)
        return user

    def build_authenticated_user(self, user: User) -> AuthenticatedUser:
        roles = tuple(user.roles.values_list("code", flat=True))
        permissions: set[str] = set()
        for role in user.roles.prefetch_related("permissions").all():
            permissions.update(role.permissions.values_list("code", flat=True))

        return AuthenticatedUser(
            user_id=user.id,
            username=user.username,
            email=user.email or "",
            branch_id=user.branch_id,
            roles=roles,
            permissions=frozenset(permissions),
        )

    def create_access_token(self, user: AuthenticatedUser) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        payload = {
            "sub": str(user.user_id),
            "username": user.username,
            "branch_id": user.branch_id,
            "roles": list(user.roles),
            "permissions": sorted(user.permissions),
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def create_refresh_token(self, user: User, device: Device | None = None) -> tuple[str, RefreshToken]:
        from apps.accounts.models import RefreshToken

        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_token_expire_days)

        with transaction.atomic():
            refresh = RefreshToken.objects.create(
                user=user,
                device=device,
                token_hash=token_hash,
                expires_at=expires_at,
            )

        if self.redis:
            ttl = int(timedelta(days=self.settings.jwt_refresh_token_expire_days).total_seconds())
            try:
                self.redis.set(
                    f"{self.REFRESH_TOKEN_PREFIX}{token_hash}",
                    str(refresh.id),
                    ex=ttl,
                )
            except Exception:
                pass  # Redis is optional; PostgreSQL stores refresh tokens

        return raw_token, refresh

    def rotate_refresh_token(self, raw_token: str) -> tuple[str, str, AuthenticatedUser]:
        from apps.accounts.models import RefreshToken

        token_hash = self._hash_token(raw_token)

        with transaction.atomic():
            refresh = (
                RefreshToken.objects.select_for_update()
                .select_related("user")
                .filter(token_hash=token_hash, revoked_at__isnull=True)
                .first()
            )
            if refresh is None or refresh.is_expired:
                raise AuthenticationError("Invalid or expired refresh token")

            refresh.revoked_at = datetime.now(UTC)
            refresh.save(update_fields=["revoked_at"])

            user = refresh.user
            if not user.is_active:
                raise AuthenticationError("Account is inactive")

            auth_user = self.build_authenticated_user(user)
            access_token = self.create_access_token(auth_user)
            new_refresh_raw, _ = self.create_refresh_token(user, refresh.device)

        return access_token, new_refresh_raw, auth_user

    def revoke_refresh_token(self, raw_token: str) -> None:
        from apps.accounts.models import RefreshToken

        token_hash = self._hash_token(raw_token)
        RefreshToken.objects.filter(token_hash=token_hash, revoked_at__isnull=True).update(
            revoked_at=datetime.now(UTC)
        )
        if self.redis:
            try:
                self.redis.delete(f"{self.REFRESH_TOKEN_PREFIX}{token_hash}")
            except Exception:
                pass

    def decode_access_token(self, token: str) -> AuthenticatedUser:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
        except JWTError as exc:
            raise AuthenticationError("Invalid access token") from exc

        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")

        return AuthenticatedUser(
            user_id=int(payload["sub"]),
            username=payload["username"],
            email=payload.get("email", ""),
            branch_id=payload.get("branch_id"),
            roles=tuple(payload.get("roles", [])),
            permissions=frozenset(payload.get("permissions", [])),
        )

    @staticmethod
    def hash_pin(pin: str) -> str:
        return make_password(pin)

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
