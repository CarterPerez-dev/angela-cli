"""
Integration for the Enhanced Task Planner into Angela's Orchestration system.

This module extends the orchestrator to fully support advanced plan execution
with all step types (CODE, API, LOOP, etc.) and proper data flow.
"""
import os
import re
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set

from angela.orchestrator import Orchestrator, RequestType
from angela.intent.planner import (
    task_planner, TaskPlan, PlanStep, 
    AdvancedTaskPlan, AdvancedPlanStep, PlanStepType
)
from angela.utils.logging import get_logger
from angela.shell.formatter import terminal_formatter

logger = get_logger(__name__)

# Patch the Orchestrator._process_multi_step_request method to use the enhanced task planner
async def enhanced_process_multi_step_request(
    self, 
    request: str, 
    context: Dict[str, Any], 
    execute: bool, 
    dry_run: bool
) -> Dict[str, Any]:
    """
    Process a multi-step operation request with enhanced execution capabilities.
    
    Args:
        request: The user request
        context: Context information
        execute: Whether to execute the commands
        dry_run: Whether to simulate execution without making changes
        
    Returns:
        Dictionary with processing results
    """
    self._logger.info(f"Processing multi-step request with enhanced capabilities: {request}")
    
    # Determine complexity for planning
    complexity = await task_planner._determine_complexity(request)
    self._logger.debug(f"Determined plan complexity: {complexity}")
    
    # Start a transaction for this multi-step operation
    transaction_id = None
    if not dry_run:
        rollback_manager = self._get_rollback_manager()
        if rollback_manager:
            transaction_id = await rollback_manager.start_transaction(f"Multi-step plan: {request[:50]}...")
    
    try:
        # Create a plan based on complexity
        if complexity == "advanced":
            # Use the advanced planner for complex tasks
            plan = await task_planner.plan_task(request, context, complexity)
            
            # Record the plan in the transaction
            if transaction_id:
                await self._record_plan_in_transaction(plan, transaction_id)
            
            # Create result with the plan
            result = await self._handle_advanced_plan_execution(plan, request, context, execute, dry_run, transaction_id)
        else:
            # Use the basic planner for simple tasks
            plan = await task_planner.plan_task(request, context)
            result = await self._handle_basic_plan_execution(plan, request, context, execute, dry_run, transaction_id)
        
        return result
        
    except Exception as e:
        # Handle any exceptions and end the transaction
        if transaction_id:
            rollback_manager = self._get_rollback_manager()
            if rollback_manager:
                await rollback_manager.end_transaction(transaction_id, "failed")
        
        self._logger.exception(f"Error processing multi-step request: {str(e)}")
        raise
        
async def _handle_advanced_plan_execution(
    self,
    plan: AdvancedTaskPlan,
    request: str,
    context: Dict[str, Any],
    execute: bool,
    dry_run: bool,
    transaction_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle execution of an advanced plan.
    
    Args:
        plan: The advanced plan to execute
        request: The original request
        context: Context information
        execute: Whether to execute commands
        dry_run: Whether to simulate execution
        transaction_id: Transaction ID for rollback
        
    Returns:
        Dictionary with results
    """
    # Create result structure with the plan
    result = {
        "request": request,
        "type": "advanced_multi_step",
        "context": context,
        "plan": {
            "id": plan.id,
            "goal": plan.goal,
            "description": plan.description,
            "steps": [
                {
                    "id": step_id,
                    "type": step.type,
                    "description": step.description,
                    "command": getattr(step, "command", None),
                    "dependencies": step.dependencies,
                    "risk": step.estimated_risk
                }
                for step_id, step in plan.steps.items()
            ],
            "entry_points": plan.entry_points,
            "step_count": len(plan.steps)
        }
    }
    
    # Display the plan for the user
    await self._display_advanced_plan(plan)
    
    # Execute the plan if requested
    if execute or dry_run:
        # Get confirmation for plan execution
        confirmed = await self._confirm_advanced_plan_execution(plan, dry_run)
        
        if confirmed or dry_run:
            # Execute the plan with initial variables from context if needed
            initial_variables = self._extract_initial_variables(context)
            
            execution_results = await task_planner.execute_plan(
                plan, 
                dry_run=dry_run,
                transaction_id=transaction_id,
                initial_variables=initial_variables
            )
            
            result["execution_results"] = execution_results
            result["success"] = execution_results.get("success", False)
            
            # Update transaction status
            if transaction_id:
                rollback_manager = self._get_rollback_manager()
                if rollback_manager:
                    status = "completed" if result["success"] else "failed"
                    await rollback_manager.end_transaction(transaction_id, status)
                    
            # For failed steps, show error information
            if not result["success"]:
                failed_step = execution_results.get("failed_step")
                if failed_step and failed_step in execution_results.get("results", {}):
                    step_result = execution_results["results"][failed_step]
                    error_msg = step_result.get("error", "Unknown error")
                    self._logger.error(f"Step {failed_step} failed: {error_msg}")
                    
                    # Format error for display
                    await terminal_formatter.display_step_error(
                        failed_step,
                        error_msg,
                        step_result.get("type", "unknown"),
                        step_result.get("description", "")
                    )
        else:
            result["cancelled"] = True
            result["success"] = False
            
            # End the transaction as cancelled
            if transaction_id:
                rollback_manager = self._get_rollback_manager()
                if rollback_manager:
                    await rollback_manager.end_transaction(transaction_id, "cancelled")
    
    return result

async def _display_advanced_plan(
    self,
    plan: AdvancedTaskPlan
) -> None:
    """
    Display an advanced task plan to the user.
    
    Args:
        plan: The advanced plan to display
    """
    await terminal_formatter.display_advanced_plan(plan)

async def _confirm_advanced_plan_execution(
    self, 
    plan: AdvancedTaskPlan, 
    dry_run: bool
) -> bool:
    """
    Get confirmation for executing an advanced plan.
    
    Args:
        plan: The plan to execute
        dry_run: Whether this is a dry run
        
    Returns:
        True if confirmed, False otherwise
    """
    if dry_run:
        # No confirmation needed for dry run
        return True
    
    # Check if any steps are high risk
    has_high_risk = any(step.estimated_risk >= 3 for step in plan.steps.values())
    
    # Check for certain step types that might need extra caution
    has_complex_steps = any(step.type in [PlanStepType.CODE, PlanStepType.API, PlanStepType.LOOP] 
                           for step in plan.steps.values())
    
    # Import confirmation dialog
    from prompt_toolkit.shortcuts import yes_no_dialog
    
    # Build warning/information message
    message = f"Do you want to execute this advanced plan with {len(plan.steps)} steps?"
    
    if has_high_risk:
        message = f"⚠️  [WARNING] This plan includes HIGH RISK operations that could significantly change your system.\n\n{message}"
    
    if has_complex_steps:
        message += "\n\nThis plan includes advanced steps like code execution, API calls, or loops."
    
    # Get confirmation with appropriate styling
    return yes_no_dialog(
        title="Confirm Advanced Plan Execution",
        text=message
    ).run()

def _extract_initial_variables(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract variables from context to use as initial variables for plan execution.
    
    Args:
        context: Context information
        
    Returns:
        Dictionary of variables
    """
    initial_vars = {}
    
    # Extract relevant information from context
    if "cwd" in context:
        initial_vars["current_directory"] = context["cwd"]
    
    if "project_root" in context:
        initial_vars["project_root"] = context["project_root"]
    
    if "project_type" in context:
        initial_vars["project_type"] = context["project_type"]
    
    if "enhanced_project" in context:
        # Extract useful project information
        project_info = context["enhanced_project"]
        if "type" in project_info:
            initial_vars["project_type"] = project_info["type"]
        
        if "frameworks" in project_info:
            initial_vars["frameworks"] = project_info["frameworks"]
        
        if "dependencies" in project_info and "top_dependencies" in project_info["dependencies"]:
            initial_vars["dependencies"] = project_info["dependencies"]["top_dependencies"]
    
    if "resolved_files" in context:
        # Extract resolved file references
        files = {}
        for ref in context["resolved_files"]:
            ref_name = ref.get("reference", "").replace(" ", "_")
            if ref_name and "path" in ref:
                files[ref_name] = ref["path"]
        
        if files:
            initial_vars["files"] = files
    
    # Add session-specific information
    if "session" in context and "entities" in context["session"]:
        entities = {}
        for name, entity in context["session"].get("entities", {}).items():
            if "type" in entity and "value" in entity:
                entities[name] = {
                    "type": entity["type"],
                    "value": entity["value"]
                }
        
        if entities:
            initial_vars["entities"] = entities
    
    return initial_vars

def _get_rollback_manager(self):
    """Get the rollback manager from the registry."""
    from angela.core.registry import registry
    return registry.get("rollback_manager")

async def _record_plan_in_transaction(self, plan, transaction_id):
    """Record a plan in a transaction."""
    rollback_manager = self._get_rollback_manager()
    if rollback_manager:
        await rollback_manager.record_plan_execution(
            plan_id=plan.id,
            goal=plan.goal,
            plan_data=plan.dict(),
            transaction_id=transaction_id
        )

# Function to apply the patches to the Orchestrator class
def apply_enhanced_planner_integration():
    """Apply the enhanced task planner integration to the Orchestrator class."""
    # Patch the _process_multi_step_request method
    Orchestrator._process_multi_step_request = enhanced_process_multi_step_request
    
    # Add new methods to the Orchestrator class
    Orchestrator._handle_advanced_plan_execution = _handle_advanced_plan_execution
    Orchestrator._display_advanced_plan = _display_advanced_plan
    Orchestrator._confirm_advanced_plan_execution = _confirm_advanced_plan_execution
    Orchestrator._extract_initial_variables = _extract_initial_variables
    Orchestrator._get_rollback_manager = _get_rollback_manager
    Orchestrator._record_plan_in_transaction = _record_plan_in_transaction
    
    logger.info("Enhanced task planner integration applied to Orchestrator")

# Apply the patches when this module is imported
apply_enhanced_planner_integration()
