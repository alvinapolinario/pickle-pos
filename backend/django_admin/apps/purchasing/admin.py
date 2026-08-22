from django.contrib import admin

from apps.purchasing.models import (
    PurchaseItem,
    PurchaseOrder,
    PurchaseReceipt,
    PurchaseReceiptItem,
    PurchaseReturn,
    PurchaseReturnItem,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "contact_name", "phone", "is_active")
    list_filter = ("is_active", "branch")
    search_fields = ("name", "contact_name", "phone", "email")


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "supplier", "branch", "status", "expected_date", "created_at")
    list_filter = ("status", "branch")
    search_fields = ("po_number", "supplier__name")
    inlines = [PurchaseItemInline]
    readonly_fields = ("po_number", "status", "ordered_at", "created_at", "updated_at")


class PurchaseReceiptItemInline(admin.TabularInline):
    model = PurchaseReceiptItem
    extra = 0
    readonly_fields = ("purchase_item", "product", "quantity", "unit_cost", "inventory_movement_id")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PurchaseReceipt)
class PurchaseReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "purchase_order", "branch", "received_by", "created_at")
    list_filter = ("branch",)
    search_fields = ("receipt_number", "purchase_order__po_number")
    inlines = [PurchaseReceiptItemInline]
    readonly_fields = ("receipt_number", "purchase_order", "branch", "received_by", "notes", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PurchaseReturnItemInline(admin.TabularInline):
    model = PurchaseReturnItem
    extra = 0
    readonly_fields = ("purchase_item", "product", "quantity", "unit_cost", "inventory_movement_id")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PurchaseReturn)
class PurchaseReturnAdmin(admin.ModelAdmin):
    list_display = ("return_number", "purchase_order", "branch", "returned_by", "created_at")
    search_fields = ("return_number", "purchase_order__po_number")
    inlines = [PurchaseReturnItemInline]
    readonly_fields = ("return_number", "purchase_order", "branch", "returned_by", "notes", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
