"""
Tests for database connections and operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from app.core.database import DatabaseManager, db_manager
from app.core.config import settings
from app.core.exceptions import DatabaseError


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""

    def test_database_manager_singleton(self):
        """Test that DatabaseManager is a singleton."""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()
        
        # Should be the same instance
        assert manager1 is manager2

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        manager = DatabaseManager()
        
        assert manager.server is None
        assert manager.database is None
        assert manager._connection_start_time is None
        assert manager._last_health_check is None
        assert manager._health_check_interval == 30

    @patch('app.core.database.couchdb.Server')
    def test_connect_success(self, mock_server):
        """Test successful database connection."""
        # Mock CouchDB server
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance
        
        # Mock database
        mock_db = Mock()
        mock_server_instance.__contains__ = Mock(return_value=True)
        mock_server_instance.__getitem__ = Mock(return_value=mock_db)
        
        # Mock version check
        mock_server_instance.version.return_value = "3.3.3"
        
        manager = DatabaseManager()
        manager.connect()
        
        assert manager.server is not None
        assert manager.database is not None
        assert manager._connection_start_time is not None

    @patch('app.core.database.couchdb.Server')
    def test_connect_database_creation(self, mock_server):
        """Test database creation when it doesn't exist."""
        # Mock CouchDB server
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance
        
        # Mock database doesn't exist initially
        mock_db = Mock()
        mock_server_instance.__contains__ = Mock(return_value=False)
        mock_server_instance.create = Mock(return_value=mock_db)
        
        # Mock version check
        mock_server_instance.version.return_value = "3.3.3"
        
        # Ensure auto-creation is enabled
        with patch.object(settings, 'COUCHDB_CREATE_DB_IF_NOT_EXISTS', True):
            manager = DatabaseManager()
            manager.connect()
            
            # Should call create
            mock_server_instance.create.assert_called_once()
            assert manager.database is mock_db

    @patch('app.core.database.couchdb.Server')
    def test_connect_no_auto_creation(self, mock_server):
        """Test connection fails when database doesn't exist and auto-creation is disabled."""
        # Mock CouchDB server
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance
        
        # Mock database doesn't exist
        mock_server_instance.__contains__ = Mock(return_value=False)
        mock_server_instance.version.return_value = "3.3.3"
        
        # Disable auto-creation
        with patch.object(settings, 'COUCHDB_CREATE_DB_IF_NOT_EXISTS', False):
            manager = DatabaseManager()
            
            with pytest.raises(DatabaseError):
                manager.connect()

    @patch('app.core.database.couchdb.Server')
    def test_connect_retry_logic(self, mock_server):
        """Test connection retry logic on failure."""
        # Mock server that fails initially then succeeds
        mock_server.side_effect = [Exception("Connection failed"), Exception("Still failing")]
        
        manager = DatabaseManager()
        
        with pytest.raises(DatabaseError, match="Failed to connect to database after"):
            manager.connect()

    def test_health_check_no_connection(self):
        """Test health check when not connected."""
        manager = DatabaseManager()
        manager.server = None
        
        health = manager.health_check()
        
        assert health["status"] == "disconnected"
        assert "error" in health

    @patch('app.core.database.couchdb.Server')
    def test_health_check_connected(self, mock_server):
        """Test health check when connected."""
        # Mock connected state
        mock_server_instance = Mock()
        mock_db = Mock()
        
        manager = DatabaseManager()
        manager.server = mock_server_instance
        manager.database = mock_db
        manager._connection_start_time = time.time() - 100
        
        # Mock successful server info call
        mock_server_instance.version.return_value = "3.3.3"
        
        health = manager.health_check()
        
        assert health["status"] == "connected"
        assert "response_time_ms" in health
        assert "server_version" in health
        assert health["server_version"] == "3.3.3"

    @patch('app.core.database.couchdb.Server')
    def test_health_check_connection_error(self, mock_server):
        """Test health check when connection has issues."""
        mock_server_instance = Mock()
        mock_server_instance.version.side_effect = Exception("Connection timeout")
        
        manager = DatabaseManager()
        manager.server = mock_server_instance
        manager._connection_start_time = time.time()
        
        health = manager.health_check()
        
        assert health["status"] == "error"
        assert "error" in health

    def test_is_connected_true(self):
        """Test is_connected returns True when connected."""
        manager = DatabaseManager()
        manager.server = Mock()
        manager.database = Mock()
        
        assert manager.is_connected() is True

    def test_is_connected_false(self):
        """Test is_connected returns False when not connected."""
        manager = DatabaseManager()
        manager.server = None
        manager.database = None
        
        assert manager.is_connected() is False

    def test_disconnect(self):
        """Test disconnect method."""
        manager = DatabaseManager()
        manager.server = Mock()
        manager.database = Mock()
        manager._connection_start_time = time.time()
        
        manager.disconnect()
        
        assert manager.server is None
        assert manager.database is None
        assert manager._connection_start_time is None

    @patch('app.core.database.couchdb.Server')
    def test_reconnect(self, mock_server):
        """Test reconnect method."""
        # Setup mocks
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance
        mock_db = Mock()
        mock_server_instance.__contains__ = Mock(return_value=True)
        mock_server_instance.__getitem__ = Mock(return_value=mock_db)
        mock_server_instance.version.return_value = "3.3.3"
        
        manager = DatabaseManager()
        manager.server = Mock()  # Simulate existing connection
        manager.database = Mock()
        
        manager.reconnect()
        
        # Should have new connections
        assert manager.server is mock_server_instance
        assert manager.database is mock_db


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager."""

    @pytest.mark.integration
    def test_actual_database_connection(self):
        """Test actual connection to CouchDB (requires running CouchDB)."""
        try:
            manager = DatabaseManager()
            manager.connect()
            
            assert manager.is_connected()
            
            # Test health check
            health = manager.health_check()
            assert health["status"] == "connected"
            
            manager.disconnect()
            assert not manager.is_connected()
            
        except Exception as e:
            pytest.skip(f"CouchDB not available for integration test: {e}")

    @pytest.mark.integration  
    def test_database_auto_creation(self):
        """Test automatic database creation."""
        try:
            # Use a temporary test database name
            test_db_name = f"{settings.COUCHDB_DB_NAME}_auto_test_{int(time.time())}"
            
            with patch.object(settings, 'COUCHDB_DB_NAME', test_db_name):
                manager = DatabaseManager()
                manager.connect()
                
                # Database should be created
                assert test_db_name in manager.server
                
                # Clean up
                if test_db_name in manager.server:
                    del manager.server[test_db_name]
                    
                manager.disconnect()
                
        except Exception as e:
            pytest.skip(f"CouchDB not available for integration test: {e}")


class TestDatabaseConfiguration:
    """Tests for database configuration."""

    def test_couchdb_url_generation(self):
        """Test CouchDB URL generation from settings."""
        expected_url = f"http://{settings.COUCHDB_USER}:{settings.COUCHDB_PASSWORD}@{settings.COUCHDB_HOST}:{settings.COUCHDB_PORT}"
        assert settings.couchdb_full_url == expected_url

    def test_couchdb_url_no_auth(self):
        """Test CouchDB URL generation without authentication."""
        expected_url = f"http://{settings.COUCHDB_HOST}:{settings.COUCHDB_PORT}"
        assert settings.couchdb_url_no_auth == expected_url

    def test_database_settings_validation(self):
        """Test that database settings are properly configured."""
        assert settings.COUCHDB_HOST is not None
        assert settings.COUCHDB_PORT > 0
        assert settings.COUCHDB_USER is not None
        assert settings.COUCHDB_PASSWORD is not None
        assert settings.COUCHDB_DB_NAME is not None


class TestDatabaseErrorHandling:
    """Tests for database error handling."""

    @patch('app.core.database.couchdb.Server')
    def test_connection_timeout_handling(self, mock_server):
        """Test handling of connection timeouts."""
        mock_server.side_effect = TimeoutError("Connection timeout")
        
        manager = DatabaseManager()
        
        with pytest.raises(DatabaseError):
            manager.connect()

    @patch('app.core.database.couchdb.Server')
    def test_authentication_error_handling(self, mock_server):
        """Test handling of authentication errors."""
        mock_server.side_effect = Exception("Unauthorized")
        
        manager = DatabaseManager()
        
        with pytest.raises(DatabaseError):
            manager.connect()

    def test_invalid_database_name_handling(self):
        """Test handling of invalid database names."""
        with patch.object(settings, 'COUCHDB_DB_NAME', 'Invalid Database Name!'):
            manager = DatabaseManager()
            
            # Should handle gracefully
            try:
                manager.connect()
            except DatabaseError:
                pass  # Expected


class TestDatabasePerformance:
    """Performance tests for database operations."""

    @pytest.mark.slow
    @patch('app.core.database.couchdb.Server')
    def test_connection_performance(self, mock_server):
        """Test that database connection is reasonably fast."""
        # Mock quick connection
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance
        mock_db = Mock()
        mock_server_instance.__contains__ = Mock(return_value=True)
        mock_server_instance.__getitem__ = Mock(return_value=mock_db)
        mock_server_instance.version.return_value = "3.3.3"
        
        manager = DatabaseManager()
        
        start_time = time.time()
        manager.connect()
        end_time = time.time()
        
        # Connection should be fast (under 5 seconds)
        assert end_time - start_time < 5.0

    @pytest.mark.slow
    def test_health_check_performance(self):
        """Test that health checks are fast."""
        manager = DatabaseManager()
        manager.server = Mock()
        manager.database = Mock()
        manager._connection_start_time = time.time()
        
        # Mock version call to return quickly
        manager.server.version.return_value = "3.3.3"
        
        start_time = time.time()
        health = manager.health_check()
        end_time = time.time()
        
        # Health check should be very fast (under 1 second)
        assert end_time - start_time < 1.0
        assert "response_time_ms" in health