# angela/toolchain/cross_tool_workflow_engine.py
"""
Cross-Tool Workflow Engine for Angela CLI.

This module provides specialized workflow orchestration capabilities for
executing complex, multi-tool workflows across different CLI tools and services.
"""
import asyncio
import re
import os
import json
import shlex
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Union, Tuple
from pathlib import Path
from enum import Enum
import uuid
import textwrap 

from pydantic import BaseModel, Field

from angela.utils.logging import get_logger
from angela.context import context_manager
from angela.core.registry import registry
from angela.ai.client import gemini_client, GeminiRequest
from angela.shell.formatter import terminal_formatter
from angela.execution.engine import execution_engine
from angela.execution.hooks import execution_hooks

logger = get_logger(__name__)

class CrossToolStep(BaseModel):
    """Model for a step in a cross-tool workflow."""
    id: str
    name: str
    description: str
    tool: str
    command: str
    transform_output: Optional[str] = None  # Code to transform output
    export_variables: Optional[List[str]] = None  # Variables to export
    required_variables: Optional[List[str]] = None  # Variables required by this step
    continue_on_failure: bool = False

class DataFlow(BaseModel):
    """Model for data flow between steps."""
    source_step: str
    target_step: str
    source_variable: str
    target_variable: str
    transformation: Optional[str] = None  # Transformation code

