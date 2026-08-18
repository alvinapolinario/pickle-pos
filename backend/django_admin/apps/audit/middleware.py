"""Attach request context for audit logging."""

from __future__ import annotations

import threading
from typing import Any

from django.http import HttpRequest, HttpResponse

_thread_locals = threading.local()


def get_current_request() -> HttpRequest | None:
    return getattr(_thread_locals, "request", None)


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            _thread_locals.request = None


def write_audit_log(
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    user=None,
    previous_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    device=None,
    ip_address: str | None = None,
    reason: str = "",
) -> None:
    from apps.audit.models import AuditLog

    request = get_current_request()
    if user is None and request and request.user.is_authenticated:
        user = request.user
    if ip_address is None and request:
        ip_address = request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        previous_values=previous_values,
        new_values=new_values,
        device=device,
        ip_address=ip_address,
        reason=reason,
    )
