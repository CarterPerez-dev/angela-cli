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
    """Get user confirmation based on risk and history."""

    preferences_manager = get_preferences_manager()
    history_manager = get_history_manager()
    base_command = command.split()[0] if command.split() else ""


    can_auto_proceed = False
    if base_command and base_command in preferences_manager.preferences.trust.trusted_commands:
        can_auto_proceed = True
        logger.debug(f"Command '{base_command}' is in trusted list.")
        
    elif preferences_manager.should_auto_execute(risk_level, command): 
        frequency = history_manager.get_command_frequency(base_command)
        success_rate = history_manager.get_command_success_rate(base_command)
        
        if frequency >= 5 and success_rate > 0.8:
            can_auto_proceed = True
            logger.info(f"Auto-proceeding with high trust command (history/success): {command}")

    if can_auto_proceed:
        await _show_auto_execution_notice(command, risk_level, preview, dry_run=dry_run)
        return True


    if dry_run:
        from angela.api.shell import get_terminal_formatter 
        terminal_formatter = get_terminal_formatter()

        await terminal_formatter.display_pre_confirmation_info(
            command=command, risk_level=risk_level, risk_reason=risk_reason,
            impact=impact, explanation=explanation, preview=preview,
            confidence_score=confidence_score
        )
        console.print(Panel(
            "[bold blue]This is a dry run. No changes will be made.[/bold blue]\n"
            "Angela will simulate the command execution.",
            border_style="blue", expand=False
        ))

        return await terminal_formatter.display_inline_confirmation("Proceed with dry run simulation?")


    if risk_level >= RISK_LEVELS["HIGH"]:
        return await _get_detailed_confirmation(
            command, risk_level, risk_reason, impact, preview, explanation, confidence_score
        )
    
    return await _get_simple_confirmation(
        command, risk_level, risk_reason, preview, explanation, confidence_score
    )


async def _show_auto_execution_notice(
    command: str,
    risk_level: int,
    preview: Optional[str],
    dry_run: bool = False  
) -> None:
    """Show a notice for auto-execution."""
    from angela.api.shell import display_auto_execution_notice
    await display_auto_execution_notice(command, risk_level, preview, dry_run=dry_run)

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
    """
    preferences_manager = get_preferences_manager()
    history_manager = get_history_manager()
    base_command = command.split()[0] if command.split() else ""
    if not base_command:
        return

    # 1. CRITICAL FIX: Skip if command is already trusted
    if base_command in preferences_manager.preferences.trust.trusted_commands:
        logger.debug(f"Command '{base_command}' already trusted, skipping learning prompt")
        return # <<< IF IT'S ALREADY TRUSTED, IT EXITS HERE

    # 2. Check if this command should be offered for learning
    pattern = history_manager._patterns.get(base_command) # This accesses a "private" attribute of HistoryManager

    
    # Only offer for commands used a few times but not yet trusted
    if pattern and pattern.count >= 2:
        # Check if user has previously rejected this command
        rejection_count = preferences_manager.get_command_rejection_count(base_command)
        
        # Determine if we should show the prompt based on rejection count
        threshold = 2  # Base threshold
        if rejection_count > 0:
            # Progressive threshold: 2, 5, 7, 9, 11, etc.
            threshold = 2 + (rejection_count * 2)
        
        if pattern.count >= threshold:
            # Get terminal formatter for inline confirmation
            from angela.api.shell import get_terminal_formatter, display_command_learning, display_trust_added_message
            terminal_formatter = get_terminal_formatter()
            
            # Create a fancy learning prompt with purple styling
            await display_command_learning(base_command, pattern.count)
            
            # Use the new custom y/n formatting
            prompt_text = f"Would you like to auto-execute this command in the future?"
            add_to_trusted = await terminal_formatter.display_inline_confirmation(prompt_text)
            
            if add_to_trusted:
                preferences_manager.add_trusted_command(base_command)
                await display_trust_added_message(base_command)
            else:
                # Record the rejection to increase the threshold for next time
                preferences_manager.increment_command_rejection_count(base_command)
                console.print(f"[dim]You'll be asked again after using this command {threshold + 2} more times.[/dim]")

# Export for API access
adaptive_confirmation = get_adaptive_confirmation
