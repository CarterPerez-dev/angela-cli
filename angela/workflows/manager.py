"""
Workflow management for Angela CLI.

This module handles user-defined workflows - reusable sequences
of commands that can be invoked by name.
"""
import os
import json
import shlex
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

from pydantic import BaseModel, Field

from angela.config import config_manager
from angela.intent.planner import TaskPlan, PlanStep
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# File for storing workflows
WORKFLOWS_FILE = config_manager.CONFIG_DIR / "workflows.json"

class WorkflowStep(BaseModel):
    """Model for a step in a workflow."""
    command: str = Field(..., description="The command to execute")
    explanation: str = Field(..., description="Explanation of what the command does")
    optional: bool = Field(False, description="Whether this step is optional")
    requires_confirmation: bool = Field(False, description="Whether this step requires explicit confirmation")


class Workflow(BaseModel):
    """Model for a user-defined workflow."""
    name: str = Field(..., description="Unique name for the workflow")
    description: str = Field(..., description="Human-readable description")
    steps: List[WorkflowStep] = Field(..., description="Steps in the workflow")
    variables: Dict[str, str] = Field(default_factory=dict, description="Variable placeholders")
    created: datetime = Field(default_factory=datetime.now, description="When the workflow was created")
    modified: datetime = Field(default_factory=datetime.now, description="When the workflow was last modified")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing workflows")
    author: Optional[str] = Field(None, description="Author of the workflow")


