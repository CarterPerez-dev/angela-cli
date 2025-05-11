# angela/shell/__init__.py
"""
Shell integration and terminal formatting for Angela CLI.

This package provides shell hook scripts, terminal formatting utilities,
interactive feedback mechanisms, and command completion functionality.
"""

# Export main components that other modules will need
from .formatter import terminal_formatter
from .inline_feedback import inline_feedback
from .completion import completion_handler

# Ensure these exports are already defined before any code tries to use them
__all__ = ['terminal_formatter', 'inline_feedback', 'completion_handler']

# Advanced formatter will modify terminal_formatter after import,
# so we need to import it after terminal_formatter is defined and exported
# But we'll use try/except to avoid blocking initialization if there's an issue
try:
    # Import this separately so if it fails, the rest of the module is still usable
    from . import advanced_formatter
    # No need to add to __all__ as it's meant for internal use
except Exception as e:
    from angela.utils.logging import get_logger
    logger = get_logger(__name__)
    logger.warning(f"Failed to import advanced_formatter: {str(e)}")
    # Continue without the advanced formatter - the basic formatter will still work
