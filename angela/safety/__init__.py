# angela/safety/__init__.py
"""
Safety validation for Angela CLI operations.

This package provides functionality to validate and confirm potentially risky
operations before execution, including command classification, preview generation,
and adaptive confirmation based on user preferences.
"""
from .classifier import classify_command_risk, analyze_command_impact
from .validator import validate_command_safety
from .preview import generate_preview
from .confirmation import get_confirmation, requires_confirmation
from .adaptive_confirmation import get_adaptive_confirmation, offer_command_learning

# Define the main safety check function
async def check_command_safety(command: str, dry_run: bool = False) -> bool:
    """
    Check if a command is safe to execute and obtain user confirmation if needed.
    
    Args:
        command: The shell command to check.
        dry_run: Whether this is a dry run (show preview without executing).
        
    Returns:
        True if the command is safe and confirmed, False otherwise.
    """
    # Step 1: Validate basic safety constraints
    is_valid, error_message = validate_command_safety(command)
    if not is_valid:
        logger.warning(f"Command validation failed: {error_message}")
        return False
    
    # Step 2: Classify the risk level
    risk_level, risk_reason = classify_command_risk(command)
    
    # Step 3: Analyze the command impact
    impact = analyze_command_impact(command)
    
    # Step 4: Generate preview if possible
    preview = await generate_preview(command)
    
    # Step 5: Get user confirmation based on risk level
    confirmed = await get_confirmation(
        command=command,
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact=impact,
        preview=preview,
        dry_run=dry_run
    )
    
    if not confirmed:
        logger.info(f"Command execution cancelled by user: {command}")
        return False
    
    return True

# Import these here to avoid circular imports since they're used within the function
from angela.utils.logging import get_logger
logger = get_logger(__name__)

# Make these available to modules that import from this package
__all__ = [
    'check_command_safety',
    'validate_command_safety',
    'classify_command_risk',
    'analyze_command_impact',
    'generate_preview',
    'get_confirmation',
    'get_adaptive_confirmation',
    'offer_command_learning',
    'requires_confirmation'
]

# Register these functions to be accessible via the service registry
# This avoids circular imports when other modules need these functions
from angela.core.registry import registry
registry.register("check_command_safety", check_command_safety)
registry.register("validate_command_safety", validate_command_safety)
