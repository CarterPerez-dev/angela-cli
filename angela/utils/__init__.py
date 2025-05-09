# angela/utils/__init__.py
"""
Utility functions for Angela CLI.

This package provides common utilities like logging, configuration management,
and helper functions used throughout the application.
"""

from .logging import setup_logging, get_logger

# EnhancedLogger is available but not exported by default
# Import directly from enhanced_logging when needed

__all__ = ['setup_logging', 'get_logger']
