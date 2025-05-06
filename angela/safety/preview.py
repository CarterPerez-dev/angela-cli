"""
Preview generator for command execution.

This module generates previews of what commands will do before they are executed,
helping users make informed decisions about risky operations.
"""
import os
import re
import shlex
import glob
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from angela.execution.engine import execution_engine
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Commands that can be simulated with more specific previews
PREVIEWABLE_COMMANDS = {
    'mkdir': preview_mkdir,
    'touch': preview_touch,
    'rm': preview_rm,
    'cp': preview_cp,
    'mv': preview_mv,
    'ls': preview_ls,
    'cat': preview_cat,
    'grep': preview_grep,
    'find': preview_find,
}

async def generate_preview(command: str) -> Optional[str]:
    """
    Generate a preview of what a command will do.
    
    Args:
        command: The shell command to preview.
        
    Returns:
        A string containing the preview, or None if preview is not available.
    """
    try:
        # Parse the command
        tokens = shlex.split(command)
        if not tokens:
            return None
        
        base_cmd = tokens[0]
        
        # Check if we have a specific preview function for this command
        if base_cmd in PREVIEWABLE_COMMANDS:
            return await PREVIEWABLE_COMMANDS[base_cmd](command, tokens)
        
        # For other commands, try to use --dry-run or similar flags if available
        return await generic_preview(command)
    
    except Exception as e:
        logger.exception(f"Error generating preview for '{command}': {str(e)}")
        return f"Preview generation failed: {str(e)}"


async def generic_preview(command: str) -> Optional[str]:
    """
    Generate a generic preview for commands without specific implementations.
    Attempts to use --dry-run flags when available.
    
    Args:
        command: The shell command to preview.
        
    Returns:
        A string containing the preview, or None if preview is not available.
    """
    # List of commands that support --dry-run or similar
    dry_run_commands = {
        'rsync': '--dry-run',
        'apt': '--dry-run',
        'apt-get': '--dry-run',
        'dnf': '--dry-run',
        'yum': '--dry-run',
        'pacman': '--print',
    }
    
    tokens = shlex.split(command)
    base_cmd = tokens[0]
    
    if base_cmd in dry_run_commands:
        # Add the dry run flag
        dry_run_flag = dry_run_commands[base_cmd]
        
        # Check if the flag is already in the command
        if dry_run_flag not in command:
            modified_command = f"{command} {dry_run_flag}"
        else:
            modified_command = command
        
        # Execute the command with the dry run flag
        stdout, stderr, return_code = await execution_engine.execute_command(modified_command)
        
        if return_code == 0:
            return f"Dry run output:\n{stdout}"
        else:
            return f"Dry run failed with error:\n{stderr}"
    
    # For commands without dry run support, return a generic message
    return "Preview not available for this command type. Use --dry-run to simulate."


async def preview_mkdir(command: str, tokens: List[str]) -> str:
    """Generate a preview for mkdir command."""
    # Parse flags and paths
    paths = []
    recursive = '-p' in tokens or '--parents' in tokens
    
    for arg in tokens[1:]:
        if not arg.startswith('-'):
            paths.append(arg)
    
    result = []
    for path in paths:
        path_obj = Path(path)
        if path_obj.exists():
            result.append(f"⚠️ Path already exists: {path}")
        elif path_obj.parent.exists() or recursive:
            result.append(f"✓ Will create directory: {path}")
        else:
            result.append(f"❌ Parent directory does not exist: {path.parent}")
    
    if not result:
        return "No directories specified to create."
    
    return "\n".join(result)


async def preview_touch(command: str, tokens: List[str]) -> str:
    """Generate a preview for touch command."""
    # Parse flags and paths
    paths = []
    
    for arg in tokens[1:]:
        if not arg.startswith('-'):
            paths.append(arg)
    
    result = []
    for path in paths:
        path_obj = Path(path)
        if path_obj.exists():
            result.append(f"Will update timestamp: {path}")
        elif path_obj.parent.exists():
            result.append(f"Will create empty file: {path}")
        else:
            result.append(f"❌ Parent directory does not exist: {path_obj.parent}")
    
    if not result:
        return "No files specified to touch."
    
    return "\n".join(result)


