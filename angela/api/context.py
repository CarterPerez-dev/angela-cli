# angela/api/context.py
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
    from angela.components.context.manager import ContextManager, context_manager
    return registry.get_or_create("context_manager", ContextManager, factory=lambda: context_manager)

# Session Manager API
def get_session_manager():
    """Get the session manager instance."""
    from angela.components.context.session import SessionManager, session_manager 
    return registry.get_or_create("session_manager", SessionManager, factory=lambda: session_manager)

# History Manager API
def get_history_manager():
    """Get the history manager instance."""
    from angela.components.context.history import HistoryManager, history_manager
    return registry.get_or_create("history_manager", HistoryManager, factory=lambda: history_manager)

# Preferences Manager API
def get_preferences_manager():
    """Get the preferences manager instance."""
    from angela.components.context.preferences import PreferencesManager, preferences_manager 
    return registry.get_or_create("preferences_manager", PreferencesManager, factory=lambda: preferences_manager)

# File Activity API
def get_file_activity_tracker():
    """Get the file activity tracker instance."""
    from angela.components.context.file_activity import FileActivityTracker, file_activity_tracker
    return registry.get_or_create("file_activity_tracker", FileActivityTracker, factory=lambda: file_activity_tracker)

def get_activity_type():
    """Get the ActivityType enum from file_activity."""
    from angela.components.context.file_activity import ActivityType
    return ActivityType

# Enhanced File Activity API
def get_enhanced_file_activity_tracker():
    """Get the enhanced file activity tracker instance."""
    from angela.components.context.enhanced_file_activity import EnhancedFileActivityTracker, enhanced_file_activity_tracker 
    return registry.get_or_create("enhanced_file_activity_tracker", EnhancedFileActivityTracker, factory=lambda: enhanced_file_activity_tracker)

def get_entity_type():
    """Get the EntityType enum from enhanced_file_activity."""
    from angela.components.context.enhanced_file_activity import EntityType
    return EntityType

# File Detector API
def get_file_detector():
    """Get the file detection functions."""
    from angela.components.context.file_detector import detect_file_type, get_content_preview
    
    class FileDetector: # This class is defined locally
        def detect_file_type(self, path: Path) -> Dict[str, Any]:
            return detect_file_type(path)
            
        def get_content_preview(self, path: Path, max_lines: int = 10, max_chars: int = 1000) -> Optional[str]:
            return get_content_preview(path, max_lines, max_chars)
    
    return registry.get_or_create("file_detector", FileDetector, factory=lambda: FileDetector()) 

# File Resolver API
def get_file_resolver():
    """Get the file resolver instance."""
    from angela.components.context.file_resolver import FileResolver, file_resolver 
    return registry.get_or_create("file_resolver", FileResolver, factory=lambda: file_resolver)

# Project Inference API
def get_project_inference():
    """Get the project inference instance."""
    from angela.components.context.project_inference import ProjectInference, project_inference 
    return registry.get_or_create("project_inference", ProjectInference, factory=lambda: project_inference)

# Project State Analyzer API
def get_project_state_analyzer():
    """Get the project state analyzer instance."""
    from angela.components.context.project_state_analyzer import ProjectStateAnalyzer, project_state_analyzer 
    return registry.get_or_create("project_state_analyzer", ProjectStateAnalyzer, factory=lambda: project_state_analyzer)

# Semantic Context Manager API
def get_semantic_context_manager():
    """Get the semantic context manager instance."""
    from angela.components.context.semantic_context_manager import SemanticContextManager, semantic_context_manager 
    return registry.get_or_create("semantic_context_manager", SemanticContextManager, factory=lambda: semantic_context_manager)

# Context Enhancer API
def get_context_enhancer():
    """Get the context enhancer instance."""
    from angela.components.context.enhancer import ContextEnhancer, context_enhancer 
    return registry.get_or_create("context_enhancer", ContextEnhancer, factory=lambda: context_enhancer)

# Get file detector function
def get_file_detector_func():
    """Get the file detection function."""
    from angela.components.context.file_detector import detect_file_type
    return detect_file_type

# Initialize functions
def initialize_project_inference():
    """Initialize project inference for the current project in background."""
    import threading
    project_root = get_context_manager().project_root
    
    # Only attempt to run the inference if a project root is detected
    if project_root:
        from angela.utils.async_utils import run_async_background
        from angela.utils.logging import get_logger
        logger = get_logger(__name__)
        
        logger.debug(f"Starting background project inference for {project_root}")
        
        # Start project inference in background without waiting for results
        run_async_background(
            get_project_inference().infer_project_info(project_root),
            callback=lambda _: logger.debug(f"Project inference completed for {project_root}"),
            error_callback=lambda e: logger.error(f"Project inference failed: {str(e)}")
        )
        
        # Also start semantic context refresh in background
        run_async_background(
            get_semantic_context_manager().refresh_context(force=True),
            callback=lambda _: logger.debug("Semantic context refresh completed"),
            error_callback=lambda e: logger.error(f"Semantic context refresh failed: {str(e)}")
        )
