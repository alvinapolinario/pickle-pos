from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import core_settings, env

_INSECURE_SECRETS = {
    "change-me",
    "change-me-jwt",
    "change-me-to-a-long-random-string-in-production",
    "change-me-jwt-secret-in-production",
}

if core_settings.app_secret_key in _INSECURE_SECRETS or len(core_settings.app_secret_key) < 32:
    raise ImproperlyConfigured("Set APP_SECRET_KEY to a long random value before running production.")
if core_settings.jwt_secret_key in _INSECURE_SECRETS or len(core_settings.jwt_secret_key) < 32:
    raise ImproperlyConfigured("Set JWT_SECRET_KEY to a long random value before running production.")

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "time=%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
