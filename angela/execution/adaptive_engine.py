# angela/execution/adaptive_engine.py

import asyncio
import os
import sys
import signal
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from angela.safety.classifier import classify_command_risk, analyze_command_impact
from angela.safety.adaptive_confirmation import get_adaptive_confirmation
from angela.execution.engine import execution_engine
from angela.context.history import history_manager
from angela.context.preferences import preferences_manager
from angela.context.session import session_manager
from angela.ai.analyzer import error_analyzer
from angela.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

class AdaptiveExecutionEngine:
    """
    Context-aware command execution engine.
    
    This engine adapts its behavior based on user history, preferences,
    and command characteristics.
    """
    
    def __init__(self):
        """Initialize the adaptive execution engine."""
        self._logger = logger
    
    async def execute_command(
        self, 
        command: str,
        natural_request: str,
        explanation: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a command with adaptive behavior based on user context.
        
        Args:
            command: The command to execute
            natural_request: The original natural language request
            explanation: AI explanation of what the command does
            dry_run: Whether to simulate the command without execution
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Preparing to execute command: {command}")
        
        # Analyze command risk and impact
        risk_level, risk_reason = classify_command_risk(command)
        impact = analyze_command_impact(command)
        
        # Add to session context
        session_manager.add_command(command)
        
        # Generate command preview if needed
        from angela.safety.preview import generate_preview
        preview = await generate_preview(command) if preferences_manager.preferences.ui.show_command_preview else None
        
        # Get adaptive confirmation based on risk level and user history
        confirmed = await get_adaptive_confirmation(
            command=command,
            risk_level=risk_level,
            risk_reason=risk_reason,
            impact=impact,
            preview=preview,
            explanation=explanation,
            natural_request=natural_request,
            dry_run=dry_run
        )
        
        if not confirmed and not dry_run:
            self._logger.info(f"Command execution cancelled by user: {command}")
            return {
                "command": command,
                "success": False,
                "cancelled": True,
                "stdout": "",
                "stderr": "Command execution cancelled by user",
                "return_code": 1,
                "dry_run": dry_run
            }
        
        # Execute the command
        result = await self._execute_with_feedback(command, dry_run)
        
        # Add to history
        history_manager.add_command(
            command=command,
            natural_request=natural_request,
            success=result["success"],
            output=result.get("stdout", ""),
            error=result.get("stderr", ""),
            risk_level=risk_level
        )
        
        # If execution failed, analyze error and suggest fixes
        if not result["success"] and result.get("stderr"):
            result["error_analysis"] = error_analyzer.analyze_error(command, result["stderr"])
            result["fix_suggestions"] = error_analyzer.generate_fix_suggestions(command, result["stderr"])
        
        # Offer to learn from successful executions
        if result["success"] and risk_level > 0:
            from angela.safety.adaptive_confirmation import offer_command_learning
            await offer_command_learning(command)
        
        return result
    
    async def _execute_with_feedback(self, command: str, dry_run: bool) -> Dict[str, Any]:
        """
        Execute a command with rich feedback.
        
        Args:
            command: The command to execute
            dry_run: Whether to simulate the command without execution
            
        Returns:
            Dictionary with execution results
        """
        use_spinners = preferences_manager.preferences.ui.use_spinners
        
        # For dry runs, return the preview directly
        if dry_run:
            # Execute in dry-run mode
            stdout, stderr, return_code = await execution_engine.dry_run_command(command)
            
            return {
                "command": command,
                "success": True,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "dry_run": True
            }
        
        # Show execution spinner if enabled
        if use_spinners:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Executing command...[/bold blue]"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Executing", total=None)
                
                # Execute the command
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command,
                    check_safety=False  # We've already done safety checks
                )
                
                # Complete the progress
                progress.update(task, completed=True)
        else:
            # Execute without spinner
            console.print("[bold blue]Executing command...[/bold blue]")
            stdout, stderr, return_code = await execution_engine.execute_command(
                command,
                check_safety=False  # We've already done safety checks
            )
        
        # Store result in session for reference
        if stdout.strip():
            session_manager.add_result(stdout.strip())
        
        return {
            "command": command,
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "dry_run": False
        }

# Global adaptive execution engine instance
adaptive_engine = AdaptiveExecutionEngine()
