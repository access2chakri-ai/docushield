"""
Logging configuration for DocuShield
Environment-aware logging with proper levels
"""
import logging
import sys
import os
from typing import Dict, Any

def setup_logging(log_level: str = None) -> None:
    """
    Setup environment-aware logging configuration
    - Production: ERROR and above only
    - Development: INFO and above
    - SQLAlchemy logs: WARNING and above (no SQL queries)
    """
    
    # Determine log level based on environment
    if log_level is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production":
            log_level = "ERROR"
        else:
            log_level = "INFO"
    
    # Root logger configuration
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stdout
    )
    
    # Silence SQLAlchemy query logs (too verbose)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Keep important SQLAlchemy logs
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    # Application loggers - environment aware
    app_level = logging.ERROR if os.getenv("ENVIRONMENT", "development").lower() == "production" else logging.INFO
    logging.getLogger('app').setLevel(app_level)
    logging.getLogger('migrations').setLevel(app_level)
    logging.getLogger('agent').setLevel(app_level)
    
    # Uvicorn logs - reduce noise
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)

def get_clean_logger(name: str) -> logging.Logger:
    """Get a logger with clean formatting"""
    return logging.getLogger(name)
