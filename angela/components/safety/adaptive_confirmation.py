# angela/components/safety/adaptive_confirmation.py

import asyncio
from typing import Dict, Any, Optional, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table

from angela.constants import RISK_LEVELS
from angela.api.context import get_history_manager, get_preferences_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Create a console for rich output
console = Console()

# Risk level names
RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}

# Rich-compatible color mapping for risk levels
RISK_COLORS = {
    RISK_LEVELS["SAFE"]: "green",
    RISK_LEVELS["LOW"]: "blue",
    RISK_LEVELS["MEDIUM"]: "yellow",
    RISK_LEVELS["HIGH"]: "red",
    RISK_LEVELS["CRITICAL"]: "dark_red",
}

async def get_adaptive_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    impact: Dict[str, Any],
    preview: Optional[str] = None,
    explanation: Optional[str] = None,
    natural_request: Optional[str] = None,
    dry_run: bool = False,
    confidence_score: Optional[float] = None,
    command_info: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Get user confirmation for a command based on risk level and user history.
    
    Args:
        command: The command to be executed
        risk_level: The risk level of the command
        risk_reason: The reason for the risk classification
        impact: The impact analysis dictionary
        preview: Optional preview of command results
        explanation: AI explanation of what the command does
        natural_request: The original natural language request
        dry_run: Whether this is a dry run
        confidence_score: Optional confidence score for the command
        command_info: Optional command information dictionary
        
    Returns:
        True if confirmed or dry_run is True, False otherwise
    """
    # Get managers from API
    preferences_manager = get_preferences_manager()
    history_manager = get_history_manager()
    
    # Check if auto-execution is enabled for this risk level and command
    if preferences_manager.should_auto_execute(risk_level, command):
        # Get command frequency and success rate
        frequency = history_manager.get_command_frequency(command)
        success_rate = history_manager.get_command_success_rate(command)
        
        # For frequently used commands with high success rate, auto-execute
        if frequency >= 5 and success_rate > 0.8:
            logger.info(f"Auto-executing command with high trust: {command}")
            await _show_auto_execution_notice(command, risk_level, preview)
            return True
    
    # Skip confirmation for dry runs
    if dry_run:
        # Get terminal formatter from API
        from angela.api.shell import get_terminal_formatter
        terminal_formatter = get_terminal_formatter()
        
        await terminal_formatter.display_pre_confirmation_info(
            command=command,
            risk_level=risk_level,
            risk_reason=risk_reason,
            impact=impact,
            explanation=explanation,
            preview=preview,
            confidence_score=confidence_score
        )
        
        console.print(Panel(
            "[bold blue]This is a dry run.[/bold blue] No changes will be made.",
            border_style="blue",
            expand=False
        ))
        
        return False
    
    # For all other cases, get explicit confirmation
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    
    # For high-risk operations, use a more detailed confirmation dialog
    if risk_level >= RISK_LEVELS["HIGH"]:
        return await _get_detailed_confirmation(
            command, risk_level, risk_reason, impact, preview, explanation, confidence_score
        )
    
    # For medium and lower risk operations, use a simpler confirmation
    return await _get_simple_confirmation(
        command, risk_level, risk_reason, preview, explanation, confidence_score
    )


async def _show_auto_execution_notice(
    command: str, 
    risk_level: int,
    preview: Optional[str]
) -> None:
    """Show a notice for auto-execution."""
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    preferences_manager = get_preferences_manager()
    
    # Get terminal formatter from API
    from angela.api.shell import get_terminal_formatter
    terminal_formatter = get_terminal_formatter()
    
    # Use a more subtle notification for auto-execution
    console.print("\n")
    console.print(Panel(
        Syntax(command, "bash", theme="monokai", word_wrap=True),
        title="Auto-Executing Trusted Command",
        border_style="green",
        expand=False
    ))
    
    # Only show preview if it's enabled in preferences
    if preview and preferences_manager.preferences.ui.show_command_preview:
        console.print(preview)
    
    # Display execution loading animation with timer
    await terminal_formatter.display_loading_timer("Auto-executing trusted command...", with_philosophy=True)


async def _get_simple_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    preview: Optional[str],
    explanation: Optional[str],
    confidence_score: Optional[float] = None
) -> bool:
    """Get a simple confirmation for medium/low risk operations."""
    # Get terminal formatter from API
    from angela.api.shell import get_terminal_formatter
    terminal_formatter = get_terminal_formatter()
    
    # Risk name for display
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    
    # Display all information
    await terminal_formatter.display_pre_confirmation_info(
        command=command,
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact={"operations": [risk_reason]},  # Simple impact for low-risk operations
        explanation=explanation,
        preview=preview,
        confidence_score=confidence_score
    )
    
    # Ask for confirmation with inline prompt
    prompt_text = f"Proceed with this {risk_name} risk operation?"
    return await terminal_formatter.display_inline_confirmation(prompt_text)


async def _get_detailed_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    impact: Dict[str, Any],
    preview: Optional[str],
    explanation: Optional[str],
    confidence_score: Optional[float] = None
) -> bool:
    """Get a detailed confirmation for high/critical risk operations."""
    # Get terminal formatter from API
    from angela.api.shell import get_terminal_formatter
    terminal_formatter = get_terminal_formatter()
    
    # Risk name for display
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    risk_color = RISK_COLORS.get(risk_level, "red")
    
    # Display all information
    await terminal_formatter.display_pre_confirmation_info(
        command=command,
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact=impact,
        explanation=explanation,
        preview=preview,
        confidence_score=confidence_score
    )
    
    # For critical operations, add an extra warning
    if risk_level >= RISK_LEVELS["CRITICAL"]:
        console.print(Panel(
            f"[bold red]⚠️  This is a {risk_name} RISK operation  ⚠️[/bold red]\n"
            "It may cause significant changes to your system or data that cannot be easily undone.",
            border_style="red",
            expand=False
        ))
    
    # Ask for confirmation with additional warning
    prompt_text = f"⚠️ Proceed with this {risk_name} RISK operation? ⚠️"
    confirmed = await terminal_formatter.display_inline_confirmation(prompt_text)
    
    # If confirmed for a high-risk operation, offer to add to trusted commands
    if confirmed and risk_level >= RISK_LEVELS["HIGH"]:
        # Get preferences manager from API
        from angela.api.context import get_preferences_manager
        preferences_manager = get_preferences_manager()
        
        # Ask if the user wants to trust this command
        trust_prompt = "Add to trusted commands for future auto-execution?"
        add_to_trusted = await terminal_formatter.display_inline_confirmation(trust_prompt)
        
        if add_to_trusted:
            preferences_manager.add_trusted_command(command)
            console.print(f"[green]Added command to trusted list. It will execute automatically in the future.[/green]")
    
    return confirmed


async def offer_command_learning(command: str) -> None:
    """
    After a successful execution, offer to add the command to trusted commands.
    
    Args:
        command: The command that was executed
    """
    # Get managers from API
    preferences_manager = get_preferences_manager()
    history_manager = get_history_manager()
    
    # Check if the command should be offered for learning
    base_command = history_manager._extract_base_command(command)
    pattern = history_manager._patterns.get(base_command)
    
    # Only offer for commands used a few times but not yet trusted
    if pattern and pattern.count >= 2 and command not in preferences_manager.preferences.trust.trusted_commands:
        # Check if user has previously rejected this command
        rejection_count = preferences_manager.get_command_rejection_count(command)
        
        # Determine if we should show the prompt based on rejection count
        threshold = 2  # Base threshold
        if rejection_count > 0:
            # Progressive threshold: 2, 5, 7, 9, 11, etc.
            threshold = 2 + (rejection_count * 2)
        
        if pattern.count >= threshold:
            # Get terminal formatter for inline confirmation
            from angela.api.shell import get_terminal_formatter
            terminal_formatter = get_terminal_formatter()
            
            # Create a fancy learning prompt
            console.print(Panel(
                f"I noticed you've used [bold cyan]{base_command}[/bold cyan] {pattern.count} times.",
                title="Command Learning",
                border_style="blue",
                expand=False
            ))
            
            prompt_text = f"Would you like to auto-execute this command in the future?"
            add_to_trusted = await terminal_formatter.display_inline_confirmation(prompt_text)
            
            if add_to_trusted:
                preferences_manager.add_trusted_command(command)
                console.print(f"Added [green]{base_command}[/green] to trusted commands.")
            else:
                # Record the rejection to increase the threshold for next time
                preferences_manager.increment_command_rejection_count(command)
                console.print(f"[dim]You'll be asked again after using this command {threshold + 2} more times.[/dim]")


# Export for API access
adaptive_confirmation = get_adaptive_confirmation
