"""
Background monitoring and proactive suggestions for Angela CLI.

This module provides background monitoring of system state and user activities
to offer proactive assistance and suggestions.
"""
import os
import sys
import asyncio
import time
import re
import signal
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
from datetime import datetime, timedelta

from angela.ai.client import GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.shell.formatter import terminal_formatter

logger = get_logger(__name__)

class BackgroundMonitor:
    """
    Background monitor for detecting potential issues and offering proactive assistance.
    
    Monitors:
    1. Git status changes
    2. Syntax errors in recently modified files
    3. System resource usage
    4. Process failures
    5. Common error patterns
    """
    
    def __init__(self):
        """Initialize the background monitor."""
        self._logger = logger
        self._monitoring_tasks = set()
        self._monitoring_active = False
        self._suggestions = set()  # To avoid repeating the same suggestions
        self._last_suggestion_time = datetime.now() - timedelta(hours=1)  # Ensure initial delay has passed
        self._suggestion_cooldown = timedelta(minutes=5)  # Minimum time between suggestions
    
    def start_monitoring(self):
        """Start background monitoring tasks."""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        
        # Create and start monitoring tasks
        self._create_monitoring_task(self._monitor_git_status(), "git_status")
        self._create_monitoring_task(self._monitor_file_changes(), "file_changes")
        self._create_monitoring_task(self._monitor_system_resources(), "system_resources")
        
        self._logger.info("Background monitoring started")
    
    def stop_monitoring(self):
        """Stop all background monitoring tasks."""
        if not self._monitoring_active:
            return
            
        self._monitoring_active = False
        
        # Cancel all running tasks
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
                
        self._monitoring_tasks.clear()
        self._logger.info("Background monitoring stopped")
    
    def _create_monitoring_task(self, coro: Awaitable, name: str) -> None:
        """
        Create and start a monitoring task.
        
        Args:
            coro: The coroutine to run as a task
            name: A name for the task (for logging)
        """
        task = asyncio.create_task(self._run_monitoring_task(coro, name))
        self._monitoring_tasks.add(task)
        task.add_done_callback(self._monitoring_tasks.discard)
    
    async def _run_monitoring_task(self, coro: Awaitable, name: str) -> None:
        """
        Run a monitoring task with error handling.
        
        Args:
            coro: The coroutine to run
            name: The task name
        """
        try:
            await coro
        except asyncio.CancelledError:
            self._logger.debug(f"Monitoring task {name} cancelled")
        except Exception as e:
            self._logger.exception(f"Error in monitoring task {name}: {str(e)}")
            
            # Restart the task after a delay
            await asyncio.sleep(30)
            if self._monitoring_active:
                self._logger.info(f"Restarting monitoring task {name}")
                if name == "git_status":
                    self._create_monitoring_task(self._monitor_git_status(), name)
                elif name == "file_changes":
                    self._create_monitoring_task(self._monitor_file_changes(), name)
                elif name == "system_resources":
                    self._create_monitoring_task(self._monitor_system_resources(), name)
    
    async def _monitor_git_status(self) -> None:
        """Monitor Git status in the current project."""
        self._logger.debug("Starting Git status monitoring")
        
        while self._monitoring_active:
            try:
                # Check if the current directory is a Git repository
                context = context_manager.get_context_dict()
                if not context.get("project_root"):
                    # No project detected, sleep and try again later
                    await asyncio.sleep(60)
                    continue
                
                project_root = Path(context["project_root"])
                git_dir = project_root / ".git"
                
                if not git_dir.exists():
                    # Not a Git repository, sleep and try again later
                    await asyncio.sleep(60)
                    continue
                
                # Check Git status
                result = await self._run_command("git status -s", cwd=str(project_root))
                
                if result["success"] and result["stdout"].strip():
                    # Check if this is different from the last status we saw
                    status_text = result["stdout"].strip()
                    
                    # Count changes
                    modified_count = status_text.count(" M ")
                    untracked_count = status_text.count("?? ")
                    deleted_count = status_text.count(" D ")
                    
                    # Analyze the status and suggest actions
                    if modified_count > 0 or untracked_count > 0 or deleted_count > 0:
                        suggestion_key = f"git_status:{modified_count}:{untracked_count}:{deleted_count}"
                        
                        if suggestion_key not in self._suggestions:
                            # Create a suggestion based on the status
                            suggestion = await self._generate_git_suggestion(
                                modified_count, 
                                untracked_count, 
                                deleted_count
                            )
                            
                            # Display the suggestion if possible
                            if suggestion and self._can_show_suggestion():
                                terminal_formatter.print_proactive_suggestion(suggestion, "Git Monitor")
                                self._suggestions.add(suggestion_key)
                                self._last_suggestion_time = datetime.now()
                
                # Wait before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                self._logger.exception(f"Error in Git status monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _monitor_file_changes(self) -> None:
        """Monitor file changes for syntax errors and linting issues."""
        self._logger.debug("Starting file changes monitoring")
        
        # Track the last modified time of each file
        last_modified_times = {}
        
        while self._monitoring_active:
            try:
                # Get current project context
                context = context_manager.get_context_dict()
                if not context.get("project_root"):
                    # No project detected, sleep and try again later
                    await asyncio.sleep(30)
                    continue
                
                project_root = Path(context["project_root"])
                
                # Scan for files that have changed
                changed_files = []
                
                for file_path in self._find_source_files(project_root):
                    try:
                        mtime = file_path.stat().st_mtime
                        
                        # Check if this file is newly modified
                        if file_path in last_modified_times:
                            if mtime > last_modified_times[file_path]:
                                changed_files.append(file_path)
                                last_modified_times[file_path] = mtime
                        else:
                            # New file we haven't seen before
                            last_modified_times[file_path] = mtime
                    except (FileNotFoundError, PermissionError):
                        # File may have been deleted or is inaccessible
                        if file_path in last_modified_times:
                            del last_modified_times[file_path]
                
                # Check changed files for issues
                for file_path in changed_files:
                    # Get file info
                    file_info = context_manager.get_file_info(file_path)
                    
                    # Check file based on language
                    if file_info.get("language") == "Python":
                        await self._check_python_file(file_path)
                    elif file_info.get("language") == "JavaScript":
                        await self._check_javascript_file(file_path)
                    # Add more language checks as needed
                
                # Wait before checking again
                await asyncio.sleep(10)
                
            except Exception as e:
                self._logger.exception(f"Error in file changes monitoring: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _monitor_system_resources(self) -> None:
        """Monitor system resources for potential issues."""
        self._logger.debug("Starting system resources monitoring")
        
        # Last values for comparison
        last_values = {
            "disk_usage": 0,
            "memory_usage": 0,
            "cpu_usage": 0
        }
        
        while self._monitoring_active:
            try:
                # Check disk space
                disk_usage = await self._get_disk_usage()
                if disk_usage > 90 and disk_usage > last_values["disk_usage"] + 5:
                    # Disk usage above 90% and increased by 5%
                    if self._can_show_suggestion():
                        suggestion = f"Your disk space is running low ({disk_usage}% used). Consider cleaning up unused files or moving data to free up space."
                        terminal_formatter.print_proactive_suggestion(suggestion, "System Monitor")
                        self._last_suggestion_time = datetime.now()
                last_values["disk_usage"] = disk_usage
                
                # Wait before checking again
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self._logger.exception(f"Error in system resources monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a shell command and return its output.
        
        Args:
            command: The command to run
            cwd: Optional working directory
            
        Returns:
            Dictionary with command results
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "command": command,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "success": process.returncode == 0
            }
        except Exception as e:
            self._logger.error(f"Error running command '{command}': {str(e)}")
            return {
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "success": False
            }
    
    def _find_source_files(self, base_dir: Path) -> List[Path]:
        """
        Find source code files in a directory.
        
        Args:
            base_dir: The base directory to search
            
        Returns:
            List of file paths
        """
        source_files = []
        
        # File extensions to look for
        extensions = {
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp",
            ".rs", ".go", ".rb", ".php", ".html", ".css", ".jsx", ".tsx"
        }
        
        # Directories to ignore
        ignore_dirs = {
            "__pycache__", "node_modules", ".git", "venv", "env",
            "build", "dist", "target", ".idea", ".vscode"
        }
        
        try:
            for root, dirs, files in os.walk(base_dir):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                
                for file in files:
                    file_ext = os.path.splitext(file)[1]
                    if file_ext in extensions:
                        source_files.append(Path(os.path.join(root, file)))
        except Exception as e:
            self._logger.error(f"Error finding source files: {str(e)}")
        
        return source_files
    
    async def _check_python_file(self, file_path: Path) -> None:
        """
        Check a Python file for syntax errors or linting issues.
        
        Args:
            file_path: Path to the Python file
        """
        # Check for syntax errors
        result = await self._run_command(f"python -m py_compile {file_path}")
        
        if not result["success"]:
            # Found a syntax error, generate a suggestion
            error_text = result["stderr"]
            suggestion_key = f"python_syntax:{file_path}"
            
            if suggestion_key not in self._suggestions and self._can_show_suggestion():
                # Extract the error message
                match = re.search(r"SyntaxError: (.*)", error_text)
                error_msg = match.group(1) if match else "syntax error"
                
                suggestion = f"Syntax error detected in {file_path.name}: {error_msg}"
                terminal_formatter.print_proactive_suggestion(suggestion, "File Monitor")
                self._suggestions.add(suggestion_key)
                self._last_suggestion_time = datetime.now()
        
        # Check with flake8 if available
        flake8_result = await self._run_command(f"flake8 {file_path}")
        
        if flake8_result["success"] and flake8_result["stdout"].strip():
            # Found linting issues
            suggestion_key = f"python_lint:{file_path}"
            
            if suggestion_key not in self._suggestions and self._can_show_suggestion():
                lint_issues = flake8_result["stdout"].strip().count('\n') + 1
                suggestion = f"Found {lint_issues} linting issues in {file_path.name}"
                terminal_formatter.print_proactive_suggestion(suggestion, "File Monitor")
                self._suggestions.add(suggestion_key)
                self._last_suggestion_time = datetime.now()
    
    async def _check_javascript_file(self, file_path: Path) -> None:
        """
        Check a JavaScript file for syntax errors or linting issues.
        
        Args:
            file_path: Path to the JavaScript file
        """
        # Check for syntax errors with Node.js
        result = await self._run_command(f"node --check {file_path}")
        
        if not result["success"]:
            # Found a syntax error, generate a suggestion
            error_text = result["stderr"]
            suggestion_key = f"js_syntax:{file_path}"
            
            if suggestion_key not in self._suggestions and self._can_show_suggestion():
                suggestion = f"Syntax error detected in {file_path.name}"
                terminal_formatter.print_proactive_suggestion(suggestion, "File Monitor")
                self._suggestions.add(suggestion_key)
                self._last_suggestion_time = datetime.now()
        
        # Check with ESLint if available
        eslint_result = await self._run_command(f"eslint {file_path}")
        
        if eslint_result["success"] and eslint_result["stdout"].strip():
            # Found linting issues
            suggestion_key = f"js_lint:{file_path}"
            
            if suggestion_key not in self._suggestions and self._can_show_suggestion():
                lint_issues = eslint_result["stdout"].strip().count('\n') + 1
                suggestion = f"Found {lint_issues} linting issues in {file_path.name}"
                terminal_formatter.print_proactive_suggestion(suggestion, "File Monitor")
                self._suggestions.add(suggestion_key)
                self._last_suggestion_time = datetime.now()
    
    async def _get_disk_usage(self) -> float:
        """
        Get disk usage percentage for the current directory.
        
        Returns:
            Disk usage percentage (0-100)
        """
        if sys.platform == "win32":
            # Windows
            result = await self._run_command("wmic logicaldisk get freespace,size")
            if result["success"]:
                lines = result["stdout"].strip().split('\n')
                if len(lines) >= 2:
                    values = lines[1].split()
                    if len(values) >= 2:
                        try:
                            free_space = int(values[0])
                            total_size = int(values[1])
                            return 100 - (free_space / total_size * 100)
                        except (ValueError, IndexError):
                            pass
            return 0
        else:
            # Unix-like
            result = await self._run_command("df -h .")
            if result["success"]:
                lines = result["stdout"].strip().split('\n')
                if len(lines) >= 2:
                    values = lines[1].split()
                    if len(values) >= 5:
                        try:
                            usage = values[4].rstrip('%')
                            return float(usage)
                        except (ValueError, IndexError):
                            pass
            return 0
    
    async def _generate_git_suggestion(
        self, 
        modified_count: int, 
        untracked_count: int, 
        deleted_count: int
    ) -> Optional[str]:
        """
        Generate a suggestion based on Git status.
        
        Args:
            modified_count: Number of modified files
            untracked_count: Number of untracked files
            deleted_count: Number of deleted files
            
        Returns:
            A suggestion string, or None if no suggestion is needed
        """
        total_changes = modified_count + untracked_count + deleted_count
        
        if total_changes <= 0:
            return None
            
        if total_changes > 10:
            return f"You have {total_changes} uncommitted changes in your Git repository. Consider committing your changes to avoid losing work."
            
        if modified_count > 0 and untracked_count > 0:
            return f"You have {modified_count} modified files and {untracked_count} untracked files. Consider using 'git add' to stage changes and 'git commit' to save your work."
            
        if modified_count > 0:
            return f"You have {modified_count} modified files that aren't committed. Use 'git commit' to save your changes."
            
        if untracked_count > 0:
            return f"You have {untracked_count} untracked files. Use 'git add' to begin tracking them."
            
        if deleted_count > 0:
            return f"You have {deleted_count} deleted files that haven't been committed. Use 'git commit' to record these deletions."
            
        return None
    
    def _can_show_suggestion(self) -> bool:
        """
        Check if we can show a suggestion now (respecting cooldown period).
        
        Returns:
            True if a suggestion can be shown, False otherwise
        """
        now = datetime.now()
        return (now - self._last_suggestion_time) >= self._suggestion_cooldown

# Global background monitor instance
background_monitor = BackgroundMonitor()
