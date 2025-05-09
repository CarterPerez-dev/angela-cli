# angela/intent/planner.py
"""
Task planning and goal decomposition for Angela CLI.

This module handles breaking down complex high-level goals into
executable action plans with dependencies and execution flow.
It provides two levels of planning capability:
1. Basic planning - For straightforward sequential tasks
2. Advanced planning - For complex tasks with branching, conditionals, and various step types
"""
import os
import re
import json
import shlex
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from angela.intent.models import ActionPlan, Intent, IntentType
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

#######################
# Basic Planning Models
#######################

class PlanStep(BaseModel):
    """Model for a single step in a basic plan."""
    command: str = Field(..., description="The command to execute")
    explanation: str = Field(..., description="Explanation of the command")
    dependencies: List[int] = Field(default_factory=list, description="Indices of steps this step depends on")
    estimated_risk: int = Field(0, description="Estimated risk level (0-4)")


class TaskPlan(BaseModel):
    """Model for a complete basic task plan."""
    goal: str = Field(..., description="The original high-level goal")
    steps: List[PlanStep] = Field(..., description="Steps to achieve the goal")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")

#######################
# Advanced Planning Models
#######################

class PlanStepType(str, Enum):
    """Types of plan steps for advanced planning."""
    COMMAND = "command"  # Shell command
    CODE = "code"        # Code to execute or save
    FILE = "file"        # File operation
    DECISION = "decision"  # Decision point, may branch execution
    API = "api"          # API call
    LOOP = "loop"        # Looping construct


class AdvancedPlanStep(BaseModel):
    """Model for an advanced plan step with additional capabilities."""
    id: str = Field(..., description="Unique identifier for this step")
    type: PlanStepType = Field(..., description="Type of step")
    description: str = Field(..., description="Human-readable description")
    command: Optional[str] = Field(None, description="Command to execute (for command type)")
    code: Optional[str] = Field(None, description="Code to execute or save (for code type)")
    file_path: Optional[str] = Field(None, description="Path for file operations (for file type)")
    file_content: Optional[str] = Field(None, description="Content for file operations (for file type)")
    condition: Optional[str] = Field(None, description="Condition for decision steps (for decision type)")
    true_branch: Optional[List[str]] = Field(None, description="Steps to execute if condition is true")
    false_branch: Optional[List[str]] = Field(None, description="Steps to execute if condition is false")
    api_url: Optional[str] = Field(None, description="URL for API calls (for api type)")
    api_method: Optional[str] = Field(None, description="HTTP method for API calls (for api type)")
    api_payload: Optional[Dict[str, Any]] = Field(None, description="Payload for API calls (for api type)")
    loop_items: Optional[str] = Field(None, description="Items to loop over (for loop type)")
    loop_body: Optional[List[str]] = Field(None, description="Steps to execute in loop (for loop type)")
    dependencies: List[str] = Field(default_factory=list, description="IDs of steps this step depends on")
    estimated_risk: int = Field(0, description="Estimated risk level (0-4)")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry: Optional[int] = Field(None, description="Number of retries on failure")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class AdvancedTaskPlan(BaseModel):
    """Model for an advanced task plan with branching and complex steps."""
    id: str = Field(..., description="Unique identifier for this plan")
    goal: str = Field(..., description="The original high-level goal")
    description: str = Field(..., description="Detailed description of the plan")
    steps: Dict[str, AdvancedPlanStep] = Field(..., description="Steps to achieve the goal, indexed by ID")
    entry_points: List[str] = Field(..., description="Step IDs to start execution with")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    created: datetime = Field(default_factory=datetime.now, description="When the plan was created")


#######################
# Unified Task Planner
#######################

