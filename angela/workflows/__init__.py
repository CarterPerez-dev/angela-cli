# angela/workflows/__init__.py
"""
Workflow management for Angela CLI.

This package handles creating, managing, and executing user-defined
workflows - reusable sequences of commands that can be invoked by name.
"""

# Export the main components that other modules will need
from .manager import workflow_manager
from .sharing import workflow_sharing_manager

__all__ = ['workflow_manager', 'workflow_sharing_manager']
