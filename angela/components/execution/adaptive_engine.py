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

# Import through API layer - fixed imports
from angela.api.safety import get_command_risk_classifier, get_adaptive_confirmation
from angela.api.execution import get_execution_engine
from angela.api.context import get_history_manager, get_preferences_manager, get_session_manager
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
        self._error_analyzer = None # Initialize to None
    
    def _get_error_analyzer(self): # New helper method
        if self._error_analyzer is None:
            # Import through API layer
            from angela.api.ai import get_error_analyzer
            self._error_analyzer = get_error_analyzer()
        return self._error_analyzer
    
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
        classifier = get_command_risk_classifier()
        risk_level, risk_reason = classifier.classify(command)
        impact = classifier.analyze_impact(command)
        
        # Add to session context
        session_manager = get_session_manager()
        session_manager.add_command(command)
        
        # Generate command preview if needed
        preferences_manager = get_preferences_manager()
        
        preview = None
        if preferences_manager.preferences.ui.show_command_preview:
            from angela.api.safety import get_command_preview_generator
            preview_generator = get_command_preview_generator()
            preview = await preview_generator.generate_preview(command)
        
        # Get adaptive confirmation based on risk level and user history
        confirmation_handler = get_adaptive_confirmation()
        confirmed = await confirmation_handler(
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
        history_manager = get_history_manager()
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
            error_analyzer = self._get_error_analyzer()
            result["error_analysis"] = error_analyzer.analyze_error(command, result["stderr"])
            result["fix_suggestions"] = error_analyzer.generate_fix_suggestions(command, result["stderr"])
        
        # Offer to learn from successful executions
        if result["success"] and risk_level > 0:
            from angela.api.safety import offer_command_learning
            if offer_command_learning:
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
        preferences_manager = get_preferences_manager()
        use_spinners = preferences_manager.preferences.ui.use_spinners
        
        # For dry runs, return the preview directly
        if dry_run:
            # Get execution engine through API
            execution_engine = get_execution_engine()
            
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
        
        # Get execution engine through API
        execution_engine = get_execution_engine()
        
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
        session_manager = get_session_manager()
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
