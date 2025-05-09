# angela/intent/complex_workflow_planner.py
"""
Complex Workflow Orchestration for Angela CLI.

This module extends the existing enhanced task planner with specialized
capabilities for orchestrating workflows across multiple CLI tools and
services, enabling end-to-end automation of complex development and
deployment pipelines.
"""
import asyncio
import json
import re
import shlex
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable

from pydantic import BaseModel, Field, validator

from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.core.registry import registry
from angela.intent.enhanced_task_planner import (
    EnhancedTaskPlanner, StepExecutionContext, 
    AdvancedTaskPlan, AdvancedPlanStep, PlanStepType,
    ExecutionResult
)
from angela.toolchain.universal_cli import universal_cli_translator
from angela.execution.adaptive_engine import adaptive_engine

logger = get_logger(__name__)

class WorkflowStepType(str, Enum):
    """Types of steps in a complex workflow."""
    COMMAND = "command"              # Standard shell command
    TOOL = "tool"                    # External CLI tool command
    API = "api"                      # API call
    DECISION = "decision"            # Decision point
    WAIT = "wait"                    # Wait for a condition
    PARALLEL = "parallel"            # Parallel execution
    CUSTOM_CODE = "custom_code"      # Custom code execution
    NOTIFICATION = "notification"    # Send notification
    VALIDATION = "validation"        # Validate a condition

class WorkflowVariable(BaseModel):
    """Model for a variable in a workflow."""
    name: str = Field(..., description="Name of the variable")
    description: Optional[str] = Field(None, description="Description of the variable")
    default_value: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(False, description="Whether the variable is required")
    type: str = Field("string", description="Data type (string, number, boolean)")
    scope: str = Field("global", description="Variable scope (global, step, local)")
    source_step: Optional[str] = Field(None, description="Step that produces this variable")

class WorkflowStepDependency(BaseModel):
    """Model for a dependency between workflow steps."""
    step_id: str = Field(..., description="ID of the dependent step")
    type: str = Field("success", description="Type of dependency (success, completion, failure)")
    condition: Optional[str] = Field(None, description="Optional condition for the dependency")

