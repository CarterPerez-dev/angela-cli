"""
Safety system for Angela CLI.

This module provides a unified interface to the safety system components:
- Risk classification
- Operation validation
- User confirmation
- Command previews
"""

from angela.safety.classifier import classify_command_risk, analyze_command_impact
from angela.safety.validator import validate_command_safety, validate_operation, ValidationError
from angela.safety.confirmation import get_confirmation, requires_confirmation
from angela.safety.preview import generate_preview

from angela.utils.logging import get_logger

logger = get_logger(__name__)


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


async def check_operation_safety(
    operation_type: str, 
    params: dict, 
    dry_run: bool = False
) -> bool:
    """
    Check if a high-level operation is safe to execute and obtain user confirmation if needed.
    
    Args:
        operation_type: The type of operation (e.g., 'create_file', 'delete_file').
        params: Parameters for the operation.
        dry_run: Whether this is a dry run (show preview without executing).
        
    Returns:
        True if the operation is safe and confirmed, False otherwise.
    """
    # Step 1: Validate the operation
    is_valid, error_message = validate_operation(operation_type, params)
    if not is_valid:
        logger.warning(f"Operation validation failed: {error_message}")
        return False
    
    # Step 2: Convert to a command if possible for risk analysis
    command = None
    if operation_type == 'execute_command':
        command = params.get('command', '')
    elif operation_type == 'create_file':
        command = f"touch {params.get('path', '')}"
    elif operation_type == 'write_file':
        command = f"echo '...' > {params.get('path', '')}"
    elif operation_type == 'delete_file':
        command = f"rm {params.get('path', '')}"
    elif operation_type == 'create_directory':
        command = f"mkdir -p {params.get('path', '')}"
    elif operation_type == 'delete_directory':
        command = f"rmdir {params.get('path', '')}"
    
    # If we have a command representation, use the command safety check
    if command:
        return await check_command_safety(command, dry_run)
    
    # For operations without a command representation, use a simplified approach
    # Determine risk level based on operation type
    if operation_type in ['delete_file', 'delete_directory']:
        risk_level = 3  # HIGH
        risk_reason = f"Deleting {operation_type.split('_')[1]}"
    elif operation_type in ['write_file', 'create_file', 'create_directory']:
        risk_level = 1  # LOW
        risk_reason = f"Creating {operation_type.split('_')[1]}"
    else:
        risk_level = 2  # MEDIUM
        risk_reason = f"Unknown operation type: {operation_type}"
    
    # Get user confirmation
    confirmed = await get_confirmation(
        command=f"{operation_type}: {params}",
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact={"operations": [operation_type], "affected_files": [params.get('path', '')]},
        preview=None,
        dry_run=dry_run
    )
    
    if not confirmed:
        logger.info(f"Operation cancelled by user: {operation_type}")
        return False
    
    return True
