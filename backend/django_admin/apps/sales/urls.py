from django.urls import path

from apps.sales import views

app_name = "sales"

urlpatterns = [
    path("app/sales/", views.sale_list, name="sale_list"),
    path("app/sales/new/", views.sale_create, name="sale_create"),
    path("app/sales/<int:pk>/", views.sale_detail, name="sale_detail"),
    path("app/sales/<int:pk>/receipt/", views.sale_receipt, name="sale_receipt"),
    path("app/sales/<int:pk>/resume/", views.sale_resume, name="sale_resume"),
    path("app/sales/<int:pk>/void/", views.sale_void, name="sale_void"),
    path("app/sales/<int:pk>/refund/", views.sale_refund, name="sale_refund"),
    path("app/transactions/", views.transaction_list, name="transaction_list"),
    path("app/refunds/", views.refund_list, name="refund_list"),
]
