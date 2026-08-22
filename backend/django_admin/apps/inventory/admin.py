from django.contrib import admin

from apps.inventory.models import InventoryBalance, InventoryMovement


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "branch",
        "product",
        "movement_type",
        "quantity",
        "reference_type",
        "performed_by",
    )
    list_filter = ("movement_type", "branch", "reference_type")
    search_fields = ("product__name", "product__sku", "notes")
    list_select_related = ("branch", "product", "performed_by")
    readonly_fields = (
        "branch",
        "product",
        "movement_type",
        "quantity",
        "unit_cost",
        "reference_type",
        "reference_id",
        "performed_by",
        "notes",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventoryBalance)
class InventoryBalanceAdmin(admin.ModelAdmin):
    list_display = ("product", "branch", "quantity", "updated_at")
    list_filter = ("branch",)
    search_fields = ("product__name", "product__sku")
    list_select_related = ("branch", "product")
    readonly_fields = ("branch", "product", "quantity", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
