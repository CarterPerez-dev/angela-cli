# angela/components/safety/adaptive_confirmation.py

import asyncio
from typing import Dict, Any, Optional, List, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import input_dialog, message_dialog, yes_no_dialog
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table

from angela.constants import RISK_LEVELS
from angela.api.context import get_history_manager, get_preferences_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Styles for different risk levels
CONFIRMATION_STYLES = Style.from_dict({
    'safe': '#2DA44E',        # Green
    'low': '#0969DA',         # Blue
    'medium': '#BF8700',      # Yellow/Orange
    'high': '#CF222E',        # Red
    'critical': '#820000',    # Dark Red
    'dialog': 'bg:#222222',
    'dialog.body': 'bg:#222222 #ffffff',
    'dialog.border': '#888888',
    'button': 'bg:#222222 #ffffff',
    'button.focused': 'bg:#0969DA #ffffff',
})

# Risk level names
RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}

# Rich-compatible color mapping for risk levels
RISK_COLORS = {
    'safe': 'green',
    'low': 'blue',
    'medium': 'yellow',
    'high': 'red',
    'critical': 'dark_red',
}

# Console setup
console = Console()

async def get_adaptive_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    impact: Dict[str, Any],
    preview: Optional[str] = None,
    explanation: Optional[str] = None,
    natural_request: Optional[str] = None,
    dry_run: bool = False,
    confidence_score: Optional[float] = None,  # Added new parameter
    command_info: Optional[Dict[str, Any]] = None  # Added new parameter
) -> bool:
    """
    Get user confirmation for a command based on risk level and user history.
    
    Args:
        command: The command to be executed
        risk_level: The risk level of the command
        risk_reason: The reason for the risk classification
        impact: The impact analysis dictionary
        preview: Optional preview of command results
        explanation: AI explanation of the command
        natural_request: The original natural language request
        dry_run: Whether this is a dry run
        confidence_score: Optional confidence score for the command
        command_info: Optional command information dictionary
        
    Returns:
        True if the user confirms, False otherwise
    """
    # If this is a dry run, skip confirmation
    if dry_run:
        await _show_dry_run_preview(command, risk_level, preview, explanation)
        return False
    
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
    
    # For all other cases, get explicit confirmation
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    risk_style = risk_name.lower() if risk_name.lower() in ['safe', 'low', 'medium', 'high', 'critical'] else 'medium'
    
    # For high-risk operations, use a more detailed confirmation dialog
    if risk_level >= RISK_LEVELS["HIGH"]:
        return await _get_detailed_confirmation(
            command, risk_level, risk_reason, impact, preview, explanation, confidence_score
        )
    
    # For medium and lower risk operations, use a simpler confirmation
    return await _get_simple_confirmation(
        command, risk_level, risk_reason, preview, explanation, confidence_score
    )


async def _show_dry_run_preview(
    command: str, 
    risk_level: int, 
    preview: Optional[str],
    explanation: Optional[str]
) -> None:
    """Show a preview for dry run mode."""
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    
    console.print("\n")
    console.print(Panel(
        Syntax(command, "bash", theme="monokai", word_wrap=True),
        title="[bold blue]DRY RUN PREVIEW[/bold blue]",
        subtitle=f"Risk Level: {risk_name}",
        border_style="blue",
        expand=False
    ))
    
    if explanation:
        console.print("[bold blue]Explanation:[/bold blue]")
        console.print(explanation)
    
    if preview:
        console.print(Panel(
            preview,
            title="Command Preview",
            border_style="blue",
            expand=False
        ))
    
    console.print("[blue]This is a dry run. No changes will be made.[/blue]")


async def _show_auto_execution_notice(
    command: str, 
    risk_level: int,
    preview: Optional[str]
) -> None:
    """Show a notice for auto-execution."""
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    preferences_manager = get_preferences_manager()
    
    # Use a more subtle notification for auto-execution
    console.print("\n")
    console.print(Panel(
        Syntax(command, "bash", theme="monokai", word_wrap=True),
        title="Auto-Executing Command",
        border_style="green",
        expand=False
    ))
    
    # Only show preview if it's enabled in preferences
    if preview and preferences_manager.preferences.ui.show_command_preview:
        console.print(preview)
    
    # Brief pause to allow user to see what's happening
    await asyncio.sleep(0.5)


async def _get_simple_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    preview: Optional[str],
    explanation: Optional[str],
    confidence_score: Optional[float] = None  # Added new parameter
) -> bool:
    """Get a simple confirmation for medium/low risk operations."""
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    risk_style = risk_name.lower() if risk_name.lower() in ['safe', 'low', 'medium', 'high', 'critical'] else 'medium'
    preferences_manager = get_preferences_manager()
    
    # Get actual color for rich components
    risk_color = RISK_COLORS.get(risk_style, "yellow")
    
    # Display the command
    console.print("\n")
    console.print(Panel(
        Syntax(command, "bash", theme="monokai", word_wrap=True),
        title=f"Execute [{risk_name} Risk]",
        border_style=risk_color,
        expand=False
    ))
    
    # Display explanation if provided
    if explanation:
        console.print(explanation)
    
    # Display confidence score if available
    if confidence_score is not None:
        confidence_color = "green" if confidence_score > 0.8 else "yellow" if confidence_score > 0.6 else "red"
        confidence_stars = int(confidence_score * 5)
        confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
        console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{confidence_score:.2f}[/{confidence_color}] {confidence_display}")
        console.print("[dim](Confidence indicates how sure Angela is that this command matches your request)[/dim]")
    
    # Display preview if available and enabled
    if preview and preferences_manager.preferences.ui.show_command_preview:
        console.print(Panel(
            preview,
            title="Preview",
            border_style=risk_color,
            expand=False
        ))
    
    # Use prompt_toolkit dialog for confirmation
    # FIXED: Using run_async() instead of run()
    confirmed = await yes_no_dialog(
        title=f'Execute {risk_name} Risk Command?',
        text=f'{command}\n\nReason: {risk_reason}',
        style=CONFIRMATION_STYLES
    ).run_async()
    
    return confirmed


