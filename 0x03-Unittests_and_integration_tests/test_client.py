#!/usr/bin/env python3
"""
Unit test for client module
"""

import unittest
from unittest.mock import patch
from parameterized import parameterized
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Test class for GithubOrgClient"""

    @parameterized.expand(
        [
            ("google.com",),
            ("abc",),
        ]
    )
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
        with patch.object(
            GithubOrgClient, "org", new_callable=lambda: known_payload
        ) as mock_org:
            # Create client instance
            client = GithubOrgClient("test_org")

            # Test that the _public_repos_url returns the expected URL
            result = client._public_repos_url

            # Assert that the result matches the repos_url from the payload
            self.assertEqual(result, known_payload["repos_url"])

    @patch("client.get_json")
    def test_public_repos(self, mock_get_json):
        """Test that public_repos returns the expected list of repos"""

        # Define a test payload with repository data
        test_repos_payload = [
            {"name": "repo1", "license": {"key": "mit"}},
            {"name": "repo2", "license": {"key": "apache-2.0"}},
            {"name": "repo3", "license": None},
        ]

        # Mock get_json to return test payload
        mock_get_json.return_value = test_repos_payload

        # Mock _public_repos_url to return a test URL
        test_repos_url = "https://api.github.com/repos/test_org/repos"

        # Use patch as a context manager to mock _public_repos_url
        with patch.object(
            GithubOrgClient, "_public_repos_url", new_callable=lambda: test_repos_url
        ) as mock_repos_url:
            # Create client instance
            client = GithubOrgClient("test_org")

            # Call public_repos method
            result = client.public_repos()

            # Test that the list of repos is what is expected
            expected_repos = ["repo1", "repo2", "repo3"]
            self.assertEqual(result, expected_repos)

            # Test with license filter
            repos_with_license = client.public_repos(license="mit")
            expected_repos_mit = ["repo1"]
            self.assertEqual(repos_with_license, expected_repos_mit)

            # Test that get_json was called once with test repos url
            mock_get_json.assert_called_once_with(test_repos_url)


if __name__ == "__main__":
    unittest.main()
