# angela/components/safety/__init__.py
"""
Safety validation for Angela CLI operations.

This package provides functionality to validate and confirm potentially risky
operations before execution, including command classification, preview generation,
and adaptive confirmation based on user preferences.
"""
from .classifier import command_risk_classifier
from .validator import validate_command_safety, validate_operation
from .preview import generate_preview
from .confirmation import get_confirmation, requires_confirmation
from .adaptive_confirmation import get_adaptive_confirmation, offer_command_learning


def classify_command_risk(command: str):
    return command_risk_classifier.classify(command)

def analyze_command_impact(command: str): 
    return command_risk_classifier.analyze_impact(command)
    
    
# Define the main safety check function
async def check_command_safety(command: str, dry_run: bool = False) -> bool:
    is_valid, error_message = validate_command_safety(command)
    if not is_valid:
        logger.warning(f"Command validation failed: {error_message}")
        return False

    risk_level, risk_reason = command_risk_classifier.classify(command) # Use instance
    impact = command_risk_classifier.analyze_impact(command)          # Use instance
    preview_text = await generate_preview(command)

    confirmed = await get_confirmation(
        command=command, risk_level=risk_level, risk_reason=risk_reason,
        impact=impact, preview=preview_text, dry_run=dry_run
    )
    if not confirmed:
        logger.info(f"Command execution cancelled by user: {command}")
        return False
    return True

async def check_operation_safety(operation_type: str, params: dict, dry_run: bool = False) -> bool:
    is_valid, error_message = validate_operation(operation_type, params)
    if not is_valid:
        logger.warning(f"Operation validation failed: {error_message}")
        return False

    if operation_type == 'execute_command':
        return await check_command_safety(params.get('command', ''), dry_run)

    from angela.constants import RISK_LEVELS
    risk_level = RISK_LEVELS["MEDIUM"]
    risk_reason = f"File operation: {operation_type}"

    if operation_type in ['delete_file', 'delete_directory']:
        risk_level = RISK_LEVELS["HIGH"]
    elif operation_type in ['create_file', 'create_directory']:
        risk_level = RISK_LEVELS["LOW"]

    impact = {
        "operations": [operation_type],
        "affected_files": [params.get('path')] if 'path' in params else [],
        "affected_dirs": [params.get('path')] if operation_type.endswith('directory') and 'path' in params else [],
        "destructive": operation_type.startswith('delete'),
        "creates_files": operation_type.startswith('create'),
        "modifies_files": operation_type in ['write_file', 'move_file', 'copy_file']
    }
    confirmed = await get_confirmation(
        command=f"{operation_type}: {params}", risk_level=risk_level, risk_reason=risk_reason,
        impact=impact, preview=None, dry_run=dry_run
    )
    if not confirmed:
        logger.info(f"Operation cancelled by user: {operation_type} {params}")
        return False
    return True

def register_safety_functions():
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("check_operation_safety", check_operation_safety)
    logger.debug("Safety functions registered.")

__all__ = [
    'check_command_safety', 'check_operation_safety',
    'validate_command_safety', 'validate_operation',
    'classify_command_risk',      # Exporting the new function defined in this __init__.py
    'analyze_command_impact',     # Exporting the new function defined in this __init__.py
    'command_risk_classifier',    # Still exporting the instance for direct use if any component needs it
    'generate_preview', 'get_confirmation', 'requires_confirmation',
    'get_adaptive_confirmation', 'offer_command_learning',
    'register_safety_functions'
]

def register_safety_functions():
    """Register safety functions to the registry to avoid circular imports."""
    # Import inside function to avoid circular imports
    from angela.core.registry import registry
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("check_operation_safety", check_operation_safety)
