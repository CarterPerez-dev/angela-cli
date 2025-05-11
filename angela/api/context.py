"""
Public API for context components.

This module provides functions to access context components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable
from pathlib import Path

from angela.core.registry import registry

# Context Manager API
def get_context_manager():
    """Get the context manager instance."""
    from angela.components.context.manager import context_manager
    return registry.get_or_create("context_manager", lambda: context_manager)

# Session Manager API
def get_session_manager():
    """Get the session manager instance."""
    from angela.components.context.session import session_manager
    return registry.get_or_create("session_manager", lambda: session_manager)

# History Manager API
def get_history_manager():
    """Get the history manager instance."""
    from angela.components.context.history import history_manager
    return registry.get_or_create("history_manager", lambda: history_manager)

# Preferences Manager API
def get_preferences_manager():
    """Get the preferences manager instance."""
    from angela.components.context.preferences import preferences_manager
    return registry.get_or_create("preferences_manager", lambda: preferences_manager)

# File Activity API
def get_file_activity_tracker():
    """Get the file activity tracker instance."""
    from angela.components.context.file_activity import file_activity_tracker
    return registry.get_or_create("file_activity_tracker", lambda: file_activity_tracker)

def get_activity_type():
    """Get the ActivityType enum from file_activity."""
    from angela.components.context.file_activity import ActivityType
    return ActivityType

# Enhanced File Activity API
def get_enhanced_file_activity_tracker():
    """Get the enhanced file activity tracker instance."""
    from angela.components.context.enhanced_file_activity import enhanced_file_activity_tracker
    return registry.get_or_create("enhanced_file_activity_tracker", lambda: enhanced_file_activity_tracker)

def get_entity_type():
    """Get the EntityType enum from enhanced_file_activity."""
    from angela.components.context.enhanced_file_activity import EntityType
    return EntityType

# File Detector API
def get_file_detector():
    """Get the file detection functions."""
    from angela.components.context.file_detector import detect_file_type, get_content_preview
    
    class FileDetector:
        def detect_file_type(self, path: Path) -> Dict[str, Any]:
            return detect_file_type(path)
            
        def get_content_preview(self, path: Path, max_lines: int = 10, max_chars: int = 1000) -> Optional[str]:
            return get_content_preview(path, max_lines, max_chars)
    
    return registry.get_or_create("file_detector", lambda: FileDetector())

# File Resolver API
def get_file_resolver():
    """Get the file resolver instance."""
    from angela.components.context.file_resolver import file_resolver
    return registry.get_or_create("file_resolver", lambda: file_resolver)

# Project Inference API
def get_project_inference():
    """Get the project inference instance."""
    from angela.components.context.project_inference import project_inference
    return registry.get_or_create("project_inference", lambda: project_inference)

# Project State Analyzer API
def get_project_state_analyzer():
    """Get the project state analyzer instance."""
    from angela.components.context.project_state_analyzer import project_state_analyzer
    return registry.get_or_create("project_state_analyzer", lambda: project_state_analyzer)

# Semantic Context Manager API
def get_semantic_context_manager():
    """Get the semantic context manager instance."""
    from angela.components.context.semantic_context_manager import semantic_context_manager
    return registry.get_or_create("semantic_context_manager", lambda: semantic_context_manager)

# Context Enhancer API
def get_context_enhancer():
    """Get the context enhancer instance."""
    from angela.components.context.enhancer import context_enhancer
    return registry.get_or_create("context_enhancer", lambda: context_enhancer)

# Initialize functions
def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    import asyncio
    if get_context_manager().project_root:
        asyncio.create_task(
            get_project_inference().infer_project_info(get_context_manager().project_root)
        )
