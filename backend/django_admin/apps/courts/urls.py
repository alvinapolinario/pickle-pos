from django.urls import path

from apps.courts import views

app_name = "courts"

urlpatterns = [
    path("app/courts/", views.court_list, name="court_list"),
    path("app/courts/new/", views.court_create, name="court_create"),
    path("app/courts/<int:pk>/edit/", views.court_edit, name="court_edit"),
    path("app/court-rates/", views.rate_list, name="rate_list"),
    path("app/court-rates/new/", views.rate_create, name="rate_create"),
    path("app/court-rates/<int:pk>/edit/", views.rate_edit, name="rate_edit"),
    path("app/bookings/", views.booking_list, name="booking_list"),
    path("app/bookings/new/", views.booking_create, name="booking_create"),
    path("app/bookings/<int:pk>/cancel/", views.booking_cancel, name="booking_cancel"),
    path("app/bookings/<int:pk>/refund/", views.booking_refund, name="booking_refund"),
    path("app/court-schedule/", views.court_schedule, name="court_schedule"),
]
