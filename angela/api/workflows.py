"""
Public API for the workflow components.

This module provides functions to access workflow components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable
from pathlib import Path

from angela.core.registry import registry

# Workflow Manager API
def get_workflow_manager():
    """Get the workflow manager instance."""
    from angela.components.workflows.manager import workflow_manager
    return registry.get_or_create("workflow_manager", lambda: workflow_manager)

# Workflow Sharing API
def get_workflow_sharing_manager():
    """Get the workflow sharing manager instance."""
    from angela.components.workflows.sharing import workflow_sharing_manager
    return registry.get_or_create("workflow_sharing_manager", lambda: workflow_sharing_manager)

# Models
def get_workflow_model_classes():
    """Get the workflow model classes."""
    from angela.components.workflows.manager import Workflow, WorkflowStep
    return Workflow, WorkflowStep
