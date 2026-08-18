from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


def health_check(_request):
    return JsonResponse({"status": "ok", "service": "django"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    path("", dashboard, name="dashboard"),
]