class WorkflowStep(BaseModel):
    """Model for a step in a complex workflow."""
    id: str = Field(..., description="Unique identifier for this step")
    name: str = Field(..., description="Human-readable name for the step")
    type: WorkflowStepType = Field(..., description="Type of workflow step")
    description: str = Field(..., description="Detailed description of what this step does")
    tool: Optional[str] = Field(None, description="Tool name for TOOL type")
    command: Optional[str] = Field(None, description="Command to execute")
    api_url: Optional[str] = Field(None, description="URL for API call")
    api_method: Optional[str] = Field("GET", description="HTTP method for API call")
    api_headers: Dict[str, str] = Field(default_factory=dict, description="Headers for API call")
    api_data: Optional[Any] = Field(None, description="Data payload for API call")
    code: Optional[str] = Field(None, description="Custom code to execute")
    condition: Optional[str] = Field(None, description="Condition for DECISION or VALIDATION type")
    wait_condition: Optional[str] = Field(None, description="Condition to wait for in WAIT type")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry: Optional[int] = Field(None, description="Number of retry attempts")
    parallel_steps: List[str] = Field(default_factory=list, description="Steps to execute in parallel")
    dependencies: List[WorkflowStepDependency] = Field(default_factory=list, description="Dependencies on other steps")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input values for the step")
    outputs: List[str] = Field(default_factory=list, description="Output variables produced by this step")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables for this step")
    working_dir: Optional[str] = Field(None, description="Working directory for this step")
    on_success: Optional[str] = Field(None, description="Step to execute on success")
    on_failure: Optional[str] = Field(None, description="Step to execute on failure")
    estimated_risk: int = Field(0, description="Risk level (0-4)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

class ComplexWorkflowPlan(BaseModel):
    """Model for a complex workflow plan."""
    id: str = Field(..., description="Unique identifier for this workflow")
    name: str = Field(..., description="Name of the workflow")
    description: str = Field(..., description="Detailed description of the workflow")
    goal: str = Field(..., description="Original goal that prompted this workflow")
    steps: Dict[str, WorkflowStep] = Field(..., description="Steps of the workflow")
    variables: Dict[str, WorkflowVariable] = Field(default_factory=dict, description="Workflow variables")
    entry_points: List[str] = Field(..., description="Step IDs to start execution with")
    exit_points: List[str] = Field(default_factory=list, description="Step IDs that conclude the workflow")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    created: datetime = Field(default_factory=datetime.now, description="When the workflow was created")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ComplexWorkflowPlanner(EnhancedTaskPlanner):
    """
    Planner specialized for creating and executing complex workflows that
    orchestrate multiple tools and services in a controlled, reliable manner.
    """
    
    def __init__(self):
        """Initialize the complex workflow planner."""
        super().__init__()
        self._logger = logger
        
        # Track currently executing workflows
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Register supported workflow step handlers
        self._step_handlers = {
            WorkflowStepType.COMMAND: self._execute_command_step,
            WorkflowStepType.TOOL: self._execute_tool_step,
            WorkflowStepType.API: self._execute_api_step,
            WorkflowStepType.DECISION: self._execute_decision_step,
            WorkflowStepType.WAIT: self._execute_wait_step,
            WorkflowStepType.PARALLEL: self._execute_parallel_step,
            WorkflowStepType.CUSTOM_CODE: self._execute_custom_code_step,
            WorkflowStepType.NOTIFICATION: self._execute_notification_step,
            WorkflowStepType.VALIDATION: self._execute_validation_step,
        }
    
    async def plan_complex_workflow(
        self,
        request: str,
        context: Dict[str, Any],
        max_steps: int = 30
    ) -> ComplexWorkflowPlan:
        """
        Plan a complex workflow involving multiple tools based on a natural language request.
        
        Args:
            request: Natural language request describing the workflow
            context: Context information for enhanced planning
            max_steps: Maximum number of steps to include in the plan
            
        Returns:
            A ComplexWorkflowPlan object
        """
        self._logger.info(f"Planning complex workflow: {request}")
        
        try:
            # Generate the workflow plan data using AI
            plan_data = await self._generate_workflow_plan(request, context, max_steps)
            
            # Extract the plan components
            workflow_id = plan_data.get("id", str(uuid.uuid4()))
            workflow_name = plan_data.get("name", f"Workflow {workflow_id[:8]}")
            description = plan_data.get("description", request)
            
            # Convert step data to model objects
            steps_data = plan_data.get("steps", {})
            steps = self._convert_step_data_to_models(steps_data)
            
            # Convert variable data to model objects
            variables_data = plan_data.get("variables", {})
            variables = self._convert_variable_data_to_models(variables_data)
            
            # Get entry points
            entry_points = plan_data.get("entry_points", [])
            if not entry_points and steps:
                # If no entry points specified, use the first step
                entry_points = [next(iter(steps.keys()))]
            
            # Create the workflow plan
            workflow_plan = ComplexWorkflowPlan(
                id=workflow_id,
                name=workflow_name,
                description=description,
                steps=steps,
                variables=variables,
                entry_points=entry_points,
                request=request,
                context_snapshot=self._take_context_snapshot(context)
            )
            
            self._logger.info(f"Created complex workflow plan with {len(steps)} steps")
            return workflow_plan
            
        except Exception as e:
            self._logger.error(f"Error generating complex workflow plan: {str(e)}")
            # Create a fallback workflow
            return self._create_fallback_workflow(request, context)
    
    async def _generate_workflow_plan(
        self, 
        request: str, 
        context: Dict[str, Any],
        max_steps: int
    ) -> Dict[str, Any]:
        """
        Generate a workflow plan using AI.
        
        Args:
            request: Natural language request
            context: Context information
            max_steps: Maximum number of steps
            
        Returns:
            Dictionary with workflow plan data
        """
        self._logger.debug(f"Generating workflow plan for: {request}")
        
        # Build a prompt enriched with system context
        cwd = context.get("cwd", "/")
        project_root = context.get("project_root", cwd)
        project_type = context.get("project_type", "unknown")
        
        # Include available tools
        available_tools = await universal_cli_translator.get_tool_suggestions()
        tools_str = ", ".join(available_tools[:15])
        if len(available_tools) > 15:
            tools_str += f" and {len(available_tools) - 15} more"
        
        prompt = f"""
You are an expert DevOps engineer and workflow automation specialist. Create a detailed workflow plan for this request:

REQUEST: "{request}"

CONTEXT:
- Current directory: {cwd}
- Project root: {project_root}
- Project type: {project_type}
- Available tools: {tools_str}

Design a comprehensive workflow that addresses all aspects of the request. Follow these guidelines:
1. Break down the workflow into logical steps with clear dependencies
2. Identify exact tools and commands needed for each step
3. Define variables needed throughout the workflow
4. Include appropriate validation and error handling
5. Structure the plan with parallel execution where possible
6. Ensure proper sequencing with dependencies

Return a structured JSON object with:
- name: A descriptive name for the workflow
- description: Detailed explanation of what this workflow accomplishes
- steps: Object mapping step IDs to step details (see step structure below)
- variables: Object mapping variable names to details (see variable structure below)
- entry_points: Array of step IDs that start the workflow
- exit_points: Array of step IDs that conclude the workflow

Step structure:
{{
  "id": "unique_step_id",
  "name": "Human-readable step name",
  "type": "command|tool|api|decision|wait|parallel|custom_code|notification|validation",
  "description": "Detailed description of this step",
  "tool": "Tool name for TOOL type",
  "command": "Command to execute",
  "condition": "Condition for DECISION or VALIDATION type",
  "dependencies": [
    {{ "step_id": "another_step_id", "type": "success|completion|failure" }}
  ],
  "inputs": {{ "key": "value" }},
  "outputs": ["variable_name1", "variable_name2"],
  "estimated_risk": 0-4
}}

Variable structure:
{{
  "name": "variable_name",
  "description": "Purpose of this variable",
  "default_value": "default if any",
  "required": true|false,
  "type": "string|number|boolean",
  "source_step": "step_id that produces this variable"
}}

Ensure the workflow is complete, practical, and executable. Include approximately {max_steps} steps or fewer, favoring quality over quantity.
"""
        
        # Call AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=4000)
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract JSON from the response
            import json
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            plan_data = json.loads(json_str)
            return plan_data
            
        except Exception as e:
            self._logger.error(f"Error parsing workflow plan JSON: {str(e)}")
            return {
                "error": str(e),
                "name": f"Workflow for: {request[:30]}...",
                "description": "Error parsing workflow plan",
                "steps": {},
                "variables": {},
                "entry_points": [],
                "exit_points": []
            }
    
    def _convert_step_data_to_models(
        self, 
        steps_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, WorkflowStep]:
        """
        Convert step data from AI to WorkflowStep models.
        
        Args:
            steps_data: Dictionary of step data
            
        Returns:
            Dictionary of WorkflowStep models
        """
        result = {}
        
        for step_id, step_data in steps_data.items():
            # Ensure step_data has required fields
            if not step_data.get("type"):
                self._logger.warning(f"Step {step_id} missing 'type' field, defaulting to 'command'")
                step_data["type"] = "command"
            
            if not step_data.get("name"):
                step_data["name"] = f"Step {step_id}"
            
            if not step_data.get("description"):
                step_data["description"] = f"Step {step_id} ({step_data['type']})"
            
            # Convert dependencies to models if present
            dependencies = []
            for dep in step_data.get("dependencies", []):
                if isinstance(dep, dict) and "step_id" in dep:
                    # Already in correct format
                    dependencies.append(WorkflowStepDependency(**dep))
                elif isinstance(dep, str):
                    # Just a step ID, assume success dependency
                    dependencies.append(WorkflowStepDependency(step_id=dep, type="success"))
            
            # Set proper dependencies format
            step_data["dependencies"] = dependencies
            
            # Ensure ID is set
            step_data["id"] = step_id
            
            # Create the model
            try:
                result[step_id] = WorkflowStep(**step_data)
            except Exception as e:
                self._logger.error(f"Error creating WorkflowStep model for {step_id}: {str(e)}")
                # Create a simplified step as fallback
                result[step_id] = WorkflowStep(
                    id=step_id,
                    name=step_data.get("name", f"Step {step_id}"),
                    type=WorkflowStepType.COMMAND,
                    description=step_data.get("description", f"Step {step_id} (fallback)"),
                    command=step_data.get("command", "echo 'Step execution error'")
                )
        
        return result
    
    def _convert_variable_data_to_models(
        self, 
        variables_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, WorkflowVariable]:
        """
        Convert variable data from AI to WorkflowVariable models.
        
        Args:
            variables_data: Dictionary of variable data
            
        Returns:
            Dictionary of WorkflowVariable models
        """
        result = {}
        
        for var_name, var_data in variables_data.items():
            # Ensure var_data has name field
            var_data["name"] = var_name
            
            # Create the model
            try:
                result[var_name] = WorkflowVariable(**var_data)
            except Exception as e:
                self._logger.error(f"Error creating WorkflowVariable model for {var_name}: {str(e)}")
                # Create a simplified variable as fallback
                result[var_name] = WorkflowVariable(
                    name=var_name,
                    description=var_data.get("description", f"Variable {var_name}"),
                    type=var_data.get("type", "string")
                )
        
        return result
    
    def _create_fallback_workflow(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> ComplexWorkflowPlan:
        """
        Create a fallback workflow plan when generation fails.
        
        Args:
            request: Natural language request
            context: Context information
            
        Returns:
            A simple ComplexWorkflowPlan
        """
        self._logger.info(f"Creating fallback workflow for: {request}")
        
        # Create a unique ID
        workflow_id = str(uuid.uuid4())
        
        # Create a simple step that echoes the error
        step_id = "fallback_step"
        step = WorkflowStep(
            id=step_id,
            name="Fallback Step",
            type=WorkflowStepType.COMMAND,
            description="Fallback step due to workflow planning error",
            command=f"echo 'Failed to create complex workflow for: {request}'",
            dependencies=[]
        )
        
        # Create the workflow plan
        return ComplexWorkflowPlan(
            id=workflow_id,
            name=f"Fallback Workflow {workflow_id[:8]}",
            description=f"Fallback workflow for: {request}",
            goal=request,
            steps={step_id: step},
            entry_points=[step_id],
            exit_points=[step_id],
            context=context,
            created=datetime.now()
        )
    
    async def execute_complex_workflow(
        self,
        workflow: ComplexWorkflowPlan,
        dry_run: bool = False,
        transaction_id: Optional[str] = None,
        initial_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a complex workflow plan.
        
        Args:
            workflow: The workflow plan to execute
            dry_run: Whether to simulate execution without making changes
            transaction_id: Optional transaction ID for rollback support
            initial_variables: Optional initial variables to set
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing complex workflow: {workflow.name}")
        
        # Initialize execution state
        execution_state = {
            "workflow_id": workflow.id,
            "started_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "current_step": None,
            "completed_steps": set(),
            "failed_steps": set(),
            "results": {},
            "variables": {},
            "transaction_id": transaction_id,
            "status": "running"
        }
        
        # Add initial variables if provided
        if initial_variables:
            execution_state["variables"].update(initial_variables)
        
        # Initialize variables from workflow definition
        for var_name, var_obj in workflow.variables.items():
            if var_obj.default_value is not None:
                execution_state["variables"][var_name] = var_obj.default_value
        
        # Start with entry points
        steps_to_execute = set(workflow.entry_points)
        all_steps = set(workflow.steps.keys())
        
        # Execute steps until there are no more steps to execute
        while steps_to_execute:
            # Get the next step to execute
            executable_steps = set()
            
            for step_id in steps_to_execute:
                if step_id in execution_state["completed_steps"] or step_id in execution_state["failed_steps"]:
                    continue
                    
                step = workflow.steps.get(step_id)
                if not step:
                    self._logger.warning(f"Step {step_id} not found in workflow")
                    continue
                    
                # Check if all dependencies are satisfied
                dependencies_satisfied = True
                for dep in step.dependencies:
                    if not self._is_dependency_satisfied(dep, execution_state):
                        dependencies_satisfied = False
                        break
                        
                if dependencies_satisfied:
                    executable_steps.add(step_id)
            
            # If no steps can be executed, check if we're stuck or done
            if not executable_steps:
                if len(execution_state["completed_steps"]) + len(execution_state["failed_steps"]) < len(all_steps):
                    # We're stuck - there are steps that can't be executed
                    self._logger.warning("Workflow execution is stuck - some steps cannot be executed")
                    execution_state["status"] = "stuck"
                    
                    # Find the steps that couldn't be executed
                    remaining_steps = all_steps - execution_state["completed_steps"] - execution_state["failed_steps"]
                    self._logger.warning(f"Steps not executed: {remaining_steps}")
                    
                    # Check each remaining step for its blocker
                    for step_id in remaining_steps:
                        step = workflow.steps.get(step_id)
                        if step:
                            for dep in step.dependencies:
                                if not self._is_dependency_satisfied(dep, execution_state):
                                    self._logger.warning(f"Step {step_id} blocked by dependency {dep.step_id} ({dep.type})")
                    
                    break
                else:
                    # All steps have been processed
                    self._logger.info("All workflow steps processed")
                    execution_state["status"] = "completed"
                    break
            
            # Execute the steps in parallel or sequentially
            execute_in_parallel = (
                len(executable_steps) > 1 and
                self._can_execute_in_parallel(executable_steps, workflow.steps)
            )
            
            if execute_in_parallel:
                # Execute steps in parallel
                self._logger.info(f"Executing {len(executable_steps)} steps in parallel")
                
                tasks = []
                for step_id in executable_steps:
                    step = workflow.steps[step_id]
                    execution_state["current_step"] = step_id
                    tasks.append(self._execute_step(step, execution_state))
                
                # Wait for all tasks to complete
                step_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, step_id in enumerate(executable_steps):
                    result = step_results[i]
                    
                    if isinstance(result, Exception):
                        self._logger.error(f"Step {step_id} failed with exception: {str(result)}")
                        execution_state["failed_steps"].add(step_id)
                        execution_state["results"][step_id] = {
                            "success": False,
                            "error": str(result),
                            "exception": True
                        }
                    else:
                        execution_state["results"][step_id] = result
                        
                        if result.get("success", False):
                            execution_state["completed_steps"].add(step_id)
                            
                            # Extract variables from the result
                            if "variables" in result:
                                for var_name, var_value in result["variables"].items():
                                    execution_state["variables"][var_name] = var_value
                        else:
                            execution_state["failed_steps"].add(step_id)
            else:
                # Execute steps sequentially
                for step_id in executable_steps:
                    step = workflow.steps[step_id]
                    execution_state["current_step"] = step_id
                    
                    # Execute the step
                    self._logger.info(f"Executing step {step_id}: {step.name}")
                    try:
                        result = await self._execute_step(step, execution_state)
                        execution_state["results"][step_id] = result
                        
                        if result.get("success", False):
                            execution_state["completed_steps"].add(step_id)
                            
                            # Extract variables from the result
                            if "variables" in result:
                                for var_name, var_value in result["variables"].items():
                                    execution_state["variables"][var_name] = var_value
                        else:
                            execution_state["failed_steps"].add(step_id)
                            
                            # Stop execution on failure unless step is marked as non-critical
                            if not step.continue_on_failure:
                                self._logger.warning(f"Step {step_id} failed and is critical - stopping workflow")
                                execution_state["status"] = "failed"
                                break
                    except Exception as e:
                        self._logger.error(f"Error executing step {step_id}: {str(e)}")
                        execution_state["failed_steps"].add(step_id)
                        execution_state["results"][step_id] = {
                            "success": False,
                            "error": str(e),
                            "exception": True
                        }
                        
                        # Stop execution on exception unless step is marked as non-critical
                        if not step.continue_on_failure:
                            self._logger.warning(f"Step {step_id} failed with exception and is critical - stopping workflow")
                            execution_state["status"] = "failed"
                            break
            
            # Update steps to execute - remove completed and failed steps
            steps_to_execute -= execution_state["completed_steps"]
            steps_to_execute -= execution_state["failed_steps"]
            
            # Add any new steps that might have become executable
            for step_id in all_steps - execution_state["completed_steps"] - execution_state["failed_steps"]:
                if step_id not in steps_to_execute:
                    step = workflow.steps.get(step_id)
                    if step:
                        # Check if all dependencies are satisfied
                        dependencies_satisfied = True
                        for dep in step.dependencies:
                            if not self._is_dependency_satisfied(dep, execution_state):
                                dependencies_satisfied = False
                                break
                                
                        if dependencies_satisfied:
                            steps_to_execute.add(step_id)
            
            # If status is failed, stop execution
            if execution_state["status"] == "failed":
                break
        
        # Calculate success based on critical steps
        critical_steps = [step_id for step_id, step in workflow.steps.items() if not step.continue_on_failure]
        failed_critical_steps = execution_state["failed_steps"].intersection(critical_steps)
        
        execution_state["success"] = (
            execution_state["status"] != "failed" and
            execution_state["status"] != "stuck" and
            len(failed_critical_steps) == 0
        )
        
        # Add end time
        execution_state["ended_at"] = datetime.now().isoformat()
        
        # Log completion
        status_str = "succeeded" if execution_state["success"] else "failed"
        self._logger.info(f"Workflow execution {status_str}: {len(execution_state['completed_steps'])} completed, {len(execution_state['failed_steps'])} failed")
        
        # Clean up the execution state for the return value
        return {
            "workflow_id": execution_state["workflow_id"],
            "success": execution_state["success"],
            "status": execution_state["status"],
            "steps_total": len(all_steps),
            "steps_completed": len(execution_state["completed_steps"]),
            "steps_failed": len(execution_state["failed_steps"]),
            "started_at": execution_state["started_at"],
            "ended_at": execution_state["ended_at"],
            "results": execution_state["results"],
            "variables": execution_state["variables"]
        }
    
    def _is_dependency_satisfied(
        self, 
        dependency: WorkflowStepDependency, 
        execution_state: Dict[str, Any]
    ) -> bool:
        """
        Check if a dependency is satisfied in the current execution state.
        
        Args:
            dependency: The dependency to check
            execution_state: Current execution state
            
        Returns:
            True if dependency is satisfied, False otherwise
        """
        step_id = dependency.step_id
        
        # Check if the step exists in completed steps
        if step_id not in execution_state["completed_steps"]:
            return False
        
        # Get the result of the dependent step
        result = execution_state["results"].get(step_id, {})
        
        # Check dependency type
        if dependency.type == "completion":
            # Only check that the step completed (success or failure)
            return True
        elif dependency.type == "success":
            # Check that the step completed successfully
            return result.get("success", False)
        elif dependency.type == "failure":
            # Check that the step failed
            return not result.get("success", False)
        
        # Unknown dependency type
        self._logger.warning(f"Unknown dependency type: {dependency.type}")
        return False


    async def _execute_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single workflow step.
        
        Args:
            step: The workflow step to execute
            execution_state: Current execution state
            
        Returns:
            Dictionary with step execution results
        """
        self._logger.debug(f"Executing step {step.id}: {step.name} (Type: {step.type})")
        
        # Check if we need to substitute variables
        try:
            # Find and replace all variable references
            if hasattr(step, "command") and step.command:
                step.command = self._substitute_variables(step.command, execution_state["variables"])
                
            if hasattr(step, "api_url") and step.api_url:
                step.api_url = self._substitute_variables(step.api_url, execution_state["variables"])
                
            if hasattr(step, "condition") and step.condition:
                step.condition = self._substitute_variables(step.condition, execution_state["variables"])
                
            if hasattr(step, "file_path") and step.file_path:
                step.file_path = self._substitute_variables(step.file_path, execution_state["variables"])
                
            if hasattr(step, "file_content") and step.file_content:
                step.file_content = self._substitute_variables(step.file_content, execution_state["variables"])
        except Exception as e:
            self._logger.error(f"Error substituting variables: {str(e)}")
        
        # Log step execution
        step_info = f"Executing step {step.id}"
        if step.description:
            step_info += f": {step.description}"
            
        self._logger.info(step_info)
        
        # Check if this is a dry run
        if execution_state["dry_run"]:
            return {
                "success": True,
                "dry_run": True,
                "message": f"[DRY RUN] Would execute step: {step.name} ({step.type})"
            }
        
        # Get the appropriate handler for this step type
        handler = self._step_handlers.get(step.type)
        if not handler:
            return {
                "success": False,
                "error": f"Unsupported step type: {step.type}"
            }
        
        # Execute the step
        try:
            result = await handler(step, execution_state)
            
            # Check for variables to extract
            if result.get("success", False) and "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    extracted_vars = self._extract_variables_from_output(output)
                    if extracted_vars:
                        if "variables" not in result:
                            result["variables"] = {}
                        result["variables"].update(extracted_vars)
            
            return result
        except Exception as e:
            self._logger.error(f"Error executing step {step.id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }
    
    async def execute_tool_across_environments(
        self,
        request: str,
        tools: List[str],
        environments: List[str] = None,
        context: Dict[str, Any] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a natural language request across multiple tools and environments.
        
        This is a higher-level method that creates and executes a workflow spanning
        multiple tools across different environments (like dev, staging, prod).
        
        Args:
            request: Natural language request
            tools: List of tools to include in the workflow
            environments: Optional list of environments to target
            context: Optional context information
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing request across environments: {request}")
        
        # Get context if not provided
        if context is None:
            context = context_manager.get_context_dict()
        
        # Set default environments if not provided
        if not environments:
            environments = ["dev"]
        
        # Build a complex workflow request that includes all tools and environments
        enhanced_request = f"{request}\n\nTools to use: {', '.join(tools)}\n"
        enhanced_request += f"Target environments: {', '.join(environments)}\n"
        
        # Add additional context about the tools if available
        tool_context = "Tool information:\n"
        for tool in tools:
            tool_info = await self._get_tool_information(tool)
            if tool_info:
                tool_context += f"- {tool}: {tool_info}\n"
        
        enhanced_request += f"\n{tool_context}"
        
        # Plan and execute the workflow
        workflow = await self.plan_complex_workflow(
            request=enhanced_request,
            context=context
        )
        
        # Execute the workflow
        result = await self.execute_complex_workflow(
            workflow=workflow,
            dry_run=dry_run
        )
        
        return {
            "original_request": request,
            "enhanced_request": enhanced_request,
            "tools": tools,
            "environments": environments,
            "workflow": workflow.dict(exclude={"context_snapshot"}),
            "execution_result": result
        }
    
    async def _get_tool_information(self, tool: str) -> Optional[str]:
        """
        Get information about a CLI tool by running its help command.
        
        Args:
            tool: The tool name
            
        Returns:
            Tool information string or None if not available
        """
        try:
            from angela.toolchain.universal_cli import universal_cli_translator
            suggestions = await universal_cli_translator.get_tool_suggestions(tool)
            
            if tool in suggestions:
                # Tool exists, try to get its help info
                help_cmd = f"{tool} --help"
                
                from angela.execution.engine import execution_engine
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command=help_cmd,
                    check_safety=True
                )
                
                if return_code == 0:
                    # Parse the help output to extract a brief description
                    lines = stdout.split('\n')
                    # Filter out blank lines and syntax lines
                    lines = [line for line in lines if line.strip() and not line.strip().startswith("usage:")]
                    
                    if lines:
                        # Take the first non-empty line as the description
                        return lines[0].strip()
                
                return f"CLI tool available in the system"
            return None
        except Exception as e:
            self._logger.debug(f"Error getting tool information for {tool}: {str(e)}")
            return None
    
    def _take_context_snapshot(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take a snapshot of the relevant context information for workflow execution.
        
        Args:
            context: The full context dictionary
            
        Returns:
            A filtered copy of the context with only relevant information
        """
        # Extract only the keys we need for workflow execution
        relevant_keys = [
            "cwd", "project_root", "project_type", "user", "environment",
            "recent_files", "session"
        ]
        
        snapshot = {}
        for key in relevant_keys:
            if key in context:
                # Make a deep copy to avoid modifying the original
                try:
                    # Try to serialize to JSON and back to ensure it's serializable
                    snapshot[key] = json.loads(json.dumps(context[key]))
                except (TypeError, json.JSONDecodeError):
                    # If not JSON serializable, convert to string
                    snapshot[key] = str(context[key])
        
        return snapshot


    
    async def _execute_command_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a command step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        if not step.command:
            return {
                "success": False,
                "error": "Missing command for command step"
            }
        
        # Apply variable substitution to the command
        command = self._substitute_variables(step.command, execution_state["variables"])
        
        self._logger.info(f"Executing command: {command}")
        
        # If dry run, just simulate the command
        if execution_state["dry_run"]:
            return {
                "success": True,
                "command": command,
                "stdout": f"[DRY RUN] Would execute: {command}",
                "stderr": "",
                "return_code": 0,
                "outputs": {}
            }
        
        # Determine working directory
        working_dir = None
        if step.working_dir:
            working_dir = self._substitute_variables(step.working_dir, execution_state["variables"])
        
        # Set up environment variables
        env = {}
        if step.environment:
            for key, value in step.environment.items():
                env[key] = self._substitute_variables(value, execution_state["variables"])
        
        # Execute the command using the adaptive engine
        try:
            # Execute using proper engine
            result = await adaptive_engine.execute_command(
                command=command,
                natural_request=f"Workflow step: {step.name}",
                explanation=step.description,
                dry_run=execution_state["dry_run"],
                working_dir=working_dir,
                environment=env if env else None
            )
            
            # Extract outputs from the command result
            outputs = {}
            outputs[f"{step.id}_success"] = result.get("success", False)
            outputs[f"{step.id}_return_code"] = result.get("return_code", -1)
            
            if "stdout" in result:
                outputs[f"{step.id}_stdout"] = result["stdout"]
                # Try to extract variables from stdout
                extracted_vars = self._extract_variables_from_output(result["stdout"])
                outputs.update(extracted_vars)
            
            if "stderr" in result:
                outputs[f"{step.id}_stderr"] = result["stderr"]
            
            return {
                "success": result.get("success", False),
                "command": command,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "return_code": result.get("return_code", -1),
                "outputs": outputs
            }
            
        except Exception as e:
            self._logger.exception(f"Error executing command step: {str(e)}")
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    async def _execute_tool_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool step in a workflow using universal_cli_translator.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        if not step.tool:
            return {
                "success": False,
                "error": "Missing tool name for tool step"
            }
        
        # Get tool name and command
        tool = self._substitute_variables(step.tool, execution_state["variables"])
        command = self._substitute_variables(step.command or "", execution_state["variables"])
        
        # Combine tool and command
        full_command = f"{tool} {command}".strip()
        
        self._logger.info(f"Executing tool command: {full_command}")
        
        # If dry run, just simulate the command
        if execution_state["dry_run"]:
            return {
                "success": True,
                "tool": tool,
                "command": full_command,
                "stdout": f"[DRY RUN] Would execute tool: {full_command}",
                "stderr": "",
                "return_code": 0,
                "outputs": {}
            }
        
        # Determine working directory
        working_dir = None
        if step.working_dir:
            working_dir = self._substitute_variables(step.working_dir, execution_state["variables"])
        
        # Set up environment variables
        env = {}
        if step.environment:
            for key, value in step.environment.items():
                env[key] = self._substitute_variables(value, execution_state["variables"])
        
        # Execute the command using the adaptive engine
        try:
            # Execute using proper engine
            result = await adaptive_engine.execute_command(
                command=full_command,
                natural_request=f"Workflow tool step: {step.name}",
                explanation=step.description,
                dry_run=execution_state["dry_run"],
                working_dir=working_dir,
                environment=env if env else None
            )
            
            # Extract outputs from the command result
            outputs = {}
            outputs[f"{step.id}_success"] = result.get("success", False)
            outputs[f"{step.id}_return_code"] = result.get("return_code", -1)
            
            if "stdout" in result:
                outputs[f"{step.id}_stdout"] = result["stdout"]
                # Try to extract variables from stdout
                extracted_vars = self._extract_variables_from_output(result["stdout"])
                outputs.update(extracted_vars)
            
            if "stderr" in result:
                outputs[f"{step.id}_stderr"] = result["stderr"]
            
            return {
                "success": result.get("success", False),
                "tool": tool,
                "command": full_command,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "return_code": result.get("return_code", -1),
                "outputs": outputs
            }
            
        except Exception as e:
            self._logger.exception(f"Error executing tool step: {str(e)}")
            return {
                "success": False,
                "tool": tool,
                "command": full_command,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    async def _execute_api_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an API call step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        if not step.api_url:
            return {
                "success": False,
                "error": "Missing API URL for API step"
            }
        
        # Apply variable substitution
        api_url = self._substitute_variables(step.api_url, execution_state["variables"])
        method = step.api_method or "GET"
        
        # Process headers with variable substitution
        headers = {}
        for key, value in step.api_headers.items():
            headers[key] = self._substitute_variables(value, execution_state["variables"])
        
        # Process data payload with variable substitution
        data = None
        if step.api_data:
            if isinstance(step.api_data, str):
                data = self._substitute_variables(step.api_data, execution_state["variables"])
            elif isinstance(step.api_data, dict):
                data = {}
                for key, value in step.api_data.items():
                    if isinstance(value, str):
                        data[key] = self._substitute_variables(value, execution_state["variables"])
                    else:
                        data[key] = value
        
        self._logger.info(f"Executing API call: {method} {api_url}")
        
        # If dry run, just simulate the API call
        if execution_state["dry_run"]:
            return {
                "success": True,
                "url": api_url,
                "method": method,
                "response": f"[DRY RUN] Would call API: {method} {api_url}",
                "outputs": {}
            }
        
        # Execute the API call
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=step.timeout or 30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Prepare the request
                if method.upper() in ["GET", "DELETE"]:
                    async with session.request(method, api_url, headers=headers) as response:
                        status = response.status
                        response_text = await response.text()
                        try:
                            response_json = await response.json()
                        except:
                            response_json = None
                else:  # POST, PUT, PATCH
                    if headers.get("Content-Type") == "application/json" and data:
                        async with session.request(method, api_url, json=data, headers=headers) as response:
                            status = response.status
                            response_text = await response.text()
                            try:
                                response_json = await response.json()
                            except:
                                response_json = None
                    else:
                        async with session.request(method, api_url, data=data, headers=headers) as response:
                            status = response.status
                            response_text = await response.text()
                            try:
                                response_json = await response.json()
                            except:
                                response_json = None
                
                # Prepare result
                success = 200 <= status < 300
                
                # Extract outputs from the response
                outputs = {}
                outputs[f"{step.id}_status"] = status
                outputs[f"{step.id}_success"] = success
                outputs[f"{step.id}_response_text"] = response_text
                
                if response_json:
                    outputs[f"{step.id}_response_json"] = response_json
                    
                    # Try to extract variables from JSON response
                    if isinstance(response_json, dict):
                        for key, value in response_json.items():
                            outputs[f"{step.id}_{key}"] = value
                
                return {
                    "success": success,
                    "url": api_url,
                    "method": method,
                    "status": status,
                    "response_text": response_text,
                    "response_json": response_json,
                    "outputs": outputs
                }
                
        except Exception as e:
            self._logger.exception(f"Error executing API step: {str(e)}")
            return {
                "success": False,
                "url": api_url,
                "method": method,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    async def _execute_decision_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a decision step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result with condition evaluation
        """
        if not step.condition:
            return {
                "success": False,
                "error": "Missing condition for decision step"
            }
        
        # Apply variable substitution to the condition
        condition = self._substitute_variables(step.condition, execution_state["variables"])
        
        self._logger.info(f"Evaluating condition: {condition}")
        
        # Evaluate the condition
        try:
            condition_result = await self._evaluate_condition(
                condition, 
                execution_state["variables"]
            )
            
            self._logger.debug(f"Condition evaluated to: {condition_result}")
            
            return {
                "success": True,
                "condition": condition,
                "condition_result": condition_result,
                "outputs": {
                    f"{step.id}_condition": condition,
                    f"{step.id}_result": condition_result
                }
            }
        except Exception as e:
            self._logger.exception(f"Error evaluating condition: {str(e)}")
            return {
                "success": False,
                "condition": condition,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    async def _execute_wait_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a wait step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        # Check for a wait condition
        if step.wait_condition:
            # Apply variable substitution to the condition
            condition = self._substitute_variables(step.wait_condition, execution_state["variables"])
            
            self._logger.info(f"Waiting for condition: {condition}")
            
            # If dry run, just simulate the wait
            if execution_state["dry_run"]:
                return {
                    "success": True,
                    "condition": condition,
                    "message": f"[DRY RUN] Would wait for condition: {condition}",
                    "outputs": {}
                }
            
            # Set up timeout
            timeout = step.timeout or 300  # Default to 5 minutes
            wait_interval = 5  # Check every 5 seconds
            max_attempts = timeout // wait_interval
            
            # Wait for the condition to be true
            for attempt in range(max_attempts):
                try:
                    condition_result = await self._evaluate_condition(
                        condition, 
                        execution_state["variables"]
                    )
                    
                    if condition_result:
                        self._logger.info(f"Wait condition satisfied after {attempt * wait_interval} seconds")
                        return {
                            "success": True,
                            "condition": condition,
                            "wait_time": attempt * wait_interval,
                            "outputs": {
                                f"{step.id}_wait_time": attempt * wait_interval,
                                f"{step.id}_success": True
                            }
                        }
                    
                    # Wait before checking again
                    await asyncio.sleep(wait_interval)
                    
                except Exception as e:
                    self._logger.error(f"Error evaluating wait condition: {str(e)}")
                    # Keep waiting, error may be temporary
            
            # Timeout reached
            self._logger.warning(f"Wait condition timed out after {timeout} seconds")
            return {
                "success": False,
                "condition": condition,
                "error": f"Wait condition timed out after {timeout} seconds",
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_timed_out": True,
                    f"{step.id}_wait_time": timeout
                }
            }
        else:
            # Fixed time wait
            wait_time = step.timeout or 10  # Default to 10 seconds
            
            self._logger.info(f"Waiting for {wait_time} seconds")
            
            # If dry run, just simulate the wait
            if execution_state["dry_run"]:
                return {
                    "success": True,
                    "wait_time": wait_time,
                    "message": f"[DRY RUN] Would wait for {wait_time} seconds",
                    "outputs": {}
                }
            
            # Wait for the specified time
            await asyncio.sleep(wait_time)
            
            return {
                "success": True,
                "wait_time": wait_time,
                "outputs": {
                    f"{step.id}_wait_time": wait_time,
                    f"{step.id}_success": True
                }
            }





    def _can_execute_in_parallel(self, step_ids: Set[str], steps: Dict[str, WorkflowStep]) -> bool:
        """
        Determine if a set of steps can be executed in parallel.
        
        Args:
            step_ids: Set of step IDs to check
            steps: Dictionary of all workflow steps
            
        Returns:
            True if the steps can be executed in parallel, False otherwise
        """
        # Check for steps that are explicitly marked as not parallel-safe
        for step_id in step_ids:
            step = steps.get(step_id)
            if step and hasattr(step, "parallel_safe") and not step.parallel_safe:
                return False
        
        # Check for steps that might modify the same resources
        resource_map = {}
        
        for step_id in step_ids:
            step = steps.get(step_id)
            if not step:
                continue
                
            # Determine resources affected by this step
            resources = self._get_step_resources(step)
            
            # Check for conflicts with already scheduled steps
            for resource in resources:
                if resource in resource_map:
                    # Another step uses this resource - check if operations are compatible
                    other_ops = resource_map[resource]
                    for op in resources[resource]:
                        if not self._are_operations_compatible(other_ops, op):
                            return False
                        
                    # Add operation to resource map
                    resource_map[resource].update(resources[resource])
                else:
                    # First step to use this resource
                    resource_map[resource] = resources[resource]
        
        return True
    
    def _get_step_resources(self, step: WorkflowStep) -> Dict[str, Set[str]]:
        """
        Determine resources affected by a workflow step.
        
        Args:
            step: The workflow step to analyze
            
        Returns:
            Dictionary mapping resource names to sets of operations
        """
        resources = {}
        
        # Check step type
        if step.type == WorkflowStepType.COMMAND or step.type == WorkflowStepType.TOOL:
            # Extract file paths from command
            command = step.command
            if not command:
                return resources
                
            # Look for file paths in the command
            path_pattern = r'(?:\'|\")([\/\w\.-]+)(?:\'|\")'
            file_paths = re.findall(path_pattern, command)
            
            # Add each file as a resource
            for path in file_paths:
                if os.path.isabs(path) or path.startswith('./') or path.startswith('../'):
                    resources[path] = {"access"}
                    
                    # Infer operation from command
                    if any(x in command for x in ["rm", "del", "remove", "unlink"]):
                        resources[path].add("delete")
                    elif any(x in command for x in ["write", "create", ">", "tee"]):
                        resources[path].add("write")
                    elif any(x in command for x in ["cp", "copy", "mv", "move"]):
                        resources[path].add("write")
                        resources[path].add("read")
                    else:
                        resources[path].add("read")
            
            # Check for database operations
            if any(x in command for x in ["mysql", "psql", "mongo", "sqlite"]):
                db_name = "database"
                resources[db_name] = {"access"}
                
                if any(x in command.lower() for x in ["select", "show", "describe"]):
                    resources[db_name].add("read")
                elif any(x in command.lower() for x in ["insert", "update", "delete", "drop", "create"]):
                    resources[db_name].add("write")
        
        elif step.type == WorkflowStepType.FILE:
            # File operations directly specify the resource
            if hasattr(step, "file_path") and step.file_path:
                path = step.file_path
                resources[path] = {"access"}
                
                # Determine operation from step properties
                operation = getattr(step, "operation", "read")
                if operation in ["write", "create", "append"]:
                    resources[path].add("write")
                elif operation in ["delete", "remove"]:
                    resources[path].add("delete")
                else:
                    resources[path].add("read")
        
        elif step.type == WorkflowStepType.API:
            # API calls are generally independent
            api_url = getattr(step, "api_url", "")
            if api_url:
                resources[api_url] = {"access"}
                
                # Determine operation from HTTP method
                method = getattr(step, "method", "GET").upper()
                if method in ["GET", "HEAD", "OPTIONS"]:
                    resources[api_url].add("read")
                else:
                    resources[api_url].add("write")
        
        return resources
    
    def _are_operations_compatible(self, existing_ops: Set[str], new_op: str) -> bool:
        """
        Determine if operations on the same resource are compatible for parallel execution.
        
        Args:
            existing_ops: Set of existing operations
            new_op: New operation to check
            
        Returns:
            True if operations are compatible, False otherwise
        """
        # Delete is never compatible with anything
        if "delete" in existing_ops or new_op == "delete":
            return False
        
        # Write is not compatible with another write
        if "write" in existing_ops and new_op == "write":
            return False
        
        # Read is compatible with other reads
        return True
    
    async def _execute_parallel_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a parallel step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        if not step.parallel_steps:
            return {
                "success": False,
                "error": "Missing parallel steps for parallel step"
            }
        
        self._logger.info(f"Executing {len(step.parallel_steps)} steps in parallel")
        
        # Check if all referenced steps exist in the workflow
        workflow = self._active_workflows[execution_state["workflow_id"]]["workflow"]
        parallel_steps = []
        
        for parallel_step_id in step.parallel_steps:
            if parallel_step_id in workflow.steps:
                parallel_steps.append(workflow.steps[parallel_step_id])
            else:
                self._logger.warning(f"Referenced parallel step {parallel_step_id} does not exist in workflow")
        
        if not parallel_steps:
            return {
                "success": False,
                "error": "No valid parallel steps found",
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": "No valid parallel steps found"
                }
            }
        
        # If dry run, just simulate the parallel execution
        if execution_state["dry_run"]:
            return {
                "success": True,
                "message": f"[DRY RUN] Would execute {len(parallel_steps)} steps in parallel",
                "parallel_steps": [s.id for s in parallel_steps],
                "outputs": {}
            }
        
        # Create tasks for each parallel step
        tasks = []
        results = {}
        
        for parallel_step in parallel_steps:
            # Create a copy of the execution state for this step
            step_execution_state = execution_state.copy()
            step_execution_state["is_parallel"] = True
            
            # Get the appropriate handler for the step type
            handler = self._step_handlers.get(parallel_step.type)
            if not handler:
                results[parallel_step.id] = {
                    "success": False,
                    "error": f"Unsupported step type: {parallel_step.type}"
                }
                continue
            
            # Create a task for this step
            tasks.append(handler(parallel_step, step_execution_state))
        
        # Execute all tasks in parallel
        try:
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, parallel_step in enumerate(parallel_steps):
                result = parallel_results[i]
                
                # Handle exceptions
                if isinstance(result, Exception):
                    results[parallel_step.id] = {
                        "success": False,
                        "error": str(result)
                    }
                else:
                    results[parallel_step.id] = result
                    
                    # Update execution state variables with outputs from this step
                    if result.get("success") and result.get("outputs"):
                        execution_state["variables"].update(result["outputs"])
                
                # Mark the step as completed
                execution_state["completed_steps"].add(parallel_step.id)
            
            # Determine overall success (all steps must succeed)
            success = all(r.get("success", False) for r in results.values())
            
            return {
                "success": success,
                "parallel_steps": [s.id for s in parallel_steps],
                "results": results,
                "outputs": {
                    f"{step.id}_success": success,
                    f"{step.id}_all_succeeded": success,
                    f"{step.id}_completed_count": len(results)
                }
            }
            
        except Exception as e:
            self._logger.exception(f"Error executing parallel steps: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    async def _execute_custom_code_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a custom code step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        if not step.code:
            return {
                "success": False,
                "error": "Missing code for custom code step"
            }
        
        # Apply variable substitution to the code
        code = self._substitute_variables(step.code, execution_state["variables"])
        
        self._logger.info(f"Executing custom code step: {step.id}")
        
        # If dry run, just simulate the code execution
        if execution_state["dry_run"]:
            return {
                "success": True,
                "message": f"[DRY RUN] Would execute custom code: {len(code)} characters",
                "outputs": {}
            }
        
        # Execute code using Python exec()
        # Note: This is potentially unsafe and should be properly sandboxed in a real implementation
        try:
            # Create a safe environment for code execution
            sandbox = {
                "variables": execution_state["variables"].copy(),
                "results": {},
                "os": os,
                "re": re,
                "json": json,
                "Path": Path,
                "datetime": datetime,
                "logging": logging,
                "logger": self._logger,
                "outputs": {}
            }
            
            # Add a print function that redirects to logger
            def safe_print(*args, **kwargs):
                self._logger.info(" ".join(str(arg) for arg in args))
            sandbox["print"] = safe_print
            
            # Execute the code in the sandbox
            exec(code, sandbox)
            
            # Extract any outputs defined by the code
            outputs = sandbox.get("outputs", {})
            
            # Include any updated variables
            for key, value in sandbox.get("variables", {}).items():
                if key not in execution_state["variables"] or execution_state["variables"][key] != value:
                    outputs[key] = value
            
            return {
                "success": True,
                "outputs": outputs,
                "code_execution": "Completed successfully"
            }
            
        except Exception as e:
            self._logger.exception(f"Error executing custom code: {str(e)}")
            return {
                "success": False,
                "code": code,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    async def _execute_notification_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a notification step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result
        """
        # Apply variable substitution to command or message
        message = step.command or "Workflow notification"
        message = self._substitute_variables(message, execution_state["variables"])
        
        self._logger.info(f"Sending notification: {message}")
        
        # If dry run, just simulate the notification
        if execution_state["dry_run"]:
            return {
                "success": True,
                "message": f"[DRY RUN] Would send notification: {message}",
                "outputs": {}
            }
        
        # In a real implementation, this would integrate with notification services
        # For now, we'll just log the notification
        self._logger.info(f"NOTIFICATION: {message}")
        
        # Print to console using rich
        try:
            from rich.console import Console
            from rich.panel import Panel
            
            console = Console()
            console.print("\n")
            console.print(Panel(
                message,
                title=f"Workflow Notification - {execution_state['workflow_id']}",
                border_style="yellow",
                expand=False
            ))
            
        except ImportError:
            # If rich is not available, just print the notification
            print(f"\n=== WORKFLOW NOTIFICATION ===\n{message}\n=============================\n")
        
        return {
            "success": True,
            "message": message,
            "outputs": {
                f"{step.id}_notification_sent": True,
                f"{step.id}_message": message
            }
        }
    
    async def _execute_validation_step(
        self, 
        step: WorkflowStep, 
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a validation step in a workflow.
        
        Args:
            step: The workflow step
            execution_state: Current execution state
            
        Returns:
            Execution result with validation result
        """
        if not step.condition:
            return {
                "success": False,
                "error": "Missing condition for validation step"
            }
        
        # Apply variable substitution to the condition
        condition = self._substitute_variables(step.condition, execution_state["variables"])
        
        self._logger.info(f"Validating condition: {condition}")
        
        # If dry run, assume validation passes
        if execution_state["dry_run"]:
            return {
                "success": True,
                "condition": condition,
                "validated": True,
                "message": f"[DRY RUN] Would validate condition: {condition}",
                "outputs": {
                    f"{step.id}_validated": True
                }
            }
        
        # Evaluate the condition
        try:
            validation_result = await self._evaluate_condition(
                condition, 
                execution_state["variables"]
            )
            
            # For validation, success means the condition was evaluated without error
            # But validated depends on the condition result
            return {
                "success": True,
                "condition": condition,
                "validated": validation_result,
                "outputs": {
                    f"{step.id}_condition": condition,
                    f"{step.id}_validated": validation_result
                }
            }
        except Exception as e:
            self._logger.exception(f"Error validating condition: {str(e)}")
            return {
                "success": False,
                "condition": condition,
                "error": str(e),
                "outputs": {
                    f"{step.id}_success": False,
                    f"{step.id}_error": str(e)
                }
            }
    
    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in a text string.
        
        Args:
            text: Text with potential variable references
            variables: Dictionary of variables
            
        Returns:
            Text with variables substituted
        """
        if not text or not isinstance(text, str):
            return text
            
        result = text
        
        # Replace ${var} syntax
        for var_name, var_value in variables.items():
            placeholder = f"${{{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))
        
        # Replace $var syntax (only for word boundaries to avoid partial replacements)
        var_pattern = r'\$([a-zA-Z0-9_]+)'
        matches = re.findall(var_pattern, result)
        
        for var_name in matches:
            if var_name in variables:
                # Replace with word boundary check
                result = re.sub(r'\$' + var_name + r'\b', str(variables[var_name]), result)
        
        return result
    
    def _extract_variables_from_output(self, output: str) -> Dict[str, Any]:
        """
        Extract variables from command output.
        
        Args:
            output: Command output text
            
        Returns:
            Dictionary of extracted variables
        """
        variables = {}
        
        # Look for lines like "VARIABLE=value" or "export VARIABLE=value"
        lines = output.splitlines()
        for line in lines:
            line = line.strip()
            if "=" in line:
                # Check for export pattern
                if line.startswith("export "):
                    line = line[7:]  # Remove "export "
                
                # Split at first equals sign
                parts = line.split("=", 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()
                    
                    # Remove quotes if present
                    if (var_value.startswith('"') and var_value.endswith('"')) or \
                       (var_value.startswith("'") and var_value.endswith("'")):
                        var_value = var_value[1:-1]
                    
                    variables[var_name] = var_value
        
        # Look for JSON output pattern
        if output.strip().startswith("{") and output.strip().endswith("}"):
            try:
                json_data = json.loads(output)
                if isinstance(json_data, dict):
                    for key, value in json_data.items():
                        variables[key] = value
            except json.JSONDecodeError:
                pass
        
        return variables
    
    async def _evaluate_condition(
        self, 
        condition: str, 
        variables: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition expression.
        
        Args:
            condition: The condition expression
            variables: Variables to use in evaluation
            
        Returns:
            Boolean result of the condition
        """
        # Check for simple comparison patterns
        # Variable equals value: $var == value
        var_equals_match = re.search(r'\$\{?([a-zA-Z0-9_]+)\}?\s*==\s*(.+)', condition)
        if var_equals_match:
            var_name = var_equals_match.group(1)
            value_str = var_equals_match.group(2).strip()
            
            # Remove quotes if present
            if (value_str.startswith('"') and value_str.endswith('"')) or \
               (value_str.startswith("'") and value_str.endswith("'")):
                value_str = value_str[1:-1]
            
            # Get variable value
            if var_name in variables:
                var_value = variables[var_name]
                return str(var_value) == value_str
            
            return False
        
        # Variable not equals value: $var != value
        var_not_equals_match = re.search(r'\$\{?([a-zA-Z0-9_]+)\}?\s*!=\s*(.+)', condition)
        if var_not_equals_match:
            var_name = var_not_equals_match.group(1)
            value_str = var_not_equals_match.group(2).strip()
            
            # Remove quotes if present
            if (value_str.startswith('"') and value_str.endswith('"')) or \
               (value_str.startswith("'") and value_str.endswith("'")):
                value_str = value_str[1:-1]
            
            # Get variable value
            if var_name in variables:
                var_value = variables[var_name]
                return str(var_value) != value_str
            
            return True  # Variable doesn't exist, so it's not equal
        
        # Contains pattern: 'x' in $var
        contains_match = re.search(r'[\'"](.+?)[\'"]\s+in\s+\$\{?([a-zA-Z0-9_]+)\}?', condition)
        if contains_match:
            value_str = contains_match.group(1)
            var_name = contains_match.group(2)
            
            if var_name in variables:
                var_value = str(variables[var_name])
                return value_str in var_value
            
            return False
        
        # File exists pattern
        file_exists_match = re.search(r'file\s+exists\s+(.+)', condition, re.IGNORECASE)
        if file_exists_match:
            file_path = file_exists_match.group(1).strip()
            
            # Replace variables in the file path
            file_path = self._substitute_variables(file_path, variables)
            
            # Remove quotes if present
            if (file_path.startswith('"') and file_path.endswith('"')) or \
               (file_path.startswith("'") and file_path.endswith("'")):
                file_path = file_path[1:-1]
            
            return Path(file_path).exists()
        
        # Command success pattern
        command_success_match = re.search(r'command\s+(.+?)\s+succeeds', condition, re.IGNORECASE)
        if command_success_match:
            command = command_success_match.group(1).strip()
            
            # Replace variables in the command
            command = self._substitute_variables(command, variables)
            
            # Remove quotes if present
            if (command.startswith('"') and command.endswith('"')) or \
               (command.startswith("'") and command.endswith("'")):
                command = command[1:-1]
            
            # Execute the command to check if it succeeds
            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                return process.returncode == 0
            except Exception as e:
                self._logger.error(f"Error executing command in condition: {str(e)}")
                return False
        
        # For more complex conditions, a real implementation would use a proper
        # expression evaluator with sandboxing for security
        
        # Default to evaluating the condition string as a boolean value
        return bool(condition and condition.lower() not in ["false", "0", "no", "n", ""])

# Global instance
complex_workflow_planner = ComplexWorkflowPlanner()
