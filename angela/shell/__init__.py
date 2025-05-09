# In angela/shell/__init__.py
"""
Shell integration and terminal formatting for Angela CLI.

This package provides shell hook scripts, terminal formatting utilities,
interactive feedback mechanisms, and command completion functionality.
"""

# Export main components that other modules will need
from .formatter import terminal_formatter
from .inline_feedback import inline_feedback
from .completion import completion_handler

# Load advanced_formatter extensions (this extends terminal_formatter)
from . import advanced_formatter

__all__ = ['terminal_formatter', 'inline_feedback', 'completion_handler']
