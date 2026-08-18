"""Celery application for background jobs."""

import os
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
django_admin_root = backend_root / "django_admin"
for path in (str(backend_root), str(django_admin_root)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from celery import Celery
from django.conf import settings

app = Celery("pickle_pos")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(name="health.ping")
def ping() -> str:
    return "pong"
