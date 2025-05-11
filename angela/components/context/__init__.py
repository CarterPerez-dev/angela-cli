# angela/context/__init__.py
"""Context management package for Angela CLI.

This package provides context awareness and tracking for files, projects,
sessions, and user preferences to enhance AI operations with relevant
environmental information.
"""

# Define initialization function instead of running at import time
def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    import asyncio
    from angela.api.context import get_context_manager, get_project_inference
    
    if get_context_manager().project_root:
        asyncio.create_task(
            get_project_inference().infer_project_info(get_context_manager().project_root)
        )

# Export the initialization function only
__all__ = ['initialize_project_inference']
