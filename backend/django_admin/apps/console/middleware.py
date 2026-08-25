"""Block tablet-only cashiers from the web console."""

from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from core.domain.auth import user_can_use_console

_EXEMPT_PREFIXES = (
    "/login/",
    "/logout/",
    "/health/",
    "/static/",
    "/media/",
    "/django-admin/",
)


class ConsoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            return self.get_response(request)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user_can_use_console(user):
            logout(request)
            messages.error(
                request,
                "This account is for the POS tablet. Sign in to the console with an Owner or Administrator account.",
            )
            return redirect("console:login")
        return self.get_response(request)
