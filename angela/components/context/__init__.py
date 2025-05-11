# angela/context/__init__.py
"""Context management package for Angela CLI.

This package provides context awareness and tracking for files, projects,
sessions, and user preferences to enhance AI operations with relevant
environmental information.
"""

# Export core context components
from .manager import context_manager
from .session import session_manager
from .history import history_manager
from .preferences import preferences_manager
from .file_detector import detect_file_type, get_content_preview
from .file_resolver import file_resolver
from .file_activity import file_activity_tracker, ActivityType
from .enhancer import context_enhancer

# Export enhanced context components
from .project_inference import project_inference
from .enhanced_file_activity import enhanced_file_activity_tracker
from .semantic_context_manager import semantic_context_manager
from .project_state_analyzer import project_state_analyzer

# Define initialization function instead of running at import time
def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    import asyncio
    if context_manager.project_root:
        asyncio.create_task(
            project_inference.infer_project_info(context_manager.project_root)
        )

# Define the public API
__all__ = [
    # Core context components
    'context_manager',
    'session_manager',
    'history_manager',
    'preferences_manager',
    
    # File-related utilities
    'detect_file_type',
    'get_content_preview',
    'file_resolver',
    'file_activity_tracker',
    'ActivityType',
    
    # Enhanced context components
    'context_enhancer',
    'project_inference',
    'enhanced_file_activity_tracker',
    'semantic_context_manager',
    'project_state_analyzer',
    
    # Initialization functions
    'initialize_project_inference'
]
