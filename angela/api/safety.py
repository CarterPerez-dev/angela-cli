"""
Public API for safety components.

This module provides functions to access safety components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable, Tuple

from angela.core.registry import registry

# Command Validator API
def get_command_validator():
    """Get the command validator instance."""
    from angela.components.safety.validator import CommandValidator, command_validator
    return registry.get_or_create("command_validator", CommandValidator, factory=lambda: command_validator)


# Command Risk Classifier API
def get_command_risk_classifier():
    """Get the command risk classifier instance."""
    from angela.components.safety.classifier import command_risk_classifier
    return registry.get_or_create("command_risk_classifier", lambda: command_risk_classifier)

# Confirmation Helper API
def get_confirmation_helper():
    """Get the confirmation helper instance."""
    from angela.components.safety.confirmation import ConfirmationHelper, confirmation_helper
    return registry.get_or_create("confirmation_helper", ConfirmationHelper, factory=lambda: confirmation_helper)

# Adaptive Confirmation API
def get_adaptive_confirmation():
    """Get the adaptive confirmation handler function."""
    from angela.components.safety.adaptive_confirmation import get_adaptive_confirmation as confirmation_func
    return confirmation_func

# Command Preview API
def get_command_preview_generator():
    """Get the command preview generator instance."""
    from angela.components.safety.preview import command_preview_generator
    return registry.get_or_create("command_preview_generator", lambda: command_preview_generator)

# Additional functions needed by components
def get_validate_command_safety_func():
    """Get the validate_command_safety function."""
    from angela.components.safety import validate_command_safety
    return validate_command_safety

def get_operation_safety_checker():
    """Get the check_operation_safety function."""
    from angela.components.safety import check_operation_safety
    return check_operation_safety

def get_command_learning_handler():
    """Get the command learning handler function."""
    from angela.components.safety.adaptive_confirmation import offer_command_learning
    return offer_command_learning

def get_command_impact_analyzer():
    """Get the command impact analyzer."""
    from angela.components.safety.classifier import analyze_command_impact
    return analyze_command_impact

def get_adaptive_confirmation_handler():
    """Get the adaptive confirmation handler."""
    from angela.components.safety.adaptive_confirmation import get_adaptive_confirmation
    return get_adaptive_confirmation

# Helper functions for direct validation
def validate_command(command: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a command for safety.
    
    Args:
        command: Command to validate
        
    Returns:
        Tuple of (is_safe, error_message)
    """
    validator = get_command_validator()
    return validator(command)

def classify_command_risk(command: str) -> Tuple[int, str]:
    """ API: Classify the risk level of a command. """
    from angela.components.safety import classify_command_risk as classify_fn
    return classify_fn(command)

def analyze_command_impact(command: str) -> Dict[str, Any]:
    """ API: Analyze the potential impact of a command. """
    from angela.components.safety import analyze_command_impact as analyze_fn 
    return analyze_fn(command)

def generate_command_preview(command: str) -> Dict[str, Any]:
    """
    Generate a preview of what a command will do.
    
    Args:
        command: Command to preview
        
    Returns:
        Dictionary with preview information
    """
    preview_generator = get_command_preview_generator()
    return preview_generator.generate_preview(command)
