"""Context management package for Angela CLI."""

from .manager import context_manager
from .session import session_manager
from .history import history_manager
from .preferences import preferences_manager
from .file_detector import detect_file_type, get_content_preview
from .file_resolver import file_resolver
from .file_activity import file_activity_tracker, ActivityType
from .enhancer import context_enhancer

# Initialize project inference in the background when importing this package
import asyncio
from .project_inference import project_inference

def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    from .manager import context_manager
    if context_manager.project_root:
        asyncio.create_task(
            project_inference.infer_project_info(context_manager.project_root)
        )

# Schedule initialization to run soon but not block import
asyncio.get_event_loop().call_soon(initialize_project_inference)
