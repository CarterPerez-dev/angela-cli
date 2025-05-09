# angela/utils/__init__.py
"""
Utility functions for Angela CLI.

This package provides common utilities like logging, configuration management,
and helper functions used throughout the application.
"""

from .logging import setup_logging, get_logger



__all__ = ['setup_logging', 'get_logger']
