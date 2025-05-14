# angela/safety/preview.py
"""
Preview generator for command execution.

This module generates previews of what commands will do before they are executed,
helping users make informed decisions about potentially risky operations.
It provides extensive coverage of Linux commands, including common utilities
and specialized tools from packages like Kali Linux.
"""
import os
import re
import shlex
import glob
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable
import platform
import asyncio
import json

from angela.api.execution import get_execution_engine
from angela.utils.logging import get_logger

logger = get_logger(__name__)


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
    recursive = any(flag in tokens for flag in ['-r', '--recursive', '-rf', '-fr', '-R'])
    force = any(flag in tokens for flag in ['-f', '--force', '-rf', '-fr'])
    
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
            try:
                file_count = sum(1 for _ in path_obj.glob('**/*'))
                result.append(f"⚠️ Will remove directory containing {file_count} files: {path}")
            except PermissionError:
                result.append(f"⚠️ Will remove directory (permission denied for counting files): {path}")
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
    
    recursive = any(flag in tokens for flag in ['-r', '--recursive', '-a', '--archive', '-R'])
    force = any(flag in tokens for flag in ['-f', '--force'])
    
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
                    dest_file = dest_path / source_path.name
                    if dest_file.exists() and not force:
                        result.append(f"⚠️ Will overwrite existing file: {dest_file}")
                    else:
                        result.append(f"Will copy {source} to {destination}/{source_path.name}")
                else:
                    result.append(f"⚠️ Cannot copy multiple sources to a single file: {destination}")
        else:
            # Single source to destination
            if dest_path.exists() and dest_path.is_file():
                if force:
                    result.append(f"Will force overwrite: {destination}")
                else:
                    result.append(f"⚠️ Will overwrite: {destination}")
            else:
                if source_path.is_dir():
                    file_count = sum(1 for _ in source_path.glob('**/*'))
                    result.append(f"Will copy directory containing {file_count} files to {destination}")
                else:
                    result.append(f"Will copy {source} to {destination}")
    
    if not result:
        return "No files specified to copy."
    
    return "\n".join(result)


async def preview_mv(command: str, tokens: List[str]) -> str:
    """Generate a preview for mv command."""
    # Need at least 3 tokens: mv source dest
    if len(tokens) < 3:
        return "Invalid mv command: missing source or destination"
    
    # Last argument is the destination
    destination = tokens[-1]
    # All arguments except the command and destination are sources
    sources = [arg for arg in tokens[1:-1] if not arg.startswith('-')]
    
    force = any(flag in tokens for flag in ['-f', '--force'])
    
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
                    dest_file = dest_path / source_path.name
                    if dest_file.exists() and not force:
                        result.append(f"⚠️ Will overwrite existing file: {dest_file}")
                    else:
                        result.append(f"Will move {source} to {destination}/{source_path.name}")
                else:
                    result.append(f"⚠️ Cannot move multiple sources to a single file: {destination}")
        else:
            # Single source to destination
            if dest_path.exists() and dest_path.is_file():
                if force:
                    result.append(f"Will force overwrite: {destination}")
                else:
                    result.append(f"⚠️ Will overwrite: {destination}")
            else:
                if source_path.is_dir():
                    file_count = sum(1 for _ in source_path.glob('**/*'))
                    result.append(f"Will move directory containing {file_count} files to {destination}")
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
                try:
                    file_count = sum(1 for _ in path_obj.iterdir())
                    result.append(f"Will list directory: {path} (contains {file_count} entries)")
                except PermissionError:
                    result.append(f"⚠️ Permission denied for directory: {path}")
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
            try:
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
            except PermissionError:
                result.append(f"⚠️ Permission denied for file: {path}")
    
    return "\n".join(result)


async def preview_grep(command: str, tokens: List[str]) -> str:
    """Generate a preview for grep command."""
    # This is a simplified preview that doesn't handle all grep options
    
    # Need at least 3 tokens: grep pattern file
    if len(tokens) < 3:
        return "Invalid grep command: missing pattern or file"
    
    pattern = None
    files = []
    recursive = any(flag in tokens for flag in ['-r', '--recursive', '-R', '--dereference-recursive'])
    
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
            try:
                file_count = sum(1 for _ in path_obj.glob('**/*') if Path(_).is_file())
                result.append(f"Will search for '{pattern}' in directory: {file_path} "
                             f"(contains {file_count} files)")
            except PermissionError:
                result.append(f"⚠️ Permission denied for some files in: {file_path}")
        else:
            # Try to count occurrences in file
            try:
                with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
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
        if arg in ['-name', '-iname'] and i + 1 < len(tokens):
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
        try:
            file_count = sum(1 for _ in dir_path.glob('**/*') if Path(_).is_file())
            dir_count = sum(1 for _ in dir_path.glob('**/*') if Path(_).is_dir())
            
            search_desc = f"Will search in: {directory} ({file_count} files, {dir_count} directories)"
            
            if name_pattern:
                search_desc += f"\nLooking for files matching: {name_pattern}"
            
            if type_filter:
                type_desc = {'f': 'files', 'd': 'directories', 'l': 'symbolic links'}.get(type_filter, type_filter)
                search_desc += f"\nFiltering by type: {type_desc}"
            
            result.append(search_desc)
        except PermissionError:
            result.append(f"⚠️ Permission denied for some files in: {directory}")
    
    return "\n".join(result)


