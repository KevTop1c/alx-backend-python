"""
Pytest configuration file for Django messaging app
"""

import os
import django
from django.conf import settings

# Configure Django settings for pytest
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "messaging_app.settings")

# pylint: disable=unused-argument
def pytest_configure(config):
    """Configure Django for pytest"""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.mysql",
                    "NAME": os.environ.get("DB_NAME", "test_messaging_db"),
                    "USER": os.environ.get("DB_USER", "test_user"),
                    "PASSWORD": os.environ.get("DB_PASSWORD", "test_password"),
                    "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
                    "PORT": os.environ.get("DB_PORT", "3306"),
                    "TEST": {
                        "NAME": "test_messaging_db",
                    },
                }
            },
            INSTALLED_APPS=[
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                # Third party apps
                "rest_framework",
                "rest_framework_simplejwt",
                "django_filters",
                # Local apps
                "chats",
            ],
            SECRET_KEY=os.environ.get("SECRET_KEY", "test-secret-key"),
        )
        django.setup()
