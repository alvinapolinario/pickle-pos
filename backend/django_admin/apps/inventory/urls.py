from django.urls import path

from apps.inventory import views

app_name = "inventory"

urlpatterns = [
    path("app/stock/", views.stock_list, name="stock_list"),
    path("app/stock/move/", views.movement_create, name="movement_create"),
    path("app/stock/count/", views.stock_count, name="stock_count"),
    path("app/stock-movements/", views.movement_list, name="movement_list"),
]
