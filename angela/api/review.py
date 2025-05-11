"""
Public API for the review components.

This module provides functions to access review components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable
from pathlib import Path

from angela.core.registry import registry

# Diff Manager API
def get_diff_manager():
    """Get the diff manager instance."""
    from angela.components.review.diff_manager import diff_manager
    return registry.get_or_create("diff_manager", lambda: diff_manager)

# Feedback Manager API
def get_feedback_manager():
    """Get the feedback manager instance."""
    from angela.components.review.feedback import feedback_manager
    return registry.get_or_create("feedback_manager", lambda: feedback_manager)
