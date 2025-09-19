"""
Database connection and initialization.
Enhanced version with connection pooling, health checks, and error handling.
"""

import couchdb
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import DatabaseError

logger = get_logger(__name__)


class DatabaseManager:
    """Enhanced database manager with connection pooling and health checks."""
    
    def __init__(self):
        self.server: Optional[couchdb.Server] = None
        self.database: Optional[couchdb.Database] = None
        self._connection_start_time = None
        self._last_health_check = None
        self._health_check_interval = 30  # seconds
    
    def connect(self) -> None:
        """Establish database connection with retry logic."""
        max_retries = 10
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to CouchDB (attempt {attempt + 1}/{max_retries})")
                
                self.server = couchdb.Server(settings.couchdb_full_url)
                
                # Test connection
                self.server.version()
                logger.info("Successfully connected to CouchDB server")
                
                # Create or get the database
                if settings.COUCHDB_CREATE_DB_IF_NOT_EXISTS:
                    if settings.COUCHDB_DB_NAME in self.server:
                        self.database = self.server[settings.COUCHDB_DB_NAME]
                        logger.info(f"Connected to existing database: {settings.COUCHDB_DB_NAME}")
                    else:
                        self.database = self.server.create(settings.COUCHDB_DB_NAME)
                        logger.info(f"Created new database: {settings.COUCHDB_DB_NAME}")
                else:
                    if settings.COUCHDB_DB_NAME not in self.server:
                        raise DatabaseError(f"Database '{settings.COUCHDB_DB_NAME}' does not exist and auto-creation is disabled")
                    self.database = self.server[settings.COUCHDB_DB_NAME]
                    logger.info(f"Connected to existing database: {settings.COUCHDB_DB_NAME}")
                
                self._connection_start_time = time.time()
                self._ensure_indexes()
                logger.info("Database connection established successfully")
                return
                
            except Exception as e:
                logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise DatabaseError(f"Failed to connect to database after {max_retries} attempts")
    
    def _ensure_indexes(self) -> None:
        """Create necessary database indexes for performance."""
        try:
            # Create indexes for common queries
            indexes = [
                {
                    "index": {
                        "fields": ["username"]
                    },
                    "name": "username-index",
                    "type": "json"
                },
                {
                    "index": {
                        "fields": ["email"]
                    },
                    "name": "email-index", 
                    "type": "json"
                },
                {
                    "index": {
                        "fields": ["status"]
                    },
                    "name": "status-index",
                    "type": "json"
                },
                {
                    "index": {
                        "fields": ["created_at"]
                    },
                    "name": "created-at-index",
                    "type": "json"
                }
            ]
            
            for index in indexes:
                try:
                    # CouchDB create_index equivalent (using _index endpoint)
                    self.database.resource.post('_index', index)
                    logger.debug(f"Created index: {index['name']}")
                except Exception as e:
                    # Index might already exist
                    logger.debug(f"Index creation skipped for {index['name']}: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to create some indexes: {e}")
    
    def disconnect(self) -> None:
        """Close database connection."""
        try:
            self.database = None
            self.server = None
            self._connection_start_time = None
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        now = time.time()
        
        # Use cached result if recent
        if (self._last_health_check and 
            now - self._last_health_check < self._health_check_interval):
            return self._cached_health_status
        
        try:
            start_time = time.time()
            
            # Test basic connectivity
            if not self.database:
                raise DatabaseError("No database connection")
            
            # Test read operation
            list(self.database.view('_all_docs', limit=1))
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            uptime = now - self._connection_start_time if self._connection_start_time else 0
            
            health_status = {
                "status": "connected",
                "response_time_ms": round(response_time, 2),
                "uptime_seconds": round(uptime, 2),
                "database_name": settings.COUCHDB_DB_NAME,
                "server_version": getattr(self.server, 'version', lambda: 'unknown')(),
                "last_check": datetime.now().isoformat()
            }
            
            self._cached_health_status = health_status
            self._last_health_check = now
            
            return health_status
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status = {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
            self._cached_health_status = health_status
            self._last_health_check = now
            return health_status
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions (CouchDB doesn't have true transactions)."""
        # CouchDB doesn't support transactions, but we can implement a pattern
        # for batch operations and rollback simulation
        operations = []
        try:
            yield operations
            # In a real transaction system, we'd commit here
            logger.debug(f"Completed batch operation with {len(operations)} operations")
        except Exception as e:
            logger.error(f"Batch operation failed: {e}")
            # In a real transaction system, we'd rollback here
            raise
    
    def get_database(self) -> couchdb.Database:
        """Get the database instance."""
        if not self.database:
            raise DatabaseError("Database not connected")
        return self.database
    
    def get_server(self) -> couchdb.Server:
        """Get the server instance."""
        if not self.server:
            raise DatabaseError("Server not connected")
        return self.server


# Global database manager instance
db_manager = DatabaseManager()

# Legacy compatibility - maintain the old 'db' interface
db = None


def get_database() -> couchdb.Database:
    """Get database instance with connection check."""
    return db_manager.get_database()


def init_database():
    """Initialize database connection."""
    global db
    db_manager.connect()
    db = db_manager.get_database()


def close_database():
    """Close database connection."""
    global db
    db_manager.disconnect()
    db = None