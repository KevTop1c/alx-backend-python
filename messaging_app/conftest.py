"""
Pytest configuration file for Django messaging app
"""

import pytest
import django
from django.conf import settings


# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
# pylint: disable=import-outside-toplevel
# pylint: disable=invalid-name
# Configure Django before running tests
def pytest_configure(config):
    """Setup Django configuration for tests"""
    if not settings.configured:
        settings.configure()
    django.setup()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for pytest-django
    Ensures database is created and migrations are run
    """
    with django_db_blocker.unblock():
        from django.core.management import call_command

        # Run migrations
        call_command("migrate", "--noinput")


@pytest.fixture
def sample_user(db):
    """
    Fixture to create a sample user for testing
    Uses the custom User model from chats app
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        phone_number="+1234567890",
        first_name="Test",
        last_name="User",
    )
    return user
