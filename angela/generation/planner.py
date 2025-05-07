# angela/generation/planner.py
"""
Project structure planning for Angela CLI.

This module is responsible for planning the structure of a new project,
identifying necessary files, their roles, and interdependencies.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re

from pydantic import BaseModel, Field

from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.generation.engine import CodeProject, CodeFile

logger = get_logger(__name__)

class ArchitectureComponent(BaseModel):
    """Model for a component in the project architecture."""
    name: str = Field(..., description="Name of the component")
    description: str = Field(..., description="Description of the component")
    responsibilities: List[str] = Field(..., description="Responsibilities of the component")
    files: List[str] = Field(default_factory=list, description="Files implementing this component")
    dependencies: List[str] = Field(default_factory=list, description="Components this depends on")

class ProjectArchitecture(BaseModel):
    """Model for a project's architecture."""
    components: List[ArchitectureComponent] = Field(..., description="Components in the architecture")
    layers: List[str] = Field(default_factory=list, description="Architectural layers")
    patterns: List[str] = Field(default_factory=list, description="Design patterns used")
    data_flow: List[str] = Field(default_factory=list, description="Data flow descriptions")

class ProjectPlanner:
    """
    Project planner for designing and organizing code projects.
    """
    
    def __init__(self):
        """Initialize the project planner."""
        self._logger = logger
    
    async def create_project_architecture(
        self, 
        description: str,
        project_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProjectArchitecture:
        """
        Create a high-level architecture for a project.
        
        Args:
            description: Natural language description of the project
            project_type: Type of project to generate
            context: Additional context information
            
        Returns:
            ProjectArchitecture object
        """
        self._logger.info(f"Creating project architecture for: {description}")
        
        # Get context if not provided
        if context is None:
            context = context_manager.get_context_dict()
        
        # Build prompt for architecture planning
        prompt = self._build_architecture_prompt(description, project_type, context)
        
        # Call AI service to generate architecture
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        self._logger.debug("Sending architecture planning request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response to extract the architecture
        architecture = await self._parse_architecture(response.text)
        
        return architecture
    
    async def refine_project_plan(
        self, 
        project: CodeProject,
        architecture: ProjectArchitecture,
        context: Optional[Dict[str, Any]] = None
    ) -> CodeProject:
        """
        Refine a project plan based on architecture.
        
        Args:
            project: Initial CodeProject
            architecture: ProjectArchitecture to use for refinement
            context: Additional context information
            
        Returns:
            Refined CodeProject
        """
        self._logger.info(f"Refining project plan for: {project.name}")
        
        # Get context if not provided
        if context is None:
            context = context_manager.get_context_dict()
        
        # Build prompt for plan refinement
        prompt = self._build_plan_refinement_prompt(project, architecture, context)
        
        # Call AI service to refine plan
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        self._logger.debug("Sending plan refinement request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response to extract the refined plan
        refined_plan = await self._parse_refined_plan(response.text, project)
        
        return refined_plan
    
    def _build_architecture_prompt(
        self, 
        description: str,
        project_type: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Build a prompt for architecture planning.
        
        Args:
            description: Natural language description of the project
            project_type: Type of project to generate
            context: Additional context information
            
        Returns:
            Prompt string for the AI service
        """
        prompt = f"""
As an experienced software architect, design a high-level architecture for a {project_type} project based on this description:

"{description}"

Analyze the requirements and create a comprehensive architecture that is:
- Modular and maintainable
- Follows SOLID principles
- Anticipates future changes/extensions
- Accounts for scalability and performance

Your response should be a JSON object with this structure:

```json
{{
  "components": [
    {{
      "name": "component_name",
      "description": "what this component does",
      "responsibilities": ["resp1", "resp2", ...],
      "files": ["expected/path/to/file.ext", ...],
      "dependencies": ["other_component_names", ...]
    }},
    ...
  ],
  "layers": ["Layer1", "Layer2", ...],
  "patterns": ["Design patterns used in the architecture"],
  "data_flow": ["Descriptions of data flow between components"]
}}
Focus on a clean separation of concerns, appropriate design patterns for {project_type}, and efficient data flow.
"""
    return prompt

async def _parse_architecture(self, response: str) -> ProjectArchitecture:
    """
    Parse the AI response to extract the architecture.
    
    Args:
        response: AI response text
        
    Returns:
        ProjectArchitecture object
    """
    try:
        # Look for JSON block in the response
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
        arch_data = json.loads(json_str)
        
        # Create ArchitectureComponent objects
        components = []
        for comp_data in arch_data.get("components", []):
            components.append(ArchitectureComponent(
                name=comp_data["name"],
                description=comp_data["description"],
                responsibilities=comp_data.get("responsibilities", []),
                files=comp_data.get("files", []),
                dependencies=comp_data.get("dependencies", [])
            ))
        
        # Create ProjectArchitecture object
        architecture = ProjectArchitecture(
            components=components,
            layers=arch_data.get("layers", []),
            patterns=arch_data.get("patterns", []),
            data_flow=arch_data.get("data_flow", [])
        )
        
        return architecture
        
    except Exception as e:
        self._logger.exception(f"Error parsing architecture: {str(e)}")
        
        # Create a minimal fallback architecture
        fallback_component = ArchitectureComponent(
            name="Core",
            description="Core application functionality",
            responsibilities=["Main application logic"],
            files=[],
            dependencies=[]
        )
        
        return ProjectArchitecture(
            components=[fallback_component],
            layers=["Presentation", "Business Logic", "Data Access"],
            patterns=["MVC"],
            data_flow=["User input -> Core processing -> Storage"]
        )

def _build_plan_refinement_prompt(
    self, 
    project: CodeProject,
    architecture: ProjectArchitecture,
    context: Dict[str, Any]
) -> str:
    """
    Build a prompt for plan refinement.
    
    Args:
        project: Initial CodeProject
        architecture: ProjectArchitecture to use for refinement
        context: Additional context information
        
    Returns:
        Prompt string for the AI service
    """
    # Extract architecture info
    arch_json = {}
    arch_json["components"] = [comp.dict() for comp in architecture.components]
    arch_json["layers"] = architecture.layers
    arch_json["patterns"] = architecture.patterns
    arch_json["data_flow"] = architecture.data_flow
    
    # Extract project info
    project_json = {}
    project_json["name"] = project.name
    project_json["description"] = project.description
    project_json["project_type"] = project.project_type
    project_json["dependencies"] = project.dependencies
    project_json["files"] = [
        {
            "path": file.path,
            "purpose": file.purpose,
            "dependencies": file.dependencies
        }
        for file in project.files
    ]
    
    prompt = f"""
You are refining a project plan based on a high-level architecture.
Here is the current project plan:
json{json.dumps(project_json, indent=2)}
And here is the architecture design:
json{json.dumps(arch_json, indent=2)}
Your task is to refine the project plan to better align with the architecture.
This may involve:

1. Adding missing files that would be needed for components in the architecture
2. Updating existing file purposes to match component responsibilities
3. Adjusting file dependencies to match component dependencies
4. Ensuring the project structure follows the architectural layers

Return a refined project plan in this JSON format:
json{{
  "name": "project_name",
  "description": "project description",
  "project_type": "{project.project_type}",
  "dependencies": {{
    "runtime": ["dep1", "dep2"],
    "development": ["dev_dep1", "dev_dep2"]
  }},
  "files": [
    {{
      "path": "path/to/file.ext",
      "purpose": "file purpose",
      "dependencies": ["other/file/paths"],
      "component": "associated_component_name"
    }}
  ],
  "structure_explanation": "explanation of the refined structure"
}}
Make sure the refined plan implements all components and follows all architectural patterns in the design.
"""
    return prompt

async def _parse_refined_plan(
    self, 
    response: str, 
    original_project: CodeProject
) -> CodeProject:
    """
    Parse the AI response to extract the refined plan.
    
    Args:
        response: AI response text
        original_project: The original project to refine
        
    Returns:
        Refined CodeProject
    """
    try:
        # Look for JSON block in the response
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
        
        # Create CodeFile objects
        files = []
        for file_data in plan_data.get("files", []):
            # Check if this file existed in the original project
            original_file = next((f for f in original_project.files if f.path == file_data["path"]), None)
            
            files.append(CodeFile(
                path=file_data["path"],
                content=original_file.content if original_file else "",
                purpose=file_data["purpose"],
                dependencies=file_data.get("dependencies", []),
                language=original_file.language if original_file else None
            ))
        
        # Create CodeProject object
        project = CodeProject(
            name=plan_data.get("name", original_project.name),
            description=plan_data.get("description", original_project.description),
            root_dir=original_project.root_dir,
            files=files,
            dependencies=plan_data.get("dependencies", original_project.dependencies),
            project_type=original_project.project_type,
            structure_explanation=plan_data.get("structure_explanation", original_project.structure_explanation)
        )
        
        return project
        
    except Exception as e:
        self._logger.exception(f"Error parsing refined plan: {str(e)}")
        
        # Return the original project if parsing failed
        return original_project
        
        
project_planner = ProjectPlanner()
