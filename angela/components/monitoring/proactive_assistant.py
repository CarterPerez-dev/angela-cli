# angela/monitoring/proactive_assistant.py
"""
Proactive Assistance V2 for Angela CLI.

This module provides enhanced monitoring and proactive suggestions 
based on combined context and system states. It integrates various
sources of information to offer intelligent, contextual assistance.
"""
import asyncio
import re
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable, Awaitable
from enum import Enum

from angela.core.registry import registry
from angela.utils.logging import get_logger
from angela.core.events import event_bus
from angela.api.shell import get_terminal_formatter
from angela.api.context import get_context_manager
from angela.api.context import get_session_manager
from angela.api.context import get_history_manager
from angela.api.ai import get_gemini_client, get_gemini_request_class
from angela.api.monitoring import get_background_monitor
from angela.api.execution import get_execution_hooks

logger = get_logger(__name__)

class AssistanceType(str, Enum):
    """Types of proactive assistance."""
    SUGGESTION = "suggestion"      # Suggest an action
    WARNING = "warning"            # Warn about a potential issue
    INSIGHT = "insight"            # Provide an insight or information
    OPTIMIZATION = "optimization"  # Suggest an optimization
    RECOVERY = "recovery"          # Suggest a recovery action
    AUTOMATION = "automation"      # Suggest automation or workflow

class AssistanceTrigger(str, Enum):
    """Triggers for proactive assistance."""
    ERROR = "error"                # Command error
    FILE_CHANGE = "file_change"    # File system change
    RESOURCE_USAGE = "resource"    # Resource usage threshold
    TIME_BASED = "time"            # Time-based trigger
    PATTERN = "pattern"            # Pattern in output or history
    COMPOUND = "compound"          # Multiple conditions

