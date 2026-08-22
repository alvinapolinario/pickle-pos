from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "mobile", "email", "branch", "is_active")
    list_filter = ("is_active", "branch")
    search_fields = ("name", "mobile", "email")
    list_select_related = ("branch",)
