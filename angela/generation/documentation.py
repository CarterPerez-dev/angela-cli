# angela/generation/documentation.py
"""
Documentation generation for Angela CLI.

This module provides capabilities for generating documentation for projects,
including READMEs, API docs, and user guides.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re

from angela.ai.client import gemini_client, GeminiRequest
from angela.utils.logging import get_logger
from angela.context import context_manager

logger = get_logger(__name__)

class DocumentationGenerator:
    """
    Generator for project documentation.
    """
    
    def __init__(self):
        """Initialize the documentation generator."""
        self._logger = logger
    
    async def generate_readme(
        self, 
        project_path: Union[str, Path],
        project_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a README file for a project.
        
        Args:
            project_path: Path to the project
            project_info: Optional project information
            context: Additional context information
            
        Returns:
            Dictionary with the generated README
        """
        self._logger.info(f"Generating README for project at {project_path}")
        
        # Analyze project if project_info not provided
        if not project_info:
            project_info = await self._analyze_project(project_path, context)
        
        # Build prompt for the AI
        prompt = self._build_readme_prompt(project_info)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.3
        )
        
        self._logger.debug("Sending README generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Extract README content from the response
        readme_content = self._extract_markdown_content(response.text)
        
        return {
            "content": readme_content,
            "file_name": "README.md",
            "project_path": str(project_path)
        }
    
    async def generate_api_docs(
        self, 
        project_path: Union[str, Path],
        files: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate API documentation for a project.
        
        Args:
            project_path: Path to the project
            files: Optional list of files to document
            context: Additional context information
            
        Returns:
            Dictionary with the generated API docs
        """
        self._logger.info(f"Generating API docs for project at {project_path}")
        
        # Convert to Path object
        project_path = Path(project_path)
        
        # Get files if not provided
        if not files:
            project_info = await self._analyze_project(project_path, context)
            files = project_info.get("files", [])
        
        # Filter for source code files
        source_files = [f for f in files if f.get("type") == "source_code"]
        
        # Determine project type
        project_type = "unknown"
        if context and "enhanced_project" in context:
            project_type = context["enhanced_project"].get("type", "unknown")
        elif any(f.get("path", "").endswith(".py") for f in source_files):
            project_type = "python"
        elif any(f.get("path", "").endswith((".js", ".jsx", ".ts", ".tsx")) for f in source_files):
            project_type = "node"
        elif any(f.get("path", "").endswith(".java") for f in source_files):
            project_type = "java"
        
        # Generate docs based on project type
        if project_type == "python":
            return await self._generate_python_api_docs(project_path, source_files)
        elif project_type == "node":
            return await self._generate_js_api_docs(project_path, source_files)
        elif project_type == "java":
            return await self._generate_java_api_docs(project_path, source_files)
        else:
            return await self._generate_generic_api_docs(project_path, source_files)
    
    async def generate_user_guide(
        self, 
        project_path: Union[str, Path],
        project_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a user guide for a project.
        
        Args:
            project_path: Path to the project
            project_info: Optional project information
            context: Additional context information
            
        Returns:
            Dictionary with the generated user guide
        """
        self._logger.info(f"Generating user guide for project at {project_path}")
        
        # Analyze project if project_info not provided
        if not project_info:
            project_info = await self._analyze_project(project_path, context)
        
        # Build prompt for the AI
        prompt = self._build_user_guide_prompt(project_info)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=6000,
            temperature=0.3
        )
        
        self._logger.debug("Sending user guide generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Extract user guide content from the response
        guide_content = self._extract_markdown_content(response.text)
        
        return {
            "content": guide_content,
            "file_name": "USER_GUIDE.md",
            "project_path": str(project_path)
        }
    
    async def generate_contributing_guide(
        self, 
        project_path: Union[str, Path],
        project_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a CONTRIBUTING guide for a project.
        
        Args:
            project_path: Path to the project
            project_info: Optional project information
            context: Additional context information
            
        Returns:
            Dictionary with the generated contributing guide
        """
        self._logger.info(f"Generating contributing guide for project at {project_path}")
        
        # Analyze project if project_info not provided
        if not project_info:
            project_info = await self._analyze_project(project_path, context)
        
        # Build prompt for the AI
        prompt = self._build_contributing_prompt(project_info)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.3
        )
        
        self._logger.debug("Sending contributing guide generation request to AI service")
        response = await gemini_client.generate_text(api_request)
        
        # Extract contributing guide content from the response
        guide_content = self._extract_markdown_content(response.text)
        
        return {
            "content": guide_content,
            "file_name": "CONTRIBUTING.md",
            "project_path": str(project_path)
        }
    
    async def _analyze_project(
        self, 
        project_path: Union[str, Path],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a project to gather information for documentation.
        
        Args:
            project_path: Path to the project
            context: Additional context information
            
        Returns:
            Dictionary with project information
        """
        self._logger.info(f"Analyzing project at {project_path}")
        
        # Convert to Path object
        project_path = Path(project_path)
        
        # Use context if available
        if context and "enhanced_project" in context:
            return {
                "project_type": context["enhanced_project"].get("type", "unknown"),
                "frameworks": context["enhanced_project"].get("frameworks", {}),
                "dependencies": context["enhanced_project"].get("dependencies", {}),
                "files": context.get("files", []),
                "path": str(project_path),
                "name": project_path.name
            }
        
        # Perform a simplified project analysis
        project_info = {
            "project_type": "unknown",
            "frameworks": {},
            "dependencies": {},
            "files": [],
            "path": str(project_path),
            "name": project_path.name
        }
        
        # Determine project type
        if (project_path / "requirements.txt").exists() or (project_path / "setup.py").exists() or (project_path / "pyproject.toml").exists():
            project_info["project_type"] = "python"
        elif (project_path / "package.json").exists():
            project_info["project_type"] = "node"
        elif (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
            project_info["project_type"] = "java"
        
        # Get dependencies
        if project_info["project_type"] == "python":
            if (project_path / "requirements.txt").exists():
                try:
                    with open(project_path / "requirements.txt", 'r') as f:
                        deps = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                        project_info["dependencies"] = {"runtime": deps}
                except Exception as e:
                    self._logger.error(f"Error reading requirements.txt: {str(e)}")
        elif project_info["project_type"] == "node":
            if (project_path / "package.json").exists():
                try:
                    with open(project_path / "package.json", 'r') as f:
                        package_data = json.load(f)
                        project_info["dependencies"] = {
                            "runtime": list(package_data.get("dependencies", {}).keys()),
                            "development": list(package_data.get("devDependencies", {}).keys())
                        }
                        # Get project name
                        if "name" in package_data:
                            project_info["name"] = package_data["name"]
                except Exception as e:
                    self._logger.error(f"Error reading package.json: {str(e)}")
        
        # Collect file information
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                # Skip common directories to ignore
                if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "venv", ".idea", ".vscode"]):
                    continue
                
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(project_path)
                
                # Skip files over 1MB
                if file_path.stat().st_size > 1000000:
                    continue
                
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
                    from angela.context.file_detector import detect_file_type
                    type_info = detect_file_detector.detect_file_type(file_path)
                    file_info["type"] = type_info.get("type")
                    file_info["language"] = type_info.get("language")
                    
                    # Read content for source code files and documentation files
                    if file_info["type"] in ["source_code", "document"] and file_path.stat().st_size < 100000:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            file_info["content"] = f.read()
                except Exception as e:
                    self._logger.debug(f"Error analyzing file {file_path}: {str(e)}")
                
                project_info["files"].append(file_info)
        
        # Try to find entry points
        project_info["entry_points"] = self._find_entry_points(project_info)
        
        return project_info
    
    def _find_entry_points(self, project_info: Dict[str, Any]) -> List[str]:
        """
        Find potential entry points for the project.
        
        Args:
            project_info: Project information
            
        Returns:
            List of potential entry point files
        """
        entry_points = []
        
        if project_info["project_type"] == "python":
            # Look for Python entry points
            main_files = [f for f in project_info["files"] if f.get("path") in [
                "main.py", "__main__.py", "app.py", "server.py", "run.py"
            ]]
            
            # If no common entry point, look for files with main function
            if not main_files:
                for file_info in project_info["files"]:
                    if file_info.get("content") and "if __name__ == '__main__'" in file_info.get("content"):
                        main_files.append(file_info)
            
            entry_points.extend([f.get("path") for f in main_files])
            
        elif project_info["project_type"] == "node":
            # Look for Node.js entry points
            main_files = [f for f in project_info["files"] if f.get("path") in [
                "index.js", "server.js", "app.js", "main.js"
            ]]
            
            # Check package.json main field
            for file_info in project_info["files"]:
                if file_info.get("path") == "package.json" and file_info.get("content"):
                    try:
                        package_data = json.loads(file_info.get("content"))
                        if "main" in package_data:
                            main_file = package_data["main"]
                            # Add to entry points if not already there
                            if main_file not in [f.get("path") for f in main_files]:
                                main_files.append({"path": main_file})
                    except Exception:
                        pass
            
            entry_points.extend([f.get("path") for f in main_files])
        
        return entry_points
    
    def _build_readme_prompt(self, project_info: Dict[str, Any]) -> str:
        """
        Build a prompt for README generation.
        
        Args:
            project_info: Project information
            
        Returns:
            Prompt string for the AI service
        """
        prompt = f"""
You are an expert technical writer tasked with creating a comprehensive README.md file for a {project_info.get('project_type', 'software')} project named "{project_info.get('name', 'Project')}".

Project details:
- Type: {project_info.get('project_type', 'Unknown')}
"""
        
        # Add dependencies information
        if "dependencies" in project_info:
            prompt += "- Dependencies:\n"
            
            if "runtime" in project_info["dependencies"]:
                runtime_deps = project_info["dependencies"]["runtime"]
                if runtime_deps:
                    prompt += f"  - Runtime: {', '.join(runtime_deps[:10])}"
                    if len(runtime_deps) > 10:
                        prompt += f" and {len(runtime_deps) - 10} more"
                    prompt += "\n"
            
            if "development" in project_info["dependencies"]:
                dev_deps = project_info["dependencies"]["development"]
                if dev_deps:
                    prompt += f"  - Development: {', '.join(dev_deps[:10])}"
                    if len(dev_deps) > 10:
                        prompt += f" and {len(dev_deps) - 10} more"
                    prompt += "\n"
        
        # Add entry points information
        if "entry_points" in project_info and project_info["entry_points"]:
            prompt += f"- Entry points: {', '.join(project_info['entry_points'])}\n"
        
        # Add file structure information
        file_types = {}
        for file_info in project_info.get("files", []):
            file_type = file_info.get("type")
            if file_type:
                if file_type not in file_types:
                    file_types[file_type] = []
                file_types[file_type].append(file_info.get("path"))
        
        prompt += "- File structure summary:\n"
        for file_type, files in file_types.items():
            prompt += f"  - {file_type} files: {len(files)}\n"
        
        # Add main source files
        source_files = file_types.get("source_code", [])
        if source_files:
            prompt += "- Main source files (up to 10):\n"
            for file in source_files[:10]:
                prompt += f"  - {file}\n"
        
        prompt += """
Create a comprehensive README.md file that follows these best practices:
1. Clear project title and description
2. Installation instructions
3. Usage examples
4. Features list
5. API documentation overview (if applicable)
6. Project structure explanation
7. Contributing guidelines reference
8. License information
9. Badges for build status, version, etc. (if applicable)

The README should be well-formatted with Markdown, including:
- Proper headings (# for main title, ## for sections, etc.)
- Code blocks with appropriate syntax highlighting
- Lists (ordered and unordered)
- Links to important resources
- Tables where appropriate

Make the README user-friendly, comprehensive, and professional.
"""
        
        return prompt
    
    async def _generate_python_api_docs(
        self, 
        project_path: Path,
        source_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate API documentation for a Python project.
        
        Args:
            project_path: Path to the project
            source_files: List of source files
            
        Returns:
            Dictionary with the generated API docs
        """
        self._logger.info("Generating Python API docs")
        
        # Filter for Python files
        python_files = [f for f in source_files if f.get("path", "").endswith(".py")]
        
        # Organize files by module/package
        modules = {}
        
        for file_info in python_files:
            file_path = file_info.get("path", "")
            
            # Skip __init__.py files with no content
            if file_path.endswith("__init__.py") and not file_info.get("content", "").strip():
                continue
            
            # Determine module name
            if "/" in file_path:
                # File in a package
                package_parts = file_path.split("/")
                module_name = ".".join(package_parts[:-1])
                if module_name not in modules:
                    modules[module_name] = []
                modules[module_name].append(file_info)
            else:
                # File in root
                module_name = "root"
                if module_name not in modules:
                    modules[module_name] = []
                modules[module_name].append(file_info)
        
        # Generate docs for each module
        module_docs = {}
        
        for module_name, files in modules.items():
            module_docs[module_name] = await self._generate_python_module_docs(module_name, files)
        
        # Create docs structure
        docs_structure = {
            "index.md": self._generate_python_docs_index(modules, project_path.name),
            "modules": module_docs
        }
        
        return {
            "structure": docs_structure,
            "format": "markdown",
            "project_path": str(project_path)
        }
    
    async def _generate_python_module_docs(
        self, 
        module_name: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate documentation for a Python module.
        
        Args:
            module_name: Name of the module
            files: List of files in the module
            
        Returns:
            Dictionary mapping file names to documentation content
        """
        module_docs = {}
        
        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            if not content:
                continue
            
            # Extract file name without extension
            file_name = os.path.basename(file_path)
            doc_name = os.path.splitext(file_name)[0]
            
            # Parse Python content
            doc_content = await self._parse_python_file(file_path, content)
            
            # Generate markdown
            markdown = f"""# {doc_name}

{doc_content.get('module_docstring', 'No description available.')}

## Classes

"""
            # Add classes
            for class_name, class_info in doc_content.get("classes", {}).items():
                markdown += f"### {class_name}\n\n{class_info.get('docstring', 'No description available.')}\n\n"
                
                # Add methods
                if class_info.get("methods"):
                    markdown += "#### Methods\n\n"
                    for method_name, method_info in class_info.get("methods", {}).items():
                        markdown += f"##### `{method_name}{method_info.get('signature', '()') }`\n\n{method_info.get('docstring', 'No description available.')}\n\n"
            
            # Add functions
            if doc_content.get("functions"):
                markdown += "## Functions\n\n"
                for func_name, func_info in doc_content.get("functions", {}).items():
                    markdown += f"### `{func_name}{func_info.get('signature', '()') }`\n\n{func_info.get('docstring', 'No description available.')}\n\n"
            
            module_docs[doc_name + ".md"] = markdown
        
        return module_docs
    
    async def _parse_python_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Parse Python file for documentation.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Dictionary with parsed documentation
        """
        # Basic structure
        doc_info = {
            "module_docstring": "",
            "classes": {},
            "functions": {}
        }
        
        # Extract module docstring
        module_docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if module_docstring_match:
            doc_info["module_docstring"] = module_docstring_match.group(1).strip()
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\([^)]*\))?:\s*(?:"""(.*?)""")?'
        for match in re.finditer(class_pattern, content, re.DOTALL):
            class_name = match.group(1)
            class_docstring = match.group(2) if match.group(2) else ""
            
            # Get class content
            class_start = match.end()
            class_content = ""
            
            # Find the end of the class (by indentation)
            for line in content[class_start:].splitlines():
                if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                    break
                class_content += line + "\n"
            
            # Extract methods
            methods = {}
            method_pattern = r'^\s+def\s+(\w+)\s*\((self(?:,\s*[^)]*)?)\):\s*(?:"""(.*?)""")?'
            for method_match in re.finditer(method_pattern, class_content, re.MULTILINE | re.DOTALL):
                method_name = method_match.group(1)
                method_signature = method_match.group(2).strip()
                method_docstring = method_match.group(3) if method_match.group(3) else ""
                
                methods[method_name] = {
                    "signature": f"({method_signature})",
                    "docstring": method_docstring.strip()
                }
            
            doc_info["classes"][class_name] = {
                "docstring": class_docstring.strip(),
                "methods": methods
            }
        
        # Extract functions
        function_pattern = r'^def\s+(\w+)\s*\(([^)]*)\):\s*(?:"""(.*?)""")?'
        for match in re.finditer(function_pattern, content, re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            func_signature = match.group(2).strip()
            func_docstring = match.group(3) if match.group(3) else ""
            
            doc_info["functions"][func_name] = {
                "signature": f"({func_signature})",
                "docstring": func_docstring.strip()
            }
        
        return doc_info
    
    def _generate_python_docs_index(self, modules: Dict[str, List[Dict[str, Any]]], project_name: str) -> str:
        """
        Generate index page for Python API docs.
        
        Args:
            modules: Dictionary mapping module names to files
            project_name: Name of the project
            
        Returns:
            Markdown content for index page
        """
        markdown = f"""# {project_name} API Documentation

## Modules

"""
        # Add module links
        for module_name, files in modules.items():
            if module_name == "root":
                markdown += "### Root Module\n\n"
            else:
                markdown += f"### {module_name}\n\n"
            
            for file_info in files:
                file_path = file_info.get("path", "")
                file_name = os.path.basename(file_path)
                doc_name = os.path.splitext(file_name)[0]
                
                markdown += f"- [{doc_name}](modules/{doc_name}.md)\n"
            
            markdown += "\n"
        
        return markdown
    
    async def _generate_js_api_docs(
        self, 
        project_path: Path,
        source_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate API documentation for a JavaScript/TypeScript project.
        
        Args:
            project_path: Path to the project
            source_files: List of source files
            
        Returns:
            Dictionary with the generated API docs
        """
        self._logger.info("Generating JavaScript/TypeScript API docs")
        
        # Filter for JS/TS files
        js_files = [f for f in source_files if f.get("path", "").endswith((".js", ".jsx", ".ts", ".tsx"))]
        
        # Organize files by directory
        directories = {}
        
        for file_info in js_files:
            file_path = file_info.get("path", "")
            
            if "/" in file_path:
                # File in a directory
                dir_parts = file_path.split("/")
                dir_name = dir_parts[0]
                if dir_name not in directories:
                    directories[dir_name] = []
                directories[dir_name].append(file_info)
            else:
                # File in root
                dir_name = "root"
                if dir_name not in directories:
                    directories[dir_name] = []
                directories[dir_name].append(file_info)
        
        # Generate docs for each directory
        dir_docs = {}
        
        for dir_name, files in directories.items():
            dir_docs[dir_name] = await self._generate_js_directory_docs(dir_name, files)
        
        # Create docs structure
        docs_structure = {
            "index.md": self._generate_js_docs_index(directories, project_path.name),
            "modules": dir_docs
        }
        
        return {
            "structure": docs_structure,
            "format": "markdown",
            "project_path": str(project_path)
        }
    
    async def _generate_js_directory_docs(
        self, 
        dir_name: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate documentation for a JavaScript/TypeScript directory.
        
        Args:
            dir_name: Name of the directory
            files: List of files in the directory
            
        Returns:
            Dictionary mapping file names to documentation content
        """
        dir_docs = {}
        
        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            if not content:
                continue
            
            # Extract file name without extension
            file_name = os.path.basename(file_path)
            doc_name = os.path.splitext(file_name)[0]
            
            # Parse JS/TS content
            is_typescript = file_path.endswith((".ts", ".tsx"))
            doc_content = await self._parse_js_file(file_path, content, is_typescript)
            
            # Generate markdown
            markdown = f"""# {doc_name}

{doc_content.get('file_description', 'No description available.')}

## Exports

"""
            # Add classes
            for class_name, class_info in doc_content.get("classes", {}).items():
                markdown += f"### Class: {class_name}\n\n{class_info.get('description', 'No description available.')}\n\n"
                
                # Add methods
                if class_info.get("methods"):
                    markdown += "#### Methods\n\n"
                    for method_name, method_info in class_info.get("methods", {}).items():
                        markdown += f"##### `{method_name}{method_info.get('signature', '()') }`\n\n{method_info.get('description', 'No description available.')}\n\n"
            
            # Add functions
            if doc_content.get("functions"):
                markdown += "## Functions\n\n"
                for func_name, func_info in doc_content.get("functions", {}).items():
                    markdown += f"### `{func_name}{func_info.get('signature', '()') }`\n\n{func_info.get('description', 'No description available.')}\n\n"
            
            # Add interfaces (TypeScript only)
            if is_typescript and doc_content.get("interfaces"):
                markdown += "## Interfaces\n\n"
                for interface_name, interface_info in doc_content.get("interfaces", {}).items():
                    markdown += f"### Interface: {interface_name}\n\n{interface_info.get('description', 'No description available.')}\n\n"
                    
                    if interface_info.get("properties"):
                        markdown += "#### Properties\n\n"
                        for prop_name, prop_info in interface_info.get("properties", {}).items():
                            markdown += f"- `{prop_name}: {prop_info.get('type', 'any')}` - {prop_info.get('description', 'No description available.')}\n"
                    
                    markdown += "\n"
            
            dir_docs[doc_name + ".md"] = markdown
        
        return dir_docs
    
    async def _parse_js_file(
        self, 
        file_path: str, 
        content: str, 
        is_typescript: bool = False
    ) -> Dict[str, Any]:
        """
        Parse JavaScript/TypeScript file for documentation.
        
        Args:
            file_path: Path to the file
            content: File content
            is_typescript: Whether the file is TypeScript
            
        Returns:
            Dictionary with parsed documentation
        """
        # Basic structure
        doc_info = {
            "file_description": "",
            "classes": {},
            "functions": {}
        }
        
        if is_typescript:
            doc_info["interfaces"] = {}
        
        # Extract file description from initial comment block
        file_comment_match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
        if file_comment_match:
            doc_info["file_description"] = self._parse_js_comment(file_comment_match.group(1))
        
        # Extract classes
        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{([^}]*\/\*\*.*?\*\/)?'
        for match in re.finditer(class_pattern, content, re.DOTALL):
            class_name = match.group(1)
            class_content = match.group(0)
            
            # Extract class comment
            class_comment_match = re.search(r'/\*\*(.*?)\*/', class_content, re.DOTALL)
            class_description = self._parse_js_comment(class_comment_match.group(1)) if class_comment_match else ""
            
            # Extract methods
            methods = {}
            method_pattern = r'(?:public|private|protected)?\s*(\w+)\s*\(([^)]*)\)(?:\s*:\s*[\w<>[\],\s]+)?(?:\s*{)?(?:\s*/\*\*(.*?)\*\/)?'
            for method_match in re.finditer(method_pattern, class_content, re.DOTALL):
                method_name = method_match.group(1)
                method_signature = method_match.group(2).strip()
                method_comment = method_match.group(3) if method_match.group(3) else ""
                
                methods[method_name] = {
                    "signature": f"({method_signature})",
                    "description": self._parse_js_comment(method_comment)
                }
            
            doc_info["classes"][class_name] = {
                "description": class_description,
                "methods": methods
            }
        
        # Extract functions
        function_pattern = r'(?:export\s+)?(?:function|const|let|var)\s+(\w+)\s*(?:=\s*(?:function)?\s*)?(?:\([^)]*\))(?:\s*:\s*[\w<>[\],\s]+)?(?:\s*=>)?(?:\s*{)?(?:\s*/\*\*(.*?)\*\/)?'
        for match in re.finditer(function_pattern, content, re.DOTALL):
            func_name = match.group(1)
            func_comment = match.group(2) if match.group(2) else ""
            
            # Determine signature (simplified)
            func_signature_match = re.search(r'\(([^)]*)\)', match.group(0))
            func_signature = func_signature_match.group(1) if func_signature_match else ""
            
            doc_info["functions"][func_name] = {
                "signature": f"({func_signature})",
                "description": self._parse_js_comment(func_comment)
            }
        
        # Extract TypeScript interfaces
        if is_typescript:
            interface_pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[\w,\s]+)?\s*{([^}]*)}'
            for match in re.finditer(interface_pattern, content, re.DOTALL):
                interface_name = match.group(1)
                interface_content = match.group(2)
                
                # Extract interface comment
                interface_comment_match = re.search(r'/\*\*(.*?)\*/', match.group(0), re.DOTALL)
                interface_description = self._parse_js_comment(interface_comment_match.group(1)) if interface_comment_match else ""
                
                # Extract properties
                properties = {}
                property_pattern = r'(\w+)(?:\?)?:\s*([\w<>[\],\s|]+)(?:;)?\s*(?://\s*(.*))?'
                for prop_match in re.finditer(property_pattern, interface_content):
                    prop_name = prop_match.group(1)
                    prop_type = prop_match.group(2).strip()
                    prop_comment = prop_match.group(3) if prop_match.group(3) else ""
                    
                    properties[prop_name] = {
                        "type": prop_type,
                        "description": prop_comment.strip()
                    }
                
                doc_info["interfaces"][interface_name] = {
                    "description": interface_description,
                    "properties": properties
                }
        
        return doc_info
    
    def _parse_js_comment(self, comment: str) -> str:
        """
        Parse JSDoc comment.
        
        Args:
            comment: JSDoc comment
            
        Returns:
            Parsed description
        """
        # Remove * at the beginning of lines
        lines = [line.strip().lstrip('*') for line in comment.splitlines()]
        
        # Join and clean up
        description = " ".join(line for line in lines if line and not line.startswith('@'))
        
        return description.strip()
    
    def _generate_js_docs_index(self, directories: Dict[str, List[Dict[str, Any]]], project_name: str) -> str:
        """
        Generate index page for JavaScript/TypeScript API docs.
        
        Args:
            directories: Dictionary mapping directory names to files
            project_name: Name of the project
            
        Returns:
            Markdown content for index page
        """
        markdown = f"""# {project_name} API Documentation

## Modules

"""
        # Add directory links
        for dir_name, files in directories.items():
            if dir_name == "root":
                markdown += "### Root Module\n\n"
            else:
                markdown += f"### {dir_name}\n\n"
            
            for file_info in files:
                file_path = file_info.get("path", "")
                file_name = os.path.basename(file_path)
                doc_name = os.path.splitext(file_name)[0]
                
                markdown += f"- [{doc_name}](modules/{doc_name}.md)\n"
            
            markdown += "\n"
        
        return markdown
    
    async def _generate_java_api_docs(
        self, 
        project_path: Path,
        source_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate API documentation for a Java project.
        
        Args:
            project_path: Path to the project
            source_files: List of source files
            
        Returns:
            Dictionary with the generated API docs
        """
        self._logger.info("Generating Java API docs")
        
        # Filter for Java files
        java_files = [f for f in source_files if f.get("path", "").endswith(".java")]
        
        # Organize files by package
        packages = {}
        
        for file_info in java_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            if not content:
                continue
            
            # Extract package name
            package_match = re.search(r'package\s+([\w.]+);', content)
            if package_match:
                package_name = package_match.group(1)
            else:
                package_name = "default"
            
            if package_name not in packages:
                packages[package_name] = []
            packages[package_name].append(file_info)
        
        # Generate docs for each package
        package_docs = {}
        
        for package_name, files in packages.items():
            package_docs[package_name] = await self._generate_java_package_docs(package_name, files)
        
        # Create docs structure
        docs_structure = {
            "index.md": self._generate_java_docs_index(packages, project_path.name),
            "packages": package_docs
        }
        
        return {
            "structure": docs_structure,
            "format": "markdown",
            "project_path": str(project_path)
        }
    
    async def _generate_java_package_docs(
        self, 
        package_name: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate documentation for a Java package.
        
        Args:
            package_name: Name of the package
            files: List of files in the package
            
        Returns:
            Dictionary mapping file names to documentation content
        """
        package_docs = {}
        
        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            if not content:
                continue
            
            # Extract file name without extension
            file_name = os.path.basename(file_path)
            class_name = os.path.splitext(file_name)[0]
            
            # Parse Java content
            doc_content = await self._parse_java_file(file_path, content)
            
            # Generate markdown
            markdown = f"""# {class_name}

Package: `{package_name}`

{doc_content.get('class_javadoc', 'No description available.')}

"""
            # Add class info
            if "is_interface" in doc_content and doc_content["is_interface"]:
                markdown += "## Interface Methods\n\n"
            else:
                markdown += "## Methods\n\n"
            
            for method_name, method_info in doc_content.get("methods", {}).items():
                markdown += f"### `{method_name}{method_info.get('signature', '()') }`\n\n{method_info.get('javadoc', 'No description available.')}\n\n"
                
                # Add parameters documentation
                if method_info.get("params"):
                    markdown += "#### Parameters\n\n"
                    for param_name, param_desc in method_info.get("params", {}).items():
                        markdown += f"- `{param_name}` - {param_desc}\n"
                    markdown += "\n"
                
                # Add return documentation
                if method_info.get("returns"):
                    markdown += f"#### Returns\n\n{method_info.get('returns')}\n\n"
                
                # Add throws documentation
                if method_info.get("throws"):
                    markdown += "#### Throws\n\n"
                    for exception, desc in method_info.get("throws", {}).items():
                        markdown += f"- `{exception}` - {desc}\n"
                    markdown += "\n"
            
            # Add fields
            if doc_content.get("fields"):
                markdown += "## Fields\n\n"
                for field_name, field_info in doc_content.get("fields", {}).items():
                    markdown += f"### `{field_info.get('type', 'Object')} {field_name}`\n\n{field_info.get('javadoc', 'No description available.')}\n\n"
            
            package_docs[class_name + ".md"] = markdown
        
        return package_docs
    
    async def _parse_java_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Parse Java file for documentation.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Dictionary with parsed documentation
        """
        # Basic structure
        doc_info = {
            "class_javadoc": "",
            "methods": {},
            "fields": {}
        }
        
        # Check if it's an interface
        if re.search(r'(?:public\s+)?interface\s+\w+', content):
            doc_info["is_interface"] = True
        
        # Extract class javadoc
        class_javadoc_match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
        if class_javadoc_match:
            doc_info["class_javadoc"] = self._parse_javadoc(class_javadoc_match.group(1))
        
        # Extract methods
        method_pattern = r'(?:/\*\*(.*?)\*/\s*)?(?:public|private|protected)?\s+(?:static\s+)?(?:final\s+)?(?:[\w<>[\],\s]+)\s+(\w+)\s*\(([^)]*)\)(?:\s+throws\s+[\w,\s]+)?(?:\s*{)?'
        for match in re.finditer(method_pattern, content, re.DOTALL):
            javadoc = match.group(1)
            method_name = match.group(2)
            params_str = match.group(3)
            
            # Skip constructor if it has the same name as the class
            class_name = os.path.splitext(os.path.basename(file_path))[0]
            if method_name == class_name:
                continue
            
            # Parse javadoc
            javadoc_info = self._parse_javadoc_with_tags(javadoc) if javadoc else {}
            
            # Format parameters
            formatted_params = []
            for param in params_str.split(","):
                param = param.strip()
                if param:
                    parts = param.split()
                    if len(parts) >= 2:
                        param_type = " ".join(parts[:-1])
                        param_name = parts[-1]
                        formatted_params.append(f"{param_type} {param_name}")
            
            # Extract throws info
            throws_match = re.search(r'throws\s+([\w,\s]+)', match.group(0))
            throws = throws_match.group(1).split(",") if throws_match else []
            
            method_info = {
                "signature": f"({', '.join(formatted_params)})",
                "javadoc": javadoc_info.get("description", ""),
                "params": javadoc_info.get("params", {}),
                "returns": javadoc_info.get("returns", ""),
                "throws": javadoc_info.get("throws", {})
            }
            
            doc_info["methods"][method_name] = method_info
        
        # Extract fields
        field_pattern = r'(?:/\*\*(.*?)\*/\s*)?(?:public|private|protected)?\s+(?:static\s+)?(?:final\s+)?(?:[\w<>[\],\s]+)\s+(\w+)\s*(?:=\s*[^;]+)?;'
        for match in re.finditer(field_pattern, content, re.DOTALL):
            javadoc = match.group(1)
            field_declaration = match.group(0)
            
            # Extract field name and type
            field_name = match.group(2)
            
            # Extract field type
            type_match = re.search(r'(?:public|private|protected)?\s+(?:static\s+)?(?:final\s+)?([\w<>[\],\s]+)\s+\w+\s*(?:=|;)', field_declaration)
            field_type = type_match.group(1).strip() if type_match else "Object"
            
            # Parse javadoc
            field_javadoc = self._parse_javadoc(javadoc) if javadoc else ""
            
            doc_info["fields"][field_name] = {
                "type": field_type,
                "javadoc": field_javadoc
            }
        
        return doc_info
    
    def _parse_javadoc(self, javadoc: str) -> str:
        """
        Parse basic Javadoc comment.
        
        Args:
            javadoc: Javadoc comment
            
        Returns:
            Parsed description
        """
        if not javadoc:
            return ""
        
        # Remove * at the beginning of lines
        lines = [line.strip().lstrip('*') for line in javadoc.splitlines()]
        
        # Join and clean up
        description = " ".join(line for line in lines if line and not line.startswith('@'))
        
        return description.strip()
    
    def _parse_javadoc_with_tags(self, javadoc: str) -> Dict[str, Any]:
        """
        Parse Javadoc comment with tags.
        
        Args:
            javadoc: Javadoc comment
            
        Returns:
            Dictionary with parsed javadoc
        """
        if not javadoc:
            return {"description": ""}
        
        result = {
            "description": "",
            "params": {},
            "returns": "",
            "throws": {}
        }
        
        # Remove * at the beginning of lines
        lines = [line.strip().lstrip('*') for line in javadoc.splitlines()]
        
        # Extract description (text before tags)
        description_lines = []
        tag_lines = []
        in_description = True
        
        for line in lines:
            if line.startswith('@'):
                in_description = False
                tag_lines.append(line)
            elif in_description:
                description_lines.append(line)
            else:
                tag_lines.append(line)
        
        result["description"] = " ".join(line for line in description_lines if line).strip()
        
        # Process tags
        current_tag = None
        current_text = []
        
        for line in tag_lines:
            if line.startswith('@'):
                # Save previous tag
                if current_tag and current_text:
                    self._add_tag_to_result(result, current_tag, " ".join(current_text).strip())
                
                # Start new tag
                parts = line.split(' ', 1)
                current_tag = parts[0][1:]  # Remove @ and get tag name
                current_text = [parts[1].strip()] if len(parts) > 1 else []
            elif current_tag:
                current_text.append(line)
        
        # Save last tag
        if current_tag and current_text:
            self._add_tag_to_result(result, current_tag, " ".join(current_text).strip())
        
        return result
    
    def _add_tag_to_result(self, result: Dict[str, Any], tag: str, text: str) -> None:
        """
        Add a parsed javadoc tag to the result.
        
        Args:
            result: Result dictionary
            tag: Tag name
            text: Tag text
        """
        if tag == "param":
            # Extract parameter name
            parts = text.split(' ', 1)
            if len(parts) > 1:
                param_name = parts[0]
                param_description = parts[1]
                result["params"][param_name] = param_description
        elif tag == "return":
            result["returns"] = text
        elif tag in ["throws", "exception"]:
            # Extract exception class
            parts = text.split(' ', 1)
            if len(parts) > 1:
                exception_class = parts[0]
                exception_description = parts[1]
                result["throws"][exception_class] = exception_description
    
    def _generate_java_docs_index(self, packages: Dict[str, List[Dict[str, Any]]], project_name: str) -> str:
        """
        Generate index page for Java API docs.
        
        Args:
            packages: Dictionary mapping package names to files
            project_name: Name of the project
            
        Returns:
            Markdown content for index page
        """
        markdown = f"""# {project_name} API Documentation

## Packages

"""
        # Add package links
        for package_name, files in packages.items():
            markdown += f"### {package_name}\n\n"
            
            for file_info in files:
                file_path = file_info.get("path", "")
                file_name = os.path.basename(file_path)
                class_name = os.path.splitext(file_name)[0]
                
                markdown += f"- [{class_name}](packages/{class_name}.md)\n"
            
            markdown += "\n"
        
        return markdown
    
    async def _generate_generic_api_docs(
        self, 
        project_path: Path,
        source_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate generic API documentation for an unknown project type.
        
        Args:
            project_path: Path to the project
            source_files: List of source files
            
        Returns:
            Dictionary with the generated API docs
        """
        self._logger.info("Generating generic API docs")
        
        # Organize files by directory
        directories = {}
        
        for file_info in source_files:
            file_path = file_info.get("path", "")
            
            if "/" in file_path:
                # File in a directory
                dir_parts = file_path.split("/")
                dir_name = dir_parts[0]
                if dir_name not in directories:
                    directories[dir_name] = []
                directories[dir_name].append(file_info)
            else:
                # File in root
                dir_name = "root"
                if dir_name not in directories:
                    directories[dir_name] = []
                directories[dir_name].append(file_info)
        
        # Generate docs for each directory
        dir_docs = {}
        
        for dir_name, files in directories.items():
            dir_docs[dir_name] = await self._generate_generic_directory_docs(dir_name, files)
        
        # Create docs structure
        docs_structure = {
            "index.md": self._generate_generic_docs_index(directories, project_path.name),
            "modules": dir_docs
        }
        
        return {
            "structure": docs_structure,
            "format": "markdown",
            "project_path": str(project_path)
        }
    
    async def _generate_generic_directory_docs(
        self, 
        dir_name: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate documentation for a generic directory.
        
        Args:
            dir_name: Name of the directory
            files: List of files in the directory
            
        Returns:
            Dictionary mapping file names to documentation content
        """
        dir_docs = {}
        
        for file_info in files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            if not content:
                continue
            
            # Extract file name without extension
            file_name = os.path.basename(file_path)
            doc_name = os.path.splitext(file_name)[0]
            
            # Generate markdown using AI
            markdown = await self._generate_file_docs_with_ai(file_info)
            
            dir_docs[doc_name + ".md"] = markdown
        
        return dir_docs
    
    def _generate_generic_docs_index(self, directories: Dict[str, List[Dict[str, Any]]], project_name: str) -> str:
        """
        Generate index page for generic API docs.
        
        Args:
            directories: Dictionary mapping directory names to files
            project_name: Name of the project
            
        Returns:
            Markdown content for index page
        """
        markdown = f"""# {project_name} API Documentation

## Modules

"""
        # Add directory links
        for dir_name, files in directories.items():
            if dir_name == "root":
                markdown += "### Root Module\n\n"
            else:
                markdown += f"### {dir_name}\n\n"
            
            for file_info in files:
                file_path = file_info.get("path", "")
                file_name = os.path.basename(file_path)
                doc_name = os.path.splitext(file_name)[0]
                
                markdown += f"- [{doc_name}](modules/{doc_name}.md)\n"
            
            markdown += "\n"
        
        return markdown
    
    async def _generate_file_docs_with_ai(self, file_info: Dict[str, Any]) -> str:
        """
        Generate documentation for a file using AI.
        
        Args:
            file_info: File information
            
        Returns:
            Markdown documentation
        """
        file_path = file_info.get("path", "")
        content = file_info.get("content", "")
        language = file_info.get("language", "Unknown")
        
        # Build prompt for AI
        prompt = f"""
You are an expert technical writer tasked with documenting a {language} file.

File path: {file_path}

File content:
```
{content[:5000] if len(content) > 5000 else content}
```
{f"..." if len(content) > 5000 else ""}

Create comprehensive documentation in Markdown format for this file, including:
1. File overview/purpose
2. Main functions/classes/components
3. Usage examples (if applicable)
4. Any dependencies or relationships with other files (if detectable)

Follow these formatting guidelines:
- Use Markdown headings appropriately (# for title, ## for sections, etc.)
- Use code blocks with appropriate syntax highlighting
- Document parameters, return values, and exceptions where applicable
- Be concise but thorough

DO NOT reproduce the entire file content - focus on documenting functionality and usage.
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=3000,
            temperature=0.2
        )
        
        self._logger.debug(f"Sending file documentation request to AI for {file_path}")
        response = await gemini_client.generate_text(api_request)
        
        # Extract documentation
        return response.text
    
    def _build_user_guide_prompt(self, project_info: Dict[str, Any]) -> str:
        """
        Build a prompt for user guide generation.
        
        Args:
            project_info: Project information
            
        Returns:
            Prompt string for the AI service
        """
        prompt = f"""
You are an expert technical writer tasked with creating a comprehensive user guide for a {project_info.get('project_type', 'software')} project named "{project_info.get('name', 'Project')}".

Project details:
- Type: {project_info.get('project_type', 'Unknown')}
"""
        
        # Add dependencies information
        if "dependencies" in project_info:
            prompt += "- Dependencies:\n"
            
            if "runtime" in project_info["dependencies"]:
                runtime_deps = project_info["dependencies"]["runtime"]
                if runtime_deps:
                    prompt += f"  - Runtime: {', '.join(runtime_deps[:10])}"
                    if len(runtime_deps) > 10:
                        prompt += f" and {len(runtime_deps) - 10} more"
                    prompt += "\n"
        
        # Add entry points information
        if "entry_points" in project_info and project_info["entry_points"]:
            prompt += f"- Entry points: {', '.join(project_info['entry_points'])}\n"
        
        # Add important source files
        source_files = [f for f in project_info.get("files", []) if f.get("type") == "source_code"]
        if source_files:
            prompt += "- Important source files:\n"
            for file in source_files[:5]:  # Limit to 5 files
                prompt += f"  - {file.get('path')}\n"
        
        prompt += """
Create a comprehensive user guide that follows these best practices:
1. Introduction and overview
2. Getting started (installation, setup)
3. Basic usage
4. Advanced features
5. Troubleshooting
6. API/command reference
7. Examples and use cases

The user guide should be well-formatted with Markdown, including:
- Proper headings (# for main title, ## for sections, etc.)
- Code blocks with appropriate syntax highlighting
- Lists (ordered and unordered)
- Tables where appropriate
- Screenshots (described with placeholders)

Make the user guide user-friendly, comprehensive, and suitable for users with varying levels of technical expertise.
"""
        
        return prompt
    
    def _build_contributing_prompt(self, project_info: Dict[str, Any]) -> str:
        """
        Build a prompt for contributing guide generation.
        
        Args:
            project_info: Project information
            
        Returns:
            Prompt string for the AI service
        """
        prompt = f"""
You are an expert technical writer tasked with creating a comprehensive CONTRIBUTING.md file for a {project_info.get('project_type', 'software')} project named "{project_info.get('name', 'Project')}".

Project details:
- Type: {project_info.get('project_type', 'Unknown')}
"""
        
        # Add file structure information
        file_types = {}
        for file_info in project_info.get("files", []):
            file_type = file_info.get("type")
            if file_type:
                if file_type not in file_types:
                    file_types[file_type] = []
                file_types[file_type].append(file_info.get("path"))
        
        prompt += "- File structure summary:\n"
        for file_type, files in file_types.items():
            prompt += f"  - {file_type} files: {len(files)}\n"
        
        prompt += """
Create a comprehensive CONTRIBUTING.md file that follows these best practices:
1. Introduction and welcome message
2. Code of conduct reference
3. Getting started for contributors
4. Development environment setup
5. Coding standards and conventions
6. Pull request process
7. Issue reporting guidelines
8. Testing instructions
9. Documentation guidelines

The contributing guide should be well-formatted with Markdown, including:
- Proper headings (# for main title, ## for sections, etc.)
- Code blocks with appropriate syntax highlighting
- Lists (ordered and unordered)
- Links to important resources

Make the contributing guide friendly, comprehensive, and helpful for new contributors.
"""
        
        return prompt
    
    def _extract_markdown_content(self, content: str) -> str:
        """
        Extract markdown content from AI response.
        
        Args:
            content: AI response text
            
        Returns:
            Markdown content
        """
        # Check if content is already markdown
        if content.startswith('#') or content.startswith('# '):
            return content
        
        # Try to extract markdown from code blocks
        markdown_match = re.search(r'```(?:markdown)?\s*(.*?)\s*```', content, re.DOTALL)
        if markdown_match:
            return markdown_match.group(1)
        
        # Otherwise, just return the response
        return content

# Global documentation generator instance
documentation_generator = DocumentationGenerator()
