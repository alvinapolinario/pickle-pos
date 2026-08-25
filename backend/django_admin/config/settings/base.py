"""Shared Django settings."""

from pathlib import Path

import environ

from core.config.settings import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Load .env from repo root when running locally
env_file = PROJECT_ROOT.parent / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

core_settings = get_settings()

SECRET_KEY = core_settings.app_secret_key
DEBUG = core_settings.debug
ALLOWED_HOSTS = core_settings.django_allowed_hosts

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.branches",
    "apps.audit",
    "apps.console",
    "apps.products",
    "apps.inventory",
    "apps.purchasing",
    "apps.shifts",
    "apps.customers",
    "apps.sales",
    "apps.sync",
    "apps.courts",
    "apps.expenses",
    "apps.membership",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.console.middleware.ConsoleAccessMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.console.context_processors.console_nav",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=core_settings.django_database_url),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "console:login"
LOGIN_REDIRECT_URL = "console:dashboard"
LOGOUT_REDIRECT_URL = "console:login"
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:7100",
    "http://127.0.0.1:7100",
    "http://localhost",
    "http://187.77.142.118",
    "https://187.77.142.118",
    "http://picklewest.net",
    "https://picklewest.net",
    "http://www.picklewest.net",
    "https://www.picklewest.net",
]

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": core_settings.redis_url,
    }
}

CELERY_BROKER_URL = core_settings.celery_broker_url
CELERY_RESULT_BACKEND = core_settings.celery_result_backend
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "prune-audit-logs-daily": {
        "task": "audit.prune_logs",
        "schedule": 60 * 60 * 24,
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