async def preview_rm(command: str, tokens: List[str]) -> str:
    """Generate a preview for rm command."""
    # Parse flags and paths
    paths = []
    recursive = '-r' in tokens or '--recursive' in tokens or '-rf' in tokens
    force = '-f' in tokens or '--force' in tokens or '-rf' in tokens
    
    for arg in tokens[1:]:
        if not arg.startswith('-'):
            paths.append(arg)
    
    # Expand any glob patterns
    expanded_paths = []
    for path in paths:
        if '*' in path or '?' in path or '[' in path:
            # Use glob to expand wildcards
            expanded = glob.glob(path)
            if expanded:
                expanded_paths.extend(expanded)
            else:
                expanded_paths.append(f"{path} (no matches)")
        else:
            expanded_paths.append(path)
    
    result = []
    for path in expanded_paths:
        path_obj = Path(path)
        if not path_obj.exists():
            if force:
                continue  # With force flag, non-existent files are silently ignored
            else:
                result.append(f"❌ Not found: {path}")
        elif path_obj.is_dir() and not recursive:
            result.append(f"❌ Cannot remove directory without -r flag: {path}")
        elif path_obj.is_dir():
            file_count = sum(1 for _ in path_obj.glob('**/*'))
            result.append(f"⚠️ Will remove directory containing {file_count} files: {path}")
        else:
            result.append(f"Will remove file: {path}")
    
    if not result:
        return "No files specified to remove or all paths are invalid."
    
    return "\n".join(result)


async def preview_cp(command: str, tokens: List[str]) -> str:
    """Generate a preview for cp command."""
    # This is a simplified preview that doesn't handle all cp options
    
    # Need at least 3 tokens: cp source dest
    if len(tokens) < 3:
        return "Invalid cp command: missing source or destination"
    
    # Last argument is the destination
    destination = tokens[-1]
    # All arguments except the command and destination are sources
    sources = [arg for arg in tokens[1:-1] if not arg.startswith('-')]
    
    recursive = '-r' in tokens or '--recursive' in tokens
    
    result = []
    for source in sources:
        source_path = Path(source)
        
        if not source_path.exists():
            result.append(f"❌ Source does not exist: {source}")
            continue
        
        if source_path.is_dir() and not recursive:
            result.append(f"❌ Cannot copy directory without -r flag: {source}")
            continue
        
        # Determine the destination path
        dest_path = Path(destination)
        if len(sources) > 1 or dest_path.is_dir():
            # Multiple sources or destination is a directory
            if not dest_path.exists():
                if dest_path.name.endswith('/'):  # Explicitly specified as directory
                    result.append(f"Will create directory: {destination}")
                else:
                    result.append(f"Will copy {source} to {destination}")
            else:
                if dest_path.is_dir():
                    result.append(f"Will copy {source} to {destination}/{source_path.name}")
                else:
                    result.append(f"⚠️ Cannot copy multiple sources to a single file: {destination}")
        else:
            # Single source to destination
            if dest_path.exists() and dest_path.is_file():
                result.append(f"⚠️ Will overwrite: {destination}")
            else:
                result.append(f"Will copy {source} to {destination}")
    
    if not result:
        return "No files specified to copy."
    
    return "\n".join(result)


async def preview_mv(command: str, tokens: List[str]) -> str:
    """Generate a preview for mv command."""
    # This is a simplified preview that doesn't handle all mv options
    
    # Need at least 3 tokens: mv source dest
    if len(tokens) < 3:
        return "Invalid mv command: missing source or destination"
    
    # Last argument is the destination
    destination = tokens[-1]
    # All arguments except the command and destination are sources
    sources = [arg for arg in tokens[1:-1] if not arg.startswith('-')]
    
    result = []
    for source in sources:
        source_path = Path(source)
        
        if not source_path.exists():
            result.append(f"❌ Source does not exist: {source}")
            continue
        
        # Determine the destination path
        dest_path = Path(destination)
        if len(sources) > 1 or dest_path.is_dir():
            # Multiple sources or destination is a directory
            if not dest_path.exists():
                if dest_path.name.endswith('/'):  # Explicitly specified as directory
                    result.append(f"Will create directory: {destination}")
                else:
                    result.append(f"Will move {source} to {destination}")
            else:
                if dest_path.is_dir():
                    result.append(f"Will move {source} to {destination}/{source_path.name}")
                else:
                    result.append(f"⚠️ Cannot move multiple sources to a single file: {destination}")
        else:
            # Single source to destination
            if dest_path.exists() and dest_path.is_file():
                result.append(f"⚠️ Will overwrite: {destination}")
            else:
                result.append(f"Will move {source} to {destination}")
    
    if not result:
        return "No files specified to move."
    
    return "\n".join(result)


async def preview_ls(command: str, tokens: List[str]) -> str:
    """Generate a preview for ls command."""
    # Extract the paths from the command
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith('-'):
            paths.append(arg)
    
    # If no paths specified, use current directory
    if not paths:
        paths = ['.']
    
    result = []
    for path in paths:
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                result.append(f"❌ Path does not exist: {path}")
                continue
            
            if path_obj.is_dir():
                # Just count files rather than listing them all
                file_count = sum(1 for _ in path_obj.iterdir())
                result.append(f"Will list directory: {path} (contains {file_count} entries)")
            else:
                result.append(f"Will show file information: {path}")
        except Exception as e:
            result.append(f"Error analyzing {path}: {str(e)}")
    
    return "\n".join(result)


