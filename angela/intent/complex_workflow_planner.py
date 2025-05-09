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
        Plan a complex workflow based on a natural language request.
        
        Args:
            request: Natural language request
            context: Context information
            max_steps: Maximum number of steps to include
            
        Returns:
            ComplexWorkflowPlan object
        """
        self._logger.info(f"Planning complex workflow: {request}")
        
        # Generate workflow plan using AI
        plan_data = await self._generate_workflow_plan(request, context, max_steps)
        
        try:
            # Create unique ID for the workflow
            workflow_id = str(uuid.uuid4())
            
            # Convert to the workflow plan model
            workflow_plan = ComplexWorkflowPlan(
                id=workflow_id,
                name=plan_data.get("name", f"Workflow_{workflow_id[:8]}"),
                description=plan_data.get("description", "Complex workflow"),
                goal=request,
                steps=self._convert_step_data_to_models(plan_data.get("steps", {})),
                variables=self._convert_variable_data_to_models(plan_data.get("variables", {})),
                entry_points=plan_data.get("entry_points", []),
                exit_points=plan_data.get("exit_points", []),
                context=context,
                created=datetime.now(),
                metadata={
                    "request": request,
                    "generated_at": datetime.now().isoformat(),
                    "generation_model": "Gemini"
                }
            )
            
            return workflow_plan
            
        except Exception as e:
            self._logger.error(f"Error creating complex workflow plan: {str(e)}")
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
        variables: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a complex workflow plan.
        
        Args:
            workflow: The workflow plan to execute
            variables: Initial variable values
            dry_run: Whether to simulate execution
            transaction_id: ID for the rollback transaction
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing complex workflow: {workflow.name} (ID: {workflow.id})")
        
        # Register this workflow as active
        self._active_workflows[workflow.id] = {
            "start_time": datetime.now(),
            "status": "running",
            "workflow": workflow,
            "results": {},
            "variables": variables or {}
        }
        
        try:
            # Initialize execution state
            execution_state = {
                "workflow_id": workflow.id,
                "start_time": datetime.now(),
                "variables": dict(variables or {}),
                "results": {},
                "completed_steps": set(),
                "pending_steps": {},
                "execution_path": [],
                "dry_run": dry_run,
                "transaction_id": transaction_id,
                "status": "running"
            }
            
            # Add default values for variables
            for var_name, var_def in workflow.variables.items():
                if var_name not in execution_state["variables"] and var_def.default_value is not None:
                    execution_state["variables"][var_name] = var_def.default_value
            
            # Initialize with entry points
            for entry_point in workflow.entry_points:
                if entry_point in workflow.steps:
                    execution_state["pending_steps"][entry_point] = workflow.steps[entry_point]
            
            # Execute steps until all are completed or no more can be executed
            while execution_state["pending_steps"] and execution_state["status"] == "running":
                # Find steps that can be executed (all dependencies satisfied)
                executable_steps = {}
                for step_id, step in execution_state["pending_steps"].items():
                    if all(self._is_dependency_satisfied(dep, execution_state) for dep in step.dependencies):
                        executable_steps[step_id] = step
                
                # If no steps can be executed, we're stuck (circular dependencies or missing steps)
                if not executable_steps:
                    self._logger.warning(f"No executable steps found in workflow {workflow.id}")
                    execution_state["status"] = "blocked"
                    break
                
                # Execute all executable steps
                newly_completed_steps = []
                
                for step_id, step in executable_steps.items():
                    self._logger.info(f"Executing step {step_id}: {step.name}")
                    
                    # Execute the step
                    handler = self._step_handlers.get(step.type)
                    if not handler:
                        self._logger.error(f"No handler found for step type {step.type}")
                        execution_state["results"][step_id] = {
                            "success": False,
                            "error": f"Unsupported step type: {step.type}"
                        }
                        newly_completed_steps.append(step_id)
                        continue
                    
                    try:
                        # Execute the step handler with the current execution state
                        result = await handler(step, execution_state)
                        
                        # Store the result
                        execution_state["results"][step_id] = result
                        
                        # Update execution path
                        execution_state["execution_path"].append(step_id)
                        
                        # Process the step's output variables
                        if result.get("success") and result.get("outputs"):
                            # Update the global variables
                            for var_name, var_value in result["outputs"].items():
                                execution_state["variables"][var_name] = var_value
                                self._logger.debug(f"Variable '{var_name}' set to value from step {step_id}")
                        
                        # Handle on_success or on_failure hooks if present
                        if result.get("success") and step.on_success:
                            # Add the success hook to pending steps if it exists
                            if step.on_success in workflow.steps:
                                execution_state["pending_steps"][step.on_success] = workflow.steps[step.on_success]
                        elif not result.get("success") and step.on_failure:
                            # Add the failure hook to pending steps if it exists
                            if step.on_failure in workflow.steps:
                                execution_state["pending_steps"][step.on_failure] = workflow.steps[step.on_failure]
                                
                        # Check if this is an exit point
                        if step_id in workflow.exit_points:
                            self._logger.info(f"Reached exit point {step_id}")
                            if not result.get("success"):
                                execution_state["status"] = "failed"
                            else:
                                execution_state["status"] = "completed"
                            
                        newly_completed_steps.append(step_id)
                        
                    except Exception as e:
                        self._logger.exception(f"Error executing step {step_id}: {str(e)}")
                        
                        execution_state["results"][step_id] = {
                            "success": False,
                            "error": str(e)
                        }
                        
                        # Check if step has on_failure hook
                        if step.on_failure:
                            # Add the failure hook to pending steps if it exists
                            if step.on_failure in workflow.steps:
                                execution_state["pending_steps"][step.on_failure] = workflow.steps[step.on_failure]
                        
                        newly_completed_steps.append(step_id)
                
                # Mark completed steps
                for step_id in newly_completed_steps:
                    execution_state["completed_steps"].add(step_id)
                    if step_id in execution_state["pending_steps"]:
                        del execution_state["pending_steps"][step_id]
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time = (end_time - execution_state["start_time"]).total_seconds()
            
            # Prepare final result
            success = execution_state["status"] == "completed"
            if execution_state["status"] == "running" and not execution_state["pending_steps"]:
                # All steps completed successfully
                success = True
                execution_state["status"] = "completed"
            
            result = {
                "success": success,
                "status": execution_state["status"],
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "steps_completed": len(execution_state["completed_steps"]),
                "steps_total": len(workflow.steps),
                "results": execution_state["results"],
                "variables": execution_state["variables"],
                "execution_path": execution_state["execution_path"],
                "execution_time": execution_time,
                "start_time": execution_state["start_time"].isoformat(),
                "end_time": end_time.isoformat()
            }
            
            # Update workflow status in active workflows
            self._active_workflows[workflow.id]["status"] = execution_state["status"]
            self._active_workflows[workflow.id]["end_time"] = end_time
            self._active_workflows[workflow.id]["results"] = result
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error in workflow execution: {str(e)}")
            
            # Update workflow status in active workflows
            end_time = datetime.now()
            self._active_workflows[workflow.id]["status"] = "failed"
            self._active_workflows[workflow.id]["end_time"] = end_time
            self._active_workflows[workflow.id]["error"] = str(e)
            
            return {
                "success": False,
                "status": "failed",
                "error": str(e),
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "execution_time": (end_time - self._active_workflows[workflow.id]["start_time"]).total_seconds()
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
