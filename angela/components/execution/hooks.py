# angela/execution/hooks.py
"""
Execution hooks for file operations and command execution.

This module provides hooks for tracking file activities during execution
and enriching context in real-time.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

# Import through API layer
from angela.api.context import get_file_activity_tracker, get_activity_type
from angela.api.utils import get_logger

logger = get_logger(__name__)

class ExecutionHooks:
    """
    Hooks for file operations and command execution.
    
    Provides hooks to track file activities during execution:
    1. Pre-execution hooks (before a command/operation is executed)
    2. Post-execution hooks (after a command/operation is executed)
    """
    
    def __init__(self):
        """Initialize the execution hooks."""
        self._logger = logger
        self._pre_execute_hooks = {}
        self._post_execute_hooks = {}


    def register_hook(self, hook_type: str, handler: callable) -> None:
        """
        Register a hook handler for a specific hook type.
        
        Args:
            hook_type: Type of hook (e.g., 'pre_execute_command', 'post_execute_command')
            handler: Callable to execute when the hook is triggered
        """
        self._logger.debug(f"Registering {hook_type} hook")
        
        if hook_type.startswith('pre_'):
            if hook_type not in self._pre_execute_hooks:
                self._pre_execute_hooks[hook_type] = []
            self._pre_execute_hooks[hook_type].append(handler)
        elif hook_type.startswith('post_'):
            if hook_type not in self._post_execute_hooks:
                self._post_execute_hooks[hook_type] = []
            self._post_execute_hooks[hook_type].append(handler)
        else:
            self._logger.warning(f"Unknown hook type: {hook_type}")
    
    def unregister_hook(self, hook_type: str, handler: callable) -> None:
        """
        Unregister a hook handler.
        
        Args:
            hook_type: Type of hook
            handler: Handler to unregister
        """
        self._logger.debug(f"Unregistering {hook_type} hook")
        
        if hook_type.startswith('pre_') and hook_type in self._pre_execute_hooks:
            if handler in self._pre_execute_hooks[hook_type]:
                self._pre_execute_hooks[hook_type].remove(handler)
        elif hook_type.startswith('post_') and hook_type in self._post_execute_hooks:
            if handler in self._post_execute_hooks[hook_type]:
                self._post_execute_hooks[hook_type].remove(handler)


    
    async def pre_execute_command(self, command: str, context: Dict[str, Any]) -> None:
        """
        Pre-execution hook for commands.
        
        Args:
            command: The command to be executed
            context: Context information
        """
        self._logger.debug(f"Pre-execute hook for command: {command}")
        
        # Extract potential file operations from the command
        await self._analyze_command_for_files(command, context)
        
        # Call registered pre-execute hooks
        hook_type = 'pre_execute_command'
        if hook_type in self._pre_execute_hooks:
            for handler in self._pre_execute_hooks[hook_type]:
                try:
                    await handler(command, context)
                except Exception as e:
                    self._logger.error(f"Error in {hook_type} hook: {str(e)}")
    
    async def post_execute_command(self, command: str, result: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Post-execution hook for commands.
        
        Args:
            command: The executed command
            result: The execution result
            context: Context information
        """
        self._logger.debug(f"Post-execute hook for command: {command}")
        
        # Check if the command succeeded
        if not result.get("success", False):
            return
        
        # Analyze command output for file information
        await self._analyze_command_output(command, result.get("stdout", ""), context)
        
        # Track file activities based on the command type
        base_command = command.split()[0] if command else ""
        
        # Handle common file operation commands
        if base_command in ["cat", "less", "more", "head", "tail"]:
            await self._track_file_viewing(command, context)
        elif base_command in ["touch", "echo", "tee"]:
            await self._track_file_creation(command, context)
        elif base_command in ["rm", "rmdir"]:
            await self._track_file_deletion(command, context)
        elif base_command in ["cp", "mv", "rsync"]:
            await self._track_file_copy_move(command, context)
        elif base_command in ["sed", "awk", "perl", "nano", "vim", "emacs"]:
            await self._track_file_modification(command, context)
        
        # Call registered post-execute hooks
        hook_type = 'post_execute_command'
        if hook_type in self._post_execute_hooks:
            for handler in self._post_execute_hooks[hook_type]:
                try:
                    await handler(command, result, context)
                except Exception as e:
                    self._logger.error(f"Error in {hook_type} hook: {str(e)}")
    
    async def pre_execute_file_operation(
        self, 
        operation_type: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Pre-execution hook for file operations.
        
        Args:
            operation_type: The type of file operation
            parameters: The operation parameters
            context: Context information
        """
        self._logger.debug(f"Pre-execute hook for file operation: {operation_type}")
        
        # Nothing specific to do before file operations for now
        pass
    
    async def post_execute_file_operation(
        self, 
        operation_type: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Post-execution hook for file operations.
        
        Args:
            operation_type: The type of file operation
            parameters: The operation parameters
            result: The operation result
            context: Context information
        """
        self._logger.debug(f"Post-execute hook for file operation: {operation_type}")
        
        # Check if the operation succeeded
        if not result.get("success", False):
            return
        
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        ActivityType = get_activity_type()
        
        # Track file activity based on operation type
        if operation_type == "create_file":
            file_path = parameters.get("path")
            if file_path:
                file_activity_tracker.track_file_creation(
                    Path(file_path),
                    None,  # No command
                    {"operation": operation_type}
                )
        elif operation_type == "write_file":
            file_path = parameters.get("path")
            if file_path:
                file_activity_tracker.track_file_modification(
                    Path(file_path),
                    None,  # No command
                    {"operation": operation_type, "append": parameters.get("append", False)}
                )
        elif operation_type == "delete_file":
            file_path = parameters.get("path")
            if file_path:
                file_activity_tracker.track_file_deletion(
                    Path(file_path),
                    None,  # No command
                    {"operation": operation_type}
                )
        elif operation_type == "read_file":
            file_path = parameters.get("path")
            if file_path:
                file_activity_tracker.track_file_viewing(
                    Path(file_path),
                    None,  # No command
                    {"operation": operation_type}
                )
        elif operation_type == "copy_file":
            source = parameters.get("source")
            destination = parameters.get("destination")
            if source and destination:
                # Track the source as read
                file_activity_tracker.track_file_viewing(
                    Path(source),
                    None,  # No command
                    {"operation": operation_type}
                )
                # Track the destination as created/modified
                file_activity_tracker.track_file_creation(
                    Path(destination),
                    None,  # No command
                    {"operation": operation_type, "source": source}
                )
        elif operation_type == "move_file":
            source = parameters.get("source")
            destination = parameters.get("destination")
            if source and destination:
                # Track the source as deleted
                file_activity_tracker.track_file_deletion(
                    Path(source),
                    None,  # No command
                    {"operation": operation_type}
                )
                # Track the destination as created
                file_activity_tracker.track_file_creation(
                    Path(destination),
                    None,  # No command
                    {"operation": operation_type, "source": source}
                )
    
    async def _analyze_command_for_files(
        self, 
        command: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Analyze a command for potential file operations.
        
        Args:
            command: The command to analyze
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        # Split command into tokens
        tokens = command.split()
        
        if not tokens:
            return
        
        base_command = tokens[0]
        
        # Check for file paths in tokens
        paths = []
        
        for token in tokens[1:]:
            # Skip options
            if token.startswith('-'):
                continue
            
            # Skip redirection operators
            if token in ['>', '<', '>>', '2>', '&>']:
                continue
            
            # Check if token looks like a path
            if '/' in token or '.' in token:
                # Resolve relative to CWD
                path = Path(context.get("cwd", ".")) / token
                if path.exists():
                    paths.append(path)
        
        # Track potential file accesses
        for path in paths:
            if path.is_file():
                file_activity_tracker.track_file_viewing(
                    path,
                    command,
                    {"pre_execution": True}
                )
    
    async def _analyze_command_output(
        self, 
        command: str,
        output: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Analyze command output for file information.
        
        Args:
            command: The executed command
            output: The command output
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        # Check for file paths in output
        paths = set()
        
        # Look for patterns that might be file paths
        path_patterns = [
            r'[\'"]([/\w\-\.]+\.\w+)[\'"]',  # Quoted paths with extension
            r'\b(/[/\w\-\.]+\.\w+)\b',       # Absolute paths with extension
            r'\b(\./[/\w\-\.]+\.\w+)\b',     # Relative paths with ./ prefix
        ]
        
        for pattern in path_patterns:
            for match in re.finditer(pattern, output):
                potential_path = match.group(1)
                
                # Resolve relative to CWD
                if not potential_path.startswith('/'):
                    potential_path = os.path.join(context.get("cwd", "."), potential_path)
                
                path = Path(potential_path)
                if path.exists() and path.is_file():
                    paths.add(path)
        
        # Track found files
        for path in paths:
            if path.is_file():
                file_activity_tracker.track_file_viewing(
                    path,
                    command,
                    {"from_output": True}
                )
    
    async def _track_file_viewing(
        self, 
        command: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Track file viewing for commands like cat, less, more, etc.
        
        Args:
            command: The executed command
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        tokens = command.split()
        
        if len(tokens) < 2:
            return
        
        # Find potential file paths
        for token in tokens[1:]:
            # Skip options
            if token.startswith('-'):
                continue
            
            # Skip if it looks like a pipe or redirection
            if token in ['|', '>', '<', '>>', '2>', '&>']:
                break
            
            # Resolve path
            path = Path(token)
            if not path.is_absolute():
                path = Path(context.get("cwd", ".")) / token
            
            if path.exists() and path.is_file():
                file_activity_tracker.track_file_viewing(
                    path,
                    command,
                    {}
                )
    
    async def _track_file_creation(
        self, 
        command: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Track file creation for commands like touch, etc.
        
        Args:
            command: The executed command
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        tokens = command.split()
        
        if len(tokens) < 2:
            return
        
        # Handle touch command
        if tokens[0] == 'touch':
            for token in tokens[1:]:
                # Skip options
                if token.startswith('-'):
                    continue
                
                # Resolve path
                path = Path(token)
                if not path.is_absolute():
                    path = Path(context.get("cwd", ".")) / token
                
                if path.exists() and path.is_file():
                    file_activity_tracker.track_file_creation(
                        path,
                        command,
                        {}
                    )
        
        # Handle echo/redirection
        elif tokens[0] == 'echo':
            # Look for redirection
            redirect_idx = -1
            for i, token in enumerate(tokens):
                if token in ['>', '>>']:
                    redirect_idx = i
                    break
            
            if redirect_idx > 0 and redirect_idx < len(tokens) - 1:
                file_path = tokens[redirect_idx + 1]
                
                # Resolve path
                path = Path(file_path)
                if not path.is_absolute():
                    path = Path(context.get("cwd", ".")) / file_path
                
                # Get ActivityType via API
                ActivityType = get_activity_type()
                operation = ActivityType.CREATED
                if tokens[redirect_idx] == '>>':
                    operation = ActivityType.MODIFIED
                
                if path.exists() and path.is_file():
                    if operation == ActivityType.CREATED:
                        file_activity_tracker.track_file_creation(
                            path,
                            command,
                            {"redirect": tokens[redirect_idx]}
                        )
                    else:
                        file_activity_tracker.track_file_modification(
                            path,
                            command,
                            {"redirect": tokens[redirect_idx]}
                        )
    
    async def _track_file_deletion(
        self, 
        command: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Track file deletion for commands like rm, etc.
        
        Args:
            command: The executed command
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        tokens = command.split()
        
        if len(tokens) < 2:
            return
        
        # Skip arguments until we find a non-option
        for token in tokens[1:]:
            # Skip options
            if token.startswith('-'):
                continue
            
            # This is probably a path
            path = Path(token)
            if not path.is_absolute():
                path = Path(context.get("cwd", ".")) / token
            
            # We can't check if it exists since it was deleted
            file_activity_tracker.track_file_deletion(
                path,
                command,
                {}
            )
    
    async def _track_file_copy_move(
        self, 
        command: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Track file copy/move for commands like cp, mv, etc.
        
        Args:
            command: The executed command
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        tokens = command.split()
        
        if len(tokens) < 3:
            return
        
        base_command = tokens[0]
        
        # Find the source and destination
        source_tokens = []
        dest_token = tokens[-1]  # Last token is destination
        
        # Collect all tokens that aren't options as source tokens
        for token in tokens[1:-1]:
            if not token.startswith('-'):
                source_tokens.append(token)
        
        # Resolve destination path
        dest_path = Path(dest_token)
        if not dest_path.is_absolute():
            dest_path = Path(context.get("cwd", ".")) / dest_token
        
        # Track each source
        for source_token in source_tokens:
            source_path = Path(source_token)
            if not source_path.is_absolute():
                source_path = Path(context.get("cwd", ".")) / source_token
            
            if base_command == 'cp':
                # For cp, source is viewed and destination is created
                file_activity_tracker.track_file_viewing(
                    source_path,
                    command,
                    {"operation": "copy", "destination": str(dest_path)}
                )
                
                # If destination is a directory, the file goes inside it
                if dest_path.is_dir():
                    actual_dest = dest_path / source_path.name
                else:
                    actual_dest = dest_path
                
                file_activity_tracker.track_file_creation(
                    actual_dest,
                    command,
                    {"operation": "copy", "source": str(source_path)}
                )
            elif base_command == 'mv':
                # For mv, source is deleted and destination is created
                file_activity_tracker.track_file_deletion(
                    source_path,
                    command,
                    {"operation": "move", "destination": str(dest_path)}
                )
                
                # If destination is a directory, the file goes inside it
                if dest_path.is_dir():
                    actual_dest = dest_path / source_path.name
                else:
                    actual_dest = dest_path
                
                file_activity_tracker.track_file_creation(
                    actual_dest,
                    command,
                    {"operation": "move", "source": str(source_path)}
                )
    
    async def _track_file_modification(
        self, 
        command: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Track file modification for commands like sed, etc.
        
        Args:
            command: The executed command
            context: Context information
        """
        # Get file activity tracker via API
        file_activity_tracker = get_file_activity_tracker()
        
        tokens = command.split()
        
        if len(tokens) < 2:
            return
        
        base_command = tokens[0]
        
        # Handle sed command
        if base_command == 'sed':
            # Find the file token (usually the last one)
            file_token = None
            for i in range(len(tokens) - 1, 0, -1):
                if not tokens[i].startswith('-') and not tokens[i].startswith("'") and not tokens[i].startswith('"'):
                    file_token = tokens[i]
                    break
            
            if file_token:
                path = Path(file_token)
                if not path.is_absolute():
                    path = Path(context.get("cwd", ".")) / file_token
                
                if path.exists() and path.is_file():
                    file_activity_tracker.track_file_modification(
                        path,
                        command,
                        {}
                    )

# Global execution hooks instance
execution_hooks = ExecutionHooks()
