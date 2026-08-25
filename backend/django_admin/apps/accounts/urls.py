from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("app/users/", views.user_list, name="user_list"),
    path("app/users/new/", views.user_create, name="user_create"),
    path("app/users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("app/users/<int:pk>/toggle/", views.user_toggle, name="user_toggle"),
    path("app/cashiers/", views.user_list, {"default_role": "cashier"}, name="cashier_list"),
]
