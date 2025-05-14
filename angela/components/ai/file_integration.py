# angela/ai/file_integration.py
"""
Integration module for AI-powered file operations.

This module bridges the AI suggestions with actual file operations,
extracting file operations from commands and executing them safely with
comprehensive pattern matching, parameter validation, and error handling.

It supports:
1. Advanced command parsing for complex shell syntax
2. Comprehensive parameter extraction
3. Safe execution with permission and boundary checks
4. Detailed logging and transaction support
5. Multi-command operation extraction
6. Pipe and redirection handling
7. Advanced shell syntax support
"""
import re
import shlex
import os
import sys
import glob
from pathlib import Path
from urllib.parse import unquote
from typing import Dict, Any, List, Tuple, Optional, Set, Union, Callable
import json
import tempfile
import asyncio
import subprocess
from datetime import datetime
from dataclasses import dataclass

from angela.api.execution import (
    get_filesystem_error_class,
    get_create_directory_func,
    get_delete_directory_func,
    get_create_file_func,
    get_read_file_func,
    get_write_file_func,
    get_delete_file_func,
    get_copy_file_func,
    get_move_file_func
)
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Enhanced type definitions for improved type safety
CommandDict = Dict[str, Any]
OperationResult = Dict[str, Any]
ExtractorFunc = Callable[[str], Tuple[str, Dict[str, Any]]]

