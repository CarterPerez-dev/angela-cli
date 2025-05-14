# angela/components/cli/utils/__init__.py
"""
CLI utility functions for Angela CLI.
"""
try:
    from angela.components.cli.utils.async_helpers import async_command
    __all__ = ['async_command']
except ImportError as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to import async_command: {e}")
    # Define a fallback that will raise a clear error if used
    def async_command(*args, **kwargs):
        raise ImportError("async_command could not be properly imported")
    __all__ = ['async_command']
