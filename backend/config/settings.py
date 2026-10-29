import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
    "rest_framework",
    "apps.accounts",
    "apps.startups",
    "apps.profiles",
    "apps.investors",
    "apps.analytics",
    "apps.documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # Accept-Language -> translated Django/DRF messages
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
        "DIRS": [],
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

# TODO: PostgreSQL for production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

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

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("de", "Deutsch"), ("uk", "Українська")]
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sessions / CSRF (SPA on the same origin via Vite proxy / reverse proxy) ---
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:5173").split(",")

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

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_ACKS_LATE = True              # задача не теряется, если воркер упал посреди обработки
CELERY_WORKER_PREFETCH_MULTIPLIER = 1     # задачи долгие (вызов ШІ), без «захвата» очереди про запас
CELERY_TASK_TIME_LIMIT = 300              # жёсткий лимит, подберите по реальному времени обработки
CELERY_TASK_SOFT_TIME_LIMIT = 270

CELERY_BEAT_SCHEDULE = {
    "purge-expired-decks": {"task": "apps.documents.tasks.purge_expired_decks", "schedule": 15 * 60},
    "requeue-stuck-jobs": {"task": "apps.documents.tasks.requeue_stuck_jobs", "schedule": 5 * 60},
}

TEASER_MAX_RETRIES = 2                    # число повторов вызова ШІ (шаг 7); решает backend
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "fake")
TEASER_LLM_PROVIDER = LLM_PROVIDER
TEASER_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TEASER_GEMINI_MODEL = os.environ.get("TEASER_GEMINI_MODEL", "gemini-3.7-flash")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
# Deprecated alias kept only for backwards compatibility. The source of truth is VendorCompliance.
TEASER_AVV_SIGNED = False
ALLOWED_REGIONS = ["eu", "sweden-central", "west-europe"]

# --- External providers / AVV-DPA registry ---
# All external providers that process personal or business data must be recorded here.
# Until a valid DPA/AVV is signed and the contract is approved, the provider is blocked.
EXTERNAL_PROVIDER_CONFIGS = {
    "azure_openai": {
        "enabled": False,
        "region": "eu",
        "dpa_signed": False,
        "dpa_valid_until": None,
        "no_model_training": False,
        "allowed_data_types": ["ai_prompt", "startup_profile", "investor_profile", "pitch_deck"],
        "notes": "Set to true only after Azure OpenAI DPA/AVV is signed.",
    },
    "postmark": {
        "enabled": False,
        "region": "eu",
        "dpa_signed": False,
        "dpa_valid_until": None,
        "no_model_training": True,
        "allowed_data_types": ["email_address", "user_id", "notification_type"],
        "notes": "Set to true only after Postmark DPA/AVV is signed.",
    },
    "azure_blob": {
        "enabled": False,
        "region": "eu",
        "dpa_signed": False,
        "dpa_valid_until": None,
        "no_model_training": True,
        "allowed_data_types": ["pitch_deck", "document_upload", "startup_profile"],
        "notes": "Set to true only after Azure Blob DPA/AVV is signed.",
    },
}


# --- E-mail ---
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BREVO_API_URL = os.environ.get("BREVO_API_URL", "https://api.brevo.com/v3")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_OPEN_TRACKING_ENABLED = os.environ.get("BREVO_OPEN_TRACKING_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
EMAIL_VERIFY_MAX_AGE = 48 * 60 * 60  # seconds

# --- Legal documents: bump a version to require re-acceptance later ---
LEGAL_DOCUMENT_VERSIONS = {
    "agb": "2026-10-01",
    "datenschutz": "2026-10-01",
    "investor-status": "2026-10-01",  # text C
}

# --- Pitch deck uploads ---
PRIVATE_MEDIA_ROOT = Path(os.environ.get("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))
if "test" in sys.argv:
    PRIVATE_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="deck-test-"))
AZURE_BLOB_ACCOUNT_NAME = os.environ.get("AZURE_BLOB_ACCOUNT_NAME", "")
AZURE_BLOB_ACCOUNT_KEY = os.environ.get("AZURE_BLOB_ACCOUNT_KEY", "")
AZURE_BLOB_CONTAINER_NAME = os.environ.get("AZURE_BLOB_CONTAINER_NAME", "startshare-private")
AZURE_BLOB_ENDPOINT_SUFFIX = os.environ.get("AZURE_BLOB_ENDPOINT_SUFFIX", "core.windows.net")
DECK_MAX_BYTES = int(os.environ.get("DECK_MAX_MB", "20")) * 1024 * 1024
# Also set client_max_body_size (nginx) a bit above DECK_MAX_BYTES.

if "test" in sys.argv:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only
