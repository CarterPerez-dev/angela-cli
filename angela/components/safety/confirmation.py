# angela/components/safety/confirmation.py

import sys
from typing import Dict, Any, Optional, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from angela.constants import RISK_LEVELS, DEFAULT_CONFIRMATION_REQUIREMENTS
from angela.config import config_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Risk level color mapping
RISK_COLORS = {
    RISK_LEVELS["SAFE"]: "green",
    RISK_LEVELS["LOW"]: "blue", 
    RISK_LEVELS["MEDIUM"]: "yellow",
    RISK_LEVELS["HIGH"]: "bright_red",  
    RISK_LEVELS["CRITICAL"]: "red",
}

# Risk level names for display
RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}


def requires_confirmation(risk_level: int) -> bool:
    """
    Determine if a risk level requires confirmation based on configuration.
    
    Args:
        risk_level: The risk level to check.
        
    Returns:
        True if confirmation is required, False otherwise.
    """
    # If confirm_all_actions is set, always confirm
    if config_manager.config.user.confirm_all_actions:
        return True
    
    # Otherwise, check the default requirements
    return DEFAULT_CONFIRMATION_REQUIREMENTS.get(risk_level, True)


def format_impact_analysis(impact: Dict[str, Any]) -> Table:
    """
    Format the command impact analysis into a rich Table.
    
    Args:
        impact: The impact analysis dictionary.
        
    Returns:
        A rich Table object with the formatted impact analysis.
    """
    table = Table(expand=True)
    
    table.add_column("Aspect", style="bold cyan")
    table.add_column("Details", style="white")
    
    # Add operation types
    operations = ", ".join(impact.get("operations", ["unknown"]))
    table.add_row("Operations", operations)
    
    # Add destructive warning if applicable
    if impact.get("destructive", False):
        table.add_row("⚠️ Warning", "[bold red]This operation may delete or overwrite files[/bold red]")
    
    # Add file creation info
    if impact.get("creates_files", False):
        table.add_row("Creates Files", "Yes")
    
    # Add file modification info
    if impact.get("modifies_files", False):
        table.add_row("Modifies Files", "Yes")
    
    # Add affected files
    affected_files = impact.get("affected_files", [])
    if affected_files:
        file_list = "\n".join(affected_files[:5])
        if len(affected_files) > 5:
            file_list += f"\n...and {len(affected_files) - 5} more"
        table.add_row("Affected Files", file_list)
    
    # Add affected directories
    affected_dirs = impact.get("affected_dirs", [])
    if affected_dirs:
        dir_list = "\n".join(affected_dirs[:5])
        if len(affected_dirs) > 5:
            dir_list += f"\n...and {len(affected_dirs) - 5} more"
        table.add_row("Affected Directories", dir_list)
    
    return table


async def get_confirmation(
    command: str, 
    risk_level: int, 
    risk_reason: str,
    impact: Dict[str, Any],
    preview: Optional[str] = None,
    dry_run: bool = False,
    explanation: Optional[str] = None,
    confidence_score: Optional[float] = None
) -> bool:
    """
    Get user confirmation for a command based on its risk level.
    
    Args:
        command: The command to be executed.
        risk_level: The risk level of the command.
        risk_reason: The reason for the risk classification.
        impact: The impact analysis dictionary.
        preview: Optional preview of command results.
        dry_run: Whether this is a dry run.
        explanation: Explanation of what the command does.
        confidence_score: Confidence score for the command.
        
    Returns:
        True if the user confirms, False otherwise.
    """
    # If safety checks are not required, return True
    if not requires_confirmation(risk_level) and not dry_run:
        return True
    
    # Get the terminal formatter
    from angela.api.shell import get_terminal_formatter
    terminal_formatter = get_terminal_formatter()
    
    # For dry run, just show the information without asking for confirmation
    if dry_run:
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
    
    # Display all the information
    await terminal_formatter.display_pre_confirmation_info(
        command=command,
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact=impact,
        explanation=explanation,
        preview=preview,
        confidence_score=confidence_score
    )
    
    # Ask for confirmation
    prompt_text = "Proceed with execution?"
    if risk_level >= RISK_LEVELS["HIGH"]:
        prompt_text = f"Proceed with this {RISK_LEVEL_NAMES.get(risk_level, 'HIGH')} risk operation?"
        
    return await terminal_formatter.display_inline_confirmation(prompt_text)