class TaskPlanner:
    """
    Task planner for breaking down complex goals into actionable steps.
    
    This planner can generate two types of plans:
    1. Basic plans (TaskPlan) - For simple sequential tasks
    2. Advanced plans (AdvancedTaskPlan) - For complex tasks with branching execution
    
    The planner automatically determines the appropriate plan type based on the
    complexity of the goal and request context.
    """
    
    def __init__(self):
        """Initialize the task planner."""
        self._logger = logger
    
    async def plan_task(
        self, 
        goal: str, 
        context: Dict[str, Any],
        complexity: str = "auto"
    ) -> Union[TaskPlan, AdvancedTaskPlan]:
        """
        Plan a task by breaking it down into actionable steps.
        
        Args:
            goal: The high-level goal description
            context: Context information
            complexity: Planning complexity level ("simple", "advanced", or "auto")
            
        Returns:
            Either a basic TaskPlan or an advanced AdvancedTaskPlan based on complexity
        """
        self._logger.info(f"Planning task: {goal} (complexity: {complexity})")
        
        # Determine planning complexity if auto
        if complexity == "auto":
            complexity = await self._determine_complexity(goal)
            self._logger.info(f"Determined complexity: {complexity}")
        
        # Use the appropriate planning strategy
        if complexity == "simple":
            # Use basic planning for simple tasks
            return await self._create_basic_plan(goal, context)
        else:
            # Use advanced planning for complex tasks
            return await self._generate_advanced_plan(goal, context)
    
    async def _determine_complexity(self, goal: str) -> str:
        """
        Determine the appropriate planning complexity for a goal.
        
        Args:
            goal: The high-level goal
            
        Returns:
            Complexity level ("simple" or "advanced")
        """
        # Simple heuristics based on goal text
        complexity_indicators = [
            "if", "when", "based on", "for each", "foreach", "loop", "iterate",
            "depending on", "decision", "alternative", "otherwise", "create file",
            "write to file", "dynamic", "api", "request", "conditionally",
            "advanced", "complex", "multiple steps", "error handling"
        ]
        
        # Count indicators
        indicator_count = sum(1 for indicator in complexity_indicators 
                              if indicator in goal.lower())
        
        # Check goal length and complexity indicators
        if len(goal.split()) > 20 or indicator_count >= 2:
            return "advanced"
        else:
            return "simple"
    
    #######################
    # Basic Planning Methods
    #######################
    
    async def _create_basic_plan(
        self, 
        goal: str, 
        context: Dict[str, Any]
    ) -> TaskPlan:
        """
        Create a basic plan for a task.
        
        Args:
            goal: The high-level goal description
            context: Context information
            
        Returns:
            A TaskPlan with steps to achieve the goal
        """
        self._logger.info(f"Creating basic plan for task: {goal}")
        
        # Generate a plan using the AI
        prompt = self._build_planning_prompt(goal, context)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Parse the plan from the response
        plan = self._parse_plan_response(response.text, goal, context)
        
        return plan
    
    def _build_planning_prompt(
        self, 
        goal: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Build a prompt for basic planning.
        
        Args:
            goal: The high-level goal
            context: Context information
            
        Returns:
            A prompt string for the AI service
        """
        # Create context string
        context_str = "Current context:\n"
        
        if context.get("cwd"):
            context_str += f"- Current working directory: {context['cwd']}\n"
        if context.get("project_root"):
            context_str += f"- Project root: {context['project_root']}\n"
        if context.get("project_type"):
            context_str += f"- Project type: {context['project_type']}\n"
        
        # Add files in current directory for context
        if context.get("cwd"):
            try:
                dir_contents = context_manager.get_directory_contents(Path(context["cwd"]))
                files_str = "\n".join([f"- {item['name']}" for item in dir_contents])
                context_str += f"\nFiles in current directory:\n{files_str}\n"
            except Exception as e:
                self._logger.error(f"Error getting directory contents: {str(e)}")
        
        # Build the prompt
        prompt = f"""
You are Angela, an AI terminal assistant. Your task is to create a detailed plan for achieving the following goal:

GOAL: {goal}

{context_str}

Break down this goal into a sequence of shell commands that would accomplish it.
For each command, provide:
1. The exact command to run
2. A brief explanation of what the command does
3. Any dependencies (which previous steps must complete first)
4. An estimated risk level (0: SAFE, 1: LOW, 2: MEDIUM, 3: HIGH, 4: CRITICAL)

Format your response as JSON:
{{
  "steps": [
    {{
      "command": "command_1",
      "explanation": "Explanation of command 1",
      "dependencies": [],
      "estimated_risk": 1
    }},
    {{
      "command": "command_2",
      "explanation": "Explanation of command 2",
      "dependencies": [0],
      "estimated_risk": 2
    }},
    ...
  ]
}}

Ensure each command is valid and appropriate for a Linux/Unix shell environment.
Use the most efficient and standard commands to accomplish the task.
Include error handling where appropriate.
"""
        
        return prompt
    
    def _parse_plan_response(self, response: str, goal: str, context: Dict[str, Any]) -> TaskPlan:
        """
        Parse the AI response to extract the basic plan.
        
        Args:
            response: The AI response text
            goal: The original high-level goal
            context: Context information
            
        Returns:
            A TaskPlan object
        """
        try:
            # Extract JSON from the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Assume the entire response is JSON
                    json_str = response
            
            # Parse the JSON
            plan_data = json.loads(json_str)
            
            # Create a TaskPlan object
            steps = []
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    command=step_data["command"],
                    explanation=step_data["explanation"],
                    dependencies=step_data.get("dependencies", []),
                    estimated_risk=step_data.get("estimated_risk", 0)
                )
                steps.append(step)
            
            return TaskPlan(
                goal=goal,
                steps=steps,
                context=context
            )
        
        except Exception as e:
            self._logger.exception(f"Error parsing plan response: {str(e)}")
            # Create a fallback single-step plan
            return TaskPlan(
                goal=goal,
                steps=[
                    PlanStep(
                        command=f"echo 'Unable to create detailed plan for: {goal}'",
                        explanation="Fallback step due to planning error",
                        dependencies=[],
                        estimated_risk=0
                    )
                ],
                context=context
            )
    
    def create_action_plan(self, task_plan: TaskPlan) -> ActionPlan:
        """
        Convert a TaskPlan to an executable ActionPlan.
        
        Args:
            task_plan: The task plan to convert
            
        Returns:
            An ActionPlan ready for execution
        """
        # Create an intent for the action plan
        intent = Intent(
            type=IntentType.UNKNOWN,
            original_request=task_plan.goal
        )
        
        # Extract commands and explanations preserving the order
        commands = []
        explanations = []
        
        # For now, we'll execute steps in the order they appear
        # In the future, we could use the dependencies to create a proper execution order
        for step in task_plan.steps:
            commands.append(step.command)
            explanations.append(step.explanation)
        
        # Determine the overall risk level (maximum of all steps)
        risk_level = max([step.estimated_risk for step in task_plan.steps], default=0)
        
        return ActionPlan(
            intent=intent,
            commands=commands,
            explanations=explanations,
            risk_level=risk_level
        )
    

    async def execute_plan(
        self, 
        plan: Union[TaskPlan, AdvancedTaskPlan], 
        dry_run: bool = False,
        transaction_id: Optional[str] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute a task plan with transaction support.
        
        Args:
            plan: The plan to execute
            dry_run: Whether to simulate execution without making changes
            transaction_id: ID of the transaction this execution belongs to
            
        Returns:
            List of execution results for each step
        """
        self._logger.info(f"Executing plan: {plan.goal}")
        
        # Handle different plan types
        if isinstance(plan, AdvancedTaskPlan):
            return await self._execute_advanced_plan(plan, dry_run, transaction_id)
        else:
            return await self._execute_basic_plan(plan, dry_run, transaction_id)
    
    async def _execute_basic_plan(
        self, 
        plan: TaskPlan, 
        dry_run: bool = False,
        transaction_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a basic task plan with transaction support.
        
        Args:
            plan: The plan to execute
            dry_run: Whether to simulate execution without making changes
            transaction_id: ID of the transaction this execution belongs to
            
        Returns:
            List of execution results for each step
        """
        results = []
        
        # Execute each step in sequence
        for i, step in enumerate(plan.steps):
            self._logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.command}")
            
            # Generate a step_id for tracking
            step_id = f"step_{i+1}"
            
            try:
                # Execute the command
                result = await execution_engine.execute_command(
                    command=step.command,
                    check_safety=True,
                    dry_run=dry_run
                )
                
                # Record command execution in the transaction if successful
                if not dry_run and transaction_id and result[2] == 0:  # return_code == 0
                    # Import here to avoid circular imports
                    from angela.execution.rollback import rollback_manager
                    
                    await rollback_manager.record_command_execution(
                        command=step.command,
                        return_code=result[2],
                        stdout=result[0],
                        stderr=result[1],
                        transaction_id=transaction_id,
                        step_id=step_id
                    )
                
                # Format the result
                execution_result = {
                    "step": i + 1,
                    "command": step.command,
                    "explanation": step.explanation,
                    "stdout": result[0],
                    "stderr": result[1],
                    "return_code": result[2],
                    "success": result[2] == 0
                }
                
                results.append(execution_result)
                
                # Stop execution if a step fails
                if result[2] != 0:
                    self._logger.warning(f"Step {i+1} failed with return code {result[2]}")
                    break
                    
            except Exception as e:
                self._logger.exception(f"Error executing step {i+1}: {str(e)}")
                
                # Record the error
                results.append({
                    "step": i + 1,
                    "command": step.command,
                    "explanation": step.explanation,
                    "error": str(e),
                    "success": False
                })
                
                # Stop execution on error
                break
        
        return results
    

    #######################
    # Advanced Planning Methods
    #######################
    
    async def _generate_advanced_plan(
        self, 
        goal: str, 
        context: Dict[str, Any]
    ) -> AdvancedTaskPlan:
        """
        Generate an advanced plan using the AI service.
        
        Args:
            goal: The high-level goal
            context: Context information
            
        Returns:
            An AdvancedTaskPlan with steps to achieve the goal
        """
        # Build a planning prompt for advanced planning
        prompt = self._build_advanced_planning_prompt(goal, context)
        
        # Call the AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000
        )
        
        self._logger.debug("Sending advanced planning request to AI service")
        api_response = await gemini_client.generate_text(api_request)
        
        # Parse the plan from the response
        plan = self._parse_advanced_plan_response(api_response.text, goal, context)
        
        return plan
    
    def _build_advanced_planning_prompt(
        self, 
        goal: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Build a prompt for generating an advanced plan.
        
        Args:
            goal: The high-level goal
            context: Context information
            
        Returns:
            A prompt string for the AI service
        """
        # Create context string
        context_str = "Current context:\n"
        
        if context.get("cwd"):
            context_str += f"- Current working directory: {context['cwd']}\n"
        if context.get("project_root"):
            context_str += f"- Project root: {context['project_root']}\n"
        if context.get("project_type"):
            context_str += f"- Project type: {context['project_type']}\n"
        
        # Add files in current directory for context
        if context.get("cwd"):
            try:
                dir_contents = context_manager.get_directory_contents(Path(context["cwd"]))
                files_str = "\n".join([f"- {item['name']}" for item in dir_contents])
                context_str += f"\nFiles in current directory:\n{files_str}\n"
            except Exception as e:
                self._logger.error(f"Error getting directory contents: {str(e)}")
        
        # Build the prompt
        prompt = f"""
You are Angela, an AI terminal assistant with advanced planning capabilities. Your task is to create a detailed, sophisticated plan for achieving the following complex goal:

GOAL: {goal}

{context_str}

This is a complex goal that may require branching, conditions, loops, or other advanced constructs.

Break down this goal into a comprehensive plan with these advanced features:
1. Different types of steps (commands, code, file operations, API calls, decisions, loops)
2. Branching execution paths based on conditions
3. Dependencies between steps
4. Error recovery strategies
5. Risk assessment for each step

Format your response as JSON:
{{
  "id": "generate a unique plan ID",
  "goal": "the original goal",
  "description": "detailed plan description",
  "steps": {{
    "step1": {{
      "id": "step1",
      "type": "command",
      "description": "Description of step 1",
      "command": "command to execute",
      "dependencies": [],
      "estimated_risk": 1
    }},
    "step2": {{
      "id": "step2",
      "type": "file",
      "description": "Create a file",
      "file_path": "/path/to/file",
      "file_content": "content to write",
      "dependencies": ["step1"],
      "estimated_risk": 2
    }},
    "step3": {{
      "id": "step3",
      "type": "decision",
      "description": "Check if a condition is met",
      "condition": "test condition",
      "true_branch": ["step4a"],
      "false_branch": ["step4b"],
      "dependencies": ["step2"],
      "estimated_risk": 0
    }},
    "step4a": {{
      "id": "step4a",
      "type": "command",
      "description": "Executed if condition is true",
      "command": "command to execute",
      "dependencies": ["step3"],
      "estimated_risk": 1
    }},
    "step4b": {{
      "id": "step4b",
      "type": "command",
      "description": "Executed if condition is false",
      "command": "command to execute",
      "dependencies": ["step3"],
      "estimated_risk": 1
    }},
    "step5": {{
      "id": "step5",
      "type": "loop",
      "description": "Process each item",
      "loop_items": "items to process",
      "loop_body": ["step6"],
      "dependencies": ["step4a", "step4b"],
      "estimated_risk": 2
    }},
    "step6": {{
      "id": "step6",
      "type": "code",
      "description": "Execute some code",
      "code": "code to execute",
      "dependencies": [],
      "estimated_risk": 1
    }}
  }},
  "entry_points": ["step1"]
}}

Ensure each step has a unique ID and clear dependencies. Entry points are the steps that should be executed first.
"""
        
        return prompt
    
    def _parse_advanced_plan_response(
        self, 
        response: str, 
        goal: str, 
        context: Dict[str, Any]
    ) -> AdvancedTaskPlan:
        """
        Parse the AI response into an AdvancedTaskPlan.
        
        Args:
            response: The AI response text
            goal: The original high-level goal
            context: Context information
            
        Returns:
            An AdvancedTaskPlan object
        """
        try:
            # Extract JSON from the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Assume the entire response is JSON
                    json_str = response
            
            # Parse the JSON
            plan_data = json.loads(json_str)
            
            # Create an AdvancedTaskPlan object
            return AdvancedTaskPlan(
                id=plan_data.get("id", f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                goal=goal,
                description=plan_data.get("description", "Advanced plan for " + goal),
                steps=plan_data["steps"],
                entry_points=plan_data.get("entry_points", [next(iter(plan_data["steps"].keys()))]),
                context=context,
                created=datetime.now()
            )
        
        except Exception as e:
            self._logger.exception(f"Error parsing advanced plan response: {str(e)}")
            # Create a fallback plan
            fallback_step_id = "fallback_step"
            return AdvancedTaskPlan(
                id=f"fallback_plan_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                goal=goal,
                description=f"Fallback plan for: {goal}",
                steps={
                    fallback_step_id: AdvancedPlanStep(
                        id=fallback_step_id,
                        type=PlanStepType.COMMAND,
                        description="Fallback step due to planning error",
                        command=f"echo 'Unable to create detailed plan for: {goal}'",
                        dependencies=[],
                        estimated_risk=0
                    )
                },
                entry_points=[fallback_step_id],
                context=context
            )
    
    async def _execute_advanced_plan(
        self, 
        plan: AdvancedTaskPlan, 
        dry_run: bool = False,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an advanced task plan with transaction support.
        
        Args:
            plan: The plan to execute
            dry_run: Whether to simulate execution without making changes
            transaction_id: ID of the transaction this execution belongs to
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing advanced plan: {plan.goal}")
        
        # Initialize execution state
        results = {}
        completed_steps = set()
        pending_steps = {}
        
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
            for step_id, step in executable_steps.items():
                self._logger.info(f"Executing step {step_id}: {step.command}")
                
                try:
                    # Handle different step types
                    if step.type == "command":
                        # Execute shell command
                        result = await execution_engine.execute_command(
                            command=step.command,
                            check_safety=True,
                            dry_run=dry_run
                        )
                        
                        # Record command execution in the transaction if successful
                        if not dry_run and transaction_id and result[2] == 0:  # return_code == 0
                            # Import here to avoid circular imports
                            from angela.execution.rollback import rollback_manager
                            
                            await rollback_manager.record_command_execution(
                                command=step.command,
                                return_code=result[2],
                                stdout=result[0],
                                stderr=result[1],
                                transaction_id=transaction_id,
                                step_id=step_id
                            )
                        
                        # Format the result
                        execution_result = {
                            "step_id": step_id,
                            "type": step.type,
                            "command": step.command,
                            "description": step.description,
                            "stdout": result[0],
                            "stderr": result[1],
                            "return_code": result[2],
                            "success": result[2] == 0
                        }
                        
                    else:
                        # Unsupported step type, mark as failure
                        execution_result = {
                            "step_id": step_id,
                            "type": step.type,
                            "description": step.description,
                            "error": f"Unsupported step type: {step.type}",
                            "success": False
                        }
                    
                    results[step_id] = execution_result
                    
                    # Mark step as completed if successful, otherwise the plan failed
                    if execution_result["success"]:
                        completed_steps.add(step_id)
                    else:
                        self._logger.warning(f"Step {step_id} failed")
                        return {
                            "success": False,
                            "steps_completed": len(completed_steps),
                            "steps_total": len(plan.steps),
                            "failed_step": step_id,
                            "results": results
                        }
                        
                except Exception as e:
                    self._logger.exception(f"Error executing step {step_id}: {str(e)}")
                    
                    # Record the error
                    results[step_id] = {
                        "step_id": step_id,
                        "type": step.type,
                        "description": step.description,
                        "error": str(e),
                        "success": False
                    }
                    
                    # Plan failed
                    return {
                        "success": False,
                        "steps_completed": len(completed_steps),
                        "steps_total": len(plan.steps),
                        "failed_step": step_id,
                        "results": results
                    }
                
                # Remove from pending steps
                del pending_steps[step_id]
        
        # Check if all steps were completed
        all_completed = len(completed_steps) == len(plan.steps)
        
        return {
            "success": all_completed,
            "steps_completed": len(completed_steps),
            "steps_total": len(plan.steps),
            "results": results
        }
    
    
    def _select_next_step(
        self, 
        plan: AdvancedTaskPlan,
        pending_steps: Set[str],
        executed_steps: Set[str]
    ) -> Optional[str]:
        """
        Select the next step to execute in an advanced plan.
        
        Args:
            plan: The plan
            pending_steps: Set of pending step IDs
            executed_steps: Set of executed step IDs
            
        Returns:
            ID of the next step to execute, or None if no steps are ready
        """
        for step_id in pending_steps:
            step = plan.steps[step_id]
            
            # Check if all dependencies are satisfied
            if all(dep in executed_steps for dep in step.dependencies):
                return step_id
        
        return None
    
    async def _execute_step(
        self, 
        step: AdvancedPlanStep,
        previous_results: Dict[str, Dict[str, Any]],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute a single step of the advanced plan.
        
        Args:
            step: The step to execute
            previous_results: Results of previously executed steps
            dry_run: Whether to simulate execution
            
        Returns:
            Dictionary with step execution results
        """
        # Import here to avoid circular imports
        from angela.execution.engine import execution_engine
        
        # Prepare base result
        result = {
            "step_id": step.id,
            "type": step.type,
            "description": step.description,
            "dry_run": dry_run
        }
        
        try:
            # Execute based on step type
            if step.type == PlanStepType.COMMAND:
                if step.command:
                    if dry_run:
                        # Simulate command execution
                        result["stdout"] = f"[DRY RUN] Would execute: {step.command}"
                        result["stderr"] = ""
                        result["return_code"] = 0
                        result["success"] = True
                    else:
                        # Execute the command
                        stdout, stderr, return_code = await execution_engine.execute_command(
                            step.command,
                            check_safety=True
                        )
                        result["stdout"] = stdout
                        result["stderr"] = stderr
                        result["return_code"] = return_code
                        result["success"] = return_code == 0
                else:
                    result["error"] = "Missing command for command step"
                    result["success"] = False
            
            elif step.type == PlanStepType.FILE:
                if step.file_path:
                    if dry_run:
                        # Simulate file operation
                        operation = "write" if step.file_content else "read"
                        result["message"] = f"[DRY RUN] Would {operation} file: {step.file_path}"
                        result["success"] = True
                    else:
                        # Execute file operation
                        if step.file_content:
                            # Write to file
                            await self._write_file(step.file_path, step.file_content)
                            result["message"] = f"Wrote content to {step.file_path}"
                            result["success"] = True
                        else:
                            # Read from file
                            content = await self._read_file(step.file_path)
                            result["content"] = content
                            result["success"] = True
                else:
                    result["error"] = "Missing file path for file step"
                    result["success"] = False
            
            elif step.type == PlanStepType.CODE:
                if step.code:
                    if dry_run:
                        # Simulate code execution
                        result["message"] = f"[DRY RUN] Would execute code: {len(step.code)} characters"
                        result["success"] = True
                    else:
                        # Execute the code
                        # This is a simplified implementation - in a real system,
                        # this would use a sandboxed execution environment
                        code_result = await self._execute_code(step.code)
                        result.update(code_result)
                else:
                    result["error"] = "Missing code for code step"
                    result["success"] = False
            
            elif step.type == PlanStepType.DECISION:
                if step.condition:
                    # Evaluate the condition
                    # This is a simplified implementation - in a real system,
                    # this would use a more sophisticated condition evaluation
                    condition_result = await self._evaluate_condition(
                        step.condition, previous_results, dry_run
                    )
                    result["condition"] = step.condition
                    result["condition_result"] = condition_result
                    result["next_branch"] = "true_branch" if condition_result else "false_branch"
                    result["success"] = True
                else:
                    result["error"] = "Missing condition for decision step"
                    result["success"] = False
            
            elif step.type == PlanStepType.API:
                if step.api_url and step.api_method:
                    if dry_run:
                        # Simulate API call
                        result["message"] = f"[DRY RUN] Would call API: {step.api_method} {step.api_url}"
                        result["success"] = True
                    else:
                        # Execute API call
                        api_result = await self._execute_api_call(
                            step.api_url, step.api_method, step.api_payload
                        )
                        result.update(api_result)
                else:
                    result["error"] = "Missing URL or method for API step"
                    result["success"] = False
            
            elif step.type == PlanStepType.LOOP:
                if step.loop_items and step.loop_body:
                    if dry_run:
                        # Simulate loop execution
                        result["message"] = f"[DRY RUN] Would loop over {step.loop_items}"
                        result["success"] = True
                    else:
                        # This is a placeholder for loop execution
                        # In a real system, this would execute the loop body for each item
                        result["message"] = f"Loop execution not implemented: {step.loop_items}"
                        result["success"] = True
                else:
                    result["error"] = "Missing items or body for loop step"
                    result["success"] = False
            
            else:
                result["error"] = f"Unknown step type: {step.type}"
                result["success"] = False
            
        except Exception as e:
            self._logger.exception(f"Error executing step {step.id}: {str(e)}")
            result["error"] = str(e)
            result["success"] = False
            
            # Handle retry if configured
            if step.retry and step.retry > 0:
                result["retry_count"] = 1
                result["retried"] = True
                
                # Attempt retries (simplified)
                for retry_num in range(1, step.retry + 1):
                    self._logger.info(f"Retrying step {step.id} (attempt {retry_num}/{step.retry})")
                    try:
                        # Wait before retrying
                        await asyncio.sleep(1)
                        
                        # Execute retry logic based on step type
                        # This is a simplified implementation
                        retry_result = await self._execute_step(step, previous_results, dry_run)
                        
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
    
    def _update_pending_steps(
        self, 
        plan: AdvancedTaskPlan,
        executed_step: AdvancedPlanStep,
        result: Dict[str, Any],
        pending_steps: Set[str],
        executed_steps: Set[str]
    ) -> None:
        """
        Update the set of pending steps based on execution result.
        
        Args:
            plan: The plan
            executed_step: The step that was just executed
            result: The execution result
            pending_steps: Set of pending step IDs to update
            executed_steps: Set of executed step IDs
        """
        # For decision steps, add the appropriate branch
        if executed_step.type == PlanStepType.DECISION:
            condition_result = result.get("condition_result", False)
            if condition_result and executed_step.true_branch:
                # Add steps from true branch
                for step_id in executed_step.true_branch:
                    if step_id not in executed_steps and step_id in plan.steps:
                        pending_steps.add(step_id)
            elif not condition_result and executed_step.false_branch:
                # Add steps from false branch
                for step_id in executed_step.false_branch:
                    if step_id not in executed_steps and step_id in plan.steps:
                        pending_steps.add(step_id)
        
        # For normal steps, add all steps that depend on this one
        for step_id, step in plan.steps.items():
            if executed_step.id in step.dependencies and step_id not in executed_steps:
                # Check if all dependencies are satisfied
                if all(dep in executed_steps for dep in step.dependencies):
                    pending_steps.add(step_id)
    
    async def _read_file(self, path: str) -> str:
        """Read content from a file."""
        from angela.execution.filesystem import read_file
        return await read_file(path)
    
    async def _write_file(self, path: str, content: str) -> bool:
        """Write content to a file."""
        from angela.execution.filesystem import write_file
        return await write_file(path, content)
    
    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """
        Execute code (placeholder implementation).
        
        In a real system, this would use a sandboxed execution environment.
        """
        return {
            "message": f"Code execution not implemented: {len(code)} characters",
            "success": True
        }
    
    async def _evaluate_condition(
        self, 
        condition: str,
        previous_results: Dict[str, Dict[str, Any]],
        dry_run: bool
    ) -> bool:
        """
        Evaluate a condition (placeholder implementation).
        
        In a real system, this would use a more sophisticated condition evaluation.
        """
        import re
        
        # Look for simple patterns
        if re.search(r'file exists', condition, re.IGNORECASE):
            # Extract file path
            match = re.search(r'file exists[:\s]+([^\s]+)', condition, re.IGNORECASE)
            if match:
                file_path = match.group(1)
                return Path(file_path).exists()
        
        if re.search(r'command success', condition, re.IGNORECASE):
            # Extract step ID
            match = re.search(r'step[:\s]+([^\s]+)', condition, re.IGNORECASE)
            if match:
                step_id = match.group(1)
                return previous_results.get(step_id, {}).get("success", False)
        
        # Default behavior for dry run
        if dry_run:
            return True
        
        # Default for unknown conditions
        return False
    
    async def _execute_api_call(
        self, 
        url: str,
        method: str,
        payload: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute an API call (placeholder implementation).
        
        In a real system, this would use a proper HTTP client.
        """
        return {
            "message": f"API call not implemented: {method} {url}",
            "success": True
        }


# Global instance
task_planner = TaskPlanner()
