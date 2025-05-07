"""
Enhanced execution system for complex task orchestration in Angela CLI.

This module extends the TaskPlanner with robust support for advanced execution steps,
including code execution, API integration, looping constructs, and intelligent
data flow between steps.
"""
import os
import re
import json
import shlex
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union, Callable
from datetime import datetime
import uuid
import logging
import aiohttp
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from angela.intent.models import ActionPlan, Intent, IntentType
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.execution.error_recovery import ErrorRecoveryManager
from angela.execution.engine import execution_engine
from angela.safety.validator import validate_command_safety
from angela.core.registry import registry

# Reuse existing models from angela/intent/planner.py
from angela.intent.planner import (
    PlanStep, TaskPlan, PlanStepType, AdvancedPlanStep, AdvancedTaskPlan,
    task_planner
)

logger = get_logger(__name__)

# Enhanced models for data flow and execution context
class StepExecutionContext(BaseModel):
    """Context for step execution with data flow capabilities."""
    step_id: str = Field(..., description="ID of the step being executed")
    plan_id: str = Field(..., description="ID of the plan being executed")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables available to the step")
    results: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Results of previously executed steps")
    transaction_id: Optional[str] = Field(None, description="Transaction ID for rollback")
    dry_run: bool = Field(False, description="Whether this is a dry run")
    parent_context: Optional[Dict[str, Any]] = Field(None, description="Parent context (e.g., for loops)")
    execution_path: List[str] = Field(default_factory=list, description="Execution path taken so far")

class DataFlowVariable(BaseModel):
    """Model for a variable in the data flow system."""
    name: str = Field(..., description="Name of the variable")
    value: Any = Field(..., description="Value of the variable")
    source_step: Optional[str] = Field(None, description="ID of the step that set this variable")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the variable was set/updated")

class ExecutionResult(BaseModel):
    """Enhanced model for execution results with data flow information."""
    step_id: str = Field(..., description="ID of the executed step")
    type: PlanStepType = Field(..., description="Type of the executed step")
    success: bool = Field(..., description="Whether execution was successful")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Output values from execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Time taken for execution in seconds")
    retried: bool = Field(False, description="Whether the step was retried")
    recovery_applied: bool = Field(False, description="Whether error recovery was applied")
    recovery_strategy: Optional[Dict[str, Any]] = Field(None, description="Recovery strategy that was applied")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw execution data")

# Data flow operators for variable references
class DataFlowOperator(Enum):
    """Operators for data flow expressions."""
    GET = "get"        # Get a value
    SET = "set"        # Set a value
    CONCAT = "concat"  # Concatenate values
    FORMAT = "format"  # Format a string with values
    JSON = "json"      # Parse or stringify JSON
    REGEX = "regex"    # Apply a regex pattern
    MATH = "math"      # Perform a math operation

