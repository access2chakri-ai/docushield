"""
Logging configuration for DocuShield
Clean, minimal logging with proper levels
"""
import logging
import sys
from typing import Dict, Any

def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup clean logging configuration
    - Application logs: INFO and above
    - SQLAlchemy logs: WARNING and above (no SQL queries)
    - Migration logs: INFO and above (but clean)
    """
    
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
    
    # Application loggers - keep at INFO
    logging.getLogger('app').setLevel(logging.INFO)
    logging.getLogger('migrations').setLevel(logging.INFO)
    logging.getLogger('agent').setLevel(logging.INFO)
    
    # Uvicorn logs - reduce noise
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)

def get_clean_logger(name: str) -> logging.Logger:
    """Get a logger with clean formatting"""
    return logging.getLogger(name)
