"""
Django settings for config project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-6k%$1(u@@udte#vit(!3+_u$$=#$ei^_c^(9)9)tqn3pobgnki",
)

CELERY_BEAT_SCHEDULE = {
    "sync-timetables-daily": {
        "task": "apps.trains.tasks.sync_all_timetables",
        "schedule": crontab(minute=0, hour=2),
    },
}

if os.getenv("ENABLE_LIVE_SYNC", "false").lower() == "true":
    CELERY_BEAT_SCHEDULE["sync-live-trains"] = {
        "task": "apps.trains.tasks.sync_relevant_live_trains",
        "schedule": crontab(minute=0, hour="*/3"),
    }


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Allowed hosts
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

# CSRF trusted origins
csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in csrf_origins.split(",")
    if origin.strip()
]

# Database configuration
db_config = dj_database_url.config(
    default=os.getenv("DATABASE_URL")
)
if db_config:
    db_config.setdefault("OPTIONS", {})
    if "postgresql" in db_config.get("ENGINE", ""):
        db_config["OPTIONS"]["options"] = "-c timezone=Asia/Kolkata"

DATABASES = {
    "default": db_config
}

use_local_redis = os.getenv("USE_LOCAL_REDIS", "False").lower() in ("true", "1", "yes")
if use_local_redis:
    raw_redis_url = os.getenv("LOCAL_REDIS_URL", "redis://redis:6379/0")
else:
    raw_redis_url = (
        os.getenv("REDIS_URL")
        or os.getenv("CELERY_BROKER_URL")
        or os.getenv("REDIS_TLS_URL")
        or "redis://redis:6379/0"
    ).strip().strip("\"'")

CELERY_BROKER_URL = raw_redis_url
CELERY_RESULT_BACKEND = raw_redis_url

# If using hosted/cloud Redis with SSL (rediss://)
if CELERY_BROKER_URL.startswith("rediss://"):
    import ssl
    CELERY_BROKER_USE_SSL = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }
    CELERY_REDIS_BACKEND_USE_SSL = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }

CELERY_TASK_RESULT_EXPIRES = 3600



# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "rest_framework",

    # Local apps
    "apps.assets",
    "apps.blocks",
    "apps.corridors",
    "apps.maintenance",
    "apps.trains",
]

# Check optional third-party apps
try:
    import corsheaders  # noqa: F401
    INSTALLED_APPS.insert(0, "corsheaders")
    has_cors = True
except ImportError:
    has_cors = False

try:
    import whitenoise  # noqa: F401
    has_whitenoise = True
except ImportError:
    has_whitenoise = False


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

if has_whitenoise:
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")

MIDDLEWARE.append("django.contrib.sessions.middleware.SessionMiddleware")

if has_cors:
    MIDDLEWARE.append("corsheaders.middleware.CorsMiddleware")

MIDDLEWARE.extend([
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
])

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True

CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ENABLE_UTC = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if has_whitenoise:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


# REST Framework configuration
REST_FRAMEWORK = {
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
}


# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "True").lower() in ("true", "1", "yes")
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_origins_env:
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in cors_origins_env.split(",")
        if origin.strip()
    ]

CORS_ALLOW_CREDENTIALS = True


# Email
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
