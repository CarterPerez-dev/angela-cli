# angela/context/__init__.py
"""Context management package for Angela CLI.

This package provides context awareness and tracking for files, projects,
sessions, and user preferences to enhance AI operations with relevant
environmental information.
"""

# Define initialization function instead of running at import time
def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    # Forward to the API implementation to ensure consistent behavior
    from angela.api.context import initialize_project_inference as api_initialize
    api_initialize()

# Export the initialization function only
__all__ = ['initialize_project_inference']
