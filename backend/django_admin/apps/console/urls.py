from django.urls import path

from apps.console import views

app_name = "console"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("app/report-sales/", views.report_sales, name="report_sales"),
    path("app/report-inventory/", views.report_inventory, name="report_inventory"),
    path("app/report-courts/", views.report_courts, name="report_courts"),
    path("app/report-financial/", views.report_financial, name="report_financial"),
    path("app/audit/", views.audit_list, name="audit_list"),
    path("app/<slug:page_name>/", views.module_page, name="module"),
]
