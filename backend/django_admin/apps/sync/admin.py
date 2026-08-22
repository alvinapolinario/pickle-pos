from django.contrib import admin

from apps.sync.models import SyncTransaction


@admin.register(SyncTransaction)
class SyncTransactionAdmin(admin.ModelAdmin):
    list_display = ("device", "client_uuid", "server_entity_type", "server_entity_id", "status", "created_at")
    list_filter = ("status", "server_entity_type")
    search_fields = ("client_uuid",)
    readonly_fields = ("device", "client_uuid", "server_entity_type", "server_entity_id", "status", "created_at")
