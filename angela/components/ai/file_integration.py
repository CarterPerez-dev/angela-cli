# angela/ai/file_integration.py
"""
Integration module for AI-powered file operations.

This module bridges the AI suggestions with actual file operations,
extracting file operations from commands and executing them safely.
"""
import re
import shlex
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

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

# Patterns for file operation commands
FILE_OPERATION_PATTERNS = [
    # mkdir patterns
    (r"^mkdir\s+(-p\s+)?(.+)$", "create_directory"),
    
    # rmdir and rm -r patterns
    (r"^rmdir\s+(.+)$", "delete_directory"),
    (r"^rm\s+(-r|-rf|--recursive)\s+(.+)$", "delete_directory"),
    
    # touch patterns
    (r"^touch\s+(.+)$", "create_file"),
    
    # cat/less/more patterns (read)
    (r"^(cat|less|more|head|tail)\s+(.+)$", "read_file"),
    
    # echo > patterns (write)
    (r"^echo\s+(.+)\s+>\s+(.+)$", "write_file"),
    (r"^echo\s+(.+)\s+>>\s+(.+)$", "append_file"),
    
    # rm patterns
    (r"^rm\s+(?!-r|--recursive)(.+)$", "delete_file"),
    
    # cp patterns
    (r"^cp\s+(?!-r|--recursive)(.+?)\s+(.+)$", "copy_file"),
    
    # mv patterns
    (r"^mv\s+(.+?)\s+(.+)$", "move_file"),
]

# Specific operation extractors
async def extract_mkdir_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract mkdir operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Check for -p/--parents flag
    parents = "-p" in tokens or "--parents" in tokens
    
    # Get directory paths
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith("-"):
            paths.append(arg)
    
    return "create_directory", {"path": paths[0] if paths else ".", "parents": parents}


async def extract_rmdir_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract rmdir operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Check for recursive flag in rm commands
    recursive = any(flag in tokens for flag in ["-r", "-rf", "--recursive", "-R"])
    force = any(flag in tokens for flag in ["-f", "-rf", "--force"])
    
    # Get directory paths
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith("-"):
            paths.append(arg)
    
    return "delete_directory", {
        "path": paths[0] if paths else ".",
        "recursive": recursive,
        "force": force
    }


async def extract_touch_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract touch operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Get file paths
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith("-"):
            paths.append(arg)
    
    return "create_file", {"path": paths[0] if paths else ".", "content": None}


async def extract_cat_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract cat operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Get file paths
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith("-"):
            paths.append(arg)
    
    # Check for binary flag
    binary = "-b" in tokens or "--binary" in tokens
    
    return "read_file", {"path": paths[0] if paths else ".", "binary": binary}


async def extract_echo_write_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract echo write operation parameters from a command."""
    # Determine if this is append (>>) or overwrite (>)
    append = ">>" in command
    
    # Split by redirection operator
    parts = command.split(">>" if append else ">", 1)
    
    # Extract the echo part and the file path
    echo_part = parts[0].strip()[5:]  # Remove 'echo ' prefix
    file_path = parts[1].strip()
    
    # Handle quoted content
    if echo_part.startswith('"') and echo_part.endswith('"'):
        content = echo_part[1:-1]
    elif echo_part.startswith("'") and echo_part.endswith("'"):
        content = echo_part[1:-1]
    else:
        content = echo_part
    
    return "write_file", {
        "path": file_path,
        "content": content,
        "append": append
    }


async def extract_rm_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract rm operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Check for force flag
    force = "-f" in tokens or "--force" in tokens
    
    # Get file paths
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith("-"):
            paths.append(arg)
    
    return "delete_file", {"path": paths[0] if paths else ".", "force": force}


async def extract_cp_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract cp operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Check for force/overwrite flag
    overwrite = "-f" in tokens or "--force" in tokens
    
    # Get source and destination
    args = [arg for arg in tokens[1:] if not arg.startswith("-")]
    
    if len(args) >= 2:
        source = args[0]
        destination = args[-1]  # Last argument is always the destination
    else:
        # Not enough arguments
        raise ValueError("cp command requires source and destination")
    
    return "copy_file", {
        "source": source,
        "destination": destination,
        "overwrite": overwrite
    }


async def extract_mv_operation(command: str) -> Tuple[str, Dict[str, Any]]:
    """Extract mv operation parameters from a command."""
    tokens = shlex.split(command)
    
    # Check for force/overwrite flag
    overwrite = "-f" in tokens or "--force" in tokens
    
    # Get source and destination
    args = [arg for arg in tokens[1:] if not arg.startswith("-")]
    
    if len(args) >= 2:
        source = args[0]
        destination = args[-1]  # Last argument is always the destination
    else:
        # Not enough arguments
        raise ValueError("mv command requires source and destination")
    
    return "move_file", {
        "source": source,
        "destination": destination,
        "overwrite": overwrite
    }


# Operation extractors mapping
OPERATION_EXTRACTORS = {
    "mkdir": extract_mkdir_operation,
    "rmdir": extract_rmdir_operation,
    "rm": extract_rmdir_operation if "-r" in "{command}" or "--recursive" in "{command}" else extract_rm_operation,
    "touch": extract_touch_operation,
    "cat": extract_cat_operation,
    "less": extract_cat_operation,
    "more": extract_cat_operation,
    "head": extract_cat_operation,
    "tail": extract_cat_operation,
    "echo": extract_echo_write_operation,
    "cp": extract_cp_operation,
    "mv": extract_mv_operation,
}


async def extract_file_operation(command: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Extract file operation details from a command string.
    
    Args:
        command: The shell command to analyze.
        
    Returns:
        A tuple of (operation_type, parameters) or None if not a file operation.
    """
    try:
        # Get the base command
        tokens = shlex.split(command)
        if not tokens:
            return None
        
        base_cmd = tokens[0]
        
        # Check if this is a known file operation
        if base_cmd in OPERATION_EXTRACTORS:
            # Use the specific extractor for this command
            extractor = OPERATION_EXTRACTORS[base_cmd]
            
            # For rm, we need to check if it's recursive
            if base_cmd == "rm":
                if any(flag in tokens for flag in ["-r", "-rf", "--recursive", "-R"]):
                    return await extract_rmdir_operation(command)
                else:
                    return await extract_rm_operation(command)
            
            # For other commands, use the registered extractor
            return await extractor(command)
        
        # Fall back to pattern matching
        for pattern, operation_type in FILE_OPERATION_PATTERNS:
            match = re.match(pattern, command)
            if match:
                # Basic extraction based on pattern groups
                if operation_type == "create_directory":
                    return operation_type, {"path": match.group(2), "parents": bool(match.group(1))}
                elif operation_type == "delete_directory":
                    return operation_type, {"path": match.group(1), "recursive": "-r" in command or "-rf" in command}
                elif operation_type == "create_file":
                    return operation_type, {"path": match.group(1), "content": None}
                elif operation_type == "read_file":
                    return operation_type, {"path": match.group(2)}
                elif operation_type == "write_file":
                    return operation_type, {"path": match.group(2), "content": match.group(1), "append": False}
                elif operation_type == "append_file":
                    return operation_type, {"path": match.group(2), "content": match.group(1), "append": True}
                elif operation_type == "delete_file":
                    return operation_type, {"path": match.group(1)}
                elif operation_type == "copy_file":
                    parts = match.group(1).rsplit(" ", 1)
                    if len(parts) == 2:
                        return operation_type, {"source": parts[0], "destination": parts[1]}
                elif operation_type == "move_file":
                    parts = match.group(1).rsplit(" ", 1)
                    if len(parts) == 2:
                        return operation_type, {"source": parts[0], "destination": parts[1]}
        
        # Not a file operation
        return None
    
    except Exception as e:
        logger.exception(f"Error extracting file operation from '{command}': {str(e)}")
        return None


