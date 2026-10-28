import os
import sys
import tempfile
from pathlib import Path

import dj_database_url
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Runtime environment -----------------------------------------------------
APP_ENV = os.environ.get("APP_ENV", "local")  # local | staging | production
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
RUNNING_TESTS = "test" in sys.argv or os.environ.get("DJANGO_TEST") == "1"

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
]

# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
    "rest_framework",
    "common",
    "apps.accounts",
    "apps.analytics",
    "apps.documents",
    "apps.investors",
    "apps.notifications",
    "apps.startups",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database ----------------------------------------------------------------
_db_url = os.environ.get("DATABASE_URL", "")
_use_db_url = _db_url and not (RUNNING_TESTS and not os.environ.get("TEST_USE_DATABASE_URL"))

if _use_db_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _db_url,
            conn_max_age=60,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    # Tests and local dev default to SQLite: fast, no cloud dependency.
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

# --- Authentication ----------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour

# --- i18n / timezone ---------------------------------------------------------
LANGUAGE_CODE = "en"  # admin UI language; DRF messages follow Accept-Language
LANGUAGES = [("en", "English"), ("de", "Deutsch"), ("uk", "Українська")]
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# --- Static files ------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sessions / CSRF (SPA on the same origin via Vite proxy / reverse proxy) -
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:5173"
).split(",")

# --- DRF ---------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "register": "10/hour",
        "password_reset": "5/hour",
        "verify": "20/hour",
        "resend": "5/hour",
    },
}

# --- Celery ------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_ACKS_LATE = True            # don't lose tasks when a worker dies mid-run
CELERY_WORKER_PREFETCH_MULTIPLIER = 1   # long AI calls: don't prefetch
CELERY_TASK_TIME_LIMIT = 600            # hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 570       # soft limit, 30s before hard
CELERY_TASK_ALWAYS_EAGER = True

CELERY_BEAT_SCHEDULE = {
    "purge-expired-decks": {
        "task": "apps.documents.tasks.purge_expired_decks",
        "schedule": 15 * 60,
    },
    "requeue-stuck-jobs": {
        "task": "apps.documents.tasks.requeue_stuck_jobs",
        "schedule": 5 * 60,
    },
    "send-weekly-digests": {
        "task": "apps.investors.tasks.generate_weekly_digests",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Mon 08:00 Europe/Berlin
    },
    "expire-stale-intro-requests": {
        "task": "apps.investors.tasks.expire_stale_intro_requests",
        "schedule": crontab(hour=4, minute=0),
    },
}

# --- E-mail ------------------------------------------------------------------
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    # no credentials (tests, a fresh clone): the letter is printed to the console
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10  # otherwise a hanging SMTP blocks the request indefinitely
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

EMAIL_VERIFY_MAX_AGE = 60 * 60 * 48          # 48 h
PASSWORD_RESET_TIMEOUT = 60 * 60             # 1 h, used by default_token_generator


# --- Legal documents: bump a version to require re-acceptance ---------------
LEGAL_DOCUMENT_VERSIONS = {
    "agb": "2026-10-01",
    "datenschutz": "2026-10-01",
    "investor-status": "2026-10-01",  # text C
}

# --- Pitch deck uploads ------------------------------------------------------
DECK_MAX_MB_DEFAULT = int(os.environ.get("DECK_MAX_MB", "20"))
DECK_MAX_BYTES = DECK_MAX_MB_DEFAULT * 1024 * 1024

# nginx client_max_body_size must be slightly above DECK_MAX_MB.

# --- Storage: Cloudflare R2 (production) or local FS (dev/tests) ------------
USE_R2 = os.environ.get("USE_R2", "true").lower() in ("1", "true", "yes") and not RUNNING_TESTS

CLOUDFLARE_R2_BUCKET = os.environ.get("CLOUDFLARE_R2_BUCKET", "")
CLOUDFLARE_R2_ACCOUNT_ID = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
CLOUDFLARE_R2_ACCESS_KEY = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY", "")
CLOUDFLARE_R2_SECRET_KEY = os.environ.get("CLOUDFLARE_R2_SECRET_KEY", "")

PRIVATE_MEDIA_ROOT = Path(os.environ.get("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))
if RUNNING_TESTS:
    PRIVATE_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="deck-test-"))

if USE_R2:
    _missing = [
        k
        for k in (
            "CLOUDFLARE_R2_BUCKET",
            "CLOUDFLARE_R2_ACCOUNT_ID",
            "CLOUDFLARE_R2_ACCESS_KEY",
            "CLOUDFLARE_R2_SECRET_KEY",
        )
        if not os.environ.get(k)
    ]
    if _missing:
        raise ImproperlyConfigured(f"R2 включён, но не заданы: {', '.join(_missing)}")

    _private_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": CLOUDFLARE_R2_BUCKET,
            "access_key": CLOUDFLARE_R2_ACCESS_KEY,
            "secret_key": CLOUDFLARE_R2_SECRET_KEY,
            "endpoint_url": f"https://{CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            "region_name": "auto",
            "signature_version": "s3v4",
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": 300,
            "file_overwrite": False,
            "location": "pitch-decks",
        },
    }
else:
    _private_storage = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(PRIVATE_MEDIA_ROOT)},
    }

STORAGES = {
    "default": _private_storage,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# --- AI providers (teaser pipeline) -----------------------------------------
# Active provider/model is normally read from PlatformConfig (admin); these are fallbacks.
# Values: "gemini" (paid, with signed AVV) | "gemini_free" | "openai" (with DPA) | "azure_openai"
TEASER_LLM_PROVIDER = os.environ.get("TEASER_LLM_PROVIDER", "gemini")
TEASER_MAX_RETRIES = 2  # retries after an invalid AI answer

# Free tiers have no data processing agreement: only for local development.
AI_ALLOW_FREE_TIER = (
    APP_ENV != "production"
    and os.environ.get("AI_ALLOW_FREE_TIER", "0") == "1"
)

# One AI call must finish well inside CELERY_TASK_SOFT_TIME_LIMIT (see Celery above).
AI_REQUEST_TIMEOUT = float(os.environ.get("AI_REQUEST_TIMEOUT", "60"))

# EUR per 1M tokens, from your price list / contract. Empty -> stored as "unknown".
# Example: {"gpt-4o-mini": {"in": "0.00", "out": "0.00"}}
AI_PRICING_EUR_PER_MTOK: dict = {}

# Google Gemini
TEASER_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEASER_GEMINI_MODEL = os.environ.get("TEASER_GEMINI_MODEL", "gemini-3.8-flash")

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# Azure OpenAI (AZURE_OPENAI_DEPLOYMENT is the deployment name, not the model name)
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "")

# --- Feature flags / guardrails ---------------------------------------------
TEASER_AVV_SIGNED = os.environ.get("TEASER_AVV_SIGNED", "false").lower() in (
    "1",
    "true",
    "yes",
)

if APP_ENV == "production" and TEASER_AVV_SIGNED and not os.environ.get("AVV_CONFIRMED_BY_LEGAL"):
    raise ImproperlyConfigured(
        "TEASER_AVV_SIGNED нельзя включать в production без подтверждения AVV."
        
    )

if "test" in sys.argv or "pytest" in sys.modules:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

if "test" in sys.argv or "pytest" in sys.modules:
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]



