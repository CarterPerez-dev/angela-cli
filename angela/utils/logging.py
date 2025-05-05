"""
Logging configuration for Angela CLI.
"""
import sys
from pathlib import Path

from loguru import logger

from angela.constants import LOG_DIR, LOG_FORMAT, LOG_ROTATION, LOG_RETENTION


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
    
    logger.debug(f"Logging initialized. Log file: {log_file}")


def get_logger(name: str = "angela"):
    """
    Get a logger instance with the given name.
    
    Args:
        name: The name for the logger.
        
    Returns:
        A logger instance.
    """
    return logger.bind(name=name)
