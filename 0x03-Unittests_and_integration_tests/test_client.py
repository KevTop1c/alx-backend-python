#!/usr/bin/env python3
"""
Unit test for client module
"""

import unittest
from unittest.mock import patch, Mock
from parameterized import parameterized, parameterized_class
from client import GithubOrgClient
from fixtures import TEST_PAYLOAD


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
            GithubOrgClient, "org",
            new_callable=lambda: known_payload
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
            GithubOrgClient, "_public_repos_url",
            new_callable=lambda: test_repos_url
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

    @parameterized.expand(
        [
            ({"license": {"key": "my_license"}}, "my_license", True),
            ({"license": {"key": "other_license"}}, "my_license", False),
        ]
    )
    def test_has_license(self, repo, license, expected_result):
        """Test that has_license returns the expected boolean value"""
        # Call the static method
        result = GithubOrgClient.has_license(repo, license)

        # Assert that the result matches the expected value
        self.assertEqual(result, expected_result)


@parameterized_class(
    ('org_payload', 'repos_payload', 'expected_repos', 'apache2_repos'),
    TEST_PAYLOAD
)

class TestIntegrationGithubOrgClient(unittest.TestCase):
    """Integration test class for GithubOrgClient"""

    org_payload = None
    repos_payload = None
    expected_repos = None
    apache2_repos = None

    @classmethod
    def setUpClass(cls):
        """Setup class method for mock requests.get"""
        cls.get_patcher = patch("requests.get")
        cls.mock_get = cls.get_patcher.start()

        # Define side effect function to return different payloads based on URL
        def side_effect(url, *args, **kwargs):
            mock_response = Mock()

            # Return org payload for org URL
            if url == "https://api.github.com/orgs/google":
                mock_response.json.return_value = cls.org_payload
            # Return repos payload for repos URL
            elif url == cls.org_payload["repos_url"]:
                mock_response.json.return_value = cls.repos_payload
            else:
                # Return empty dict for unexpected URLs
                mock_response.json.return_value = {}

            return mock_response

        cls.mock_get.side_effect = side_effect

    @classmethod
    def tearDownClass(cls):
        """Tears down the class by stopping the patcher"""
        cls.get_patcher.stop()

    def test_public_repos(self):
        """Tests the public_repos method"""
        client = GithubOrgClient("google")
        repos = client.public_repos()
        self.assertEqual(repos, self.expected_repos)

    def test_public_repos_with_license(self):
        """Tests the public_repos method with a license filter."""
        client = GithubOrgClient("google")
        repos = client.public_repos(license="apache-2.0")
        self.assertEqual(repos, self.apache2_repos)
        self.mock_get.assert_called()


if __name__ == "__main__":
    unittest.main()
