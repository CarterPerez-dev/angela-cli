"""
Task planning and goal decomposition for Angela CLI.

This module handles breaking down complex high-level goals into
executable action plans with dependencies and execution flow.
"""
import re
import shlex
from typing import Dict, Any, List, Tuple, Optional, Set
from pathlib import Path

from pydantic import BaseModel, Field

from angela.intent.models import ActionPlan, Intent, IntentType
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class PlanStep(BaseModel):
    """Model for a single step in a plan."""
    command: str = Field(..., description="The command to execute")
    explanation: str = Field(..., description="Explanation of the command")
    dependencies: List[int] = Field(default_factory=list, description="Indices of steps this step depends on")
    estimated_risk: int = Field(0, description="Estimated risk level (0-4)")


class TaskPlan(BaseModel):
    """Model for a complete task plan."""
    goal: str = Field(..., description="The original high-level goal")
    steps: List[PlanStep] = Field(..., description="Steps to achieve the goal")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")


class TaskPlanner:
    """
    Task planner for breaking down complex goals into actionable steps.
    
    This class handles:
    1. Analyzing high-level goals
    2. Breaking them down into sequences of commands
    3. Determining dependencies between steps
    4. Generating executable action plans
    """
    
    def __init__(self):
        """Initialize the task planner."""
        self._logger = logger
    
    async def plan_task(self, goal: str, context: Dict[str, Any]) -> TaskPlan:
        """
        Plan a complex task by breaking it down into actionable steps.
        
        Args:
            goal: The high-level goal description
            context: Context information
            
        Returns:
            A TaskPlan with the steps to achieve the goal
        """
        self._logger.info(f"Planning task: {goal}")
        
        # Generate a plan using the AI
        plan = await self._generate_plan(goal, context)
        
        self._logger.info(f"Generated plan with {len(plan.steps)} steps")
        return plan
    
    async def _generate_plan(self, goal: str, context: Dict[str, Any]) -> TaskPlan:
        """
        Generate a plan using the AI service.
        
        Args:
            goal: The high-level goal
            context: Context information
            
        Returns:
            A TaskPlan with steps to achieve the goal
        """
        # Build a planning prompt
        prompt = self._build_planning_prompt(goal, context)
        
        # Call the AI service
        api_request = GeminiRequest(prompt=prompt)
        api_response = await gemini_client.generate_text(api_request)
        
        # Parse the plan from the response
        plan = self._parse_plan_response(api_response.text, goal, context)
        
        return plan
    
    def _build_planning_prompt(self, goal: str, context: Dict[str, Any]) -> str:
        """
        Build a prompt for generating a plan.
        
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
        Parse the AI response into a TaskPlan.
        
        Args:
            response: The AI response text
            goal: The original high-level goal
            context: Context information
            
        Returns:
            A TaskPlan object
        """
        try:
            # Extract JSON from the response
            import json
            import re
            
            # Find JSON content
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
    
    async def execute_plan(self, task_plan: TaskPlan, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute a task plan.
        
        Args:
            task_plan: The task plan to execute
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            A list of execution results for each step
        """
        # Convert to action plan
        action_plan = self.create_action_plan(task_plan)
        
        # Import here to avoid circular imports
        from angela.execution.engine import execution_engine
        
        # Execute the plan
        results = await execution_engine.execute_plan(
            action_plan,
            check_safety=True,
            dry_run=dry_run
        )
        
        return results


# Global task planner instance
task_planner = TaskPlanner()