async def preview_chmod(command: str, tokens: List[str]) -> str:
    """Generate a preview for chmod command."""
    # Need at least 3 tokens: chmod mode file
    if len(tokens) < 3:
        return "Invalid chmod command: missing mode or file"
    
    mode = None
    files = []
    recursive = any(flag in tokens for flag in ['-R', '--recursive', '-r'])
    
    # Get mode and files
    for arg in tokens[1:]:
        if arg.startswith('-'):
            continue
        
        if not mode:
            mode = arg
        else:
            files.append(arg)
    
    if not mode:
        return "No mode specified for chmod."
    
    if not files:
        return "No files specified for chmod."
    
    # Human readable mode description
    mode_desc = mode
    try:
        if mode.isdigit() and len(mode) <= 4:
            # Numeric mode
            if len(mode) == 3:  # 644
                owner = int(mode[0])
                group = int(mode[1])
                others = int(mode[2])
                readable = []
                
                if owner >= 4:
                    readable.append("Owner: read")
                    owner -= 4
                if owner >= 2:
                    readable.append("Owner: write")
                    owner -= 2
                if owner >= 1:
                    readable.append("Owner: execute")
                
                if group >= 4:
                    readable.append("Group: read")
                    group -= 4
                if group >= 2:
                    readable.append("Group: write")
                    group -= 2
                if group >= 1:
                    readable.append("Group: execute")
                
                if others >= 4:
                    readable.append("Others: read")
                    others -= 4
                if others >= 2:
                    readable.append("Others: write")
                    others -= 2
                if others >= 1:
                    readable.append("Others: execute")
                
                mode_desc = f"{mode} ({', '.join(readable)})"
            elif len(mode) == 4:  # 0644
                # Skip the first digit (special flags)
                owner = int(mode[1])
                group = int(mode[2])
                others = int(mode[3])
                readable = []
                
                if owner >= 4:
                    readable.append("Owner: read")
                    owner -= 4
                if owner >= 2:
                    readable.append("Owner: write")
                    owner -= 2
                if owner >= 1:
                    readable.append("Owner: execute")
                
                if group >= 4:
                    readable.append("Group: read")
                    group -= 4
                if group >= 2:
                    readable.append("Group: write")
                    group -= 2
                if group >= 1:
                    readable.append("Group: execute")
                
                if others >= 4:
                    readable.append("Others: read")
                    others -= 4
                if others >= 2:
                    readable.append("Others: write")
                    others -= 2
                if others >= 1:
                    readable.append("Others: execute")
                
                mode_desc = f"{mode} ({', '.join(readable)})"
    except:
        # Just use the mode as provided if we can't parse it
        pass
    
    result = []
    for file_path in files:
        path_obj = Path(file_path)
        if not path_obj.exists():
            result.append(f"❌ Path does not exist: {file_path}")
        elif path_obj.is_dir() and recursive:
            try:
                file_count = sum(1 for _ in path_obj.glob('**/*'))
                result.append(f"Will change permissions to {mode_desc} on directory: {file_path} "
                             f"and its contents ({file_count} items)")
            except PermissionError:
                result.append(f"⚠️ Permission denied for some files in: {file_path}")
        elif path_obj.is_dir() and not recursive:
            result.append(f"Will change permissions to {mode_desc} on directory: {file_path} (not recursive)")
        else:
            result.append(f"Will change permissions to {mode_desc} on file: {file_path}")
    
    return "\n".join(result)


async def preview_chown(command: str, tokens: List[str]) -> str:
    """Generate a preview for chown command."""
    # Need at least 3 tokens: chown owner file
    if len(tokens) < 3:
        return "Invalid chown command: missing owner or file"
    
    owner = None
    files = []
    recursive = any(flag in tokens for flag in ['-R', '--recursive', '-r'])
    
    # Get owner and files
    for arg in tokens[1:]:
        if arg.startswith('-'):
            continue
        
        if not owner:
            owner = arg
        else:
            files.append(arg)
    
    if not owner:
        return "No owner specified for chown."
    
    if not files:
        return "No files specified for chown."
    
    result = []
    for file_path in files:
        path_obj = Path(file_path)
        if not path_obj.exists():
            result.append(f"❌ Path does not exist: {file_path}")
        elif path_obj.is_dir() and recursive:
            try:
                file_count = sum(1 for _ in path_obj.glob('**/*'))
                result.append(f"Will change ownership to {owner} on directory: {file_path} "
                             f"and its contents ({file_count} items)")
            except PermissionError:
                result.append(f"⚠️ Permission denied for some files in: {file_path}")
        elif path_obj.is_dir() and not recursive:
            result.append(f"Will change ownership to {owner} on directory: {file_path} (not recursive)")
        else:
            result.append(f"Will change ownership to {owner} on file: {file_path}")
    
    return "\n".join(result)


async def preview_apt(command: str, tokens: List[str]) -> str:
    """Generate a preview for apt/apt-get commands."""
    if len(tokens) < 2:
        return "Invalid apt command: missing subcommand"
    
    subcommand = tokens[1]
    packages = []
    
    # Extract packages (arguments after subcommand that don't start with -)
    for arg in tokens[2:]:
        if not arg.startswith('-'):
            packages.append(arg)
    
    if subcommand in ["install", "remove", "purge"]:
        if not packages:
            return f"No packages specified for apt {subcommand}"
        
        action = {
            "install": "install",
            "remove": "remove",
            "purge": "purge (remove including configuration)"
        }.get(subcommand, subcommand)
        
        return f"Will {action} the following packages: {', '.join(packages)}"
    
    elif subcommand in ["update"]:
        return "Will update package index from all configured sources"
    
    elif subcommand in ["upgrade", "dist-upgrade", "full-upgrade"]:
        if subcommand == "dist-upgrade" or subcommand == "full-upgrade":
            return "Will perform a smart upgrade that may add or remove packages as needed"
        else:
            return "Will upgrade all installed packages to their latest versions"
    
    elif subcommand in ["autoremove"]:
        return "Will remove automatically installed packages that are no longer required"
    
    elif subcommand in ["search"]:
        if not packages:
            return "No search terms specified"
        return f"Will search for packages matching: {', '.join(packages)}"
    
    else:
        return f"Will execute apt {subcommand} command"


