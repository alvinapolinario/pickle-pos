from django.urls import path

from apps.shifts import views

app_name = "shifts"

urlpatterns = [
    path("app/shifts/", views.shift_list, name="shift_list"),
    path("app/shifts/open/", views.shift_open, name="shift_open"),
    path("app/shifts/<int:pk>/", views.shift_detail, name="shift_detail"),
    path("app/shifts/<int:pk>/cash-in/", views.shift_cash_in, name="shift_cash_in"),
    path("app/shifts/<int:pk>/cash-out/", views.shift_cash_out, name="shift_cash_out"),
    path("app/shifts/<int:pk>/close/", views.shift_close, name="shift_close"),
]
