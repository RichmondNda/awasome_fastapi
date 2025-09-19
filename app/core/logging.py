"""
Logging configuration for the application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Override default log level
        log_file: Optional file to write logs to
    """
    level = log_level or settings.LOG_LEVEL
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            *([] if log_file is None else [logging.FileHandler(log_file)])
        ]
    )
    
    # Configure specific loggers
    if settings.ENVIRONMENT == "production":
        # Reduce noise in production
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    else:
        # More verbose in development
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    
    # Suppress CouchDB connection logs unless DEBUG
    if level.upper() != "DEBUG":
        logging.getLogger("couchdb").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)