from django.contrib import admin

from apps.shifts.models import CashierShift, CashTransaction


class CashTransactionInline(admin.TabularInline):
    model = CashTransaction
    extra = 0
    readonly_fields = ("transaction_type", "amount", "reason", "performed_by", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CashierShift)
class CashierShiftAdmin(admin.ModelAdmin):
    list_display = ("cashier", "branch", "status", "opening_cash", "expected_cash", "actual_cash", "over_short", "opened_at")
    list_filter = ("status", "branch")
    search_fields = ("cashier__username",)
    inlines = [CashTransactionInline]
    readonly_fields = ("expected_cash", "over_short", "opened_at", "closed_at")