class WorkflowManager:
    """
    Manager for user-defined workflows.
    
    This class handles:
    1. Defining new workflows from natural language descriptions
    2. Storing and retrieving workflows
    3. Executing workflows with parameter substitution
    4. Listing and searching available workflows
    """
    
    def __init__(self):
        """Initialize the workflow manager."""
        self._workflows: Dict[str, Workflow] = {}
        self._workflow_file = WORKFLOWS_FILE
        self._logger = logger
        self._load_workflows()
    
    def _load_workflows(self) -> None:
        """Load workflows from the storage file."""
        try:
            if self._workflow_file.exists():
                with open(self._workflow_file, "r") as f:
                    data = json.load(f)
                    
                for workflow_data in data:
                    try:
                        # Handle datetime serialization
                        if "created" in workflow_data:
                            workflow_data["created"] = datetime.fromisoformat(workflow_data["created"])
                        if "modified" in workflow_data:
                            workflow_data["modified"] = datetime.fromisoformat(workflow_data["modified"])
                            
                        workflow = Workflow(**workflow_data)
                        self._workflows[workflow.name] = workflow
                    except Exception as e:
                        self._logger.error(f"Error loading workflow: {str(e)}")
                
                self._logger.info(f"Loaded {len(self._workflows)} workflows")
            else:
                self._logger.info("No workflows file found, starting with empty workflows")
                self._save_workflows()  # Create the file
        except Exception as e:
            self._logger.error(f"Error loading workflows: {str(e)}")
    
    def _save_workflows(self) -> None:
        """Save workflows to the storage file."""
        try:
            # Ensure the directory exists
            self._workflow_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert workflows to serializable dict
            data = []
            for workflow in self._workflows.values():
                workflow_dict = workflow.dict()
                # Handle datetime serialization
                workflow_dict["created"] = workflow_dict["created"].isoformat()
                workflow_dict["modified"] = workflow_dict["modified"].isoformat()
                data.append(workflow_dict)
            
            # Write to file
            with open(self._workflow_file, "w") as f:
                json.dump(data, f, indent=2)
                
            self._logger.info(f"Saved {len(self._workflows)} workflows")
        except Exception as e:
            self._logger.error(f"Error saving workflows: {str(e)}")
    
    async def define_workflow(
        self, 
        name: str, 
        description: str, 
        steps: List[Dict[str, Any]],
        variables: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> Workflow:
        """
        Define a new workflow or update an existing one.
        
        Args:
            name: Unique name for the workflow
            description: Human-readable description
            steps: List of step dictionaries with commands and explanations
            variables: Optional variable placeholders
            tags: Optional tags for categorization
            author: Optional author name
            
        Returns:
            The created or updated Workflow
        """
        # Convert steps to WorkflowStep objects
        workflow_steps = []
        for step_data in steps:
            workflow_step = WorkflowStep(
                command=step_data["command"],
                explanation=step_data.get("explanation", ""),
                optional=step_data.get("optional", False),
                requires_confirmation=step_data.get("requires_confirmation", False)
            )
            workflow_steps.append(workflow_step)
        
        # Check if workflow already exists
        if name in self._workflows:
            # Update existing workflow
            workflow = self._workflows[name]
            workflow.description = description
            workflow.steps = workflow_steps
            workflow.variables = variables or {}
            workflow.modified = datetime.now()
            if tags:
                workflow.tags = tags
            if author:
                workflow.author = author
                
            self._logger.info(f"Updated workflow: {name}")
        else:
            # Create new workflow
            workflow = Workflow(
                name=name,
                description=description,
                steps=workflow_steps,
                variables=variables or {},
                tags=tags or [],
                author=author
            )
            self._workflows[name] = workflow
            self._logger.info(f"Created new workflow: {name}")
        
        # Save updated workflows
        self._save_workflows()
        
        return workflow
    
    async def define_workflow_from_natural_language(
        self, 
        name: str, 
        description: str, 
        natural_language: str,
        context: Dict[str, Any]
    ) -> Workflow:
        """
        Define a workflow from a natural language description.
        
        Args:
            name: Unique name for the workflow
            description: Human-readable description
            natural_language: Natural language description of the workflow steps
            context: Context information
            
        Returns:
            The created Workflow
        """
        # Import here to avoid circular imports
        from angela.intent.planner import task_planner
        from angela.ai.client import gemini_client, GeminiRequest
        
        self._logger.info(f"Creating workflow from natural language: {name}")
        
        # Generate a plan using the task planner
        try:
            plan = await task_planner.plan_task(natural_language, context)
            
            # Convert plan steps to workflow steps
            steps = []
            for plan_step in plan.steps:
                step = {
                    "command": plan_step.command,
                    "explanation": plan_step.explanation,
                    "optional": False,
                    "requires_confirmation": plan_step.estimated_risk >= 3  # High or Critical risk
                }
                steps.append(step)
                
            # Identify potential variables
            variables = await self._identify_variables(steps, natural_language)
            
            # Create the workflow
            workflow = await self.define_workflow(
                name=name,
                description=description,
                steps=steps,
                variables=variables,
                tags=["user-defined"]
            )
            
            return workflow
            
        except Exception as e:
            self._logger.exception(f"Error creating workflow from natural language: {str(e)}")
            # Create a placeholder workflow
            placeholder_workflow = await self.define_workflow(
                name=name,
                description=description,
                steps=[{
                    "command": f"echo 'Error creating workflow: {str(e)}'",
                    "explanation": "This is a placeholder for a workflow that could not be created",
                    "optional": False,
                    "requires_confirmation": False
                }],
                tags=["error", "placeholder"]
            )
            return placeholder_workflow
    
    async def _identify_variables(
        self, 
        steps: List[Dict[str, Any]], 
        natural_language: str
    ) -> Dict[str, str]:
        """
        Identify potential variables in workflow steps.
        
        Args:
            steps: The workflow steps
            natural_language: Original natural language description
            
        Returns:
            Dictionary of variable names and descriptions
        """
        # Extract all commands
        commands = [step["command"] for step in steps]
        
        # Build prompt for variable identification
        prompt = f"""
Identify potential variables in the following workflow commands:

Commands:
{json.dumps(commands, indent=2)}

Original description:
{natural_language}

Identify parameters or values that might change each time the workflow is run.
For each variable, provide:
1. A variable name (use format like $NAME or {{NAME}})
2. A description of what the variable represents

Format your response as JSON:
{{
  "variables": {{
    "$VARIABLE1": "Description of variable 1",
    "$VARIABLE2": "Description of variable 2",
    ...
  }}
}}
"""
        
        # Call AI service
        from angela.ai.client import gemini_client, GeminiRequest
        
        api_request = GeminiRequest(prompt=prompt, max_tokens=2000)
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        try:
            # Extract JSON from the response
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Fallback to entire response
                json_str = response.text
                
            # Parse JSON
            result = json.loads(json_str)
            variables = result.get("variables", {})
            
            self._logger.info(f"Identified {len(variables)} variables")
            return variables
            
        except Exception as e:
            self._logger.error(f"Error identifying variables: {str(e)}")
            return {}
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """
        Get a workflow by name.
        
        Args:
            name: Name of the workflow to retrieve
            
        Returns:
            The Workflow if found, None otherwise
        """
        return self._workflows.get(name)
    
    def list_workflows(self, tag: Optional[str] = None) -> List[Workflow]:
        """
        List all workflows, optionally filtered by tag.
        
        Args:
            tag: Optional tag to filter workflows
            
        Returns:
            List of matching Workflows
        """
        if tag:
            return [w for w in self._workflows.values() if tag in w.tags]
        else:
            return list(self._workflows.values())
    
    def search_workflows(self, query: str) -> List[Workflow]:
        """
        Search for workflows by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching Workflows
        """
        query_lower = query.lower()
        results = []
        
        for workflow in self._workflows.values():
            # Check name, description, and tags
            if (query_lower in workflow.name.lower() or 
                query_lower in workflow.description.lower() or
                any(query_lower in tag.lower() for tag in workflow.tags)):
                results.append(workflow)
                
        return results
    
    def delete_workflow(self, name: str) -> bool:
        """
        Delete a workflow by name.
        
        Args:
            name: Name of the workflow to delete
            
        Returns:
            True if deleted, False if not found
        """
        if name in self._workflows:
            del self._workflows[name]
            self._save_workflows()
            self._logger.info(f"Deleted workflow: {name}")
            return True
        
        return False
    
    async def execute_workflow(
        self, 
        workflow_name: str, 
        variables: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a workflow with variable substitution.
        
        Args:
            workflow_name: Name of the workflow to execute
            variables: Variable values for substitution
            context: Context information
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with execution results
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_name}"
            }
        
        # Import here to avoid circular imports
        from angela.intent.planner import TaskPlan, PlanStep, task_planner
        
        # Convert workflow to a task plan
        plan_steps = []
        for i, step in enumerate(workflow.steps):
            # Apply variable substitution
            command = self._substitute_variables(step.command, variables)
            
            plan_step = PlanStep(
                command=command,
                explanation=step.explanation,
                dependencies=[i-1] if i > 0 else [],  # Simple linear dependencies
                estimated_risk=3 if step.requires_confirmation else 1  # Default risk levels
            )
            plan_steps.append(plan_step)
            
        plan = TaskPlan(
            goal=f"Execute workflow: {workflow.name}",
            steps=plan_steps,
            context=context
        )
        
        # Execute the plan
        results = await task_planner.execute_plan(plan, dry_run=dry_run)
        
        return {
            "workflow": workflow.name,
            "description": workflow.description,
            "steps": len(workflow.steps),
            "results": results,
            "success": all(result.get("success", False) for result in results),
            "dry_run": dry_run
        }
    
    def _substitute_variables(self, command: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in a command.
        
        Args:
            command: The command template
            variables: Variable values for substitution
            
        Returns:
            Command with variables substituted
        """
        result = command
        
        # Handle ${VAR} and $VAR syntax
        for var_name, var_value in variables.items():
            # Remove leading $ if present
            clean_name = var_name[1:] if var_name.startswith('$') else var_name
            
            # Substitute ${VAR} syntax
            result = result.replace(f"${{{clean_name}}}", str(var_value))
            
            # Substitute $VAR syntax
            result = result.replace(f"${clean_name}", str(var_value))
        
        return result


# Global workflow manager instance
workflow_manager = WorkflowManager()