class CrossToolWorkflow(BaseModel):
    """Model for a cross-tool workflow."""
    id: str
    name: str
    description: str
    steps: Dict[str, CrossToolStep]
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)  # Step ID -> List of dependent step IDs
    data_flow: List[DataFlow] = Field(default_factory=list)
    entry_points: List[str] = Field(default_factory=list)  # List of step IDs
    variables: Dict[str, Any] = Field(default_factory=dict)  # Initial variables
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CrossToolWorkflowEngine:
    """
    Specialized workflow engine for orchestrating complex workflows
    across different CLI tools and services.
    """
    
    def __init__(self):
        """Initialize the cross-tool workflow engine."""
        self._logger = logger
        self._active_workflows = {}  # ID -> workflow state
        self._workflow_history = {}  # ID -> execution history
        
        # Initialize needed components
        self._enhanced_universal_cli = None
    
    def initialize(self):
        """Initialize the workflow engine."""
        # Get enhanced universal CLI
        self._enhanced_universal_cli = registry.get("enhanced_universal_cli")
        if not self._enhanced_universal_cli:
            try:
                from angela.toolchain.enhanced_universal_cli import enhanced_universal_cli
                self._enhanced_universal_cli = enhanced_universal_cli
                registry.register("enhanced_universal_cli", enhanced_universal_cli)
            except ImportError:
                self._logger.error("Failed to import Enhanced Universal CLI")
                self._enhanced_universal_cli = None
    
    async def create_workflow(
        self,
        request: str,
        context: Dict[str, Any],
        tools: Optional[List[str]] = None,
        max_steps: int = 20
    ) -> CrossToolWorkflow:
        """
        Create a cross-tool workflow based on a natural language request.
        
        Args:
            request: Natural language request
            context: Context information
            tools: Optional list of tools to include
            max_steps: Maximum number of steps to generate
            
        Returns:
            A CrossToolWorkflow object
        """
        self._logger.info(f"Creating cross-tool workflow: {request}")
        
        # Initialize if needed
        if not self._enhanced_universal_cli:
            self.initialize()
        
        # If tools not provided, try to detect from the request
        if not tools:
            tools = await self._detect_required_tools(request)
            self._logger.info(f"Detected tools: {tools}")
        
        # Generate workflow
        try:
            workflow_data = await self._generate_workflow(request, context, tools, max_steps)
            
            # Create workflow object
            workflow_id = workflow_data.get("id", str(uuid.uuid4()))
            workflow_name = workflow_data.get("name", f"Workflow {workflow_id[:8]}")
            description = workflow_data.get("description", request)
            
            # Create step objects
            steps = {}
            steps_data = workflow_data.get("steps", {})
            for step_id, step_data in steps_data.items():
                steps[step_id] = CrossToolStep(
                    id=step_id,
                    name=step_data.get("name", f"Step {step_id}"),
                    description=step_data.get("description", ""),
                    tool=step_data.get("tool", ""),
                    command=step_data.get("command", ""),
                    transform_output=step_data.get("transform_output"),
                    export_variables=step_data.get("export_variables", []),
                    required_variables=step_data.get("required_variables", []),
                    continue_on_failure=step_data.get("continue_on_failure", False)
                )
            
            # Get dependencies
            dependencies = workflow_data.get("dependencies", {})
            
            # Get data flow
            data_flow = []
            data_flow_data = workflow_data.get("data_flow", [])
            for flow_data in data_flow_data:
                data_flow.append(DataFlow(
                    source_step=flow_data.get("source_step", ""),
                    target_step=flow_data.get("target_step", ""),
                    source_variable=flow_data.get("source_variable", ""),
                    target_variable=flow_data.get("target_variable", ""),
                    transformation=flow_data.get("transformation")
                ))
            
            # Get entry points
            entry_points = workflow_data.get("entry_points", [])
            if not entry_points and steps:
                # If no entry points provided, use first step
                entry_points = [next(iter(steps.keys()))]
            
            # Get initial variables
            variables = workflow_data.get("variables", {})
            
            # Create workflow object
            workflow = CrossToolWorkflow(
                id=workflow_id,
                name=workflow_name,
                description=description,
                steps=steps,
                dependencies=dependencies,
                data_flow=data_flow,
                entry_points=entry_points,
                variables=variables,
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "request": request,
                    "tools": tools
                }
            )
            
            return workflow
        
        except Exception as e:
            self._logger.error(f"Error creating cross-tool workflow: {str(e)}")
            raise
    
    async def execute_workflow(
        self,
        workflow: CrossToolWorkflow,
        variables: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a cross-tool workflow.
        
        Args:
            workflow: The workflow to execute
            variables: Optional initial variables
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing cross-tool workflow: {workflow.name}")
        
        # Initialize execution state
        execution_state = {
            "workflow_id": workflow.id,
            "started_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "variables": workflow.variables.copy(),
            "completed_steps": set(),
            "failed_steps": set(),
            "results": {},
            "status": "running"
        }
        
        # Update with provided variables
        if variables:
            execution_state["variables"].update(variables)
        
        # Store the active workflow
        self._active_workflows[workflow.id] = execution_state
        
        try:
            # Determine initial steps to execute (entry points)
            steps_to_execute = self._get_initial_steps(workflow)
            
            # Track all steps
            all_steps = set(workflow.steps.keys())
            
            # Execute steps until no more steps can be executed
            while steps_to_execute:
                # Get next batch of steps to execute (based on dependencies)
                executable_steps = self._get_executable_steps(workflow, steps_to_execute, execution_state)
                
                if not executable_steps:
                    # Check if we're stuck
                    remaining_steps = all_steps - execution_state["completed_steps"] - execution_state["failed_steps"]
                    if remaining_steps:
                        self._logger.warning(f"Workflow execution is stuck. Remaining steps: {remaining_steps}")
                        execution_state["status"] = "stuck"
                    else:
                        self._logger.info("All workflow steps completed")
                        execution_state["status"] = "completed"
                    break
                
                # Execute steps
                for step_id in executable_steps:
                    step = workflow.steps[step_id]
                    
                    # Execute the step
                    self._logger.info(f"Executing step {step_id}: {step.name}")
                    result = await self._execute_step(step, workflow, execution_state)
                    
                    # Store the result
                    execution_state["results"][step_id] = result
                    
                    # Update step status
                    if result.get("success", False):
                        execution_state["completed_steps"].add(step_id)
                        
                        # Apply data flow from this step
                        await self._apply_data_flow(step_id, workflow, execution_state)
                    else:
                        execution_state["failed_steps"].add(step_id)
                        
                        # Check if this failure should stop the workflow
                        if not step.continue_on_failure:
                            self._logger.warning(f"Step {step_id} failed and is critical - stopping workflow")
                            execution_state["status"] = "failed"
                            break
                
                # If status is failed, stop execution
                if execution_state["status"] == "failed":
                    break
                
                # Update steps to execute - remove completed and failed steps
                steps_to_execute -= execution_state["completed_steps"]
                steps_to_execute -= execution_state["failed_steps"]
                
                # Add new executable steps based on dependencies
                new_steps = self._get_next_steps(workflow, execution_state)
                steps_to_execute.update(new_steps)
            
            # Calculate success based on status and critical steps
            critical_steps = [step_id for step_id, step in workflow.steps.items() 
                             if not step.continue_on_failure]
            
            failed_critical_steps = execution_state["failed_steps"].intersection(critical_steps)
            
            execution_state["success"] = (
                execution_state["status"] != "failed" and
                execution_state["status"] != "stuck" and
                len(failed_critical_steps) == 0
            )
            
            # Add end time
            execution_state["ended_at"] = datetime.now().isoformat()
            
            # Store execution history
            self._workflow_history[workflow.id] = {
                "workflow": workflow.dict(),
                "execution": {
                    "started_at": execution_state["started_at"],
                    "ended_at": execution_state["ended_at"],
                    "success": execution_state["success"],
                    "status": execution_state["status"],
                    "steps_completed": list(execution_state["completed_steps"]),
                    "steps_failed": list(execution_state["failed_steps"]),
                    "variables": execution_state["variables"]
                }
            }
            
            # Clear active workflow
            if workflow.id in self._active_workflows:
                del self._active_workflows[workflow.id]
            
            # Return execution results
            return {
                "workflow_id": execution_state["workflow_id"],
                "success": execution_state["success"],
                "status": execution_state["status"],
                "steps_total": len(all_steps),
                "steps_completed": len(execution_state["completed_steps"]),
                "steps_failed": len(execution_state["failed_steps"]),
                "started_at": execution_state["started_at"],
                "ended_at": execution_state["ended_at"],
                "variables": execution_state["variables"],
                "results": execution_state["results"]
            }
            
        except Exception as e:
            self._logger.error(f"Error executing workflow: {str(e)}")
            
            # Update execution state
            execution_state["status"] = "error"
            execution_state["error"] = str(e)
            execution_state["ended_at"] = datetime.now().isoformat()
            execution_state["success"] = False
            
            # Clear active workflow
            if workflow.id in self._active_workflows:
                del self._active_workflows[workflow.id]
            
            # Return error result
            return {
                "workflow_id": execution_state["workflow_id"],
                "success": False,
                "status": "error",
                "error": str(e),
                "started_at": execution_state["started_at"],
                "ended_at": execution_state["ended_at"]
            }
    
    def _get_initial_steps(self, workflow: CrossToolWorkflow) -> Set[str]:
        """
        Get initial steps to execute based on entry points.
        
        Args:
            workflow: The workflow
            
        Returns:
            Set of step IDs to execute initially
        """
        # Use entry points or first step if not specified
        if workflow.entry_points:
            return set(workflow.entry_points)
        elif workflow.steps:
            return {next(iter(workflow.steps.keys()))}
        else:
            return set()
    
    def _get_executable_steps(
        self,
        workflow: CrossToolWorkflow,
        steps_to_execute: Set[str],
        execution_state: Dict[str, Any]
    ) -> Set[str]:
        """
        Get steps that can be executed based on dependencies.
        
        Args:
            workflow: The workflow
            steps_to_execute: Steps being considered for execution
            execution_state: Current execution state
            
        Returns:
            Set of executable step IDs
        """
        executable_steps = set()
        
        for step_id in steps_to_execute:
            # Check if already completed or failed
            if (step_id in execution_state["completed_steps"] or 
                step_id in execution_state["failed_steps"]):
                continue
            
            # Check if step exists
            if step_id not in workflow.steps:
                continue
            
            # Check dependencies - step is executable if all dependencies are completed
            dependencies_satisfied = True
            
            # Get dependencies for this step
            for dep_step_id in workflow.dependencies.get(step_id, []):
                if dep_step_id not in execution_state["completed_steps"]:
                    dependencies_satisfied = False
                    break
            
            # Check required variables
            step = workflow.steps[step_id]
            for var_name in step.required_variables or []:
                if var_name not in execution_state["variables"]:
                    dependencies_satisfied = False
                    break
            
            if dependencies_satisfied:
                executable_steps.add(step_id)
        
        return executable_steps
    
    def _get_next_steps(
        self,
        workflow: CrossToolWorkflow,
        execution_state: Dict[str, Any]
    ) -> Set[str]:
        """
        Get next steps to execute based on dependencies.
        
        Args:
            workflow: The workflow
            execution_state: Current execution state
            
        Returns:
            Set of step IDs to execute next
        """
        next_steps = set()
        
        # For each step, check if its dependencies are satisfied
        for step_id in workflow.steps:
            # Skip completed or failed steps
            if (step_id in execution_state["completed_steps"] or 
                step_id in execution_state["failed_steps"]):
                continue
            
            # Check dependencies
            dependencies_satisfied = True
            for dep_step_id in workflow.dependencies.get(step_id, []):
                if dep_step_id not in execution_state["completed_steps"]:
                    dependencies_satisfied = False
                    break
            
            # Check required variables
            step = workflow.steps[step_id]
            for var_name in step.required_variables or []:
                if var_name not in execution_state["variables"]:
                    dependencies_satisfied = False
                    break
            
            if dependencies_satisfied:
                next_steps.add(step_id)
        
        return next_steps
    
    async def _execute_step(
        self,
        step: CrossToolStep,
        workflow: CrossToolWorkflow,
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.
        
        Args:
            step: The step to execute
            workflow: The workflow
            execution_state: Current execution state
            
        Returns:
            Dictionary with step execution results
        """
        self._logger.debug(f"Executing step {step.id}: {step.name}")
        
        # Check if this is a dry run
        if execution_state["dry_run"]:
            return {
                "success": True,
                "dry_run": True,
                "message": f"[DRY RUN] Would execute: {step.tool} {step.command}"
            }
        
        # Parse the command, replacing variable references
        command = self._substitute_variables(step.command, execution_state["variables"])
        
        # Execute the command
        try:
            # Use enhanced universal CLI for command execution
            if self._enhanced_universal_cli:
                # Try to use the enhanced translation if available
                translation_result = await self._enhanced_universal_cli.translate_with_context(
                    request=command,
                    tool=step.tool
                )
                
                if translation_result.get("success", False) and "command" in translation_result:
                    command = translation_result["command"]
            
            # Execute the command
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=command,
                check_safety=True
            )
            
            # Process the output
            result = {
                "success": return_code == 0,
                "return_code": return_code,
                "stdout": stdout,
                "stderr": stderr,
                "command": command
            }
            
            # Apply output transformation if specified
            if step.transform_output:
                try:
                    transformed_output = await self._transform_step_output(
                        step.transform_output,
                        stdout,
                        stderr,
                        return_code
                    )
                    
                    if transformed_output is not None:
                        result["transformed_output"] = transformed_output
                except Exception as e:
                    self._logger.error(f"Error transforming output: {str(e)}")
            
            # Extract variables if specified
            if step.export_variables and (stdout or stderr):
                variables = self._extract_variables_from_output(stdout, step.export_variables)
                
                if variables:
                    result["variables"] = variables
                    # Update execution state variables
                    execution_state["variables"].update(variables)
                    
                    self._logger.debug(f"Extracted variables: {variables}")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error executing step {step.id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _transform_step_output(
        self,
        transform_code: str,
        stdout: str,
        stderr: str,
        return_code: int
    ) -> Any:
        """
        Transform step output using the provided code.
        
        Args:
            transform_code: Python code for transformation
            stdout: Command standard output
            stderr: Command standard error
            return_code: Command return code
            
        Returns:
            Transformed output
        """
        # Create a sandbox for code execution
        sandbox = {
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "result": None,
            "import_modules": ["json", "re"],
            "json": json,
            "re": re
        }
        
        # Prefix with safety wrapper
        safe_code = f"""
# Transformation code
import json
import re

def transform_output(stdout, stderr, return_code):
    result = None
    
    # User provided transformation code
{textwrap.indent(transform_code, '    ')}
    
    return result

# Execute transformation
result = transform_output(stdout, stderr, return_code)
"""
        
        # Execute in a temporary file
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as temp_file:
            temp_file.write(safe_code)
            temp_file.flush()
            
            # Run the transformation using subprocess
            try:
                import sys
                process = await asyncio.create_subprocess_exec(
                    sys.executable, temp_file.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={"PYTHONPATH": os.pathsep.join(sys.path)}
                )
                
                proc_stdout, proc_stderr = await process.communicate()
                
                if process.returncode != 0:
                    self._logger.error(f"Error transforming output: {proc_stderr.decode()}")
                    return None
                
                # The result should be the last line of stdout
                result_line = proc_stdout.decode().strip().split("\n")[-1]
                
                try:
                    # Try to parse as JSON
                    transformed = json.loads(result_line)
                    return transformed
                except json.JSONDecodeError:
                    # Return as string
                    return result_line
                    
            except Exception as e:
                self._logger.error(f"Error executing transformation code: {str(e)}")
                return None
    
    def _extract_variables_from_output(
        self,
        output: str,
        variable_names: List[str]
    ) -> Dict[str, Any]:
        """
        Extract variables from command output.
        
        Args:
            output: Command output
            variable_names: List of variable names to extract
            
        Returns:
            Dictionary of extracted variables
        """
        variables = {}
        
        # Try to parse output as JSON first
        if output.strip().startswith('{') and output.strip().endswith('}'):
            try:
                json_data = json.loads(output)
                
                # Extract variables from JSON
                for var_name in variable_names:
                    if var_name in json_data:
                        variables[var_name] = json_data[var_name]
                
                return variables
            except json.JSONDecodeError:
                pass
        
        # Look for variable assignments in output
        for var_name in variable_names:
            # Look for patterns like "VAR=value" or "VAR: value"
            patterns = [
                rf'^{var_name}=(.+?)$',
                rf'^{var_name}:\s*(.+?)$',
                rf'export\s+{var_name}=(.+?)$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, output, re.MULTILINE)
                if match:
                    variables[var_name] = match.group(1).strip()
                    break
        
        return variables
    
    async def _apply_data_flow(
        self,
        source_step_id: str,
        workflow: CrossToolWorkflow,
        execution_state: Dict[str, Any]
    ) -> None:
        """
        Apply data flow from a completed step.
        
        Args:
            source_step_id: ID of the completed step
            workflow: The workflow
            execution_state: Current execution state
        """
        # Find data flow entries where this step is the source
        flows = [flow for flow in workflow.data_flow 
                if flow.source_step == source_step_id]
        
        if not flows:
            return
        
        for flow in flows:
            # Get the source variable from step results
            step_result = execution_state["results"].get(source_step_id, {})
            
            source_value = None
            
            # Check different places for the variable
            if flow.source_variable in step_result.get("variables", {}):
                source_value = step_result["variables"][flow.source_variable]
            elif flow.source_variable == "stdout":
                source_value = step_result.get("stdout", "")
            elif flow.source_variable == "stderr":
                source_value = step_result.get("stderr", "")
            elif flow.source_variable == "return_code":
                source_value = step_result.get("return_code", 0)
            elif "transformed_output" in step_result:
                # Check if transformed output is a dict
                transformed = step_result["transformed_output"]
                if isinstance(transformed, dict) and flow.source_variable in transformed:
                    source_value = transformed[flow.source_variable]
            
            if source_value is None:
                self._logger.warning(f"Source variable {flow.source_variable} not found in step {source_step_id}")
                continue
            
            # Apply transformation if specified
            if flow.transformation:
                try:
                    transformed_value = await self._transform_value(
                        flow.transformation,
                        source_value
                    )
                    
                    if transformed_value is not None:
                        source_value = transformed_value
                except Exception as e:
                    self._logger.error(f"Error transforming value: {str(e)}")
            
            # Set the target variable
            execution_state["variables"][flow.target_variable] = source_value
            
            self._logger.debug(f"Applied data flow: {flow.source_step}.{flow.source_variable} -> {flow.target_variable}")
    
    async def _transform_value(self, transform_code: str, value: Any) -> Any:
        """
        Transform a value using the provided code.
        
        Args:
            transform_code: Python code for transformation
            value: Value to transform
            
        Returns:
            Transformed value
        """
        # Create a sandbox for code execution
        sandbox = {
            "value": value,
            "result": None,
            "import_modules": ["json", "re"],
            "json": json,
            "re": re
        }
        
        # Prefix with safety wrapper
        safe_code = f"""
# Transformation code
import json
import re

def transform_value(value):
    result = None
    
    # User provided transformation code
{textwrap.indent(transform_code, '    ')}
    
    return result

# Execute transformation
result = transform_value(value)
"""
        
        # Execute in a temporary file
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as temp_file:
            temp_file.write(safe_code)
            temp_file.flush()
            
            # Run the transformation using subprocess
            try:
                import sys
                
                # Create a JSON serializable representation of the value
                value_json = json.dumps(value)
                
                process = await asyncio.create_subprocess_exec(
                    sys.executable, temp_file.name,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={"PYTHONPATH": os.pathsep.join(sys.path)}
                )
                
                proc_stdout, proc_stderr = await process.communicate(value_json.encode())
                
                if process.returncode != 0:
                    self._logger.error(f"Error transforming value: {proc_stderr.decode()}")
                    return None
                
                # The result should be the last line of stdout
                result_line = proc_stdout.decode().strip().split("\n")[-1]
                
                try:
                    # Try to parse as JSON
                    transformed = json.loads(result_line)
                    return transformed
                except json.JSONDecodeError:
                    # Return as string
                    return result_line
                    
            except Exception as e:
                self._logger.error(f"Error executing transformation code: {str(e)}")
                return None
    
    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variable references in a string.
        
        Args:
            text: The string to substitute
            variables: Dictionary of variables
            
        Returns:
            String with variables substituted
        """
        if not text:
            return text
        
        result = text
        
        # Replace ${var} syntax
        for var_name, var_value in variables.items():
            placeholder = f"${{{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))
        
        # Replace $var syntax (only for word boundaries)
        for var_name, var_value in variables.items():
            result = re.sub(r'\$' + var_name + r'\b', str(var_value), result)
        
        return result
    
    async def _detect_required_tools(self, request: str) -> List[str]:
        """
        Detect which tools are required for a workflow based on a request.
        
        Args:
            request: Natural language request
            
        Returns:
            List of detected tools
        """
        self._logger.debug(f"Detecting required tools for: {request}")
        
        # Use AI to detect required tools
        prompt = f"""
Analyze this workflow request to determine which command-line tools would be needed:
"{request}"

Return a JSON array with the names of the required CLI tools (e.g., git, docker, aws, etc.)
Sort them by importance (most important first).

Format:
["tool1", "tool2", "tool3"]
"""

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=500)
            response = await gemini_client.generate_text(api_request)
            
            # Extract tools
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            detected_tools = json.loads(json_str)
            
            # Validate tools
            if not isinstance(detected_tools, list):
                raise ValueError("Expected a list of tools")
            
            # Convert to strings and ensure proper format
            return [str(tool).strip().lower() for tool in detected_tools]
            
        except Exception as e:
            self._logger.error(f"Error detecting required tools: {str(e)}")
            
            # Try basic pattern matching as fallback
            common_tools = ["git", "docker", "npm", "pip", "aws", "gcloud", "kubectl"]
            detected = []
            
            for tool in common_tools:
                if tool in request.lower():
                    detected.append(tool)
            
            return detected or ["bash"]  # Default to bash if no tools detected
    
    async def _generate_workflow(
        self,
        request: str,
        context: Dict[str, Any],
        tools: List[str],
        max_steps: int
    ) -> Dict[str, Any]:
        """
        Generate a workflow based on a request, context, and tools.
        
        Args:
            request: Natural language request
            context: Context information
            tools: List of tools to include
            max_steps: Maximum number of steps
            
        Returns:
            Dictionary with workflow definition
        """
        self._logger.info(f"Generating workflow for: {request}")
        
        # Create a detailed prompt for workflow generation
        project_info = self._extract_project_info(context)
        
        # Get information about the tools
        tool_info = await self._get_tool_info(tools)
        
        prompt = f"""
You are an expert workflow designer. Create a detailed cross-tool workflow for this request:
"{request}"

Project information:
{project_info}

Tools to use: {', '.join(tools)}

Tool information:
{tool_info}

Maximum steps: {max_steps}

Create a complete workflow specification in JSON format with the following structure:
{{
  "id": "unique_id",
  "name": "Workflow Name",
  "description": "Detailed description of what the workflow does",
  "steps": {{
    "step1": {{
      "name": "Step 1 Name",
      "description": "What this step does",
      "tool": "tool_name",
      "command": "command to execute",
      "transform_output": "optional code to transform output",
      "export_variables": ["variable1", "variable2"],
      "required_variables": ["dependency1", "dependency2"],
      "continue_on_failure": false
    }},
    // More steps...
  }},
  "dependencies": {{
    "step2": ["step1"],  // Step2 depends on step1
    "step3": ["step1", "step2"]  // Step3 depends on both step1 and step2
  }},
  "data_flow": [
    {{
      "source_step": "step1",
      "target_step": "step2",
      "source_variable": "variable1",
      "target_variable": "input1",
      "transformation": "optional transformation code"
    }}
    // More data flows...
  ],
  "entry_points": ["step1"],  // Steps to start execution with
  "variables": {{
    "initial_var1": "value1",
    "initial_var2": "value2"
  }}
}}

Ensure the workflow:
1. Uses the correct syntax for each tool
2. Includes proper command validation and error handling
3. Correctly passes data between steps using the data_flow section
4. Has meaningful step names and descriptions
5. Uses absolute paths for file references whenever possible
6. Has a logical sequence of steps with proper dependencies
7. Uses as few steps as possible to accomplish the goal efficiently
8. Makes proper use of variables for data that needs to be shared between steps
"""

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=4000)
            response = await gemini_client.generate_text(api_request)
            
            # Extract workflow JSON
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            workflow_data = json.loads(json_str)
            
            # Ensure required fields are present
            if "id" not in workflow_data:
                workflow_data["id"] = str(uuid.uuid4())
            
            if "name" not in workflow_data or not workflow_data["name"]:
                workflow_data["name"] = f"Workflow for {request[:30]}..."
            
            if "description" not in workflow_data or not workflow_data["description"]:
                workflow_data["description"] = request
            
            if "steps" not in workflow_data or not workflow_data["steps"]:
                raise ValueError("Workflow must contain steps")
            
            if "dependencies" not in workflow_data:
                workflow_data["dependencies"] = {}
            
            if "data_flow" not in workflow_data:
                workflow_data["data_flow"] = []
            
            if "entry_points" not in workflow_data or not workflow_data["entry_points"]:
                # Use first step as entry point
                workflow_data["entry_points"] = [next(iter(workflow_data["steps"].keys()))]
            
            if "variables" not in workflow_data:
                workflow_data["variables"] = {}
            
            return workflow_data
            
        except Exception as e:
            self._logger.error(f"Error generating workflow: {str(e)}")
            raise
    
    def _extract_project_info(self, context: Dict[str, Any]) -> str:
        """
        Extract relevant project information from context.
        
        Args:
            context: Context information
            
        Returns:
            String with project information
        """
        info = []
        
        if "project_root" in context:
            info.append(f"Project root: {context['project_root']}")
        
        if "cwd" in context:
            info.append(f"Current directory: {context['cwd']}")
        
        if "project_type" in context:
            info.append(f"Project type: {context['project_type']}")
        
        # Add project state if available
        if "project_state" in context:
            state = context["project_state"]
            
            # Add Git information
            if "git_state" in state:
                git_state = state["git_state"]
                if git_state.get("is_git_repo", False):
                    info.append(f"Git repository: Yes")
                    if "current_branch" in git_state:
                        info.append(f"Current branch: {git_state['current_branch']}")
                    if git_state.get("has_changes", False):
                        info.append(f"Has uncommitted changes: Yes")
            
            # Add dependency information
            if "dependencies" in state:
                deps = state["dependencies"]
                if deps.get("package_manager"):
                    info.append(f"Package manager: {deps['package_manager']}")
        
        return "\n".join(info)
    
    async def _get_tool_info(self, tools: List[str]) -> str:
        """
        Get information about specified tools.
        
        Args:
            tools: List of tools
            
        Returns:
            String with tool information
        """
        info = []
        
        for tool in tools:
            # Basic command for getting version information
            version_cmd = f"{tool} --version"
            
            try:
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command=version_cmd,
                    check_safety=True
                )
                
                if return_code == 0 and stdout.strip():
                    info.append(f"{tool}: {stdout.strip()}")
                else:
                    # Try alternative version flag
                    version_cmd = f"{tool} -v"
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command=version_cmd,
                        check_safety=True
                    )
                    
                    if return_code == 0 and stdout.strip():
                        info.append(f"{tool}: {stdout.strip()}")
                    else:
                        info.append(f"{tool}: Available but version unknown")
            except Exception:
                # Just note that the tool is being used
                info.append(f"{tool}: Will be used in workflow")
        
        return "\n".join(info)
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the status of a workflow execution.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Dictionary with workflow status
        """
        # Check if workflow is active
        if workflow_id in self._active_workflows:
            execution_state = self._active_workflows[workflow_id]
            
            return {
                "workflow_id": workflow_id,
                "status": execution_state["status"],
                "active": True,
                "started_at": execution_state["started_at"],
                "steps_completed": len(execution_state["completed_steps"]),
                "steps_failed": len(execution_state["failed_steps"]),
                "current_variables": execution_state["variables"]
            }
        
        # Check workflow history
        if workflow_id in self._workflow_history:
            history = self._workflow_history[workflow_id]["execution"]
            
            return {
                "workflow_id": workflow_id,
                "status": history["status"],
                "active": False,
                "started_at": history["started_at"],
                "ended_at": history["ended_at"],
                "success": history.get("success", False),
                "steps_completed": len(history["steps_completed"]),
                "steps_failed": len(history["steps_failed"])
            }
        
        # Workflow not found
        return {
            "workflow_id": workflow_id,
            "status": "not_found",
            "active": False
        }
    
    async def update_workflow(
        self,
        workflow: CrossToolWorkflow,
        request: str,
        context: Dict[str, Any]
    ) -> CrossToolWorkflow:
        """
        Update an existing workflow based on a new request.
        
        Args:
            workflow: Existing workflow
            request: New request to incorporate
            context: Context information
            
        Returns:
            Updated workflow
        """
        self._logger.info(f"Updating workflow {workflow.name}: {request}")
        
        # Get existing tools
        existing_tools = set()
        for step in workflow.steps.values():
            if step.tool:
                existing_tools.add(step.tool)
        
        # Detect new tools required by the request
        new_tools = await self._detect_required_tools(request)
        
        # Combine tools
        tools = list(existing_tools) + [t for t in new_tools if t not in existing_tools]
        
        # Create an enhancing prompt
        prompt = f"""
