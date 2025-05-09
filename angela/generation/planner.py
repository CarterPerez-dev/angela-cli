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


from angela.generation.context_manager import generation_context_manager
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.generation.engine import CodeProject, CodeFile

logger = get_logger(__name__)

class ComponentRelationship(BaseModel):
    """Model for relationships between architecture components."""
    source: str = Field(..., description="Source component")
    target: str = Field(..., description="Target component")
    type: str = Field(..., description="Type of relationship (e.g., 'uses', 'inherits', 'implements')")
    description: Optional[str] = Field(None, description="Optional description of the relationship")
    
    
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
    relationships: List[ComponentRelationship] = Field(default_factory=list, description="Relationships between components")
    structure_type: str = Field("layered", description="Type of architecture structure (e.g., 'layered', 'modular', 'microservices')")


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



    async def create_detailed_project_architecture(
        self, 
        description: str,
        project_type: str,
        framework: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ProjectArchitecture:
        """
        Create a detailed architecture for a project with component relationships.
        
        Args:
            description: Natural language description of the project
            project_type: Type of project to generate
            framework: Optional framework to use (e.g., 'react', 'django')
            context: Additional context information
            
        Returns:
            ProjectArchitecture object with detailed component relationships
        """
        self._logger.info(f"Creating detailed project architecture for: {description}")
        
        # Get context if not provided
        if context is None:
            context = context_manager.get_context_dict()
        
        # Determine appropriate architecture style based on project type and framework
        architecture_style = self._determine_architecture_style(project_type, framework)
        
        # Build enhanced prompt for architecture planning
        prompt = self._build_detailed_architecture_prompt(description, project_type, framework, architecture_style, context)
        
        # Call AI service to generate architecture
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,  # Increased token limit for more detailed planning
            temperature=0.2
        )
        
        self._logger.debug("Sending detailed architecture planning request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response to extract the architecture
        architecture = await self._parse_detailed_architecture(response.text, architecture_style)
        
        # Store in global context
        generation_context_manager.set_global_context("architecture", architecture.dict())
        generation_context_manager.set_global_context("project_type", project_type)
        if framework:
            generation_context_manager.set_global_context("framework", framework)
        
        return architecture
    
    def _determine_architecture_style(self, project_type: str, framework: Optional[str]) -> str:
        """
        Determine appropriate architecture style based on project type and framework.
        
        Args:
            project_type: Type of project
            framework: Optional framework name
            
        Returns:
            Architecture style string
        """
        # Default to layered architecture
        style = "layered"
        
        # Web application frameworks often use MVC or similar
        if framework in ["django", "flask", "spring", "rails", "laravel"]:
            style = "mvc"
        # Modern JavaScript frameworks often use component-based architecture
        elif framework in ["react", "vue", "angular"]:
            style = "component-based"
        # API-focused projects might use clean architecture
        elif "api" in project_type or project_type == "node" and not framework:
            style = "clean-architecture"
        # Microservices for larger distributed systems
        elif "microservice" in project_type:
            style = "microservices"
        
        return style
    
    def _build_detailed_architecture_prompt(
        self, 
        description: str,
        project_type: str,
        framework: Optional[str],
        architecture_style: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Build a detailed prompt for architecture planning.
        
        Args:
            description: Project description
            project_type: Type of project
            framework: Optional framework
            architecture_style: Architecture style
            context: Additional context
            
        Returns:
            Prompt string for the AI service
        """
        framework_str = f" using {framework}" if framework else ""
        
        prompt = f"""
As an expert software architect, design a detailed architecture for a {project_type}{framework_str} project based on this description:

"{description}"

I'm looking for a {architecture_style} style architecture that is:
- Modular and maintainable
- Follows SOLID principles
- Anticipates future changes/extensions
- Accounts for scalability and performance

In your design:
1. Follow best practices for {project_type}{framework_str} projects
2. Use patterns and conventions typical of {architecture_style} architectures
3. Include clear separation of concerns
4. Show relationships between components

Your response should be a JSON object with this structure:

```json
{{
  "components": [
    {{
      "name": "component_name",
      "description": "detailed description of this component",
      "responsibilities": ["resp1", "resp2", ...],
      "files": ["expected/path/to/file.ext", ...],
      "dependencies": ["other_component_names", ...]
    }},
    ...
  ],
  "layers": ["Layer1", "Layer2", ...],
  "patterns": ["Design patterns used in the architecture"],
  "data_flow": ["Descriptions of data flow between components"],
  "relationships": [
    {{
      "source": "component_name",
      "target": "other_component",
      "type": "relationship_type", 
      "description": "details about how they relate"
    }},
    ...
  ],
  "structure_type": "{architecture_style}"
}}
"""

        # Add specific guidance based on architecture style
        if architecture_style == "mvc":
            prompt += """
For MVC architecture, include these components:
- Models (data and business logic)
- Views (user interface elements)
- Controllers (handle requests and coordinate models and views)
- Routes/URL configuration
- Services (optional business logic layer)
- Data access/repositories (for database interactions)
"""
        elif architecture_style == "component-based":
            prompt += """
For component-based architecture, consider:
- UI Components (reusable interface elements)
- Container Components (manage state and data flow)
- Services (handle data fetching and processing)
- Stores/State Management (centralized state)
- Utilities/Helpers (reusable functions)
- API Integration (services for external communication)
"""
        elif architecture_style == "clean-architecture":
            prompt += """
For clean architecture, include these layers:
- Entities (core business objects)
- Use Cases/Interactors (application-specific business rules)
- Interface Adapters (controllers, presenters, gateways)
- Frameworks & Drivers (external interfaces, web, DB, UI)

Ensure the dependency rule is followed: outer layers can depend on inner layers, but inner layers cannot depend on outer layers.
"""
        elif architecture_style == "microservices":
            prompt += """
For microservices architecture, consider:
- Individual service components (each with its own responsibility)
- API Gateways
- Service Discovery
- Communication patterns between services
- Data management strategies (database per service or shared)
- Cross-cutting concerns (logging, monitoring, security)
"""
        
        return prompt
    
    async def _parse_detailed_architecture(
        self, 
        response: str,
        architecture_style: str
    ) -> ProjectArchitecture:
        """
        Parse the AI response to extract the detailed architecture.
        
        Args:
            response: AI response text
            architecture_style: The architecture style
            
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
            
            # Create ComponentRelationship objects
            relationships = []
            for rel_data in arch_data.get("relationships", []):
                relationships.append(ComponentRelationship(
                    source=rel_data["source"],
                    target=rel_data["target"],
                    type=rel_data["type"],
                    description=rel_data.get("description")
                ))
            
            # Create ProjectArchitecture object
            architecture = ProjectArchitecture(
                components=components,
                layers=arch_data.get("layers", []),
                patterns=arch_data.get("patterns", []),
                data_flow=arch_data.get("data_flow", []),
                relationships=relationships,
                structure_type=arch_data.get("structure_type", architecture_style)
            )
            
            return architecture
            
        except Exception as e:
            self._logger.exception(f"Error parsing detailed architecture: {str(e)}")
            
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
                data_flow=["User input -> Core processing -> Storage"],
                relationships=[],
                structure_type=architecture_style
            )
            
    async def generate_dependency_graph(self, architecture: ProjectArchitecture) -> Dict[str, Any]:
        """
        Generate a dependency graph from the architecture.
        
        Args:
            architecture: The project architecture
            
        Returns:
            Dictionary with nodes and edges for visualization
        """
        nodes = []
        edges = []
        
        # Create nodes for each component
        for component in architecture.components:
            nodes.append({
                "id": component.name,
                "label": component.name,
                "type": "component"
            })
            
            # Add edges for component dependencies
            for dependency in component.dependencies:
                edges.append({
                    "source": component.name,
                    "target": dependency,
                    "type": "depends_on"
                })
        
        # Add edges for explicit relationships
        for relationship in architecture.relationships:
            # Check if the edge already exists
            edge_exists = False
            for edge in edges:
                if edge["source"] == relationship.source and edge["target"] == relationship.target:
                    edge_exists = True
                    break
            
            if not edge_exists:
                edges.append({
                    "source": relationship.source,
                    "target": relationship.target,
                    "type": relationship.type
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
        
    async def create_project_plan_from_architecture(
        self, 
        architecture: ProjectArchitecture,
        project_name: str,
        project_type: str,
        description: str,
        framework: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> CodeProject:
        """
        Create a more detailed project plan based on architecture.
        
        Args:
            architecture: The project architecture
            project_name: Name of the project
            project_type: Type of project
            description: Project description
            framework: Optional framework
            context: Additional context
            
        Returns:
            CodeProject with detailed file structure
        """
        self._logger.info(f"Creating project plan from architecture for: {project_name}")
        
        # Get context if not provided
        if context is None:
            context = context_manager.get_context_dict()
            
        # Get root directory
        root_dir = context.get("cwd", ".")
        
        # Determine dependencies based on project type and framework
        dependencies = await self._determine_project_dependencies(project_type, framework, description)
        
        # Create files from architecture components
        files = []
        for component in architecture.components:
            component_files = await self._create_files_for_component(
                component, 
                project_type, 
                framework
            )
            files.extend(component_files)
        
        # Add standard project files
        standard_files = await self._add_standard_project_files(
            project_type, 
            framework, 
            project_name
        )
        files.extend(standard_files)
        
        # Create the project
        project = CodeProject(
            name=project_name,
            description=description,
            root_dir=root_dir,
            files=files,
            dependencies=dependencies,
            project_type=project_type,
            structure_explanation=f"Project follows {architecture.structure_type} architecture with {len(architecture.components)} components across {len(architecture.layers)} layers."
        )
        
        return project
    
    async def _determine_project_dependencies(
        self, 
        project_type: str, 
        framework: Optional[str],
        description: str
    ) -> Dict[str, List[str]]:
        """
        Determine project dependencies based on type and framework.
        
        Args:
            project_type: Type of project
            framework: Optional framework
            description: Project description
            
        Returns:
            Dictionary with runtime and development dependencies
        """
        # Build prompt for dependency determination
        prompt = f"""
As an expert software developer, determine the necessary dependencies for a {project_type} project{f' using {framework}' if framework else ''} based on this description:

"{description}"

Return a JSON object with runtime and development dependencies:
```json
{{
  "runtime": ["dep1", "dep2", ...],
  "development": ["dev_dep1", "dev_dep2", ...]
}}
Include only the necessary dependencies for the core functionality described.
Use the latest stable versions and follow best practices for {project_type} projects.
"""
    # Call AI service
    api_request = GeminiRequest(
        prompt=prompt,
        max_tokens=2000,
        temperature=0.2
    )
    
    self._logger.debug("Sending dependency determination request to AI service")
    response = await gemini_client.generate_text(api_request)
    
    try:
        # Extract JSON from response
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'({.*})', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
        
        # Parse JSON
        dependencies = json.loads(json_str)
        
        # Ensure correct structure
        if "runtime" not in dependencies:
            dependencies["runtime"] = []
        if "development" not in dependencies:
            dependencies["development"] = []
        
        return dependencies
        
    except Exception as e:
        self._logger.error(f"Error parsing dependencies: {str(e)}")
        
        # Return default dependencies based on project type and framework
        if project_type == "python":
            if framework == "django":
                return {
                    "runtime": ["django", "django-rest-framework", "psycopg2-binary"],
                    "development": ["pytest", "pytest-django", "flake8", "black"]
                }
            elif framework == "flask":
                return {
                    "runtime": ["flask", "flask-sqlalchemy", "flask-migrate", "flask-cors"],
                    "development": ["pytest", "pytest-flask", "flake8", "black"]
                }
            elif framework == "fastapi":
                return {
                    "runtime": ["fastapi", "uvicorn", "sqlalchemy", "pydantic"],
                    "development": ["pytest", "black", "isort", "mypy"]
                }
            else:
                return {
                    "runtime": ["requests", "pydantic"],
                    "development": ["pytest", "black", "isort"]
                }
        elif project_type == "node":
            if framework == "react":
                return {
                    "runtime": ["react", "react-dom", "react-router-dom"],
                    "development": ["@testing-library/react", "jest", "eslint", "prettier"]
                }
            elif framework == "express":
                return {
                    "runtime": ["express", "cors", "mongoose", "dotenv"],
                    "development": ["nodemon", "jest", "supertest", "eslint"]
                }
            else:
                return {
                    "runtime": ["axios", "dotenv"],
                    "development": ["jest", "eslint", "prettier"]
                }
        else:
            return {
                "runtime": [],
                "development": []
            }

async def _create_files_for_component(
    self, 
    component: ArchitectureComponent,
    project_type: str,
    framework: Optional[str]
) -> List[CodeFile]:
    """
    Create CodeFile objects for a component based on its responsibilities.
    
    Args:
        component: The architecture component
        project_type: Type of project
        framework: Optional framework
        
    Returns:
        List of CodeFile objects
    """
    files = []
    
    # If component already has files defined, use those
    if component.files:
        for file_path in component.files:
            files.append(CodeFile(
                path=file_path,
                content="",  # Content will be generated later
                purpose=f"Part of the {component.name} component: {component.description}",
                dependencies=[],
                language=self._get_language_from_file_path(file_path, project_type)
            ))
        
        return files
    
    # Otherwise, generate files based on the component name and responsibilities
    component_path = component.name.lower().replace(" ", "_")
    
    # Handle different project types
    if project_type == "python":
        # Create a Python package
        files.append(CodeFile(
            path=f"{component_path}/__init__.py",
            content="",
            purpose=f"Package initialization for {component.name}",
            dependencies=[],
            language="python"
        ))
        
        # Add main module
        files.append(CodeFile(
            path=f"{component_path}/main.py",
            content="",
            purpose=f"Main module for {component.name}: {component.description}",
            dependencies=[],
            language="python"
        ))
        
        # Add files based on responsibilities
        for resp in component.responsibilities:
            # Convert responsibility to a file name
            resp_name = resp.lower().replace(" ", "_").replace("-", "_")
            resp_name = re.sub(r'[^a-z0-9_]', '', resp_name)
            
            # Skip if too generic
            if resp_name in ["main", "init", "core", "base"]:
                continue
            
            # Create file
            files.append(CodeFile(
                path=f"{component_path}/{resp_name}.py",
                content="",
                purpose=f"Handles {resp} in the {component.name} component",
                dependencies=[f"{component_path}/__init__.py"],
                language="python"
            ))
            
    elif project_type == "node":
        if framework in ["react", "vue", "angular"]:
            # Frontend component structure
            component_path = f"src/components/{component_path}"
            
            if framework == "react":
                # React component
                files.append(CodeFile(
                    path=f"{component_path}/index.js",
                    content="",
                    purpose=f"Main file for {component.name} React component",
                    dependencies=[],
                    language="javascript"
                ))
                
                files.append(CodeFile(
                    path=f"{component_path}/{component.name.replace(' ', '')}.js",
                    content="",
                    purpose=f"{component.name} React component: {component.description}",
                    dependencies=[],
                    language="javascript"
                ))
                
                files.append(CodeFile(
                    path=f"{component_path}/{component.name.replace(' ', '')}.css",
                    content="",
                    purpose=f"Styles for {component.name} React component",
                    dependencies=[],
                    language="css"
                ))
                
            elif framework == "vue":
                # Vue component
                files.append(CodeFile(
                    path=f"{component_path}/{component.name.replace(' ', '')}.vue",
                    content="",
                    purpose=f"{component.name} Vue component: {component.description}",
                    dependencies=[],
                    language="vue"
                ))
                
            elif framework == "angular":
                # Angular component
                component_selector = component.name.toLowerCase().replace(" ", "-")
                files.append(CodeFile(
                    path=f"{component_path}/{component_selector}.component.ts",
                    content="",
                    purpose=f"{component.name} Angular component: {component.description}",
                    dependencies=[],
                    language="typescript"
                ))
                
                files.append(CodeFile(
                    path=f"{component_path}/{component_selector}.component.html",
                    content="",
                    purpose=f"Template for {component.name} Angular component",
                    dependencies=[],
                    language="html"
                ))
                
                files.append(CodeFile(
                    path=f"{component_path}/{component_selector}.component.css",
                    content="",
                    purpose=f"Styles for {component.name} Angular component",
                    dependencies=[],
                    language="css"
                ))
        else:
            # Backend Node.js structure
            if "controller" in component.name.lower() or "route" in component.name.lower():
                # API controllers/routes
                files.append(CodeFile(
                    path=f"src/routes/{component_path}.js",
                    content="",
                    purpose=f"{component.name}: {component.description}",
                    dependencies=[],
                    language="javascript"
                ))
            elif "model" in component.name.lower():
                # Database models
                files.append(CodeFile(
                    path=f"src/models/{component_path}.js",
                    content="",
                    purpose=f"{component.name}: {component.description}",
                    dependencies=[],
                    language="javascript"
                ))
            elif "service" in component.name.lower():
                # Services
                files.append(CodeFile(
                    path=f"src/services/{component_path}.js",
                    content="",
                    purpose=f"{component.name}: {component.description}",
                    dependencies=[],
                    language="javascript"
                ))
            else:
                # Generic module
                files.append(CodeFile(
                    path=f"src/{component_path}/index.js",
                    content="",
                    purpose=f"Main file for {component.name}",
                    dependencies=[],
                    language="javascript"
                ))
    
    elif project_type == "java":
        # Java package structure
        base_package = "com.example.app"
        component_package = component.name.toLowerCase().replace(" ", "")
        
        files.append(CodeFile(
            path=f"src/main/java/{base_package.replace('.', '/')}/{component_package}/{component.name.replace(' ', '')}.java",
            content="",
            purpose=f"Main class for {component.name}: {component.description}",
            dependencies=[],
            language="java"
        ))
        
        # Add files based on responsibilities
        for resp in component.responsibilities:
            # Convert responsibility to a class name
            class_name = "".join(word.capitalize() for word in resp.split())
            class_name = re.sub(r'[^a-zA-Z0-9]', '', class_name)
            
            # Skip if too generic
            if class_name.lower() in ["main", "core", "base", "app"]:
                continue
            
            # Create file
            files.append(CodeFile(
                path=f"src/main/java/{base_package.replace('.', '/')}/{component_package}/{class_name}.java",
                content="",
                purpose=f"Handles {resp} in the {component.name} component",
                dependencies=[],
                language="java"
            ))
    
    return files

def _get_language_from_file_path(self, file_path: str, project_type: str) -> Optional[str]:
    """
    Determine language from file path.
    
    Args:
        file_path: Path to the file
        project_type: Type of project
        
    Returns:
        Language string or None
    """
    # Extract file extension
    ext = Path(file_path).suffix.lower()
    
    # Map extensions to languages
    if ext == ".py":
        return "python"
    elif ext in [".js", ".jsx"]:
        return "javascript"
    elif ext in [".ts", ".tsx"]:
        return "typescript"
    elif ext == ".java":
        return "java"
    elif ext == ".go":
        return "go"
    elif ext == ".rs":
        return "rust"
    elif ext == ".rb":
        return "ruby"
    elif ext == ".php":
        return "php"
    elif ext == ".html":
        return "html"
    elif ext == ".css":
        return "css"
    elif ext == ".vue":
        return "vue"
    elif ext == ".json":
        return "json"
    elif ext == ".md":
        return "markdown"
    elif ext == ".xml":
        return "xml"
    elif ext == ".yaml" or ext == ".yml":
        return "yaml"
    
    # Fallback to project type
    return project_type

async def _add_standard_project_files(
    self, 
    project_type: str,
    framework: Optional[str],
    project_name: str
) -> List[CodeFile]:
    """
    Add standard files for the project type.
    
    Args:
        project_type: Type of project
        framework: Optional framework
        project_name: Name of the project
        
    Returns:
        List of CodeFile objects
    """
    files = []
    
    # Common files for all projects
    files.append(CodeFile(
        path="README.md",
        content="",
        purpose="Project documentation",
        dependencies=[],
        language="markdown"
    ))
    
    files.append(CodeFile(
        path=".gitignore",
        content="",
        purpose="Git ignore file",
        dependencies=[],
        language="gitignore"
    ))
    
    # Project-specific files
    if project_type == "python":
        files.append(CodeFile(
            path="requirements.txt",
            content="",
            purpose="Python dependencies",
            dependencies=[],
            language="text"
        ))
        
        files.append(CodeFile(
            path="setup.py",
            content="",
            purpose="Python package setup",
            dependencies=[],
            language="python"
        ))
        
        if framework == "django":
            files.append(CodeFile(
                path="manage.py",
                content="",
                purpose="Django management script",
                dependencies=[],
                language="python"
            ))
            
            files.append(CodeFile(
                path=f"{project_name.lower().replace(' ', '_')}/settings.py",
                content="",
                purpose="Django settings",
                dependencies=[],
                language="python"
            ))
            
            files.append(CodeFile(
                path=f"{project_name.lower().replace(' ', '_')}/urls.py",
                content="",
                purpose="Django URL configuration",
                dependencies=[],
                language="python"
            ))
            
            files.append(CodeFile(
                path=f"{project_name.lower().replace(' ', '_')}/__init__.py",
                content="",
                purpose="Django project initialization",
                dependencies=[],
                language="python"
            ))
        
        elif framework == "flask":
            files.append(CodeFile(
                path="app.py",
                content="",
                purpose="Flask application entry point",
                dependencies=[],
                language="python"
            ))
            
            files.append(CodeFile(
                path="config.py",
                content="",
                purpose="Flask configuration",
                dependencies=[],
                language="python"
            ))
        
        elif framework == "fastapi":
            files.append(CodeFile(
                path="main.py",
                content="",
                purpose="FastAPI application entry point",
                dependencies=[],
                language="python"
            ))
    
    elif project_type == "node":
        files.append(CodeFile(
            path="package.json",
            content="",
            purpose="Node.js package configuration",
            dependencies=[],
            language="json"
        ))
        
        files.append(CodeFile(
            path=".env.example",
            content="",
            purpose="Example environment variables",
            dependencies=[],
            language="env"
        ))
        
        if framework == "react":
            files.append(CodeFile(
                path="src/index.js",
                content="",
                purpose="React application entry point",
                dependencies=[],
                language="javascript"
            ))
            
            files.append(CodeFile(
                path="src/App.js",
                content="",
                purpose="Main React component",
                dependencies=[],
                language="javascript"
            ))
            
            files.append(CodeFile(
                path="public/index.html",
                content="",
                purpose="HTML entry point",
                dependencies=[],
                language="html"
            ))
        
        elif framework == "express":
            files.append(CodeFile(
                path="src/index.js",
                content="",
                purpose="Express application entry point",
                dependencies=[],
                language="javascript"
            ))
            
            files.append(CodeFile(
                path="src/app.js",
                content="",
                purpose="Express application setup",
                dependencies=[],
                language="javascript"
            ))
    
    elif project_type == "java":
        files.append(CodeFile(
            path="pom.xml",
            content="",
            purpose="Maven project configuration",
            dependencies=[],
            language="xml"
        ))
        
        base_package = "com.example.app"
        
        if framework == "spring":
            files.append(CodeFile(
                path=f"src/main/java/{base_package.replace('.', '/')}/Application.java",
                content="",
                purpose="Spring Boot application entry point",
                dependencies=[],
                language="java"
            ))
            
            files.append(CodeFile(
                path="src/main/resources/application.properties",
                content="",
                purpose="Spring Boot configuration",
                dependencies=[],
                language="properties"
            ))
    
    return files




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
