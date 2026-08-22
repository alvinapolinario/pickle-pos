from django.contrib import admin

from apps.expenses.models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "is_active")
    list_filter = ("is_active", "branch")
    search_fields = ("name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("incurred_on", "category", "amount", "branch", "notes")
    list_filter = ("category", "branch")
    search_fields = ("notes",)
    list_select_related = ("category", "branch")
