"""
Django settings for shopproject (production-ready)
Django 5.2.x
"""

from pathlib import Path
import os
import dj_database_url

# ------------------------------------------------------
# Paths
# ------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Optional local overrides (e.g., env.py for local dev)
if os.path.isfile(BASE_DIR / "env.py"):
    import env  # type: ignore

# ------------------------------------------------------
# Core / Debug
# ------------------------------------------------------
DEBUG = str(os.environ.get("DJANGO_DEBUG", "false")).lower() == "true"

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY and not DEBUG:
    raise RuntimeError("SECRET_KEY is required in production.")

# Comma-separated: e.g. "yourdomain.com,.yourdomain.com,project.herokuapp.com"
_allowed = os.environ.get(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,.herokuapp.com"
)
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]

# ------------------------------------------------------
# Applications
# ------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    "cloudinary",
    "cloudinary_storage",
    "django_summernote",

    "shop",
]

SITE_ID = 1

# ------------------------------------------------------
# Middleware
# ------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # static files in prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",   # enables APPEND_SLASH
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "shopproject.urls"

# ------------------------------------------------------
# Templates
# ------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.i18n",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "shopproject.wsgi.application"

# ------------------------------------------------------
# Database
# ------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

# ------------------------------------------------------
# Password validators
# ------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------
# Internationalization
# ------------------------------------------------------
LANGUAGE_CODE = "de"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("de", "Deutsch"),
    ("ar", "العربية"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# ------------------------------------------------------
# Static & Media
# ------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: hashed & compressed static files in prod
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media via Cloudinary
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# ------------------------------------------------------
# Trailing slashes
# ------------------------------------------------------
# If a URL is missing the trailing slash, CommonMiddleware will redirect /path -> /path/
APPEND_SLASH = True

# ------------------------------------------------------
# Security / HTTPS
# ------------------------------------------------------
# If you’re behind a proxy (Heroku, nginx), honor X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Respect env for CSRF trusted origins. Example:
# CSRF_TRUSTED_ORIGINS="https://yourdomain.com,https://project.herokuapp.com"
_csrf_env = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = _csrf_env
else:
    # Derive a basic default (HTTPS only, skip localhost)
    CSRF_TRUSTED_ORIGINS = [
        f"https://{h.lstrip('.')}" for h in ALLOWED_HOSTS
        if h not in {"localhost", "127.0.0.1"}
    ]

# Baseline secure headers (these are safe for both envs)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Django uses the modern Referrer-Policy header:
SECURE_REFERRER_POLICY = "same-origin"

# ---- ENV-SPECIFIC: Production vs Local Dev ----
if DEBUG:
    # Local development: NEVER force HTTPS or set HSTS
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    # Production: force HTTPS + HSTS
    SECURE_SSL_REDIRECT = str(os.environ.get("SECURE_SSL_REDIRECT", "true")).lower() == "true"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ------------------------------------------------------
# Logging (simple, production-safe)
# ------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO" if not DEBUG else "DEBUG"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

# ------------------------------------------------------
# Default PK
# ------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
