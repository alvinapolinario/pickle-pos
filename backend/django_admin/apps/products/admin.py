from django.contrib import admin

from apps.products.models import BranchProductPrice, Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "sort_order", "is_active")
    list_filter = ("is_active", "branch")
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "category",
        "branch",
        "selling_price",
        "unit",
        "tax_status",
        "track_inventory",
        "is_active",
    )
    list_filter = ("is_active", "tax_status", "track_inventory", "branch", "category")
    search_fields = ("sku", "barcode", "name")
    autocomplete_fields = ("category", "branch")
    list_select_related = ("category", "branch")


@admin.register(BranchProductPrice)
class BranchProductPriceAdmin(admin.ModelAdmin):
    list_display = ("product", "branch", "selling_price", "updated_at")
    list_filter = ("branch",)
    search_fields = ("product__name", "product__sku")
    list_select_related = ("product", "branch")
