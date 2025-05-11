# angela/api/interfaces.py
"""
Public API for interface components.

This module provides functions to access interface components.
"""

def get_command_executor_class():
    """Get the CommandExecutor abstract base class."""
    from angela.components.interfaces.execution import CommandExecutor
    return CommandExecutor

def get_adaptive_executor_class():
    """Get the AdaptiveExecutor abstract base class."""
    from angela.components.interfaces.execution import AdaptiveExecutor
    return AdaptiveExecutor

def get_safety_validator_class():
    """Get the SafetyValidator abstract base class."""
    from angela.components.interfaces.safety import SafetyValidator
    return SafetyValidator
