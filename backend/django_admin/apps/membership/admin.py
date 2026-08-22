from django.contrib import admin

from apps.membership.models import LoyaltyTransaction, Membership, MembershipTier


@admin.register(MembershipTier)
class MembershipTierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "branch", "court_discount_pct", "canteen_discount_pct", "is_active")
    list_filter = ("is_active", "branch")
    search_fields = ("name", "code")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("customer", "tier", "status", "started_on", "expires_on", "branch")
    list_filter = ("status", "tier", "branch")
    search_fields = ("customer__name", "tier__name")


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "customer", "points", "kind", "source_type", "source_id")
    list_filter = ("kind", "source_type")
    search_fields = ("customer__name",)
    readonly_fields = ("customer", "branch", "points", "kind", "source_type", "source_id", "notes", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
