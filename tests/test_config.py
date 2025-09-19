"""
Test configuration and environment settings.
"""

import os
import pytest
from typing import Dict, Any

# Test environment variables
TEST_ENV_VARS = {
    "ENVIRONMENT": "test",
    "DEBUG": "true",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only",
    "COUCHDB_USER": "admin",
    "COUCHDB_PASSWORD": "password",
    "COUCHDB_HOST": "localhost",
    "COUCHDB_PORT": "5984",
    "COUCHDB_DB_NAME": "awasome_test_db",
    "COUCHDB_CREATE_DB_IF_NOT_EXISTS": "true",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_DB": "1",  # Use different Redis DB for tests
    "LOG_LEVEL": "DEBUG",
    "RATE_LIMIT_PER_MINUTE": "1000"  # Higher limit for tests
}


def setup_test_environment():
    """Set up test environment variables."""
    for key, value in TEST_ENV_VARS.items():
        os.environ[key] = value


# API Response Constants
API_V1_PREFIX = "/api/v1"

# Test Data Constants
VALID_EMAIL_ADDRESSES = [
    "user@example.com",
    "test.user+tag@domain.co.uk",
    "firstname.lastname@company.org"
]

INVALID_EMAIL_ADDRESSES = [
    "invalid-email",
    "@example.com",
    "user@",
    "user..name@example.com"
]

VALID_USERNAMES = [
    "user123",
    "test_user",
    "user-name",
    "USERNAME"
]

INVALID_USERNAMES = [
    "us",  # too short
    "user with spaces",
    "user@domain",
    "user#123",
    "a" * 51  # too long
]

VALID_PASSWORDS = [
    "StrongPassword123!",
    "MyP@ssw0rd",
    "Test123$ecure"
]

WEAK_PASSWORDS = [
    "123456",  # too simple
    "password",  # too common
    "PASSWORD123",  # no lowercase
    "password123",  # no uppercase
    "Password",  # no digits or special chars
    "Pass1!"  # too short
]


class TestAPIResponses:
    """Expected API response structures for testing."""
    
    @staticmethod
    def success_response(data: Any = None) -> Dict[str, Any]:
        """Standard success response structure."""
        response = {"success": True}
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def error_response(message: str, code: int = 400) -> Dict[str, Any]:
        """Standard error response structure."""
        return {
            "error": message,
            "status_code": code
        }
    
    @staticmethod
    def validation_error(errors: list) -> Dict[str, Any]:
        """Validation error response structure."""
        return {
            "detail": errors
        }


class TestDataBuilder:
    """Helper class to build test data."""
    
    @staticmethod
    def user_create_data(**kwargs) -> Dict[str, Any]:
        """Build user creation data with optional overrides."""
        base_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }
        base_data.update(kwargs)
        return base_data
    
    @staticmethod
    def user_update_data(**kwargs) -> Dict[str, Any]:
        """Build user update data with optional overrides."""
        base_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        base_data.update(kwargs)
        return base_data


# Database test helpers
class DatabaseTestHelpers:
    """Helper functions for database testing."""
    
    @staticmethod
    async def create_test_user(db, user_data: Dict[str, Any]) -> str:
        """Create a test user in the database and return the ID."""
        # Implementation depends on your user repository
        # This is a placeholder - implement based on your UserRepository
        pass
    
    @staticmethod
    async def cleanup_test_users(db):
        """Clean up all test users from the database."""
        # Implementation depends on your database structure
        pass


# pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test" 
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    

@pytest.fixture(autouse=True)
def setup_test_env():
    """Automatically setup test environment for all tests."""
    setup_test_environment()