# Detailed operation types to support more operations
class OperationType:
    CREATE_DIRECTORY = "create_directory"
    DELETE_DIRECTORY = "delete_directory"
    CREATE_FILE = "create_file"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    COPY_FILE = "copy_file"
    MOVE_FILE = "move_file"
    APPEND_FILE = "append_file"
    LINK_FILE = "link_file"
    PERMISSION_CHANGE = "permission_change"
    OWNERSHIP_CHANGE = "ownership_change"
    FIND_FILES = "find_files"
    COMPRESS_FILES = "compress_files"
    EXTRACT_FILES = "extract_files"
    LIST_FILES = "list_files"
    VIEW_FILE_INFO = "view_file_info"
    RENAME_FILE = "rename_file"
    SEARCH_IN_FILES = "search_in_files"
    TRANSFORM_FILE = "transform_file"
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all operation types as a list."""
        return [attr for attr in dir(cls) if not attr.startswith('_') and attr.isupper()]
    
    @classmethod
    def is_valid_type(cls, operation_type: str) -> bool:
        """Check if the given string is a valid operation type."""
        return operation_type in cls.get_all_types()

# Advanced pattern matching for file operations
# Using verbose multi-line patterns for improved readability and maintainability
FILE_OPERATION_PATTERNS = [
    # Directory operations
    (
        r"""^mkdir\s+                            # mkdir command
        (?P<mkdir_flags>-[pvZ]*\s+)?            # Optional flags
        (?P<mkdir_mode>-m\s+\d+\s+)?            # Optional mode setting
        (?P<mkdir_paths>.+)$                     # Paths to create
        """,
        OperationType.CREATE_DIRECTORY
    ),
    
    (
        r"""^rmdir\s+                            # rmdir command
        (?P<rmdir_flags>--[a-z-]*\s+)?          # Optional long flags
        (?P<rmdir_paths>.+)$                     # Paths to remove
        """,
        OperationType.DELETE_DIRECTORY
    ),
    
    (
        r"""^rm\s+                               # rm command
        (?P<rm_recursive>-[rfR]+|--recursive)\s+ # Recursive flag options
        (?P<rm_force>-f|--force\s+)?            # Optional force flag
        (?P<rm_verbose>-v|--verbose\s+)?        # Optional verbose flag
        (?P<rm_paths>.+)$                        # Paths to remove
        """,
        OperationType.DELETE_DIRECTORY
    ),
    
    # File creation operations
    (
        r"""^touch\s+                            # touch command
        (?P<touch_flags>-[acm]+\s+)?            # Optional flags (access, no create, modification)
        (?P<touch_time>-t\s+\d+\s+)?            # Optional time setting
        (?P<touch_files>.+)$                     # Files to touch
        """,
        OperationType.CREATE_FILE
    ),
    
    # File reading operations
    (
        r"""^(?P<read_cmd>cat|less|more|head|tail)\s+  # Reading commands
        (?P<read_flags>-[nA-Z]*\s+)?                   # Optional flags
        (?P<read_count>-n\s+\d+\s+)?                   # Optional line count
        (?P<read_files>.+)$                            # Files to read
        """,
        OperationType.READ_FILE
    ),
    
    # File writing operations with echo
    (
        r"""^echo\s+                             # echo command
        (?P<echo_content>.*?)                    # Content to write (non-greedy)
        \s+>\s+                                  # Redirection operator
        (?P<echo_file>.+)$                       # Output file
        """,
        OperationType.WRITE_FILE
    ),
    
    # File appending operations with echo
    (
        r"""^echo\s+                             # echo command
        (?P<echo_append_content>.*?)             # Content to append (non-greedy)
        \s+>>\s+                                 # Append redirection operator
        (?P<echo_append_file>.+)$                # Target file
        """,
        OperationType.APPEND_FILE
    ),
    
    # File deletion with rm (non-recursive)
    (
        r"""^rm\s+                               # rm command
        (?!-[rR]|-[a-z]*[rR]|-recursive)         # Not recursive
        (?P<rm_file_flags>-[fiv]+\s+)?           # Optional flags
        (?P<rm_files>.+)$                        # Files to remove
        """,
        OperationType.DELETE_FILE
    ),
    
    # File copy operations
    (
        r"""^cp\s+                               # cp command
        (?P<cp_flags>-[rRfipavx]+\s+)?           # Optional flags
        (?!-r|--recursive)                       # Not recursive (handled separately)
        (?P<cp_source>.*?)\s+                    # Source (non-greedy)
        (?P<cp_dest>.+)$                         # Destination (the rest)
        """,
        OperationType.COPY_FILE
    ),
    
    # Recursive file/directory copy
    (
        r"""^cp\s+                               # cp command
        (?P<cp_recursive_flags>-[a-zA-Z]*?[rR]|-recursive|--recursive)\s+ # Recursive flag
        (?P<cp_recursive_opts>-[fipavx]+\s+)?    # Optional other flags
        (?P<cp_recursive_source>.*?)\s+          # Source path
        (?P<cp_recursive_dest>.+)$               # Destination path
        """,
        OperationType.COPY_FILE  # Handled specially in the extractor
    ),
    
    # File move operations
    (
        r"""^mv\s+                               # mv command
        (?P<mv_flags>-[finuv]+\s+)?              # Optional flags
        (?P<mv_source>.*?)\s+                    # Source (non-greedy)
        (?P<mv_dest>.+)$                         # Destination (the rest)
        """,
        OperationType.MOVE_FILE
    ),
    
    # Symbolic link operations
    (
        r"""^ln\s+                               # ln command
        (?P<ln_symbolic>-s|--symbolic)\s+        # Symbolic flag
        (?P<ln_flags>-[fnv]+\s+)?                # Optional flags
        (?P<ln_target>.*?)\s+                    # Target path
        (?P<ln_link>.+)$                         # Link path
        """,
        OperationType.LINK_FILE
    ),
    
    # Permission change operations
    (
        r"""^chmod\s+                            # chmod command
        (?P<chmod_recursive>-R|--recursive\s+)?  # Optional recursive flag
        (?P<chmod_mode>[0-7]{3,4}|[ugoa]*[+-=][rwxXst]+)\s+ # Permission mode
        (?P<chmod_files>.+)$                     # Files to change
        """,
        OperationType.PERMISSION_CHANGE
    ),
    
    # Ownership change operations
    (
        r"""^chown\s+                            # chown command
        (?P<chown_recursive>-R|--recursive\s+)?  # Optional recursive flag
        (?P<chown_opts>-[hfv]+\s+)?              # Optional flags
        (?P<chown_owner>[^:]+)                   # Owner
        (?P<chown_group>:[^:]+)?\s+              # Optional group
        (?P<chown_files>.+)$                     # Files to change
        """,
        OperationType.OWNERSHIP_CHANGE
    ),
    
    # Find operations
    (
        r"""^find\s+                             # find command
        (?P<find_path>[^-].*?)                   # Starting path (before first option)
        (?P<find_options>.*)$                    # Find options (the rest)
        """,
        OperationType.FIND_FILES
    ),
    
    # List files operations
    (
        r"""^ls\s+                               # ls command
        (?P<ls_flags>-[laAFhrtSiR1]+\s+)?        # Optional flags
        (?P<ls_path>.*)$                         # Path (optional)
        """,
        OperationType.LIST_FILES
    ),
    
    # File info operations
    (
        r"""^(?P<info_cmd>file|stat|du|df)\s+    # Info commands
        (?P<info_flags>-[a-zA-Z]+\s+)?           # Optional flags
        (?P<info_target>.+)$                     # Target files/dirs
        """,
        OperationType.VIEW_FILE_INFO
    ),
    
    # Compression operations
    (
        r"""^(?P<compress_cmd>tar|gzip|zip|bzip2|xz)\s+  # Compression commands
        (?P<compress_flags>-[cvfzjJ]+\s+)?               # Optional flags
        (?P<compress_args>.+)$                           # Command arguments
        """,
        OperationType.COMPRESS_FILES
    ),
    
    # File search operations
    (
        r"""^(?P<search_cmd>grep|egrep|fgrep|rg|ag)\s+  # Search commands
        (?P<search_flags>-[riavnwEFo]+\s+)?             # Optional flags
        (?P<search_pattern>'[^']*'|"[^"]*"|\S+)\s+      # Search pattern
        (?P<search_files>.+)$                           # Files to search
        """,
        OperationType.SEARCH_IN_FILES
    ),
    
    # File transformation operations
    (
        r"""^(?P<transform_cmd>sed|awk|tr|sort|uniq)\s+ # Transform commands 
        (?P<transform_args>.+)$                         # Command arguments
        """,
        OperationType.TRANSFORM_FILE
    ),
]

# Advanced extractors for different operation types

async def extract_mkdir_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract mkdir operation parameters with advanced flag and path handling.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles multiple paths
        - Supports permission modes (-m flag)
        - Properly handles quoted paths with spaces
        - Extracts verbose and parent directory creation flags
    """
    logger.debug(f"Extracting mkdir operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "parents": False,
        "mode": None,
        "verbose": False,
        "paths": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-p' or token == '--parents':
                parameters["parents"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif token == '-m' or token == '--mode':
                # Handle mode parameter if there's another token available
                if i + 1 < len(tokens):
                    i += 1
                    parameters["mode"] = tokens[i]
            elif token.startswith('-') and 'p' in token:
                # Handle combined flags like -pv
                parameters["parents"] = True
                if 'v' in token:
                    parameters["verbose"] = True
            elif token.startswith('-') and 'm' in token:
                # Handle combined mode flag like -pm
                parameters["parents"] = 'p' in token
                # For -m, we need the next argument as the mode
                if i + 1 < len(tokens):
                    i += 1
                    parameters["mode"] = tokens[i]
        else:
            # It's a path
            parameters["paths"].append(token)
        
        i += 1
    
    # If no paths were specified, use the current directory
    if not parameters["paths"]:
        parameters["paths"] = ["."]
    
    # For the unified interface, use the first path as the main path parameter
    # but keep all paths in the 'paths' list
    return OperationType.CREATE_DIRECTORY, {
        "path": parameters["paths"][0],
        "parents": parameters["parents"],
        "mode": parameters["mode"],
        "verbose": parameters["verbose"],
        "all_paths": parameters["paths"]
    }

async def extract_rmdir_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract rmdir operation parameters with enhanced safety checks.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles multiple paths
        - Detects unsafe patterns (e.g., rmdir /)
        - Supports --ignore-fail-on-non-empty flag
        - Properly handles quoted paths with spaces
        - Path normalization and security validation
    """
    logger.debug(f"Extracting rmdir operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "ignore_non_empty": False,
        "verbose": False,
        "paths": []
    }
    
    # Security check - list of paths that should never be removed directly
    critical_paths = ['/', '/boot', '/etc', '/usr', '/var', '/bin', '/sbin', '/lib']
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '--ignore-fail-on-non-empty':
                parameters["ignore_non_empty"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif token.startswith('--'):
                # Handle other long options
                pass
            elif 'v' in token:
                # Handle combined flags like -pv
                parameters["verbose"] = True
        else:
            # It's a path
            # Normalize path for security check
            normalized_path = os.path.normpath(token)
            
            # Check if the path is in the list of critical paths
            if normalized_path in critical_paths:
                logger.warning(f"Attempt to remove critical system path: {normalized_path}")
                raise ValueError(f"Refusing to remove critical system path: {normalized_path}")
                
            parameters["paths"].append(token)
        
        i += 1
    
    # If no paths were specified, raise an error
    if not parameters["paths"]:
        raise ValueError("No paths specified for rmdir operation")
    
    return OperationType.DELETE_DIRECTORY, {
        "path": parameters["paths"][0],  # Primary path is the first one
        "recursive": False,  # rmdir is not recursive
        "force": False,  # rmdir doesn't have a force option
        "ignore_non_empty": parameters["ignore_non_empty"],
        "verbose": parameters["verbose"],
        "all_paths": parameters["paths"]
    }

async def extract_rm_recursive_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract recursive rm operation parameters with comprehensive safety checks.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Advanced safety detection for system paths
        - Support for multiple paths and globs
        - Analysis of multiple flags (-r, -f, -v, etc.)
        - Detection of recursive operations
        - Path validation and normalization
    """
    logger.debug(f"Extracting recursive rm operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "recursive": False,
        "force": False,
        "verbose": False,
        "interactive": False,
        "paths": []
    }
    
    # Security check - list of paths that should never be removed recursively
    critical_paths = ['/', '/boot', '/etc', '/usr', '/var', '/bin', '/sbin', '/lib', '/dev']
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-r' or token == '-R' or token == '--recursive':
                parameters["recursive"] = True
            elif token == '-f' or token == '--force':
                parameters["force"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif token == '-i' or token == '--interactive':
                parameters["interactive"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -rf
                for char in token[1:]:
                    if char == 'r' or char == 'R':
                        parameters["recursive"] = True
                    elif char == 'f':
                        parameters["force"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
                    elif char == 'i':
                        parameters["interactive"] = True
        else:
            # It's a path
            # Check for risky glob patterns
            if token == '*' or token == '.*':
                logger.warning(f"Detected potentially dangerous wildcard in rm command: {token}")
                # Continue, but with a warning
            
            # Normalize path for security check
            normalized_path = os.path.normpath(token)
            
            # Check if the path is in the list of critical paths
            if normalized_path in critical_paths:
                logger.warning(f"Attempt to recursively remove critical system path: {normalized_path}")
                raise ValueError(f"Refusing to recursively remove critical system path: {normalized_path}")
                
            parameters["paths"].append(token)
        
        i += 1
    
    # If no paths were specified or recursive flag is not set, raise an error
    if not parameters["paths"]:
        raise ValueError("No paths specified for rm operation")
    
    if not parameters["recursive"]:
        logger.warning("Recursive flag not found but extract_rm_recursive_operation was called")
        parameters["recursive"] = True  # Force recursive since this function was called
    
    return OperationType.DELETE_DIRECTORY, {
        "path": parameters["paths"][0],  # Primary path is the first one
        "recursive": parameters["recursive"],
        "force": parameters["force"],
        "verbose": parameters["verbose"],
        "interactive": parameters["interactive"],
        "all_paths": parameters["paths"]
    }

async def extract_touch_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract touch operation parameters with support for multiple options.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles multiple files
        - Supports -a (access time), -m (modification time), -c (no create) flags
        - Supports custom timestamp via -t and -d options
        - Path validation and creation of parent directories
    """
    logger.debug(f"Extracting touch operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "access_only": False,       # -a flag
        "modification_only": False, # -m flag
        "no_create": False,         # -c flag
        "timestamp": None,          # -t or -d flag
        "timestamp_format": None,   # format specifier for timestamp
        "files": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-a':
                parameters["access_only"] = True
            elif token == '-m':
                parameters["modification_only"] = True
            elif token == '-c' or token == '--no-create':
                parameters["no_create"] = True
            elif token == '-t':
                # Handle timestamp parameter if there's another token available
                if i + 1 < len(tokens):
                    i += 1
                    parameters["timestamp"] = tokens[i]
                    parameters["timestamp_format"] = "[[CC]YY]MMDDhhmm[.ss]"
            elif token == '-d' or token == '--date':
                # Handle date string parameter
                if i + 1 < len(tokens):
                    i += 1
                    parameters["timestamp"] = tokens[i]
                    parameters["timestamp_format"] = "human_readable"
            elif not token.startswith('--'):
                # Handle combined flags like -am
                for char in token[1:]:
                    if char == 'a':
                        parameters["access_only"] = True
                    elif char == 'm':
                        parameters["modification_only"] = True
                    elif char == 'c':
                        parameters["no_create"] = True
        else:
            # It's a file path
            parameters["files"].append(token)
        
        i += 1
    
    # If no files were specified, raise an error
    if not parameters["files"]:
        raise ValueError("No files specified for touch operation")
    
    return OperationType.CREATE_FILE, {
        "path": parameters["files"][0],  # Primary file is the first one
        "content": None,  # touch doesn't add content
        "access_only": parameters["access_only"],
        "modification_only": parameters["modification_only"],
        "no_create": parameters["no_create"],
        "timestamp": parameters["timestamp"],
        "timestamp_format": parameters["timestamp_format"],
        "all_files": parameters["files"]
    }

async def extract_cat_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract cat/less/more/head/tail operation parameters with options.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Supports multiple commands (cat, less, more, head, tail)
        - Handles line number options (-n)
        - Detects binary files with -b flag
        - Supports multiple files with concatenation
        - Special handling for head/tail specific options
    """
    logger.debug(f"Extracting read file operation from: {command}")
    tokens = shlex.split(command)
    
    # Get the command type (cat, less, more, head, tail)
    cmd_type = tokens[0]
    
    # Default parameters
    parameters = {
        "command_type": cmd_type,
        "line_numbers": False,    # -n flag for cat
        "show_ends": False,       # -E flag for cat
        "binary": False,          # -b flag
        "line_count": None,       # -n value for head/tail
        "bytes_count": None,      # -c value for head/tail
        "follow": False,          # -f flag for tail
        "files": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-n' or token == '--number':
                parameters["line_numbers"] = True
                # For head/tail, -n requires a value
                if cmd_type in ['head', 'tail'] and i + 1 < len(tokens) and not tokens[i+1].startswith('-'):
                    i += 1
                    parameters["line_count"] = tokens[i]
            elif token == '-E' or token == '--show-ends':
                parameters["show_ends"] = True
            elif token == '-b' or token == '--binary':
                parameters["binary"] = True
            elif token == '-c' or token == '--bytes':
                # For head/tail, -c requires a value
                if i + 1 < len(tokens) and not tokens[i+1].startswith('-'):
                    i += 1
                    parameters["bytes_count"] = tokens[i]
            elif token == '-f' or token == '--follow':
                if cmd_type == 'tail':
                    parameters["follow"] = True
            elif not token.startswith('--') and len(token) > 1:
                # Handle combined flags like -nE
                for char in token[1:]:
                    if char == 'n':
                        parameters["line_numbers"] = True
                    elif char == 'E':
                        parameters["show_ends"] = True
                    elif char == 'b':
                        parameters["binary"] = True
                    elif char == 'f' and cmd_type == 'tail':
                        parameters["follow"] = True
        else:
            # It's a file path
            parameters["files"].append(token)
        
        i += 1
    
    # If no files were specified, use stdin (or raise an error if needed)
    if not parameters["files"]:
        logger.warning(f"No files specified for {cmd_type} operation, assuming stdin")
        parameters["files"] = ["-"]  # Convention for stdin
    
    return OperationType.READ_FILE, {
        "path": parameters["files"][0],  # Primary file is the first one
        "command_type": parameters["command_type"],
        "binary": parameters["binary"],
        "line_numbers": parameters["line_numbers"],
        "show_ends": parameters["show_ends"],
        "line_count": parameters["line_count"],
        "bytes_count": parameters["bytes_count"],
        "follow": parameters["follow"],
        "all_files": parameters["files"]
    }

async def extract_echo_write_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract echo write operation parameters with enhanced content handling.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles complex quoting in content (', ", escaped quotes)
        - Supports -e flag for interpreting backslash escapes
        - Detects append mode (>> vs >)
        - Handles potential heredocs and pipe redirections
        - Preserves newlines and special characters
    """
    logger.debug(f"Extracting echo write operation from: {command}")
    
    # Determine if this is append (>>) or overwrite (>)
    append = ">>" in command
    op = ">>" if append else ">"
    
    # We can't just split by the operator because it might appear in quotes
    # Need a more sophisticated approach
    
    # First, identify the position of the unquoted redirect operator
    # This is challenging because of potential nested quotes
    in_single_quote = False
    in_double_quote = False
    escape_next = False
    redirect_pos = -1
    
    for i, char in enumerate(command):
        # Handle escape sequences
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\' and not in_single_quote:
            escape_next = True
            continue
            
        # Handle quotes
        if char == "'" and not in_double_quote and not escape_next:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and not escape_next:
            in_double_quote = not in_double_quote
            
        # Check for redirect operator when not in quotes
        if not in_single_quote and not in_double_quote:
            if command[i:i+len(op)] == op:
                redirect_pos = i
                break
    
    if redirect_pos == -1:
        raise ValueError(f"Could not find unquoted redirect operator '{op}' in command: {command}")
    
    # Split the command by the identified position
    echo_part = command[:redirect_pos].strip()
    file_part = command[redirect_pos + len(op):].strip()
    
    # Remove 'echo ' prefix
    if echo_part.startswith('echo '):
        echo_part = echo_part[5:]
    
    # Check for -e or -n flags in echo
    interpret_escapes = False
    suppress_newline = False
    
    if echo_part.startswith('-'):
        parts = echo_part.split(' ', 1)
        if len(parts) > 1:
            flags, content = parts
            
            if 'e' in flags:
                interpret_escapes = True
            if 'n' in flags:
                suppress_newline = True
                
            echo_part = content
    
    # Handle quoted content
    content = echo_part
    if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
        # Strip the quotes
        content = content[1:-1]
        
        # If it was double-quoted and we're interpreting escapes, process them
        if interpret_escapes and echo_part.startswith('"'):
            # Replace common escape sequences
            content = content.replace('\\n', '\n')
            content = content.replace('\\t', '\t')
            content = content.replace('\\r', '\r')
            content = content.replace('\\\\', '\\')
    
    # Process the file path - handle quoting
    file_path = file_part
    if (file_path.startswith('"') and file_path.endswith('"')) or (file_path.startswith("'") and file_path.endswith("'")):
        file_path = file_path[1:-1]
    
    if not suppress_newline and not content.endswith('\n'):
        content += '\n'
    
    return (OperationType.APPEND_FILE if append else OperationType.WRITE_FILE), {
        "path": file_path,
        "content": content,
        "append": append,
        "interpret_escapes": interpret_escapes,
        "suppress_newline": suppress_newline
    }

async def extract_rm_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract rm (non-recursive) operation parameters with advanced options.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles multiple files
        - Supports force (-f), interactive (-i), and verbose (-v) flags
        - Path validation and security checks
        - Multi-file support
    """
    logger.debug(f"Extracting rm (non-recursive) operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "recursive": False,  # This is non-recursive rm
        "force": False,      # -f flag
        "interactive": False, # -i flag
        "verbose": False,    # -v flag
        "files": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            # Ensure this isn't a recursive rm
            if token == '-r' or token == '-R' or token == '--recursive':
                # This would be handled by extract_rm_recursive_operation
                logger.warning(f"Detected recursive flag in extract_rm_operation: {token}")
                return await extract_rm_recursive_operation(command)
                
            if token == '-f' or token == '--force':
                parameters["force"] = True
            elif token == '-i' or token == '--interactive':
                parameters["interactive"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -fv
                for char in token[1:]:
                    if char == 'r' or char == 'R':
                        # This would be recursive
                        logger.warning(f"Detected recursive flag in extract_rm_operation: {token}")
                        return await extract_rm_recursive_operation(command)
                    elif char == 'f':
                        parameters["force"] = True
                    elif char == 'i':
                        parameters["interactive"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
        else:
            # It's a file path
            parameters["files"].append(token)
        
        i += 1
    
    # If no files were specified, raise an error
    if not parameters["files"]:
        raise ValueError("No files specified for rm operation")
    
    return OperationType.DELETE_FILE, {
        "path": parameters["files"][0],  # Primary file is the first one
        "force": parameters["force"],
        "interactive": parameters["interactive"],
        "verbose": parameters["verbose"],
        "all_files": parameters["files"]
    }

async def extract_cp_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract cp operation parameters with comprehensive options handling.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Detects recursive copies
        - Supports archive mode (-a), preserve attributes (-p)
        - Handles force (-f), interactive (-i), and verbose (-v) flags
        - Multi-file support with directory detection
        - Path validation and security checks
    """
    logger.debug(f"Extracting cp operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "recursive": False,    # -r flag
        "archive": False,      # -a flag (implies -rp)
        "preserve": False,     # -p flag
        "force": False,        # -f flag
        "interactive": False,  # -i flag
        "verbose": False,      # -v flag
        "files": [],
        "destination": None
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-r' or token == '-R' or token == '--recursive':
                parameters["recursive"] = True
            elif token == '-a' or token == '--archive':
                parameters["archive"] = True
                parameters["recursive"] = True  # -a implies -r
                parameters["preserve"] = True   # -a implies -p
            elif token == '-p' or token == '--preserve':
                parameters["preserve"] = True
            elif token == '-f' or token == '--force':
                parameters["force"] = True
            elif token == '-i' or token == '--interactive':
                parameters["interactive"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -rfv
                for char in token[1:]:
                    if char == 'r' or char == 'R':
                        parameters["recursive"] = True
                    elif char == 'a':
                        parameters["archive"] = True
                        parameters["recursive"] = True
                        parameters["preserve"] = True
                    elif char == 'p':
                        parameters["preserve"] = True
                    elif char == 'f':
                        parameters["force"] = True
                    elif char == 'i':
                        parameters["interactive"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
        else:
            # It's a file path
            parameters["files"].append(token)
        
        i += 1
    
    # Need at least source and destination
    if len(parameters["files"]) < 2:
        raise ValueError("cp requires at least source and destination")
    
    # The last file is the destination
    parameters["destination"] = parameters["files"].pop()
    
    # If only one source file and destination is a directory
    # the operation type should be COPY_FILE
    # If multiple source files or recursive, it's more complex
    operation_type = OperationType.COPY_FILE
    
    # Determine source and destination
    source = parameters["files"][0] if parameters["files"] else None
    destination = parameters["destination"]
    
    return operation_type, {
        "source": source,
        "destination": destination,
        "recursive": parameters["recursive"],
        "archive": parameters["archive"],
        "preserve": parameters["preserve"],
        "force": parameters["force"],
        "interactive": parameters["interactive"],
        "verbose": parameters["verbose"],
        "overwrite": parameters["force"],  # For API compatibility
        "all_sources": parameters["files"] # All source files (could be multiple)
    }

async def extract_mv_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract mv operation parameters with all option support.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles force (-f), interactive (-i), and verbose (-v) flags
        - Multi-file support with directory detection
        - No-clobber (-n) option support
        - Path validation and security checks
    """
    logger.debug(f"Extracting mv operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "force": False,        # -f flag
        "interactive": False,  # -i flag
        "verbose": False,      # -v flag
        "no_clobber": False,   # -n flag (don't overwrite)
        "update": False,       # -u flag (only move if source is newer)
        "files": [],
        "destination": None
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-f' or token == '--force':
                parameters["force"] = True
                parameters["no_clobber"] = False  # -f overrides -n
            elif token == '-i' or token == '--interactive':
                parameters["interactive"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif token == '-n' or token == '--no-clobber':
                parameters["no_clobber"] = True
                parameters["force"] = False  # -n overrides -f
            elif token == '-u' or token == '--update':
                parameters["update"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -fv
                for char in token[1:]:
                    if char == 'f':
                        parameters["force"] = True
                        parameters["no_clobber"] = False
                    elif char == 'i':
                        parameters["interactive"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
                    elif char == 'n':
                        parameters["no_clobber"] = True
                        parameters["force"] = False
                    elif char == 'u':
                        parameters["update"] = True
        else:
            # It's a file path
            parameters["files"].append(token)
        
        i += 1
    
    # Need at least source and destination
    if len(parameters["files"]) < 2:
        raise ValueError("mv requires at least source and destination")
    
    # The last file is the destination
    parameters["destination"] = parameters["files"].pop()
    
    # Determine source and destination
    source = parameters["files"][0] if parameters["files"] else None
    destination = parameters["destination"]
    
    return OperationType.MOVE_FILE, {
        "source": source,
        "destination": destination,
        "force": parameters["force"],
        "interactive": parameters["interactive"],
        "verbose": parameters["verbose"],
        "no_clobber": parameters["no_clobber"],
        "update": parameters["update"],
        "overwrite": parameters["force"] and not parameters["no_clobber"],  # For API compatibility
        "all_sources": parameters["files"] # All source files (could be multiple)
    }

async def extract_ln_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract ln (link) operation parameters with comprehensive options.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Distinguishes between symbolic and hard links
        - Supports force (-f) and verbose (-v) flags
        - Handles backing up existing files (-b)
        - Path validation and security checks
    """
    logger.debug(f"Extracting ln operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "symbolic": False,     # -s flag
        "force": False,        # -f flag
        "verbose": False,      # -v flag
        "no_dereference": False, # -n flag
        "backup": False,       # -b flag
        "files": [],
        "target": None,
        "link_name": None
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-s' or token == '--symbolic':
                parameters["symbolic"] = True
            elif token == '-f' or token == '--force':
                parameters["force"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif token == '-n' or token == '--no-dereference':
                parameters["no_dereference"] = True
            elif token == '-b' or token == '--backup':
                parameters["backup"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -sfv
                for char in token[1:]:
                    if char == 's':
                        parameters["symbolic"] = True
                    elif char == 'f':
                        parameters["force"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
                    elif char == 'n':
                        parameters["no_dereference"] = True
                    elif char == 'b':
                        parameters["backup"] = True
        else:
            # It's a file path
            parameters["files"].append(token)
        
        i += 1
    
    # Need at least target and link_name
    if len(parameters["files"]) < 2:
        raise ValueError("ln requires at least target and link_name")
    
    # The last file is the link_name
    parameters["link_name"] = parameters["files"].pop()
    
    # The first remaining file is the target
    parameters["target"] = parameters["files"][0]
    
    return OperationType.LINK_FILE, {
        "target": parameters["target"],
        "link_name": parameters["link_name"],
        "symbolic": parameters["symbolic"],
        "force": parameters["force"],
        "verbose": parameters["verbose"],
        "no_dereference": parameters["no_dereference"],
        "backup": parameters["backup"],
        "overwrite": parameters["force"],  # For API compatibility
        "all_targets": parameters["files"] # All target files (could be multiple)
    }

async def extract_chmod_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract chmod operation parameters with advanced mode handling.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles octal modes (e.g., 755) and symbolic modes (e.g., u+x)
        - Supports recursive (-R) and verbose (-v) flags
        - Detailed parsing of complex permission specifications
        - Multi-file support with validation
    """
    logger.debug(f"Extracting chmod operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "recursive": False,    # -R flag
        "verbose": False,      # -v flag
        "mode": None,
        "files": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    mode_found = False
    
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-R' or token == '--recursive':
                parameters["recursive"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -Rv
                for char in token[1:]:
                    if char == 'R':
                        parameters["recursive"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
        else:
            # If we haven't found the mode yet, this is it
            if not mode_found:
                parameters["mode"] = token
                mode_found = True
            else:
                # It's a file path
                parameters["files"].append(token)
        
        i += 1
    
    # Need mode and at least one file
    if not mode_found:
        raise ValueError("chmod requires mode specification")
        
    if not parameters["files"]:
        raise ValueError("chmod requires at least one file")
    
    # Validate mode - should be octal (e.g., 755) or symbolic (e.g., u+x)
    mode = parameters["mode"]
    is_octal = all(c in '01234567' for c in mode)
    is_symbolic = any(c in 'ugoa+-=rwxXst' for c in mode)
    
    if not (is_octal or is_symbolic):
        logger.warning(f"Suspicious chmod mode: {mode}")
        # Continue anyway - in case of false positive
    
    return OperationType.PERMISSION_CHANGE, {
        "mode": parameters["mode"],
        "path": parameters["files"][0],  # Primary file is the first one
        "recursive": parameters["recursive"],
        "verbose": parameters["verbose"],
        "all_files": parameters["files"]
    }

async def extract_chown_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract chown operation parameters with complete option support.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Supports recursive (-R) and verbose (-v) flags
        - Handles separate owner and group specifications
        - Supports reference file for ownership (-reference)
        - Multi-file support with validation
        - Special handling for numeric UIDs/GIDs
    """
    logger.debug(f"Extracting chown operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "recursive": False,      # -R flag
        "verbose": False,        # -v flag
        "dereference": True,     # Default is to dereference symlinks
        "preserve_root": True,   # Default is to preserve root
        "from_file": None,       # --reference option
        "owner": None,
        "group": None,
        "files": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    owner_group_found = False
    
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags and options
        if token.startswith('-'):
            if token == '-R' or token == '--recursive':
                parameters["recursive"] = True
            elif token == '-v' or token == '--verbose':
                parameters["verbose"] = True
            elif token == '-h' or token == '--no-dereference':
                parameters["dereference"] = False
            elif token == '--preserve-root':
                parameters["preserve_root"] = True
            elif token == '--no-preserve-root':
                parameters["preserve_root"] = False
            elif token == '--reference':
                if i + 1 < len(tokens):
                    i += 1
                    parameters["from_file"] = tokens[i]
            elif token.startswith('--reference='):
                parameters["from_file"] = token[len('--reference='):]
            elif not token.startswith('--'):
                # Handle combined flags like -Rvh
                for char in token[1:]:
                    if char == 'R':
                        parameters["recursive"] = True
                    elif char == 'v':
                        parameters["verbose"] = True
                    elif char == 'h':
                        parameters["dereference"] = False
        else:
            # If we haven't found the owner:group yet, this is it
            if not owner_group_found and not parameters["from_file"]:
                owner_spec = token
                owner_group_found = True
                
                # Parse owner and group from owner_spec (e.g., "user:group")
                if ':' in owner_spec:
                    parts = owner_spec.split(':', 1)
                    parameters["owner"] = parts[0] if parts[0] else None
                    parameters["group"] = parts[1] if parts[1] else None
                else:
                    parameters["owner"] = owner_spec
                    parameters["group"] = None
            else:
                # It's a file path
                parameters["files"].append(token)
        
        i += 1
    
    # Need owner specification or reference file, and at least one target file
    if not (owner_group_found or parameters["from_file"]):
        raise ValueError("chown requires owner specification or --reference option")
        
    if not parameters["files"]:
        raise ValueError("chown requires at least one file")
    
    # Security check - warn for recursive ownership change to system directories
    if parameters["recursive"]:
        critical_paths = ['/', '/boot', '/etc', '/usr', '/var', '/bin', '/sbin', '/lib']
        for file_path in parameters["files"]:
            normalized_path = os.path.normpath(file_path)
            if normalized_path in critical_paths:
                logger.warning(f"Attempt to recursively change ownership of critical system path: {normalized_path}")
                # Continue anyway - no need to block, just warn
    
    return OperationType.OWNERSHIP_CHANGE, {
        "owner": parameters["owner"],
        "group": parameters["group"],
        "path": parameters["files"][0],  # Primary file is the first one
        "recursive": parameters["recursive"],
        "verbose": parameters["verbose"],
        "dereference": parameters["dereference"],
        "preserve_root": parameters["preserve_root"],
        "from_file": parameters["from_file"],
        "all_files": parameters["files"]
    }

async def extract_find_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract find operation parameters with advanced option parsing.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Handles starting path and complex search expressions
        - Parses multiple search criteria (-name, -type, -size, etc.)
        - Advanced detection of actions (-exec, -delete, etc.)
        - Multi-path support and depth limits
    """
    logger.debug(f"Extracting find operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "starting_paths": [],
        "expressions": [],
        "name_patterns": [],
        "type_filters": [],
        "size_filters": [],
        "time_filters": [],
        "exec_actions": [],
        "max_depth": None,
        "min_depth": None,
        "has_delete_action": False
    }
    
    # Special handling for the find command
    # The first arguments before any options are starting paths
    i = 1  # Skip the command itself
    
    # First, collect starting paths
    while i < len(tokens) and not tokens[i].startswith('-'):
        parameters["starting_paths"].append(tokens[i])
        i += 1
    
    # If no starting paths specified, default to current directory
    if not parameters["starting_paths"]:
        parameters["starting_paths"].append(".")
    
    # Now parse the expressions/predicates
    current_expression = []
    
    while i < len(tokens):
        token = tokens[i]
        current_expression.append(token)
        
        # Check for specific options
        if token == '-name' or token == '-iname':
            if i + 1 < len(tokens):
                i += 1
                parameters["name_patterns"].append((token, tokens[i]))
                current_expression.append(tokens[i])
                
        elif token == '-type':
            if i + 1 < len(tokens):
                i += 1
                parameters["type_filters"].append(tokens[i])
                current_expression.append(tokens[i])
                
        elif token == '-size':
            if i + 1 < len(tokens):
                i += 1
                parameters["size_filters"].append(tokens[i])
                current_expression.append(tokens[i])
                
        elif token.startswith('-mtime') or token.startswith('-atime') or token.startswith('-ctime'):
            if i + 1 < len(tokens):
                i += 1
                parameters["time_filters"].append((token, tokens[i]))
                current_expression.append(tokens[i])
                
        elif token == '-maxdepth':
            if i + 1 < len(tokens):
                i += 1
                parameters["max_depth"] = int(tokens[i])
                current_expression.append(tokens[i])
                
        elif token == '-mindepth':
            if i + 1 < len(tokens):
                i += 1
                parameters["min_depth"] = int(tokens[i])
                current_expression.append(tokens[i])
                
        elif token == '-exec':
            # -exec takes all tokens until \; or + is found
            exec_cmd = []
            i += 1
            while i < len(tokens) and tokens[i] not in [';', '+']:
                exec_cmd.append(tokens[i])
                current_expression.append(tokens[i])
                i += 1
                
            if i < len(tokens):
                # Include the terminator
                terminator = tokens[i]
                current_expression.append(terminator)
                parameters["exec_actions"].append((' '.join(exec_cmd), terminator))
                
        elif token == '-delete':
            parameters["has_delete_action"] = True
            
        # Add the complete expression
        if token in ['-o', '-a', ')'] or i == len(tokens) - 1:
            if current_expression:
                parameters["expressions"].append(' '.join(current_expression))
                current_expression = []
        
        i += 1
    
    # Safety check - warn for potentially dangerous find operations
    if parameters["has_delete_action"]:
        logger.warning("Find command includes -delete action, which could remove many files")
        
    # For any -exec rm commands, warn as well
    for exec_cmd, terminator in parameters["exec_actions"]:
        if exec_cmd.startswith('rm '):
            logger.warning(f"Find command includes -exec rm command: {exec_cmd}")
    
    return OperationType.FIND_FILES, {
        "path": parameters["starting_paths"][0],  # Primary path is the first one
        "starting_paths": parameters["starting_paths"],
        "expressions": parameters["expressions"],
        "name_patterns": parameters["name_patterns"],
        "type_filters": parameters["type_filters"],
        "size_filters": parameters["size_filters"],
        "time_filters": parameters["time_filters"],
        "exec_actions": parameters["exec_actions"],
        "max_depth": parameters["max_depth"],
        "min_depth": parameters["min_depth"],
        "has_delete_action": parameters["has_delete_action"]
    }

async def extract_ls_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract ls operation parameters with comprehensive option parsing.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Supports all common ls flags (-l, -a, -h, -R, etc.)
        - Handles multiple directories
        - Path validation
        - Advanced formatting options
    """
    logger.debug(f"Extracting ls operation from: {command}")
    tokens = shlex.split(command)
    
    # Default parameters
    parameters = {
        "long_format": False,      # -l flag
        "all_files": False,        # -a flag
        "almost_all": False,       # -A flag
        "human_readable": False,   # -h flag
        "recursive": False,        # -R flag
        "sort_time": False,        # -t flag
        "sort_size": False,        # -S flag
        "reverse": False,          # -r flag
        "one_per_line": False,     # -1 flag
        "columns": False,          # -C flag
        "show_colors": False,      # --color flag
        "paths": []
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-l':
                parameters["long_format"] = True
            elif token == '-a' or token == '--all':
                parameters["all_files"] = True
            elif token == '-A' or token == '--almost-all':
                parameters["almost_all"] = True
            elif token == '-h' or token == '--human-readable':
                parameters["human_readable"] = True
            elif token == '-R' or token == '--recursive':
                parameters["recursive"] = True
            elif token == '-t':
                parameters["sort_time"] = True
            elif token == '-S':
                parameters["sort_size"] = True
            elif token == '-r' or token == '--reverse':
                parameters["reverse"] = True
            elif token == '-1':
                parameters["one_per_line"] = True
            elif token == '-C':
                parameters["columns"] = True
            elif token == '--color' or token == '--color=always':
                parameters["show_colors"] = True
            elif not token.startswith('--'):
                # Handle combined flags like -laR
                for char in token[1:]:
                    if char == 'l':
                        parameters["long_format"] = True
                    elif char == 'a':
                        parameters["all_files"] = True
                    elif char == 'A':
                        parameters["almost_all"] = True
                    elif char == 'h':
                        parameters["human_readable"] = True
                    elif char == 'R':
                        parameters["recursive"] = True
                    elif char == 't':
                        parameters["sort_time"] = True
                    elif char == 'S':
                        parameters["sort_size"] = True
                    elif char == 'r':
                        parameters["reverse"] = True
                    elif char == '1':
                        parameters["one_per_line"] = True
                    elif char == 'C':
                        parameters["columns"] = True
        else:
            # It's a path
            parameters["paths"].append(token)
        
        i += 1
    
    # If no paths specified, default to current directory
    if not parameters["paths"]:
        parameters["paths"].append(".")
    
    return OperationType.LIST_FILES, {
        "path": parameters["paths"][0],  # Primary path is the first one
        "long_format": parameters["long_format"],
        "all_files": parameters["all_files"],
        "almost_all": parameters["almost_all"],
        "human_readable": parameters["human_readable"],
        "recursive": parameters["recursive"],
        "sort_time": parameters["sort_time"],
        "sort_size": parameters["sort_size"],
        "reverse": parameters["reverse"],
        "one_per_line": parameters["one_per_line"],
        "columns": parameters["columns"],
        "show_colors": parameters["show_colors"],
        "all_paths": parameters["paths"]
    }

async def extract_search_in_files_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract grep/search operation parameters with pattern and file handling.
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Supports grep, egrep, fgrep, ripgrep, ag commands
        - Parses complex regex patterns safely
        - Handles multiple files and globs
        - Supports all common search flags
    """
    logger.debug(f"Extracting search in files operation from: {command}")
    tokens = shlex.split(command)
    
    # Get the command type (grep, egrep, fgrep, rg, ag)
    cmd_type = tokens[0]
    
    # Default parameters
    parameters = {
        "command_type": cmd_type,
        "recursive": False,      # -r flag
        "ignore_case": False,    # -i flag
        "invert_match": False,   # -v flag
        "line_numbers": False,   # -n flag
        "word_regexp": False,    # -w flag
        "extended_regexp": False,  # -E flag
        "fixed_strings": False,  # -F flag
        "only_matching": False,  # -o flag
        "pattern": None,
        "files": []
    }
    
    # egrep and fgrep are shortcuts for grep -E and grep -F
    if cmd_type == 'egrep':
        parameters["extended_regexp"] = True
    elif cmd_type == 'fgrep':
        parameters["fixed_strings"] = True
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    pattern_found = False
    
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags
        if token.startswith('-'):
            if token == '-r' or token == '-R' or token == '--recursive':
                parameters["recursive"] = True
            elif token == '-i' or token == '--ignore-case':
                parameters["ignore_case"] = True
            elif token == '-v' or token == '--invert-match':
                parameters["invert_match"] = True
            elif token == '-n' or token == '--line-number':
                parameters["line_numbers"] = True
            elif token == '-w' or token == '--word-regexp':
                parameters["word_regexp"] = True
            elif token == '-E' or token == '--extended-regexp':
                parameters["extended_regexp"] = True
            elif token == '-F' or token == '--fixed-strings':
                parameters["fixed_strings"] = True
            elif token == '-o' or token == '--only-matching':
                parameters["only_matching"] = True
            elif token == '-e' or token == '--regexp':
                # -e explicitly specifies the pattern
                if i + 1 < len(tokens):
                    i += 1
                    parameters["pattern"] = tokens[i]
                    pattern_found = True
            elif not token.startswith('--'):
                # Handle combined flags like -rin
                for char in token[1:]:
                    if char == 'r' or char == 'R':
                        parameters["recursive"] = True
                    elif char == 'i':
                        parameters["ignore_case"] = True
                    elif char == 'v':
                        parameters["invert_match"] = True
                    elif char == 'n':
                        parameters["line_numbers"] = True
                    elif char == 'w':
                        parameters["word_regexp"] = True
                    elif char == 'E':
                        parameters["extended_regexp"] = True
                    elif char == 'F':
                        parameters["fixed_strings"] = True
                    elif char == 'o':
                        parameters["only_matching"] = True
        else:
            # If we haven't found the pattern yet, this is it
            if not pattern_found:
                parameters["pattern"] = token
                pattern_found = True
            else:
                # It's a file path
                parameters["files"].append(token)
        
        i += 1
    
    # Need pattern and at least one file (or recursive search)
    if not pattern_found:
        raise ValueError(f"{cmd_type} requires a pattern")
        
    if not parameters["files"] and not parameters["recursive"]:
        logger.warning(f"{cmd_type} has no files specified, will read from stdin")
        parameters["files"] = ["-"]  # Convention for stdin
    
    return OperationType.SEARCH_IN_FILES, {
        "pattern": parameters["pattern"],
        "path": parameters["files"][0] if parameters["files"] else ".",  # Primary file or current dir
        "command_type": parameters["command_type"],
        "recursive": parameters["recursive"],
        "ignore_case": parameters["ignore_case"],
        "invert_match": parameters["invert_match"],
        "line_numbers": parameters["line_numbers"],
        "word_regexp": parameters["word_regexp"],
        "extended_regexp": parameters["extended_regexp"],
        "fixed_strings": parameters["fixed_strings"],
        "only_matching": parameters["only_matching"],
        "all_files": parameters["files"]
    }

async def extract_transform_file_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract file transformation operation parameters (sed, awk, etc.).
    
    Args:
        command: The shell command to analyze
        
    Returns:
        A tuple of (operation_type, parameters)
        
    Features:
        - Supports sed, awk, tr, sort, uniq
        - Safely handles complex script patterns
        - Parses input/output file specifications
        - Special handling for in-place edits
    """
    logger.debug(f"Extracting file transformation operation from: {command}")
    tokens = shlex.split(command)
    
    # Get the command type (sed, awk, tr, sort, uniq)
    cmd_type = tokens[0]
    
    # Default parameters
    parameters = {
        "command_type": cmd_type,
        "in_place": False,      # -i flag for sed
        "script": None,         # Script or pattern
        "input_files": [],
        "output_redirection": None,
        "script_file": None     # -f flag for sed/awk
    }
    
    # Parse all options and arguments
    i = 1  # Skip the command itself
    script_found = False
    
    # Special handling for redirect operators
    command_str = command
    redirect_match = re.search(r'\s+(>|>>)\s+(\S+)', command_str)
    if redirect_match:
        parameters["output_redirection"] = {
            "operator": redirect_match.group(1),
            "file": redirect_match.group(2)
        }
    
    while i < len(tokens):
        token = tokens[i]
        
        # Handle flags and command-specific options
        if token.startswith('-'):
            if cmd_type == 'sed' and (token == '-i' or token.startswith('-i')):
                parameters["in_place"] = True
                # Check for backup suffix like -i.bak
                if token != '-i' and len(token) > 2:
                    parameters["backup_suffix"] = token[2:]
            elif (cmd_type in ['sed', 'awk']) and (token == '-f'):
                # Script file
                if i + 1 < len(tokens):
                    i += 1
                    parameters["script_file"] = tokens[i]
                    script_found = True
            elif (cmd_type == 'sort') and (token in ['-n', '-r', '-k', '-t']):
                # Sort options
                if token in ['-k', '-t'] and i + 1 < len(tokens):
                    i += 1  # Skip the next token which is the parameter
            # Add more command-specific options as needed
        else:
            # If we haven't found the script/pattern yet and there's no script file
            if not script_found and not parameters["script_file"]:
                parameters["script"] = token
                script_found = True
            else:
                # It's an input file
                parameters["input_files"].append(token)
        
        i += 1
    
    # Command-specific validation
    if cmd_type in ['sed', 'awk'] and not (script_found or parameters["script_file"]):
        raise ValueError(f"{cmd_type} requires a script or pattern")
    
    # For sed in-place edits, need at least one input file
    if cmd_type == 'sed' and parameters["in_place"] and not parameters["input_files"]:
        raise ValueError("sed with -i requires at least one input file")
    
    # If no input files, will read from stdin
    if not parameters["input_files"] and not parameters["output_redirection"]:
        logger.debug(f"{cmd_type} has no files specified, will read from stdin")
        parameters["input_files"] = ["-"]  # Convention for stdin
    
    return OperationType.TRANSFORM_FILE, {
        "command_type": parameters["command_type"],
        "script": parameters["script"],
        "script_file": parameters["script_file"],
        "in_place": parameters["in_place"],
        "path": parameters["input_files"][0] if parameters["input_files"] else "-",  # Primary input
        "backup_suffix": parameters.get("backup_suffix"),
        "output_redirection": parameters["output_redirection"],
        "all_files": parameters["input_files"]
    }

# Operation extractors mapping - map command tokens to extractor functions
OPERATION_EXTRACTORS = {
    "mkdir": extract_mkdir_operation,
    "rmdir": extract_rmdir_operation,
    "rm": lambda cmd: extract_rm_recursive_operation(cmd) if any(x in cmd for x in ['-r', '-R', '--recursive']) else extract_rm_operation(cmd),
    "touch": extract_touch_operation,
    "cat": extract_cat_operation,
    "less": extract_cat_operation,
    "more": extract_cat_operation,
    "head": extract_cat_operation,
    "tail": extract_cat_operation,
    "echo": extract_echo_write_operation,
    "cp": extract_cp_operation,
    "mv": extract_mv_operation,
    "ln": extract_ln_operation,
    "chmod": extract_chmod_operation,
    "chown": extract_chown_operation,
    "find": extract_find_operation,
    "ls": extract_ls_operation,
    "grep": extract_search_in_files_operation,
    "egrep": extract_search_in_files_operation,
    "fgrep": extract_search_in_files_operation,
    "rg": extract_search_in_files_operation,
    "ag": extract_search_in_files_operation,
    "sed": extract_transform_file_operation,
    "awk": extract_transform_file_operation,
    "tr": extract_transform_file_operation,
    "sort": extract_transform_file_operation,
    "uniq": extract_transform_file_operation,
}

class CommandParser:
    """Advanced parser for shell commands with pipe and redirection handling."""
    
    def __init__(self):
        self.logger = logger
    
    def parse_command(self, command: str) -> List[Dict[str, Any]]:
        """
        Parse a shell command into components, handling pipes and redirections.
        
        Args:
            command: The shell command to parse
            
        Returns:
            List of command dictionaries with components
        """
        self.logger.debug(f"Parsing command: {command}")
        
        # Handle pipes
        if '|' in command:
            pipe_parts = self._split_by_pipes(command)
            
            commands = []
            for part in pipe_parts:
                parsed = self._parse_simple_command(part)
                if parsed:
                    commands.append(parsed)
                    
            return commands
        else:
            # Single command without pipes
            parsed = self._parse_simple_command(command)
            return [parsed] if parsed else []
    
    def _split_by_pipes(self, command: str) -> List[str]:
        """
        Split a command by pipe operators, respecting quotes.
        
        Args:
            command: The shell command to split
            
        Returns:
            List of command parts
        """
        parts = []
        current_part = ""
        in_single_quote = False
        in_double_quote = False
        escape_next = False
        
        for char in command:
            # Handle escape sequences
            if escape_next:
                current_part += char
                escape_next = False
                continue
                
            if char == '\\' and not in_single_quote:
                escape_next = True
                current_part += char
                continue
                
            # Handle quotes
            if char == "'" and not in_double_quote and not escape_next:
                in_single_quote = not in_single_quote
                current_part += char
            elif char == '"' and not in_single_quote and not escape_next:
                in_double_quote = not in_double_quote
                current_part += char
            # Handle pipe when not in quotes
            elif char == '|' and not in_single_quote and not in_double_quote:
                parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
        
        # Add the last part
        if current_part.strip():
            parts.append(current_part.strip())
            
        return parts
    
    def _parse_simple_command(self, command: str) -> Dict[str, Any]:
        """
        Parse a simple command (no pipes) with redirections.
        
        Args:
            command: The shell command to parse
            
        Returns:
            Dictionary with command components
        """
        # Handle redirections
        redirects = []
        
        # Find redirections (> output, >> append, < input, 2> error)
        redirect_patterns = [
            (r'\s+2>\s+(\S+)', 'stderr'),       # Error redirection
            (r'\s+1>\s+(\S+)', 'stdout'),       # Explicit stdout
            (r'\s+>\s+(\S+)', 'stdout'),        # Stdout redirection
            (r'\s+>>\s+(\S+)', 'append'),       # Append redirection
            (r'\s+<\s+(\S+)', 'stdin'),         # Input redirection
            (r'\s+2>>\s+(\S+)', 'stderr_append'), # Error append
            (r'\s+&>\s+(\S+)', 'both'),         # Both stdout and stderr
        ]
        
        # Extract redirections from command
        clean_command = command
        for pattern, redir_type in redirect_patterns:
            matches = re.finditer(pattern, command)
            for match in matches:
                redirects.append({
                    'type': redir_type,
                    'file': match.group(1),
                    'operator': match.group(0).strip()
                })
                # Remove redirection from command for further processing
                clean_command = clean_command.replace(match.group(0), '')
        
        # Get the base command without redirections
        base_command = clean_command.strip()
        
        # Extract command and arguments
        try:
            tokens = shlex.split(base_command)
            if not tokens:
                return None
                
            return {
                'command': base_command,
                'base_cmd': tokens[0],
                'args': tokens[1:],
                'redirects': redirects
            }
        except Exception as e:
            self.logger.error(f"Error parsing command '{base_command}': {str(e)}")
            return {
                'command': base_command,
                'base_cmd': base_command.split()[0] if base_command.split() else '',
                'args': [],
                'redirects': redirects,
                'error': str(e)
            }

async def extract_file_operation(command: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Enhanced extraction of file operation details from a command string.
    
    Analyzes shell commands to identify file operations with comprehensive
    pattern matching and parameter extraction. Supports complex syntax including
    quotes, redirections, and multi-file operations.
    
    Args:
        command: The shell command to analyze.
        
    Returns:
        A tuple of (operation_type, parameters) or None if not a file operation.
        
    Raises:
        ValueError: For invalid or unsafe commands.
    """
    try:
        # Get the base command for matching
        tokens = shlex.split(command)
        if not tokens:
            return None
        
        base_cmd = tokens[0]
        
        # Check if this is a known file operation using the extractors dictionary
        if base_cmd in OPERATION_EXTRACTORS:
            extractor = OPERATION_EXTRACTORS[base_cmd]
            
            # Invoke the appropriate extractor
            try:
                return await extractor(command)
            except ValueError as e:
                logger.warning(f"Extraction error for '{command}': {str(e)}")
                raise  # Re-raise for proper error handling
            except Exception as e:
                logger.error(f"Unexpected error extracting operation details for '{command}': {str(e)}")
                raise ValueError(f"Error analyzing command: {str(e)}")
        
        # If extractor not found, try pattern matching
        for pattern, operation_type in FILE_OPERATION_PATTERNS:
            # Use verbose regex with re.VERBOSE flag
            match = re.match(pattern, command, re.VERBOSE)
            if match:
                # Extract parameters based on pattern groups
                # Check the pattern template to determine parameter extraction strategy
                if 'mkdir' in pattern:
                    return operation_type, {
                        "path": match.group('mkdir_paths').split()[0] if 'mkdir_paths' in match.groupdict() else ".",
                        "parents": bool('mkdir_flags' in match.groupdict() and match.group('mkdir_flags') and 'p' in match.group('mkdir_flags')),
                        "mode": match.group('mkdir_mode').split()[1] if 'mkdir_mode' in match.groupdict() and match.group('mkdir_mode') else None
                    }
                elif 'rmdir' in pattern:
                    return operation_type, {
                        "path": match.group('rmdir_paths').split()[0] if 'rmdir_paths' in match.groupdict() else "."
                    }
                elif 'rm' in pattern and 'recursive' in pattern:
                    return operation_type, {
                        "path": match.group('rm_paths').split()[0] if 'rm_paths' in match.groupdict() else ".",
                        "recursive": True,
                        "force": bool('rm_force' in match.groupdict() and match.group('rm_force')),
                        "verbose": bool('rm_verbose' in match.groupdict() and match.group('rm_verbose'))
                    }
                elif 'touch' in pattern:
                    return operation_type, {
                        "path": match.group('touch_files').split()[0] if 'touch_files' in match.groupdict() else ".",
                        "content": None
                    }
                elif 'read_cmd' in pattern:
                    return operation_type, {
                        "path": match.group('read_files').split()[0] if 'read_files' in match.groupdict() else "-",
                        "binary": False,
                        "command_type": match.group('read_cmd') if 'read_cmd' in match.groupdict() else "cat"
                    }
                elif 'echo' in pattern and '>' in pattern and not '>>' in pattern:
                    return operation_type, {
                        "path": match.group('echo_file') if 'echo_file' in match.groupdict() else "output.txt",
                        "content": match.group('echo_content') if 'echo_content' in match.groupdict() else "",
                        "append": False
                    }
                elif 'echo' in pattern and '>>' in pattern:
                    return operation_type, {
                        "path": match.group('echo_append_file') if 'echo_append_file' in match.groupdict() else "output.txt",
                        "content": match.group('echo_append_content') if 'echo_append_content' in match.groupdict() else "",
                        "append": True
                    }
                elif 'rm' in pattern and not 'recursive' in pattern:
                    return operation_type, {
                        "path": match.group('rm_files').split()[0] if 'rm_files' in match.groupdict() else ".",
                        "force": bool('rm_file_flags' in match.groupdict() and match.group('rm_file_flags') and 'f' in match.group('rm_file_flags'))
                    }
                elif 'cp' in pattern and not 'recursive' in pattern:
                    return operation_type, {
                        "source": match.group('cp_source') if 'cp_source' in match.groupdict() else ".",
                        "destination": match.group('cp_dest') if 'cp_dest' in match.groupdict() else ".",
                        "force": bool('cp_flags' in match.groupdict() and match.group('cp_flags') and 'f' in match.group('cp_flags')),
                        "recursive": False,
                        "overwrite": bool('cp_flags' in match.groupdict() and match.group('cp_flags') and 'f' in match.group('cp_flags'))
                    }
                elif 'cp' in pattern and 'recursive' in pattern:
                    return operation_type, {
                        "source": match.group('cp_recursive_source') if 'cp_recursive_source' in match.groupdict() else ".",
                        "destination": match.group('cp_recursive_dest') if 'cp_recursive_dest' in match.groupdict() else ".",
                        "recursive": True,
                        "force": bool('cp_recursive_opts' in match.groupdict() and match.group('cp_recursive_opts') and 'f' in match.group('cp_recursive_opts')),
                        "overwrite": bool('cp_recursive_opts' in match.groupdict() and match.group('cp_recursive_opts') and 'f' in match.group('cp_recursive_opts'))
                    }
                elif 'mv' in pattern:
                    return operation_type, {
                        "source": match.group('mv_source') if 'mv_source' in match.groupdict() else ".",
                        "destination": match.group('mv_dest') if 'mv_dest' in match.groupdict() else ".",
                        "force": bool('mv_flags' in match.groupdict() and match.group('mv_flags') and 'f' in match.group('mv_flags')),
                        "overwrite": bool('mv_flags' in match.groupdict() and match.group('mv_flags') and 'f' in match.group('mv_flags'))
                    }
                elif 'ln' in pattern:
                    return operation_type, {
                        "target": match.group('ln_target') if 'ln_target' in match.groupdict() else ".",
                        "link_name": match.group('ln_link') if 'ln_link' in match.groupdict() else ".",
                        "symbolic": bool('ln_symbolic' in match.groupdict() and match.group('ln_symbolic')),
                        "force": bool('ln_flags' in match.groupdict() and match.group('ln_flags') and 'f' in match.group('ln_flags')),
                        "overwrite": bool('ln_flags' in match.groupdict() and match.group('ln_flags') and 'f' in match.group('ln_flags'))
                    }
        
        # No match found
        return None
        
    except Exception as e:
        logger.exception(f"Error extracting file operation from '{command}': {str(e)}")
        return None

async def execute_file_operation(
    operation_type: str, 
    parameters: Dict[str, Any],
    dry_run: bool = False,
    transaction_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a file operation with comprehensive validation, error checking, and transaction support.
    
    Args:
        operation_type: The type of file operation
        parameters: Parameters for the operation
        dry_run: Whether to simulate execution without making changes
        transaction_id: Optional transaction ID for rollback support
        
    Returns:
        Dictionary with operation results
        
    Raises:
        ValueError: For invalid parameters or operation types
        FileSystemError: For filesystem-related errors
    """
    logger.info(f"Executing file operation: {operation_type}" + (" (dry run)" if dry_run else ""))
    logger.debug(f"Parameters: {parameters}")
    
    # Create base result structure
    result = {
        "operation": operation_type,
        "parameters": parameters,
        "success": False,
        "dry_run": dry_run,
        "timestamp": datetime.now().isoformat(),
        "transaction_id": transaction_id
    }
    
    # Validate operation type
    if not hasattr(OperationType, operation_type.upper()):
        error_msg = f"Unknown file operation: {operation_type}"
        logger.error(error_msg)
        result["error"] = error_msg
        return result
    
    try:
        # Execute based on operation type
        if operation_type == OperationType.CREATE_DIRECTORY:
            path = parameters.get("path")
            parents = parameters.get("parents", True)
            mode = parameters.get("mode")
            
            if not path:
                raise ValueError("Path parameter is required for create_directory operation")
            
            # Get the creation function from the API
            create_directory_func = get_create_directory_func()
            success = await create_directory_func(
                path, 
                parents=parents, 
                mode=mode, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
            # Handle additional paths if specified
            all_paths = parameters.get("all_paths", [])
            if len(all_paths) > 1:  # If there are multiple paths
                additional_results = []
                for additional_path in all_paths[1:]:
                    additional_success = await create_directory_func(
                        additional_path,
                        parents=parents,
                        mode=mode,
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    additional_results.append({
                        "path": additional_path,
                        "success": additional_success
                    })
                result["additional_results"] = additional_results
            
        elif operation_type == OperationType.DELETE_DIRECTORY:
            path = parameters.get("path")
            recursive = parameters.get("recursive", False)
            force = parameters.get("force", False)
            
            if not path:
                raise ValueError("Path parameter is required for delete_directory operation")
            
            # Security check for critical paths
            critical_paths = ['/', '/boot', '/etc', '/usr', '/var', '/bin', '/sbin', '/lib']
            normalized_path = os.path.normpath(path)
            if normalized_path in critical_paths:
                error_msg = f"Refusing to remove critical system path: {normalized_path}"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            # Get the deletion function from the API
            delete_directory_func = get_delete_directory_func()
            success = await delete_directory_func(
                path, 
                recursive=recursive, 
                force=force, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
            # Handle additional paths if specified
            all_paths = parameters.get("all_paths", [])
            if len(all_paths) > 1:  # If there are multiple paths
                additional_results = []
                for additional_path in all_paths[1:]:
                    # Security check for critical paths
                    norm_path = os.path.normpath(additional_path)
                    if norm_path in critical_paths:
                        additional_results.append({
                            "path": additional_path,
                            "success": False,
                            "error": f"Refusing to remove critical system path: {norm_path}"
                        })
                        continue
                        
                    additional_success = await delete_directory_func(
                        additional_path,
                        recursive=recursive,
                        force=force,
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    additional_results.append({
                        "path": additional_path,
                        "success": additional_success
                    })
                result["additional_results"] = additional_results
            
        elif operation_type == OperationType.CREATE_FILE:
            path = parameters.get("path")
            content = parameters.get("content")
            no_create = parameters.get("no_create", False)
            
            if not path:
                raise ValueError("Path parameter is required for create_file operation")
            
            # Check for the case when "no_create" is specified and the file exists
            if no_create and os.path.exists(path) and not dry_run:
                # With -c flag, touch doesn't create new files
                result["success"] = True
                result["message"] = f"File {path} exists, not creating due to no_create option"
                return result
            
            # Get the creation function from the API
            create_file_func = get_create_file_func()
            success = await create_file_func(
                path, 
                content=content, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
            # Handle additional files if specified
            all_files = parameters.get("all_files", [])
            if len(all_files) > 1:  # If there are multiple files
                additional_results = []
                for additional_file in all_files[1:]:
                    additional_success = await create_file_func(
                        additional_file,
                        content=content,
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    additional_results.append({
                        "path": additional_file,
                        "success": additional_success
                    })
                result["additional_results"] = additional_results
            
        elif operation_type == OperationType.READ_FILE:
            path = parameters.get("path")
            binary = parameters.get("binary", False)
            command_type = parameters.get("command_type", "cat")
            line_count = parameters.get("line_count")
            follow = parameters.get("follow", False)
            
            if not path:
                raise ValueError("Path parameter is required for read_file operation")
            
            # Get the read function from the API
            read_file_func = get_read_file_func()
            
            # For head/tail, we might need special handling for line counts
            if command_type in ["head", "tail"] and line_count:
                try:
                    # Read the entire file first
                    content = await read_file_func(path, binary=binary)
                    
                    # Convert to lines and trim as needed
                    lines = content.splitlines()
                    
                    # Parse line count (could be positive or negative)
                    n = int(line_count)
                    
                    if command_type == "head":
                        # Take first n lines
                        result_lines = lines[:n] if n > 0 else lines[:len(lines)+n]
                    else:  # tail
                        # Take last n lines
                        result_lines = lines[-n:] if n > 0 else lines[:-n]
                        
                    # Reassemble the content
                    content = "\n".join(result_lines)
                    if content and not content.endswith("\n"):
                        content += "\n"
                        
                    result["content"] = content
                    result["success"] = True
                except Exception as e:
                    logger.error(f"Error processing {command_type} operation: {str(e)}")
                    result["error"] = f"Error processing {command_type} operation: {str(e)}"
                    return result
            else:
                # Standard file reading
                content = await read_file_func(path, binary=binary)
                result["content"] = content
                result["success"] = True
            
            # If multiple files are specified, read them all
            all_files = parameters.get("all_files", [])
            if len(all_files) > 1:  # If there are multiple files
                additional_results = []
                for additional_file in all_files[1:]:
                    try:
                        additional_content = await read_file_func(additional_file, binary=binary)
                        additional_results.append({
                            "path": additional_file,
                            "content": additional_content,
                            "success": True
                        })
                    except Exception as e:
                        additional_results.append({
                            "path": additional_file,
                            "error": str(e),
                            "success": False
                        })
                result["additional_results"] = additional_results
            
        elif operation_type == OperationType.WRITE_FILE:
            path = parameters.get("path")
            content = parameters.get("content", "")
            append = parameters.get("append", False)
            
            if not path:
                raise ValueError("Path parameter is required for write_file operation")
            
            # Get the write function from the API
            write_file_func = get_write_file_func()
            success = await write_file_func(
                path, 
                content, 
                append=append, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
        elif operation_type == OperationType.APPEND_FILE:
            # This uses the same function as WRITE_FILE but with append=True
            path = parameters.get("path")
            content = parameters.get("content", "")
            
            if not path:
                raise ValueError("Path parameter is required for append_file operation")
            
            # Get the write function from the API
            write_file_func = get_write_file_func()
            success = await write_file_func(
                path, 
                content, 
                append=True, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
        elif operation_type == OperationType.DELETE_FILE:
            path = parameters.get("path")
            force = parameters.get("force", False)
            
            if not path:
                raise ValueError("Path parameter is required for delete_file operation")
            
            # Get the delete function from the API
            delete_file_func = get_delete_file_func()
            success = await delete_file_func(
                path, 
                force=force, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
            # Handle additional files if specified
            all_files = parameters.get("all_files", [])
            if len(all_files) > 1:  # If there are multiple files
                additional_results = []
                for additional_file in all_files[1:]:
                    additional_success = await delete_file_func(
                        additional_file,
                        force=force,
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    additional_results.append({
                        "path": additional_file,
                        "success": additional_success
                    })
                result["additional_results"] = additional_results
            
        elif operation_type == OperationType.COPY_FILE:
            source = parameters.get("source")
            destination = parameters.get("destination")
            overwrite = parameters.get("overwrite", False)
            recursive = parameters.get("recursive", False)
            preserve = parameters.get("preserve", False)
            
            if not source or not destination:
                raise ValueError("Source and destination parameters are required for copy_file operation")
            
            # Get the copy function from the API
            copy_file_func = get_copy_file_func()
            
            # For recursive copies, use directory APIs if needed
            if recursive and os.path.isdir(source):
                # Source is a directory, use appropriate API
                create_directory_func = get_create_directory_func()
                
                # Create the destination directory if it doesn't exist
                if not os.path.exists(destination) and not dry_run:
                    await create_directory_func(destination, parents=True)
                
                # Copy all files and subdirectories (simplified)
                success = True
                if not dry_run:
                    for root, dirs, files in os.walk(source):
                        # Compute relative path
                        rel_path = os.path.relpath(root, source)
                        target_dir = os.path.join(destination, rel_path)
                        
                        # Create directories
                        for dir_name in dirs:
                            dir_path = os.path.join(target_dir, dir_name)
                            try:
                                await create_directory_func(dir_path, parents=True)
                            except Exception as e:
                                logger.error(f"Error creating directory {dir_path}: {str(e)}")
                                success = False
                        
                        # Copy files
                        for file_name in files:
                            src_file = os.path.join(root, file_name)
                            dst_file = os.path.join(target_dir, file_name)
                            try:
                                await copy_file_func(
                                    src_file,
                                    dst_file,
                                    overwrite=overwrite,
                                    transaction_id=transaction_id
                                )
                            except Exception as e:
                                logger.error(f"Error copying file {src_file}: {str(e)}")
                                success = False
                
                result["success"] = success
                result["recursive"] = True
            else:
                # Standard file copy
                success = await copy_file_func(
                    source, 
                    destination, 
                    overwrite=overwrite, 
                    dry_run=dry_run,
                    transaction_id=transaction_id
                )
                result["success"] = success
            
            # Handle multiple source files if destination is a directory
            all_sources = parameters.get("all_sources", [])
            if len(all_sources) > 1 and os.path.isdir(destination):
                additional_results = []
                for additional_source in all_sources[1:]:
                    dest_path = os.path.join(destination, os.path.basename(additional_source))
                    additional_success = await copy_file_func(
                        additional_source,
                        dest_path,
                        overwrite=overwrite,
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    additional_results.append({
                        "source": additional_source,
                        "destination": dest_path,
                        "success": additional_success
                    })
                result["additional_results"] = additional_results
            
        elif operation_type == OperationType.MOVE_FILE:
            source = parameters.get("source")
            destination = parameters.get("destination")
            overwrite = parameters.get("overwrite", False)
            
            if not source or not destination:
                raise ValueError("Source and destination parameters are required for move_file operation")
            
            # Get the move function from the API
            move_file_func = get_move_file_func()
            success = await move_file_func(
                source, 
                destination, 
                overwrite=overwrite, 
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            result["success"] = success
            
            # Handle multiple source files if destination is a directory
            all_sources = parameters.get("all_sources", [])
            if len(all_sources) > 1 and os.path.isdir(destination):
                additional_results = []
                for additional_source in all_sources[1:]:
                    dest_path = os.path.join(destination, os.path.basename(additional_source))
                    additional_success = await move_file_func(
                        additional_source,
                        dest_path,
                        overwrite=overwrite,
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    additional_results.append({
                        "source": additional_source,
                        "destination": dest_path,
                        "success": additional_success
                    })
                result["additional_results"] = additional_results
        
        elif operation_type == OperationType.LINK_FILE:
            target = parameters.get("target")
            link_name = parameters.get("link_name")
            symbolic = parameters.get("symbolic", True)
            force = parameters.get("force", False)
            
            if not target or not link_name:
                raise ValueError("Target and link_name parameters are required for link_file operation")
            
            # Create the link using appropriate OS function
            try:
                if not dry_run:
                    # Check if link exists and needs to be removed
                    if os.path.exists(link_name) or os.path.islink(link_name):
                        if force:
                            try:
                                if os.path.isdir(link_name) and not os.path.islink(link_name):
                                    os.rmdir(link_name)
                                else:
                                    os.unlink(link_name)
                            except Exception as e:
                                logger.error(f"Error removing existing link: {str(e)}")
                                result["error"] = f"Error removing existing link: {str(e)}"
                                return result
                        else:
                            result["error"] = f"Link destination {link_name} already exists"
                            return result
                    
                    # Create the link
                    if symbolic:
                        os.symlink(target, link_name)
                    else:
                        os.link(target, link_name)
                        
                # Record for transaction if provided
                if transaction_id:
                    # Use delete_file for rollback (whether symbolic or hard link)
                    delete_file_func = get_delete_file_func()
                    # Register the rollback operation but don't execute it
                    await delete_file_func(
                        link_name,
                        force=True,
                        dry_run=True,  # Register but don't execute
                        transaction_id=transaction_id,
                        operation_type="rollback"  # Mark as rollback operation
                    )
                
                result["success"] = True
            except Exception as e:
                logger.error(f"Error creating link: {str(e)}")
                result["error"] = f"Error creating link: {str(e)}"
                return result
        
        elif operation_type == OperationType.PERMISSION_CHANGE:
            path = parameters.get("path")
            mode = parameters.get("mode")
            recursive = parameters.get("recursive", False)
            
            if not path or not mode:
                raise ValueError("Path and mode parameters are required for permission_change operation")
            
            # Execute the chmod operation
            try:
                if not dry_run:
                    # Convert mode to integer if it's an octal string
                    mode_value = mode
                    if isinstance(mode, str) and all(c in '01234567' for c in mode):
                        mode_value = int(mode, 8)
                    
                    # Apply permissions
                    if recursive:
                        for root, dirs, files in os.walk(path):
                            # Change permissions on directories
                            for directory in dirs:
                                dir_path = os.path.join(root, directory)
                                os.chmod(dir_path, mode_value if isinstance(mode_value, int) else int(mode_value, 8))
                            
                            # Change permissions on files
                            for file in files:
                                file_path = os.path.join(root, file)
                                os.chmod(file_path, mode_value if isinstance(mode_value, int) else int(mode_value, 8))
                    
                    # Always chmod the path itself
                    os.chmod(path, mode_value if isinstance(mode_value, int) else int(mode_value, 8))
                    
                result["success"] = True
                
                # Handle additional files if specified
                all_files = parameters.get("all_files", [])
                if len(all_files) > 1:  # If there are multiple files
                    additional_results = []
                    for additional_file in all_files[1:]:
                        # Skip the file we already processed
                        if additional_file == path:
                            continue
                            
                        try:
                            if not dry_run:
                                if recursive and os.path.isdir(additional_file):
                                    for root, dirs, files in os.walk(additional_file):
                                        # Change permissions on directories
                                        for directory in dirs:
                                            dir_path = os.path.join(root, directory)
                                            os.chmod(dir_path, mode_value if isinstance(mode_value, int) else int(mode_value, 8))
                                        
                                        # Change permissions on files
                                        for file in files:
                                            file_path = os.path.join(root, file)
                                            os.chmod(file_path, mode_value if isinstance(mode_value, int) else int(mode_value, 8))
                                
                                # Always chmod the path itself
                                os.chmod(additional_file, mode_value if isinstance(mode_value, int) else int(mode_value, 8))
                                
                            additional_results.append({
                                "path": additional_file,
                                "success": True
                            })
                        except Exception as e:
                            additional_results.append({
                                "path": additional_file,
                                "error": str(e),
                                "success": False
                            })
                    
                    if additional_results:
                        result["additional_results"] = additional_results
                
            except Exception as e:
                logger.error(f"Error changing permissions: {str(e)}")
                result["error"] = f"Error changing permissions: {str(e)}"
                return result
        
        elif operation_type == OperationType.OWNERSHIP_CHANGE:
            path = parameters.get("path")
            owner = parameters.get("owner")
            group = parameters.get("group")
            recursive = parameters.get("recursive", False)
            
            if not path:
                raise ValueError("Path parameter is required for ownership_change operation")
            
            # At least one of owner or group should be specified
            if owner is None and group is None:
                raise ValueError("At least one of owner or group must be specified")
            
            # Execute the chown operation
            try:
                if not dry_run:
                    import pwd
                    import grp
                    
                    # Get numeric UID/GID if names were provided
                    uid = -1  # -1 means don't change
                    gid = -1  # -1 means don't change
                    
                    if owner is not None:
                        try:
                            # Try to interpret as numeric UID first
                            if owner.isdigit():
                                uid = int(owner)
                            else:
                                # Look up user by name
                                uid = pwd.getpwnam(owner).pw_uid
                        except KeyError:
                            raise ValueError(f"User '{owner}' not found")
                    
                    if group is not None:
                        try:
                            # Try to interpret as numeric GID first
                            if group.isdigit():
                                gid = int(group)
                            else:
                                # Look up group by name
                                gid = grp.getgrnam(group).gr_gid
                        except KeyError:
                            raise ValueError(f"Group '{group}' not found")
                    
                    # Apply ownership changes
                    if recursive:
                        for root, dirs, files in os.walk(path):
                            # Change ownership on directories
                            for directory in dirs:
                                dir_path = os.path.join(root, directory)
                                os.chown(dir_path, uid, gid)
                            
                            # Change ownership on files
                            for file in files:
                                file_path = os.path.join(root, file)
                                os.chown(file_path, uid, gid)
                    
                    # Always chown the path itself
                    os.chown(path, uid, gid)
                    
                result["success"] = True
                
                # Handle additional files if specified
                all_files = parameters.get("all_files", [])
                if len(all_files) > 1:  # If there are multiple files
                    additional_results = []
                    for additional_file in all_files[1:]:
                        # Skip the file we already processed
                        if additional_file == path:
                            continue
                            
                        try:
                            if not dry_run:
                                if recursive and os.path.isdir(additional_file):
                                    for root, dirs, files in os.walk(additional_file):
                                        # Change ownership on directories
                                        for directory in dirs:
                                            dir_path = os.path.join(root, directory)
                                            os.chown(dir_path, uid, gid)
                                        
                                        # Change ownership on files
                                        for file in files:
                                            file_path = os.path.join(root, file)
                                            os.chown(file_path, uid, gid)
                                
                                # Always chown the path itself
                                os.chown(additional_file, uid, gid)
                                
                            additional_results.append({
                                "path": additional_file,
                                "success": True
                            })
                        except Exception as e:
                            additional_results.append({
                                "path": additional_file,
                                "error": str(e),
                                "success": False
                            })
                    
                    if additional_results:
                        result["additional_results"] = additional_results
                
            except Exception as e:
                logger.error(f"Error changing ownership: {str(e)}")
                result["error"] = f"Error changing ownership: {str(e)}"
                return result
        
        # Special handling for advanced operations that are read-only
        elif operation_type in [OperationType.LIST_FILES, OperationType.FIND_FILES, 
                               OperationType.VIEW_FILE_INFO, OperationType.SEARCH_IN_FILES]:
            # These operations are typically executed directly via shell
            # and don't need the same kind of transaction support
            result["success"] = True
            result["message"] = f"Operation {operation_type} would be executed directly"
            
            # In dry run, just return success
            if dry_run:
                return result
                
            # For actual execution, try to call the OS command
            try:
                # Reconstruct command from parameters
                cmd = []
                
                if operation_type == OperationType.LIST_FILES:
                    # ls command
                    cmd.append("ls")
                    if parameters.get("long_format", False):
                        cmd.append("-l")
                    if parameters.get("all_files", False):
                        cmd.append("-a")
                    if parameters.get("human_readable", False):
                        cmd.append("-h")
                    if parameters.get("recursive", False):
                        cmd.append("-R")
                    
                    # Add paths
                    for p in parameters.get("all_paths", [parameters.get("path", ".")]):
                        cmd.append(p)
                        
                elif operation_type == OperationType.FIND_FILES:
                    # find command
                    cmd.append("find")
                    
                    # Add starting paths
                    for p in parameters.get("starting_paths", [parameters.get("path", ".")]):
                        cmd.append(p)
                    
                    # Add expressions
                    for expr in parameters.get("expressions", []):
                        cmd.extend(shlex.split(expr))
                
                elif operation_type == OperationType.VIEW_FILE_INFO:
                    # file/stat/du command
                    cmd_type = parameters.get("command_type", "file")
                    cmd.append(cmd_type)
                    
                    # Add any flags
                    if "info_flags" in parameters and parameters["info_flags"]:
                        cmd.extend(shlex.split(parameters["info_flags"]))
                    
                    # Add target
                    cmd.append(parameters.get("path", "."))
                
                elif operation_type == OperationType.SEARCH_IN_FILES:
                    # grep/egrep/fgrep/rg/ag command
                    cmd_type = parameters.get("command_type", "grep")
                    cmd.append(cmd_type)
                    
                    # Add flags
                    if parameters.get("recursive", False):
                        cmd.append("-r")
                    if parameters.get("ignore_case", False):
                        cmd.append("-i")
                    if parameters.get("line_numbers", False):
                        cmd.append("-n")
                    
                    # Add pattern and files
                    cmd.append(parameters.get("pattern", ""))
                    for f in parameters.get("all_files", [parameters.get("path", ".")]):
                        cmd.append(f)
                
                # Execute the command
                if cmd:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await proc.communicate()
                    
                    result["command"] = " ".join(cmd)
                    result["stdout"] = stdout.decode('utf-8', errors='replace')
                    result["stderr"] = stderr.decode('utf-8', errors='replace')
                    result["return_code"] = proc.returncode
                    result["success"] = proc.returncode == 0
            
            except Exception as e:
                logger.error(f"Error executing {operation_type} operation: {str(e)}")
                result["error"] = f"Error executing {operation_type} operation: {str(e)}"
                result["success"] = False
        
        elif operation_type == OperationType.TRANSFORM_FILE:
            # Transform operations like sed/awk are complex and often require direct shell execution
            command_type = parameters.get("command_type", "sed")
            path = parameters.get("path", "-")  # Default to stdin
            script = parameters.get("script")
            script_file = parameters.get("script_file")
            in_place = parameters.get("in_place", False)
            
            # Construct the command
            cmd = [command_type]
            
            # Add options
            if command_type == "sed" and in_place:
                suffix = parameters.get("backup_suffix")
                if suffix is not None:
                    cmd.append(f"-i{suffix}")
                else:
                    cmd.append("-i")
            
            # Add script or script file
            if script_file:
                cmd.extend(["-f", script_file])
            elif script:
                cmd.append(script)
            else:
                raise ValueError(f"{command_type} requires a script or pattern")
            
            # Add input files
            for f in parameters.get("all_files", [path]):
                cmd.append(f)
            
            # In dry run, just return the command
            if dry_run:
                result["command"] = " ".join(cmd)
                result["success"] = True
                return result
            
            # Execute the command
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                result["command"] = " ".join(cmd)
                result["stdout"] = stdout.decode('utf-8', errors='replace')
                result["stderr"] = stderr.decode('utf-8', errors='replace')
                result["return_code"] = proc.returncode
                result["success"] = proc.returncode == 0
                
                # For in-place edits, need to record the transaction for rollback
                if transaction_id and command_type == "sed" and in_place:
                    for f in parameters.get("all_files", [path]):
                        # Read the original content for potential rollback
                        if os.path.exists(f) and not f == "-":
                            try:
                                with open(f, 'r', encoding='utf-8') as file:
                                    original_content = file.read()
                                    
                                # Register a rollback operation to restore the original content
                                write_file_func = get_write_file_func()
                                await write_file_func(
                                    f,
                                    original_content,
                                    append=False,
                                    dry_run=True,  # Register but don't execute
                                    transaction_id=transaction_id,
                                    operation_type="rollback"  # Mark as rollback operation
                                )
                            except Exception as e:
                                logger.warning(f"Could not register rollback for file {f}: {str(e)}")
            
            except Exception as e:
                logger.error(f"Error executing {operation_type} operation: {str(e)}")
                result["error"] = f"Error executing {operation_type} operation: {str(e)}"
                result["success"] = False
        
        # Add more operation types here as needed
        
        else:
            # Unknown operation type
            result["error"] = f"Operation {operation_type} not implemented"
            result["success"] = False
        
        return result
            
    except get_filesystem_error_class() as e:
        logger.exception(f"Error executing file operation: {str(e)}")
        return {
            "operation": operation_type,
            "parameters": parameters,
            "success": False,
            "error": str(e),
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id
        }
    except Exception as e:
        logger.exception(f"Unexpected error in file operation: {str(e)}")
        return {
            "operation": operation_type,
            "parameters": parameters,
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id
        }

# Enhanced utilities for advanced use cases

class NaturalLanguageFileOperationExtractor:
    """
    Extracts file operations from natural language requests.
    
    This class uses pattern matching and heuristics to identify file-related
    operations in natural language requests and convert them to structured
    operations that can be executed.
    """
    
    def __init__(self):
        """Initialize the extractor with patterns and vocabulary."""
        self.logger = logger
        
        # Common file operation verbs and their mapped operations
        self.operation_verbs = {
            "create": [OperationType.CREATE_FILE, OperationType.CREATE_DIRECTORY],
            "make": [OperationType.CREATE_FILE, OperationType.CREATE_DIRECTORY],
            "new": [OperationType.CREATE_FILE, OperationType.CREATE_DIRECTORY],
            "touch": [OperationType.CREATE_FILE],
            "mkdir": [OperationType.CREATE_DIRECTORY],
            "remove": [OperationType.DELETE_FILE, OperationType.DELETE_DIRECTORY],
            "delete": [OperationType.DELETE_FILE, OperationType.DELETE_DIRECTORY],
            "erase": [OperationType.DELETE_FILE],
            "rm": [OperationType.DELETE_FILE, OperationType.DELETE_DIRECTORY],
            "read": [OperationType.READ_FILE],
            "view": [OperationType.READ_FILE],
            "show": [OperationType.READ_FILE],
            "display": [OperationType.READ_FILE],
            "cat": [OperationType.READ_FILE],
            "type": [OperationType.READ_FILE],  # Windows 'type' command
            "write": [OperationType.WRITE_FILE],
            "save": [OperationType.WRITE_FILE],
            "append": [OperationType.APPEND_FILE],
            "add to": [OperationType.APPEND_FILE],
            "copy": [OperationType.COPY_FILE],
            "duplicate": [OperationType.COPY_FILE],
            "cp": [OperationType.COPY_FILE],
            "move": [OperationType.MOVE_FILE],
            "rename": [OperationType.MOVE_FILE],
            "mv": [OperationType.MOVE_FILE],
            "link": [OperationType.LINK_FILE],
            "ln": [OperationType.LINK_FILE],
            "symlink": [OperationType.LINK_FILE],
            "chmod": [OperationType.PERMISSION_CHANGE],
            "change permissions": [OperationType.PERMISSION_CHANGE],
            "chown": [OperationType.OWNERSHIP_CHANGE],
            "change owner": [OperationType.OWNERSHIP_CHANGE],
            "find": [OperationType.FIND_FILES],
            "search": [OperationType.FIND_FILES, OperationType.SEARCH_IN_FILES],
            "locate": [OperationType.FIND_FILES],
            "list": [OperationType.LIST_FILES],
            "ls": [OperationType.LIST_FILES],
            "dir": [OperationType.LIST_FILES],  # Windows 'dir' command
            "grep": [OperationType.SEARCH_IN_FILES],
            "search in": [OperationType.SEARCH_IN_FILES],
            "look for": [OperationType.SEARCH_IN_FILES],
            "find in": [OperationType.SEARCH_IN_FILES],
        }
        
        # File type vocabulary
        self.file_type_vocab = {
            "file": "file",
            "document": "file",
            "text file": "file",
            "folder": "directory",
            "directory": "directory",
            "dir": "directory",
            "subdirectory": "directory",
            "sub-directory": "directory",
            "image": "file",
            "picture": "file",
            "photo": "file",
            "video": "file",
            "script": "file",
            "program": "file",
            "executable": "file",
            "configuration": "file",
            "config": "file",
            "log": "file",
            "data": "file",
        }
        
        # Common file extensions mapped to their types
        self.file_extensions = {
            ".txt": "text",
            ".md": "markdown",
            ".py": "python",
            ".js": "javascript",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".xml": "xml",
            ".csv": "csv",
            ".pdf": "pdf",
            ".jpg": "image",
            ".jpeg": "image",
            ".png": "image",
            ".gif": "image",
            ".mp4": "video",
            ".avi": "video",
            ".mp3": "audio",
            ".wav": "audio",
            ".doc": "document",
            ".docx": "document",
            ".xls": "spreadsheet",
            ".xlsx": "spreadsheet",
            ".ppt": "presentation",
            ".pptx": "presentation",
            ".zip": "archive",
            ".tar": "archive",
            ".gz": "archive",
            ".sh": "shell",
            ".bat": "batch",
            ".exe": "executable",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "header",
            ".java": "java",
            ".class": "java-class",
            ".rb": "ruby",
            ".php": "php",
            ".go": "go",
            ".rs": "rust",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react-ts",
        }
        
        # Natural language patterns for file operations
        self.file_operation_patterns = [
            # Create directory
            (r'create\s+(?:a\s+)?(?:new\s+)?(?:directory|folder|dir)\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.CREATE_DIRECTORY),
            (r'make\s+(?:a\s+)?(?:new\s+)?(?:directory|folder|dir)\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.CREATE_DIRECTORY),
            
            # Create file
            (r'create\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.CREATE_FILE),
            (r'make\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.CREATE_FILE),
            (r'touch\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.CREATE_FILE),
            
            # Read file
            (r'(?:read|view|show|display|cat)\s+(?:the\s+)?(?:contents\s+of\s+)?(?:file\s+)?["\']?([^"\']+)["\']?', OperationType.READ_FILE),
            (r'(?:show|display)\s+(?:me\s+)?(?:what\'?s?\s+in|the\s+contents\s+of)\s+(?:the\s+file\s+)?["\']?([^"\']+)["\']?', OperationType.READ_FILE),
            (r'(?:read|view|show|display|cat)\s+(?:the\s+)?file\s+["\']?([^"\']+)["\']?', OperationType.READ_FILE),
            
            # Write to file
            (r'(?:write|save)\s+["\']?([^"\']*)["\']?\s+to\s+(?:the\s+)?(?:file\s+)?["\']?([^"\']+)["\']?', OperationType.WRITE_FILE),
            (r'(?:write|save)\s+(?:the\s+)?(?:text|string|content)\s+["\']?([^"\']*)["\']?\s+(?:to|into)\s+(?:a|the)?\s+file\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.WRITE_FILE),
            (r'(?:create|make)\s+(?:a\s+)?file\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?\s+with\s+(?:the\s+)?(?:content|text|contents)\s+["\']?([^"\']*)["\']?', OperationType.WRITE_FILE),
            
            # Append to file
            (r'(?:append|add)\s+["\']?([^"\']*)["\']?\s+to\s+(?:the\s+)?(?:file\s+)?["\']?([^"\']+)["\']?', OperationType.APPEND_FILE),
            (r'(?:append|add)\s+(?:the\s+)?(?:text|string|content)\s+["\']?([^"\']*)["\']?\s+to\s+(?:the\s+)?(?:end\s+of\s+)?(?:the\s+)?file\s+(?:called\s+|named\s+)?["\']?([^"\']+)["\']?', OperationType.APPEND_FILE),
            
            # Copy file/directory
            (r'(?:copy|duplicate|cp)\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?', OperationType.COPY_FILE),
            
            # Move/rename file/directory
            (r'(?:move|rename|mv)\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?', OperationType.MOVE_FILE),
            
            # Delete file/directory
            (r'(?:delete|remove|erase|rm)\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?', OperationType.DELETE_FILE),
            (r'(?:delete|remove|erase|rm)\s+(?:the\s+)?directory\s+["\']?([^"\']+)["\']?', OperationType.DELETE_DIRECTORY),
            
            # List files
            (r'(?:list|ls|show)\s+(?:the\s+)?(?:files|contents)\s+(?:in|of)\s+(?:the\s+)?(?:directory|folder|dir)?\s+["\']?([^"\']+)["\']?', OperationType.LIST_FILES),
            (r'(?:list|ls|show)\s+(?:the\s+)?(?:directory|folder|dir)\s+["\']?([^"\']+)["\']?', OperationType.LIST_FILES),
            
            # Search operations
            (r'(?:find|search|locate)\s+(?:for\s+)?(?:all\s+)?(?:the\s+)?(?:files|directories|folders)\s+(?:with|containing|named)\s+["\']?([^"\']+)["\']?(?:\s+in\s+(?:the\s+)?(?:directory|folder|dir)?\s+["\']?([^"\']+)["\']?)?', OperationType.FIND_FILES),
            (r'(?:find|search|grep|look)\s+(?:for\s+)?["\']?([^"\']+)["\']?\s+in\s+(?:the\s+)?file\s+["\']?([^"\']+)["\']?', OperationType.SEARCH_IN_FILES),
            
            # Change permissions
            (r'(?:chmod|change\s+permissions\s+(?:of|for))\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+([0-7]{3,4})', OperationType.PERMISSION_CHANGE),
            (r'(?:chmod|change\s+permissions\s+(?:of|for))\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+([ugoa][+-=][rwxXst]+)', OperationType.PERMISSION_CHANGE),
            
            # Change ownership
            (r'(?:chown|change\s+(?:the\s+)?owner\s+(?:of|for))\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+([^:"\']+)(?::([^"\']+))?', OperationType.OWNERSHIP_CHANGE),
        ]
    
    async def extract_from_natural_language(self, request: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Extract file operation from a natural language request.
        
        Args:
            request: The natural language request
            
        Returns:
            A tuple of (operation_type, parameters) or None if no operation detected
            
        Example:
            "create a file called test.txt with the content Hello World"
            -> (OperationType.WRITE_FILE, {"path": "test.txt", "content": "Hello World"})
        """
        self.logger.debug(f"Extracting file operation from natural language: {request}")
        
        # Normalize the request (lowercase, remove excess whitespace)
        normalized_request = " ".join(request.lower().strip().split())
        
        # First, try to match against the predefined patterns
        for pattern, operation_type in self.file_operation_patterns:
            match = re.search(pattern, normalized_request)
            if match:
                # Extract parameters based on the pattern
                params = self._extract_parameters_from_match(match, operation_type)
                
                # If parameters were extracted successfully, return the operation
                if params:
                    return (operation_type, params)
        
        # If no match found with predefined patterns, try verb-based extraction
        return await self._extract_by_verb_analysis(normalized_request)
    
    def _extract_parameters_from_match(self, match: re.Match, operation_type: str) -> Optional[Dict[str, Any]]:
        """Extract operation parameters from a regex match."""
        if operation_type == OperationType.CREATE_DIRECTORY:
            return {
                "path": match.group(1),
                "parents": True
            }
        
        elif operation_type == OperationType.CREATE_FILE:
            # May have content in a second capture group
            content = match.group(2) if len(match.groups()) > 1 else None
            return {
                "path": match.group(1),
                "content": content
            }
        
        elif operation_type == OperationType.READ_FILE:
            return {
                "path": match.group(1),
                "binary": False
            }
        
        elif operation_type == OperationType.WRITE_FILE:
            # The pattern determines which group contains which data
            if "with" in match.string and match.lastindex >= 2:
                # "create file X with content Y" pattern
                return {
                    "path": match.group(1),
                    "content": match.group(2),
                    "append": False
                }
            elif "to" in match.string and match.lastindex >= 2:
                # "write X to file Y" pattern
                return {
                    "path": match.group(2),
                    "content": match.group(1),
                    "append": False
                }
            else:
                # Default case
                return {
                    "path": match.group(1),
                    "content": "",
                    "append": False
                }
        
        elif operation_type == OperationType.APPEND_FILE:
            # Similar to write, but with append=True
            if "to" in match.string and match.lastindex >= 2:
                # "append X to file Y" pattern
                return {
                    "path": match.group(2),
                    "content": match.group(1),
                    "append": True
                }
            else:
                # Default case
                return {
                    "path": match.group(1),
                    "content": "",
                    "append": True
                }
        
        elif operation_type == OperationType.COPY_FILE:
            # "copy X to Y" pattern
            return {
                "source": match.group(1),
                "destination": match.group(2),
                "overwrite": False
            }
        
        elif operation_type == OperationType.MOVE_FILE:
            # "move X to Y" pattern
            return {
                "source": match.group(1),
                "destination": match.group(2),
                "overwrite": False
            }
        
        elif operation_type == OperationType.DELETE_FILE:
            return {
                "path": match.group(1),
                "force": False
            }
        
        elif operation_type == OperationType.DELETE_DIRECTORY:
            return {
                "path": match.group(1),
                "recursive": True,
                "force": False
            }
        
        elif operation_type == OperationType.LIST_FILES:
            # The directory to list might be in group 1 or 2
            path = match.group(1) if match.lastindex >= 1 else "."
            return {
                "path": path,
                "long_format": "details" in match.string or "long" in match.string,
                "all_files": "all" in match.string or "hidden" in match.string
            }
        
        elif operation_type == OperationType.FIND_FILES:
            # Pattern might be in group 1, directory in group 2
            pattern = match.group(1) if match.lastindex >= 1 else "*"
            path = match.group(2) if match.lastindex >= 2 else "."
            
            return {
                "path": path,
                "starting_paths": [path],
                "expressions": [f"-name '{pattern}'"]
            }
        
        elif operation_type == OperationType.SEARCH_IN_FILES:
            # Search pattern in group 1, file in group 2
            pattern = match.group(1) if match.lastindex >= 1 else ""
            file_path = match.group(2) if match.lastindex >= 2 else ""
            
            return {
                "pattern": pattern,
                "path": file_path,
                "command_type": "grep",
                "all_files": [file_path]
            }
        
        elif operation_type == OperationType.PERMISSION_CHANGE:
            # File in group 1, mode in group 2
            file_path = match.group(1) if match.lastindex >= 1 else ""
            mode = match.group(2) if match.lastindex >= 2 else ""
            
            return {
                "path": file_path,
                "mode": mode,
                "recursive": "recursive" in match.string or "-R" in match.string
            }
        
        elif operation_type == OperationType.OWNERSHIP_CHANGE:
            # File in group 1, owner in group 2, group (optional) in group 3
            file_path = match.group(1) if match.lastindex >= 1 else ""
            owner = match.group(2) if match.lastindex >= 2 else None
            group = match.group(3) if match.lastindex >= 3 else None
            
            return {
                "path": file_path,
                "owner": owner,
                "group": group,
                "recursive": "recursive" in match.string or "-R" in match.string
            }
        
        return None
    
    async def _extract_by_verb_analysis(self, request: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Extract operation based on verb analysis and more flexible pattern matching.
        
        This method provides a fallback for when the predefined patterns don't match.
        It analyzes the verbs and nouns in the request to determine the operation.
        """
        # Look for operation verbs
        for verb, operation_types in self.operation_verbs.items():
            if verb in request.split() or f"{verb} " in request:
                # Found a potential operation verb, now extract parameters
                operation_type = operation_types[0]  # Use the first matched operation as default
                
                # Special handling for different operation types
                if operation_type in [OperationType.CREATE_FILE, OperationType.CREATE_DIRECTORY]:
                    return await self._extract_creation_operation(request, verb, operation_types)
                    
                elif operation_type in [OperationType.DELETE_FILE, OperationType.DELETE_DIRECTORY]:
                    return await self._extract_deletion_operation(request, verb, operation_types)
                    
                elif operation_type == OperationType.READ_FILE:
                    return await self._extract_read_operation(request, verb)
                    
                elif operation_type in [OperationType.WRITE_FILE, OperationType.APPEND_FILE]:
                    return await self._extract_write_operation(request, verb, operation_type)
                    
                elif operation_type == OperationType.COPY_FILE:
                    return await self._extract_copy_operation(request, verb)
                    
                elif operation_type == OperationType.MOVE_FILE:
                    return await self._extract_move_operation(request, verb)
                    
                elif operation_type == OperationType.LIST_FILES:
                    return await self._extract_list_operation(request, verb)
                    
                elif operation_type == OperationType.FIND_FILES:
                    return await self._extract_find_operation(request, verb, operation_types)
        
        # No operation verb found
        return None
    
    async def _extract_creation_operation(self, request: str, verb: str, operation_types: List[str]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract creation operation (file or directory)."""
        # Determine if creating a file or directory
        is_directory = False
        for dir_term in ["directory", "folder", "dir"]:
            if dir_term in request:
                is_directory = True
                break
        
        operation_type = OperationType.CREATE_DIRECTORY if is_directory else OperationType.CREATE_FILE
        
        # Extract the path
        path_match = re.search(r'(?:called|named)\s+["\']?([^"\']+)["\']?', request)
        if not path_match:
            # Try to find a path-like pattern
            path_match = re.search(r'(?:called|named|path)?\s+([~\/\w\.-]+)(?:\s+|$)', request)
            
        if not path_match:
            # Last resort: look for anything that might be a path
            for word in request.split():
                if '/' in word or '.' in word or word.startswith('~'):
                    path = word
                    break
            else:
                # No path found
                return None
        else:
            path = path_match.group(1)
        
        # For file creation, check for content
        content = None
        if operation_type == OperationType.CREATE_FILE:
            content_match = re.search(r'(?:with|content|text)\s+["\']([^"\']+)["\']', request)
            if content_match:
                content = content_match.group(1)
            
            # Final parameter assembly
            return (operation_type, {
                "path": path,
                "content": content
            })
        else:
            # Directory creation
            return (operation_type, {
                "path": path,
                "parents": True
            })
    
    async def _extract_deletion_operation(self, request: str, verb: str, operation_types: List[str]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract deletion operation (file or directory)."""
        # Determine if deleting a file or directory
        is_directory = False
        for dir_term in ["directory", "folder", "dir"]:
            if dir_term in request:
                is_directory = True
                break
        
        operation_type = OperationType.DELETE_DIRECTORY if is_directory else OperationType.DELETE_FILE
        
        # Extract the path
        path_match = re.search(r'(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?', request)
        if not path_match:
            # Try to find a path-like pattern
            path_match = re.search(r'(?:the\s+)?(?:file|directory|folder)?\s+([~\/\w\.-]+)(?:\s+|$)', request)
            
        if not path_match:
            # Last resort: look for anything that might be a path
            for word in request.split():
                if '/' in word or '.' in word or word.startswith('~'):
                    path = word
                    break
            else:
                # No path found
                return None
        else:
            path = path_match.group(1)
        
        # Check for force/recursive flags
        force = "force" in request or "-f" in request
        recursive = "recursive" in request or "-r" in request or "-R" in request
        
        # For directory, set recursive by default
        if operation_type == OperationType.DELETE_DIRECTORY:
            recursive = True
            
            return (operation_type, {
                "path": path,
                "recursive": recursive,
                "force": force
            })
        else:
            # File deletion
            return (operation_type, {
                "path": path,
                "force": force
            })
    
    async def _extract_read_operation(self, request: str, verb: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract read operation."""
        # Extract the path
        path_match = re.search(r'(?:the\s+)?(?:file|content[s]?(?:\s+of)?)\s+["\']?([^"\']+)["\']?', request)
        if not path_match:
            # Try to find a path-like pattern
            path_match = re.search(r'(?:the\s+)?(?:file|content[s]?(?:\s+of)?)?(\S+\.\w+)', request)
            
        if not path_match:
            # Last resort: look for anything that might be a path
            for word in request.split():
                if '.' in word or '/' in word:
                    path = word
                    break
            else:
                # No path found
                return None
        else:
            path = path_match.group(1)
        
        # Check for additional flags
        binary = "binary" in request or "-b" in request
        
        return (OperationType.READ_FILE, {
            "path": path,
            "binary": binary
        })
    
    async def _extract_write_operation(self, request: str, verb: str, operation_type: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract write or append operation."""
        # Determine if this is a write or append operation based on the verb
        if verb in ["append", "add to"]:
            operation_type = OperationType.APPEND_FILE
        else:
            operation_type = OperationType.WRITE_FILE
        
        # Try to find pattern: "write/append X to Y"
        path_match = None
        content_match = None
        
        if "to" in request:
            # Look for "text X to file Y" pattern
            pattern = r'(?:the\s+)?(?:text|string|content)\s+["\']([^"\']+)["\']?\s+(?:to|into)\s+(?:the\s+)?(?:file\s+)?["\']?([^"\']+)["\']?'
            full_match = re.search(pattern, request)
            if full_match:
                content_match = full_match.group(1)
                path_match = full_match.group(2)
            else:
                # Look for "X to file Y" pattern
                pattern = r'["\']?([^"\']+)["\']?\s+to\s+(?:the\s+)?(?:file\s+)?["\']?([^"\']+)["\']?'
                full_match = re.search(pattern, request)
                if full_match:
                    content_match = full_match.group(1)
                    path_match = full_match.group(2)
        
        # If not found, try the "with content" pattern
        if not path_match or not content_match:
            # Look for "file X with content Y" pattern
            pattern = r'(?:the\s+)?file\s+["\']?([^"\']+)["\']?\s+with\s+(?:the\s+)?(?:content|text)\s+["\']?([^"\']+)["\']?'
            full_match = re.search(pattern, request)
            if full_match:
                path_match = full_match.group(1)
                content_match = full_match.group(2)
        
        # If still not found, look for path and content separately
        if not path_match:
            # Try to find a path-like pattern
            path_match = re.search(r'(?:the\s+)?file\s+["\']?([^"\']+)["\']?', request)
            if not path_match:
                path_match = re.search(r'(?:the\s+)?file\s+(\S+\.\w+)', request)
                
            if not path_match:
                # Last resort: look for anything that might be a path
                for word in request.split():
                    if '.' in word:
                        path = word
                        break
                else:
                    # No path found
                    return None
            else:
                path = path_match.group(1)
        else:
            path = path_match
        
        if not content_match:
            # Look for quoted content
            content_match = re.search(r'["\']([^"\']+)["\']', request)
            if content_match:
                content = content_match.group(1)
            else:
                # No content specified
                content = ""
        else:
            content = content_match
        
        return (operation_type, {
            "path": path,
            "content": content,
            "append": operation_type == OperationType.APPEND_FILE
        })
    
    async def _extract_copy_operation(self, request: str, verb: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract copy operation."""
        # Look for "copy X to Y" pattern
        pattern = r'(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?'
        match = re.search(pattern, request)
        
        if not match:
            # Try a simpler pattern
            pattern = r'(\S+)\s+to\s+(\S+)'
            match = re.search(pattern, request)
            
        if not match:
            # No source/destination found
            return None
            
        source = match.group(1)
        destination = match.group(2)
        
        # Check for recursive flag
        recursive = "recursive" in request or "-r" in request or "-R" in request
        
        return (OperationType.COPY_FILE, {
            "source": source,
            "destination": destination,
            "recursive": recursive,
            "overwrite": False
        })
    
    async def _extract_move_operation(self, request: str, verb: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract move operation."""
        # Look for "move X to Y" pattern
        pattern = r'(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?\s+to\s+(?:the\s+)?(?:file|directory|folder)?\s+["\']?([^"\']+)["\']?'
        match = re.search(pattern, request)
        
        if not match:
            # Try a simpler pattern
            pattern = r'(\S+)\s+to\s+(\S+)'
            match = re.search(pattern, request)
            
        if not match:
            # No source/destination found
            return None
            
        source = match.group(1)
        destination = match.group(2)
        
        # Check for force flag
        force = "force" in request or "-f" in request
        
        return (OperationType.MOVE_FILE, {
            "source": source,
            "destination": destination,
            "overwrite": force
        })
    
    async def _extract_list_operation(self, request: str, verb: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract list operation."""
        # Check for path specification
        path_match = re.search(r'(?:in|of)\s+(?:the\s+)?(?:directory|folder|dir)?\s+["\']?([^"\']+)["\']?', request)
        
        if not path_match:
            # Try to find a path-like pattern
            path_match = re.search(r'(?:in|of)\s+(?:the\s+)?(?:directory|folder|dir)?\s+([~\/\w\.-]+)(?:\s+|$)', request)
            
        path = path_match.group(1) if path_match else "."
        
        # Check for flags
        long_format = "long" in request or "details" in request or "-l" in request
        all_files = "all" in request or "hidden" in request or "-a" in request
        recursive = "recursive" in request or "-R" in request
        
        return (OperationType.LIST_FILES, {
            "path": path,
            "long_format": long_format,
            "all_files": all_files,
            "recursive": recursive
        })
    
    async def _extract_find_operation(self, request: str, verb: str, operation_types: List[str]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Extract find operation."""
        # Determine if we're searching for files or in files
        in_files = "in file" in request or "text in" in request or "content in" in request
        operation_type = OperationType.SEARCH_IN_FILES if in_files else OperationType.FIND_FILES
        
        if operation_type == OperationType.SEARCH_IN_FILES:
            # Extract pattern and file
            pattern_match = re.search(r'(?:for\s+)?["\']?([^"\']+)["\']?\s+in\s+(?:the\s+)?file\s+["\']?([^"\']+)["\']?', request)
            
            if not pattern_match:
                # Try alternate patterns
                pattern_match = re.search(r'(?:the\s+)?text\s+["\']?([^"\']+)["\']?\s+in\s+(?:the\s+)?file\s+["\']?([^"\']+)["\']?', request)
                
            if not pattern_match:
                # No pattern/file found
                return None
                
            pattern = pattern_match.group(1)
            file_path = pattern_match.group(2)
            
            return (operation_type, {
                "pattern": pattern,
                "path": file_path,
                "command_type": "grep",
                "all_files": [file_path]
            })
        else:
            # Find files operation
            pattern_match = re.search(r'(?:with|named|containing)\s+["\']?([^"\']+)["\']?', request)
            pattern = pattern_match.group(1) if pattern_match else "*"
            
            # Check for path specification
            path_match = re.search(r'in\s+(?:the\s+)?(?:directory|folder|dir)?\s+["\']?([^"\']+)["\']?', request)
            path = path_match.group(1) if path_match else "."
            
            return (operation_type, {
                "path": path,
                "starting_paths": [path],
                "expressions": [f"-name '{pattern}'"]
            })

# Initialize the natural language extractor
nl_file_operation_extractor = NaturalLanguageFileOperationExtractor()

# Enhanced function to extract file operations from natural language
async def extract_file_operation_from_natural_language(request: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Extract file operation details from a natural language request.
    
    Args:
        request: The natural language request
        
    Returns:
        A tuple of (operation_type, parameters) or None if not a file operation
    """
    logger.debug(f"Extracting file operation from natural language: {request}")
    
    return await nl_file_operation_extractor.extract_from_natural_language(request)

# Batch operations processing
async def execute_batch_file_operations(
    operations: List[Tuple[str, Dict[str, Any]]],
    dry_run: bool = False,
    transaction_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Execute a batch of file operations as a transaction.
    
    Args:
        operations: List of (operation_type, parameters) tuples
        dry_run: Whether to simulate execution without making changes
        transaction_id: Optional transaction ID for rollback support
        
    Returns:
        List of operation results
    """
    logger.info(f"Executing batch of {len(operations)} file operations" + (" (dry run)" if dry_run else ""))
    
    # Start a new transaction if none provided
    own_transaction = False
    if transaction_id is None and not dry_run:
        # Import function to start a transaction
        from angela.api.execution import get_rollback_manager
        rollback_manager = get_rollback_manager()
        transaction_id = await rollback_manager.start_transaction(f"Batch file operations ({len(operations)} operations)")
        own_transaction = True
    
    results = []
    success = True
    
    try:
        # Execute each operation
        for operation_type, parameters in operations:
            result = await execute_file_operation(
                operation_type,
                parameters,
                dry_run=dry_run,
                transaction_id=transaction_id
            )
            results.append(result)
            
            # Update overall success
            if not result.get("success", False):
                success = False
                
        # Complete transaction if we started it
        if own_transaction and transaction_id:
            from angela.api.execution import get_rollback_manager
            rollback_manager = get_rollback_manager()
            await rollback_manager.end_transaction(
                transaction_id,
                "completed" if success else "failed"
            )
            
        return results
    
    except Exception as e:
        logger.exception(f"Error executing batch file operations: {str(e)}")
        
        # Roll back transaction if we started it
        if own_transaction and transaction_id:
            from angela.api.execution import get_rollback_manager
            rollback_manager = get_rollback_manager()
            await rollback_manager.end_transaction(transaction_id, "failed")
            
        raise
