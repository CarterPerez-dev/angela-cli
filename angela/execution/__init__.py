# angela/execution/__init__.py
"""
Execution components for Angela CLI.

This package provides functionality for executing commands, managing file operations,
handling errors during execution, and supporting rollback capabilities.
"""
# Export key components that other modules need
from .engine import execution_engine
from .adaptive_engine import adaptive_engine
from .rollback import rollback_manager
from .filesystem import (
    create_directory, delete_directory,
    create_file, read_file, write_file, delete_file,
    copy_file, move_file, FileSystemError
)
from .hooks import execution_hooks

__all__ = [
    'execution_engine', 
    'adaptive_engine',
    'rollback_manager',
    'execution_hooks',
    'create_directory', 'delete_directory',
    'create_file', 'read_file', 'write_file', 'delete_file',
    'copy_file', 'move_file', 'FileSystemError'
]
