# angela/components/safety/__init__.py
"""
Safety validation for Angela CLI operations.

This package provides functionality to validate and confirm potentially risky
operations before execution, including command classification, preview generation,
and adaptive confirmation based on user preferences.
"""
from .classifier import classify_command_risk, analyze_command_impact
from .validator import validate_command_safety, validate_operation
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


# Add this after the check_command_safety function
async def check_operation_safety(operation_type: str, params: dict, dry_run: bool = False) -> bool:
    """
    Check if an operation is safe to execute and obtain user confirmation if needed.
    
    Args:
        operation_type: The type of operation (e.g., 'create_file', 'delete_directory').
        params: Parameters for the operation.
        dry_run: Whether this is a dry run (show preview without executing).
        
    Returns:
        True if the operation is safe and confirmed, False otherwise.
    """
    # Step 1: Validate basic safety constraints
    is_valid, error_message = validate_operation(operation_type, params)
    if not is_valid:
        logger.warning(f"Operation validation failed: {error_message}")
        return False
    
    # Step 2: For command operations, use the command safety check
    if operation_type == 'execute_command':
        return await check_command_safety(params.get('command', ''), dry_run)
    
    # Step 3: For file operations, analyze the risk level
    # Default to MEDIUM risk for most operations
    from angela.constants import RISK_LEVELS
    risk_level = RISK_LEVELS["MEDIUM"]
    risk_reason = f"File operation: {operation_type}"
    
    # Adjust risk level based on operation type
    if operation_type in ['delete_file', 'delete_directory']:
        risk_level = RISK_LEVELS["HIGH"]
        risk_reason = f"Destructive file operation: {operation_type}"
    elif operation_type in ['create_file', 'create_directory']:
        risk_level = RISK_LEVELS["LOW"]
        risk_reason = f"File creation: {operation_type}"
    
    # Step 4: Create an impact analysis
    impact = {
        "operations": [operation_type],
        "affected_files": [params.get('path')] if 'path' in params else [],
        "affected_dirs": [params.get('path')] if operation_type.endswith('directory') and 'path' in params else [],
        "destructive": operation_type.startswith('delete'),
        "creates_files": operation_type.startswith('create'),
        "modifies_files": operation_type in ['write_file', 'move_file', 'copy_file']
    }
    
    # Step 5: Get user confirmation based on risk level
    confirmed = await get_confirmation(
        command=f"{operation_type}: {params}",
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact=impact,
        preview=None,  # No preview for file operations
        dry_run=dry_run
    )
    
    if not confirmed:
        logger.info(f"Operation cancelled by user: {operation_type} {params}")
        return False
    
    return True
    
# Import these here to avoid circular imports since they're used within the function
from angela.utils.logging import get_logger
logger = get_logger(__name__)

__all__ = [
    'check_command_safety',
    'check_operation_safety', 
    'validate_command_safety',
    'validate_operation',
    'classify_command_risk',
    'analyze_command_impact',
    'generate_preview',
    'get_confirmation',
    'get_adaptive_confirmation',
    'offer_command_learning',
    'requires_confirmation'
]

def register_safety_functions():
    """Register safety functions to the registry to avoid circular imports."""
    # Import inside function to avoid circular imports
    from angela.core.registry import registry
    registry.register("check_command_safety", check_command_safety)
    registry.register("validate_command_safety", validate_command_safety)
    registry.register("check_operation_safety", check_operation_safety)
