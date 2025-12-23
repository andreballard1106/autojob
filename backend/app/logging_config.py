"""
Centralized Logging Configuration

Ensures all errors and important events are properly logged to the terminal.
"""

import logging
import sys
from typing import Optional

from app.config import settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset levelname for other handlers
        record.levelname = levelname
        
        return formatted


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure application-wide logging.
    
    Args:
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    elif settings.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Create formatter
    formatter = ColoredFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    
    # App loggers - show all messages
    for logger_name in ['app', 'automation', 'autofill']:
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(level)
        app_logger.propagate = True
    
    # SQLAlchemy - controlled by sql_echo setting
    sqlalchemy_level = logging.DEBUG if settings.sql_echo else logging.WARNING
    logging.getLogger('sqlalchemy.engine').setLevel(sqlalchemy_level)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # Uvicorn - show access logs and errors
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    
    # Third-party libraries - reduce noise
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured with level: {logging.getLevelName(level)}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Usually __name__ from the calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

