"""
Enhanced Pydantic models with advanced validation and serialization.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import re
from uuid import UUID


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username must be between 3 and 50 characters",
        example="john_doe"
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address",
        example="john.doe@example.com"
    )
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="User's first name",
        example="John"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="User's last name",
        example="Doe"
    )
    phone: Optional[str] = Field(
        None,
        pattern=r"^\+?[\d\s\-\(\)]+$",
        description="Phone number in international format",
        example="+1234567890"
    )
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="User biography",
        example="Software developer passionate about Python"
    )
    
    @field_validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @field_validator('first_name', 'last_name')
    def validate_names(cls, v):
        """Validate name fields."""
        if v and not re.match(r'^[a-zA-ZÀ-ÿ\s\'-]+$', v):
            raise ValueError('Names must contain only letters, spaces, apostrophes, and hyphens')
        return v.title() if v else v


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be at least 8 characters long",
        example="securePassword123!"
    )
    confirm_password: str = Field(
        ...,
        description="Password confirmation",
        example="securePassword123!"
    )
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Validate that passwords match."""
        if self.password and self.confirm_password and self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
    
    @field_validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="Username must be between 3 and 50 characters"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Valid email address"
    )
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="User's first name"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="User's last name"
    )
    phone: Optional[str] = Field(
        None,
        description="User phone number",
        pattern=r"^\+?1?\d{9,15}$",
        examples=["+33123456789", "0123456789"]
    )
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="User biography"
    )
    status: Optional[UserStatus] = Field(
        None,
        description="User status"
    )
    
    @field_validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must contain only letters, numbers, underscores, and hyphens')
        return v.lower() if v else v


class UserInDB(UserBase):
    """Schema for user stored in database."""
    
    id: str = Field(..., description="Unique user identifier")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User status")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    password_hash: str = Field(..., description="Hashed password")
    is_verified: bool = Field(default=False, description="Email verification status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(default=0, description="Number of times user has logged in")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional user metadata"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567890",
                "bio": "Software developer",
                "status": "active",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "is_verified": True,
                "last_login": "2023-01-01T12:00:00Z",
                "login_count": 10
            }
        }


class UserPublic(UserBase):
    """Schema for public user representation (without sensitive data)."""
    
    id: str = Field(..., description="Unique user identifier")
    status: UserStatus = Field(..., description="User status")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    is_verified: bool = Field(..., description="Email verification status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567890",
                "bio": "Software developer",
                "status": "active",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "is_verified": True,
                "last_login": "2023-01-01T12:00:00Z"
            }
        }


class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip",
        example=0
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of records to return (max 100)",
        example=10
    )


class PaginatedResponse(BaseSchema):
    """Schema for paginated responses."""
    
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")
    has_more: bool = Field(..., description="Whether there are more items")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "skip": 0,
                "limit": 10,
                "has_more": True
            }
        }


class UserListResponse(PaginatedResponse):
    """Schema for paginated user list response."""
    
    items: List[UserPublic] = Field(..., description="List of users")


class HealthCheck(BaseSchema):
    """Schema for health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp in ISO format")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    database: Dict[str, Any] = Field(..., description="Database connection status")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2023-01-01T12:00:00Z",
                "version": "1.0.0",
                "uptime": 3600.0,
                "database": {
                    "status": "connected",
                    "response_time_ms": 5.2
                }
            }
        }