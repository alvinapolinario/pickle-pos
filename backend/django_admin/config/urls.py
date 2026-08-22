from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(_request):
    from django.db import connection

    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok", "service": "django", "database": "ok"})
    except Exception:
        return JsonResponse(
            {"status": "degraded", "service": "django", "database": "error"},
            status=503,
        )


urlpatterns = [
    path("health/", health_check, name="health"),
    path("django-admin/", admin.site.urls),
    path("", include("apps.products.urls")),
    path("", include("apps.inventory.urls")),
    path("", include("apps.purchasing.urls")),
    path("", include("apps.shifts.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.sales.urls")),
    path("", include("apps.courts.urls")),
    path("", include("apps.expenses.urls")),
    path("", include("apps.console.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