class ProactiveAssistant:
    """
    Enhanced proactive assistance system that monitors various aspects of
    system and user activity to provide timely, contextual suggestions.
    """
    
    def __init__(self):
        """Initialize the proactive assistant."""
        self._logger = logger
        self._recent_suggestions = set()  # To avoid repeating suggestions
        self._last_suggestion_time = datetime.now() - timedelta(hours=1)
        self._suggestion_cooldown = timedelta(minutes=3)
        
        # Registered insight handlers
        self._insight_handlers = {
            "git_status": self._handle_git_status_insight,
            "file_syntax_error": self._handle_file_syntax_error,
            "disk_space_low": self._handle_disk_space_insight,
            "python_syntax_error": self._handle_python_syntax_error,
            "javascript_syntax_error": self._handle_javascript_syntax_error,
            "test_failure": self._handle_test_failure_insight,
            "build_failure": self._handle_build_failure_insight,
            "deployment_issue": self._handle_deployment_issue_insight,
            "network_issue": self._handle_network_issue_insight,
            "security_alert": self._handle_security_alert_insight,
            "performance_issue": self._handle_performance_issue_insight,
            "dependency_update": self._handle_dependency_update_insight,
        }
        
        # Event tracking
        self._command_error_history = []
        self._pattern_detectors = []
        self._active_listening = False
        
        # Initialize pattern detectors
        self._setup_pattern_detectors()
    
    def start(self):
        """Start the proactive assistant."""
        from angela.api.monitoring import get_background_monitor
        from angela.api.execution import get_execution_hooks
        
        if self._active_listening:
            return
        
        self._active_listening = True
        
        # Subscribe to events
        event_bus.subscribe("monitoring:*", self._handle_monitoring_event)
        event_bus.subscribe("command:error", self._handle_command_error)
        event_bus.subscribe("command:executed", self._handle_command_executed)
        
        # Register with background monitor
        get_background_monitor().register_insight_callback(self._handle_monitor_insight)
        
        # Register with execution hooks - with error handling
        try:
            execution_hooks = get_execution_hooks()
            execution_hooks.register_hook("post_execute_command", self._post_execute_command_hook)
            self._logger.debug("Successfully registered post_execute_command hook")
        except Exception as e:
            self._logger.error(f"Error registering with execution hooks: {str(e)}")
        
        self._logger.info("Proactive assistant started")
    
    def stop(self):
        """Stop the proactive assistant."""
        from angela.api.monitoring import get_background_monitor
        from angela.api.execution import get_execution_hooks
        
        if not self._active_listening:
            return
        
        self._active_listening = False
        
        # Unsubscribe from events
        event_bus.unsubscribe("monitoring:*", self._handle_monitoring_event)
        event_bus.unsubscribe("command:error", self._handle_command_error)
        event_bus.unsubscribe("command:executed", self._handle_command_executed)
        
        # Unregister from background monitor
        get_background_monitor().unregister_insight_callback(self._handle_monitor_insight)
        
        # Unregister from execution hooks
        get_execution_hooks().unregister_hook("post_execute_command", self._post_execute_command_hook)
        
        self._logger.info("Proactive assistant stopped")
    
    def _setup_pattern_detectors(self):
        """Set up pattern detectors for command output."""
        # Add pattern detectors
        self._pattern_detectors = [
            {
                "name": "missing_dependency",
                "pattern": r"(?:command not found|No module named|cannot find module|Cannot find module|npm ERR! missing)",
                "handler": self._handle_missing_dependency_pattern
            },
            {
                "name": "permission_denied",
                "pattern": r"(?:Permission denied|EACCES|access is denied)",
                "handler": self._handle_permission_denied_pattern
            },
            {
                "name": "port_in_use",
                "pattern": r"(?:port \d+ is already in use|address already in use|EADDRINUSE)",
                "handler": self._handle_port_in_use_pattern
            },
            {
                "name": "api_rate_limit",
                "pattern": r"(?:rate limit exceeded|too many requests|429 Too Many Requests)",
                "handler": self._handle_api_rate_limit_pattern
            },
            {
                "name": "disk_full",
                "pattern": r"(?:No space left on device|disk quota exceeded|ENOSPC)",
                "handler": self._handle_disk_full_pattern
            },
            {
                "name": "network_unreachable",
                "pattern": r"(?:network is unreachable|could not resolve host|connection refused|ECONNREFUSED)",
                "handler": self._handle_network_unreachable_pattern
            },
            {
                "name": "outdated_cli",
                "pattern": r"(?:newer version|update available|outdated|deprecated)",
                "handler": self._handle_outdated_cli_pattern
            },
        ]
    
    async def _handle_monitoring_event(self, event_name: str, event_data: Dict[str, Any]):
        """
        Handle events from the monitoring system.
        
        Args:
            event_name: Name of the event
            event_data: Event data
        """
        self._logger.debug(f"Received monitoring event: {event_name}")
        
        # Extract insight type from event name
        parts = event_name.split(":")
        if len(parts) >= 2:
            insight_type = parts[1]
            
            # Check if we have a handler for this insight type
            handler = self._insight_handlers.get(insight_type)
            if handler:
                await handler(event_data)
    
    async def _handle_command_error(self, command: str, error: str, return_code: int):
        """
        Handle command error events.
        
        Args:
            command: The command that failed
            error: Error message
            return_code: Return code
        """
        self._logger.debug(f"Received command error event: {command}")
        
        # Add to error history
        self._command_error_history.append({
            "command": command,
            "error": error,
            "return_code": return_code,
            "timestamp": datetime.now()
        })
        
        # Limit history size
        if len(self._command_error_history) > 10:
            self._command_error_history = self._command_error_history[-10:]
        
        # Check for patterns in the error message
        for detector in self._pattern_detectors:
            if re.search(detector["pattern"], error, re.IGNORECASE):
                await detector["handler"](command, error, return_code)
    
    async def _handle_command_executed(self, command: str, output: str, return_code: int):
        """
        Handle command executed events.
        
        Args:
            command: The executed command
            output: Command output
            return_code: Return code
        """
        self._logger.debug(f"Received command executed event: {command}")
        
        # Check for successful test/build/deploy commands
        if return_code == 0:
            # Check for test command patterns
            test_patterns = [
                r"(?:pytest|unittest|jest|npm test|go test|rspec|gradle test|mvn test)",
                r"(?:run tests|running tests|test suite)"
            ]
            
            is_test_command = any(re.search(pattern, command, re.IGNORECASE) for pattern in test_patterns)
            
            if is_test_command:
                await self._handle_successful_tests(command, output)
            
            # Check for build command patterns
            build_patterns = [
                r"(?:npm run build|yarn build|go build|mvn package|gradle build)",
                r"(?:docker build|make build)"
            ]
            
            is_build_command = any(re.search(pattern, command, re.IGNORECASE) for pattern in build_patterns)
            
            if is_build_command:
                await self._handle_successful_build(command, output)
            
            # Check for deploy command patterns
            deploy_patterns = [
                r"(?:deploy|publish|release)",
                r"(?:kubectl apply|helm install|terraform apply)",
                r"(?:aws|gcloud|az)\s+(?:deploy|app|function)",
                r"(?:firebase deploy|vercel deploy|netlify deploy)"
            ]
            
            is_deploy_command = any(re.search(pattern, command, re.IGNORECASE) for pattern in deploy_patterns)
            
            if is_deploy_command:
                await self._handle_successful_deploy(command, output)
        
        # Check for patterns in the output
        for detector in self._pattern_detectors:
            if re.search(detector["pattern"], output, re.IGNORECASE):
                await detector["handler"](command, output, return_code)
    
    async def _post_execute_command_hook(self, command: str, result: Dict[str, Any], context: Dict[str, Any]):
        """
        Hook called after a command is executed.
        
        Args:
            command: The executed command
            result: Execution result
            context: Execution context
        """
        self._logger.debug(f"Post-execute command hook: {command}")
        
        # Check for success/failure
        success = result.get("success", False)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        
        if success:
            # Publish successful command event
            await event_bus.publish("command:executed", {
                "command": command,
                "output": stdout,
                "return_code": result.get("return_code", 0)
            })
        else:
            # Publish command error event
            await event_bus.publish("command:error", {
                "command": command,
                "error": stderr,
                "return_code": result.get("return_code", -1)
            })
        
        # Check for optimization opportunities in successful commands
        if success and self._can_show_suggestion():
            # Check for repeated commands
            await self._check_for_repeated_commands(command)
            
            # Check for inefficient command patterns
            await self._check_for_inefficient_patterns(command)
    
    async def _handle_monitor_insight(self, insight_type: str, insight_data: Dict[str, Any]):
        """
        Handle insights from background monitoring.
        
        Args:
            insight_type: Type of insight
            insight_data: Insight data
        """
        self._logger.debug(f"Received monitor insight: {insight_type}")
        
        # Check if we have a handler for this insight type
        handler = self._insight_handlers.get(insight_type)
        if handler:
            await handler(insight_data)
    
    async def _handle_git_status_insight(self, insight_data: Dict[str, Any]):
        """
        Handle git status insights.
        
        Args:
            insight_data: Insight data
        """
        from angela.api.shell import get_terminal_formatter
        
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"git_status:{insight_data.get('modified_count', 0)}:{insight_data.get('untracked_count', 0)}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        get_terminal_formatter().print_proactive_suggestion(suggestion, "Git Status")
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_file_syntax_error(self, insight_data: Dict[str, Any]):
        """
        Handle file syntax error insights.
        
        Args:
            insight_data: Insight data
        """
        from angela.api.shell import get_terminal_formatter
        
        if not self._can_show_suggestion():
            return
        
        file_path = insight_data.get("file_path")
        error_message = insight_data.get("error_message", "syntax error")
        
        if not file_path:
            return
        
        # Check if we've seen this error recently
        suggestion_key = f"syntax_error:{file_path}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Generate suggestion
        suggestion = f"Syntax error detected in {Path(file_path).name}: {error_message}"
        
        # Show the suggestion
        get_terminal_formatter().print_proactive_suggestion(
            suggestion, 
            "File Error", 
            "Consider fixing this error to avoid compilation/runtime issues."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_disk_space_insight(self, insight_data: Dict[str, Any]):
        """
        Handle disk space insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        disk_usage = insight_data.get("disk_usage", 0)
        suggestion_key = f"disk_space:{int(disk_usage // 5) * 5}"  # Round to nearest 5%
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Disk Space Warning", 
            "You might want to free up space to avoid issues."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_python_syntax_error(self, insight_data: Dict[str, Any]):
        """
        Handle Python syntax error insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        file_path = insight_data.get("file_path")
        if not file_path:
            return
        
        # Check if we've seen this error recently
        suggestion_key = f"python_syntax:{file_path}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Python Syntax Error", 
            "Fix this error to ensure your Python code runs correctly."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_javascript_syntax_error(self, insight_data: Dict[str, Any]):
        """
        Handle JavaScript syntax error insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        file_path = insight_data.get("file_path")
        if not file_path:
            return
        
        # Check if we've seen this error recently
        suggestion_key = f"js_syntax:{file_path}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "JavaScript Syntax Error", 
            "Fix this error to ensure your JavaScript code runs correctly."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
        await self._notify_insight_callbacks("javascript_syntax_error", insight_data)    
    
    async def _handle_test_failure_insight(self, insight_data: Dict[str, Any]):
        """
        Handle test failure insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"test_failure:{insight_data.get('test_file', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Get recent commits to enhance suggestion
        recent_commit_message = None
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "log", "-1", "--pretty=%s",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0:
                recent_commit_message = stdout.decode('utf-8').strip()
        except Exception:
            pass
        
        if recent_commit_message:
            enhanced_suggestion = f"{suggestion}\n\nTests failed after your recent commit: '{recent_commit_message}'"
            suggestion = enhanced_suggestion
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Test Failure", 
            "Would you like me to help troubleshoot this test failure?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
  
        await self._notify_insight_callbacks("test_failure", insight_data)  
  
    
    async def _handle_build_failure_insight(self, insight_data: Dict[str, Any]):
        """
        Handle build failure insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"build_failure:{insight_data.get('build_id', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Build Failure", 
            "Need help debugging this build issue?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()

        await self._notify_insight_callbacks("build_failure", insight_data)
    
    async def _handle_deployment_issue_insight(self, insight_data: Dict[str, Any]):
        """
        Handle deployment issue insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"deployment_issue:{insight_data.get('deployment_id', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Deployment Issue", 
            "I can help diagnose and fix this deployment problem."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()

        await self._notify_insight_callbacks("deployment_issue", insight_data)

    
    async def _handle_network_issue_insight(self, insight_data: Dict[str, Any]):
        """
        Handle network issue insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"network_issue:{insight_data.get('service', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Network Issue", 
            "Would you like me to diagnose the network problem?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
        
        await self._notify_insight_callbacks("network_issue", insight_data)
    
    async def _handle_security_alert_insight(self, insight_data: Dict[str, Any]):
        """
        Handle security alert insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Security alerts are important, always show them
        # with a shorter cooldown
        has_shorter_cooldown = (datetime.now() - self._last_suggestion_time) >= timedelta(seconds=30)
        
        if not has_shorter_cooldown:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"security_alert:{insight_data.get('issue_type', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion with high visibility
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "⚠️ Security Alert ⚠️", 
            "This security issue requires immediate attention!",
            style="bold red on yellow"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()

        await self._notify_insight_callbacks("security_alert", insight_data)
    
    async def _handle_performance_issue_insight(self, insight_data: Dict[str, Any]):
        """
        Handle performance issue insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"performance_issue:{insight_data.get('resource', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Performance Issue", 
            "I can suggest optimizations to improve performance."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()


        await self._notify_insight_callbacks("performance_issue", insight_data)
    
    async def _handle_dependency_update_insight(self, insight_data: Dict[str, Any]):
        """
        Handle dependency update insights.
        
        Args:
            insight_data: Insight data
        """
        if not self._can_show_suggestion():
            return
        
        suggestion = insight_data.get("suggestion")
        if not suggestion:
            return
        
        # Check if we've seen this suggestion recently
        suggestion_key = f"dependency_update:{insight_data.get('package', 'unknown')}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Dependency Update Available", 
            "Would you like me to update this dependency for you?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()

        await self._notify_insight_callbacks("dependency_update", insight_data)

    
    async def _handle_missing_dependency_pattern(self, command: str, output: str, return_code: int):
        """
        Handle missing dependency pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = f"missing_dependency:{command}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Try to extract the missing dependency
        dependency = None
        
        # Common patterns for different package managers
        dependency_patterns = [
            # npm/yarn
            r"npm ERR! missing:.*?([a-zA-Z0-9_\-\./@]+)@",
            # pip/python
            r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]",
            # Command not found
            r"command not found: ([a-zA-Z0-9_\-\.]+)",
            # Go
            r"cannot find package \"([a-zA-Z0-9_\-\./]+)\"",
            # General
            r"(?:missing|not found|cannot find).*?([a-zA-Z0-9_\-\./@:]+)"
        ]
        
        for pattern in dependency_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                dependency = match.group(1)
                break
        
        # Generate suggestion based on the command and output
        if dependency:
            suggestion = f"It looks like you're missing the dependency: {dependency}"
            
            # Try to determine the command to install it
            install_cmd = None
            
            if "npm" in command.lower() or "node" in command.lower():
                install_cmd = f"npm install {dependency}"
            elif "yarn" in command.lower():
                install_cmd = f"yarn add {dependency}"
            elif "pip" in command.lower() or "python" in command.lower():
                install_cmd = f"pip install {dependency}"
            elif "go" in command.lower():
                install_cmd = f"go get {dependency}"
            
            if install_cmd:
                suggestion += f"\n\nYou can install it with:\n{install_cmd}"
        else:
            # Generic suggestion
            suggestion = "It looks like you're missing a dependency needed for this command."
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Missing Dependency", 
            "Would you like me to install the missing dependency?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_permission_denied_pattern(self, command: str, output: str, return_code: int):
        """
        Handle permission denied pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = f"permission_denied:{command}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Try to extract the file/directory with permission issue
        path = None
        
        path_pattern = r"[Pp]ermission denied.*?['\"]?([/\w\-\.]+)['\"]?"
        match = re.search(path_pattern, output, re.IGNORECASE)
        if match:
            path = match.group(1)
        
        # Generate suggestion based on the command and output
        if path:
            suggestion = f"Permission denied for: {path}"
            suggestion += "\n\nYou might need to run the command with sudo or adjust permissions."
            suggestion += f"\nTry: sudo {command}"
            
            if "r" in output.lower():
                suggestion += f"\n\nOr change permissions: chmod +r {path}"
            
            if "w" in output.lower():
                suggestion += f"\n\nOr change permissions: chmod +w {path}"
            
            if "x" in output.lower():
                suggestion += f"\n\nOr change permissions: chmod +x {path}"
        else:
            # Generic suggestion
            suggestion = "You don't have sufficient permissions to run this command."
            suggestion += f"\n\nYou might need to use sudo: sudo {command}"
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Permission Denied", 
            "Need help fixing this permission issue?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_port_in_use_pattern(self, command: str, output: str, return_code: int):
        """
        Handle port in use pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Try to extract the port number
        port = None
        
        port_pattern = r"port (\d+)|:(\d+).*?(?:already in use|EADDRINUSE)"
        match = re.search(port_pattern, output, re.IGNORECASE)
        if match:
            port = match.group(1) or match.group(2)
        
        # Check if we've seen this pattern recently
        suggestion_key = f"port_in_use:{port or 'unknown'}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Generate suggestion based on the command and output
        if port:
            suggestion = f"Port {port} is already in use by another process."
            suggestion += "\n\nYou can find the process using this port with:"
            
            if "linux" in sys.platform or "darwin" in sys.platform:
                suggestion += f"\nlsof -i :{port}"
            elif "win" in sys.platform:
                suggestion += f"\nnetstat -ano | findstr :{port}"
            
            suggestion += "\n\nOr you can use a different port in your command."
        else:
            # Generic suggestion
            suggestion = "A port is already in use by another process."
            suggestion += "\n\nYou can try using a different port in your command."
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Port Already In Use", 
            "Need help resolving this port conflict?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_api_rate_limit_pattern(self, command: str, output: str, return_code: int):
        """
        Handle API rate limit pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = "api_rate_limit"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Generate suggestion
        suggestion = "You've hit an API rate limit."
        suggestion += "\n\nTips for handling rate limits:"
        suggestion += "\n1. Wait and retry later"
        suggestion += "\n2. Implement exponential backoff"
        suggestion += "\n3. Check if authentication would increase your rate limit"
        suggestion += "\n4. Consider caching responses to reduce API calls"
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "API Rate Limit Exceeded", 
            "Would you like me to create a retry script with backoff?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_disk_full_pattern(self, command: str, output: str, return_code: int):
        """
        Handle disk full pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = "disk_full"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Generate suggestion
        suggestion = "You've run out of disk space."
        suggestion += "\n\nCommands to help free up space:"
        suggestion += "\n1. df -h (check disk usage)"
        suggestion += "\n2. du -h --max-depth=1 (find large directories)"
        suggestion += "\n3. find . -type f -size +100M (find large files)"
        suggestion += "\n4. rm -rf ~/.cache/* (clear cache files)"
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Disk Full", 
            "Would you like me to help you free up disk space?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_network_unreachable_pattern(self, command: str, output: str, return_code: int):
        """
        Handle network unreachable pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = "network_unreachable"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Try to extract the host/URL
        host = None
        
        host_pattern = r"(?:host|resolve|connect to|unreachable)[:\s]+([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})"
        match = re.search(host_pattern, output, re.IGNORECASE)
        if match:
            host = match.group(1)
        
        # Generate suggestion
        if host:
            suggestion = f"Unable to reach {host}. This might be due to network connectivity issues."
        else:
            suggestion = "You're experiencing network connectivity issues."
        
        suggestion += "\n\nCommands to diagnose network problems:"
        suggestion += "\n1. ping google.com (check basic connectivity)"
        suggestion += "\n2. nslookup example.com (check DNS resolution)"
        suggestion += "\n3. traceroute example.com (check routing)"
        suggestion += "\n4. curl -I https://example.com (check HTTP connectivity)"
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Network Connectivity Issue", 
            "Would you like me to help diagnose the network problem?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_outdated_cli_pattern(self, command: str, output: str, return_code: int):
        """
        Handle outdated CLI tool pattern.
        
        Args:
            command: The command that was executed
            output: Command output
            return_code: Return code
        """
        if not self._can_show_suggestion():
            return
        
        # Extract tool name from command
        tool = command.split()[0] if command else "tool"
        
        # Check if we've seen this pattern recently
        suggestion_key = f"outdated_cli:{tool}"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Generate suggestion
        suggestion = f"Your {tool} CLI tool has an update available."
        suggestion += "\n\nCommon update commands:"
        
        if tool == "npm":
            suggestion += "\nnpm install -g npm@latest"
        elif tool == "pip":
            suggestion += "\npip install --upgrade pip"
        elif tool == "yarn":
            suggestion += "\nnpm install -g yarn@latest"
        elif tool == "docker":
            suggestion += "\nRefer to https://docs.docker.com/engine/install/ for update instructions"
        elif tool == "kubectl":
            suggestion += "\nRefer to https://kubernetes.io/docs/tasks/tools/install-kubectl/ for update instructions"
        elif tool == "aws":
            suggestion += "\npip install --upgrade awscli"
        elif tool == "gcloud":
            suggestion += "\ngcloud components update"
        else:
            suggestion += f"\nCheck the {tool} documentation for update instructions"
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Update Available", 
            f"Would you like me to update the {tool} CLI tool?"
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_successful_tests(self, command: str, output: str):
        """
        Handle successful test command execution.
        
        Args:
            command: The test command
            output: Command output
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = "successful_tests"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Extract test statistics if possible
        test_count = None
        time_taken = None
        coverage = None
        
        # Common patterns for test output
        test_count_pattern = r"(?:Ran|Running|Executed) (\d+) tests?"
        time_pattern = r"(?:in|finished in|took) ([0-9\.]+)s?"
        coverage_pattern = r"(?:Coverage|coverage)[^0-9]*?([0-9\.]+%)"
        
        test_match = re.search(test_count_pattern, output, re.IGNORECASE)
        time_match = re.search(time_pattern, output, re.IGNORECASE)
        coverage_match = re.search(coverage_pattern, output, re.IGNORECASE)
        
        if test_match:
            test_count = test_match.group(1)
        if time_match:
            time_taken = time_match.group(1)
        if coverage_match:
            coverage = coverage_match.group(1)
        
        # Generate suggestion
        suggestion = "🎉 All tests passed successfully!"
        
        if test_count:
            suggestion += f"\n\nRan {test_count} tests"
        if time_taken:
            suggestion += f" in {time_taken}s"
        if coverage:
            suggestion += f"\nTest coverage: {coverage}"
        
        # Add project context if CI/CD is not set up
        context = context_manager.get_context_dict()
        project_type = context.get("project_type")
        
        ci_files = [
            ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", 
            ".travis.yml", ".circleci"
        ]
        
        has_ci = any(Path(context.get("project_root", ".")).glob(ci_file) for ci_file in ci_files)
        
        if not has_ci and project_type:
            suggestion += "\n\nConsider setting up CI/CD to automate testing."
            suggestion += "\nI can help you create a CI/CD configuration for GitHub Actions, GitLab CI, or Jenkins."
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Tests Passed", 
            "Great job! Your code is working as expected."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_successful_build(self, command: str, output: str):
        """
        Handle successful build command execution.
        
        Args:
            command: The build command
            output: Command output
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = "successful_build"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Generate suggestion
        suggestion = "🔨 Build completed successfully!"
        
        # Extract build time if available
        time_pattern = r"(?:in|finished in|took|time) ([0-9\.]+)s?"
        time_match = re.search(time_pattern, output, re.IGNORECASE)
        
        if time_match:
            suggestion += f"\nBuild took {time_match.group(1)}s"
        
        # Check if tests were run as part of the build
        has_tests = "test" in output.lower() or "spec" in output.lower()
        
        if has_tests:
            suggestion += "\nTests were included in the build and passed"
        
        # Check if deployment might be next
        context = context_manager.get_context_dict()
        recent_commands = context.get("session", {}).get("recent_commands", [])
        
        has_recent_test = any("test" in cmd for cmd in recent_commands[-5:]) if recent_commands else False
        
        if has_recent_test:
            suggestion += "\n\nYour tests and build have both succeeded. Would you like to deploy?"
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Build Succeeded", 
            "Your code has built successfully."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _handle_successful_deploy(self, command: str, output: str):
        """
        Handle successful deploy command execution.
        
        Args:
            command: The deploy command
            output: Command output
        """
        if not self._can_show_suggestion():
            return
        
        # Check if we've seen this pattern recently
        suggestion_key = "successful_deploy"
        
        if suggestion_key in self._recent_suggestions:
            return
        
        # Try to extract the deployment URL or environment
        url_pattern = r"(?:deployed to|available at|url|http)[:\s]+(https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}[^\s]*)"
        env_pattern = r"(?:deployed to|environment|env)[:\s]+([a-zA-Z0-9\-\_]+)"
        
        url_match = re.search(url_pattern, output, re.IGNORECASE)
        env_match = re.search(env_pattern, output, re.IGNORECASE)
        
        # Generate suggestion
        suggestion = "🚀 Deployment completed successfully!"
        
        if url_match:
            url = url_match.group(1)
            suggestion += f"\n\nYour application is available at: {url}"
        
        if env_match:
            env = env_match.group(1)
            suggestion += f"\n\nDeployed to environment: {env}"
        
        # Check if monitoring should be suggested
        has_monitoring_terms = any(term in output.lower() for term in ["monitor", "logging", "metrics", "health"])
        
        if not has_monitoring_terms:
            suggestion += "\n\nDon't forget to monitor your deployment for any issues."
            suggestion += "\nI can help you set up monitoring tools if needed."
        
        # Show the suggestion
        terminal_formatter.print_proactive_suggestion(
            suggestion, 
            "Deployment Succeeded", 
            "Your application has been deployed successfully."
        )
        
        # Remember this suggestion
        self._recent_suggestions.add(suggestion_key)
        self._last_suggestion_time = datetime.now()
    
    async def _check_for_repeated_commands(self, command: str):
        """
        Check for repeated commands and suggest workflow automation.
        
        Args:
            command: The command that was executed
        """
        from angela.api.context import get_history_manager
        from angela.api.shell import get_terminal_formatter
        
        # Get recent commands
        recent_commands = get_history_manager().get_recent_commands(limit=20)
        if not recent_commands:
            return
        
        # Count occurrences of the current command
        command_count = sum(1 for cmd in recent_commands if cmd == command)
        
        # If command has been repeated multiple times, suggest workflow
        if command_count >= 3:
            # Check if we've seen this pattern recently
            suggestion_key = f"repeated_command:{command}"
            
            if suggestion_key in self._recent_suggestions:
                return
            
            # Generate suggestion
            suggestion = f"I noticed you've run this command {command_count} times:"
            suggestion += f"\n{command}"
            suggestion += "\n\nWould you like me to create a workflow for this task?"
            suggestion += "\nYou can then run it with a simple command like: angela run my-workflow"
            
            # Show the suggestion
            get_terminal_formatter().print_proactive_suggestion(
                suggestion, 
                "Workflow Opportunity", 
                "I can automate this repeated command for you."
            )
            
            # Remember this suggestion
            self._recent_suggestions.add(suggestion_key)
            self._last_suggestion_time = datetime.now()
    
    async def _check_for_inefficient_patterns(self, command: str):
        """
        Check for inefficient command patterns and suggest optimizations.
        
        Args:
            command: The command that was executed
        """
        # Define patterns to check and their optimizations
        inefficient_patterns = [
            {
                "pattern": r"find\s+.+?\s+-name\s+.+?\s+\|\s+xargs",
                "suggestion": "You can use 'find -exec' instead of piping to xargs for better handling of filenames with spaces:\nfind . -name '*.txt' -exec command {} \\;",
                "key": "find_xargs"
            },
            {
                "pattern": r"grep\s+.+?\s+\|\s+grep",
                "suggestion": "You can combine multiple grep patterns with the -e option:\ngrep -e 'pattern1' -e 'pattern2' file.txt",
                "key": "grep_pipe"
            },
            {
                "pattern": r"cat\s+.+?\s+\|\s+grep",
                "suggestion": "You can use grep directly on the file for better performance:\ngrep 'pattern' file.txt",
                "key": "cat_grep"
            },
            {
                "pattern": r"sort\s+.+?\s+\|\s+uniq",
                "suggestion": "You can use 'sort -u' to sort and get unique lines in one command:\nsort -u file.txt",
                "key": "sort_uniq"
            }
        ]
        
        # Check each pattern
        for pattern_info in inefficient_patterns:
            if re.search(pattern_info["pattern"], command, re.IGNORECASE):
                # Check if we've seen this pattern recently
                suggestion_key = f"inefficient_pattern:{pattern_info['key']}"
                
                if suggestion_key in self._recent_suggestions:
                    continue
                
                # Generate suggestion
                suggestion = "I noticed a command pattern that could be optimized:"
                suggestion += f"\n{command}"
                suggestion += f"\n\n{pattern_info['suggestion']}"
                
                # Show the suggestion
                terminal_formatter.print_proactive_suggestion(
                    suggestion, 
                    "Command Optimization", 
                    "Here's a more efficient way to achieve the same result."
                )
                
                # Remember this suggestion
                self._recent_suggestions.add(suggestion_key)
                self._last_suggestion_time = datetime.now()
                
                # Only show one suggestion at a time
                break
    
    def _can_show_suggestion(self) -> bool:
        """
        Check if we can show a suggestion right now (respecting cooldown).
        
        Returns:
            True if a suggestion can be shown, False otherwise
        """
        return (datetime.now() - self._last_suggestion_time) >= self._suggestion_cooldown
    
    def get_suggestion_opportunity(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if there's an opportunity for a proactive suggestion.
        
        This method is called by the orchestrator before processing a request
        to see if there's a proactive suggestion that could be offered.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Suggestion opportunity data or None
        """
        # Implement proactive suggestion opportunities
        # For example, suggesting CI/CD setup for repositories without it
        # This would require access to the project context, history, etc.
        return None

# Global instance
proactive_assistant = ProactiveAssistant()
