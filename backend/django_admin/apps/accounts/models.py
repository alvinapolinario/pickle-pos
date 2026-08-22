from django.contrib.auth.models import AbstractUser
from django.db import models


class Permission(models.Model):
    """Application permission used for RBAC."""

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    module = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["module", "code"]

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    """Role grouping permissions (Owner, Manager, Cashier, etc.)."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """Custom user with branch assignment, roles, and optional cashier PIN."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    phone = models.CharField(max_length=30, blank=True)
    pin_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["branch", "is_active"]),
        ]

    @property
    def permission_codes(self) -> set[str]:
        codes: set[str] = set()
        for role in self.roles.prefetch_related("permissions").all():
            codes.update(role.permissions.values_list("code", flat=True))
        return codes


class Device(models.Model):
    """Registered POS terminal authorized for sync and sales."""

    device_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="devices",
    )
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_devices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.device_code} ({self.name})"


class RefreshToken(models.Model):
    """Hashed refresh token for mobile API sessions."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refresh_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
        ]

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone

        return timezone.now() >= self.expires_at


class PosConnection(models.Model):
    """Singleton pairing config so tablets can scan the API URL and key."""

    SINGLETON_PK = 1

    api_key = models.CharField(max_length=80)
    public_base_url = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "POS connection"

    def __str__(self) -> str:
        return self.public_base_url or "POS connection"