async def _get_detailed_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    impact: Dict[str, Any],
    preview: Optional[str],
    explanation: Optional[str],
    confidence_score: Optional[float] = None  # Added new parameter
) -> bool:
    """Get a detailed confirmation for high/critical risk operations."""
    risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
    risk_style = risk_name.lower() if risk_name.lower() in ['safe', 'low', 'medium', 'high', 'critical'] else 'high'
    preferences_manager = get_preferences_manager()
    
    # Get actual color for rich components
    risk_color = RISK_COLORS.get(risk_style, "red")
    
    # Format the command and impact information
    console.print("\n")
    console.print(Panel(
        Syntax(command, "bash", theme="monokai", word_wrap=True),
        title=f"[bold {risk_color}]HIGH RISK OPERATION[/bold {risk_color}]",
        border_style=risk_color,
        expand=False
    ))
    
    console.print(f"[bold {risk_color}]Risk Level:[/bold {risk_color}] {risk_name}")
    console.print(f"[bold {risk_color}]Reason:[/bold {risk_color}] {risk_reason}")
    
    # Display confidence score if available
    if confidence_score is not None:
        confidence_color = "green" if confidence_score > 0.8 else "yellow" if confidence_score > 0.6 else "red"
        confidence_stars = int(confidence_score * 5)
        confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
        console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{confidence_score:.2f}[/{confidence_color}] {confidence_display}")
        console.print("[dim](Confidence indicates how sure Angela is that this command matches your request)[/dim]")
    
    # Display explanation if provided
    if explanation:
        console.print("[bold]Explanation:[/bold]")
        console.print(explanation)
    
    # Display impact analysis if enabled
    if preferences_manager.preferences.ui.show_impact_analysis:
        # Create a table for impact analysis
        table = Table(title="Impact Analysis", expand=True)
        table.add_column("Aspect", style="bold cyan")
        table.add_column("Details", style="white")
        
        # Add operations
        operations = ", ".join(impact.get("operations", ["unknown"]))
        table.add_row("Operations", operations)
        
        # Add warning for destructive operations
        if impact.get("destructive", False):
            table.add_row("⚠️ Warning", f"[bold {risk_color}]This operation may delete or overwrite files[/bold {risk_color}]")
        
        # Add affected files/directories
        affected_files = impact.get("affected_files", [])
        if affected_files:
            file_list = "\n".join(affected_files[:5])
            if len(affected_files) > 5:
                file_list += f"\n...and {len(affected_files) - 5} more"
            table.add_row("Affected Files", file_list)
        
        console.print(table)
    
    # Display preview if available and enabled
    if preview and preferences_manager.preferences.ui.show_command_preview:
        console.print(Panel(
            preview,
            title="Command Preview",
            border_style=risk_color,
            expand=False
        ))
    
    # For critical operations, use an even more prominent warning
    if risk_level == RISK_LEVELS["CRITICAL"]:
        console.print(Panel(
            "⚠️  [bold red]This is a CRITICAL risk operation[/bold red] ⚠️\n"
            "It may cause significant changes to your system or data loss.",
            border_style="red",
            expand=False
        ))
    
    # Use prompt_toolkit dialog for confirmation
    # FIXED: Using run_async() instead of run()
    confirmed = await yes_no_dialog(
        title=f'WARNING: Execute {risk_name} Risk Command?',
        text=f'{command}\n\nThis is a {risk_name} risk operation.\nReason: {risk_reason}\n\nAre you sure you want to proceed?',
        style=CONFIRMATION_STYLES
    ).run_async()
    
    # If confirmed for a high-risk operation, offer to add to trusted commands
    if confirmed and risk_level >= RISK_LEVELS["HIGH"]:
        # FIXED: Using run_async() instead of run()
        add_to_trusted = await yes_no_dialog(
            title='Add to Trusted Commands?',
            text=f'Would you like to auto-execute similar commands in the future?',
            style=CONFIRMATION_STYLES
        ).run_async()
        
        if add_to_trusted:
            preferences_manager.add_trusted_command(command)
    
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
            # FIXED: Using run_async() instead of run()
            add_to_trusted = await yes_no_dialog(
                title='Add to Trusted Commands?',
                text=f'You\'ve used "{base_command}" {pattern.count} times. Would you like to auto-execute it in the future?',
                style=CONFIRMATION_STYLES
            ).run_async()
            
            if add_to_trusted:
                preferences_manager.add_trusted_command(command)
                console.print(f"Added [green]{base_command}[/green] to trusted commands.")
            else:
                # Record the rejection to increase the threshold for next time
                preferences_manager.increment_command_rejection_count(command)
                console.print(f"[dim]You'll be asked again after using this command {threshold + 2} more times.[/dim]")


adaptive_confirmation = get_adaptive_confirmation
