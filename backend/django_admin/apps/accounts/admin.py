from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import Device, Permission, RefreshToken, Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")
    filter_horizontal = ("permissions",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "module")
    search_fields = ("name", "code", "module")
    list_filter = ("module",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "branch", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "branch", "roles")
    search_fields = ("username", "email", "first_name", "last_name")
    filter_horizontal = ("roles", "groups", "user_permissions")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Pickle POS", {"fields": ("branch", "roles", "pin_hash", "phone")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Pickle POS", {"fields": ("branch", "roles", "phone")}),
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_code", "name", "branch", "is_active", "last_seen_at")
    list_filter = ("is_active", "branch")
    search_fields = ("device_code", "name")


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "device", "expires_at", "revoked_at", "created_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__username", "token_hash")
    readonly_fields = ("token_hash", "created_at")