You are updating an existing workflow to incorporate new requirements.

Original workflow:
{json.dumps(workflow.dict(), indent=2)}

New requirements:
"{request}"

Tools available: {', '.join(tools)}

Update the workflow to incorporate the new requirements while preserving as much of the original workflow as possible.
You should:
1. Modify existing steps if they need to change
2. Add new steps as needed
3. Update dependencies and data flow
4. Ensure the workflow remains coherent and efficient

Return the complete updated workflow in the same JSON format as the original.
"""

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=4000)
            response = await gemini_client.generate_text(api_request)
            
            # Extract workflow JSON
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            workflow_data = json.loads(json_str)
            
            # Create updated workflow
            updated_workflow = CrossToolWorkflow(**workflow_data)
            
            # Update metadata
            if "metadata" not in updated_workflow.dict() or not updated_workflow.metadata:
                updated_workflow.metadata = workflow.metadata.copy()
            
            updated_workflow.metadata["updated_at"] = datetime.now().isoformat()
            updated_workflow.metadata["update_request"] = request
            
            return updated_workflow
            
        except Exception as e:
            self._logger.error(f"Error updating workflow: {str(e)}")
            raise

# Create global instance
cross_tool_workflow_engine = CrossToolWorkflowEngine()

# Register it in the service registry
registry.register("cross_tool_workflow_engine", cross_tool_workflow_engine)

# Initialize on module import
cross_tool_workflow_engine.initialize()