async def preview_cat(command: str, tokens: List[str]) -> str:
    """Generate a preview for cat command."""
    # Extract the paths from the command
    paths = []
    for arg in tokens[1:]:
        if not arg.startswith('-'):
            paths.append(arg)
    
    if not paths:
        return "No files specified to display."
    
    result = []
    for path in paths:
        path_obj = Path(path)
        if not path_obj.exists():
            result.append(f"❌ File does not exist: {path}")
        elif path_obj.is_dir():
            result.append(f"❌ Cannot display directory content: {path}")
        else:
            # Get file size
            size = path_obj.stat().st_size
            size_str = f"{size} bytes"
            if size > 1024:
                size_str = f"{size/1024:.1f} KB"
            if size > 1024 * 1024:
                size_str = f"{size/(1024*1024):.1f} MB"
            
            # Try to determine if it's a text file
            try:
                with open(path_obj, 'rb') as f:
                    is_text = True
                    for block in iter(lambda: f.read(1024), b''):
                        if b'\0' in block:
                            is_text = False
                            break
                
                if is_text:
                    # Count lines
                    with open(path_obj, 'r', errors='replace') as f:
                        line_count = sum(1 for _ in f)
                    result.append(f"Will display text file: {path} ({size_str}, {line_count} lines)")
                else:
                    result.append(f"⚠️ Will display binary file: {path} ({size_str})")
            except Exception as e:
                result.append(f"Error analyzing {path}: {str(e)}")
    
    return "\n".join(result)


async def preview_grep(command: str, tokens: List[str]) -> str:
    """Generate a preview for grep command."""
    # This is a simplified preview that doesn't handle all grep options
    
    # Need at least 3 tokens: grep pattern file
    if len(tokens) < 3:
        return "Invalid grep command: missing pattern or file"
    
    pattern = None
    files = []
    recursive = '-r' in tokens or '--recursive' in tokens
    
    # Simple parsing to extract pattern and files
    pattern_found = False
    for arg in tokens[1:]:
        if arg.startswith('-'):
            continue
        
        if not pattern_found:
            pattern = arg
            pattern_found = True
        else:
            files.append(arg)
    
    if not pattern:
        return "No pattern specified for grep."
    
    if not files:
        if recursive:
            files = ['.']
        else:
            return "No files specified for grep."
    
    result = []
    for file_path in files:
        path_obj = Path(file_path)
        if not path_obj.exists():
            result.append(f"❌ Path does not exist: {file_path}")
        elif path_obj.is_dir() and not recursive:
            result.append(f"❌ Cannot grep directory without -r flag: {file_path}")
        elif path_obj.is_dir() and recursive:
            # Count files in directory
            file_count = sum(1 for _ in path_obj.glob('**/*') if Path(_).is_file())
            result.append(f"Will search for '{pattern}' in directory: {file_path} "
                         f"(contains {file_count} files)")
        else:
            # Try to count occurrences in file
            try:
                with open(path_obj, 'r', errors='replace') as f:
                    content = f.read()
                    count = len(re.findall(pattern, content))
                    result.append(f"Will search for '{pattern}' in {file_path} "
                                 f"(potentially {count} matches)")
            except Exception as e:
                result.append(f"Will search in {file_path}, but preview failed: {str(e)}")
    
    return "\n".join(result)


async def preview_find(command: str, tokens: List[str]) -> str:
    """Generate a preview for find command."""
    # Extract directories to search from the command
    # This is a simple implementation that doesn't handle all find options
    
    dirs = []
    name_pattern = None
    type_filter = None
    
    # Find the directories (arguments before the first option)
    for i, arg in enumerate(tokens[1:], 1):
        if arg.startswith('-'):
            break
        dirs.append(arg)
    
    # If no directories specified, use current directory
    if not dirs:
        dirs = ['.']
    
    # Try to extract name pattern if present
    for i, arg in enumerate(tokens):
        if arg == '-name' and i + 1 < len(tokens):
            name_pattern = tokens[i + 1]
        elif arg == '-type' and i + 1 < len(tokens):
            type_filter = tokens[i + 1]
    
    result = []
    for directory in dirs:
        dir_path = Path(directory)
        if not dir_path.exists():
            result.append(f"❌ Directory does not exist: {directory}")
            continue
        
        if not dir_path.is_dir():
            result.append(f"❌ Not a directory: {directory}")
            continue
        
        # Count files and directories in the search path
        file_count = sum(1 for _ in dir_path.glob('**/*') if Path(_).is_file())
        dir_count = sum(1 for _ in dir_path.glob('**/*') if Path(_).is_dir())
        
        search_desc = f"Will search in: {directory} ({file_count} files, {dir_count} directories)"
        
        if name_pattern:
            search_desc += f"\nLooking for files matching: {name_pattern}"
        
        if type_filter:
            type_desc = {'f': 'files', 'd': 'directories', 'l': 'symbolic links'}.get(type_filter, type_filter)
            search_desc += f"\nFiltering by type: {type_desc}"
        
        result.append(search_desc)
    
    return "\n".join(result)
