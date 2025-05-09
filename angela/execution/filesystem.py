# angela/execution/filesystem.py
"""
File system operations for Angela CLI.

This module provides high-level file and directory operations with safety checks
and proper error handling.
"""
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, BinaryIO, TextIO

from angela.utils.logging import get_logger
from angela.safety import check_operation_safety

logger = get_logger(__name__)

# Directory for storing backup files for rollback operations
BACKUP_DIR = Path(tempfile.gettempdir()) / "angela-backups"


class FileSystemError(Exception):
    """Exception raised for file system operation errors."""
    pass


# Ensure backup directory exists
def _ensure_backup_dir():
    """Create the backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


async def create_directory(
    path: Union[str, Path], 
    parents: bool = True,
    dry_run: bool = False
) -> bool:
    """
    Create a directory at the specified path.
    
    Args:
        path: The path where the directory should be created.
        parents: Whether to create parent directories if they don't exist.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    path_obj = Path(path)
    operation_params = {
        'path': str(path_obj),
        'parents': parents
    }
    
    try:
        # Check if the operation is safe
        if not await check_operation_safety('create_directory', operation_params, dry_run):
            return False
        
        # If this is a dry run, stop here
        if dry_run:
            logger.info(f"DRY RUN: Would create directory at {path_obj}")
            return True
        
        # Create the directory
        if parents:
            path_obj.mkdir(parents=True, exist_ok=True)
        else:
            path_obj.mkdir(exist_ok=False)
        
        logger.info(f"Created directory at {path_obj}")
        return True
    
    except Exception as e:
        logger.exception(f"Error creating directory at {path_obj}: {str(e)}")
        raise FileSystemError(f"Failed to create directory: {str(e)}")


