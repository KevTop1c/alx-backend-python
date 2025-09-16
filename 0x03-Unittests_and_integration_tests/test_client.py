#!/usr/bin/env python3
"""
Unit test for client module
"""

import unittest
from unittest.mock import patch, Mock
from parameterized import parameterized
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Test class for GithubOrgClient"""

    @parameterized.expand([
        ("google.com",),
        ("abc",),
    ])
    @patch("client.get_json")
    def test_org(self, org_name, mock_get_json):
        """Test that GithubOrgClient returns the correct value"""

        # Setup mock return value
        expected_org_data = {"login": org_name, "id": 12345}
        mock_get_json.return_value = expected_org_data

        # Create client instance
        client = GithubOrgClient(org_name)

        # Call the org method
        result = client.org

        # Assert that get_json was called once with the expected URL
        expected_url = f"https://api.github.com/orgs/{org_name}"
        mock_get_json.assert_called_once_with(expected_url)

        # Assert that the result matches the expected data
        self.assertEqual(result, expected_org_data)


    def test_public_repos_url(self):
        """Test that _public_repos_url returns the correct value"""

        # Define a known payload with repos_url
        known_payload = {
            "login": "test_org",
            "id": 12345,
            "repos_url": "https://api.github.com/orgs/test_org/repos",
        }

        # Use patch as context manager to mock GithubOrgClient
        with patch.object(GithubOrgClient, "org",
                          new_callable=lambda: known_payload) as mock_org:
            # Create client instance
            client = GithubOrgClient("test_org")

            # Test that the _public_repos_url returns the expected URL
            result = client._public_repos_url

            # Assert that the result matches the repos_url from the payload
            self.assertEqual(result, known_payload["repos_url"])


if __name__ == "__main__":
    unittest.main()