"""
Sample test file for the messaging app
"""

import pytest


# pylint: disable=invalid-name
# pylint: disable=import-outside-toplevel
# Pytest-style tests
@pytest.mark.unit
def test_python_basics():
    """Test basic Python functionality"""
    assert 2 + 2 == 4
    assert "hello".upper() == "HELLO"
    assert [1, 2, 3] == [1, 2, 3]


@pytest.mark.unit
def test_string_operations():
    """Test string operations"""
    test_string = "GitHub Actions"
    assert test_string.lower() == "github actions"
    assert len(test_string) == 14
    assert "Actions" in test_string


@pytest.mark.django_db(transaction=True)
def test_user_creation():
    """Test that we can create a user in the database"""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",
        phone_number="+1234567890",
        first_name="Test",
        last_name="User",
    )

    assert User.objects.count() == 1
    assert user.email == "testuser@example.com"
    assert user.first_name == "Test"


@pytest.mark.django_db(transaction=True)
def test_user_authentication():
    """Test user authentication"""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = User.objects.create_user(
        email="authuser@example.com",
        password="authpass123",
        phone_number="+0987654321",
        first_name="Auth",
        last_name="User",
    )

    assert user.check_password("authpass123")
    assert not user.check_password("wrongpassword")


@pytest.mark.django_db(transaction=True)
def test_sample_user_fixture(sample_user):
    """Test using the sample_user fixture"""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    assert sample_user.email == "test@example.com"
    assert sample_user.first_name == "Test"
    assert User.objects.count() == 1