async def preview_systemctl(command: str, tokens: List[str]) -> str:
    """Generate a preview for systemctl command."""
    if len(tokens) < 2:
        return "Invalid systemctl command: missing subcommand"
    
    subcommand = tokens[1]
    units = []
    
    # Extract units (arguments after subcommand that don't start with -)
    for arg in tokens[2:]:
        if not arg.startswith('-'):
            units.append(arg)
    
    if subcommand in ["start", "stop", "restart", "reload", "enable", "disable", "mask", "unmask"]:
        if not units:
            return f"No units specified for systemctl {subcommand}"
        
        action = {
            "start": "start",
            "stop": "stop",
            "restart": "restart",
            "reload": "reload",
            "enable": "enable (auto-start at boot)",
            "disable": "disable (prevent auto-start at boot)",
            "mask": "mask (completely prevent from starting)",
            "unmask": "unmask (allow starting)"
        }.get(subcommand, subcommand)
        
        return f"Will {action} the following service units: {', '.join(units)}"
    
    elif subcommand in ["status"]:
        if not units:
            return "Will show system status"
        return f"Will show status of the following service units: {', '.join(units)}"
    
    elif subcommand in ["list-units", "list-sockets", "list-timers"]:
        list_type = subcommand.split('-')[1]
        return f"Will list all active {list_type}"
    
    else:
        return f"Will execute systemctl {subcommand} command"


async def preview_docker(command: str, tokens: List[str]) -> str:
    """Generate a preview for docker command."""
    if len(tokens) < 2:
        return "Invalid docker command: missing subcommand"
    
    subcommand = tokens[1]
    args = []
    
    # Extract args (arguments after subcommand that don't start with -)
    for arg in tokens[2:]:
        if not arg.startswith('-'):
            args.append(arg)
    
    if subcommand in ["run"]:
        image = None
        for arg in tokens[2:]:
            if not arg.startswith('-'):
                image = arg
                break
        
        if not image:
            return "No image specified for docker run"
        
        return f"Will run a new container from image: {image}"
    
    elif subcommand in ["start", "stop", "restart", "kill"]:
        if not args:
            return f"No containers specified for docker {subcommand}"
        
        action = {
            "start": "start",
            "stop": "stop",
            "restart": "restart",
            "kill": "kill (force stop)"
        }.get(subcommand, subcommand)
        
        return f"Will {action} the following containers: {', '.join(args)}"
    
    elif subcommand in ["rm"]:
        if not args:
            return "No containers specified for docker rm"
        return f"Will remove the following containers: {', '.join(args)}"
    
    elif subcommand in ["rmi"]:
        if not args:
            return "No images specified for docker rmi"
        return f"Will remove the following images: {', '.join(args)}"
    
    elif subcommand in ["build"]:
        context = "."  # Default context is current directory
        for i, arg in enumerate(tokens[2:], 2):
            if not arg.startswith('-'):
                context = arg
                break
        
        return f"Will build a Docker image from context: {context}"
    
    elif subcommand in ["ps"]:
        return "Will list running containers"
    
    elif subcommand in ["images"]:
        return "Will list available Docker images"
    
    elif subcommand in ["logs"]:
        if not args:
            return "No container specified for docker logs"
        return f"Will show logs for container: {args[0]}"
    
    elif subcommand in ["pull"]:
        if not args:
            return "No image specified for docker pull"
        return f"Will pull image: {args[0]}"
    
    elif subcommand in ["exec"]:
        if len(args) < 2:
            return "Missing container or command for docker exec"
        return f"Will execute command in container: {args[0]}"
    
    else:
        return f"Will execute docker {subcommand} command"


async def preview_git(command: str, tokens: List[str]) -> str:
    """Generate a preview for git command."""
    if len(tokens) < 2:
        return "Invalid git command: missing subcommand"
    
    subcommand = tokens[1]
    args = []
    
    # Extract args (arguments after subcommand that don't start with -)
    for arg in tokens[2:]:
        if not arg.startswith('-'):
            args.append(arg)
    
    if subcommand in ["clone"]:
        if not args:
            return "No repository URL specified for git clone"
        
        repo_url = args[0]
        target_dir = args[1] if len(args) > 1 else repo_url.split('/')[-1].replace('.git', '')
        
        return f"Will clone repository from {repo_url} to {target_dir}"
    
    elif subcommand in ["pull", "fetch"]:
        remote = args[0] if args else "origin"
        branch = args[1] if len(args) > 1 else "current branch"
        
        action = "pull (fetch + merge)" if subcommand == "pull" else "fetch"
        
        return f"Will {action} from remote {remote}, branch {branch}"
    
    elif subcommand in ["push"]:
        remote = args[0] if args else "origin"
        branch = args[1] if len(args) > 1 else "current branch"
        
        return f"Will push to remote {remote}, branch {branch}"
    
    elif subcommand in ["add"]:
        if not args:
            return "No files specified for git add"
        
        files = args
        return f"Will stage the following files for commit: {', '.join(files)}"
    
    elif subcommand in ["commit"]:
        message = ""
        for i, arg in enumerate(tokens[2:], 2):
            if arg in ["-m", "--message"] and i + 1 < len(tokens):
                message = tokens[i + 1]
                break
        
        return f"Will commit staged changes" + (f" with message: '{message}'" if message else "")
    
    elif subcommand in ["branch"]:
        if not args:
            return "Will list branches"
        
        branch_name = args[0]
        return f"Will create branch: {branch_name}"
    
    elif subcommand in ["checkout"]:
        if not args:
            return "No branch or files specified for git checkout"
        
        target = args[0]
        
        if "-b" in tokens or "--branch" in tokens:
            return f"Will create and switch to new branch: {target}"
        else:
            return f"Will switch to branch/commit: {target}"
    
    elif subcommand in ["merge"]:
        if not args:
            return "No branch specified for git merge"
        
        branch = args[0]
        return f"Will merge branch {branch} into current branch"
    
    elif subcommand in ["reset"]:
        target = args[0] if args else "HEAD"
        
        if "--hard" in tokens:
            return f"⚠️ Will reset working tree and index to {target} (discarding all uncommitted changes)"
        elif "--soft" in tokens:
            return f"Will reset HEAD to {target} (keeping uncommitted changes)"
        else:
            return f"Will reset index to {target} (keeping working tree changes)"
    
    elif subcommand in ["status"]:
        return "Will show working tree status"
    
    elif subcommand in ["log"]:
        return "Will show commit logs"
    
    else:
        return f"Will execute git {subcommand} command"


