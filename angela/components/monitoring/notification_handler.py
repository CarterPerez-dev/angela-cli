# angela/monitoring/notification_handler.py

"""
Handles notifications from shell hooks for Angela CLI.
"""
import asyncio
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import sys

from angela.utils.logging import get_logger
from angela.api.context import get_context_manager
from angela.api.context import get_session_manager
from angela.api.context import get_file_activity_tracker
from angela.api.monitoring import get_background_monitor
from angela.api.shell import get_inline_feedback

logger = get_logger(__name__)

class NotificationHandler:
    """
    Handles notifications from shell hooks.
    
    This class processes notifications sent by the shell integration hooks like
    command pre-execution, post-execution, and directory changes.
    """
    
    def __init__(self):
        """Initialize the notification handler."""
        self._logger = logger
        # Store currently running long commands for monitoring
        self._running_commands = {}
        # Track command execution times for performance insights
        self._command_times = {}
        # Track recent directories for context enhancement
        self._recent_directories = []
        # Maximum number of directories to track
        self._max_directories = 10
        # Track commonly failing commands for better suggestions
        self._command_errors = {}
        # Maximum command errors to track
        self._max_errors_per_command = 5
    
    async def handle_notification(self, notification_type: str, *args) -> None:
        """
        Handle a notification from the shell hooks.
        
        Args:
            notification_type: Type of notification (pre_exec, post_exec, dir_change)
            args: Additional arguments for the notification
        """
        self._logger.debug(f"Received notification: {notification_type} with args: {args}")
        
        if notification_type == "pre_exec":
            await self._handle_pre_exec(args[0] if args else "")
        elif notification_type == "post_exec":
            await self._handle_post_exec(
                command=args[0] if len(args) > 0 else "",
                exit_code=int(args[1]) if len(args) > 1 else 0,
                duration=int(args[2]) if len(args) > 2 else 0,
                stderr=args[3] if len(args) > 3 else ""
            )
        elif notification_type == "dir_change":
            await self._handle_dir_change(args[0] if args else "")
    
    async def _handle_pre_exec(self, command: str) -> None:
        """
        Handle command pre-execution notification.
        
        Args:
            command: The command about to be executed
        """
        from angela.api.context import get_session_manager, get_context_manager
        from angela.api.monitoring import get_background_monitor
        
        if not command:
            return
            
        # Update session context
        get_session_manager().add_entity("current_command", "command", command)
        
        # Record start time for performance tracking
        self._running_commands[command] = {
            "start_time": asyncio.get_event_loop().time(),
            "cwd": str(get_context_manager().cwd)
        }
        
        # Log the command for later analysis
        self._logger.info(f"Command started: {command}")
        
        # If it's a potentially long-running command, start monitoring
        if _is_long_running_command(command):
            get_background_monitor().start_command_monitoring(command)
    
    async def _handle_post_exec(self, command: str, exit_code: int, duration: int, stderr: str = "") -> None:
        """
        Handle command post-execution notification.
        
        Args:
            command: The executed command
            exit_code: The command's exit code
            duration: Execution duration in seconds
            stderr: Standard error output (if available)
        """
        from angela.api.context import get_session_manager
        from angela.api.monitoring import get_background_monitor
        from angela.api.shell import get_inline_feedback
        
        if not command:
            return
            
        # Update command statistics
        cmd_base = _extract_base_command(command)
        if cmd_base not in self._command_times:
            self._command_times[cmd_base] = {"count": 0, "total_time": 0, "failures": 0}
        
        self._command_times[cmd_base]["count"] += 1
        self._command_times[cmd_base]["total_time"] += duration
        if exit_code != 0:
            self._command_times[cmd_base]["failures"] += 1
            
            # Track error information for this command
            if cmd_base not in self._command_errors:
                self._command_errors[cmd_base] = []
                
            # Store error information with limited history
            self._command_errors[cmd_base].append({
                "command": command,
                "stderr": stderr,
                "exit_code": exit_code,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Trim error history if needed
            if len(self._command_errors[cmd_base]) > self._max_errors_per_command:
                self._command_errors[cmd_base].pop(0)
        
        # Clean up running commands
        if command in self._running_commands:
            del self._running_commands[command]
        
        # Stop monitoring if it was a long-running command
        if _is_long_running_command(command):
            get_background_monitor().stop_command_monitoring(command)
        
        # Add to session recent commands
        get_session_manager().add_command(command)
        get_session_manager().add_entity("last_exit_code", "exit_code", exit_code)
        if stderr:
            get_session_manager().add_entity("last_stderr", "error_output", stderr)
        
        # If command failed, store it for potential automatic fixes
        if exit_code != 0:
            get_session_manager().add_entity("last_failed_command", "command", command)
            
            # Analyze the failed command and show proactive suggestions
            fix_suggestion = await self._analyze_failed_command(command, stderr)
            if fix_suggestion:
                # Trigger a proactive suggestion in the terminal
                await get_inline_feedback().show_message(
                    f"Command failed. Suggestion: {fix_suggestion}",
                    message_type="warning",
                    timeout=15
                )
    
    async def _handle_dir_change(self, new_dir: str) -> None:
        """
        Handle directory change notification.
        
        Args:
            new_dir: The new current directory
        """
        from angela.api.context import get_context_manager
        from angela.api.context import get_session_manager
        from angela.api.shell import get_inline_feedback
        
        if not new_dir:
            return
            
        # Update context manager with new directory
        get_context_manager().refresh_context()
        
        # Add to recent directories
        if new_dir not in self._recent_directories:
            self._recent_directories.insert(0, new_dir)
            # Trim to max size
            if len(self._recent_directories) > self._max_directories:
                self._recent_directories = self._recent_directories[:self._max_directories]
        
        # Update session context
        get_session_manager().add_entity("current_directory", "directory", new_dir)
        get_session_manager().add_entity("recent_directories", "directories", self._recent_directories)
        
        # If moving to a project directory, refresh project context
        project_root = get_context_manager().project_root
        if project_root:
            get_session_manager().add_entity("project_root", "directory", str(project_root))
            
            # If this is a new project, show a helpful message
            if str(project_root) not in self._recent_directories[1:]:
                project_type = get_context_manager().project_type
                if project_type:
                    await get_inline_feedback().show_message(
                        f"Detected {project_type.capitalize()} project. Type 'angela help-with {project_type}' for project-specific assistance.",
                        message_type="info",
                        timeout=5
                    )

    async def _analyze_failed_command(self, command: str, stderr: str = "") -> Optional[str]:
        """
        Analyze a failed command to generate a fix suggestion.
        
        Args:
            command: The failed command
            stderr: Standard error output (if available)
            
        Returns:
            A suggestion string or None if no suggestion is available
        """
        from angela.api.context import get_session_manager, get_history_manager
        
        # Get exit code from session if stderr not provided
        if not stderr:
            stderr_entity = get_session_manager().get_entity("last_stderr")
            stderr = stderr_entity.get("value", "") if stderr_entity else ""
        
        # Common error patterns and suggested fixes
        error_patterns = [
            # Git errors
            {
                "pattern": "fatal: could not read Username",
                "command_pattern": "git push",
                "suggestion": "Try setting up SSH keys or use a credential helper: git config --global credential.helper cache"
            },
            {
                "pattern": "fatal: not a git repository",
                "command_pattern": "git",
                "suggestion": "Initialize a git repository first: git init"
            },
            {
                "pattern": "error: failed to push some refs",
                "command_pattern": "git push",
                "suggestion": "Pull changes first: git pull --rebase"
            },
            {
                "pattern": "CONFLICT",
                "command_pattern": "git merge",
                "suggestion": "Resolve merge conflicts and then commit the changes"
            },
            {
                "pattern": "error: Your local changes to the following files would be overwritten by merge",
                "command_pattern": "git pull",
                "suggestion": "Stash your changes first: git stash"
            },
            
            # Python/pip errors
            {
                "pattern": "No module named",
                "command_pattern": "python",
                "suggestion": "Install the missing module with pip: pip install [module_name]"
            },
            {
                "pattern": "ModuleNotFoundError",
                "command_pattern": "python",
                "suggestion": "Install the missing module with pip: pip install [module_name]"
            },
            {
                "pattern": "Could not find a version that satisfies the requirement",
                "command_pattern": "pip install",
                "suggestion": "Check the package name or try with a specific version"
            },
            {
                "pattern": "SyntaxError",
                "command_pattern": "python",
                "suggestion": "Fix the syntax error in your Python file"
            },
            
            # NPM errors
            {
                "pattern": "npm ERR! code ENOENT",
                "command_pattern": "npm",
                "suggestion": "Check if package.json exists in the current directory"
            },
            {
                "pattern": "npm ERR! code E404",
                "command_pattern": "npm install",
                "suggestion": "Package not found. Check the package name and registry"
            },
            {
                "pattern": "Missing script:",
                "command_pattern": "npm run",
                "suggestion": "The script does not exist in package.json. Check available scripts with: npm run"
            },
            
            # Docker errors
            {
                "pattern": "Error response from daemon",
                "command_pattern": "docker",
                "suggestion": "Check if docker daemon is running: systemctl start docker"
            },
            {
                "pattern": "image not found",
                "command_pattern": "docker",
                "suggestion": "Pull the image first: docker pull [image_name]"
            },
            
            # Permission errors
            {
                "pattern": "Permission denied",
                "suggestion": "Try running with sudo or check file permissions"
            },
            
            # Make errors
            {
                "pattern": "No rule to make target",
                "command_pattern": "make",
                "suggestion": "Check your Makefile for the correct target names"
            },
            
            # Generic command not found
            {
                "pattern": "command not found",
                "suggestion": "Install the required package or check the command spelling"
            }
        ]
        
        # Check for specific error patterns in stderr
        for pattern in error_patterns:
            error_pattern = pattern["pattern"]
            cmd_pattern = pattern.get("command_pattern", "")
            
            # Skip if command pattern doesn't match
            if cmd_pattern and cmd_pattern not in command:
                continue
                
            if error_pattern in stderr:
                suggestion = pattern["suggestion"]
                
                # Extract module name if applicable
                if "[module_name]" in suggestion and "No module named " in stderr:
                    module_match = re.search(r"No module named '([^']+)'", stderr)
                    if module_match:
                        module_name = module_match.group(1)
                        suggestion = suggestion.replace("[module_name]", module_name)
                
                # Extract image name if applicable
                if "[image_name]" in suggestion and "image not found" in stderr:
                    image_match = re.search(r"[Ee]rror.*image (.*): not found", stderr)
                    if image_match:
                        image_name = image_match.group(1)
                        suggestion = suggestion.replace("[image_name]", image_name)
                
                return suggestion
        
        # Learning from command history
        cmd_base = _extract_base_command(command)
        
        # Check if we have similar past failures
        if cmd_base in self._command_errors:
            # Look for successful commands that followed the same failed command
            similar_commands = get_history_manager().search_similar_command(command)
            if similar_commands and similar_commands.get("success", False):
                return f"Previously successful command: {similar_commands['command']}"
        
        # Fallback suggestions based on command type
        fallback_suggestions = {
            "git": "Check git status and repository configuration",
            "npm": "Verify package.json is valid and node_modules is not corrupted",
            "pip": "Check your Python environment and package requirements",
            "python": "Verify your Python code syntax and imported modules",
            "docker": "Ensure Docker daemon is running and you have sufficient permissions",
            "make": "Check Makefile syntax and required dependencies",
            "yarn": "Verify package.json and yarn.lock files",
            "cargo": "Check your Rust project configuration",
            "mvn": "Verify your Maven configuration and dependencies"
        }
        
        # Return fallback suggestion if available
        if cmd_base in fallback_suggestions:
            return fallback_suggestions[cmd_base]
        
        # No suggestion available
        return None

def _extract_base_command(command: str) -> str:
    """
    Extract the base command from a full command string.
    
    Args:
        command: The full command string
        
    Returns:
        The base command (first word or git subcommand)
    """
    parts = command.strip().split()
    if not parts:
        return ""
    
    # Handle git subcommands as a special case
    if parts[0] == "git" and len(parts) > 1:
        return f"git {parts[1]}"
    
    # Handle npm subcommands
    if parts[0] == "npm" and len(parts) > 1:
        return f"npm {parts[1]}"
    
    # Handle docker subcommands
    if parts[0] == "docker" and len(parts) > 1:
        return f"docker {parts[1]}"
    
    return parts[0]

def _is_long_running_command(command: str) -> bool:
    """
    Check if a command is potentially long-running.
    
    Args:
        command: The command to check
        
    Returns:
        True if the command is potentially long-running
    """
    long_running_patterns = [
        "npm install", "pip install", "apt", "brew", "docker build", 
        "docker-compose up", "make", "cmake", "gcc", "g++", "mvn", "gradle",
        "cargo build", "test", "pytest", "yarn", "sleep", "find", "grep -r",
        "ffmpeg", "convert", "zip", "tar", "unzip", "gunzip", "rsync"
    ]
    
    return any(pattern in command for pattern in long_running_patterns)

def _has_known_fix_pattern(command: str) -> bool:
    """
    Check if a command has a known fix pattern.
    
    Args:
        command: The command to check
        
    Returns:
        True if there's a known fix pattern for this command
    """
    known_patterns = [
        "git push", "git pull", "git commit", "git merge", "git checkout",
        "npm install", "npm run", "npm start", "npm test", "npm build",
        "pip install", "pip uninstall", "python", "pytest", "python -m",
        "docker", "docker-compose", "docker run", "docker build",
        "cargo", "cargo build", "cargo test", "cargo run",
        "make", "make clean", "make install", 
        "mvn", "gradle", "yarn", "bundle"
    ]
    
    return any(pattern in command for pattern in known_patterns)

# Global instance
notification_handler = NotificationHandler()
