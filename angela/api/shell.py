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
    from angela.components.shell.formatter import terminal_formatter
    return registry.get_or_create("terminal_formatter", lambda: terminal_formatter)

# Output Type Enum
def get_output_type_enum():
    """Get the OutputType enum from formatter."""
    from angela.components.shell.formatter import OutputType
    return OutputType

# Inline Feedback API
def get_inline_feedback():
    """Get the inline feedback instance."""
    from angela.components.shell.inline_feedback import inline_feedback
    return registry.get_or_create("inline_feedback", lambda: inline_feedback)

# Completion Handler API
def get_completion_handler():
    """Get the completion handler instance."""
    from angela.components.shell.completion import completion_handler
    return registry.get_or_create("completion_handler", lambda: completion_handler)

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
