from django.contrib import admin

from apps.branches.models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "city", "is_active", "created_at")
    list_filter = ("is_active", "city")
    search_fields = ("code", "name", "city")
