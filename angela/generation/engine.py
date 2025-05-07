# angela/generation/engine.py
"""
Advanced code generation engine for Angela CLI.

This module provides capabilities for generating entire directory structures
and multiple code files based on high-level natural language descriptions.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import json
import re

from pydantic import BaseModel, Field

from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.context.enhancer import context_enhancer
from angela.utils.logging import get_logger
from angela.execution.filesystem import create_directory, create_file, write_file
from angela.generation.validators import validate_code

logger = get_logger(__name__)

class CodeFile(BaseModel):
    """Model for a code file to be generated."""
    path: str = Field(..., description="Relative path to the file")
    content: str = Field(..., description="Content of the file")
    purpose: str = Field(..., description="Purpose/description of the file")
    dependencies: List[str] = Field(default_factory=list, description="Paths of files this depends on")
    language: Optional[str] = Field(None, description="Programming language of the file")

class CodeProject(BaseModel):
    """Model for a complete code project to be generated."""
    name: str = Field(..., description="Name of the project")
    description: str = Field(..., description="Description of the project")
    root_dir: str = Field(..., description="Root directory for the project")
    files: List[CodeFile] = Field(..., description="List of files to generate")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="External dependencies")
    project_type: str = Field(..., description="Type of project (e.g., python, node)")
    structure_explanation: str = Field(..., description="Explanation of the project structure")

class CodeGenerationEngine:
    """
    Advanced code generation engine that can create entire projects
    based on natural language descriptions.
    """
    
    def __init__(self):
        """Initialize the code generation engine."""
        self._logger = logger
    
    async def generate_project(
        self, 
        description: str, 
        output_dir: Optional[str] = None,
        project_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> CodeProject:
        """
        Generate a complete project from a description.
        
        Args:
            description: Natural language description of the project
            output_dir: Directory where the project should be generated (defaults to cwd)
            project_type: Optional type of project to generate (auto-detected if None)
            context: Additional context information
            
        Returns:
            CodeProject object representing the generated project
        """
        self._logger.info(f"Generating project from description: {description}")
        
        # Get current context if not provided
        if context is None:
            context = context_manager.get_context_dict()
            context = await context_enhancer.enrich_context(context)
        
        # Determine output directory
        if output_dir is None:
            output_dir = context.get("cwd", os.getcwd())
        
        # Create project plan
        project_plan = await self._create_project_plan(description, output_dir, project_type, context)
        self._logger.info(f"Created project plan with {len(project_plan.files)} files")
        
        # Validate the project plan
        is_valid, validation_errors = await self._validate_project_plan(project_plan)
        
        if not is_valid:
            self._logger.error(f"Project plan validation failed: {validation_errors}")
            # Try to fix validation errors
            project_plan = await self._fix_validation_errors(project_plan, validation_errors)
        
        return project_plan
    
    async def create_project_files(
        self, 
        project: CodeProject,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Create the actual files for a project.
        
        Args:
            project: CodeProject to generate
            dry_run: Whether to simulate file creation without making changes
            
        Returns:
            Dictionary with creation results
        """
        self._logger.info(f"Creating project files for: {project.name}")
        
        # Create the root directory if it doesn't exist
        root_path = Path(project.root_dir)
        if not root_path.exists() and not dry_run:
            await create_directory(root_path, parents=True)
        
        # Create files in dependency order
        created_files = []
        file_errors = []
        dependency_graph = self._build_dependency_graph(project.files)
        
        # Process files in dependency order
        for file in self._get_ordered_files(project.files, dependency_graph):
            file_path = root_path / file.path
            
            # Create parent directories if needed
            if not dry_run:
                await create_directory(file_path.parent, parents=True)
            
            # Write file content
            try:
                if not dry_run:
                    await write_file(file_path, file.content)
                created_files.append(str(file_path))
                self._logger.debug(f"Created file: {file_path}")
            except Exception as e:
                self._logger.error(f"Error creating file {file_path}: {str(e)}")
                file_errors.append({"path": str(file_path), "error": str(e)})
        
        return {
            "project_name": project.name,
            "root_dir": str(root_path),
            "created_files": created_files,
            "file_errors": file_errors,
            "file_count": len(created_files),
            "success": len(file_errors) == 0,
            "dry_run": dry_run
        }
    
    async def _create_project_plan(
        self, 
        description: str, 
        output_dir: str,
        project_type: Optional[str],
        context: Dict[str, Any]
    ) -> CodeProject:
        """
        Create a plan for a project based on the description.
        
        Args:
            description: Natural language description of the project
            output_dir: Directory where the project should be generated
            project_type: Optional type of project to generate
            context: Additional context information
            
        Returns:
            CodeProject object with the plan
        """
        # Determine project type if not specified
        if project_type is None:
            project_type = await self._infer_project_type(description, context)
            self._logger.debug(f"Inferred project type: {project_type}")
        
        # Build prompt for project planning
        prompt = self._build_project_planning_prompt(description, project_type, context)
        
        # Call AI service to generate project plan
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,  # Large token limit for complex project plans
            temperature=0.2   # Low temperature for more deterministic output
        )
        
        self._logger.debug("Sending project planning request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response to extract the project plan
        project_plan = await self._parse_project_plan(response.text, output_dir, project_type)
        
        # Generate detailed content for each file
        project_plan = await self._generate_file_contents(project_plan, context)
        
        return project_plan
    
    async def _infer_project_type(
        self, 
        description: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Infer the project type from the description.
        
        Args:
            description: Natural language description of the project
            context: Additional context information
            
        Returns:
            String indicating the project type
        """
        # Check for explicit mentions of languages/frameworks
        tech_indicators = {
            "python": ["python", "flask", "django", "fastapi", "sqlalchemy", "pytest"],
            "node": ["node", "javascript", "express", "react", "vue", "angular", "npm"],
            "java": ["java", "spring", "maven", "gradle", "junit"],
            "go": ["go", "golang", "gin", "echo"],
            "ruby": ["ruby", "rails", "sinatra", "rspec"],
            "rust": ["rust", "cargo", "actix", "rocket"],
        }
        
        # Lowercase description for easier matching
        description_lower = description.lower()
        
        # Count mentions of each technology
        tech_counts = {}
        for tech, indicators in tech_indicators.items():
            count = sum(indicator in description_lower for indicator in indicators)
            if count > 0:
                tech_counts[tech] = count
        
        # If we found clear indicators, return the most mentioned
        if tech_counts:
            return max(tech_counts.items(), key=lambda x: x[1])[0]
        
        # No clear indicators, use AI to infer
        prompt = f"""
Determine the most suitable programming language/framework for this project:

"{description}"

Return only the project type as a single word, using one of these options:
python, node, java, go, ruby, rust, or other.
"""
        
        api_request = GeminiRequest(prompt=prompt, max_tokens=10)
        response = await gemini_client.generate_text(api_request)
        
        # Extract the project type from the response
        project_type = response.text.strip().lower()
        
        # Default to python if we couldn't determine
        if project_type not in {"python", "node", "java", "go", "ruby", "rust"}:
            return "python"
        
        return project_type
    
    def _build_project_planning_prompt(
        self, 
        description: str,
        project_type: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Build a prompt for project planning.
        
        Args:
            description: Natural language description of the project
            project_type: Type of project to generate
            context: Additional context information
            
        Returns:
            Prompt string for the AI service
        """
        prompt = f"""
You are an expert software architect tasked with planning a {project_type} project based on this description:

"{description}"

First, analyze the requirements and identify:
1. Core components needed
2. Data models and their relationships
3. Key functionality to be implemented
4. External dependencies required

Then, create a detailed project structure plan in JSON format, including:

```json
{{
  "name": "project_name",
  "description": "brief project description",
  "project_type": "{project_type}",
  "dependencies": {{
    "runtime": ["list", "of", "dependencies"],
    "development": ["test", "frameworks", "etc"]
  }},
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "purpose": "description of the file's purpose",
      "dependencies": ["other/files/this/depends/on"],
      "language": "programming language"
    }}
  ],
  "structure_explanation": "explanation of why this structure was chosen"
}}
Focus on creating a well-structured, maintainable project following best practices for {project_type} projects. Include appropriate configuration files, tests, documentation, and proper project organization.
The project should be modular, follow SOLID principles, and be easy to extend.
"""
    return prompt

async def _parse_project_plan(
    self, 
    response: str, 
    output_dir: str,
    project_type: str
) -> CodeProject:
    """
    Parse the AI response to extract the project plan.
    
    Args:
        response: AI response text
        output_dir: Directory where the project should be generated
        project_type: Type of project to generate
        
    Returns:
        CodeProject object with the plan
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
            files.append(CodeFile(
                path=file_data["path"],
                content="",  # Content will be generated later
                purpose=file_data["purpose"],
                dependencies=file_data.get("dependencies", []),
                language=file_data.get("language")
            ))
        
        # Create CodeProject object
        project = CodeProject(
            name=plan_data.get("name", f"new_{project_type}_project"),
            description=plan_data.get("description", "Generated project"),
            root_dir=output_dir,
            files=files,
            dependencies=plan_data.get("dependencies", {}),
            project_type=project_type,
            structure_explanation=plan_data.get("structure_explanation", "")
        )
        
        return project
        
    except Exception as e:
        self._logger.exception(f"Error parsing project plan: {str(e)}")
        
        # Create a minimal fallback project
        fallback_file = CodeFile(
            path="main.py" if project_type == "python" else "index.js",
            content="",
            purpose="Main entry point",
            dependencies=[],
            language=project_type
        )
        
        return CodeProject(
            name=f"new_{project_type}_project",
            description="Generated project (fallback)",
            root_dir=output_dir,
            files=[fallback_file],
            dependencies={},
            project_type=project_type,
            structure_explanation="Fallback project structure due to parsing error."
        )

async def _generate_file_contents(
    self, 
    project: CodeProject,
    context: Dict[str, Any]
) -> CodeProject:
    """
    Generate content for each file in the project.
    
    Args:
        project: CodeProject with file information
        context: Additional context information
        
    Returns:
        Updated CodeProject with file contents
    """
    self._logger.info(f"Generating content for {len(project.files)} files")
    
    # Process files in dependency order
    dependency_graph = self._build_dependency_graph(project.files)
    
    # Prepare batches of files to generate (to avoid too many concurrent requests)
    batches = self._create_file_batches(project.files, dependency_graph)
    
    # Generate content for each batch
    for batch_idx, batch in enumerate(batches):
        self._logger.debug(f"Processing batch {batch_idx+1}/{len(batches)} with {len(batch)} files")
        
        # Generate content for each file in the batch concurrently
        tasks = []
        for file in batch:
            # Load previous file contents for dependencies
            dependencies_content = {}
            for dep_path in file.dependencies:
                # Find the dependent file
                for dep_file in project.files:
                    if dep_file.path == dep_path and dep_file.content:
                        dependencies_content[dep_path] = dep_file.content
            
            task = self._generate_file_content(
                file, 
                project, 
                dependencies_content,
                context
            )
            tasks.append(task)
        
        # Wait for all tasks in this batch to complete
        results = await asyncio.gather(*tasks)
        
        # Update file contents
        for file, content in zip(batch, results):
            file.content = content
    
    return project

async def _generate_file_content(
    self, 
    file: CodeFile, 
    project: CodeProject,
    dependencies_content: Dict[str, str],
    context: Dict[str, Any]
) -> str:
    """
    Generate content for a single file.
    
    Args:
        file: CodeFile to generate content for
        project: Parent CodeProject
        dependencies_content: Content of files this depends on
        context: Additional context information
        
    Returns:
        Generated file content
    """
    self._logger.debug(f"Generating content for file: {file.path}")
    
    # Build prompt for file content generation
    prompt = self._build_file_content_prompt(file, project, dependencies_content)
    
    # Call AI service to generate file content
    api_request = GeminiRequest(
        prompt=prompt,
        max_tokens=4000,
        temperature=0.2
    )
    
    response = await gemini_client.generate_text(api_request)
    
    # Extract code from the response
    content = self._extract_code_from_response(response.text, file.path)
    
    # Validate the generated code
    is_valid, validation_message = validate_code(content, file.path)
    
    # If validation failed, try once more with the error message
    if not is_valid:
        self._logger.warning(f"Validation failed for {file.path}: {validation_message}")
        
        # Build a new prompt with the validation error
        fix_prompt = f"""
The code you generated has an issue that needs to be fixed:
{validation_message}
Here is the original code:
{content}
Please provide the corrected code for file '{file.path}'.
Only respond with the corrected code, nothing else.
"""
        # Call AI service to fix the code
        fix_request = GeminiRequest(
            prompt=fix_prompt,
            max_tokens=4000,
            temperature=0.1
        )
        
        fix_response = await gemini_client.generate_text(fix_request)
        
        # Extract fixed code
        fixed_content = self._extract_code_from_response(fix_response.text, file.path)
        
        # Validate again
        is_valid, _ = validate_code(fixed_content, file.path)
        if is_valid:
            content = fixed_content
    
    return content

def _build_file_content_prompt(
    self, 
    file: CodeFile, 
    project: CodeProject,
    dependencies_content: Dict[str, str]
) -> str:
    """
    Build a prompt for generating file content.
    
    Args:
        file: CodeFile to generate content for
        project: Parent CodeProject
        dependencies_content: Content of files this depends on
        
    Returns:
        Prompt string for the AI service
    """
    # Add language context based on file extension
    language_hints = ""
    if file.language:
        language_hints = f"The file should be written in {file.language}."
    
    # Add dependencies context
    dependencies_context = ""
    if dependencies_content:
        dependencies_context = "This file depends on the following files:\n\n"
        
        for dep_path, content in dependencies_content.items():
            # Limit content size to avoid token limits
            if len(content) > 1000:
                content = content[:1000] + "\n... (truncated)"
            
            dependencies_context += f"File: {dep_path}\n```\n{content}\n```\n\n"
    
    prompt = f"""
You are an expert software developer working on a {project.project_type} project named "{project.name}".
{project.description}
You need to create the file "{file.path}" with the following purpose:
{file.purpose}
{language_hints}
The project has the following overall structure:
{project.structure_explanation}
{dependencies_context}
Generate only the code for this file. The code should be well-structured, properly formatted, and follow best practices for its language. Include appropriate comments and documentation.
Only return the file content, nothing else.
"""
    return prompt

def _extract_code_from_response(self, response: str, file_path: str) -> str:
    """
    Extract code from the AI response.
    
    Args:
        response: AI response text
        file_path: Path of the file being generated
        
    Returns:
        Extracted code content
    """
    # Try to extract code from markdown code blocks
    code_match = re.search(r'```(?:\w+)?\s*(.*?)\s*```', response, re.DOTALL)
    if code_match:
        return code_match.group(1)
    
    # No code block found, use the entire response
    return response.strip()

def _build_dependency_graph(self, files: List[CodeFile]) -> Dict[str, Set[str]]:
    """
    Build a dependency graph for the files.
    
    Args:
        files: List of files to process
        
    Returns:
        Dictionary mapping file paths to sets of dependent file paths
    """
    # Map file paths to indices
    path_to_index = {file.path: i for i, file in enumerate(files)}
    
    # Initialize the graph
    graph = {}
    for file in files:
        graph[file.path] = set()
        for dep_path in file.dependencies:
            if dep_path in path_to_index:
                graph[file.path].add(dep_path)
    
    return graph

def _get_ordered_files(
    self, 
    files: List[CodeFile], 
    graph: Dict[str, Set[str]]
) -> List[CodeFile]:
    """
    Get files in dependency order (topological sort).
    
    Args:
        files: List of files to order
        graph: Dependency graph
        
    Returns:
        Ordered list of files
    """
    # Map file paths to objects
    path_to_file = {file.path: file for file in files}
    
    # Keep track of visited and ordered nodes
    visited = set()
    ordered = []
    
    def visit(path):
        """DFS visit function for topological sort."""
        if path in visited:
            return
        
        visited.add(path)
        
        # Visit dependencies first
        for dep_path in graph.get(path, set()):
            visit(dep_path)
        
        # Add to ordered list
        if path in path_to_file:
            ordered.append(path_to_file[path])
    
    # Visit all nodes
    for file in files:
        visit(file.path)
    
    return ordered

def _create_file_batches(
    self, 
    files: List[CodeFile], 
    graph: Dict[str, Set[str]]
) -> List[List[CodeFile]]:
    """
    Create batches of files that can be generated concurrently.
    
    Args:
        files: List of files to batch
        graph: Dependency graph
        
    Returns:
        List of file batches
    """
    # Get files in dependency order
    ordered_files = self._get_ordered_files(files, graph)
    
    # Group files by their dependency level
    levels = {}
    path_to_level = {}
    
    # Compute the dependency level for each file
    for file in ordered_files:
        # The level is 1 + the maximum level of dependencies
        max_dep_level = 0
        for dep_path in file.dependencies:
            if dep_path in path_to_level:
                max_dep_level = max(max_dep_level, path_to_level[dep_path])
        
        level = max_dep_level + 1
        path_to_level[file.path] = level
        
        if level not in levels:
            levels[level] = []
        
        levels[level].append(file)
    
    # Create batches from levels
    batches = []
    for level in sorted(levels.keys()):
        batches.append(levels[level])
    
    return batches

async def _validate_project_plan(
    self, 
    project: CodeProject
) -> Tuple[bool, List[str]]:
    """
    Validate a project plan for consistency.
    
    Args:
        project: CodeProject to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check for duplicate file paths
    paths = [file.path for file in project.files]
    if len(paths) != len(set(paths)):
        duplicate_paths = [path for path in paths if paths.count(path) > 1]
        errors.append(f"Duplicate file paths: {set(duplicate_paths)}")
    
    # Check for circular dependencies
    try:
        graph = self._build_dependency_graph(project.files)
        self._get_ordered_files(project.files, graph)
    except Exception as e:
        errors.append(f"Circular dependencies detected: {str(e)}")
    
    # Check for missing dependencies
    path_set = set(paths)
    for file in project.files:
        for dep_path in file.dependencies:
            if dep_path not in path_set:
                errors.append(f"File {file.path} depends on non-existent file {dep_path}")
    
    return len(errors) == 0, errors

async def _fix_validation_errors(
    self, 
    project: CodeProject, 
    errors: List[str]
) -> CodeProject:
    """
    Try to fix validation errors in a project plan.
    
    Args:
        project: The project plan to fix
        errors: List of validation errors
        
    Returns:
        Fixed CodeProject
    """
    self._logger.info(f"Attempting to fix {len(errors)} validation errors")
    
    # Handle duplicate paths
    if any("Duplicate file paths" in error for error in errors):
        # Create a map of paths to files
        path_to_files = {}
        for file in project.files:
            if file.path not in path_to_files:
                path_to_files[file.path] = []
            path_to_files[file.path].append(file)
        
        # Keep only the first instance of each duplicate
        new_files = []
        for path, files in path_to_files.items():
            new_files.append(files[0])
        
        project.files = new_files
    
    # Handle circular dependencies
    if any("Circular dependencies" in error for error in errors):
        # Remove dependencies that create cycles
        graph = {}
        for file in project.files:
            graph[file.path] = set(file.dependencies)
        
        # Find and break cycles
        visited = set()
        path = []
        
        def find_cycles(node):
            if node in path:
                # Cycle detected, break it
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                
                # Remove the last dependency in the cycle
                source = cycle[-2]
                target = cycle[-1]
                for file in project.files:
                    if file.path == source:
                        if target in file.dependencies:
                            file.dependencies.remove(target)
                            self._logger.debug(f"Removed dependency from {source} to {target} to break cycle")
                
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, set()):
                if find_cycles(neighbor):
                    return True
            
            path.pop()
            return False
        
        # Find and fix all cycles
        for node in list(graph.keys()):
            while find_cycles(node):
                visited = set()
                path = []
        
    # Handle missing dependencies
    if any("depends on non-existent file" in error for error in errors):
        # Remove dependencies that don't exist
        valid_paths = {file.path for file in project.files}
        for file in project.files:
            file.dependencies = [dep for dep in file.dependencies if dep in valid_paths]
    
    return project


code_generation_engine = CodeGenerationEngine()
