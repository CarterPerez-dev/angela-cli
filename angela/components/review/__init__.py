# angela/review/__init__.py
"""
Review components for Angela CLI.

This package provides functionality for reviewing, diffing, and applying 
feedback to code and text content.
"""

from .diff_manager import diff_manager
from .feedback import feedback_manager

__all__ = ['diff_manager', 'feedback_manager']
