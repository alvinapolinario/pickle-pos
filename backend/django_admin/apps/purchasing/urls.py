from django.urls import path

from apps.purchasing import views

app_name = "purchasing"

urlpatterns = [
    path("app/suppliers/", views.supplier_list, name="supplier_list"),
    path("app/suppliers/new/", views.supplier_create, name="supplier_create"),
    path("app/suppliers/<int:pk>/edit/", views.supplier_edit, name="supplier_edit"),
    path("app/suppliers/<int:pk>/toggle/", views.supplier_toggle, name="supplier_toggle"),
    path("app/purchase-orders/", views.purchase_order_list, name="purchase_order_list"),
    path("app/purchase-orders/new/", views.purchase_order_create, name="purchase_order_create"),
    path("app/purchase-orders/<int:pk>/edit/", views.purchase_order_edit, name="purchase_order_edit"),
    path("app/purchase-orders/<int:pk>/", views.purchase_order_detail, name="purchase_order_detail"),
    path("app/purchase-orders/<int:pk>/receive/", views.receive_create, name="purchase_order_receive"),
    path("app/purchase-orders/<int:pk>/return/", views.return_create, name="purchase_order_return"),
    path("app/purchase-orders/<int:pk>/cancel/", views.purchase_order_cancel, name="purchase_order_cancel"),
    path("app/receiving/", views.receiving_list, name="receiving_list"),
    path("app/receiving/new/", views.receive_create, name="receive_create"),
]