async def delete_directory(
    path: Union[str, Path], 
    recursive: bool = False,
    force: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Delete a directory at the specified path.
    
    Args:
        path: The path of the directory to delete.
        recursive: Whether to recursively delete contents (rmdir vs rm -r).
        force: Whether to ignore errors if the directory doesn't exist.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    path_obj = Path(path)
    operation_params = {
        'path': str(path_obj),
        'recursive': recursive,
        'force': force
    }
    
    try:
        # Check if the directory exists
        if not path_obj.exists():
            if force:
                logger.info(f"Directory does not exist, but force=True: {path_obj}")
                return True
            else:
                raise FileSystemError(f"Directory does not exist: {path_obj}")
        
        # Verify it's actually a directory
        if not path_obj.is_dir():
            raise FileSystemError(f"Path is not a directory: {path_obj}")
        
        # Check if the operation is safe
        if not await check_operation_safety('delete_directory', operation_params, dry_run):
            return False
        
        # Create a backup for rollback if needed
        if not dry_run and recursive:
            await _backup_directory(path_obj)
        
        # If this is a dry run, stop here
        if dry_run:
            logger.info(f"DRY RUN: Would delete directory at {path_obj}")
            return True
        
        # Delete the directory
        if recursive:
            shutil.rmtree(path_obj)
            logger.info(f"Recursively deleted directory at {path_obj}")
        else:
            path_obj.rmdir()
            logger.info(f"Deleted directory at {path_obj}")
        
        return True
    
    except Exception as e:
        logger.exception(f"Error deleting directory at {path_obj}: {str(e)}")
        raise FileSystemError(f"Failed to delete directory: {str(e)}")


async def create_file(
    path: Union[str, Path], 
    content: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """
    Create a file at the specified path with optional content.
    
    Args:
        path: The path where the file should be created.
        content: Optional content to write to the file (if None, like touch).
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    path_obj = Path(path)
    operation_params = {
        'path': str(path_obj),
        'content': content is not None
    }
    
    try:
        # Check if the operation is safe
        if not await check_operation_safety('create_file', operation_params, dry_run):
            return False
        
        # If this is a dry run, stop here
        if dry_run:
            if content:
                logger.info(f"DRY RUN: Would create file with content at {path_obj}")
            else:
                logger.info(f"DRY RUN: Would touch file at {path_obj}")
            return True
        
        # Make sure parent directory exists
        if not path_obj.parent.exists():
            await create_directory(path_obj.parent, dry_run=False)
        
        # Handle backup if the file already exists
        if path_obj.exists():
            await _backup_file(path_obj)
        
        # Create/write the file
        if content is not None:
            with open(path_obj, 'w') as f:
                f.write(content)
            logger.info(f"Created file with content at {path_obj}")
        else:
            path_obj.touch()
            logger.info(f"Touched file at {path_obj}")
        
        return True
    
    except Exception as e:
        logger.exception(f"Error creating file at {path_obj}: {str(e)}")
        raise FileSystemError(f"Failed to create file: {str(e)}")


async def read_file(
    path: Union[str, Path], 
    binary: bool = False
) -> Union[str, bytes]:
    """
    Read the content of a file.
    
    Args:
        path: The path of the file to read.
        binary: Whether to read the file in binary mode.
        
    Returns:
        The content of the file as a string or bytes.
    """
    path_obj = Path(path)
    operation_params = {
        'path': str(path_obj),
        'binary': binary
    }
    
    try:
        # Check if the file exists
        if not path_obj.exists():
            raise FileSystemError(f"File does not exist: {path_obj}")
        
        # Verify it's actually a file
        if not path_obj.is_file():
            raise FileSystemError(f"Path is not a file: {path_obj}")
        
        # Check if the operation is safe
        if not await check_operation_safety('read_file', operation_params, False):
            raise FileSystemError("Operation not permitted due to safety constraints")
        
        # Read the file
        if binary:
            with open(path_obj, 'rb') as f:
                content = f.read()
        else:
            with open(path_obj, 'r', errors='replace') as f:
                content = f.read()
        
        logger.info(f"Read file at {path_obj}")
        return content
    
    except Exception as e:
        logger.exception(f"Error reading file at {path_obj}: {str(e)}")
        raise FileSystemError(f"Failed to read file: {str(e)}")


async def write_file(
    path: Union[str, Path], 
    content: Union[str, bytes],
    append: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Write content to a file.
    
    Args:
        path: The path of the file to write.
        content: The content to write to the file.
        append: Whether to append to the file instead of overwriting.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    path_obj = Path(path)
    is_binary = isinstance(content, bytes)
    operation_params = {
        'path': str(path_obj),
        'append': append,
        'binary': is_binary
    }
    
    try:
        # Check if the operation is safe
        if not await check_operation_safety('write_file', operation_params, dry_run):
            return False
        
        # If this is a dry run, stop here
        if dry_run:
            mode = "append to" if append else "write to"
            logger.info(f"DRY RUN: Would {mode} file at {path_obj}")
            return True
        
        # Make sure parent directory exists
        if not path_obj.parent.exists():
            await create_directory(path_obj.parent, dry_run=False)
        
        # Handle backup if the file already exists
        if path_obj.exists():
            await _backup_file(path_obj)
        
        # Write the file
        mode = 'ab' if append and is_binary else 'wb' if is_binary else 'a' if append else 'w'
        with open(path_obj, mode) as f:
            f.write(content)
        
        action = "Appended to" if append else "Wrote to"
        logger.info(f"{action} file at {path_obj}")
        return True
    
    except Exception as e:
        logger.exception(f"Error writing to file at {path_obj}: {str(e)}")
        raise FileSystemError(f"Failed to write file: {str(e)}")


async def delete_file(
    path: Union[str, Path], 
    force: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Delete a file at the specified path.
    
    Args:
        path: The path of the file to delete.
        force: Whether to ignore errors if the file doesn't exist.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    path_obj = Path(path)
    operation_params = {
        'path': str(path_obj),
        'force': force
    }
    
    try:
        # Check if the file exists
        if not path_obj.exists():
            if force:
                logger.info(f"File does not exist, but force=True: {path_obj}")
                return True
            else:
                raise FileSystemError(f"File does not exist: {path_obj}")
        
        # Verify it's actually a file
        if not path_obj.is_file():
            raise FileSystemError(f"Path is not a file: {path_obj}")
        
        # Check if the operation is safe
        if not await check_operation_safety('delete_file', operation_params, dry_run):
            return False
        
        # Create a backup for rollback if needed
        if not dry_run:
            await _backup_file(path_obj)
        
        # If this is a dry run, stop here
        if dry_run:
            logger.info(f"DRY RUN: Would delete file at {path_obj}")
            return True
        
        # Delete the file
        path_obj.unlink()
        logger.info(f"Deleted file at {path_obj}")
        
        return True
    
    except Exception as e:
        logger.exception(f"Error deleting file at {path_obj}: {str(e)}")
        raise FileSystemError(f"Failed to delete file: {str(e)}")


async def copy_file(
    source: Union[str, Path], 
    destination: Union[str, Path],
    overwrite: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Copy a file from source to destination.
    
    Args:
        source: The path of the file to copy.
        destination: The destination path.
        overwrite: Whether to overwrite the destination if it exists.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    source_obj = Path(source)
    dest_obj = Path(destination)
    operation_params = {
        'source': str(source_obj),
        'destination': str(dest_obj),
        'overwrite': overwrite
    }
    
    try:
        # Check if the source file exists
        if not source_obj.exists():
            raise FileSystemError(f"Source file does not exist: {source_obj}")
        
        # Verify source is actually a file
        if not source_obj.is_file():
            raise FileSystemError(f"Source path is not a file: {source_obj}")
        
        # Check if the destination exists and handle overwrite
        if dest_obj.exists():
            if not overwrite:
                raise FileSystemError(f"Destination already exists: {dest_obj}")
            
            # Create a backup of the destination file
            if not dry_run:
                await _backup_file(dest_obj)
        
        # Check if the operation is safe
        if not await check_operation_safety('copy_file', operation_params, dry_run):
            return False
        
        # If this is a dry run, stop here
        if dry_run:
            logger.info(f"DRY RUN: Would copy {source_obj} to {dest_obj}")
            return True
        
        # Make sure parent directory exists
        if not dest_obj.parent.exists():
            await create_directory(dest_obj.parent, dry_run=False)
        
        # Copy the file
        shutil.copy2(source_obj, dest_obj)
        logger.info(f"Copied {source_obj} to {dest_obj}")
        
        return True
    
    except Exception as e:
        logger.exception(f"Error copying {source_obj} to {dest_obj}: {str(e)}")
        raise FileSystemError(f"Failed to copy file: {str(e)}")


async def move_file(
    source: Union[str, Path], 
    destination: Union[str, Path],
    overwrite: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Move a file from source to destination.
    
    Args:
        source: The path of the file to move.
        destination: The destination path.
        overwrite: Whether to overwrite the destination if it exists.
        dry_run: Whether to simulate the operation without making changes.
        
    Returns:
        True if the operation was successful, False otherwise.
    """
    source_obj = Path(source)
    dest_obj = Path(destination)
    operation_params = {
        'source': str(source_obj),
        'destination': str(dest_obj),
        'overwrite': overwrite
    }
    
    try:
        # Check if the source file exists
        if not source_obj.exists():
            raise FileSystemError(f"Source file does not exist: {source_obj}")
        
        # Verify source is actually a file
        if not source_obj.is_file():
            raise FileSystemError(f"Source path is not a file: {source_obj}")
        
        # Check if the destination exists and handle overwrite
        if dest_obj.exists():
            if not overwrite:
                raise FileSystemError(f"Destination already exists: {dest_obj}")
            
            # Create a backup of the destination file
            if not dry_run:
                await _backup_file(dest_obj)
        
        # Check if the operation is safe
        if not await check_operation_safety('move_file', operation_params, dry_run):
            return False
        
        # Create a backup of the source file
        if not dry_run:
            await _backup_file(source_obj)
        
        # If this is a dry run, stop here
        if dry_run:
            logger.info(f"DRY RUN: Would move {source_obj} to {dest_obj}")
            return True
        
        # Make sure parent directory exists
        if not dest_obj.parent.exists():
            await create_directory(dest_obj.parent, dry_run=False)
        
        # Move the file
        shutil.move(str(source_obj), str(dest_obj))
        logger.info(f"Moved {source_obj} to {dest_obj}")
        
        return True
    
    except Exception as e:
        logger.exception(f"Error moving {source_obj} to {dest_obj}: {str(e)}")
        raise FileSystemError(f"Failed to move file: {str(e)}")


# --- Helper functions for backups and rollbacks ---

async def _backup_file(path: Path) -> Path:
    """
    Create a backup of a file for potential rollback.
    
    Args:
        path: The path of the file to back up.
        
    Returns:
        The path of the backup file.
    """
    try:
        _ensure_backup_dir()
        
        # Create a unique backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = BACKUP_DIR / backup_name
        
        # Copy the file to the backup location
        shutil.copy2(path, backup_path)
        logger.debug(f"Created backup of {path} at {backup_path}")
        
        return backup_path
    
    except Exception as e:
        logger.warning(f"Failed to create backup of {path}: {str(e)}")
        # Not raising an exception here as this is a non-critical operation
        return None


async def _backup_directory(path: Path) -> Path:
    """
    Create a backup of a directory for potential rollback.
    
    Args:
        path: The path of the directory to back up.
        
    Returns:
        The path of the backup directory.
    """
    try:
        _ensure_backup_dir()
        
        # Create a unique backup directory name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = BACKUP_DIR / backup_name
        
        # Copy the directory to the backup location
        shutil.copytree(path, backup_path)
        logger.debug(f"Created backup of directory {path} at {backup_path}")
        
        return backup_path
    
    except Exception as e:
        logger.warning(f"Failed to create backup of directory {path}: {str(e)}")
        # Not raising an exception here as this is a non-critical operation
        return None
