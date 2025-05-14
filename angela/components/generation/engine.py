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
import time
import sys

# Import models from the new models module instead of defining them here
from angela.components.generation.models import CodeFile, CodeProject
from angela.components.generation.validators import validate_code
from angela.api.ai import get_gemini_client, get_gemini_request_class
from angela.api.context import get_context_manager, get_context_enhancer
from angela.utils.logging import get_logger
from angela.api.execution import get_filesystem_functions

logger = get_logger(__name__)
GeminiRequest = get_gemini_request_class()


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
            context_manager = get_context_manager()
            context_enhancer = get_context_enhancer()
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
        filesystem = get_filesystem_functions()
        
        if not root_path.exists() and not dry_run:
            await filesystem.create_directory(root_path, parents=True)
        
        # Create files in dependency order
        created_files = []
        file_errors = []
        dependency_graph = self._build_dependency_graph(project.files)
        
        # Process files in dependency order
        for file in self._get_ordered_files(project.files, dependency_graph):
            file_path = root_path / file.path
            
            # Create parent directories if needed
            if not dry_run:
                await filesystem.create_directory(file_path.parent, parents=True)
            
            # Write file content
            try:
                if not dry_run:
                    await filesystem.write_file(file_path, file.content)
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
        gemini_client = get_gemini_client()
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
        
        gemini_client = get_gemini_client()
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
        gemini_client = get_gemini_client()
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

    async def add_feature_to_project(
        self, 
        description: str, 
        project_dir: Union[str, Path],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a new feature to an existing project.
        
        Args:
            description: Natural language description of the feature to add
            project_dir: Path to the project directory
            context: Additional context information
            
        Returns:
            Dictionary with information about the added feature
        """
        self._logger.info(f"Adding feature to project: {description}")
        
        # Get context if not provided
        if context is None:
            context_manager = get_context_manager()
            context_enhancer = get_context_enhancer()
            context = context_manager.get_context_dict()
            context = await context_enhancer.enrich_context(context)
        
        # Convert to Path object
        project_path = Path(project_dir)
        
        # Step 1: Analyze existing project structure
        project_analysis = await self._analyze_existing_project(project_path, context)
        project_type = project_analysis.get("project_type")
        
        if not project_type:
            self._logger.error("Could not determine project type")
            return {
                "success": False,
                "error": "Could not determine project type",
                "project_dir": str(project_path)
            }
        
        # Step 2: Generate feature plan based on description and existing project
        feature_plan = await self._generate_feature_plan(description, project_analysis, context)
        
        # Step 3: Generate file contents for new/modified files
        feature_files = await self._generate_feature_files(feature_plan, project_analysis, context)
        
        # Step 4: Apply changes to the project
        result = await self._apply_feature_changes(feature_files, project_path)
        
        return {
            "success": result.get("success", False),
            "description": description,
            "project_type": project_type,
            "new_files": result.get("created_files", []),
            "modified_files": result.get("modified_files", []),
            "errors": result.get("errors", []),
            "project_dir": str(project_path)
        }

    async def _analyze_existing_project(
        self, 
        project_path: Path, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze an existing project structure.
        
        Args:
            project_path: Path to the project directory
            context: Context information
            
        Returns:
            Dictionary with project analysis information
        """
        self._logger.info(f"Analyzing existing project structure at {project_path}")
        
        # Get project information from context if available
        project_info = {}
        
        if "enhanced_project" in context:
            project_info = {
                "project_type": context["enhanced_project"].get("type", "unknown"),
                "frameworks": context["enhanced_project"].get("frameworks", {}),
                "dependencies": context["enhanced_project"].get("dependencies", {})
            }
        
        # If project type is unknown or not in context, detect it
        if project_info.get("project_type") == "unknown" or not project_info:
            # Import through API layer
            from angela.api.toolchain import get_ci_cd_integration
            ci_cd_integration = get_ci_cd_integration()
            detection_result = await ci_cd_integration.detect_project_type(project_path)
            project_info["project_type"] = detection_result.get("project_type")
        
        # Get file structure
        files = []
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                # Skip common directories to ignore
                if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "venv"]):
                    continue
                    
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(project_path)
                
                # Get basic file info
                file_info = {
                    "path": str(rel_path),
                    "full_path": str(file_path),
                    "type": None,
                    "language": None,
                    "content": None
                }
                
                # Try to determine file type and language
                try:
                    file_detector = get_file_detector()
                    type_info = file_detector.detect_file_type(file_path)
                    file_info["type"] = type_info.get("type")
                    file_info["language"] = type_info.get("language")
                    
                    # Read content for source code files (limit to prevent memory issues)
                    if type_info.get("type") == "source_code" and file_path.stat().st_size < 100000:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            file_info["content"] = f.read()
                except Exception as e:
                    self._logger.debug(f"Error analyzing file {file_path}: {str(e)}")
                
                files.append(file_info)
        
        # Add files to project info
        project_info["files"] = files
        project_info["main_files"] = []
        
        # Try to identify important files based on project type
        if project_info.get("project_type") == "python":
            # Look for main Python files
            for file_info in files:
                if file_info["path"].endswith(".py"):
                    if any(name in file_info["path"].lower() for name in ["main", "app", "index", "server"]):
                        project_info["main_files"].append(file_info["path"])
        elif project_info.get("project_type") == "node":
            # Look for main JavaScript/TypeScript files
            for file_info in files:
                if file_info["path"].endswith((".js", ".ts", ".jsx", ".tsx")):
                    if any(name in file_info["path"].lower() for name in ["main", "app", "index", "server"]):
                        project_info["main_files"].append(file_info["path"])
        
        return project_info

    async def _generate_feature_plan(
        self, 
        description: str,
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a plan for adding a feature to the project.
        
        Args:
            description: Feature description
            project_analysis: Analysis of the existing project
            context: Context information
            
        Returns:
            Dictionary with the feature plan
        """
        self._logger.info(f"Generating feature plan for: {description}")
        
        project_type = project_analysis.get("project_type", "unknown")
        
        # Build a prompt for the AI to generate a feature plan
        prompt = f"""
You are an expert software developer tasked with planning how to add a new feature to an existing {project_type} project.

Feature description: "{description}"

Based on the existing project structure, determine:
1. What new files need to be created
2. What existing files need to be modified
3. How the new feature integrates with the existing codebase

Project Information:
- Project Type: {project_type}
- Main Files: {project_analysis.get('main_files', [])}
- Frameworks: {project_analysis.get('frameworks', {})}

Project Structure:
"""
        
        # Add information about existing files
        files_by_type = {}
        for file_info in project_analysis.get("files", []):
            file_type = file_info.get("type", "unknown")
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            files_by_type[file_type].append(file_info["path"])
        
        for file_type, files in files_by_type.items():
            prompt += f"\n{file_type.upper()} FILES:\n"
            for file_path in files[:10]:  # Limit to 10 files per type to avoid token limits
                prompt += f"- {file_path}\n"
            if len(files) > 10:
                prompt += f"- ... and {len(files) - 10} more {file_type} files\n"
        
        # Add content of main files to give context
        prompt += "\nMain File Contents:\n"
        for file_path in project_analysis.get("main_files", [])[:3]:  # Limit to 3 main files
            for file_info in project_analysis.get("files", []):
                if file_info["path"] == file_path and file_info.get("content"):
                    content = file_info["content"]
                    if len(content) > 1000:  # Limit content size
                        content = content[:1000] + "\n... (truncated)"
                    prompt += f"\nFile: {file_path}\n```\n{content}\n```\n"
        
        prompt += """
Provide your response as a JSON object with this structure:
```json
{
  "new_files": [
    {
      "path": "relative/path/to/file.ext",
      "purpose": "description of the file's purpose",
      "content_template": "template for file content with {{placeholders}}",
      "language": "programming language"
    }
  ],
  "modified_files": [
    {
      "path": "relative/path/to/existing/file.ext",
      "purpose": "description of the modifications",
      "modifications": [
        {
          "type": "add_import",
          "content": "import statement to add",
          "line": 0
        },
        {
          "type": "add_function",
          "content": "function to add",
          "after": "existing function or pattern"
        },
        {
          "type": "replace",
          "search": "code to search for",
          "replace": "replacement code"
        }
      ]
    }
  ],
  "integration_points": [
    "Description of how the feature integrates with existing code"
  ]
}
```
Focus on creating a clean, maintainable implementation that follows the project's existing patterns and best practices.
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.2
        )
        
        self._logger.debug("Sending feature plan request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        plan = await self._parse_feature_plan(response.text)
        
        return plan

    async def _parse_feature_plan(self, response: str) -> Dict[str, Any]:
        """
        Parse the AI response to extract the feature plan.
        
        Args:
            response: AI response text
            
        Returns:
            Dictionary with the feature plan
        """
        # Look for JSON block in the response
        try:
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
            
            return plan_data
        
        except Exception as e:
            self._logger.exception(f"Error parsing feature plan: {str(e)}")
            
            # Return a minimal fallback plan
            return {
                "new_files": [],
                "modified_files": [],
                "integration_points": [
                    "Unable to parse AI response. Consider providing more specific feature description."
                ]
            }

    async def _generate_feature_files(
        self, 
        feature_plan: Dict[str, Any],
        project_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate content for new files and modifications for existing files.
        
        Args:
            feature_plan: Feature plan from _generate_feature_plan
            project_analysis: Analysis of the existing project
            context: Context information
            
        Returns:
            Dictionary with file contents and modifications
        """
        self._logger.info("Generating feature file contents")
        
        feature_files = {
            "new_files": [],
            "modified_files": []
        }
        
        # Process new files
        for file_info in feature_plan.get("new_files", []):
            # Generate content for the new file
            content = await self._generate_new_file_content(
                file_info,
                project_analysis,
                feature_plan,
                context
            )
            
            feature_files["new_files"].append({
                "path": file_info["path"],
                "content": content,
                "purpose": file_info.get("purpose", "")
            })
        
        # Process modified files
        for file_info in feature_plan.get("modified_files", []):
            # Get original content
            original_content = self._get_file_content(file_info["path"], project_analysis)
            
            if original_content is None:
                self._logger.warning(f"Could not find content for file: {file_info['path']}")
                continue
            
            # Apply modifications
            modified_content = await self._apply_file_modifications(
                original_content,
                file_info.get("modifications", []),
                file_info,
                project_analysis,
                feature_plan,
                context
            )
            
            feature_files["modified_files"].append({
                "path": file_info["path"],
                "original_content": original_content,
                "modified_content": modified_content,
                "purpose": file_info.get("purpose", "")
            })
        
        return feature_files

    def _get_file_content(self, file_path: str, project_analysis: Dict[str, Any]) -> Optional[str]:
        """
        Get the content of a file from the project analysis.
        
        Args:
            file_path: Path to the file
            project_analysis: Analysis of the existing project
            
        Returns:
            File content or None if not found
        """
        for file_info in project_analysis.get("files", []):
            if file_info["path"] == file_path:
                return file_info.get("content")
        return None

    async def _generate_new_file_content(
        self, 
        file_info: Dict[str, Any],
        project_analysis: Dict[str, Any],
        feature_plan: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate content for a new file.
        
        Args:
            file_info: Information about the new file
            project_analysis: Analysis of the existing project
            feature_plan: Overall feature plan
            context: Context information
            
        Returns:
            Generated file content
        """
        self._logger.debug(f"Generating content for new file: {file_info['path']}")
        
        # Get template if provided
        template = file_info.get("content_template", "")
        
        # If template has placeholders, we should fill them in
        # This is simplified; in a real implementation you would have more context
        if template and "{{" in template:
            # Process template with placeholders
            # This is just a simple example
            template = template.replace("{{project_type}}", project_analysis.get("project_type", ""))
        
        # If template is not provided or is minimal, generate content with AI
        if len(template.strip()) < 50:  # Arbitrary threshold
            # Build prompt for file generation
            prompt = f"""
Generate the content for a new file in a {project_analysis.get('project_type', 'unknown')} project.

File path: {file_info['path']}
File purpose: {file_info.get('purpose', 'Unknown')}

This file is part of a new feature described as:
{feature_plan.get('integration_points', ['Unknown'])[0] if feature_plan.get('integration_points') else 'Unknown'}

The project already has files like:
"""
            # Add a few relevant existing files for context
            file_extension = Path(file_info['path']).suffix
            for existing_file in project_analysis.get("files", [])[:5]:
                if existing_file.get("path", "").endswith(file_extension):
                    prompt += f"- {existing_file['path']}\n"
            
            # Add content of a similar file for style reference
            similar_files = [f for f in project_analysis.get("files", []) 
                            if f.get("path", "").endswith(file_extension) and f.get("content")]
            
            if similar_files:
                similar_file = similar_files[0]
                content = similar_file.get("content", "")
                if len(content) > 1000:  # Limit content size
                    content = content[:1000] + "\n... (truncated)"
                prompt += f"\nReference file ({similar_file['path']}) for style consistency:\n"
                prompt += f"```\n{content}\n```\n"
            
            prompt += "\nGenerate the complete content for the new file, following the project's style and conventions."
            
            # Call AI service
            api_request = GeminiRequest(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.2
            )
            
            response = await gemini_client.generate_text(api_request)
            
            # Extract code from the response
            content = self._extract_code_from_response(response.text, file_info['path'])
            return content
        
        return template

    async def _apply_file_modifications(
        self, 
        original_content: str,
        modifications: List[Dict[str, Any]],
        file_info: Dict[str, Any],
        project_analysis: Dict[str, Any],
        feature_plan: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Apply modifications to an existing file.
        
        Args:
            original_content: Original file content
            modifications: List of modifications to apply
            file_info: Information about the file
            project_analysis: Analysis of the existing project
            feature_plan: Overall feature plan
            context: Context information
            
        Returns:
            Modified file content
        """
        self._logger.debug(f"Applying modifications to file: {file_info['path']}")
        
        modified_content = original_content
        
        # Apply each modification in sequence
        for mod in modifications:
            mod_type = mod.get("type", "")
            
            if mod_type == "add_import":
                # Add import statement at the top
                import_stmt = mod.get("content", "")
                if import_stmt:
                    # Find where imports end
                    lines = modified_content.splitlines()
                    import_end_line = 0
                    
                    # Look for existing imports
                    for i, line in enumerate(lines):
                        if line.strip().startswith(("import ", "from ")):
                            import_end_line = i + 1
                    
                    # Insert import at the right position
                    lines.insert(import_end_line, import_stmt)
                    modified_content = "\n".join(lines)
            
            elif mod_type == "add_function":
                # Add function/method to the file
                function_content = mod.get("content", "")
                after_pattern = mod.get("after", "")
                
                if function_content:
                    if after_pattern and after_pattern in modified_content:
                        # Insert after specific pattern
                        parts = modified_content.split(after_pattern, 1)
                        modified_content = parts[0] + after_pattern + "\n\n" + function_content + "\n" + parts[1]
                    else:
                        # Append to the end of the file
                        if not modified_content.endswith("\n"):
                            modified_content += "\n"
                        modified_content += "\n" + function_content + "\n"
            
            elif mod_type == "replace":
                # Replace text in the file
                search_text = mod.get("search", "")
                replace_text = mod.get("replace", "")
                
                if search_text and replace_text:
                    modified_content = modified_content.replace(search_text, replace_text)
        
        # If no modifications were applied successfully or instructions were unclear,
        # use AI to apply the modifications
        if modified_content == original_content:
            modified_content = await self._generate_file_modifications_with_ai(
                original_content,
                file_info,
                project_analysis,
                feature_plan,
                context
            )
        
        return modified_content

    async def _generate_file_modifications_with_ai(
        self, 
        original_content: str,
        file_info: Dict[str, Any],
        project_analysis: Dict[str, Any],
        feature_plan: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Use AI to generate modifications for a file when structured modifications fail.
        
        Args:
            original_content: Original file content
            file_info: Information about the file
            project_analysis: Analysis of the existing project
            feature_plan: Overall feature plan
            context: Context information
            
        Returns:
            Modified file content
        """
        self._logger.debug(f"Using AI to generate modifications for: {file_info['path']}")
        
        # Build prompt for generating modifications
        prompt = f"""
Modify the content of an existing file in a {project_analysis.get('project_type', 'unknown')} project to implement a new feature.

File path: {file_info['path']}
Modification purpose: {file_info.get('purpose', 'Unknown')}

This modification is part of a new feature described as:
{feature_plan.get('integration_points', ['Unknown'])[0] if feature_plan.get('integration_points') else 'Unknown'}

Original file content:
```
{original_content}
```

Your task is to modify this file to implement the specified feature. Return the complete modified content.
Follow the project's existing coding style and patterns.
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Extract code from the response
        modified_content = self._extract_code_from_response(response.text, file_info['path'])
        return modified_content

    async def _apply_feature_changes(
        self, 
        feature_files: Dict[str, Any],
        project_path: Path
    ) -> Dict[str, Any]:
        """
        Apply the generated feature changes to the project.
        
        Args:
            feature_files: Generated file contents and modifications
            project_path: Path to the project directory
            
        Returns:
            Dictionary with application results
        """
        self._logger.info("Applying feature changes to project")
        
        result = {
            "success": True,
            "created_files": [],
            "modified_files": [],
            "errors": []
        }
        
        # Get filesystem functions
        filesystem = get_filesystem_functions()
        
        # Create new files
        for file_info in feature_files.get("new_files", []):
            file_path = project_path / file_info["path"]
            
            try:
                # Create parent directories if needed
                await filesystem.create_directory(file_path.parent, parents=True)
                
                # Write file content
                await filesystem.write_file(file_path, file_info["content"])
                
                result["created_files"].append(str(file_path))
                self._logger.debug(f"Created new file: {file_path}")
            except Exception as e:
                self._logger.error(f"Error creating file {file_path}: {str(e)}")
                result["errors"].append({"path": str(file_path), "error": str(e)})
                result["success"] = False
        
        # Modify existing files
        for file_info in feature_files.get("modified_files", []):
            file_path = project_path / file_info["path"]
            
            try:
                # Check if file exists
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Write modified content
                await filesystem.write_file(file_path, file_info["modified_content"])
                
                result["modified_files"].append(str(file_path))
                self._logger.debug(f"Modified file: {file_path}")
            except Exception as e:
                self._logger.error(f"Error modifying file {file_path}: {str(e)}")
                result["errors"].append({"path": str(file_path), "error": str(e)})
                result["success"] = False
        
        return result

    async def _extract_dependencies_from_feature(
        self, 
        feature_files: Dict[str, Any],
        project_type: str
    ) -> Dict[str, List[str]]:
        """
        Extract dependencies from newly added or modified feature files.
        
        Args:
            feature_files: Dictionary with new and modified files
            project_type: Type of the project (python, node, etc.)
            
        Returns:
            Dictionary with runtime and development dependencies
        """
        self._logger.info("Extracting dependencies from feature files")
        
        dependencies = {
            "runtime": [],
            "development": []
        }
        
        # Process based on project type
        if project_type == "python":
            # Look for Python import statements in new files
            for file_info in feature_files.get("new_files", []):
                if file_info["path"].endswith(".py"):
                    content = file_info["content"]
                    
                    # Extract import statements using regex
                    import_lines = re.findall(r'^(?:import|from)\s+([^\s.]+)(?:\.|.*?import)', content, re.MULTILINE)
                    
                    # Filter out standard library modules
                    for module in import_lines:
                        if module not in sys.modules or (hasattr(sys.modules[module], '__file__') and 
                                                        sys.modules[module].__file__ and 
                                                        'site-packages' in sys.modules[module].__file__):
                            if module not in dependencies["runtime"] and module not in ["__future__", "typing", "os", "sys", "re", "json", "time", "datetime"]:
                                dependencies["runtime"].append(module)
            
            # Also check modified files for new imports
            for file_info in feature_files.get("modified_files", []):
                if file_info["path"].endswith(".py"):
                    original_content = file_info["original_content"]
                    modified_content = file_info["modified_content"]
                    
                    # Extract imports from original and modified content
                    original_imports = set(re.findall(r'^(?:import|from)\s+([^\s.]+)(?:\.|.*?import)', original_content, re.MULTILINE))
                    modified_imports = set(re.findall(r'^(?:import|from)\s+([^\s.]+)(?:\.|.*?import)', modified_content, re.MULTILINE))
                    
                    # Find new imports
                    new_imports = modified_imports - original_imports
                    
                    # Add to dependencies list
                    for module in new_imports:
                        if module not in dependencies["runtime"] and module not in ["__future__", "typing", "os", "sys", "re", "json", "time", "datetime"]:
                            dependencies["runtime"].append(module)
                            
        elif project_type == "node":
            # Look for import/require statements in JavaScript/TypeScript files
            js_extensions = [".js", ".jsx", ".ts", ".tsx"]
            
            for file_info in feature_files.get("new_files", []):
                if any(file_info["path"].endswith(ext) for ext in js_extensions):
                    content = file_info["content"]
                    
                    # Look for ES6 imports
                    es6_imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'".][^\'"]*)[\'"]\s*;?', content)
                    
                    # Look for require statements
                    require_imports = re.findall(r'(?:const|let|var)\s+.*?=\s+require\([\'"]([^\'".][^\'"]*)[\'"]\)\s*;?', content)
                    
                    # Combine all found imports
                    all_imports = es6_imports + require_imports
                    
                    # Filter out relative imports
                    for module in all_imports:
                        if not module.startswith(".") and module not in dependencies["runtime"]:
                            dependencies["runtime"].append(module)
            
            # Also check modified files
            for file_info in feature_files.get("modified_files", []):
                if any(file_info["path"].endswith(ext) for ext in js_extensions):
                    original_content = file_info["original_content"]
                    modified_content = file_info["modified_content"]
                    
                    # Extract imports from original content
                    original_es6 = set(re.findall(r'import\s+.*?from\s+[\'"]([^\'".][^\'"]*)[\'"]\s*;?', original_content))
                    original_require = set(re.findall(r'(?:const|let|var)\s+.*?=\s+require\([\'"]([^\'".][^\'"]*)[\'"]\)\s*;?', original_content))
                    original_imports = original_es6.union(original_require)
                    
                    # Extract imports from modified content
                    modified_es6 = set(re.findall(r'import\s+.*?from\s+[\'"]([^\'".][^\'"]*)[\'"]\s*;?', modified_content))
                    modified_require = set(re.findall(r'(?:const|let|var)\s+.*?=\s+require\([\'"]([^\'".][^\'"]*)[\'"]\)\s*;?', modified_content))
                    modified_imports = modified_es6.union(modified_require)
                    
                    # Find new imports
                    new_imports = modified_imports - original_imports
                    
                    # Add to dependencies list
                    for module in new_imports:
                        if not module.startswith(".") and module not in dependencies["runtime"]:
                            dependencies["runtime"].append(module)
        
        # Add common testing libraries based on project type
        if project_type == "python":
            dependencies["development"] = ["pytest", "pytest-cov"]
        elif project_type == "node":
            dependencies["development"] = ["jest", "eslint"]
        
        return dependencies

    async def generate_complex_project(
        self, 
        description: str, 
        output_dir: Optional[str] = None,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        use_detailed_planning: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> CodeProject:
        """
        Generate a complex multi-file project with enhanced architecture planning.
        
        Args:
            description: Natural language description of the project
            output_dir: Directory where the project should be generated (defaults to cwd)
            project_type: Optional type of project to generate (auto-detected if None)
            framework: Optional framework to use (e.g., 'react', 'django')
            use_detailed_planning: Whether to use detailed architecture planning
            context: Additional context information
            
        Returns:
            CodeProject object representing the generated project
        """
        self._logger.info(f"Generating complex project from description: {description}")
        
        
        from angela.api.generation import get_generation_context_manager # Import inside method
        generation_context_manager = get_generation_context_manager()          
        
        start_time = time.time()
        
        # Get current context if not provided
        if context is None:
            context_manager = get_context_manager()
            context_enhancer = get_context_enhancer()
            context = context_manager.get_context_dict()
            context = await context_enhancer.enrich_context(context)
        
        # Determine output directory
        if output_dir is None:
            output_dir = context.get("cwd", os.getcwd())
        
        # Determine project type if not specified
        if project_type is None:
            project_type = await self._infer_project_type(description, context)
            self._logger.debug(f"Inferred project type: {project_type}")
        
        # Get project name from description
        project_name = await self._extract_project_name(description, project_type)
        self._logger.debug(f"Project name: {project_name}")
        
        # Determine framework if not specified
        if framework is None and project_type in ["python", "node", "java"]:
            framework = await self._infer_framework(description, project_type)
            self._logger.debug(f"Inferred framework: {framework}")
        
        # Get project planner through the API layer
        from angela.api.generation import get_project_planner, get_project_architecture_class
        project_planner = get_project_planner()
        ProjectArchitecture = get_project_architecture_class()
        
        # Create a detailed architecture if requested
        if use_detailed_planning:
            # Generate a detailed architecture
            architecture = await project_planner.create_detailed_project_architecture(
                description=description,
                project_type=project_type,
                framework=framework,
                context=context
            )
            
            self._logger.info(f"Created detailed architecture with {len(architecture.components)} components")
            
            # Generate dependency graph for visualization
            dependency_graph = await project_planner.generate_dependency_graph(architecture)
            
            # Create project plan from architecture
            project_plan = await project_planner.create_project_plan_from_architecture(
                architecture=architecture,
                project_name=project_name,
                project_type=project_type,
                description=description,
                framework=framework,
                context=context
            )
        else:
            # Use the standard project planning approach
            project_plan = await self._create_project_plan(
                description=description,
                output_dir=output_dir,
                project_type=project_type,
                context=context
            )
        
        self._logger.info(f"Created project plan with {len(project_plan.files)} files")
        
        # Analyze project structure to understand relationships between files
        generation_context_manager = get_generation_context_manager()
        analysis_result = await generation_context_manager.analyze_code_relationships(project_plan.files)
        self._logger.debug(f"Code relationship analysis complete: {analysis_result}")
        
        # Generate file contents with enhanced context
        project_plan = await self._generate_complex_file_contents(project_plan, context)
        
        # Log generation time
        elapsed_time = time.time() - start_time
        self._logger.info(f"Project generation completed in {elapsed_time:.2f} seconds")
        
        return project_plan
    
    async def _extract_project_name(self, description: str, project_type: str) -> str:
        """
        Extract a project name from the description.
        
        Args:
            description: Project description
            project_type: Type of project
            
        Returns:
            Project name
        """
        # Build prompt for project name extraction
        prompt = f"""
Extract a concise, appropriate project name from this description for a {project_type} project:

"{description}"

Return ONLY the project name as a single phrase, nothing else.
The name should be concise, memorable, and related to the project's purpose.
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=20,  # Very small limit since we only need the name
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Clean up the response
        name = response.text.strip().strip('"\'').strip()
        
        # If the name is too long, truncate it
        if len(name) > 50:
            name = name[:50]
        
        # Replace spaces with underscores and remove special characters
        name = re.sub(r'[^a-zA-Z0-9 _-]', '', name)
        
        # If extraction failed, use a default name
        if not name:
            name = f"new_{project_type}_project"
        
        return name
    
    async def _infer_framework(self, description: str, project_type: str) -> Optional[str]:
        """
        Infer the framework from the description.
        
        Args:
            description: Project description
            project_type: Type of project
            
        Returns:
            Framework name or None
        """
        # Build prompt for framework inference
        prompt = f"""
Determine the most appropriate framework for this {project_type} project:

"{description}"

Consider only the most popular, mainstream frameworks for {project_type}.
For Python, consider: Django, Flask, FastAPI
For Node.js, consider: Express, React, Vue, Angular, Next.js
For Java, consider: Spring Boot, Jakarta EE, Quarkus

Return ONLY the framework name, nothing else.
If no specific framework is clearly indicated, return "None".
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=20,  # Very small limit since we only need the framework name
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Clean up the response
        framework = response.text.strip().strip('"\'').strip()
        
        # Check if a framework was identified
        if framework.lower() in ["none", "no framework", "unknown"]:
            return None
        
        return framework
    
    async def _generate_complex_file_contents(
        self, 
        project: CodeProject,
        context: Dict[str, Any]
    ) -> CodeProject:
        """
        Generate content for each file in the project with enhanced context awareness.
        
        Args:
            project: CodeProject with file information
            context: Additional context information
            
        Returns:
            Updated CodeProject with file contents
        """
        self._logger.info(f"Generating content for {len(project.files)} files with enhanced context")
        
        # Process files in dependency order
        dependency_graph = self._build_dependency_graph(project.files)
        
        # Prepare batches of files to generate
        batches = self._create_file_batches(project.files, dependency_graph)
        
        # Generate content for each batch
        for batch_idx, batch in enumerate(batches):
            self._logger.debug(f"Processing batch {batch_idx+1}/{len(batches)} with {len(batch)} files")
            
            # Generate content for each file in the batch concurrently
            tasks = []
            for file in batch:
                # Get files that this file depends on
                dependencies = self._get_dependency_files(file, project.files, dependency_graph)
                
                task = self._generate_complex_file_content(
                    file, 
                    project, 
                    dependencies,
                    context
                )
                tasks.append(task)
            
            # Wait for all tasks in this batch to complete
            results = await asyncio.gather(*tasks)
            
            # Update file contents
            for file, content in zip(batch, results):
                file.content = content
                
                # Register file in generation context manager
                await generation_context_manager.extract_entities_from_file(file)
        
        return project
    
    def _get_dependency_files(
        self, 
        file: CodeFile, 
        all_files: List[CodeFile],
        dependency_graph: Dict[str, Set[str]]
    ) -> List[CodeFile]:
        """
        Get the files that this file depends on.
        
        Args:
            file: The file to get dependencies for
            all_files: All files in the project
            dependency_graph: Dependency graph
            
        Returns:
            List of dependency files
        """
        # Get dependency paths
        dep_paths = dependency_graph.get(file.path, set())
        
        # Find the corresponding files
        return [f for f in all_files if f.path in dep_paths]
    
    async def _generate_complex_file_content(
        self, 
        file: CodeFile, 
        project: CodeProject,
        dependencies: List[CodeFile],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate content for a single file with enhanced context.
        
        Args:
            file: CodeFile to generate content for
            project: Parent CodeProject
            dependencies: Files this file depends on
            context: Additional context information
            
        Returns:
            Generated file content
        """
        self._logger.debug(f"Generating content for file: {file.path}")
        
        
        from angela.api.generation import get_generation_context_manager 
        generation_context_manager = get_generation_context_manager()    

        # Build prompt for file content generation
        prompt = self._build_complex_file_content_prompt(file, project, dependencies)
        
        # Enhance prompt with generation context
        generation_context_manager = get_generation_context_manager()
        related_files = [dep.path for dep in dependencies]
        enhanced_prompt = await generation_context_manager.enhance_prompt_with_context(
            prompt=prompt,
            file_path=file.path,
            related_files=related_files
        )
        
        # Set reasonable token limits based on file complexity
        max_tokens = self._determine_max_tokens_for_file(file)
        
        # Call AI service to generate file content
        gemini_client = get_gemini_client()
        api_request = GeminiRequest(
            prompt=enhanced_prompt,
            max_tokens=max_tokens,
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
                max_tokens=max_tokens,
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
    
    def _build_complex_file_content_prompt(
        self, 
        file: CodeFile, 
        project: CodeProject,
        dependencies: List[CodeFile]
    ) -> str:
        """
        Build a prompt for generating file content with enhanced context.
        
        Args:
            file: CodeFile to generate content for
            project: Parent CodeProject
            dependencies: Files this file depends on
            
        Returns:
            Prompt string for the AI service
        """
        # Get file extension and determine language
        ext = Path(file.path).suffix.lower()
        language = file.language or self._get_language_from_extension(ext)
        
        # Determine the file's role in the project
        file_role = self._determine_file_role(file, project)
        
        # Project structure details
        structure_details = f"Project follows {project.structure_explanation}" if project.structure_explanation else ""
        
        # List dependencies with their purposes
        dependencies_context = ""
        if dependencies:
            dependencies_context = "This file depends on:\n"
            for dep in dependencies:
                dependencies_context += f"- {dep.path}: {dep.purpose}\n"
                
                # Include top sections of dependency content if available
                if dep.content:
                    # Show first 20 non-empty lines or 500 chars, whichever is less
                    preview_lines = [line for line in dep.content.split('\n') if line.strip()][:20]
                    preview = '\n'.join(preview_lines)
                    if len(preview) > 500:
                        preview = preview[:500] + "...(truncated)"
                    
                    dependencies_context += f"  Content preview:\n```\n{preview}\n```\n"
        
        prompt = f"""
You are an expert software developer working on a {project.project_type} project named "{project.name}".

PROJECT DESCRIPTION:
{project.description}

FILE DETAILS:
Path: {file.path}
Purpose: {file.purpose}
Language: {language}
Role: {file_role}

PROJECT STRUCTURE:
{structure_details}

{dependencies_context}

Your task is to generate high-quality, production-ready code for this file that:
1. Fulfills the stated purpose
2. Integrates properly with dependencies
3. Follows best practices and conventions for {language}
4. Is well-structured and commented appropriately
5. Includes proper error handling
6. Is efficient and maintainable

Generate ONLY the content for this file, nothing else.
"""
        
        # Add language-specific guidance
        if language == "python":
            prompt += """
Python-specific guidance:
- Follow PEP 8 style guidelines
- Use proper type hints
- Include docstrings for classes and functions
- Use proper exception handling
- Avoid circular imports
"""
        elif language in ["javascript", "typescript"]:
            prompt += """
JavaScript/TypeScript guidance:
- Use modern ES6+ syntax
- Handle async operations properly with async/await
- Use proper error handling
- Include JSDoc comments for functions
- Use consistent naming conventions
"""
        elif language in ["java"]:
            prompt += """
Java guidance:
- Follow standard Java conventions
- Use proper exception handling
- Include JavaDoc comments
- Use appropriate access modifiers
- Follow SOLID principles
"""
        
        # Add role-specific guidance
        if "model" in file_role.lower() or "entity" in file_role.lower():
            prompt += """
For data models/entities:
- Define clear field types and validation
- Include necessary relationships
- Add appropriate methods for data access
- Consider serialization needs
- Include proper constraints and indexes if applicable
"""
        elif "controller" in file_role.lower() or "view" in file_role.lower():
            prompt += """
For controllers/views:
- Focus on handling user input and presentation
- Keep business logic separate
- Include proper validation
- Handle errors gracefully
- Consider user experience
"""
        elif "service" in file_role.lower() or "util" in file_role.lower():
            prompt += """
For services/utilities:
- Create reusable, focused components
- Include comprehensive error handling
- Ensure thread safety if applicable
- Make functions pure when possible
- Use dependency injection where appropriate
"""
        
        return prompt
    
    def _determine_file_role(self, file: CodeFile, project: CodeProject) -> str:
        """
        Determine the role of a file in the project.
        
        Args:
            file: The file to determine role for
            project: The parent project
            
        Returns:
            String describing the file's role
        """
        path = file.path.lower()
        
        # Check based on directory/path pattern
        if "model" in path or "entity" in path or "schema" in path:
            return "Data Model/Entity"
        elif "controller" in path:
            return "Controller"
        elif "view" in path or "template" in path or "component" in path:
            return "View/UI Component"
        elif "service" in path:
            return "Service"
        elif "repository" in path or "dao" in path:
            return "Data Access"
        elif "util" in path or "helper" in path:
            return "Utility"
        elif "config" in path or "setting" in path:
            return "Configuration"
        elif "middleware" in path:
            return "Middleware"
        elif "test" in path:
            return "Test"
        elif "route" in path or "url" in path:
            return "Routing"
        elif "api" in path:
            return "API Endpoint"
        elif "__init__.py" in path:
            return "Package Initialization"
        elif any(path.endswith(ext) for ext in [".js", ".ts"]) and "index" in path:
            return "Module Entry Point"
        
        # Check based on file purpose
        purpose = file.purpose.lower()
        if "model" in purpose or "entity" in purpose or "schema" in purpose:
            return "Data Model/Entity"
        elif "controller" in purpose:
            return "Controller"
        elif "view" in purpose or "template" in purpose or "component" in purpose or "ui" in purpose:
            return "View/UI Component"
        elif "service" in purpose:
            return "Service"
        elif "repository" in purpose or "dao" in purpose:
            return "Data Access"
        
        # Default
        return "General Component"
    
    def _determine_max_tokens_for_file(self, file: CodeFile) -> int:
        """
        Determine the maximum tokens to allocate for generating a file.
        
        Args:
            file: The file to determine token limit for
            
        Returns:
            Maximum token count
        """
        # Base token limit
        base_limit = 8000
        
        # Adjust based on expected file complexity
        path = file.path.lower()
        
        # Configuration files are typically smaller
        if "config" in path or path.endswith((".json", ".yaml", ".yml", ".toml", ".ini")):
            return base_limit // 2
        
        # Main application files often need more tokens
        if "main" in path or "app" in path or "index" in path:
            return base_limit * 2
        
        # Complex components like controllers, services might need more
        if "controller" in path or "service" in path:
            return int(base_limit * 1.5)
        
        # Test files may need more tokens to properly test functionality
        if "test" in path:
            return int(base_limit * 1.25)
        
        return base_limit
    
    def _get_language_from_extension(self, ext: str) -> str:
        """
        Get language from file extension.
        
        Args:
            ext: File extension with dot
            
        Returns:
            Language name
        """
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "JavaScript (React)",
            ".ts": "TypeScript",
            ".tsx": "TypeScript (React)",
            ".java": "Java",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".json": "JSON",
            ".xml": "XML",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".md": "Markdown",
            ".sql": "SQL",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C/C++ Header",
            ".cs": "C#",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".vue": "Vue"
        }
        
        return ext_map.get(ext, "Unknown")
    
    async def generate_file_summaries(self, project: CodeProject) -> Dict[str, str]:
        """
        Generate concise summaries for each file in the project.
        
        Args:
            project: The CodeProject to summarize
            
        Returns:
            Dictionary mapping file paths to summaries
        """
        self._logger.info(f"Generating summaries for {len(project.files)} files")
        
        summaries = {}
        
        # Process files in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(project.files), batch_size):
            batch = project.files[i:i+batch_size]
            
            # Generate summaries concurrently
            tasks = [self._generate_file_summary(file) for file in batch]
            batch_summaries = await asyncio.gather(*tasks)
            
            # Add to results
            for file, summary in zip(batch, batch_summaries):
                summaries[file.path] = summary
        
        return summaries
    
    async def _generate_file_summary(self, file: CodeFile) -> str:
        """
        Generate a concise summary for a file.
        
        Args:
            file: The file to summarize
            
        Returns:
            Summary string
        """
        # Skip if no content
        if not file.content:
            return "Empty file"
        
        # Build prompt
        prompt = f"""
Provide a concise 1-2 sentence summary of this {file.language if file.language else ''} file:
{file.content[:4000] if len(file.content) > 4000 else file.content}

{f"File content truncated due to length ({len(file.content)} chars)" if len(file.content) > 4000 else ""}

Focus on what the file does rather than how it does it. Highlight its purpose, key functionality, and role in the system.
Keep your response to 1-2 sentences maximum.
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=100,  # Very short summary
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Return cleaned summary
        return response.text.strip()

code_generation_engine = CodeGenerationEngine()