async def execute_file_operation(
    operation_type: str, 
    parameters: Dict[str, Any],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute a file operation based on type and parameters.
    
    Args:
        operation_type: The type of file operation.
        parameters: Parameters for the operation.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        A dictionary with the operation results.
    """
    try:
        logger.info(f"Executing file operation: {operation_type}")
        logger.debug(f"Parameters: {parameters}")
        
        result = {
            "operation": operation_type,
            "parameters": parameters,
            "success": False,
            "dry_run": dry_run,
        }
        
        # Execute the appropriate operation
        if operation_type == "create_directory":
            path = parameters.get("path")
            parents = parameters.get("parents", True)
            
            create_directory_func = get_create_directory_func()
            success = await create_directory_func(path, parents=parents, dry_run=dry_run)
            result["success"] = success
            
        elif operation_type == "delete_directory":
            path = parameters.get("path")
            recursive = parameters.get("recursive", False)
            force = parameters.get("force", False)
            
            delete_directory_func = get_delete_directory_func()
            success = await delete_directory_func(
                path, recursive=recursive, force=force, dry_run=dry_run
            )
            result["success"] = success
            
        elif operation_type == "create_file":
            path = parameters.get("path")
            content = parameters.get("content")
            
            create_file_func = get_create_file_func()
            success = await create_file_func(path, content=content, dry_run=dry_run)
            result["success"] = success
            
        elif operation_type == "read_file":
            path = parameters.get("path")
            binary = parameters.get("binary", False)
            
            read_file_func = get_read_file_func()
            content = await read_file_func(path, binary=binary)
            result["content"] = content
            result["success"] = True
            
        elif operation_type == "write_file":
            path = parameters.get("path")
            content = parameters.get("content", "")
            append = parameters.get("append", False)
            
            write_file_func = get_write_file_func()
            success = await write_file_func(
                path, content, append=append, dry_run=dry_run
            )
            result["success"] = success
            
        elif operation_type == "delete_file":
            path = parameters.get("path")
            force = parameters.get("force", False)
            
            delete_file_func = get_delete_file_func()
            success = await delete_file_func(path, force=force, dry_run=dry_run)
            result["success"] = success
            
        elif operation_type == "copy_file":
            source = parameters.get("source")
            destination = parameters.get("destination")
            overwrite = parameters.get("overwrite", False)
            
            copy_file_func = get_copy_file_func()
            success = await copy_file_func(
                source, destination, overwrite=overwrite, dry_run=dry_run
            )
            result["success"] = success
            
        elif operation_type == "move_file":
            source = parameters.get("source")
            destination = parameters.get("destination")
            overwrite = parameters.get("overwrite", False)
            
            move_file_func = get_move_file_func()
            success = await move_file_func(
                source, destination, overwrite=overwrite, dry_run=dry_run
            )
            result["success"] = success
            
        else:
            logger.warning(f"Unknown file operation: {operation_type}")
            result["error"] = f"Unknown file operation: {operation_type}"
        
        return result
        
    except get_filesystem_error_class() as e:
        logger.exception(f"Error executing file operation: {str(e)}")
        return {
            "operation": operation_type,
            "parameters": parameters,
            "success": False,
            "error": str(e),
            "dry_run": dry_run,
        }
    except Exception as e:
        logger.exception(f"Unexpected error in file operation: {str(e)}")
        return {
            "operation": operation_type,
            "parameters": parameters,
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "dry_run": dry_run,
        }