async def preview_ssh(command: str, tokens: List[str]) -> str:
    """Generate a preview for ssh command."""
    if len(tokens) < 2:
        return "Invalid ssh command: missing host"
    
    # Extract host and command
    host = None
    remote_command = None
    
    port = None
    identity_file = None
    forwarding = []
    
    i = 1
    while i < len(tokens):
        if tokens[i] in ["-p", "-P"] and i + 1 < len(tokens):
            port = tokens[i + 1]
            i += 2
        elif tokens[i] in ["-i"] and i + 1 < len(tokens):
            identity_file = tokens[i + 1]
            i += 2
        elif tokens[i] in ["-L", "-R", "-D"] and i + 1 < len(tokens):
            forwarding.append(f"{tokens[i]} {tokens[i + 1]}")
            i += 2
        elif tokens[i].startswith("-"):
            # Skip other options
            i += 1
        else:
            # First non-option argument is the host
            host = tokens[i]
            
            # Everything after the host is the command
            if i + 1 < len(tokens):
                remote_command = " ".join(tokens[i + 1:])
            break
    
    result = []
    result.append(f"Will connect to SSH server: {host}")
    
    if port:
        result.append(f"Using port: {port}")
    
    if identity_file:
        result.append(f"Using identity file: {identity_file}")
    
    if forwarding:
        for f in forwarding:
            if f.startswith("-L"):
                result.append(f"Setting up local port forwarding: {f[3:]}")
            elif f.startswith("-R"):
                result.append(f"Setting up remote port forwarding: {f[3:]}")
            elif f.startswith("-D"):
                result.append(f"Setting up dynamic port forwarding: {f[3:]}")
    
    if remote_command:
        result.append(f"Will execute remote command: {remote_command}")
    else:
        result.append("Will open an interactive SSH session")
    
    return "\n".join(result)


async def preview_ping(command: str, tokens: List[str]) -> str:
    """Generate a preview for ping command."""
    if len(tokens) < 2:
        return "Invalid ping command: missing host"
    
    host = None
    count = None
    
    i = 1
    while i < len(tokens):
        if tokens[i] in ["-c"] and i + 1 < len(tokens):
            count = tokens[i + 1]
            i += 2
        elif tokens[i].startswith("-"):
            # Skip other options
            i += 1
        else:
            # First non-option argument is the host
            host = tokens[i]
            break
    
    if not host:
        return "No host specified for ping"
    
    if count:
        return f"Will send {count} ICMP echo requests to {host}"
    else:
        return f"Will continuously ping {host} (until interrupted)"


async def preview_wget(command: str, tokens: List[str]) -> str:
    """Generate a preview for wget command."""
    if len(tokens) < 2:
        return "Invalid wget command: missing URL"
    
    url = None
    output_file = None
    
    i = 1
    while i < len(tokens):
        if tokens[i] in ["-O", "--output-document"] and i + 1 < len(tokens):
            output_file = tokens[i + 1]
            i += 2
        elif tokens[i].startswith("-"):
            # Skip other options
            i += 1
        else:
            # First non-option argument is the URL
            url = tokens[i]
            break
    
    if not url:
        return "No URL specified for wget"
    
    if output_file:
        return f"Will download {url} to {output_file}"
    else:
        # Extract filename from URL
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path = parsed_url.path
            filename = path.split('/')[-1]
            if not filename:
                filename = "index.html"
            
            return f"Will download {url} to {filename}"
        except:
            return f"Will download {url}"


async def preview_curl(command: str, tokens: List[str]) -> str:
    """Generate a preview for curl command."""
    if len(tokens) < 2:
        return "Invalid curl command: missing URL"
    
    url = None
    output_file = None
    
    i = 1
    while i < len(tokens):
        if tokens[i] in ["-o", "--output"] and i + 1 < len(tokens):
            output_file = tokens[i + 1]
            i += 2
        elif tokens[i].startswith("-"):
            # Skip other options
            i += 1
        else:
            # First non-option argument is the URL
            url = tokens[i]
            break
    
    if not url:
        return "No URL specified for curl"
    
    if output_file:
        return f"Will download {url} to {output_file}"
    else:
        return f"Will fetch content from {url} and display it on stdout"


async def preview_tar(command: str, tokens: List[str]) -> str:
    """Generate a preview for tar command."""
    if len(tokens) < 2:
        return "Invalid tar command: missing operation"
    
    operation = None
    file = None
    targets = []
    
    # Check for operation flags
    for arg in tokens[1:]:
        if arg.startswith("-"):
            if 'c' in arg:
                operation = "create"
            elif 'x' in arg:
                operation = "extract"
            elif 't' in arg:
                operation = "list"
            
            if 'f' in arg and len(tokens) > tokens.index(arg) + 1:
                file = tokens[tokens.index(arg) + 1]
        elif not file:
            # If we've seen -f but no filename yet, this is the filename
            file = arg
        else:
            # Otherwise it's a target file/directory
            targets.append(arg)
    
    if not operation:
        return "No operation specified for tar (create, extract, or list)"
    
    if not file:
        return "No archive file specified for tar"
    
    if operation == "create":
        if not targets:
            return "No files/directories specified for tar archive creation"
        
        return f"Will create tar archive {file} containing: {', '.join(targets)}"
    
    elif operation == "extract":
        if not Path(file).exists():
            return f"❌ Archive file does not exist: {file}"
        
        extract_dir = targets[0] if targets else "current directory"
        return f"Will extract tar archive {file} to {extract_dir}"
    
    elif operation == "list":
        if not Path(file).exists():
            return f"❌ Archive file does not exist: {file}"
        
        return f"Will list contents of tar archive {file}"
    
    return f"Will perform tar {operation} operation on {file}"


