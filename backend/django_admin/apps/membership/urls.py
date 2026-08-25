from django.urls import path

from apps.membership import views

app_name = "membership"

urlpatterns = [
    path("app/memberships/", views.membership_list, name="membership_list"),
    path("app/memberships/tiers/new/", views.tier_create, name="tier_create"),
    path("app/memberships/tiers/<int:pk>/edit/", views.tier_edit, name="tier_edit"),
    path("app/memberships/assign/", views.membership_assign, name="membership_assign"),
    path("app/memberships/<int:pk>/edit/", views.membership_edit, name="membership_edit"),
    path("app/memberships/<int:pk>/cancel/", views.membership_cancel, name="membership_cancel"),
]
