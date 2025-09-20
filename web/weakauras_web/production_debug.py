"""
Production settings with debug mode enabled for troubleshooting.
Use only for temporary debugging - never for normal production operation.
"""

import os

from .production import *  # noqa: F403,F401

# Override DEBUG mode for troubleshooting
DEBUG = True

# CSRF trusted origins for cross-origin requests (inherited from production + debug additions)
CSRF_TRUSTED_ORIGINS = [
    "https://bot.weakauras.wtf",
    "http://bot.weakauras.wtf",  # For development/testing
    "http://localhost:8000",  # For local debugging
    "http://127.0.0.1:8000",  # For local debugging
]

# Enable more verbose logging for debugging
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
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.getenv(
                "DJANGO_LOG_FILE", "/var/log/weakauras-bot/django.log"
            ),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "macros": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "servers": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "user_stats": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "authentication": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "allauth": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Note: To disable secure cookies for debugging CSRF/session issues,
# set SESSION_COOKIE_SECURE = False and CSRF_COOKIE_SECURE = False
