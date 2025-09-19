"""
User API endpoints with comprehensive CRUD operations and Redis caching.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path
from fastapi.responses import JSONResponse

from ...services.user import get_user_service
from ...schemas.user import (
    UserCreate, UserUpdate, UserPublic, UserListResponse,
    PaginationParams, UserStatus, HealthCheck
)
from ...core.logging import get_logger
from ...core.exceptions import NotFoundError, ConflictError, ValidationError
from ...core.config import settings
from ...cache import UserCache, cache

logger = get_logger(__name__)

router = APIRouter()


# Dependency to get pagination parameters
def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return (max 100)")
) -> PaginationParams:
    """Get pagination parameters from query string."""
    return PaginationParams(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with comprehensive validation and business logic.",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "User with username or email already exists"},
        422: {"description": "Validation error"}
    }
)
async def create_user(user_data: UserCreate):
    """
    Create a new user.
    
    - **username**: Must be unique, 3-50 characters, alphanumeric with underscores/hyphens
    - **email**: Must be unique and valid email format
    - **password**: Must be at least 8 characters with uppercase, lowercase, digit, and special character
    - **first_name**: Optional, 1-100 characters
    - **last_name**: Optional, 1-100 characters
    - **phone**: Optional, international format
    - **bio**: Optional, max 500 characters
    
    User lists cache is invalidated after successful creation.
    """
    try:
        user = get_user_service().create_user(user_data)
        
        # Invalidate user lists cache after creation
        await UserCache.invalidate_users_lists()
        logger.info(f"🗑️ User lists cache invalidated after creating user")
        
        logger.info(f"API: Created user {user.username} ({user.id})")
        return user
    except (ConflictError, ValidationError) as e:
        logger.warning(f"API: User creation failed: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Get user by ID (cached)",
    description="Retrieve a specific user by their unique identifier. Results are cached for faster access.",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"}
    }
)
async def get_user(
    user_id: str = Path(..., description="Unique user identifier")
):
    """
    Get a user by their ID.
    
    - **user_id**: UUID string identifying the user
    
    User data is cached for 30 minutes to reduce database load.
    """
    try:
        # Try cache first
        logger.debug(f"Checking cache for user: {user_id}")
        cached_user = await UserCache.get_user(user_id)
        
        if cached_user:
            logger.info(f"🎯 Cache HIT: Retrieved user {cached_user.get('username')} from cache")
            return UserPublic(**cached_user)
        
        # Cache miss - get from database
        logger.info(f"🔄 Cache MISS: Fetching user {user_id} from database")
        user = get_user_service().get_user(user_id)
        
        # Cache the user for 30 minutes
        user_dict = user.model_dump()
        await UserCache.set_user(user_id, user_dict, ttl=1800)
        
        logger.debug(f"API: Retrieved user {user.username} ({user.id}) - cached for 30min")
        return user
        
    except NotFoundError as e:
        logger.warning(f"API: User not found: {user_id}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users with pagination and filtering (cached)",
    description="Retrieve a paginated list of users with optional filtering and search. Results are cached for better performance.",
    responses={
        200: {"description": "Users retrieved successfully"}
    }
)
async def list_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[UserStatus] = Query(None, description="Filter by user status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in username and email")
):
    """
    List users with pagination and optional filtering.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Number of records to return (default: 10, max: 100)
    - **status**: Filter by user status (active, inactive, suspended)
    - **is_verified**: Filter by email verification status
    - **search**: Search term to find users by username or email
    
    Results are cached for 10 minutes to reduce database load.
    """
    try:
        # Try to get from cache first
        cache_key = f"users_list_{pagination.skip}_{pagination.limit}_{status}_{is_verified}_{search or 'none'}"
        logger.debug(f"Checking cache for key: {cache_key}")
        
        cached_result = await UserCache.get_users_list(
            page=pagination.skip // pagination.limit + 1,
            limit=pagination.limit,
            filters={'status': status, 'is_verified': is_verified, 'search': search}
        )
        
        if cached_result:
            logger.info(f"🎯 Cache HIT: Retrieved {len(cached_result.get('items', []))} users from cache")
            return UserListResponse(**cached_result)
        
        # Cache miss - get from database
        logger.info("🔄 Cache MISS: Fetching from database")
        result = get_user_service().list_users(
            pagination=pagination,
            status=status,
            is_verified=is_verified,
            search=search
        )
        
        # Cache the result for 10 minutes
        result_dict = result.model_dump()
        await UserCache.set_users_list(
            users=result_dict,
            page=pagination.skip // pagination.limit + 1,
            limit=pagination.limit,
            ttl=600,  # 10 minutes
            filters={'status': status, 'is_verified': is_verified, 'search': search}
        )
        
        logger.debug(f"API: Listed {len(result.items)} users (total: {result.total}) - cached for 10min")
        return result
        
    except ValidationError as e:
        logger.error(f"API: Error listing users: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    summary="Update user",
    description="Update an existing user with partial data.",
    responses={
        200: {"description": "User updated successfully"},
        404: {"description": "User not found"},
        409: {"description": "Username or email conflict"},
        422: {"description": "Validation error"}
    }
)
async def update_user(
    user_data: UserUpdate,
    user_id: str = Path(..., description="Unique user identifier")
):
    """
    Update a user.
    
    - **user_id**: UUID string identifying the user
    - Only provided fields will be updated
    - Username and email must remain unique if changed
    
    Cache is invalidated after successful update.
    """
    try:
        user = get_user_service().update_user(user_id, user_data)
        
        # Invalidate cache after successful update
        await UserCache.delete_user(user_id)
        await UserCache.invalidate_users_lists()
        logger.info(f"🗑️ Cache invalidated for user {user_id}")
        
        logger.info(f"API: Updated user {user.username} ({user.id})")
        return user
    except (NotFoundError, ConflictError, ValidationError) as e:
        logger.warning(f"API: User update failed for {user_id}: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.delete(
    "/{user_id}",
    summary="Delete user",
    description="Soft delete a user (marks as deleted but preserves data).",
    responses={
        200: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
        409: {"description": "User already deleted"}
    }
)
async def delete_user(
    user_id: str = Path(..., description="Unique user identifier")
):
    """
    Delete a user (soft delete).
    
    - **user_id**: UUID string identifying the user
    - This is a soft delete - the user is marked as deleted but data is preserved
    
    Cache is invalidated after successful deletion.
    """
    try:
        result = get_user_service().delete_user(user_id)
        
        # Invalidate cache after successful deletion
        await UserCache.delete_user(user_id)
        await UserCache.invalidate_users_lists()
        logger.info(f"🗑️ Cache invalidated for deleted user {user_id}")
        
        logger.info(f"API: Deleted user {user_id}")
        return result
    except (NotFoundError, ConflictError) as e:
        logger.warning(f"API: User deletion failed for {user_id}: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.patch(
    "/{user_id}/status",
    response_model=UserPublic,
    summary="Change user status",
    description="Change user status (admin operation).",
    responses={
        200: {"description": "User status changed successfully"},
        404: {"description": "User not found"},
        409: {"description": "Invalid status transition"}
    }
)
async def change_user_status(
    new_status: UserStatus,
    user_id: str = Path(..., description="Unique user identifier")
):
    """
    Change user status (admin operation).
    
    - **user_id**: UUID string identifying the user
    - **new_status**: New status to set (active, inactive, suspended)
    - Cannot change status of deleted users
    """
    try:
        user = get_user_service().change_user_status(user_id, new_status)
        logger.info(f"API: Changed status for user {user.username} ({user.id}) to {new_status}")
        return user
    except (NotFoundError, ConflictError) as e:
        logger.warning(f"API: Status change failed for {user_id}: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/username/{username}",
    response_model=UserPublic,
    summary="Get user by username",
    description="Retrieve a user by their username.",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"}
    }
)
async def get_user_by_username(
    username: str = Path(..., min_length=3, max_length=50, description="Username to search for")
):
    """
    Get a user by username.
    
    - **username**: The username to search for (case-insensitive)
    """
    try:
        user = get_user_service().get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with username '{username}' not found"
            )
        logger.debug(f"API: Retrieved user by username: {user.username} ({user.id})")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error getting user by username {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.get(
    "/email/{email}",
    response_model=UserPublic,
    summary="Get user by email",
    description="Retrieve a user by their email address.",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"}
    }
)
async def get_user_by_email(
    email: str = Path(..., description="Email address to search for")
):
    """
    Get a user by email.
    
    - **email**: The email address to search for (case-insensitive)
    """
    try:
        user = get_user_service().get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' not found"
            )
        logger.debug(f"API: Retrieved user by email: {user.username} ({user.id})")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error getting user by email {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.get(
    "/stats/summary",
    response_model=Dict[str, Any],
    summary="Get user statistics",
    description="Get comprehensive statistics about users in the system.",
    responses={
        200: {"description": "Statistics retrieved successfully"}
    }
)
async def get_user_stats():
    """
    Get user statistics.
    
    Returns comprehensive statistics including:
    - Total user count
    - Status distribution
    - Verification rates
    """
    try:
        stats = get_user_service().get_user_stats()
        logger.debug("API: Retrieved user statistics")
        return stats
    except ValidationError as e:
        logger.error(f"API: Error getting user stats: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/export/json",
    response_model=List[Dict[str, Any]],
    summary="Export users",
    description="Export all users data in JSON format.",
    responses={
        200: {"description": "Users exported successfully"}
    }
)
async def export_users():
    """
    Export all users in JSON format.
    
    Returns all active users (excluding deleted ones) with public information.
    """
    try:
        users = get_user_service().export_users(format="json")
        logger.info(f"API: Exported {len(users)} users")
        return users
    except ValidationError as e:
        logger.error(f"API: Error exporting users: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))