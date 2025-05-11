# angela/execution/engine.py 
"""
Engine for safely executing commands.
"""
import asyncio
import shlex
import subprocess
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING

# Import through API layer
from angela.utils.logging import get_logger
from angela.core.registry import registry  # Fixed import

if TYPE_CHECKING:
    from angela.intent.models import ActionPlan
    
logger = get_logger(__name__)

class ExecutionEngine:
    """Engine for safely executing commands."""
    
    def __init__(self):
        """Initialize the execution engine."""
        self._logger = logger
    
    def _get_safety_check_function(self):
        """Get the safety check function with lazy imports to avoid circular dependencies."""
        # Use direct import here as a fallback if registry approach fails
        try:
            # Try registry first
            check_func = registry.get("check_command_safety")
            
            if check_func:
                return check_func
                
            # Direct import as fallback (should not normally happen once initialized)
            from angela.components.safety import check_command_safety
            return check_command_safety
        except ImportError:
            self._logger.error("Could not import safety check function")
            return None
    
    async def execute_command(
        self, 
        command: str,
        check_safety: bool = True,
        dry_run: bool = False
    ) -> Tuple[str, str, int]:
        """
        Execute a shell command and return its output.
        
        Args:
            command: The shell command to execute.
            check_safety: Whether to perform safety checks before execution.
            dry_run: Whether to simulate the command without actual execution.
            
        Returns:
            A tuple of (stdout, stderr, return_code).
        """
        self._logger.info(f"Preparing to execute command: {command}")
        
        # If safety checks are requested, perform them
        if check_safety:
            # Get safety check function using our helper method
            check_command_safety_func = self._get_safety_check_function()

            if not check_command_safety_func:
                self._logger.error("Safety check function not available")
                return "", "Safety check function not configured", 1

            # Check if the command is safe to execute
            is_safe = await check_command_safety_func(command, dry_run)
            if not is_safe:
                self._logger.warning(f"Command execution cancelled due to safety concerns: {command}")
                return "", "Command execution cancelled due to safety concerns", 1

            # For dry runs, return simulated results
            if dry_run:
                self._logger.info(f"DRY RUN: Would execute command: {command}")
                return f"[DRY RUN] Would execute: {command}", "", 0
        
        # Execute the command
        try:
            # Split the command properly using shlex
            args = shlex.split(command)
            
            # Execute the command and capture output
            if command.startswith('cd ') and ' && ' in command:
                # Extract working directory and actual command
                cd_part, actual_command = command.split(' && ', 1)
                working_dir = cd_part[3:].strip()  # Remove the 'cd ' prefix
                
                # Execute the actual command with the correct working directory
                process = await asyncio.create_subprocess_exec(
                    *shlex.split(actual_command),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_dir  # Set the working directory instead of using cd
                )
            else:
                # For regular commands without cd
                use_shell = '&&' in command or '|' in command or '>' in command or '<' in command
                
                if use_shell:
                    # Use shell mode for complex shell commands
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                else:
                    # For simple commands, use exec
                    process = await asyncio.create_subprocess_exec(
                        *shlex.split(command),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
            
            # Wait for the command to complete
            stdout_bytes, stderr_bytes = await process.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            self._logger.debug(f"Command completed with return code: {process.returncode}")
            self._logger.debug(f"stdout: {stdout[:100]}{'...' if len(stdout) > 100 else ''}")
            if stderr:
                self._logger.debug(f"stderr: {stderr}")
            
            # Record the operation for potential rollback
            if not dry_run and process.returncode == 0:
                # Get rollback_manager safely without circular imports
                try:
                    # Try getting from registry first 
                    rollback_manager_instance = registry.get("rollback_manager")
                    
                    if rollback_manager_instance:
                        await rollback_manager_instance.record_operation(
                            operation_type="execute_command",
                            params={"command": command},
                            backup_path=None  # Commands don't have direct file backups
                        )
                except Exception as e:
                    self._logger.warning(f"Could not record operation for rollback: {e}")
            
            return stdout, stderr, process.returncode
        
        except Exception as e:
            self._logger.exception(f"Error executing command '{command}': {str(e)}")
            return "", str(e), -1
    
    async def dry_run_command(self, command: str) -> Tuple[str, str, int]:
        """
        Simulate command execution for previewing without actually running the command.
        
        Args:
            command: The shell command to simulate
            
        Returns:
            A tuple of (stdout, stderr, return_code)
        """
        return f"[DRY RUN] Would execute: {command}", "", 0

# Global execution engine instance
execution_engine = ExecutionEngine()
