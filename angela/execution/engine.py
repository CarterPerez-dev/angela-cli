"""
Engine for safely executing commands.

This module provides the core functionality for command execution with 
safety checks, dry-run capabilities, and execution tracking.
"""
import asyncio
import shlex
import subprocess
from typing import Dict, Any, List, Tuple, Optional

from angela.utils.logging import get_logger
from angela.intent.models import ActionPlan

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
            # Import here to avoid circular imports
            from angela.safety import check_command_safety
            
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
                from angela.execution.rollback import rollback_manager
                await rollback_manager.record_operation(
                    operation_type="execute_command",
                    params={"command": command},
                    backup_path=None  # Commands don't have direct file backups
                )
            
            return stdout, stderr, process.returncode
        
        except Exception as e:
            self._logger.exception(f"Error executing command '{command}': {str(e)}")
            return "", str(e), -1
    
    async def execute_plan(
        self, 
        plan: ActionPlan,
        check_safety: bool = True,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute an action plan and return the results.
        
        Args:
            plan: The action plan to execute.
            check_safety: Whether to perform safety checks before execution.
            dry_run: Whether to simulate the commands without actual execution.
            
        Returns:
            A list of execution results, one for each command in the plan.
        """
        results = []
        
        for i, command in enumerate(plan.commands):
            explanation = plan.explanations[i] if i < len(plan.explanations) else ""
            
            # Execute the command with safety checks if requested
            stdout, stderr, return_code = await self.execute_command(
                command, 
                check_safety=check_safety,
                dry_run=dry_run
            )
            
            # Record the result
            result = {
                "command": command,
                "explanation": explanation,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "success": return_code == 0,
                "dry_run": dry_run
            }
            
            results.append(result)
            
            # If a command fails, stop executing the plan
            if return_code != 0 and not dry_run:
                self._logger.warning(f"Stopping plan execution due to command failure: {command}")
                break
        
        return results
    
    async def dry_run_command(self, command: str) -> Tuple[str, str, int]:
        """
        Perform a dry run of a command without executing it.
        
        Args:
            command: The shell command to simulate.
            
        Returns:
            A tuple of (simulated_stdout, simulated_stderr, return_code).
        """
        # Import here to avoid circular imports
        from angela.safety.preview import generate_preview
        
        preview = await generate_preview(command)
        
        if preview:
            return preview, "", 0
        else:
            return f"[DRY RUN] Would execute: {command}", "", 0

# Global execution engine instance
execution_engine = ExecutionEngine()
