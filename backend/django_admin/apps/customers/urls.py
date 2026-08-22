from django.urls import path

from apps.customers import views

app_name = "customers"

urlpatterns = [
    path("app/customers/", views.customer_list, name="customer_list"),
    path("app/customers/new/", views.customer_create, name="customer_create"),
    path("app/customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("app/customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("app/customers/<int:pk>/toggle/", views.customer_toggle, name="customer_toggle"),
]
