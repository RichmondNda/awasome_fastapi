"""
Base repository class implementing the Repository pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime
import uuid

import couchdb
from ..core.database import get_database
from ..core.logging import get_logger
from ..core.exceptions import NotFoundError, DatabaseError, ConflictError

logger = get_logger(__name__)

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository class."""
    
    def __init__(self):
        self.db = get_database()
    
    @property
    @abstractmethod
    def entity_name(self) -> str:
        """Name of the entity for error messages."""
        pass
    
    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return str(uuid.uuid4())
    
    def _add_timestamps(self, data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """Add creation and update timestamps."""
        now = datetime.utcnow()
        
        if not is_update:
            data['created_at'] = now.isoformat()
        
        data['updated_at'] = now.isoformat()
        return data
    
    def _handle_couchdb_error(self, error: Exception, operation: str, entity_id: str = None):
        """Handle CouchDB specific errors and convert to appropriate exceptions."""
        error_msg = str(error)
        
        if "not found" in error_msg.lower() or "missing" in error_msg.lower():
            identifier = entity_id or "unknown"
            raise NotFoundError(self.entity_name, identifier)
        elif "conflict" in error_msg.lower():
            raise ConflictError(f"{self.entity_name} update conflict")
        else:
            logger.error(f"{operation} failed for {self.entity_name}: {error}")
            raise DatabaseError(f"{operation} operation failed")
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        pass
    
    @abstractmethod
    def list_all(self, skip: int = 0, limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """List entities with pagination and filtering."""
        pass
    
    @abstractmethod
    def count(self, **filters) -> int:
        """Count entities with optional filtering."""
        pass