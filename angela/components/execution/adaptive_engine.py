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
        """
        self._logger.info(f"Preparing to execute command: {command} (Dry run: {dry_run})")
        self._logger.debug(f"Natural request: {natural_request}, Explanation: {explanation}")

        # Get the terminal_formatter once
        terminal_formatter = get_terminal_formatter()

        # --- NEW: Handle interactive commands first ---
        # It's good practice to import where used if it's a local utility
        # or ensure it's imported at the top if it's a core utility.
        try:
            from angela.utils.command_utils import is_interactive_command, display_command_recommendation
        except ImportError:
            self._logger.error("Failed to import command_utils. Interactive command check will be skipped.")
            # Define dummy functions to prevent NameError if import fails, or handle differently
            def is_interactive_command(_cmd): return False, ""
            def display_command_recommendation(_cmd): pass


        is_interactive, base_cmd = is_interactive_command(command)
        if is_interactive and not dry_run:
            self._logger.info(f"Interactive command '{base_cmd}' detected. Displaying recommendation.")
            # display_command_recommendation(command) # This function should ideally use terminal_formatter
                                                    # For now, let's assume it prints directly or we'll integrate it.
                                                    # If it's async, it should be awaited.
            # Let's use the _handle_interactive_command_recommendation method for consistent display
            return await self._handle_interactive_command_recommendation(command, explanation)
        # --- END: Handle interactive commands ---

        # Analyze command risk and impact
        classifier = get_command_risk_classifier()
        risk_level, risk_reason = classifier.classify(command)
        impact = classifier.analyze_impact(command)
        self._logger.debug(f"Command risk: Level {risk_level}, Reason: {risk_reason}")

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
            self._logger.debug(f"Generated preview: {preview[:100] if preview else 'None'}")

        # Get confidence score if available
        confidence_score = None
        try:
            from angela.api.ai import get_confidence_scorer
            confidence_scorer = get_confidence_scorer()
            # Ensure context is passed for confidence scoring; using a simple one if not available
            current_context = {"request": natural_request, "cwd": str(Path.cwd())} # Example context
            confidence_score = confidence_scorer.score_command_confidence(natural_request, command, current_context)
            self._logger.debug(f"Confidence score: {confidence_score}")
        except Exception as e:
            self._logger.error(f"Error calculating confidence score: {str(e)}")

        command_info = {
            "command": command, "risk_level": risk_level, "risk_reason": risk_reason,
            "impact": impact, "preview": preview, "explanation": explanation,
            "confidence_score": confidence_score, "dry_run": dry_run
        }

        # Get adaptive confirmation
        confirmation_handler = get_adaptive_confirmation()
        confirmed_for_execution = await confirmation_handler(
            command=command, risk_level=risk_level, risk_reason=risk_reason,
            impact=impact, preview=preview, explanation=explanation,
            natural_request=natural_request, dry_run=dry_run,
            confidence_score=confidence_score, command_info=command_info
        )
        self._logger.debug(f"Confirmation for execution: {confirmed_for_execution}")

        if not confirmed_for_execution and not dry_run:
            self._logger.info(f"Command execution cancelled by user: {command}")
            return {
                "command": command, "success": False, "cancelled": True, "stdout": "",
                "stderr": "Command execution cancelled by user", "return_code": 1,
                "dry_run": dry_run, "confidence": confidence_score
            }

        # --- Execute the command ---
        execution_result: Dict[str, Any] # Type hint for clarity
        try:
            execution_result = await self._execute_with_feedback(command, dry_run)
        except Exception as e:
            self._logger.error(f"Error during _execute_with_feedback: {str(e)}", exc_info=True)
            execution_result = {
                "command": command, "success": False, "stdout": "",
                "stderr": f"Core execution error: {str(e)}", "return_code": -1,
                "dry_run": dry_run, "confidence": confidence_score, "error": str(e)
            }

        # --- Process and display results ---
        # This is where the display_result_summary call should be.
        # It uses execution_result, which is now defined.
        if not dry_run and not execution_result.get("cancelled") and not execution_result.get("recommendation_only"):
            self._logger.debug("Displaying result summary.")
            await terminal_formatter.display_result_summary(execution_result)
        elif dry_run:
            self._logger.debug("Displaying dry run summary.")
            # For dry run, adaptive_confirmation already shows the preview.
            # _execute_with_feedback for dry_run also returns a message.
            # We might want a specific dry_run summary display here if the current output isn't enough.
            # For now, let's assume existing dry-run output is sufficient.
            if execution_result.get("stdout"): # stdout from dry_run_command in engine
                 await terminal_formatter.display_result_summary(execution_result)

        # Add confidence score to the final result returned by this function
        final_result_payload = {**execution_result, "confidence": confidence_score}


        # Add to history
        history_manager = get_history_manager()
        history_manager.add_command(
            command=command, natural_request=natural_request,
            success=execution_result.get("success", False),
            output=execution_result.get("stdout", ""),
            error=execution_result.get("stderr", ""),
            risk_level=risk_level
        )

        # Error analysis and fix suggestions
        if not execution_result.get("success", False) and execution_result.get("stderr") and not dry_run:
            self._logger.debug("Analyzing error for failed command.")
            error_analyzer = self._get_error_analyzer()
            final_result_payload["error_analysis"] = error_analyzer.analyze_error(command, execution_result["stderr"])
            final_result_payload["fix_suggestions"] = error_analyzer.generate_fix_suggestions(command, execution_result["stderr"])
            # Display error analysis if it was generated
            if "error_analysis" in final_result_payload:
                 terminal_formatter.print_error_analysis(final_result_payload["error_analysis"])


        # Offer command learning
        if execution_result.get("success", False) and risk_level > 0 and not dry_run:
            self._logger.debug("Offering command learning.")
            from angela.api.safety import offer_command_learning
            if offer_command_learning:
                await offer_command_learning(command)

        return final_result_payload
    
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
            # For interactive commands, provide a recommendation instead
            return await self._handle_interactive_command_recommendation(command)
        else:
            # Execute non-interactive command with spinner/timer
            execution_started = False
            try:
                # Show execution spinner if enabled
                stdout, stderr, return_code, execution_time = await terminal_formatter.display_execution_timer(
                    command,
                    with_philosophy=True
                )
                
                execution_started = True
                
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
            except Exception as e:
                self._logger.error(f"Error in execution feedback: {str(e)}")
                
                # If we didn't start execution through the timer, fall back to direct execution
                if not execution_started:
                    self._logger.info("Falling back to direct execution")
                    try:
                        stdout, stderr, return_code = await execution_engine.execute_command(
                            command,
                            check_safety=False  # Safety already checked
                        )
                        execution_time = 0.0  # We don't know the exact time
                        
                        return {
                            "command": command,
                            "success": return_code == 0,
                            "stdout": stdout,
                            "stderr": stderr,
                            "return_code": return_code,
                            "execution_time": execution_time,
                            "dry_run": False
                        }
                    except Exception as direct_e:
                        self._logger.error(f"Direct execution also failed: {str(direct_e)}")
                        return {
                            "command": command,
                            "success": False,
                            "stdout": "",
                            "stderr": f"Execution error: {str(direct_e)}",
                            "return_code": -1,
                            "execution_time": 0.0,
                            "dry_run": False
                        }
                
                # Return error information from the original exception
                return {
                    "command": command,
                    "success": False,
                    "stdout": "",
                    "stderr": f"Error in execution: {str(e)}",
                    "return_code": -1,
                    "execution_time": 0.0,
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