async def preview_zip(command: str, tokens: List[str]) -> str:
    """Generate a preview for zip command."""
    if len(tokens) < 3:
        return "Invalid zip command: missing zip file or files to zip"
    
    zip_file = tokens[1]
    files = tokens[2:]
    
    if zip_file.endswith(".zip"):
        if not files:
            return "No files specified for zip"
        
        return f"Will create zip archive {zip_file} containing: {', '.join(files)}"
    else:
        # Swap if arguments are in the wrong order
        if any(f.endswith(".zip") for f in files):
            for i, f in enumerate(files):
                if f.endswith(".zip"):
                    zip_file, files[i] = files[i], zip_file
                    break
            
            return f"Will create zip archive {zip_file} containing: {', '.join(files)}"
        else:
            return f"Will create zip archive {zip_file}.zip containing: {', '.join(files)}"


async def preview_unzip(command: str, tokens: List[str]) -> str:
    """Generate a preview for unzip command."""
    if len(tokens) < 2:
        return "Invalid unzip command: missing zip file"
    
    zip_file = None
    extract_dir = None
    
    i = 1
    while i < len(tokens):
        if tokens[i] in ["-d"] and i + 1 < len(tokens):
            extract_dir = tokens[i + 1]
            i += 2
        elif tokens[i].startswith("-"):
            # Skip other options
            i += 1
        else:
            # First non-option argument is the zip file
            zip_file = tokens[i]
            break
    
    if not zip_file:
        return "No zip file specified for unzip"
    
    if not Path(zip_file).exists():
        return f"❌ Zip file does not exist: {zip_file}"
    
    if extract_dir:
        return f"Will extract zip archive {zip_file} to {extract_dir}"
    else:
        return f"Will extract zip archive {zip_file} to current directory"


async def preview_python(command: str, tokens: List[str]) -> str:
    """Generate a preview for python command."""
    if len(tokens) < 2:
        return "Will start an interactive Python interpreter"
    
    script = None
    script_args = []
    
    i = 1
    while i < len(tokens):
        if tokens[i] in ["-c"] and i + 1 < len(tokens):
            return f"Will execute Python code: {tokens[i + 1]}"
        elif tokens[i] in ["-m"] and i + 1 < len(tokens):
            return f"Will run Python module: {tokens[i + 1]}"
        elif tokens[i].startswith("-"):
            # Skip other options
            i += 1
        else:
            # First non-option argument is the script
            script = tokens[i]
            script_args = tokens[i + 1:]
            break
    
    if not script:
        return "Will start an interactive Python interpreter"
    
    if not Path(script).exists():
        return f"❌ Python script does not exist: {script}"
    
    return f"Will execute Python script: {script}" + (f" with arguments: {' '.join(script_args)}" if script_args else "")


async def preview_pip(command: str, tokens: List[str]) -> str:
    """Generate a preview for pip command."""
    if len(tokens) < 2:
        return "Invalid pip command: missing subcommand"
    
    subcommand = tokens[1]
    packages = []
    
    # Extract packages (arguments after subcommand that don't start with -)
    for arg in tokens[2:]:
        if not arg.startswith('-'):
            packages.append(arg)
    
    if subcommand in ["install"]:
        if not packages:
            return "No packages specified for pip install"
        
        return f"Will install Python packages: {', '.join(packages)}"
    
    elif subcommand in ["uninstall"]:
        if not packages:
            return "No packages specified for pip uninstall"
        
        return f"Will uninstall Python packages: {', '.join(packages)}"
    
    elif subcommand in ["list"]:
        return "Will list installed Python packages"
    
    elif subcommand in ["show"]:
        if not packages:
            return "No packages specified for pip show"
        
        return f"Will show information about Python packages: {', '.join(packages)}"
    
    elif subcommand in ["search"]:
        if not packages:
            return "No search terms specified for pip search"
        
        return f"Will search for Python packages matching: {', '.join(packages)}"
    
    else:
        return f"Will execute pip {subcommand} command"


async def preview_ifconfig(command: str, tokens: List[str]) -> str:
    """Generate a preview for ifconfig command."""
    if len(tokens) == 1:
        return "Will display network interface configuration for all interfaces"
    
    interface = tokens[1]
    
    if len(tokens) == 2:
        return f"Will display network interface configuration for {interface}"
    
    # Check for 'up' or 'down' action
    if "up" in tokens:
        return f"Will bring network interface {interface} up"
    elif "down" in tokens:
        return f"Will bring network interface {interface} down"
    
    # Check for IP address configuration
    has_ip = False
    for i, token in enumerate(tokens):
        if token in ["inet", "addr"]:
            if i + 1 < len(tokens):
                ip_addr = tokens[i + 1]
                has_ip = True
                return f"Will configure network interface {interface} with IP address {ip_addr}"
    
    return f"Will modify network interface {interface} configuration"


