# angela/safety/validator.py
"""
Safety validation for operations.

This module validates operations against safety policies and constraints
before they are executed.
"""
import os
import re
import shlex
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from angela.constants import RISK_LEVELS
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Define dangerous patterns that should be blocked
DANGEROUS_PATTERNS = [
    # Remove critical system directories
    (r"rm\s+(-r|-f|--recursive|--force)\s+(/|/boot|/etc|/bin|/sbin|/lib|/usr|/var|~)",
     "Removing critical system directories is not allowed"),
    
    # Format disk operations
    (r"(mkfs|fdisk|dd|shred)\s+.*(/dev/sd[a-z]|/dev/nvme[0-9])",
     "Disk formatting operations are not allowed"),
    
    # Critical system commands
    (r"(shutdown|reboot|halt|poweroff|init\s+0|init\s+6)",
     "System power commands are not allowed"),
    
    # Chmod 777 recursively
    (r"chmod\s+(-R|--recursive)\s+777",
     "Setting recursive 777 permissions is not allowed"),
    
    # Network disruption
    (r"(ifconfig|ip)\s+.*down",
     "Network interface disabling is not allowed"),
    
    # Dangerous redirects
    (r">\s*(/etc/passwd|/etc/shadow|/etc/sudoers)",
     "Writing directly to critical system files is not allowed"),
    
    # Hidden command execution
    (r";\s*rm\s+",
     "Hidden deletion commands are not allowed"),
    
    # Web download + execute
    (r"(curl|wget).*\|\s*(bash|sh)",
     "Downloading and executing scripts is not allowed"),
    
    # Disk full attack
    (r"(dd|fallocate)\s+.*if=/dev/zero",
     "Creating large files that may fill disk space is not allowed"),
    
    # Dangerous shell loops
    (r"for\s+.*\s+in\s+.*;.*rm\s+",
     "Shell loops with file deletion are not allowed"),
]

# Define patterns that would require root/sudo access
ROOT_PATTERNS = [
    r"^sudo\s+",
    r"^pkexec\s+",
    r"^su\s+(-|--|-c|\w+)\s+",
    r"(chmod|chown|chgrp)\s+.*(/usr/|/etc/|/bin/|/sbin/|/lib/|/var/)",
    r"(touch|rm|mv|cp)\s+.*(/usr/|/etc/|/bin/|/sbin/|/lib/|/var/)",
    r">\s*(/usr/|/etc/|/bin/|/sbin/|/lib/|/var/)",
]

class ValidationError(Exception):
    """Exception raised when a command fails validation."""
    pass


def validate_command_safety(command: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a command against safety rules.
    
    Args:
        command: The shell command to validate.
        
    Returns:
        A tuple of (is_valid, error_message). If is_valid is False,
        error_message will contain the reason.
    """
    if not command.strip():
        return True, None
    
    # Check against dangerous patterns
    for pattern, message in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            logger.warning(f"Command '{command}' blocked: {message}")
            return False, message
    
    # Check permission requirements
    if not is_superuser() and requires_superuser(command):
        logger.warning(f"Command '{command}' requires superuser privileges")
        return False, "This command requires superuser privileges, which Angela CLI doesn't have."
    
    return True, None


def requires_superuser(command: str) -> bool:
    """
    Check if a command requires superuser privileges.
    
    Args:
        command: The shell command to check.
        
    Returns:
        True if the command requires superuser privileges, False otherwise.
    """
    for pattern in ROOT_PATTERNS:
        if re.search(pattern, command):
            return True
    
    return False


def is_superuser() -> bool:
    """
    Check if the current process has superuser privileges.
    
    Returns:
        True if running as superuser, False otherwise.
    """
    return os.geteuid() == 0 if hasattr(os, 'geteuid') else False


def check_file_permission(path: Path, require_write: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Check if a file has the required permissions.
    
    Args:
        path: The path to check.
        require_write: Whether write permission is required.
        
    Returns:
        A tuple of (has_permission, error_message). If has_permission is False,
        error_message will contain the reason.
    """
    try:
        if not path.exists():
            # If the file doesn't exist, check if the parent directory is writable
            if require_write:
                parent = path.parent
                if not parent.exists():
                    return False, f"Parent directory {parent} does not exist"
                if not os.access(parent, os.W_OK):
                    return False, f"No write permission for directory {parent}"
            return True, None
        
        if not os.access(path, os.R_OK):
            return False, f"No read permission for {path}"
        
        if require_write and not os.access(path, os.W_OK):
            return False, f"No write permission for {path}"
        
        return True, None
    
    except Exception as e:
        logger.exception(f"Error checking permissions for {path}: {str(e)}")
        return False, f"Permission check failed: {str(e)}"


def validate_operation(operation_type: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a high-level operation against safety rules.
    
    Args:
        operation_type: The type of operation (e.g., 'create_file', 'delete_file').
        params: Parameters for the operation.
        
    Returns:
        A tuple of (is_valid, error_message). If is_valid is False,
        error_message will contain the reason.
    """
    try:
        if operation_type == 'create_file':
            path = Path(params.get('path', ''))
            return check_file_permission(path, require_write=True)
        
        elif operation_type == 'write_file':
            path = Path(params.get('path', ''))
            return check_file_permission(path, require_write=True)
        
        elif operation_type == 'read_file':  # Add this handler
            path = Path(params.get('path', ''))
            return check_file_permission(path, require_write=False)
            
        elif operation_type == 'delete_file':
            path = Path(params.get('path', ''))
            # Check if this is a system file
            system_dirs = ['/bin', '/sbin', '/lib', '/usr', '/etc', '/var']
            if any(str(path).startswith(dir) for dir in system_dirs):
                return False, f"Deleting system files is not allowed: {path}"
            
            return check_file_permission(path, require_write=True)
        
        elif operation_type == 'create_directory':
            path = Path(params.get('path', ''))
            if path.exists():
                return False, f"Path already exists: {path}"
            return check_file_permission(path.parent, require_write=True)
        
        elif operation_type == 'delete_directory':
            path = Path(params.get('path', ''))
            # Check if this is a system directory
            system_dirs = ['/bin', '/sbin', '/lib', '/usr', '/etc', '/var']
            if any(str(path).startswith(dir) for dir in system_dirs):
                return False, f"Deleting system directories is not allowed: {path}"
            
            return check_file_permission(path, require_write=True)
        
        elif operation_type == 'copy_file':  # Add this handler
            source = Path(params.get('source', ''))
            destination = Path(params.get('destination', ''))
            
            # Check if source exists
            if not source.exists():
                return False, f"Source file does not exist: {source}"
                
            # Check destination permissions
            return check_file_permission(destination.parent, require_write=True)
            
        elif operation_type == 'move_file':  # Add this handler
            source = Path(params.get('source', ''))
            destination = Path(params.get('destination', ''))
            
            # Check if source exists
            if not source.exists():
                return False, f"Source file does not exist: {source}"
                
            # Check permissions for both source and destination
            source_ok, source_err = check_file_permission(source, require_write=True)
            if not source_ok:
                return False, source_err
                
            return check_file_permission(destination.parent, require_write=True)
            
        elif operation_type == 'execute_command':
            command = params.get('command', '')
            return validate_command_safety(command)
        
        # Unknown operation type
        logger.warning(f"Unknown operation type: {operation_type}")
        return False, f"Unknown operation type: {operation_type}"
    
    except Exception as e:
        logger.exception(f"Error validating operation {operation_type}: {str(e)}")
        return False, f"Validation failed: {str(e)}"
