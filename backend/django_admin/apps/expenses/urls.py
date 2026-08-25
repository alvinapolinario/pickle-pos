from django.urls import path

from apps.expenses import views

app_name = "expenses"

urlpatterns = [
    path("app/expenses/", views.expense_list, name="expense_list"),
    path("app/expenses/new/", views.expense_create, name="expense_create"),
    path("app/expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("app/expenses/categories/new/", views.category_create, name="category_create"),
]
