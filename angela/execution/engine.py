# angela/execution/engine.py 
"""
Engine for safely executing commands.
"""
import asyncio
import shlex
import subprocess
from typing import Dict, Any, List, Tuple, Optional

from angela.utils.logging import get_logger
from angela.intent.models import ActionPlan
from angela.core.registry import registry

logger = get_logger(__name__)

class ExecutionEngine:
    """Engine for safely executing commands."""
    
    def __init__(self):
        """Initialize the execution engine."""
        self._logger = logger
    
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
            # Get check_command_safety function from registry to avoid circular import
            check_command_safety = registry.get("check_command_safety")
            
            # Check if the command is safe to execute
            is_safe = await check_command_safety(command, dry_run)
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
            process = await asyncio.create_subprocess_exec(
                *args,
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
                # Get rollback_manager from registry to avoid circular import
                rollback_manager = registry.get("rollback_manager")
                if rollback_manager:
                    await rollback_manager.record_operation(
                        operation_type="execute_command",
                        params={"command": command},
                        backup_path=None  # Commands don't have direct file backups
                    )
            
            return stdout, stderr, process.returncode
        
        except Exception as e:
            self._logger.exception(f"Error executing command '{command}': {str(e)}")
            return "", str(e), -1

# Global execution engine instance
execution_engine = ExecutionEngine()
