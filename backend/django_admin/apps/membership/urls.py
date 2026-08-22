from django.urls import path

from apps.membership import views

app_name = "membership"

urlpatterns = [
    path("app/memberships/", views.membership_list, name="membership_list"),
    path("app/memberships/tiers/new/", views.tier_create, name="tier_create"),
    path("app/memberships/assign/", views.membership_assign, name="membership_assign"),
    path("app/memberships/<int:pk>/cancel/", views.membership_cancel, name="membership_cancel"),
]
