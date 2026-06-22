import re
import tempfile
from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
from django.utils.translation import gettext_lazy as _

env = environ.Env()
root_path = environ.Path(__file__) - 2
env_file = Path(root_path(".env"))
if env_file.is_file():
    env.read_env(str(env_file))
BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# Basic Config
# -----------------------------------------------------------------------------
ROOT_URLCONF = "conf.urls"
WSGI_APPLICATION = "conf.wsgi.application"
DEBUG = env.bool("DEBUG", default=False)

# -----------------------------------------------------------------------------
# Time & Language
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Security and Users
# -----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
AUTH_USER_MODEL = "users.CustomUser"
MIN_PASSWORD_LENGTH = env.int("MIN_PASSWORD_LENGTH", default=8)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": MIN_PASSWORD_LENGTH},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -----------------------------------------------------------------------------
# Billing gate (Phase 6 stopgap)
# -----------------------------------------------------------------------------
# Phase 6 not yet built. When False, contact_revealed flips to True automatically
# on inquiry accept (everything is effectively a free trial). Set to True once
# billing is live to enforce the gate. See docs/PHASE_6_BILLING.md.
BILLING_GATE_ENABLED = env.bool("BILLING_GATE_ENABLED", default=False)

# -----------------------------------------------------------------------------
# Databases
# -----------------------------------------------------------------------------
DJANGO_DATABASE_URL = env.db("DATABASE_URL")
DATABASES = {"default": DJANGO_DATABASE_URL}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------------
# Applications configuration
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Unfold must come before django.contrib.admin to override its templates.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # 3rd party apps
    "corsheaders",
    "rest_framework",
    "django_filters",
    "knox",
    "django_celery_beat",
    "drf_spectacular",
    "import_export",
    # local apps
    "apps.users",
    "apps.core",
    "apps.catalog",
    "apps.providers",
    "apps.inquiries",
    "apps.subscriptions",
    "apps.suggestions",
    "apps.reviews",
]

MIDDLEWARE = [
    "apps.core.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [root_path("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [],
        },
    },
]

# -----------------------------------------------------------------------------
# Unfold Admin
# -----------------------------------------------------------------------------
from django.urls import reverse_lazy  # noqa: E402

UNFOLD = {
    "SITE_TITLE": "Sabil Life Admin",
    "SITE_HEADER": "Sabil Life",
    "SITE_SUBHEADER": "Doha family directory",
    "SITE_URL": "/",
    "SITE_SYMBOL": "family_restroom",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "THEME": None,  # None = let user toggle light/dark
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Catalog"),
                "separator": True,
                "items": [
                    {
                        "title": _("Listings"),
                        "icon": "storefront",
                        "link": reverse_lazy(
                            "admin:catalog_listing_changelist"
                        ),
                    },
                    {
                        "title": _("Reviews"),
                        "icon": "rate_review",
                        "link": reverse_lazy(
                            "admin:reviews_review_changelist"
                        ),
                    },
                ],
            },
            {
                "title": _("Providers"),
                "separator": True,
                "items": [
                    {
                        "title": _("Provider profiles"),
                        "icon": "badge",
                        "link": reverse_lazy(
                            "admin:providers_providerprofile_changelist"
                        ),
                    },
                ],
            },
            {
                "title": _("Engagement"),
                "separator": True,
                "items": [
                    {
                        "title": _("Inquiries"),
                        "icon": "forum",
                        "link": reverse_lazy(
                            "admin:inquiries_inquiry_changelist"
                        ),
                    },
                    {
                        "title": _("Subscriptions"),
                        "icon": "school",
                        "link": reverse_lazy(
                            "admin:subscriptions_masterclasssubscription_changelist"
                        ),
                    },
                    {
                        "title": _("Suggestions"),
                        "icon": "tips_and_updates",
                        "link": reverse_lazy(
                            "admin:suggestions_servicesuggestion_changelist"
                        ),
                    },
                ],
            },
            {
                "title": _("Users & Access"),
                "separator": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:users_customuser_changelist"),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": _("Scheduling"),
                "separator": True,
                "items": [
                    {
                        "title": _("Periodic tasks"),
                        "icon": "schedule",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_periodictask_changelist"
                        ),
                    },
                    {
                        "title": _("Crontab schedules"),
                        "icon": "alarm",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_crontabschedule_changelist"
                        ),
                    },
                ],
            },
        ],
    },
    "TABS": [
        {
            "models": ["catalog.listing"],
            "items": [
                {
                    "title": _("All listings"),
                    "link": reverse_lazy("admin:catalog_listing_changelist"),
                },
                {
                    "title": _("Pending"),
                    "link": (
                        lambda request: reverse_lazy(
                            "admin:catalog_listing_changelist"
                        )
                        + "?status__exact=PENDING"
                    ),
                },
                {
                    "title": _("Active"),
                    "link": (
                        lambda request: reverse_lazy(
                            "admin:catalog_listing_changelist"
                        )
                        + "?status__exact=ACTIVE"
                    ),
                },
            ],
        },
    ],
}

