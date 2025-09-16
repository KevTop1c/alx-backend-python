# GitHub Organization Client - Test Suite

## Overview
This project provides a comprehensive test suite for a `GithubOrgClient` class that interacts with the GitHub API to retrieve organization repository information. The tests ensure proper functionality, error handling, and integration with external APIs.

## Project Structure
```text
├── client.py              # Main GithubOrgClient implementation
├── utils.py               # Utility functions (access_nested_map, get_json, memoize)
├── test_utils.py          # Unit tests for utility functions
├── test_client.py         # Unit tests for GithubOrgClient
├── fixtures.py            # Test data fixtures for integration testing
└── README.md              # This file
```

## Utility Functions Tested
### 1. access_nested_map
**Purpose:** Safely access values in nested dictionaries using a path of keys.

**Test Cases:**
- Valid paths that return expected values
- Invalid paths that raise appropriate KeyError exceptions
- Proper error message formatting

### 2. get_json
**Purpose:** Retrieve JSON data from remote URLs with HTTP request handling.

**Test Features:**
- Mocked HTTP calls to prevent external requests
- URL validation and call tracking
- JSON response parsing verification

### 3. memoize decorator
**Purpose:** Cache method results to prevent redundant computations.

**Test Verification:**
- Method results are cached after first call
- Underlying method is called only once
- Subsequent calls return cached values

## GithubOrgClient Functionality
### Core Methods
#### 1. public_repos()
- Retrieves all public repositories for an organization
- Supports optional license filtering
- Returns list of repository names

#### 2. has_license() (static method)
- Checks if a repository has a specific license
- Handles various license structures and edge cases
- Returns boolean result

## Key Features Tested
- **Repository retrieval:** Fetching org repos from GitHub API
- **License filtering:** Filtering repositories by license type
- **Error handling:** Proper exception handling for invalid paths
- **API integration:** Correct URL construction and API calls
- **Data processing:** Proper extraction of repository names

## Test Types Implemented
### 1. Unit Tests
- Isolated testing of individual components
- Mocked dependencies for controlled testing
-  Parameterized testing for multiple scenarios

### 2. Integration Tests
- End-to-end testing of API integration
- Mocked only external HTTP requests
- Realistic test data from fixtures
- Verification of complete workflow

## Test Data Fixtures
The `fixtures.py` file contains comprehensive test data including:
- **Organization payload:** GitHub organization API response
- **Repositories payload:** List of repository data with various licenses
- **Expected results:** Pre-calculated results for verification
- **Realistic data:** Actual GitHub API response structure

## Test Coverage
### Utility Functions
- ✅ access_nested_map with valid and invalid paths
- ✅ get_json with mocked HTTP responses
- ✅ memoize decorator caching behavior

### GithubOrgClient
- ✅ public_repos without license filter
- ✅ public_repos with license filtering
- ✅ has_license static method with various scenarios
- ✅ API integration and URL handling
- ✅ Error handling and edge cases

## Testing Methodology
### Mocking Strategy
- **HTTP requests:** Mocked using `unittest.mock.patch`
- **External dependencies:** Isolated for unit testing
- **Property access:** Mocked using `PropertyMock`
- **Side effects:** Custom response handling based on URLs

### Parameterized Testing
- Multiple test scenarios in single test methods
- Comprehensive coverage of edge cases
- Reduced code duplication

### Assertion Types
- Equality assertions for result validation
- Exception assertions for error handling
- Call count assertions for method invocation tracking
- Collection assertions for list contents

## Usage
### Running Tests
```bash
# Run all tests
python -m unittest discover

# Run specific test file
python -m unittest test_utils.py
python -m unittest test_client.py

# Run with verbose output
python -m unittest discover -v
```

### Test Organization
- **test_utils.py:** Tests for utility functions
- **test_client.py:** Tests for GithubOrgClient class
- **Fixtures:** Realistic test data for integration testing

### Key Dependencies
- `unittest`: Python's built-in testing framework
- `parameterized`: For parameterized test cases
- `unittest.mock`: For mocking external dependencies

## Quality Assurance
- **PEP 8 compliance:** Code follows Python style guidelines
- **Comprehensive coverage:** All major functionalities tested
- **Edge case handling:** Various error scenarios covered
- **Integration testing:** Real-world API interaction tested
- **Documentation:** Clear docstrings and comments throughout

This test suite ensures that the `GithubOrgClient` reliably interacts with the GitHub API, handles various response scenarios, and provides accurate results for repository information retrieval and filtering.# README