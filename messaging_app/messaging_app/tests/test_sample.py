"""
Sample test file for the messaging app
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User


class SampleTestCase(TestCase):
    """Sample test case to verify testing setup works"""

    def test_basic_assertion(self):
        """Test that basic assertions work"""
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)
        self.assertFalse(False)

    def test_database_access(self):
        """Test that database is accessible"""
        # Create a test user
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Verify user was created
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")

    def test_user_authentication(self):
        """Test user authentication"""
        # Create a user
        user = User.objects.create_user(username="authuser", password="authpass123")

        # Test authentication
        self.assertTrue(user.check_password("authpass123"))
        self.assertFalse(user.check_password("wrongpassword"))


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