# -----------------------------------------------------------------------------
# Rest Framework
# -----------------------------------------------------------------------------
REST_KNOX = {
    "SECURE_HASH_ALGORITHM": "hashlib.sha512",
    "AUTH_TOKEN_CHARACTER_LENGTH": 64,
    "TOKEN_TTL": timedelta(hours=10),
    "USER_SERIALIZER": "apps.users.serializers.UserProfileSerializer",
    "TOKEN_LIMIT_PER_USER": None,
    "AUTO_REFRESH": False,
    "AUTO_REFRESH_MAX_TTL": None,
    "MIN_REFRESH_INTERVAL": 60,
    "AUTH_HEADER_PREFIX": "Bearer",
    "TOKEN_MODEL": "knox.AuthToken",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("knox.auth.TokenAuthentication",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "VERSION_PARAM": "version",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # TODO ⚡ Adjust the throttle rates for your API
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "100/day",
        "user_login": "5/minute",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sabil Life API",
    "DESCRIPTION": (
        "Backend API for Sabil Life — Doha family directory, "
        "providers, inquiries, and commissions."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

if DEBUG:
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

if DEBUG:
    try:
        import django_extensions  # noqa

        INSTALLED_APPS += ["django_extensions"]
    except ImportError:
        pass

    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] += (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    )

    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
        "rest_framework.renderers.BrowsableAPIRenderer",
    )

CORS_ALLOW_ALL_ORIGINS = DEBUG
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}


# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_RESULT_EXTENDED = True

# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

# -----------------------------------------------------------------------------
# Sentry and logging
# -----------------------------------------------------------------------------
# Error reporting
IGNORABLE_404_URLS = [
    re.compile(r"^/apple-touch-icon.*\.png$"),
    re.compile(r"^/favicon\.ico$"),
    re.compile(r"^/robots\.txt$"),
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.core.middleware.RequestIDFilter"},
        "timed_log": {"()": "apps.core.middleware.TimeLogFilter"},
    },
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": (
                "%(asctime)s %(levelname)s %(module)s "
                "%(process)d %(thread)d %(message)s "
                "%(client)s %(request_id)s %(path)s "
                "%(user_id)s %(status_code)d %(response_time).3f "
            ),
        },
        "simple": {
            "format": "%(asctime)s [%(levelname)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

if not DEBUG:
    sentry_dsn = env("SENTRY_DSN", default=None)
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )

# -----------------------------------------------------------------------------
# Static & Media Files
# -----------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [root_path("static")]
STATIC_ROOT = tempfile.mkdtemp() if DEBUG else root_path("static_root")

MEDIA_URL = "/media/"
MEDIA_ROOT = root_path("media_root")

# -----------------------------------------------------------------------------
# Django Debug Toolbar and Django Extensions
# -----------------------------------------------------------------------------
if DEBUG:
    import socket

    INSTALLED_APPS += ["debug_toolbar"]
    INTERNAL_IPS = ["127.0.0.1"]

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
