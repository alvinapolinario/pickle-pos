from django.contrib import admin

from apps.courts.models import Booking, BookingRefund, Court, CourtRate


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "branch", "status", "hourly_rate", "is_active")
    list_filter = ("status", "is_active", "branch")
    search_fields = ("name", "code")
    list_select_related = ("branch",)


@admin.register(CourtRate)
class CourtRateAdmin(admin.ModelAdmin):
    list_display = ("court", "weekday", "hourly_rate", "is_active")
    list_filter = ("weekday", "is_active")
    list_select_related = ("court",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_number", "court", "start_at", "end_at", "status", "amount", "payment_status")
    list_filter = ("status", "payment_status", "branch")
    search_fields = ("booking_number",)
    list_select_related = ("court", "branch", "customer")
    readonly_fields = ("booking_number", "amount")


@admin.register(BookingRefund)
class BookingRefundAdmin(admin.ModelAdmin):
    list_display = ("refund_number", "booking", "amount", "method", "created_at")
    list_filter = ("method", "branch")
    search_fields = ("refund_number", "booking__booking_number")
    list_select_related = ("booking", "branch")
    readonly_fields = ("refund_number", "amount")
