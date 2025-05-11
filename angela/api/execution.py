# angela/api/execution.py
"""
Public API for the execution components.

This module provides functions to access execution components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Tuple, Union, Callable, Coroutine # Added Coroutine
from pathlib import Path

from angela.core.registry import registry

def get_error_recovery_manager():
    """Get the error recovery manager instance."""
    from angela.components.execution.error_recovery import ErrorRecoveryManager, error_recovery_manager
    return registry.get_or_create("error_recovery_manager", ErrorRecoveryManager, factory=lambda: error_recovery_manager)

# Execution Engine API
def get_execution_engine():
    """Get the execution engine instance."""
    from angela.components.execution.engine import ExecutionEngine, execution_engine
    return registry.get_or_create("execution_engine", ExecutionEngine, factory=lambda: execution_engine)

# Adaptive Engine API
def get_adaptive_engine():
    """Get the adaptive execution engine instance."""
    from angela.components.execution.adaptive_engine import AdaptiveExecutionEngine, adaptive_engine
    return registry.get_or_create("adaptive_engine", AdaptiveExecutionEngine, factory=lambda: adaptive_engine)

# Rollback API
def get_rollback_manager():
    """Get the rollback manager instance."""
    from angela.components.execution.rollback import RollbackManager, rollback_manager
    return registry.get_or_create("rollback_manager", RollbackManager, factory=lambda: rollback_manager)

# Execution Hooks API
def get_execution_hooks():
    """Get the execution hooks instance."""
    from angela.components.execution.hooks import ExecutionHooks, execution_hooks
    return registry.get_or_create("execution_hooks", ExecutionHooks, factory=lambda: execution_hooks)

# --- Filesystem Function Getters ---
def get_create_directory_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the create_directory function."""
    from angela.components.execution.filesystem import create_directory
    return create_directory

def get_delete_directory_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the delete_directory function."""
    from angela.components.execution.filesystem import delete_directory
    return delete_directory

def get_create_file_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the create_file function."""
    from angela.components.execution.filesystem import create_file
    return create_file

def get_read_file_func() -> Callable[..., Coroutine[Any, Any, Union[str, bytes]]]:
    """Get the read_file function."""
    from angela.components.execution.filesystem import read_file
    return read_file

def get_write_file_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the write_file function."""
    from angela.components.execution.filesystem import write_file
    return write_file

def get_delete_file_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the delete_file function."""
    from angela.components.execution.filesystem import delete_file
    return delete_file

def get_copy_file_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the copy_file function."""
    from angela.components.execution.filesystem import copy_file
    return copy_file

def get_move_file_func() -> Callable[..., Coroutine[Any, Any, bool]]:
    """Get the move_file function."""
    from angela.components.execution.filesystem import move_file
    return move_file

# Filesystem API (This returns a wrapper class, which is different from individual function getters)
def get_filesystem_functions():
    """Get filesystem functions wrapper."""
    from angela.components.execution.filesystem import (
        create_directory, delete_directory,
        create_file, read_file, write_file, delete_file,
        copy_file, move_file, FileSystemError, BACKUP_DIR
    )
    
    class FilesystemFunctions:
        def __init__(self):
            self.create_directory = create_directory
            self.delete_directory = delete_directory
            self.create_file = create_file
            self.read_file = read_file
            self.write_file = write_file
            self.delete_file = delete_file
            self.copy_file = copy_file
            self.move_file = move_file
            self.FileSystemError = FileSystemError
            self.BACKUP_DIR = BACKUP_DIR
    
    return registry.get_or_create("filesystem_functions_wrapper", FilesystemFunctions, factory=lambda: FilesystemFunctions())


# Access constants directly
def get_backup_dir():
    """Get the backup directory path."""
    from angela.components.execution.filesystem import BACKUP_DIR
    return BACKUP_DIR

# Get FileSystemError class
def get_filesystem_error_class():
    """Get the FileSystemError class."""
    from angela.components.execution.filesystem import FileSystemError
    return FileSystemError
