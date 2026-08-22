from django.contrib import admin

from apps.sales.models import HeldOrder, Payment, Refund, RefundItem, Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = (
        "product",
        "sku",
        "name",
        "quantity",
        "unit_price",
        "line_gross",
        "line_discount",
        "line_tax",
        "line_net",
        "quantity_refunded",
    )

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("method", "amount", "reference", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_number",
        "receipt_number",
        "branch",
        "cashier",
        "net_amount",
        "status",
        "payment_status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "branch")
    search_fields = ("transaction_number", "receipt_number")
    inlines = [SaleItemInline, PaymentInline]
    readonly_fields = (
        "transaction_number",
        "receipt_number",
        "client_sale_uuid",
        "gross_amount",
        "discount_amount",
        "tax_amount",
        "net_amount",
        "change_amount",
        "created_at",
        "updated_at",
    )


@admin.register(HeldOrder)
class HeldOrderAdmin(admin.ModelAdmin):
    list_display = ("sale", "branch", "created_at")
    list_select_related = ("sale", "branch")


class RefundItemInline(admin.TabularInline):
    model = RefundItem
    extra = 0
    readonly_fields = ("sale_item", "quantity", "amount")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("refund_number", "sale", "amount", "method", "created_at")
    inlines = [RefundItemInline]
    readonly_fields = ("refund_number", "amount", "created_at")
