"""
Public API for the execution components.

This module provides functions to access execution components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Tuple, Union, Callable
from pathlib import Path

from angela.core.registry import registry

# Add this function to angela/api/execution.py
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

# Filesystem API
def get_filesystem_functions():
    """Get filesystem functions."""
    from angela.components.execution.filesystem import (
        create_directory, delete_directory,
        create_file, read_file, write_file, delete_file,
        copy_file, move_file, FileSystemError, BACKUP_DIR
    )
    
    class FilesystemFunctions: # This class is defined locally
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
    
    return registry.get_or_create("filesystem_functions", FilesystemFunctions, factory=lambda: FilesystemFunctions())

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
