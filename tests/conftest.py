"""
Test configuration and fixtures.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import db_manager


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_client() -> Generator:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
async def db_session():
    """Create a database session for testing."""
    # Connect to test database
    await db_manager.connect()
    
    # Create test database if needed
    test_db_name = f"{settings.COUCHDB_DB_NAME}_test"
    if test_db_name not in db_manager.server:
        test_db = db_manager.server.create(test_db_name)
    else:
        test_db = db_manager.server[test_db_name]
    
    # Use test database
    original_db = db_manager.database
    db_manager.database = test_db
    
    yield test_db
    
    # Cleanup: delete all test documents
    for doc_id in test_db:
        if not doc_id.startswith('_design/'):
            try:
                doc = test_db[doc_id]
                test_db.delete(doc)
            except:
                pass
    
    # Restore original database
    db_manager.database = original_db


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!"
    }


@pytest.fixture
def sample_user_update_data():
    """Sample user update data for testing."""
    return {
        "first_name": "Updated",
        "last_name": "Name",
        "bio": "Updated bio"
    }


@pytest.fixture
def auth_headers():
    """Authorization headers for testing."""
    # This would typically contain a valid JWT token
    # For now, return empty dict - implement JWT testing as needed
    return {}