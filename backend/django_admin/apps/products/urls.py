from django.urls import path

from apps.products import views

app_name = "products"

urlpatterns = [
    path("app/categories/", views.category_list, name="category_list"),
    path("app/categories/new/", views.category_create, name="category_create"),
    path("app/categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("app/categories/<int:pk>/toggle/", views.category_toggle, name="category_toggle"),
    path("app/products/", views.product_list, name="product_list"),
    path("app/products/new/", views.product_create, name="product_create"),
    path("app/products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("app/products/<int:pk>/toggle/", views.product_toggle, name="product_toggle"),
]
