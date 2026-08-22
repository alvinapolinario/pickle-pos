from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    *CSRF_TRUSTED_ORIGINS,
    "http://127.0.0.1",
    "http://10.250.106.91",
    "http://10.250.106.91:7100",
    "http://10.250.106.91:80",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