async def preview_ip(command: str, tokens: List[str]) -> str:
    """Generate a preview for ip command."""
    if len(tokens) < 2:
        return "Invalid ip command: missing subcommand"
    
    subcommand = tokens[1]
    
    if subcommand in ["addr", "address"]:
        if len(tokens) < 3:
            return "Will display all IP addresses on all interfaces"
        
        action = tokens[2]
        
        if action in ["show", "list", "ls"]:
            if len(tokens) > 3:
                interface = tokens[3]
                return f"Will display IP addresses for interface {interface}"
            else:
                return "Will display all IP addresses on all interfaces"
        
        elif action in ["add"]:
            if len(tokens) < 5:
                return "Invalid ip addr add command: missing IP address or interface"
            
            ip_addr = tokens[3]
            interface = tokens[5] if len(tokens) > 5 and tokens[4] == "dev" else tokens[4]
            
            return f"Will add IP address {ip_addr} to interface {interface}"
        
        elif action in ["del", "delete"]:
            if len(tokens) < 5:
                return "Invalid ip addr del command: missing IP address or interface"
            
            ip_addr = tokens[3]
            interface = tokens[5] if len(tokens) > 5 and tokens[4] == "dev" else tokens[4]
            
            return f"Will remove IP address {ip_addr} from interface {interface}"
    
    elif subcommand in ["link"]:
        if len(tokens) < 3:
            return "Will display all network interfaces"
        
        action = tokens[2]
        
        if action in ["show", "list", "ls"]:
            if len(tokens) > 3:
                interface = tokens[3]
                return f"Will display information for interface {interface}"
            else:
                return "Will display all network interfaces"
        
        elif action in ["set"]:
            if len(tokens) < 4:
                return "Invalid ip link set command: missing interface"
            
            interface = tokens[3]
            
            if "up" in tokens:
                return f"Will bring network interface {interface} up"
            elif "down" in tokens:
                return f"Will bring network interface {interface} down"
            else:
                return f"Will modify network interface {interface} configuration"
    
    elif subcommand in ["route"]:
        if len(tokens) < 3:
            return "Will display routing table"
        
        action = tokens[2]
        
        if action in ["show", "list", "ls"]:
            return "Will display routing table"
        
        elif action in ["add"]:
            return "Will add a new route to the routing table"
        
        elif action in ["del", "delete"]:
            return "Will delete a route from the routing table"
    
    return f"Will execute ip {subcommand} command"


async def preview_nmap(command: str, tokens: List[str]) -> str:
    """Generate a preview for nmap command."""
    if len(tokens) < 2:
        return "Invalid nmap command: missing target"
    
    targets = []
    ports = "default"
    scan_type = "default scan"
    
    for i, arg in enumerate(tokens[1:], 1):
        if arg in ["-p", "--ports"] and i + 1 < len(tokens):
            ports = tokens[i + 1]
        elif arg in ["-sS", "-sT", "-sU", "-sV", "-sC"]:
            scan_types = {
                "-sS": "SYN scan",
                "-sT": "TCP connect scan",
                "-sU": "UDP scan",
                "-sV": "Version detection",
                "-sC": "Script scan"
            }
            scan_type = scan_types.get(arg, arg)
        elif not arg.startswith("-"):
            targets.append(arg)
    
    if not targets:
        return "No targets specified for nmap"
    
    return f"Will perform {scan_type} on {', '.join(targets)}" + (f" on ports {ports}" if ports != "default" else "")


# Commands that can be simulated with more specific previews
PREVIEWABLE_COMMANDS = {
    # File operations
    'mkdir': preview_mkdir,
    'touch': preview_touch,
    'rm': preview_rm,
    'cp': preview_cp,
    'mv': preview_mv,
    'ls': preview_ls,
    'cat': preview_cat,
    'grep': preview_grep,
    'find': preview_find,
    'chmod': preview_chmod,
    'chown': preview_chown,
    
    # Archive operations
    'tar': preview_tar,
    'zip': preview_zip,
    'unzip': preview_unzip,
    
    # Package management
    'apt': preview_apt,
    'apt-get': preview_apt,
    'pip': preview_pip,
    
    # Service management
    'systemctl': preview_systemctl,
    
    # Container operations
    'docker': preview_docker,
    
    # Version control
    'git': preview_git,
    
    # Network operations
    'ssh': preview_ssh,
    'ping': preview_ping,
    'wget': preview_wget,
    'curl': preview_curl,
    'ifconfig': preview_ifconfig,
    'ip': preview_ip,
    'nmap': preview_nmap,
    
    # Programming languages
    'python': preview_python,
    'python3': preview_python,
}

