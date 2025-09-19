"""
User repository implementing CRUD operations for user entities.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import secrets

from .base import BaseRepository
from ..schemas.user import UserStatus, UserInDB
from ..core.logging import get_logger
from ..core.exceptions import ConflictError, ValidationError

logger = get_logger(__name__)


class UserRepository(BaseRepository[UserInDB]):
    """Repository for user-related database operations."""
    
    @property
    def entity_name(self) -> str:
        return "User"
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using secure methods."""
        # Generate a random salt
        salt = secrets.token_hex(32)
        
        # Hash password with salt using SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, password_hash = hashed.split(':')
            
            # Hash the provided password with the stored salt
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            
            return new_hash.hex() == password_hash
        except ValueError:
            return False
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        try:
            # Check if username or email already exists
            if self.get_by_username(data.get('username')):
                raise ConflictError(f"Username '{data.get('username')}' already exists")
            
            if self.get_by_email(data.get('email')):
                raise ConflictError(f"Email '{data.get('email')}' already exists")
            
            # Generate ID and add timestamps
            user_id = self._generate_id()
            user_data = data.copy()
            
            # Hash password if provided
            if 'password' in user_data:
                user_data['password_hash'] = self._hash_password(user_data.pop('password'))
            
            # Remove confirm_password if present
            user_data.pop('confirm_password', None)
            
            # Set default values
            user_data.update({
                '_id': user_id,
                'id': user_id,
                'status': user_data.get('status', UserStatus.ACTIVE),
                'is_verified': user_data.get('is_verified', False),
                'login_count': 0,
                'metadata': user_data.get('metadata', {})
            })
            
            # Add timestamps
            user_data = self._add_timestamps(user_data)
            
            # Save to database
            doc_id, doc_rev = self.db.save(user_data)
            user_data['_rev'] = doc_rev
            
            logger.info(f"Created user: {user_data.get('username')} ({user_id})")
            return user_data
            
        except (ConflictError, ValidationError):
            raise
        except Exception as e:
            self._handle_couchdb_error(e, "Create user")
    
    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            if user_id not in self.db:
                return None
            
            user_data = dict(self.db[user_id])
            
            # Check if user is soft deleted
            if user_data.get('status') == UserStatus.DELETED:
                return None
            
            return user_data
            
        except Exception as e:
            self._handle_couchdb_error(e, "Get user by ID", user_id)
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            # Use Mango query for efficient lookup
            result = list(self.db.find({
                'selector': {
                    'username': username,
                    'status': {'$ne': UserStatus.DELETED}
                },
                'limit': 1
            }))
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            # Use Mango query for efficient lookup
            result = list(self.db.find({
                'selector': {
                    'email': email,
                    'status': {'$ne': UserStatus.DELETED}
                },
                'limit': 1
            }))
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def update(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user."""
        try:
            # Get existing user
            if user_id not in self.db:
                raise NotFoundError(self.entity_name, user_id)
            
            existing_user = dict(self.db[user_id])
            
            # Check if user is deleted
            if existing_user.get('status') == UserStatus.DELETED:
                raise NotFoundError(self.entity_name, user_id)
            
            # Check for username conflicts (if username is being updated)
            new_username = data.get('username')
            if new_username and new_username != existing_user.get('username'):
                existing_username_user = self.get_by_username(new_username)
                if existing_username_user and existing_username_user['id'] != user_id:
                    raise ConflictError(f"Username '{new_username}' already exists")
            
            # Check for email conflicts (if email is being updated)
            new_email = data.get('email')
            if new_email and new_email != existing_user.get('email'):
                existing_email_user = self.get_by_email(new_email)
                if existing_email_user and existing_email_user['id'] != user_id:
                    raise ConflictError(f"Email '{new_email}' already exists")
            
            # Merge updates with existing data
            updated_data = existing_user.copy()
            
            # Only update provided fields
            for key, value in data.items():
                if value is not None:  # Allow explicit None values for optional fields
                    updated_data[key] = value
            
            # Add update timestamp
            updated_data = self._add_timestamps(updated_data, is_update=True)
            
            # Save updated document
            doc_id, doc_rev = self.db.save(updated_data)
            updated_data['_rev'] = doc_rev
            
            logger.info(f"Updated user: {updated_data.get('username')} ({user_id})")
            return updated_data
            
        except (NotFoundError, ConflictError, ValidationError):
            raise
        except Exception as e:
            self._handle_couchdb_error(e, "Update user", user_id)
    
    def delete(self, user_id: str) -> bool:
        """Soft delete a user by marking as deleted."""
        try:
            # Get existing user
            if user_id not in self.db:
                raise NotFoundError(self.entity_name, user_id)
            
            existing_user = dict(self.db[user_id])
            
            # Check if already deleted
            if existing_user.get('status') == UserStatus.DELETED:
                raise ConflictError("User is already deleted")
            
            # Mark as deleted instead of actually deleting
            existing_user['status'] = UserStatus.DELETED
            existing_user['deleted_at'] = datetime.utcnow().isoformat()
            existing_user = self._add_timestamps(existing_user, is_update=True)
            
            # Save updated document
            self.db.save(existing_user)
            
            logger.info(f"Soft deleted user: {existing_user.get('username')} ({user_id})")
            return True
            
        except (NotFoundError, ConflictError):
            raise
        except Exception as e:
            self._handle_couchdb_error(e, "Delete user", user_id)
    
    def hard_delete(self, user_id: str) -> bool:
        """Permanently delete a user (admin operation)."""
        try:
            if user_id not in self.db:
                raise NotFoundError(self.entity_name, user_id)
            
            user_data = dict(self.db[user_id])
            del self.db[user_id]
            
            logger.warning(f"Hard deleted user: {user_data.get('username')} ({user_id})")
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            self._handle_couchdb_error(e, "Hard delete user", user_id)
    
    def list_all(self, skip: int = 0, limit: int = 10, **filters) -> List[Dict[str, Any]]:
        """List users with pagination and filtering."""
        try:
            # Build selector
            selector = {'status': {'$ne': UserStatus.DELETED}}
            
            # Add filters
            if filters.get('status'):
                selector['status'] = filters['status']
            if filters.get('is_verified') is not None:
                selector['is_verified'] = filters['is_verified']
            if filters.get('search'):
                # Simple text search on username and email
                search_term = filters['search']
                selector['$or'] = [
                    {'username': {'$regex': f'(?i){search_term}'}},
                    {'email': {'$regex': f'(?i){search_term}'}}
                ]
            
            # Execute query with pagination
            result = list(self.db.find({
                'selector': selector,
                'skip': skip,
                'limit': limit,
                'sort': [{'created_at': 'desc'}]
            }))
            
            logger.debug(f"Retrieved {len(result)} users (skip={skip}, limit={limit})")
            return result
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def count(self, **filters) -> int:
        """Count users with optional filtering."""
        try:
            # Build selector
            selector = {'status': {'$ne': UserStatus.DELETED}}
            
            # Add filters
            if filters.get('status'):
                selector['status'] = filters['status']
            if filters.get('is_verified') is not None:
                selector['is_verified'] = filters['is_verified']
            if filters.get('search'):
                search_term = filters['search']
                selector['$or'] = [
                    {'username': {'$regex': f'(?i){search_term}'}},
                    {'email': {'$regex': f'(?i){search_term}'}}
                ]
            
            # Count using find with limit 0 (CouchDB specific)
            # Note: This is not the most efficient for large datasets
            # In production, consider using a view with reduce
            result = list(self.db.find({
                'selector': selector,
                'fields': ['_id']
            }))
            
            return len(result)
            
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0
    
    def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password."""
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False
            
            return self._verify_password(password, user.get('password_hash', ''))
            
        except Exception as e:
            logger.error(f"Error verifying password for user {user_id}: {e}")
            return False
    
    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp and increment login count."""
        try:
            user = self.get_by_id(user_id)
            if user:
                update_data = {
                    'last_login': datetime.utcnow().isoformat(),
                    'login_count': user.get('login_count', 0) + 1
                }
                self.update(user_id, update_data)
                logger.debug(f"Updated last login for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")


# Repository instance
# Global repository instance - initialized lazily
_user_repository: Optional['UserRepository'] = None

def get_user_repository() -> 'UserRepository':
    """Get the user repository instance (lazy initialization)."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository