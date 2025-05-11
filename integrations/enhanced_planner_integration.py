# angela/integrations/enhanced_planner_integration.py
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

from angela.utils.logging import get_logger

logger = get_logger(__name__)

def apply_enhanced_planner_integration():
    """Apply the enhanced task planner integration to the Orchestrator class."""
    logger.info("Applying enhanced task planner integration")
    
    try:
        # Import these here to avoid circular imports
        from angela.orchestrator import Orchestrator, RequestType
        
        # First try to import the enhanced task planner directly
        try:
            from angela.intent.enhanced_task_planner import enhanced_task_planner
            logger.info("Successfully imported enhanced_task_planner")
        except ImportError as e:
            logger.warning(f"Could not import enhanced_task_planner directly: {e}")
            # Fall back to trying to import from planner (after our fix)
            try:
                from angela.intent.planner import task_planner as enhanced_task_planner
                logger.info("Using task_planner as fallback for enhanced_task_planner")
            except ImportError:
                logger.error("Could not import any task planner, enhanced integration will be limited")
                return
        
        # Import planning models
        from angela.intent.planner import (
            TaskPlan, PlanStep, 
            AdvancedTaskPlan, AdvancedPlanStep, PlanStepType
        )
        
        # Import the shell formatter
        from angela.shell.formatter import terminal_formatter
        
        # Store original method for fallback
        original_process_multi_step = Orchestrator._process_multi_step_request
        
        # Define enhanced process method with fallback to original
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
            
            try:
                # Determine complexity for planning
                complexity = await enhanced_task_planner._determine_complexity(request)
                self._logger.debug(f"Determined plan complexity: {complexity}")
                
                # Start a transaction for this multi-step operation
                transaction_id = None
                if not dry_run:
                    rollback_manager = self._get_rollback_manager()
                    if rollback_manager:
                        transaction_id = await rollback_manager.start_transaction(f"Multi-step plan: {request[:50]}...")
                
                # Create a plan based on complexity
                if complexity == "advanced":
                    # Use the advanced planner for complex tasks
                    plan = await enhanced_task_planner.plan_task(request, context, complexity)
                    
                    # Record the plan in the transaction
                    if transaction_id:
                        await self._record_plan_in_transaction(plan, transaction_id)
                    
                    # Create result with the plan
                    result = await self._handle_advanced_plan_execution(plan, request, context, execute, dry_run, transaction_id)
                else:
                    # Use the basic planner for simple tasks
                    plan = await enhanced_task_planner.plan_task(request, context)
                    result = await self._handle_basic_plan_execution(plan, request, context, execute, dry_run, transaction_id)
                
                return result
                
            except Exception as e:
                # Handle any exceptions and end the transaction
                self._logger.exception(f"Error in enhanced multi-step processing: {str(e)}")
                self._logger.info("Falling back to original multi-step processing method")
                
                # Fall back to original method
                return await original_process_multi_step(self, request, context, execute, dry_run)
        
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
                    
                    execution_results = await enhanced_task_planner.execute_plan(
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
        
        # Define other methods to be patched onto the Orchestrator
        async def _handle_basic_plan_execution(
            self,
            plan: TaskPlan,
            request: str,
            context: Dict[str, Any],
            execute: bool,
            dry_run: bool,
            transaction_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Handle execution of a basic plan."""
            # Use the original functionality from orchestrator if available
            if hasattr(self, "_process_basic_multi_step"):
                return await self._process_basic_multi_step(plan, request, context, execute, dry_run, transaction_id)
            
            # Create result with the plan
            result = {
                "request": request,
                "type": "multi_step",
                "context": context,
                "plan": {
                    "goal": plan.goal,
                    "steps": [
                        {
                            "command": step.command,
                            "explanation": step.explanation,
                            "dependencies": step.dependencies,
                            "risk": step.estimated_risk
                        }
                        for step in plan.steps
                    ],
                    "step_count": len(plan.steps)
                }
            }
            
            # Execute the plan if requested
            if execute or dry_run:
                # Display the plan
                await terminal_formatter.display_task_plan(plan)
                
                # Get confirmation for plan execution
                from prompt_toolkit.shortcuts import yes_no_dialog
                confirmed = dry_run or yes_no_dialog(
                    title="Confirm Plan Execution",
                    text=f"Do you want to execute this {len(plan.steps)}-step plan?",
                ).run()
                
                if confirmed or dry_run:
                    # Execute the plan
                    execution_results = await enhanced_task_planner.execute_plan(
                        plan, 
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    
                    result["execution_results"] = execution_results
                    result["success"] = all(r.get("success", False) for r in execution_results)
                    
                    # Update transaction status
                    if transaction_id:
                        rollback_manager = self._get_rollback_manager()
                        if rollback_manager:
                            status = "completed" if result["success"] else "failed"
                            await rollback_manager.end_transaction(transaction_id, status)
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
            from rich.console import Console
            from rich.panel import Panel
            
            console = Console()
            
            # Show warnings for high-risk plans
            if has_high_risk:
                console.print(Panel(
                    "⚠️  [bold red]This plan includes HIGH RISK operations[/bold red] ⚠️\n"
                    "Some of these steps could make significant changes to your system.",
                    border_style="red",
                    expand=False
                ))
            
            # Show complexity warning for advanced plans
            if has_complex_steps:
                console.print(Panel(
                    "[bold yellow]This plan includes advanced steps (code execution, API calls, loops).[/bold yellow]",
                    border_style="yellow",
                    expand=False
                ))
            
            # Get confirmation
            confirmed = yes_no_dialog(
                title="Confirm Advanced Plan Execution",
                text=f"Do you want to execute this {len(plan.steps)}-step advanced plan?",
            ).run()
            
            return confirmed
        
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
        
        # Patch the methods onto the Orchestrator class with proper binding
        Orchestrator._process_multi_step_request = enhanced_process_multi_step_request.__get__(
            None, Orchestrator
        )
        Orchestrator._handle_advanced_plan_execution = _handle_advanced_plan_execution.__get__(
            None, Orchestrator
        )
        Orchestrator._handle_basic_plan_execution = _handle_basic_plan_execution.__get__(
            None, Orchestrator
        )
        Orchestrator._display_advanced_plan = _display_advanced_plan.__get__(
            None, Orchestrator
        )
        Orchestrator._confirm_advanced_plan_execution = _confirm_advanced_plan_execution.__get__(
            None, Orchestrator
        )
        Orchestrator._extract_initial_variables = _extract_initial_variables.__get__(
            None, Orchestrator
        )
        Orchestrator._get_rollback_manager = _get_rollback_manager.__get__(
            None, Orchestrator
        )
        Orchestrator._record_plan_in_transaction = _record_plan_in_transaction.__get__(
            None, Orchestrator
        )
        
        logger.info("Enhanced task planner integration applied to Orchestrator successfully")
        
    except ImportError as e:
        logger.error(f"Failed to apply enhanced planner integration: {str(e)}")
        logger.error("Advanced planning capabilities will be limited")
    except Exception as e:
        logger.exception(f"Error applying enhanced planner integration: {str(e)}")
        logger.error("Advanced planning capabilities will be limited")
