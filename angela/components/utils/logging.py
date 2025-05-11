# angela/utils/logging.py
"""
Logging configuration for Angela CLI.
"""
import sys
import logging
from pathlib import Path

from loguru import logger
from angela.constants import LOG_DIR, LOG_FORMAT, LOG_ROTATION, LOG_RETENTION
from angela.utils.enhanced_logging import EnhancedLogger

# Dictionary to store enhanced logger instances
_enhanced_loggers = {}

def setup_logging(debug: bool = False) -> None:
    """
    Configure the application logging.
    
    Args:
        debug: Whether to enable debug logging.
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Remove default handlers
    logger.remove()
    
    # Add console handler with appropriate level
    log_level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=log_level,
        diagnose=debug,  # Include variable values in traceback if debug is True
    )
    
    # Add file handler
    log_file = LOG_DIR / "angela.log"
    logger.add(
        log_file,
        format=LOG_FORMAT,
        level="INFO",
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
    )
    
    # Add structured JSON log file
    json_log_file = LOG_DIR / "angela_structured.log"
    logger.add(
        json_log_file,
        serialize=True,  # Output as JSON
        level="INFO",
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
    )
    
    logger.debug(f"Logging initialized. Log files: {log_file}, {json_log_file}")


def get_logger(name: str = "angela") -> EnhancedLogger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: The name for the logger.
        
    Returns:
        An enhanced logger instance.
    """
    # Check if we already have an enhanced logger for this name
    if name in _enhanced_loggers:
        return _enhanced_loggers[name]
    
    # Create a new enhanced logger
    enhanced_logger = EnhancedLogger(name)
    _enhanced_loggers[name] = enhanced_logger
    
    return enhanced_logger
