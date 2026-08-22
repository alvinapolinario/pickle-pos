from django.contrib import admin

from apps.branches.models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "city", "vat_registered", "is_active", "created_at")
    list_filter = ("is_active", "vat_registered", "city")
    search_fields = ("code", "name", "city")
