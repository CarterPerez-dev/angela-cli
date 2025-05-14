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
from angela.api.shell import get_terminal_formatter

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
    
    # In the execute_command method of AdaptiveExecutionEngine
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
        # Add interactive command check near the beginning of the method
        from angela.utils.command_utils import is_interactive_command, display_command_recommendation
        
        is_interactive, base_cmd = is_interactive_command(command)
        if is_interactive and not dry_run:
            # Display recommendation for interactive commands
            display_command_recommendation(command)
            
            # Return result without execution
            return {
                "command": command,
                "success": True,
                "recommendation_only": True,
                "stdout": f"Interactive command '{base_cmd}' not executed - please run manually",
                "stderr": "",
                "return_code": 0,
                "execution_time": 0.1,
                "dry_run": False
            }
        

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
        
        # Get confidence score if available
        confidence_score = None
        try:
            from angela.api.ai import get_confidence_scorer
            confidence_scorer = get_confidence_scorer()
            context = {"request": natural_request}
            confidence_score = confidence_scorer.score_command_confidence(natural_request, command, context)
        except Exception as e:
            self._logger.error(f"Error calculating confidence score: {str(e)}")
        
        # Prepare full information to display before confirmation
        command_info = {
            "command": command,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "impact": impact,
            "preview": preview,
            "explanation": explanation,
            "confidence_score": confidence_score,
            "dry_run": dry_run
        }
        
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
            dry_run=dry_run,
            confidence_score=confidence_score,  # Pass the confidence score
            command_info=command_info          # Pass the command info
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
                "dry_run": dry_run,
                "confidence": confidence_score  # Include confidence in result
            }
        
        # Execute the command
        result = await self._execute_with_feedback(command, dry_run)
        
        # Add confidence score to the result
        result["confidence"] = confidence_score
        
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
        Execute a command with rich feedback, handling interactive commands.
        
        Args:
            command: The command to execute
            dry_run: Whether to simulate the command without execution
            
        Returns:
            Dictionary with execution results
        """
        # Get preferences manager to check for UI preferences
        preferences_manager = get_preferences_manager()
        use_spinners = preferences_manager.preferences.ui.use_spinners
        
        # Get execution engine through API
        execution_engine = get_execution_engine()
        # Get terminal formatter through API
        terminal_formatter = get_terminal_formatter()
        
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
        
        # --- HANDLE INTERACTIVE/CONTINUOUS COMMANDS ---
        interactive_continuous_commands = [
            # Terminal-based editors and pagers
            "vim", "vi", "nano", "emacs", "pico", "less", "more", 
            # Interactive monitoring tools
            "top", "htop", "btop", "iotop", "iftop", "nmon", "glances", "atop",
            # Networking tools with continuous output
            "ping", "traceroute", "mtr", "tcpdump", "wireshark", "tshark", "ngrep",
            # File monitoring
            "tail", "watch", 
            # System logs
            "journalctl", "dmesg",
            # Remote sessions
            "ssh", "telnet", "nc", "netcat",
            # Database and interactive shells
            "mysql", "psql", "sqlite3", "mongo", "redis-cli",
            # Interactive debuggers
            "gdb", "lldb", "pdb",
            # Other interactive utilities
            "tmux", "screen"
        ]
        
        base_cmd_to_execute = command.split()[0] if command.split() else ""
        
        # Enhanced detection for commands that should be interactive
        is_special_interactive_cmd = False
        if base_cmd_to_execute in interactive_continuous_commands:
            # Standard interactive commands get automatic interactive mode
            if base_cmd_to_execute in ["top", "htop", "btop", "vim", "vi", "nano", "emacs", 
                                      "less", "more", "ssh", "mysql", "psql", "mongo",
                                      "gdb", "lldb", "pdb", "tmux", "screen"]:
                is_special_interactive_cmd = True
            # Commands that are interactive only with certain flags
            elif base_cmd_to_execute == "ping" and "-c" not in command:
                is_special_interactive_cmd = True
            elif base_cmd_to_execute == "tail" and "-f" in command:
                is_special_interactive_cmd = True
            elif base_cmd_to_execute == "journalctl" and "-f" in command:
                is_special_interactive_cmd = True
            elif base_cmd_to_execute == "watch":
                is_special_interactive_cmd = True
        
        # Log the decision for debugging
        self._logger.debug(f"Executing command '{command}' with interactive={is_special_interactive_cmd}")
        
        if is_special_interactive_cmd:
            # NEW: Instead of executing, provide a recommendation for interactive commands
            return await self._handle_interactive_command_recommendation(command)
        else:
            # Show execution spinner if enabled
            stdout, stderr, return_code, execution_time = await terminal_formatter.display_execution_timer(
                command,
                with_philosophy=True
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
                "execution_time": execution_time, 
                "dry_run": False
            }
    
    async def _handle_interactive_command_recommendation(
        self, 
        command: str, 
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Instead of executing interactive commands, provide recommendations to the user.
        
        Args:
            command: The interactive command
            explanation: Optional explanation of what the command does
            
        Returns:
            Dictionary with recommendation results
        """
        base_cmd = command.split()[0] if command.split() else ""
        
        # Create a formatted recommendation
        recommendation = f"""
    [bold cyan]Interactive Command Detected:[/bold cyan]
    
    Angela doesn't directly execute terminal-interactive commands like {base_cmd}.
    You can run this command yourself by typing:
    
        [bold green]{command}[/bold green]
    
    This will launch {base_cmd} in your terminal.
    """
    
        if explanation:
            recommendation += f"\n[italic]{explanation}[/italic]"
        
        # Print the recommendation
        self._console.print(Panel(
            recommendation,
            title="[bold blue]Command Recommendation[/bold blue]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            expand=False
        ))
        
        # Return a success result but mark it as recommendation only
        return {
            "command": command,
            "success": True,
            "recommendation_only": True,
            "stdout": f"Recommended command: {command}",
            "stderr": "",
            "return_code": 0
        }

    async def _handle_interactive_command_recommendation(
        self, 
        command: str, 
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Instead of executing interactive commands, provide recommendations to the user.
        
        Args:
            command: The interactive command
            explanation: Optional explanation of what the command does
            
        Returns:
            Dictionary with recommendation results
        """
        # Get rich console
        from rich.console import Console
        from rich.panel import Panel
        from angela.components.shell.formatter import COLOR_PALETTE, DEFAULT_BOX
        console = Console()
        
        base_cmd = command.split()[0] if command.split() else ""
        
        # Create a formatted recommendation
        recommendation = f"""
    [bold cyan]Interactive Command Detected:[/bold cyan]
    
    Angela doesn't directly execute terminal-interactive commands like {base_cmd}.
    You can run this command yourself by typing:
    
        [bold green]{command}[/bold green]
    
    This will launch {base_cmd} in your terminal.
    """
    
        if explanation:
            recommendation += f"\n[italic]{explanation}[/italic]"
        
        # Print the recommendation
        console.print(Panel(
            recommendation,
            title="[bold blue]Command Recommendation[/bold blue]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            expand=False
        ))
        
        # Return a success result but mark it as recommendation only
        return {
            "command": command,
            "success": True,
            "recommendation_only": True,
            "stdout": f"Recommended command: {command}",
            "stderr": "",
            "return_code": 0
        }



# Global adaptive execution engine instance
adaptive_engine = AdaptiveExecutionEngine()
