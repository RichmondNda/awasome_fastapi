"""
User service implementing business logic for user operations.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ..repositories.user import get_user_repository
from ..schemas.user import (
    UserCreate, UserUpdate, UserPublic, UserInDB, 
    UserStatus, PaginationParams, UserListResponse
)
from ..core.logging import get_logger
from ..core.exceptions import NotFoundError, ConflictError, ValidationError
from ..core.config import settings

logger = get_logger(__name__)


class UserService:
    """Service class for user-related business logic."""
    
    def __init__(self):
        self.repository = get_user_repository()
    
    def create_user(self, user_data: UserCreate) -> UserPublic:
        """Create a new user with business logic validation."""
        try:
            logger.info(f"Creating new user: {user_data.username}")
            
            # Convert Pydantic model to dict
            user_dict = user_data.dict()
            
            # Apply business logic
            user_dict['username'] = user_dict['username'].lower().strip()
            user_dict['email'] = user_dict['email'].lower().strip()
            
            # Create user in repository
            created_user = self.repository.create(user_dict)
            
            # Convert to public schema (excluding sensitive data)
            public_user = self._to_public_user(created_user)
            
            logger.info(f"Successfully created user: {public_user.username} ({public_user.id})")
            return public_user
            
        except (ConflictError, ValidationError) as e:
            logger.warning(f"User creation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating user: {e}")
            raise ValidationError("Failed to create user")
    
    def get_user(self, user_id: str) -> UserPublic:
        """Get a user by ID."""
        try:
            logger.debug(f"Getting user: {user_id}")
            
            user_data = self.repository.get_by_id(user_id)
            if not user_data:
                raise NotFoundError("User", user_id)
            
            return self._to_public_user(user_data)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise ValidationError("Failed to retrieve user")
    
    def get_user_by_username(self, username: str) -> Optional[UserPublic]:
        """Get a user by username."""
        try:
            logger.debug(f"Getting user by username: {username}")
            
            user_data = self.repository.get_by_username(username.lower().strip())
            if not user_data:
                return None
            
            return self._to_public_user(user_data)
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[UserPublic]:
        """Get a user by email."""
        try:
            logger.debug(f"Getting user by email: {email}")
            
            user_data = self.repository.get_by_email(email.lower().strip())
            if not user_data:
                return None
            
            return self._to_public_user(user_data)
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> UserPublic:
        """Update a user with business logic validation."""
        try:
            logger.info(f"Updating user: {user_id}")
            
            # Convert Pydantic model to dict, excluding None values
            update_dict = user_data.dict(exclude_unset=True)
            
            if not update_dict:
                raise ValidationError("No fields provided for update")
            
            # Apply business logic
            if 'username' in update_dict:
                update_dict['username'] = update_dict['username'].lower().strip()
            if 'email' in update_dict:
                update_dict['email'] = update_dict['email'].lower().strip()
            
            # Update user in repository
            updated_user = self.repository.update(user_id, update_dict)
            
            # Convert to public schema
            public_user = self._to_public_user(updated_user)
            
            logger.info(f"Successfully updated user: {public_user.username} ({public_user.id})")
            return public_user
            
        except (NotFoundError, ConflictError, ValidationError) as e:
            logger.warning(f"User update failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating user {user_id}: {e}")
            raise ValidationError("Failed to update user")
    
    def delete_user(self, user_id: str) -> Dict[str, str]:
        """Soft delete a user."""
        try:
            logger.info(f"Deleting user: {user_id}")
            
            # Check if user exists first
            user_data = self.repository.get_by_id(user_id)
            if not user_data:
                raise NotFoundError("User", user_id)
            
            # Perform soft delete
            success = self.repository.delete(user_id)
            
            if success:
                logger.info(f"Successfully deleted user: {user_data.get('username')} ({user_id})")
                return {"message": f"User '{user_data.get('username')}' has been deleted"}
            else:
                raise ValidationError("Failed to delete user")
                
        except (NotFoundError, ConflictError) as e:
            logger.warning(f"User deletion failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting user {user_id}: {e}")
            raise ValidationError("Failed to delete user")
    
    def list_users(
        self, 
        pagination: PaginationParams,
        status: Optional[UserStatus] = None,
        is_verified: Optional[bool] = None,
        search: Optional[str] = None
    ) -> UserListResponse:
        """List users with pagination and filtering."""
        try:
            logger.debug(f"Listing users (skip={pagination.skip}, limit={pagination.limit})")
            
            # Validate pagination limits
            actual_limit = min(pagination.limit, settings.MAX_PAGE_SIZE)
            
            # Build filters
            filters = {}
            if status:
                filters['status'] = status
            if is_verified is not None:
                filters['is_verified'] = is_verified
            if search:
                filters['search'] = search.strip()
            
            # Get users and total count
            users_data = self.repository.list_all(
                skip=pagination.skip,
                limit=actual_limit,
                **filters
            )
            
            total_count = self.repository.count(**filters)
            
            # Convert to public users
            public_users = [self._to_public_user(user) for user in users_data]
            
            # Build response
            response = UserListResponse(
                items=public_users,
                total=total_count,
                skip=pagination.skip,
                limit=actual_limit,
                has_more=pagination.skip + len(public_users) < total_count
            )
            
            logger.debug(f"Listed {len(public_users)} users out of {total_count} total")
            return response
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise ValidationError("Failed to retrieve users")
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            logger.debug("Getting user statistics")
            
            total_users = self.repository.count()
            active_users = self.repository.count(status=UserStatus.ACTIVE)
            inactive_users = self.repository.count(status=UserStatus.INACTIVE)
            suspended_users = self.repository.count(status=UserStatus.SUSPENDED)
            verified_users = self.repository.count(is_verified=True)
            unverified_users = self.repository.count(is_verified=False)
            
            stats = {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "suspended_users": suspended_users,
                "verified_users": verified_users,
                "unverified_users": unverified_users,
                "verification_rate": round(verified_users / total_users * 100, 2) if total_users > 0 else 0,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"Generated user statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            raise ValidationError("Failed to retrieve user statistics")
    
    def verify_user_password(self, user_id: str, password: str) -> bool:
        """Verify user password (for authentication)."""
        try:
            logger.debug(f"Verifying password for user: {user_id}")
            
            is_valid = self.repository.verify_password(user_id, password)
            
            if is_valid:
                # Update last login
                self.repository.update_last_login(user_id)
                logger.debug(f"Password verification successful for user: {user_id}")
            else:
                logger.warning(f"Password verification failed for user: {user_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying password for user {user_id}: {e}")
            return False
    
    def change_user_status(self, user_id: str, new_status: UserStatus) -> UserPublic:
        """Change user status (admin operation)."""
        try:
            logger.info(f"Changing user status: {user_id} -> {new_status}")
            
            # Validate status transition
            user_data = self.repository.get_by_id(user_id)
            if not user_data:
                raise NotFoundError("User", user_id)
            
            current_status = UserStatus(user_data.get('status', UserStatus.ACTIVE))
            
            # Check if status change is allowed
            if current_status == UserStatus.DELETED:
                raise ConflictError("Cannot change status of deleted user")
            
            # Update status
            update_data = {"status": new_status}
            updated_user = self.repository.update(user_id, update_data)
            
            public_user = self._to_public_user(updated_user)
            
            logger.info(f"Successfully changed user status: {public_user.username} ({user_id}) -> {new_status}")
            return public_user
            
        except (NotFoundError, ConflictError) as e:
            logger.warning(f"Status change failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error changing user status {user_id}: {e}")
            raise ValidationError("Failed to change user status")
    
    def export_users(self, format: str = "json") -> List[Dict[str, Any]]:
        """Export all users data."""
        try:
            logger.info(f"Exporting users in {format} format")
            
            # Get all users (no pagination for export)
            all_users = self.repository.list_all(skip=0, limit=10000)  # Large limit for export
            
            if format.lower() == "json":
                # Convert to public format for export
                export_data = []
                for user in all_users:
                    public_user = self._to_public_user(user)
                    export_data.append(public_user.dict())
                
                logger.info(f"Exported {len(export_data)} users")
                return export_data
            else:
                raise ValidationError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting users: {e}")
            raise ValidationError("Failed to export users")
    
    def _to_public_user(self, user_data: Dict[str, Any]) -> UserPublic:
        """Convert internal user data to public user schema."""
        try:
            # Remove sensitive fields
            safe_data = {k: v for k, v in user_data.items() 
                        if k not in ['password_hash', '_rev', 'metadata']}
            
            return UserPublic(**safe_data)
            
        except Exception as e:
            logger.error(f"Error converting user to public format: {e}")
            raise ValidationError("Failed to process user data")


# Service instance - initialized lazily
_user_service: Optional['UserService'] = None

def get_user_service() -> 'UserService':
    """Get the user service instance (lazy initialization)."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service