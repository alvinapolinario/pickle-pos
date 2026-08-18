"""ASGI config for Pickle POS Django admin."""

import os
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent.parent
django_admin_root = backend_root / "django_admin"
for path in (str(backend_root), str(django_admin_root)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.asgi import get_asgi_application

application = get_asgi_application()
