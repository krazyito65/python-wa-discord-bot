"""
Production settings for WeakAuras Discord Bot web interface.
"""

import os

from .settings import *  # noqa: F403,F405
from .settings import MIDDLEWARE  # noqa: F401

# Override settings for production
DEBUG = False
ENVIRONMENT = "prod"

# Security settings for production
# sourced from /etc/weakauras-bot/production.env
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost").split(",")

# Force HTTPS in production (temporarily disabled for testing)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Static files production settings
STATIC_ROOT = "/var/www/weakauras-bot/static"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Production logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.getenv(
                "DJANGO_LOG_FILE", "/var/log/weakauras-bot/django.log"
            ),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
        "macros": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
        "servers": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
        "user_stats": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Override secret key from environment
# sourced from /etc/weakauras-bot/production.env
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "DJANGO_SECRET_KEY environment variable must be set for production"
    )

# Database configuration from environment
if os.getenv("DATABASE_URL"):
    import os
    from pathlib import Path as PathLib

    database_url = os.getenv("DATABASE_URL")
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        # Ensure directory exists
        PathLib(db_path).parent.mkdir(parents=True, exist_ok=True)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": db_path,
            }
        }
