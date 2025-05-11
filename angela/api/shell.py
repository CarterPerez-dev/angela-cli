# angela/api/shell.py
"""
Public API for shell components.

This module provides functions to access shell components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable, Awaitable, Tuple

from angela.core.registry import registry

# Terminal Formatter API
def get_terminal_formatter():
    """Get the terminal formatter instance."""
    from angela.components.shell.formatter import TerminalFormatter, terminal_formatter # Import Class and instance
    return registry.get_or_create("terminal_formatter", TerminalFormatter, factory=lambda: terminal_formatter)

# Output Type Enum
def get_output_type_enum():
    """Get the OutputType enum from formatter."""
    from angela.components.shell.formatter import OutputType
    return OutputType

# Inline Feedback API
def get_inline_feedback():
    """Get the inline feedback instance."""
    from angela.components.shell.inline_feedback import InlineFeedback, inline_feedback # Import Class and instance
    return registry.get_or_create("inline_feedback", InlineFeedback, factory=lambda: inline_feedback)

# Completion Handler API
def get_completion_handler():
    """Get the completion handler instance."""
    from angela.components.shell.completion import CompletionHandler, completion_handler # Import Class and instance
    return registry.get_or_create("completion_handler", CompletionHandler, factory=lambda: completion_handler)

# Advanced Formatter API Functions
async def display_advanced_plan(plan: Any) -> None:
    """
    Display an advanced task plan with rich formatting.
    
    Args:
        plan: The advanced task plan to display
    """
    from angela.components.shell.advanced_formatter import display_advanced_plan as _display_advanced_plan
    await _display_advanced_plan(plan)

async def display_execution_results(plan: Any, results: Dict[str, Any]) -> None:
    """
    Display execution results for an advanced task plan.
    
    Args:
        plan: The executed advanced task plan
        results: The execution results
    """
    from angela.components.shell.advanced_formatter import display_execution_results as _display_execution_results
    await _display_execution_results(plan, results)

async def display_step_details(step_id: str, result: Dict[str, Any], plan: Optional[Any] = None) -> None:
    """
    Display detailed results for a specific step.
    
    Args:
        step_id: ID of the step
        result: The step's execution result
        plan: Optional plan for context
    """
    from angela.components.shell.advanced_formatter import display_step_details as _display_step_details
    await _display_step_details(step_id, result, plan)

async def display_step_error(step_id: str, error: str, step_type: str, description: str) -> None:
    """
    Display an error that occurred during step execution.
    
    Args:
        step_id: ID of the failed step
        error: Error message
        step_type: Type of the step
        description: Step description
    """
    from angela.components.shell.advanced_formatter import display_step_error as _display_step_error
    await _display_step_error(step_id, error, step_type, description)
    
    
    
async def display_pre_confirmation_info(
    command: str,
    risk_level: int,
    risk_reason: str,
    impact: Dict[str, Any],
    explanation: Optional[str] = None,
    preview: Optional[str] = None,
    confidence_score: Optional[float] = None,
    execution_time: Optional[float] = None
) -> None:
    """
    Display a comprehensive pre-confirmation information block.
    
    Args:
        command: The command to be executed
        risk_level: Risk level (0-4)
        risk_reason: Reason for the risk assessment
        impact: Impact analysis dictionary
        explanation: Optional explanation of the command
        preview: Optional preview of command execution
        confidence_score: Optional AI confidence score (0-1)
        execution_time: Optional execution time if this is post-execution
    """
    from angela.components.shell.formatter import terminal_formatter
    await terminal_formatter.display_pre_confirmation_info(
        command=command,
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact=impact,
        explanation=explanation,
        preview=preview,
        confidence_score=confidence_score,
        execution_time=execution_time
    )


async def display_inline_confirmation(
    prompt_text: str = "Proceed with execution?"
) -> bool:
    """
    Display an inline confirmation prompt and get user input.
    
    Args:
        prompt_text: The confirmation prompt text
        
    Returns:
        True if confirmed, False otherwise
    """
    from angela.components.shell.formatter import terminal_formatter
    return await terminal_formatter.display_inline_confirmation(prompt_text)

async def display_execution_timer(
    command: str,
    with_philosophy: bool = True
) -> Tuple[str, str, int, float]:
    """
    Display a command execution timer with philosophy quotes.
    
    Args:
        command: The command being executed
        with_philosophy: Whether to display philosophy quotes
        
    Returns:
        Tuple of (stdout, stderr, return_code, execution_time)
    """
    from angela.components.shell.formatter import terminal_formatter
    return await terminal_formatter.display_execution_timer(command, with_philosophy)

async def display_loading_timer(
    message: str,
    with_philosophy: bool = True
) -> None:
    """
    Display a loading timer with optional philosophy quotes.
    
    Args:
        message: The loading message to display
        with_philosophy: Whether to display philosophy quotes
    """
    from angela.components.shell.formatter import terminal_formatter
    await terminal_formatter.display_loading_timer(message, with_philosophy)

def get_inline_feedback():
    """Get the inline feedback instance."""
    from angela.components.shell.inline_feedback import InlineFeedback, inline_feedback
    return inline_feedback
