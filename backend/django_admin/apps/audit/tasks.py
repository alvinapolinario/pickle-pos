from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from core.config.settings import get_settings


@shared_task(name="audit.prune_logs")
def prune_audit_logs(days: int | None = None) -> int:
    from apps.audit.models import AuditLog

    retention = days if days is not None else get_settings().audit_retention_days
    cutoff = timezone.now() - timedelta(days=retention)
    deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
