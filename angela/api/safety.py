"""
Public API for safety components.

This module provides functions to access safety components with lazy initialization.
"""
from typing import Optional, Type, Any, Dict, List, Union, Callable, Tuple

from angela.core.registry import registry

# Command Validator API
def get_command_validator():
    """Get the command validator instance."""
    from angela.components.safety.validator import command_validator
    return registry.get_or_create("command_validator", lambda: command_validator)

# Command Risk Classifier API
def get_command_risk_classifier():
    """Get the command risk classifier instance."""
    from angela.components.safety.classifier import command_risk_classifier
    return registry.get_or_create("command_risk_classifier", lambda: command_risk_classifier)

# Confirmation Helper API
def get_confirmation_helper():
    """Get the confirmation helper instance."""
    from angela.components.safety.confirmation import confirmation_helper
    return registry.get_or_create("confirmation_helper", lambda: confirmation_helper)

# Adaptive Confirmation API
def get_adaptive_confirmation():
    """Get the adaptive confirmation instance."""
    from angela.components.safety.adaptive_confirmation import adaptive_confirmation
    return registry.get_or_create("adaptive_confirmation", lambda: adaptive_confirmation)

# Command Preview API
def get_command_preview_generator():
    """Get the command preview generator instance."""
    from angela.components.safety.preview import command_preview_generator
    return registry.get_or_create("command_preview_generator", lambda: command_preview_generator)

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

def classify_command_risk(command: str) -> Dict[str, Any]:
    """
    Classify the risk level of a command.
    
    Args:
        command: Command to classify
        
    Returns:
        Dictionary with risk classification
    """
    classifier = get_command_risk_classifier()
    return classifier.classify(command)

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
