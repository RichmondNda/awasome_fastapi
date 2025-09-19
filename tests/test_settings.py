"""
Tests for application configuration.
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings, settings


class TestSettingsValidation:
    """Test configuration settings validation."""

    def test_default_settings(self):
        """Test default settings values."""
        test_settings = Settings()
        
        assert test_settings.PROJECT_NAME == "Awasome FastAPI"
        assert test_settings.VERSION == "1.0.0"
        assert test_settings.ENVIRONMENT == "development"
        assert test_settings.DEBUG is False
        assert test_settings.API_V1_STR == "/api/v1"
        assert test_settings.DEFAULT_PAGE_SIZE == 10
        assert test_settings.MAX_PAGE_SIZE == 100

    def test_environment_validation(self):
        """Test environment field validation."""
        # Valid environments
        valid_envs = ["development", "staging", "production"]
        
        for env in valid_envs:
            test_settings = Settings(ENVIRONMENT=env)
            assert test_settings.ENVIRONMENT == env.lower()

        # Invalid environment should raise validation error
        with pytest.raises(ValidationError):
            Settings(ENVIRONMENT="invalid_env")

    def test_cors_origins_string_parsing(self):
        """Test CORS origins parsing from string."""
        cors_string = "http://localhost:3000,http://localhost:8080,https://example.com"
        
        test_settings = Settings(BACKEND_CORS_ORIGINS=cors_string)
        
        expected = ["http://localhost:3000", "http://localhost:8080", "https://example.com"]
        assert test_settings.BACKEND_CORS_ORIGINS == expected

    def test_cors_origins_list_input(self):
        """Test CORS origins with list input."""
        cors_list = ["http://localhost:3000", "https://example.com"]
        
        test_settings = Settings(BACKEND_CORS_ORIGINS=cors_list)
        
        assert test_settings.BACKEND_CORS_ORIGINS == cors_list

    def test_database_url_properties(self):
        """Test database URL generation properties."""
        test_settings = Settings(
            COUCHDB_USER="testuser",
            COUCHDB_PASSWORD="testpass", 
            COUCHDB_HOST="localhost",
            COUCHDB_PORT=5984
        )
        
        expected_full = "http://testuser:testpass@localhost:5984"
        expected_no_auth = "http://localhost:5984"
        
        assert test_settings.couchdb_full_url == expected_full
        assert test_settings.couchdb_url_no_auth == expected_no_auth

    def test_redis_url_property(self):
        """Test Redis URL generation property."""
        test_settings = Settings(
            REDIS_HOST="redis-server",
            REDIS_PORT=6379,
            REDIS_DB=2
        )
        
        expected = "redis://redis-server:6379/2"
        assert test_settings.redis_url == expected

    def test_environment_properties(self):
        """Test environment-related properties."""
        # Test production
        prod_settings = Settings(ENVIRONMENT="production")
        assert prod_settings.is_production is True
        assert prod_settings.is_development is False
        
        # Test development
        dev_settings = Settings(ENVIRONMENT="development")
        assert dev_settings.is_production is False
        assert dev_settings.is_development is True