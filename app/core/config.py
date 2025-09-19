"""
Configuration settings for the FastAPI application.
Uses Pydantic settings for environment variable validation.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import secrets


class Settings(BaseSettings):
    """Application settings."""
    
    # General
    PROJECT_NAME: str = "Awasome FastAPI"
    PROJECT_VERSION: str = "1.0.0"
    VERSION: str = "1.0.0"  # Alias for backward compatibility
    DESCRIPTION: str = "Awasome FastAPI Microservice with comprehensive features"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    API_PREFIX: str = "/api"
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    # CouchDB Configuration
    COUCHDB_USER: str = Field(env="COUCHDB_USER")
    COUCHDB_PASSWORD: str = Field(env="COUCHDB_PASSWORD")
    COUCHDB_HOST: str = Field(default="localhost", env="COUCHDB_HOST")
    COUCHDB_PORT: int = Field(default=5984, env="COUCHDB_PORT")
    COUCHDB_DB_NAME: str = Field(env="COUCHDB_DB_NAME")
    COUCHDB_CREATE_DB_IF_NOT_EXISTS: bool = Field(default=True, env="COUCHDB_CREATE_DB_IF_NOT_EXISTS")
    
    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Cache Configuration
    CACHE_DEFAULT_TTL: int = Field(default=3600, env="CACHE_DEFAULT_TTL")  # 1 hour
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @field_validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment values."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()
    
    @property
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if environment is development."""
        return self.ENVIRONMENT == "development"
    
    @property
    def couchdb_full_url(self) -> str:
        """Get full CouchDB URL with credentials."""
        return f"http://{self.COUCHDB_USER}:{self.COUCHDB_PASSWORD}@{self.COUCHDB_HOST}:{self.COUCHDB_PORT}"
    
    @property
    def couchdb_url_no_auth(self) -> str:
        """Get CouchDB URL without credentials."""
        return f"http://{self.COUCHDB_HOST}:{self.COUCHDB_PORT}"
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Create global settings instance
settings = Settings()