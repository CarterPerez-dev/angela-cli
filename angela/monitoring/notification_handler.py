"""
Handles notifications from shell hooks for Angela CLI.
"""
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from angela.utils.logging import get_logger
from angela.context import context_manager
from angela.context.session import session_manager
from angela.context.file_activity import file_activity_tracker
from angela.monitoring.background import background_monitor
from angela.orchestrator import orchestrator

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
                duration=int(args[2]) if len(args) > 2 else 0
            )
        elif notification_type == "dir_change":
            await self._handle_dir_change(args[0] if args else "")
    
    async def _handle_pre_exec(self, command: str) -> None:
        """
        Handle command pre-execution notification.
        
        Args:
            command: The command about to be executed
        """
        if not command:
            return
            
        # Update session context
        session_manager.add_entity("current_command", "command", command)
        
        # Record start time for performance tracking
        self._running_commands[command] = {
            "start_time": asyncio.get_event_loop().time(),
            "cwd": str(context_manager.cwd)
        }
        
        # Log the command for later analysis
        self._logger.info(f"Command started: {command}")
        
        # If it's a potentially long-running command, start monitoring
        if _is_long_running_command(command):
            background_monitor.start_command_monitoring(command)
    
    async def _handle_post_exec(self, command: str, exit_code: int, duration: int) -> None:
        """
        Handle command post-execution notification.
        
        Args:
            command: The executed command
            exit_code: The command's exit code
            duration: Execution duration in seconds
        """
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
        
        # Clean up running commands
        if command in self._running_commands:
            del self._running_commands[command]
        
        # Stop monitoring if it was a long-running command
        if _is_long_running_command(command):
            background_monitor.stop_command_monitoring(command)
        
        # Add to session recent commands
        session_manager.add_command(command)
        session_manager.add_entity("last_exit_code", "exit_code", exit_code)
        
        # If command failed, store it for potential automatic fixes
        if exit_code != 0:
            session_manager.add_entity("last_failed_command", "command", command)
            
            # If this is a common command with a known fix pattern, offer help
            # This would be expanded with more sophisticated analysis
            if _has_known_fix_pattern(command):
                # This would trigger a proactive suggestion in the terminal
                pass
    
    async def _handle_dir_change(self, new_dir: str) -> None:
        """
        Handle directory change notification.
        
        Args:
            new_dir: The new current directory
        """
        if not new_dir:
            return
            
        # Update context manager with new directory
        context_manager.refresh_context()
        
        # Add to recent directories
        if new_dir not in self._recent_directories:
            self._recent_directories.insert(0, new_dir)
            # Trim to max size
            if len(self._recent_directories) > self._max_directories:
                self._recent_directories = self._recent_directories[:self._max_directories]
        
        # Update session context
        session_manager.add_entity("current_directory", "directory", new_dir)
        session_manager.add_entity("recent_directories", "directories", self._recent_directories)
        
        # If moving to a project directory, refresh project context
        project_root = context_manager.project_root
        if project_root:
            session_manager.add_entity("project_root", "directory", str(project_root))

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
        "docker-compose up", "make", "cmake", "gcc", "mvn", "gradle",
        "cargo build", "test", "pytest", "yarn", "sleep", "find"
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
    # This would be expanded with more sophisticated pattern matching
    known_patterns = [
        "git push", "git pull", "npm install", "pip install"
    ]
    
    return any(pattern in command for pattern in known_patterns)

# Global instance
notification_handler = NotificationHandler()
