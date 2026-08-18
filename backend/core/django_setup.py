"""Initialize Django ORM for non-Django entrypoints (FastAPI, Celery)."""

import os
import sys
from pathlib import Path


def setup_django() -> None:
    """Configure Django settings and call django.setup() once."""
    backend_root = Path(__file__).resolve().parent.parent
    django_admin_root = backend_root / "django_admin"

    for path in (str(backend_root), str(django_admin_root)):
        if path not in sys.path:
            sys.path.insert(0, path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()
