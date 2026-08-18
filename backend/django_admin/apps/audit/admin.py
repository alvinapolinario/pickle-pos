from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "user", "created_at")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("entity_id", "user__username", "action")
    readonly_fields = (
        "user",
        "action",
        "entity_type",
        "entity_id",
        "previous_values",
        "new_values",
        "device",
        "ip_address",
        "reason",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