class EnhancedTaskPlanner:
    """
    Enhanced task planner with robust execution capabilities for complex steps.
    
    This class extends the original TaskPlanner with:
    1. Full support for CODE, API, LOOP execution
    2. Formal data flow mechanism between steps
    3. Enhanced error handling with ErrorRecoveryManager integration
    4. Comprehensive logging and debugging
    5. Security measures for code execution
    """
    
    def __init__(self):
        """Initialize the enhanced task planner."""
        self._logger = logger
        self._error_recovery_manager = registry.get("error_recovery_manager")
        if not self._error_recovery_manager:
            self._error_recovery_manager = ErrorRecoveryManager()
        
        # Initialize variable store for data flow
        self._variables: Dict[str, DataFlowVariable] = {}
        
        # Track execution statistics
        self._execution_stats = {
            "executed_plans": 0,
            "executed_steps": 0,
            "errors": 0,
            "recoveries": 0,
            "code_executions": 0,
            "api_calls": 0,
            "loops_executed": 0,
        }
        
        # Set up the sandbox environment for code execution
        self._setup_code_sandbox()
    
    def _setup_code_sandbox(self):
        """Set up the sandbox environment for code execution."""
        # Create a temp directory for code execution if it doesn't exist
        self._sandbox_dir = Path(tempfile.gettempdir()) / "angela_sandbox"
        self._sandbox_dir.mkdir(exist_ok=True)
        
        # Set up allowed imports for code execution
        self._allowed_imports = {
            # Standard library
            "os", "sys", "re", "json", "csv", "datetime", "math", "random",
            "collections", "itertools", "functools", "pathlib", "uuid",
            "time", "tempfile", "shutil", "hashlib", "base64", "hmac",
            "urllib", "http", "typing",
            
            # Common third-party libs (would need to be installed in the sandbox)
            "requests", "aiohttp", "bs4", "pandas", "numpy", "matplotlib",
        }
        
        # Set up banned function patterns
        self._banned_functions = [
            r"__import__\(",
            r"eval\(",
            r"exec\(",
            r"compile\(",
            r"globals\(\)",
            r"locals\(\)",
            r"getattr\(",
            r"setattr\(",
            r"delattr\(",
            r"subprocess\.",
            r"os\.system",
            r"os\.popen",
            r"open\(.+,\s*['\"]w['\"]",  # Writing to files
        ]
        
        self._logger.debug(f"Code sandbox set up at {self._sandbox_dir}")
    
    async def execute_advanced_plan(
        self, 
        plan: AdvancedTaskPlan, 
        dry_run: bool = False,
        transaction_id: Optional[str] = None,
        initial_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an advanced task plan with full support for all step types.
        
        Args:
            plan: The advanced task plan to execute
            dry_run: Whether to simulate execution without making changes
            transaction_id: ID of the transaction this execution belongs to
            initial_variables: Initial variables for data flow
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing advanced plan: {plan.goal} (ID: {plan.id})")
        start_time = datetime.now()
        
        # Reset variable store for this execution
        self._variables = {}
        
        # Set initial variables if provided
        if initial_variables:
            for name, value in initial_variables.items():
                self._set_variable(name, value, "initial")
        
        # Initialize execution context
        context = StepExecutionContext(
            step_id="",
            plan_id=plan.id,
            transaction_id=transaction_id,
            dry_run=dry_run,
            results={},
            variables=self._variables.copy() if self._variables else {}
        )
        
        # Initialize execution state
        results = {}
        completed_steps = set()
        pending_steps = {}
        execution_path = []
        
        # Initialize with entry points
        for entry_point in plan.entry_points:
            if entry_point in plan.steps:
                pending_steps[entry_point] = plan.steps[entry_point]
        
        # Execute steps until all are completed or no more can be executed
        while pending_steps:
            # Find steps that can be executed (all dependencies satisfied)
            executable_steps = {}
            for step_id, step in pending_steps.items():
                if all(dep in completed_steps for dep in step.dependencies):
                    executable_steps[step_id] = step
            
            # If no steps can be executed, we're stuck (circular dependencies or missing steps)
            if not executable_steps:
                self._logger.warning("No executable steps found, possible circular dependencies")
                break
            
            # Execute all executable steps
            newly_completed_steps = []
            
            for step_id, step in executable_steps.items():
                self._logger.info(f"Executing step {step_id}: {step.type} - {step.description}")
                
                # Update execution context for this step
                context.step_id = step_id
                context.execution_path = execution_path.copy()
                
                # Execute the step with enhanced error handling
                try:
                    start_step_time = datetime.now()
                    
                    result = await self._execute_advanced_step(
                        step=step,
                        context=context
                    )
                    
                    # Calculate execution time
                    execution_time = (datetime.now() - start_step_time).total_seconds()
                    
                    # Add execution time to result
                    if isinstance(result, dict) and "execution_time" not in result:
                        result["execution_time"] = execution_time
                    
                    # Store the result
                    results[step_id] = result
                    context.results[step_id] = result
                    
                    # Update execution path
                    execution_path.append(step_id)
                    
                    # Check for next steps based on step type
                    if step.type == PlanStepType.DECISION:
                        # Decision step might have conditional branches
                        condition_result = result.get("condition_result", False)
                        branch_key = "true_branch" if condition_result else "false_branch"
                        next_steps = getattr(step, branch_key, [])
                        
                        self._logger.debug(f"Decision step {step_id} evaluated to {condition_result}, following {branch_key}")
                        
                        if next_steps:
                            for next_step_id in next_steps:
                                if next_step_id in plan.steps and next_step_id not in completed_steps:
                                    pending_steps[next_step_id] = plan.steps[next_step_id]
                    
                    elif step.type == PlanStepType.LOOP:
                        # Loop execution will use recursion
                        loop_result = result.get("loop_results", [])
                        self._logger.debug(f"Loop step {step_id} executed {len(loop_result)} iterations")
                    
                    # Mark step as completed
                    completed_steps.add(step_id)
                    newly_completed_steps.append(step_id)
                    
                    # Update execution stats
                    self._execution_stats["executed_steps"] += 1
                    if step.type == PlanStepType.CODE:
                        self._execution_stats["code_executions"] += 1
                    elif step.type == PlanStepType.API:
                        self._execution_stats["api_calls"] += 1
                    elif step.type == PlanStepType.LOOP:
                        self._execution_stats["loops_executed"] += 1
                    
                    # Check if we need to stop due to an error
                    if not result.get("success", False):
                        self._logger.warning(f"Step {step_id} failed with error: {result.get('error', 'Unknown error')}")
                        
                        # Attempt error recovery
                        if not dry_run and self._error_recovery_manager:
                            recovery_result = await self._attempt_recovery(step, result, context)
                            
                            if recovery_result.get("recovery_success", False):
                                self._logger.info(f"Recovery succeeded for step {step_id}")
                                results[step_id] = recovery_result
                                context.results[step_id] = recovery_result
                                self._execution_stats["recoveries"] += 1
                            else:
                                self._logger.error(f"Recovery failed for step {step_id}")
                                return {
                                    "success": False,
                                    "steps_completed": len(completed_steps),
                                    "steps_total": len(plan.steps),
                                    "failed_step": step_id,
                                    "results": results,
                                    "error": result.get("error", "Unknown error"),
                                    "execution_path": execution_path,
                                    "execution_time": (datetime.now() - start_time).total_seconds()
                                }
                        else:
                            # No recovery attempted, return failure
                            return {
                                "success": False,
                                "steps_completed": len(completed_steps),
                                "steps_total": len(plan.steps),
                                "failed_step": step_id,
                                "results": results,
                                "error": result.get("error", "Unknown error"),
                                "execution_path": execution_path,
                                "execution_time": (datetime.now() - start_time).total_seconds()
                            }
                            
                except Exception as e:
                    self._logger.exception(f"Error executing step {step_id}: {str(e)}")
                    self._execution_stats["errors"] += 1
                    
                    # Record error result
                    error_result = {
                        "step_id": step_id,
                        "type": step.type,
                        "description": step.description,
                        "error": str(e),
                        "success": False,
                        "execution_time": (datetime.now() - start_step_time).total_seconds()
                    }
                    
                    results[step_id] = error_result
                    context.results[step_id] = error_result
                    
                    # Attempt recovery
                    if not dry_run and self._error_recovery_manager:
                        recovery_result = await self._attempt_recovery(step, error_result, context)
                        
                        if recovery_result.get("recovery_success", False):
                            self._logger.info(f"Recovery succeeded for step {step_id}")
                            results[step_id] = recovery_result
                            context.results[step_id] = recovery_result
                            self._execution_stats["recoveries"] += 1
                        else:
                            self._logger.error(f"Recovery failed for step {step_id}")
                            return {
                                "success": False,
                                "steps_completed": len(completed_steps),
                                "steps_total": len(plan.steps),
                                "failed_step": step_id,
                                "results": results,
                                "error": str(e),
                                "execution_path": execution_path,
                                "execution_time": (datetime.now() - start_time).total_seconds()
                            }
                    else:
                        # No recovery attempted, return failure
                        return {
                            "success": False,
                            "steps_completed": len(completed_steps),
                            "steps_total": len(plan.steps),
                            "failed_step": step_id,
                            "results": results,
                            "error": str(e),
                            "execution_path": execution_path,
                            "execution_time": (datetime.now() - start_time).total_seconds()
                        }
            
            # Remove completed steps from pending steps
            for step_id in newly_completed_steps:
                if step_id in pending_steps:
                    del pending_steps[step_id]
            
            # If we're using sequential execution (i.e., no newly completed steps during the last iteration)
            # update pending_steps with steps that depend on the newly completed steps
            if not newly_completed_steps:
                # Find steps that depend on the newly completed steps
                for step_id, step in plan.steps.items():
                    if step_id not in completed_steps and not step_id in pending_steps:
                        # Check if all dependencies are now satisfied
                        if all(dep in completed_steps for dep in step.dependencies):
                            pending_steps[step_id] = step
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Update execution stats
        self._execution_stats["executed_plans"] += 1
        
        # Check if all steps were completed
        all_completed = len(completed_steps) == len(plan.steps)
        
        return {
            "success": all_completed,
            "steps_completed": len(completed_steps),
            "steps_total": len(plan.steps),
            "results": results,
            "execution_path": execution_path,
            "execution_time": execution_time,
            "variables": {k: v.dict() for k, v in self._variables.items()}
        }
    
    async def _execute_advanced_step(
        self, 
        step: AdvancedPlanStep,
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a single step of an advanced plan with full support for all step types.
        
        Args:
            step: The step to execute
            context: Execution context with variables and results
            
        Returns:
            Dictionary with execution results
        """
        start_time = datetime.now()
        
        # Prepare common result fields
        result = {
            "step_id": step.id,
            "type": step.type,
            "description": step.description,
            "success": False
        }
        
        try:
            # Process any variable references in parameters
            processed_step = await self._resolve_step_variables(step, context)
            
            # Select appropriate execution method based on step type
            if processed_step.type == PlanStepType.COMMAND:
                step_result = await self._execute_command_step(processed_step, context)
            
            elif processed_step.type == PlanStepType.CODE:
                step_result = await self._execute_code_step(processed_step, context)
            
            elif processed_step.type == PlanStepType.FILE:
                step_result = await self._execute_file_step(processed_step, context)
            
            elif processed_step.type == PlanStepType.DECISION:
                step_result = await self._execute_decision_step(processed_step, context)
            
            elif processed_step.type == PlanStepType.API:
                step_result = await self._execute_api_step(processed_step, context)
            
            elif processed_step.type == PlanStepType.LOOP:
                step_result = await self._execute_loop_step(processed_step, context)
            
            else:
                # Unknown step type
                raise ValueError(f"Unknown step type: {processed_step.type}")
            
            # Merge step-specific results with common fields
            result.update(step_result)
            
            # Extract and store output variables if specified
            if "outputs" in step_result:
                for var_name, var_value in step_result["outputs"].items():
                    self._set_variable(var_name, var_value, step.id)
            
            # Set standard execution time
            result["execution_time"] = (datetime.now() - start_time).total_seconds()
            
            return result
        
        except Exception as e:
            self._logger.exception(f"Error in _execute_advanced_step for {step.id}: {str(e)}")
            
            # Add error information to result
            result["error"] = str(e)
            result["success"] = False
            result["execution_time"] = (datetime.now() - start_time).total_seconds()
            
            # Handle retry if configured
            if step.retry and step.retry > 0:
                result["retry_count"] = 1
                result["retried"] = True
                
                # Attempt retries
                for retry_num in range(1, step.retry + 1):
                    self._logger.info(f"Retrying step {step.id} (attempt {retry_num}/{step.retry})")
                    try:
                        # Wait before retrying with exponential backoff
                        await asyncio.sleep(2 ** retry_num)
                        
                        # Execute retry logic
                        retry_result = await self._execute_advanced_step(step, context)
                        
                        if retry_result.get("success", False):
                            # Retry succeeded
                            retry_result["retry_count"] = retry_num
                            retry_result["retried"] = True
                            return retry_result
                    except Exception as retry_e:
                        self._logger.error(f"Error in retry {retry_num} for step {step.id}: {str(retry_e)}")
                
                # All retries failed
                result["retry_exhausted"] = True
            
            return result
    
    async def _resolve_step_variables(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> AdvancedPlanStep:
        """
        Resolve variables in step parameters.
        
        Args:
            step: The step with potentially unresolved variables
            context: Execution context with variables
            
        Returns:
            Step with resolved variables
        """
        # Create a copy to avoid modifying the original
        step_dict = step.dict()
        
        # Define a recursive function to process variables in any value
        def process_value(value, path=""):
            if isinstance(value, str):
                # Check for variable references like ${var_name}
                var_pattern = r'\${([^}]+)}'
                matches = re.findall(var_pattern, value)
                
                if matches:
                    result = value
                    for var_name in matches:
                        var_value = self._get_variable_value(var_name, context)
                        if var_value is not None:
                            # Replace the variable reference with its value
                            result = result.replace(f"${{{var_name}}}", str(var_value))
                    return result
                return value
            
            elif isinstance(value, dict):
                return {k: process_value(v, f"{path}.{k}") for k, v in value.items()}
            
            elif isinstance(value, list):
                return [process_value(item, f"{path}[{i}]") for i, item in enumerate(value)]
            
            return value
        
        # Process all fields in the step
        processed_dict = process_value(step_dict)
        
        # Create a new step with processed values
        return AdvancedPlanStep(**processed_dict)
    
    def _get_variable_value(self, var_name: str, context: StepExecutionContext) -> Any:
        """
        Get the value of a variable, supporting both simple names and expressions.
        
        Args:
            var_name: Name of the variable or expression
            context: Execution context
            
        Returns:
            Variable value or None if not found
        """
        # Check for expressions like "result.step1.stdout"
        if "." in var_name:
            parts = var_name.split(".")
            if parts[0] == "result" or parts[0] == "results":
                if len(parts) >= 3:
                    step_id = parts[1]
                    result_field = parts[2]
                    
                    # Get the result for the specified step
                    step_result = context.results.get(step_id)
                    if step_result:
                        # Extract the requested field
                        if result_field in step_result:
                            return step_result[result_field]
                        
                        # Try nested fields
                        if len(parts) > 3:
                            nested_value = step_result
                            for part in parts[2:]:
                                if isinstance(nested_value, dict) and part in nested_value:
                                    nested_value = nested_value[part]
                                else:
                                    return None
                            return nested_value
        
        # Simple variable lookup
        if var_name in self._variables:
            return self._variables[var_name].value
        
        # Check in context variables
        if var_name in context.variables:
            return context.variables[var_name]
        
        return None
    
    def _set_variable(self, name: str, value: Any, source_step: str) -> None:
        """
        Set a variable in the variable store.
        
        Args:
            name: Name of the variable
            value: Value to set
            source_step: ID of the step setting the variable
        """
        self._variables[name] = DataFlowVariable(
            name=name,
            value=value,
            source_step=source_step,
            timestamp=datetime.now()
        )
        self._logger.debug(f"Variable '{name}' set to value from step {source_step}")
    
    async def _execute_command_step(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a command step.
        
        Args:
            step: The step to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        if not step.command:
            return {
                "success": False,
                "error": "Missing command for command step"
            }
        
        self._logger.info(f"Executing command: {step.command}")
        
        if context.dry_run:
            # Simulate command execution
            return {
                "success": True,
                "stdout": f"[DRY RUN] Would execute: {step.command}",
                "stderr": "",
                "return_code": 0,
                "outputs": {
                    f"{step.id}_stdout": f"[DRY RUN] Would execute: {step.command}",
                    f"{step.id}_success": True
                }
            }
        
        # Validate command safety if not specified to skip
        skip_safety = getattr(step, "skip_safety_check", False)
        if not skip_safety:
            # Get validate_command_safety function
            validate_func = registry.get("validate_command_safety")
            if validate_func:
                is_safe, error_message = validate_func(step.command)
                if not is_safe:
                    return {
                        "success": False,
                        "error": f"Command safety validation failed: {error_message}",
                        "command": step.command
                    }
        
        # Execute the command
        try:
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=step.command,
                check_safety=not skip_safety
            )
            
            # Create result
            result = {
                "success": return_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "command": step.command,
                "outputs": {
                    f"{step.id}_stdout": stdout,
                    f"{step.id}_stderr": stderr,
                    f"{step.id}_return_code": return_code,
                    f"{step.id}_success": return_code == 0
                }
            }
            
            # Record command execution in the transaction if successful
            if context.transaction_id and return_code == 0:
                # Import here to avoid circular imports
                rollback_manager = registry.get("rollback_manager")
                if rollback_manager:
                    await rollback_manager.record_command_execution(
                        command=step.command,
                        return_code=return_code,
                        stdout=stdout,
                        stderr=stderr,
                        transaction_id=context.transaction_id,
                        step_id=step.id
                    )
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error executing command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "command": step.command
            }
    
    async def _execute_code_step(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a code step securely.
        
        Args:
            step: The step to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        if not step.code:
            return {
                "success": False,
                "error": "Missing code for code step"
            }
        
        self._logger.info(f"Executing code step: {step.id}")
        
        if context.dry_run:
            # Simulate code execution
            return {
                "success": True,
                "output": f"[DRY RUN] Would execute code: {len(step.code)} characters",
                "outputs": {
                    f"{step.id}_output": f"[DRY RUN] Would execute code: {len(step.code)} characters",
                    f"{step.id}_success": True
                }
            }
        
        try:
            # Validate code for security
            is_safe, validation_error = self._validate_code_security(step.code)
            if not is_safe:
                return {
                    "success": False,
                    "error": f"Code security validation failed: {validation_error}",
                    "code": step.code[:100] + "..." if len(step.code) > 100 else step.code
                }
            
            # Determine code language
            language = getattr(step, "language", "python").lower()
            
            if language == "python":
                # Execute Python code
                code_result = await self._execute_python_code(step.code, context)
            elif language == "javascript" or language == "js":
                # Execute JavaScript code
                code_result = await self._execute_javascript_code(step.code, context)
            elif language == "shell" or language == "bash":
                # Execute shell code
                code_result = await self._execute_shell_code(step.code, context)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported code language: {language}"
                }
            
            # Add step ID to outputs
            if "outputs" in code_result and isinstance(code_result["outputs"], dict):
                prefixed_outputs = {}
                for key, value in code_result["outputs"].items():
                    prefixed_outputs[f"{step.id}_{key}"] = value
                code_result["outputs"] = prefixed_outputs
            
            # Add the code content to result for debugging
            if "code" not in code_result:
                code_short = step.code[:100] + "..." if len(step.code) > 100 else step.code
                code_result["code"] = code_short
            
            return code_result
            
        except Exception as e:
            self._logger.exception(f"Error executing code step: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": step.code[:100] + "..." if len(step.code) > 100 else step.code
            }
    
    def _validate_code_security(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate code for security concerns.
        
        Args:
            code: The code to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check for banned function patterns
        for pattern in self._banned_functions:
            if re.search(pattern, code):
                return False, f"Code contains potentially unsafe pattern: {pattern}"
        
        # Check for potentially harmful import statements
        # This is a simplified check; a real implementation might be more sophisticated
        import_pattern = r'^import\s+([a-zA-Z0-9_.,\s]+)$|^from\s+([a-zA-Z0-9_.]+)\s+import'
        for match in re.finditer(import_pattern, code, re.MULTILINE):
            imports = match.group(1) or match.group(2)
            if imports:
                for imp in re.split(r'[\s,]+', imports):
                    # Get the base module (before the first dot)
                    base_module = imp.split('.')[0].strip()
                    if base_module and base_module not in self._allowed_imports:
                        return False, f"Import of module '{base_module}' is not allowed"
        
        return True, None
    
    async def _execute_python_code(
        self, 
        code: str, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute Python code securely.
        
        Args:
            code: The Python code to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        # Create a unique identifier for this execution
        execution_id = str(uuid.uuid4())
        
        # Create a temporary file to store the code
        temp_dir = self._sandbox_dir / execution_id
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / "code.py"
        
        # Create a file to store the variables
        variables_file = temp_dir / "variables.json"
        
        try:
            # Prepare context variables
            context_vars = {}
            for var_name, var in self._variables.items():
                context_vars[var_name] = var.value
            
            # Write variables to file (serializing complex objects to JSON)
            with open(variables_file, 'w') as f:
                json.dump(context_vars, f)
            
            # Add wrapper code to load variables and capture output
            wrapper_code = f'''
# Generated wrapper for secure code execution
import json
import sys
import io
import traceback

# Redirect stdout and stderr
original_stdout = sys.stdout
original_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

# Output dictionary for capturing results
outputs = {{"success": False}}

try:
    # Load variables from file
    with open("{variables_file}", "r") as var_file:
        variables = json.load(var_file)
    
    # Make variables available in execution context
    globals().update(variables)
    
    # Execute the user code
    {code}
    
    # Capture stdout and stderr
    outputs["stdout"] = sys.stdout.getvalue()
    outputs["stderr"] = sys.stderr.getvalue()
    outputs["success"] = True
    
    # If there's a 'result' or 'output' variable, capture it
    if 'result' in locals():
        outputs["result"] = result
    if 'output' in locals():
        outputs["output"] = output
    
    # Capture all locals that don't start with '_'
    outputs["variables"] = {{
        k: v for k, v in locals().items() 
        if not k.startswith('_') and k not in ['variables', 'var_file']
    }}
    
except Exception as e:
    outputs["error"] = str(e)
    outputs["traceback"] = traceback.format_exc()
    outputs["success"] = False

# Restore stdout and stderr
sys.stdout = original_stdout
sys.stderr = original_stderr

# Write outputs to file
with open("{temp_dir / 'output.json'}", "w") as output_file:
    json.dump(outputs, output_file, default=str)
'''
            
            # Write the wrapper code to the temporary file
            with open(temp_file, 'w') as f:
                f.write(wrapper_code)
            
            # Execute the code in a separate process with a timeout
            timeout = getattr(step, "timeout", 30)  # Default 30 seconds
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for process with timeout
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                return_code = process.returncode
                
                # Read output file
                output_file = temp_dir / 'output.json'
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        outputs = json.load(f)
                else:
                    outputs = {
                        "success": False,
                        "error": "Output file was not created"
                    }
                
                # Create the result
                result = {
                    "success": outputs.get("success", False),
                    "outputs": outputs.get("variables", {}),
                    "stdout": outputs.get("stdout", ""),
                    "stderr": outputs.get("stderr", "")
                }
                
                if "error" in outputs:
                    result["error"] = outputs["error"]
                    result["traceback"] = outputs.get("traceback", "")
                
                if "result" in outputs:
                    result["result"] = outputs["result"]
                
                if "output" in outputs:
                    result["output"] = outputs["output"]
                
                return result
                
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                return {
                    "success": False,
                    "error": f"Code execution timed out after {timeout} seconds"
                }
                
        except Exception as e:
            self._logger.exception(f"Error in Python code execution: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                self._logger.error(f"Error cleaning up temporary files: {str(e)}")
    
    async def _execute_javascript_code(
        self, 
        code: str, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute JavaScript code securely.
        
        Args:
            code: The JavaScript code to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        # Create a unique identifier for this execution
        execution_id = str(uuid.uuid4())
        
        # Create a temporary file to store the code
        temp_dir = self._sandbox_dir / execution_id
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / "code.js"
        
        # Create a file to store the variables
        variables_file = temp_dir / "variables.json"
        
        try:
            # Prepare context variables
            context_vars = {}
            for var_name, var in self._variables.items():
                context_vars[var_name] = var.value
            
            # Write variables to file (serializing complex objects to JSON)
            with open(variables_file, 'w') as f:
                json.dump(context_vars, f)
            
            # Add wrapper code to load variables and capture output
            wrapper_code = f'''
// Generated wrapper for secure code execution
const fs = require('fs');

// Load variables from file
const variables = JSON.parse(fs.readFileSync("{variables_file}", "utf8"));

// Make variables available in execution context
Object.assign(global, variables);

// Output object for capturing results
const outputs = {{
    success: false,
    stdout: "",
    stderr: "",
    variables: {{}}
}};

// Capture console.log output
const originalLog = console.log;
const originalError = console.error;
const logs = [];
const errors = [];

console.log = (...args) => {{
    const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' ');
    logs.push(message);
    outputs.stdout += message + "\\n";
    originalLog.apply(console, args);
}};

console.error = (...args) => {{
    const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' ');
    errors.push(message);
    outputs.stderr += message + "\\n";
    originalError.apply(console, args);
}};

try {{
    // Execute the user code
    {code}
    
    outputs.success = true;
    
    // If there's a 'result' or 'output' variable, capture it
    if (typeof result !== 'undefined') {{
        outputs.result = result;
    }}
    if (typeof output !== 'undefined') {{
        outputs.output = output;
    }}
    
    // Capture all globals that don't start with '_'
    for (const key in global) {{
        if (!key.startsWith('_') && 
            key !== 'variables' && 
            key !== 'outputs' &&
            key !== 'require' &&
            key !== 'module' &&
            key !== 'exports' &&
            key !== 'Buffer' &&
            key !== 'process' &&
            typeof global[key] !== 'function') {{
            outputs.variables[key] = global[key];
        }}
    }}
    
}} catch (error) {{
    outputs.success = false;
    outputs.error = error.message;
    outputs.stack = error.stack;
}}

// Restore console functions
console.log = originalLog;
console.error = originalError;

// Write outputs to file
fs.writeFileSync("{temp_dir / 'output.json'}", JSON.stringify(outputs, (key, value) => {{
    // Handle circular references
    if (typeof value === 'object' && value !== null) {{
        if (seen.has(value)) {{
            return '[Circular]';
        }}
        seen.add(value);
    }}
    return value;
}}, 2));

function replacer(key, value) {{
    if (typeof value === 'object' && value !== null) {{
        return Object.fromEntries(
            Object.entries(value)
                .filter(([k, v]) => typeof v !== 'function')
        );
    }}
    return value;
}}

fs.writeFileSync("{temp_dir / 'output.json'}", JSON.stringify(outputs, replacer, 2));
'''
            
            # Write the wrapper code to the temporary file
            with open(temp_file, 'w') as f:
                f.write(wrapper_code)
            
            # Check if Node.js is available
            try:
                # Try to run a simple Node.js command
                process = await asyncio.create_subprocess_exec(
                    "node", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode != 0:
                    return {
                        "success": False,
                        "error": "Node.js is not available for JavaScript execution"
                    }
            except Exception:
                return {
                    "success": False,
                    "error": "Node.js is not available for JavaScript execution"
                }
            
            # Execute the code in a separate process with a timeout
            timeout = getattr(step, "timeout", 30)  # Default 30 seconds
            
            process = await asyncio.create_subprocess_exec(
                "node", str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for process with timeout
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                return_code = process.returncode
                
                # Read output file
                output_file = temp_dir / 'output.json'
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        outputs = json.load(f)
                else:
                    outputs = {
                        "success": False,
                        "error": "Output file was not created"
                    }
                
                # Create the result
                result = {
                    "success": outputs.get("success", False),
                    "outputs": outputs.get("variables", {}),
                    "stdout": outputs.get("stdout", ""),
                    "stderr": outputs.get("stderr", "")
                }
                
                if "error" in outputs:
                    result["error"] = outputs["error"]
                    result["stack"] = outputs.get("stack", "")
                
                if "result" in outputs:
                    result["result"] = outputs["result"]
                
                if "output" in outputs:
                    result["output"] = outputs["output"]
                
                return result
                
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                return {
                    "success": False,
                    "error": f"Code execution timed out after {timeout} seconds"
                }
                
        except Exception as e:
            self._logger.exception(f"Error in JavaScript code execution: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                self._logger.error(f"Error cleaning up temporary files: {str(e)}")
    
    async def _execute_shell_code(
        self, 
        code: str, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute shell code securely.
        
        Args:
            code: The shell code to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        # Create a unique identifier for this execution
        execution_id = str(uuid.uuid4())
        
        # Create a temporary file to store the code
        temp_dir = self._sandbox_dir / execution_id
        temp_dir.mkdir(exist_ok=True)
        
        script_file = temp_dir / "script.sh"
        
        try:
            # Write the code to the temporary file
            with open(script_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write("set -e\n")  # Exit on error
                
                # Export variables from context
                for var_name, var in self._variables.items():
                    # Only export string variables (shell can't handle complex types)
                    if isinstance(var.value, str) or isinstance(var.value, (int, float, bool)):
                        f.write(f"export {var_name}=\"{str(var.value)}\"\n")
                
                # Add code to capture results
                f.write("OUTPUT_FILE=\"$(mktemp)\"\n")
                f.write("VARS_FILE=\"$(mktemp)\"\n")
                f.write("\n# User code begins\n")
                f.write(code)
                f.write("\n# User code ends\n\n")
                
                # Capture environment variables
                f.write("env > \"$VARS_FILE\"\n")
                
                # Export stdout location
                f.write("echo \"$OUTPUT_FILE\" > " + str(temp_dir / "output_file.txt") + "\n")
                f.write("echo \"$VARS_FILE\" > " + str(temp_dir / "vars_file.txt") + "\n")
            
            # Make the script executable
            script_file.chmod(0o755)
            
            # Execute the script with a timeout
            timeout = getattr(step, "timeout", 30)  # Default 30 seconds
            
            process = await asyncio.create_subprocess_exec(
                str(script_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for process with timeout
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                return_code = process.returncode
                
                # Read output file location
                output_file_location = temp_dir / "output_file.txt"
                vars_file_location = temp_dir / "vars_file.txt"
                
                outputs = {}
                
                if output_file_location.exists():
                    with open(output_file_location, 'r') as f:
                        output_file = f.read().strip()
                        if os.path.exists(output_file):
                            with open(output_file, 'r') as of:
                                try:
                                    outputs = json.load(of)
                                except json.JSONDecodeError:
                                    # Not JSON, treat as plain text
                                    outputs["output"] = of.read()
                
                # Read captured environment variables
                exported_vars = {}
                if vars_file_location.exists():
                    with open(vars_file_location, 'r') as f:
                        vars_file = f.read().strip()
                        if os.path.exists(vars_file):
                            with open(vars_file, 'r') as vf:
                                for line in vf:
                                    if '=' in line:
                                        key, value = line.split('=', 1)
                                        exported_vars[key] = value.strip()
                
                # Create result
                result = {
                    "success": return_code == 0,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "return_code": return_code,
                    "outputs": exported_vars
                }
                
                if "output" in outputs:
                    result["output"] = outputs["output"]
                
                if return_code != 0:
                    result["error"] = f"Shell script failed with return code {return_code}"
                
                return result
                
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                return {
                    "success": False,
                    "error": f"Shell script execution timed out after {timeout} seconds"
                }
                
        except Exception as e:
            self._logger.exception(f"Error in shell code execution: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                self._logger.error(f"Error cleaning up temporary files: {str(e)}")
    
    async def _execute_file_step(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a file operation step.
        
        Args:
            step: The step to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        if not step.file_path:
            return {
                "success": False,
                "error": "Missing file path for file step"
            }
        
        self._logger.info(f"Executing file operation on {step.file_path}")
        
        if context.dry_run:
            # Simulate file operation
            operation = "write" if step.file_content else "read"
            return {
                "success": True,
                "message": f"[DRY RUN] Would {operation} file: {step.file_path}",
                "outputs": {
                    f"{step.id}_message": f"[DRY RUN] Would {operation} file: {step.file_path}",
                    f"{step.id}_success": True
                }
            }
        
        try:
            # Determine the operation type
            operation = getattr(step, "operation", "read" if not step.file_content else "write")
            
            # Get filesystem functions
            from angela.execution.filesystem import (
                read_file, write_file, create_directory, delete_file, delete_directory,
                move_file, copy_file
            )
            
            if operation == "read":
                # Read file content
                content = await read_file(step.file_path)
                return {
                    "success": True,
                    "content": content,
                    "outputs": {
                        f"{step.id}_content": content,
                        f"{step.id}_success": True
                    }
                }
                
            elif operation == "write":
                # Create parent directories if needed
                file_path = Path(step.file_path)
                await create_directory(file_path.parent, parents=True)
                
                # Write content to file
                await write_file(step.file_path, step.file_content)
                return {
                    "success": True,
                    "message": f"Content written to {step.file_path}",
                    "outputs": {
                        f"{step.id}_message": f"Content written to {step.file_path}",
                        f"{step.id}_success": True
                    }
                }
                
            elif operation == "delete":
                # Delete file or directory
                if Path(step.file_path).is_dir():
                    await delete_directory(step.file_path)
                    message = f"Directory {step.file_path} deleted"
                else:
                    await delete_file(step.file_path)
                    message = f"File {step.file_path} deleted"
                    
                return {
                    "success": True,
                    "message": message,
                    "outputs": {
                        f"{step.id}_message": message,
                        f"{step.id}_success": True
                    }
                }
                
            elif operation == "copy":
                # Get destination path
                destination = getattr(step, "destination", None)
                if not destination:
                    return {
                        "success": False,
                        "error": "Missing destination for copy operation"
                    }
                
                # Copy file or directory
                await copy_file(step.file_path, destination)
                return {
                    "success": True,
                    "message": f"Copied {step.file_path} to {destination}",
                    "outputs": {
                        f"{step.id}_message": f"Copied {step.file_path} to {destination}",
                        f"{step.id}_source": step.file_path,
                        f"{step.id}_destination": destination,
                        f"{step.id}_success": True
                    }
                }
                
            elif operation == "move":
                # Get destination path
                destination = getattr(step, "destination", None)
                if not destination:
                    return {
                        "success": False,
                        "error": "Missing destination for move operation"
                    }
                
                # Move file or directory
                await move_file(step.file_path, destination)
                return {
                    "success": True,
                    "message": f"Moved {step.file_path} to {destination}",
                    "outputs": {
                        f"{step.id}_message": f"Moved {step.file_path} to {destination}",
                        f"{step.id}_source": step.file_path,
                        f"{step.id}_destination": destination,
                        f"{step.id}_success": True
                    }
                }
                
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file operation: {operation}"
                }
                
        except Exception as e:
            self._logger.exception(f"Error in file operation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": step.file_path
            }
    
    async def _execute_decision_step(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a decision step.
        
        Args:
            step: The step to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        if not step.condition:
            return {
                "success": False,
                "error": "Missing condition for decision step"
            }
        
        self._logger.info(f"Evaluating condition: {step.condition}")
        
        try:
            # Determine condition evaluation method
            condition_type = getattr(step, "condition_type", "expression")
            
            if condition_type == "expression":
                # Evaluate simple expression
                condition_result = await self._evaluate_expression(step.condition, context)
            elif condition_type == "code":
                # Evaluate code for condition
                condition_code = getattr(step, "condition_code", "")
                if not condition_code:
                    return {
                        "success": False,
                        "error": "Missing condition_code for code-based condition"
                    }
                
                # Create a temporary code step
                code_step = AdvancedPlanStep(
                    id=f"{step.id}_condition",
                    type=PlanStepType.CODE,
                    description=f"Condition evaluation for {step.id}",
                    code=condition_code,
                    dependencies=[],
                    estimated_risk=0
                )
                
                # Execute the code
                code_result = await self._execute_code_step(code_step, context)
                
                # Get condition result from code execution
                condition_result = code_result.get("success", False)
                if "result" in code_result:
                    condition_result = bool(code_result["result"])
            else:
                return {
                    "success": False,
                    "error": f"Unsupported condition_type: {condition_type}"
                }
            
            # Create result
            result = {
                "success": True,
                "condition": step.condition,
                "condition_result": condition_result,
                "next_branch": "true_branch" if condition_result else "false_branch",
                "outputs": {
                    f"{step.id}_condition_result": condition_result,
                    f"{step.id}_next_branch": "true_branch" if condition_result else "false_branch",
                    f"{step.id}_success": True
                }
            }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error evaluating condition: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "condition": step.condition
            }
    
    async def _evaluate_expression(
        self, 
        expression: str, 
        context: StepExecutionContext
    ) -> bool:
        """
        Evaluate a simple condition expression.
        
        Args:
            expression: The condition expression
            context: Execution context
            
        Returns:
            Boolean result of the condition
        """
        # Check for file existence condition
        file_exists_match = re.search(r'file(?:\s+)exists(?:[:=\s]+)(.+)', expression, re.IGNORECASE)
        if file_exists_match:
            file_path = file_exists_match.group(1).strip()
            # Resolve variables in the file path
            file_path = await self._resolve_variables_in_string(file_path, context)
            return Path(file_path).exists()
        
        # Check for command success condition
        cmd_success_match = re.search(r'command(?:\s+)success(?:[:=\s]+)(.+)', expression, re.IGNORECASE)
        if cmd_success_match:
            step_id = cmd_success_match.group(1).strip()
            return context.results.get(step_id, {}).get("success", False)
        
        # Check for output contains condition
        output_contains_match = re.search(r'output(?:\s+)contains(?:[:=\s]+)(.+?)(?:[:=\s]+)in(?:[:=\s]+)(.+)', expression, re.IGNORECASE)
        if output_contains_match:
            pattern = output_contains_match.group(1).strip()
            step_id = output_contains_match.group(2).strip()
            
            # Resolve variables in the pattern
            pattern = await self._resolve_variables_in_string(pattern, context)
            
            # Get output from the specified step
            step_output = context.results.get(step_id, {}).get("stdout", "")
            return pattern in step_output
        
        # Check for variable condition
        var_match = re.search(r'variable(?:\s+)(.+?)(?:\s*)([=!<>]=|[<>])(?:\s*)(.+)', expression, re.IGNORECASE)
        if var_match:
            var_name = var_match.group(1).strip()
            operator = var_match.group(2).strip()
            value = var_match.group(3).strip()
            
            # Get variable value
            var_value = self._get_variable_value(var_name, context)
            if var_value is None:
                return False
            
            # Evaluate comparison
            try:
                # Convert value to appropriate type
                if value.lower() == "true":
                    compare_value = True
                elif value.lower() == "false":
                    compare_value = False
                elif value.isdigit():
                    compare_value = int(value)
                elif re.match(r'^-?\d+(\.\d+)?$', value):
                    compare_value = float(value)
                else:
                    # Try to resolve variables in the value
                    resolved_value = await self._resolve_variables_in_string(value, context)
                    if resolved_value != value:
                        # Value contained variables, use the resolved value
                        compare_value = resolved_value
                    else:
                        # Treat as a string but strip quotes
                        compare_value = value.strip('\'"')
                
                # Compare based on operator
                if operator == "==":
                    return var_value == compare_value
                elif operator == "!=":
                    return var_value != compare_value
                elif operator == "<":
                    return var_value < compare_value
                elif operator == ">":
                    return var_value > compare_value
                elif operator == "<=":
                    return var_value <= compare_value
                elif operator == ">=":
                    return var_value >= compare_value
                else:
                    return False
            except Exception as e:
                self._logger.error(f"Error comparing variable {var_name} with value {value}: {str(e)}")
                return False
        
        # Simple boolean evaluation for unknown conditions
        return bool(expression and expression.lower() not in ['false', '0', 'no', 'n', ''])
    
    async def _resolve_variables_in_string(
        self, 
        text: str, 
        context: StepExecutionContext
    ) -> str:
        """
        Resolve variables in a string.
        
        Args:
            text: The string with potential variable references
            context: Execution context
            
        Returns:
            String with variables resolved
        """
        if not text or "${" not in text:
            return text
        
        result = text
        var_pattern = r'\${([^}]+)}'
        matches = re.findall(var_pattern, text)
        
        for var_name in matches:
            var_value = self._get_variable_value(var_name, context)
            if var_value is not None:
                # Replace the variable reference with its value
                result = result.replace(f"${{{var_name}}}", str(var_value))
        
        return result
    
    async def _execute_api_step(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute an API call step.
        
        Args:
            step: The step to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        if not step.api_url:
            return {
                "success": False,
                "error": "Missing API URL for API step"
            }
        
        method = getattr(step, "api_method", "GET").upper()
        self._logger.info(f"Executing API call: {method} {step.api_url}")
        
        if context.dry_run:
            # Simulate API call
            return {
                "success": True,
                "message": f"[DRY RUN] Would call API: {method} {step.api_url}",
                "outputs": {
                    f"{step.id}_message": f"[DRY RUN] Would call API: {method} {step.api_url}",
                    f"{step.id}_url": step.api_url,
                    f"{step.id}_method": method,
                    f"{step.id}_success": True
                }
            }
        
        try:
            # Get timeout if specified
            timeout = getattr(step, "timeout", 30)
            
            # Get headers if specified
            headers = getattr(step, "api_headers", {})
            
            # Get query parameters if specified
            params = getattr(step, "api_params", {})
            
            # Get payload if specified
            payload = step.api_payload if hasattr(step, "api_payload") else None
            
            # Create a client session
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                # Prepare the request
                request_kwargs = {
                    "headers": headers,
                    "params": params,
                    "ssl": not getattr(step, "insecure_ssl", False)  # Allow insecure SSL as an explicit option
                }
                
                # Add payload for methods that support it
                if method in ["POST", "PUT", "PATCH"] and payload is not None:
                    # Determine content type
                    content_type = headers.get("Content-Type") if headers else None
                    
                    if content_type and "application/json" in content_type:
                        # Send as JSON
                        request_kwargs["json"] = payload
                    elif content_type and "application/x-www-form-urlencoded" in content_type:
                        # Send as form data
                        request_kwargs["data"] = payload
                    elif isinstance(payload, dict):
                        # Default to JSON if payload is a dict
                        request_kwargs["json"] = payload
                    else:
                        # Default to raw data
                        request_kwargs["data"] = payload
                
                # Execute the request
                async with session.request(method, step.api_url, **request_kwargs) as response:
                    # Read response
                    response_text = await response.text()
                    
                    # Try to parse as JSON
                    response_json = None
                    try:
                        response_json = await response.json()
                    except Exception:
                        # Not JSON, leave as None
                        pass
                    
                    # Prepare result
                    result = {
                        "success": 200 <= response.status < 300,
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "text": response_text,
                        "outputs": {
                            f"{step.id}_status_code": response.status,
                            f"{step.id}_response_text": response_text,
                            f"{step.id}_success": 200 <= response.status < 300
                        }
                    }
                    
                    # Add JSON response if available
                    if response_json is not None:
                        result["json"] = response_json
                        result["outputs"][f"{step.id}_response_json"] = response_json
                    
                    # Add error information for non-success responses
                    if not result["success"]:
                        result["error"] = f"API call failed with status code {response.status}"
                    
                    return result
                    
        except aiohttp.ClientError as e:
            self._logger.exception(f"Error in API call: {str(e)}")
            return {
                "success": False,
                "error": f"API request error: {str(e)}",
                "url": step.api_url,
                "method": method
            }
        except Exception as e:
            self._logger.exception(f"Unexpected error in API call: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": step.api_url,
                "method": method
            }
    
    async def _execute_loop_step(
        self, 
        step: AdvancedPlanStep, 
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a loop step.
        
        Args:
            step: The step to execute
            context: Execution context
            
        Returns:
            Dictionary with execution results
        """
        if not step.loop_items or not step.loop_body:
            return {
                "success": False,
                "error": "Missing loop_items or loop_body for loop step"
            }
        
        self._logger.info(f"Executing loop step: {step.id}")
        
        if context.dry_run:
            # Simulate loop execution
            return {
                "success": True,
                "message": f"[DRY RUN] Would loop over {step.loop_items}",
                "outputs": {
                    f"{step.id}_message": f"[DRY RUN] Would loop over {step.loop_items}",
                    f"{step.id}_success": True
                }
            }
        
        try:
            # Resolve loop items
            loop_items = await self._resolve_loop_items(step.loop_items, context)
            
            if not loop_items:
                return {
                    "success": True,
                    "message": "Loop executed with empty items list",
                    "loop_results": [],
                    "outputs": {
                        f"{step.id}_message": "Loop executed with empty items list",
                        f"{step.id}_success": True,
                        f"{step.id}_iterations": 0
                    }
                }
            
            self._logger.debug(f"Loop will execute over {len(loop_items)} items")
            
            # Execute the loop body for each item
            loop_results = []
            iteration_outputs = {}
            
            for i, item in enumerate(loop_items):
                iteration_key = f"iteration_{i}"
                iteration_id = f"{step.id}_{iteration_key}"
                
                self._logger.debug(f"Executing loop iteration {i} with item: {item}")
                
                # Create a new context for this iteration
                iteration_context = StepExecutionContext(
                    step_id=iteration_id,
                    plan_id=context.plan_id,
                    transaction_id=context.transaction_id,
                    dry_run=context.dry_run,
                    results=context.results.copy(),
                    variables={
                        **context.variables,
                        "loop_item": item,
                        "loop_index": i,
                        "loop_item_index": i,  # Alternative name
                        "loop_first": i == 0,
                        "loop_last": i == len(loop_items) - 1
                    },
                    parent_context=context,
                    execution_path=context.execution_path + [f"{step.id}[{i}]"]
                )
                
                # Execute each step in the loop body
                iteration_results = {}
                
                for j, body_step_id in enumerate(step.loop_body):
                    if body_step_id not in context.plan_id:
                        self._logger.error(f"Loop body step {body_step_id} not found in plan")
                        continue
                    
                    # Get the step from the plan
                    body_step = find
                    
                    # Extract outputs from the iteration
                    if "outputs" in iteration_result:
                        for output_key, output_value in iteration_result.get("outputs", {}).items():
                            iteration_outputs[f"{iteration_key}_{output_key}"] = output_value
                
                loop_results.append({
                    "index": i,
                    "item": item,
                    "success": all(result.get("success", False) for result in iteration_results.values()),
                    "results": iteration_results
                })
            
            # Prepare the result
            result = {
                "success": all(lr["success"] for lr in loop_results),
                "loop_results": loop_results,
                "iterations": len(loop_results),
                "outputs": {
                    **iteration_outputs,
                    f"{step.id}_success": all(lr["success"] for lr in loop_results),
                    f"{step.id}_iterations": len(loop_results)
                }
            }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error in loop execution: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "loop_items": step.loop_items
            }
    
    async def _resolve_loop_items(
        self, 
        loop_items_expr: str, 
        context: StepExecutionContext
    ) -> List[Any]:
        """
        Resolve loop items from various sources.
        
        Args:
            loop_items_expr: Expression for loop items
            context: Execution context
            
        Returns:
            List of items to loop over
        """
        # Check if loop_items is a variable reference
        var_match = re.match(r'\${([^}]+)}$', loop_items_expr)
        if var_match:
            var_name = var_match.group(1)
            var_value = self._get_variable_value(var_name, context)
            
            if var_value is not None:
                if isinstance(var_value, list):
                    return var_value
                elif isinstance(var_value, dict):
                    # For dictionaries, loop over items
                    return list(var_value.items())
                elif isinstance(var_value, str):
                    # For strings, try to parse as JSON
                    try:
                        parsed = json.loads(var_value)
                        if isinstance(parsed, list):
                            return parsed
                    except json.JSONDecodeError:
                        # Not JSON, split by lines
                        return var_value.splitlines()
        
        # Check for range expression: range(start, end, step)
        range_match = re.match(r'range\((\d+)(?:,\s*(\d+))?(?:,\s*(\d+))?\)', loop_items_expr)
        if range_match:
            if range_match.group(2):
                # range(start, end, [step])
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                step = int(range_match.group(3)) if range_match.group(3) else 1
                return list(range(start, end, step))
            else:
                # range(end)
                end = int(range_match.group(1))
                return list(range(end))
        
        # Check for file list: files(pattern)
        files_match = re.match(r'files\(([^)]+)\)', loop_items_expr)
        if files_match:
            pattern = files_match.group(1).strip('"\'')
            
            # Resolve pattern if it contains variables
            resolved_pattern = await self._resolve_variables_in_string(pattern, context)
            
            # Import here to avoid circular imports
            from glob import glob
            
            # Get list of files matching the pattern
            file_list = glob(resolved_pattern)
            return file_list
        
        # Check for JSON array
        if loop_items_expr.startswith('[') and loop_items_expr.endswith(']'):
            try:
                items = json.loads(loop_items_expr)
                if isinstance(items, list):
                    return items
            except json.JSONDecodeError:
                pass
        
        # Check for comma-separated list
        if ',' in loop_items_expr:
            return [item.strip() for item in loop_items_expr.split(',')]
        
        # Default: return as single item
        return [loop_items_expr]
    
    async def _attempt_recovery(
        self, 
        step: AdvancedPlanStep,
        result: Dict[str, Any],
        context: StepExecutionContext
    ) -> Dict[str, Any]:
        """
        Attempt to recover from a failed step.
        
        Args:
            step: The failed step
            result: The failure result
            context: Execution context
            
        Returns:
            Updated result after recovery attempt
        """
        if not self._error_recovery_manager:
            return {
                **result,
                "recovery_attempted": True,
                "recovery_success": False,
                "recovery_error": "Error recovery manager not available"
            }
        
        self._logger.info(f"Attempting recovery for failed step {step.id}")
        
        try:
            # Create a recovery-compatible step dictionary
            step_dict = {
                "id": step.id,
                "command": getattr(step, "command", ""),
                "explanation": step.description
            }
            
            # Call the error recovery manager
            recovery_result = await self._error_recovery_manager.handle_error(
                step_dict, result, {"context": context.dict()}
            )
            
            if recovery_result.get("recovery_success", False):
                self._logger.info(f"Recovery succeeded for step {step.id}")
                
                # Merge success fields
                result["success"] = True
                result["recovery_applied"] = True
                result["recovery_strategy"] = recovery_result.get("recovery_strategy")
                
                # Copy any new outputs from recovery
                if "outputs" in recovery_result:
                    if "outputs" not in result:
                        result["outputs"] = {}
                    result["outputs"].update(recovery_result["outputs"])
                
                return result
            else:
                self._logger.warning(f"Recovery failed for step {step.id}")
                return {
                    **result,
                    "recovery_attempted": True,
                    "recovery_success": False,
                    "recovery_error": recovery_result.get("error", "Unknown recovery error")
                }
            
        except Exception as e:
            self._logger.exception(f"Error in recovery attempt: {str(e)}")
            return {
                **result,
                "recovery_attempted": True,
                "recovery_success": False,
                "recovery_error": str(e)
            }

# Extend the existing TaskPlanner with the enhanced functionality
class EnhancedTaskPlanner(TaskPlanner):
    """
    Enhanced TaskPlanner with support for advanced execution capabilities.
    
    This class extends the original TaskPlanner with the capabilities
    from the EnhancedTaskPlanner.
    """
    
    def __init__(self):
        """Initialize the enhanced task planner."""
        super().__init__()
        self._enhanced_planner = EnhancedTaskPlanner()
    
    async def execute_plan(
        self, 
        plan: Union[TaskPlan, AdvancedTaskPlan], 
        dry_run: bool = False,
        transaction_id: Optional[str] = None,
        initial_variables: Optional[Dict[str, Any]] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute a task plan with full support for all step types.
        
        Args:
            plan: The plan to execute
            dry_run: Whether to simulate execution without making changes
            transaction_id: ID of the transaction this execution belongs to
            initial_variables: Initial variables for data flow
            
        Returns:
            List of execution results for each step or execution result dict
        """
        if isinstance(plan, AdvancedTaskPlan):
            # Use the enhanced execution for advanced plans
            return await self._enhanced_planner.execute_advanced_plan(
                plan, dry_run, transaction_id, initial_variables
            )
        else:
            # Use the original execution for basic plans
            return await super()._execute_basic_plan(plan, dry_run, transaction_id)

# Create an instance of the enhanced task planner
enhanced_task_planner = EnhancedTaskPlanner()

# Replace the global task_planner with the enhanced version
task_planner = enhanced_task_planner