# Commands that support dry-run options
DRY_RUN_COMMANDS = {
    # Package management
    'apt': '--dry-run',
    'apt-get': '--dry-run',
    'dnf': '--dry-run',
    'yum': '--dry-run',
    'zypper': '--dry-run',
    'pacman': '--print',
    
    # File operations
    'rsync': '--dry-run',
    'cp': '--dry-run',
    'mv': '--dry-run',
    'rm': '--dry-run',
    
    # Archive operations
    'tar': '--list',  # Not exactly dry-run but shows what would be extracted
    
    # File system operations
    'mkfs': '--fake',
    'mount': '--fake',
    'umount': '--fake',
    
    # Network operations
    'iptables': '--check',
    'ufw': '--dry-run',
    
    # Container operations
    'docker': ['--dry-run', 'inspect'],  # Depends on subcommand
    
    # Version control
    'git': ['--dry-run', 'whatchanged'],  # Depends on subcommand
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
            preview_func = PREVIEWABLE_COMMANDS[base_cmd]
            return await preview_func(command, tokens)
        
        # For other commands, try to use --dry-run or similar flags if available
        if base_cmd in DRY_RUN_COMMANDS:
            dry_run_option = DRY_RUN_COMMANDS[base_cmd]
            
            if isinstance(dry_run_option, list):
                # More complex command with multiple dry run options depending on subcommand
                if len(tokens) > 1:
                    subcommand = tokens[1]
                    
                    # Docker-specific handling
                    if base_cmd == 'docker':
                        if subcommand in ['run', 'create']:
                            return await docker_dry_run(command, dry_run_option[0])
                        elif subcommand in ['rm', 'rmi', 'stop', 'kill']:
                            return await docker_dry_run(command, dry_run_option[0])
                    
                    # Git-specific handling
                    if base_cmd == 'git':
                        if subcommand in ['add', 'clean', 'rm']:
                            return await git_dry_run(command, dry_run_option[0], subcommand)
                
                # Default to the first option if no specific handling
                return await generic_dry_run(command, dry_run_option[0])
            else:
                # Simple command with one dry run option
                return await generic_dry_run(command, dry_run_option)
        
        # If all else fails, use a generic preview message
        return await generic_preview(command)
    
    except Exception as e:
        logger.exception(f"Error generating preview for '{command}': {str(e)}")
        return f"Preview generation failed: {str(e)}"


async def docker_dry_run(command: str, dry_run_flag: str) -> str:
    """
    Generate a preview for Docker commands using --dry-run.
    
    Args:
        command: The Docker command to preview.
        dry_run_flag: The dry run flag to use.
        
    Returns:
        A string containing the preview.
    """
    tokens = shlex.split(command)
    
    if len(tokens) < 2:
        return "Invalid Docker command: missing subcommand"
    
    subcommand = tokens[1]
    
    if subcommand in ['run', 'create']:
        # For run/create, add --dry-run to see what container would be created
        if dry_run_flag not in command:
            modified_command = insert_option_before_image(command, dry_run_flag)
            return f"Docker will create a container with these settings (dry run):\n\n{modified_command}"
    
    elif subcommand in ['rm', 'rmi', 'stop', 'kill']:
        # For these commands, we can list the affected containers/images
        if len(tokens) < 3:
            return f"No targets specified for docker {subcommand}"
        
        targets = [arg for arg in tokens[2:] if not arg.startswith('-')]
        
        if not targets:
            return f"No targets specified for docker {subcommand}"
        
        if subcommand == 'rm':
            return f"Will remove Docker containers: {', '.join(targets)}"
        elif subcommand == 'rmi':
            return f"Will remove Docker images: {', '.join(targets)}"
        elif subcommand in ['stop', 'kill']:
            return f"Will {subcommand} Docker containers: {', '.join(targets)}"
    
    # For any other Docker command, just return a generic message
    return f"Will execute Docker {subcommand} command"


async def git_dry_run(command: str, dry_run_flag: str, subcommand: str) -> str:
    """
    Generate a preview for Git commands using --dry-run.
    
    Args:
        command: The Git command to preview.
        dry_run_flag: The dry run flag to use.
        subcommand: The Git subcommand.
        
    Returns:
        A string containing the preview.
    """
    # For git add, clean, rm, add --dry-run to see what would happen
    if dry_run_flag not in command:
        modified_command = command + " " + dry_run_flag
        
        # Execute the command with dry run
        execution_engine = get_execution_engine()
        stdout, stderr, return_code = await execution_engine.execute_command(modified_command)
        
        if return_code == 0:
            # Process the output based on the subcommand
            if subcommand == 'add':
                if stdout.strip():
                    return f"Git will stage these files:\n\n{stdout}"
                else:
                    return "No files would be staged."
            elif subcommand == 'clean':
                if stdout.strip():
                    return f"Git would remove these untracked files:\n\n{stdout}"
                else:
                    return "No files would be removed."
            elif subcommand == 'rm':
                if stdout.strip():
                    return f"Git would remove these files:\n\n{stdout}"
                else:
                    return "No files would be removed."
            else:
                return f"Git dry run output:\n\n{stdout}"
        else:
            return f"Git dry run failed: {stderr}"
    
    # If already has dry run flag, just return a generic message
    return f"Will execute Git {subcommand} command with dry run"


async def generic_dry_run(command: str, dry_run_flag: str) -> str:
    """
    Generate a preview by running the command with a dry run flag.
    
    Args:
        command: The command to preview.
        dry_run_flag: The dry run flag to use.
        
    Returns:
        A string containing the preview.
    """
    # Check if the flag is already in the command
    if dry_run_flag not in command:
        modified_command = command + " " + dry_run_flag
        
        # Execute the command with the dry run flag
        execution_engine = get_execution_engine()
        stdout, stderr, return_code = await execution_engine.execute_command(modified_command)
        
        if return_code == 0:
            if stdout.strip():
                return f"Dry run output:\n\n{stdout.strip()}"
            else:
                return "Command would execute successfully (dry run produced no output)."
        else:
            return f"Dry run failed: {stderr.strip()}"
    else:
        # If the command already has the dry run flag, execute it as is
        execution_engine = get_execution_engine()
        stdout, stderr, return_code = await execution_engine.execute_command(command)
        
        if return_code == 0:
            return f"Dry run output:\n\n{stdout.strip()}"
        else:
            return f"Dry run failed: {stderr.strip()}"


def insert_option_before_image(command: str, option: str) -> str:
    """
    Insert an option before the image name in a Docker command.
    
    Args:
        command: The Docker command.
        option: The option to insert.
        
    Returns:
        The modified command.
    """
    tokens = shlex.split(command)
    
    if len(tokens) < 3:
        # Not enough tokens for a proper Docker run command
        return command + " " + option
    
    # Find the image position - it's the first non-option argument after 'run'
    image_pos = None
    for i, token in enumerate(tokens[2:], 2):
        if not token.startswith('-'):
            image_pos = i
            break
    
    if image_pos is None:
        # No image found, just append the option
        return command + " " + option
    
    # Insert the option right before the image
    tokens.insert(image_pos, option)
    
    # Reconstruct the command
    return " ".join(tokens)


async def generic_preview(command: str) -> str:
    """
    Generate a generic preview for commands without specific implementations.
    
    Args:
        command: The shell command to preview.
        
    Returns:
        A string containing the preview.
    """
    tokens = shlex.split(command)
    base_cmd = tokens[0]
    
    # Try to identify what type of command this is
    if base_cmd in ["node", "npm", "npx"]:
        return await node_preview(command, tokens)
    elif base_cmd in ["java", "javac", "jar"]:
        return await java_preview(command, tokens)
    elif base_cmd in ["gcc", "g++", "make", "cmake"]:
        return await build_preview(command, tokens)
    
    # For truly unknown commands, provide a helpful but generic message
    return "Preview not available for this command type. Use --dry-run to simulate if supported."


async def node_preview(command: str, tokens: List[str]) -> str:
    """Generate a preview for Node.js commands."""
    if tokens[0] == "node":
        if len(tokens) < 2:
            return "Will start an interactive Node.js REPL"
        
        script = tokens[1]
        if not script.startswith("-"):
            if not Path(script).exists():
                return f"❌ Node.js script does not exist: {script}"
            return f"Will execute Node.js script: {script}"
    
    elif tokens[0] == "npm":
        if len(tokens) < 2:
            return "Will display npm help"
        
        subcommand = tokens[1]
        
        if subcommand in ["install", "i"]:
            packages = [arg for arg in tokens[2:] if not arg.startswith('-') and arg != "."]
            if not packages:
                if "--save-dev" in command or "-D" in command:
                    return "Will install development dependencies from package.json"
                else:
                    return "Will install dependencies from package.json"
            
            return f"Will install npm packages: {', '.join(packages)}"
        
        elif subcommand in ["uninstall", "remove", "rm", "un", "r"]:
            packages = [arg for arg in tokens[2:] if not arg.startswith('-')]
            if not packages:
                return "No packages specified for npm uninstall"
            
            return f"Will uninstall npm packages: {', '.join(packages)}"
        
        elif subcommand in ["start", "run"]:
            if subcommand == "start":
                return "Will run the 'start' script defined in package.json"
            elif len(tokens) > 2:
                script = tokens[2]
                return f"Will run the '{script}' script defined in package.json"
    
    return f"Will execute {tokens[0]} command"


async def java_preview(command: str, tokens: List[str]) -> str:
    """Generate a preview for Java commands."""
    if tokens[0] == "java":
        class_name = None
        
        for i, arg in enumerate(tokens[1:], 1):
            if not arg.startswith('-'):
                class_name = arg
                break
        
        if not class_name:
            return "Invalid java command: missing class name"
        
        return f"Will execute Java class: {class_name}"
    
    elif tokens[0] == "javac":
        files = [arg for arg in tokens[1:] if not arg.startswith('-') and arg.endswith('.java')]
        
        if not files:
            return "No Java source files specified for compilation"
        
        return f"Will compile Java source files: {', '.join(files)}"
    
    elif tokens[0] == "jar":
        if len(tokens) < 2:
            return "Invalid jar command: missing operation"
        
        operation = tokens[1]
        
        if operation in ["cf", "c"]:
            if len(tokens) < 3:
                return "Invalid jar command: missing jar file"
            
            jar_file = tokens[2]
            files = tokens[3:]
            
            return f"Will create JAR file {jar_file}" + (f" containing {len(files)} files" if files else "")
        
        elif operation in ["xf", "x"]:
            if len(tokens) < 3:
                return "Invalid jar command: missing jar file"
            
            jar_file = tokens[2]
            
            return f"Will extract JAR file {jar_file}"
        
        elif operation in ["tf", "t"]:
            if len(tokens) < 3:
                return "Invalid jar command: missing jar file"
            
            jar_file = tokens[2]
            
            return f"Will list contents of JAR file {jar_file}"
    
    return f"Will execute {tokens[0]} command"


async def build_preview(command: str, tokens: List[str]) -> str:
    """Generate a preview for build commands."""
    if tokens[0] in ["gcc", "g++"]:
        source_files = []
        output_file = "a.out"  # Default output
        
        for i, arg in enumerate(tokens[1:], 1):
            if arg == "-o" and i + 1 < len(tokens):
                output_file = tokens[i + 1]
            elif not arg.startswith('-') and arg.endswith(('.c', '.cpp', '.h', '.hpp', '.o')):
                source_files.append(arg)
        
        if not source_files:
            return f"No source files specified for {tokens[0]}"
        
        return f"Will compile source files ({', '.join(source_files)}) to {output_file}"
    
    elif tokens[0] == "make":
        if len(tokens) < 2:
            return "Will run the default make target"
        
        targets = [arg for arg in tokens[1:] if not arg.startswith('-')]
        
        if not targets:
            return "Will run the default make target"
        
        return f"Will run make targets: {', '.join(targets)}"
    
    elif tokens[0] == "cmake":
        if len(tokens) < 2:
            return "Will configure a CMake project in the current directory"
        
        build_dir = None
        
        for i, arg in enumerate(tokens[1:], 1):
            if not arg.startswith('-'):
                build_dir = arg
                break
        
        if build_dir:
            return f"Will configure a CMake project from {build_dir}"
        else:
            return "Will configure a CMake project with custom options"
    
    return f"Will execute {tokens[0]} command"


class CommandPreviewGenerator:
    """Generator for command previews."""
    
    async def generate_preview(self, command: str) -> Optional[str]:
        """
        Generate a preview of what a command will do.
        
        Args:
            command: The shell command to preview.
            
        Returns:
            A string containing the preview, or None if preview is not available.
        """
        # This simply delegates to the existing function
        preview_text = await generate_preview(command)
        
        return preview_text

# Create a global instance of the generator class
command_preview_generator = CommandPreviewGenerator()
