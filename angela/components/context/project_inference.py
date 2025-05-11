# angela/context/project_inference.py

import os
import glob
import json
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple

from angela.utils.logging import get_logger

logger = get_logger(__name__)

class ProjectInference:
    """
    Advanced project type and structure inference.
    
    This class provides:
    1. Detection of project type based on files and structure
    2. Inference of project dependencies
    3. Identification of important project files
    4. Framework and technology detection
    """
    
    # Project type signatures
    PROJECT_SIGNATURES = {
        "python": {
            "files": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "directories": ["venv", ".venv", "env", ".env"],
            "extensions": [".py", ".pyi", ".pyx"]
        },
        "node": {
            "files": ["package.json", "package-lock.json", "yarn.lock", "node_modules"],
            "extensions": [".js", ".jsx", ".ts", ".tsx"]
        },
        "rust": {
            "files": ["Cargo.toml", "Cargo.lock"],
            "directories": ["src", "target"],
            "extensions": [".rs"]
        },
        "go": {
            "files": ["go.mod", "go.sum"],
            "directories": ["pkg", "cmd"],
            "extensions": [".go"]
        },
        "java": {
            "files": ["pom.xml", "build.gradle", "gradlew", "settings.gradle"],
            "directories": ["src/main/java", "target", "build"],
            "extensions": [".java", ".class", ".jar"]
        },
        "dotnet": {
            "files": [".csproj", ".sln", "packages.config"],
            "directories": ["bin", "obj"],
            "extensions": [".cs", ".vb", ".fs"]
        },
        "php": {
            "files": ["composer.json", "composer.lock"],
            "directories": ["vendor"],
            "extensions": [".php"]
        },
        "ruby": {
            "files": ["Gemfile", "Gemfile.lock", "Rakefile"],
            "directories": ["lib", "bin"],
            "extensions": [".rb"]
        },
        "flutter": {
            "files": ["pubspec.yaml", "pubspec.lock"],
            "directories": ["lib", "android", "ios"],
            "extensions": [".dart"]
        },
        "docker": {
            "files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
            "extensions": []
        },
        "web": {
            "files": ["index.html", "style.css", "script.js"],
            "extensions": [".html", ".htm", ".css", ".js"]
        }
    }
    
    # Framework signatures
    FRAMEWORK_SIGNATURES = {
        "python": {
            "django": ["manage.py", "settings.py", "wsgi.py", "asgi.py"],
            "flask": ["app.py", "wsgi.py", "requirements.txt"],
            "fastapi": ["main.py", "app.py", "api.py"],
            "tornado": ["server.py", "app.py"],
            "sqlalchemy": ["models.py", "database.py"],
            "pytest": ["conftest.py", "test_*.py", "pytest.ini"],
            "jupyter": [".ipynb"],
            "pandas": ["*.csv", "*.xlsx"],
            "tensorflow": ["model.h5", "keras"]
        },
        "node": {
            "react": ["react", "jsx", "tsx", "components"],
            "vue": ["vue.config.js", "Vue", "components"],
            "angular": ["angular.json", "app.module.ts"],
            "express": ["app.js", "routes", "middleware"],
            "nextjs": ["next.config.js", "pages", "public"],
            "gatsby": ["gatsby-config.js", "gatsby-node.js"],
            "electron": ["electron", "main.js", "renderer.js"]
        },
        "web": {
            "bootstrap": ["bootstrap"],
            "tailwind": ["tailwind.config.js", "tailwindcss"],
            "jquery": ["jquery"]
        }
    }
    
    def __init__(self):
        """Initialize the project inference system."""
        self._logger = logger
        self._cache = {}  # Cache inference results
    
    async def infer_project_info(self, project_root: Path) -> Dict[str, Any]:
        """
        Infer detailed information about a project.
        
        Args:
            project_root: The project root directory
            
        Returns:
            Dictionary with project information
        """
        # Check cache first
        cache_key = str(project_root)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        self._logger.info(f"Inferring project information for {project_root}")
        
        # Basic project type detection
        project_type = await self._detect_project_type(project_root)
        
        # Get more detailed information
        result = {
            "project_root": str(project_root),
            "project_type": project_type,
            "detected_files": await self._list_important_files(project_root, project_type),
            "detected_frameworks": await self._detect_frameworks(project_root, project_type),
            "dependencies": await self._detect_dependencies(project_root, project_type),
            "structure": await self._analyze_project_structure(project_root, project_type)
        }
        
        # Cache the result
        self._cache[cache_key] = result
        
        return result
    
    async def _detect_project_type(self, project_root: Path) -> str:
        """
        Detect the primary type of a project.
        
        Args:
            project_root: The project root directory
            
        Returns:
            Project type string
        """
        # Count signature matches for each project type
        scores = {}
        
        for project_type, signature in self.PROJECT_SIGNATURES.items():
            score = 0
            
            # Check for signature files
            for file_pattern in signature.get("files", []):
                # Handle glob patterns
                if "*" in file_pattern:
                    matches = list(project_root.glob(file_pattern))
                    score += len(matches)
                else:
                    if (project_root / file_pattern).exists():
                        score += 3  # Higher weight for exact file matches
                        
            # Check for signature directories
            for dir_pattern in signature.get("directories", []):
                # Handle glob patterns
                if "*" in dir_pattern:
                    matches = list(project_root.glob(dir_pattern))
                    score += len(matches)
                else:
                    if (project_root / dir_pattern).exists() and (project_root / dir_pattern).is_dir():
                        score += 2  # Medium weight for directory matches
            
            # Check for file extensions
            for ext in signature.get("extensions", []):
                # Count files with this extension
                count = len(list(project_root.glob(f"**/*{ext}")))
                score += min(count, 10)  # Cap at 10 to avoid skewing
            
            scores[project_type] = score
        
        # Get the project type with the highest score
        if not scores:
            return "unknown"
        
        # If multiple project types have similar scores, handle mixed projects
        max_score = max(scores.values())
        candidates = [pt for pt, score in scores.items() if score >= max_score * 0.7]
        
        if len(candidates) > 1:
            # Special case: For web + node, prefer node as it's more specific
            if "web" in candidates and "node" in candidates:
                return "node"
            
            # Return composite project type for truly mixed projects
            return "+".join(candidates)
        
        # Return the highest scoring project type
        return max(scores.items(), key=lambda x: x[1])[0]
    
    async def _list_important_files(self, project_root: Path, project_type: str) -> List[Dict[str, Any]]:
        """
        List important files in the project.
        
        Args:
            project_root: The project root directory
            project_type: The detected project type
            
        Returns:
            List of important file information
        """
        important_files = []
        
        # Handle composite project types
        if "+" in project_type:
            types = project_type.split("+")
            for pt in types:
                important_files.extend(await self._list_important_files(project_root, pt))
            return important_files
        
        # Get signatures for this project type
        signature = self.PROJECT_SIGNATURES.get(project_type, {})
        
        # Check for signature files
        for file_pattern in signature.get("files", []):
            # Handle glob patterns
            if "*" in file_pattern:
                for file_path in project_root.glob(file_pattern):
                    if file_path.is_file():
                        important_files.append({
                            "path": str(file_path.relative_to(project_root)),
                            "type": "signature_file",
                            "project_type": project_type
                        })
            else:
                file_path = project_root / file_pattern
                if file_path.exists() and file_path.is_file():
                    important_files.append({
                        "path": str(file_path.relative_to(project_root)),
                        "type": "signature_file",
                        "project_type": project_type
                    })
        
        # Add common important files for any project
        common_files = ["README.md", "LICENSE", ".gitignore", "CHANGELOG.md"]
        for file_name in common_files:
            file_path = project_root / file_name
            if file_path.exists() and file_path.is_file():
                important_files.append({
                    "path": file_name,
                    "type": "documentation"
                })
        
        # Add project-specific logic
        if project_type == "python":
            # Look for main Python modules
            for file_path in project_root.glob("**/*.py"):
                if file_path.name == "__main__.py" or file_path.name == "main.py":
                    important_files.append({
                        "path": str(file_path.relative_to(project_root)),
                        "type": "entry_point"
                    })
        
        elif project_type == "node":
            # Look for main JavaScript/TypeScript files
            for pattern in ["index.js", "main.js", "server.js", "app.js", "index.ts", "main.ts"]:
                for file_path in project_root.glob(f"**/{pattern}"):
                    # Skip node_modules
                    if "node_modules" not in str(file_path):
                        important_files.append({
                            "path": str(file_path.relative_to(project_root)),
                            "type": "entry_point"
                        })
        
        # Add more project-specific logic as needed
        
        return important_files
    
    async def _detect_frameworks(self, project_root: Path, project_type: str) -> Dict[str, float]:
        """
        Detect frameworks and technologies used in the project.
        
        Args:
            project_root: The project root directory
            project_type: The detected project type
            
        Returns:
            Dictionary of framework names and confidence scores
        """
        frameworks = {}
        
        # Handle composite project types
        if "+" in project_type:
            types = project_type.split("+")
            for pt in types:
                frameworks.update(await self._detect_frameworks(project_root, pt))
            return frameworks
        
        # Get framework signatures for this project type
        if project_type in self.FRAMEWORK_SIGNATURES:
            for framework, patterns in self.FRAMEWORK_SIGNATURES[project_type].items():
                matches = 0
                total_patterns = len(patterns)
                
                for pattern in patterns:
                    # Handle glob patterns
                    if "*" in pattern:
                        files = list(project_root.glob(f"**/{pattern}"))
                        if files:
                            matches += 1
                    else:
                        # Check for exact file match
                        for file_path in project_root.glob("**/*"):
                            if pattern in file_path.name or pattern in str(file_path):
                                matches += 1
                                break
                
                # Calculate confidence score
                if total_patterns > 0 and matches > 0:
                    confidence = min(matches / total_patterns, 1.0)
                    if confidence >= 0.3:  # Threshold for reporting
                        frameworks[framework] = confidence
        
        # Check dependencies if we have appropriate files
        if project_type == "python":
            requirements_path = project_root / "requirements.txt"
            if requirements_path.exists():
                frameworks.update(await self._analyze_python_requirements(requirements_path))
            
        elif project_type == "node":
            package_json_path = project_root / "package.json"
            if package_json_path.exists():
                frameworks.update(await self._analyze_package_json(package_json_path))
        
        return frameworks
    
    async def _detect_dependencies(self, project_root: Path, project_type: str) -> List[Dict[str, Any]]:
        """
        Detect dependencies of the project.
        
        Args:
            project_root: The project root directory
            project_type: The detected project type
            
        Returns:
            List of dependencies with metadata
        """
        dependencies = []
        
        # Handle composite project types
        if "+" in project_type:
            types = project_type.split("+")
            for pt in types:
                dependencies.extend(await self._detect_dependencies(project_root, pt))
            return dependencies
        
        # Extract dependencies based on project type
        if project_type == "python":
            # Check requirements.txt
            requirements_path = project_root / "requirements.txt"
            if requirements_path.exists():
                dependencies.extend(await self._extract_python_requirements(requirements_path))
            
            # Check setup.py
            setup_py_path = project_root / "setup.py"
            if setup_py_path.exists():
                dependencies.extend(await self._extract_python_setup_dependencies(setup_py_path))
                
            # Check pyproject.toml
            pyproject_path = project_root / "pyproject.toml"
            if pyproject_path.exists():
                dependencies.extend(await self._extract_pyproject_dependencies(pyproject_path))
                
        elif project_type == "node":
            # Check package.json
            package_json_path = project_root / "package.json"
            if package_json_path.exists():
                dependencies.extend(await self._extract_node_dependencies(package_json_path))
                
        # Add more project types as needed
        
        return dependencies
    
    async def _analyze_project_structure(self, project_root: Path, project_type: str) -> Dict[str, Any]:
        """
        Analyze the structure of the project.
        
        Args:
            project_root: The project root directory
            project_type: The detected project type
            
        Returns:
            Dictionary with structure information
        """
        # Count files by type
        file_counts = {}
        
        # Walk the directory tree
        for root, dirs, files in os.walk(project_root):
            # Skip hidden directories and common exclude patterns
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "venv", "__pycache__", "build", "dist"]]
            
            for file in files:
                # Get file extension
                _, ext = os.path.splitext(file)
                if ext:
                    if ext not in file_counts:
                        file_counts[ext] = 0
                    file_counts[ext] += 1
        
        # Identify main directories
        main_dirs = []
        for item in project_root.iterdir():
            if item.is_dir() and not item.name.startswith(".") and item.name not in ["node_modules", "venv", "__pycache__"]:
                main_dirs.append({
                    "name": item.name,
                    "path": str(item.relative_to(project_root)),
                    "file_count": sum(1 for _ in item.glob("**/*") if _.is_file())
                })
        
        # Sort by file count
        main_dirs.sort(key=lambda x: x["file_count"], reverse=True)
        
        return {
            "file_counts": file_counts,
            "main_directories": main_dirs[:5],  # Top 5 directories
            "total_files": sum(file_counts.values()),
            "directory_structure": await self._generate_directory_structure(project_root)
        }
    
    async def _generate_directory_structure(self, project_root: Path, max_depth: int = 3) -> Dict[str, Any]:
        """
        Generate a hierarchical representation of the directory structure.
        
        Args:
            project_root: The project root directory
            max_depth: Maximum depth to traverse
            
        Returns:
            Dictionary representing the directory structure
        """
        def _build_tree(path: Path, current_depth: int) -> Dict[str, Any]:
            if current_depth > max_depth:
                return {"type": "directory", "name": path.name, "truncated": True}
            
            result = {"type": "directory", "name": path.name, "children": []}
            
            try:
                # List directory contents
                items = list(path.iterdir())
                
                # Skip large directories
                if len(items) > 50:
                    result["children"].append({"type": "info", "name": f"{len(items)} items (too many to show)"})
                    return result
                
                # Add directories first
                for item in sorted([i for i in items if i.is_dir()], key=lambda x: x.name):
                    # Skip hidden directories and common excludes
                    if item.name.startswith(".") or item.name in ["node_modules", "venv", "__pycache__", "build", "dist"]:
                        continue
                    
                    child = _build_tree(item, current_depth + 1)
                    result["children"].append(child)
                
                # Then add files
                for item in sorted([i for i in items if i.is_file()], key=lambda x: x.name):
                    # Skip hidden files
                    if item.name.startswith("."):
                        continue
                    
                    result["children"].append({"type": "file", "name": item.name})
                
                return result
            except PermissionError:
                result["children"].append({"type": "error", "name": "Permission denied"})
                return result
        
        return _build_tree(project_root, 0)
    
    async def _analyze_python_requirements(self, requirements_path: Path) -> Dict[str, float]:
        """
        Analyze Python requirements.txt for frameworks.
        
        Args:
            requirements_path: Path to requirements.txt
            
        Returns:
            Dictionary of framework names and confidence scores
        """
        frameworks = {}
        
        # Framework indicators in requirements
        framework_indicators = {
            "django": "django",
            "flask": "flask",
            "fastapi": "fastapi",
            "tornado": "tornado",
            "sqlalchemy": "sqlalchemy",
            "pytest": "pytest",
            "pandas": "pandas",
            "numpy": "numpy",
            "tensorflow": "tensorflow",
            "pytorch": "torch",
            "jupyter": "jupyter"
        }
        
        try:
            with open(requirements_path, "r") as f:
                requirements = f.read()
                
            for framework, indicator in framework_indicators.items():
                pattern = rf"\b{re.escape(indicator)}[>=<~!]"
                if re.search(pattern, requirements, re.IGNORECASE):
                    frameworks[framework] = 1.0  # High confidence for direct dependencies
        except Exception as e:
            self._logger.error(f"Error analyzing requirements.txt: {str(e)}")
        
        return frameworks
    
    async def _analyze_package_json(self, package_json_path: Path) -> Dict[str, float]:
        """
        Analyze package.json for frameworks.
        
        Args:
            package_json_path: Path to package.json
            
        Returns:
            Dictionary of framework names and confidence scores
        """
        frameworks = {}
        
        # Framework indicators in package.json
        framework_indicators = {
            "react": ["react", "react-dom"],
            "vue": ["vue"],
            "angular": ["@angular/core"],
            "express": ["express"],
            "nextjs": ["next"],
            "gatsby": ["gatsby"],
            "electron": ["electron"]
        }
        
        try:
            with open(package_json_path, "r") as f:
                package_data = json.load(f)
            
            # Check dependencies and devDependencies
            all_deps = {}
            all_deps.update(package_data.get("dependencies", {}))
            all_deps.update(package_data.get("devDependencies", {}))
            
            for framework, indicators in framework_indicators.items():
                if any(dep in all_deps for dep in indicators):
                    frameworks[framework] = 1.0  # High confidence for direct dependencies
        except Exception as e:
            self._logger.error(f"Error analyzing package.json: {str(e)}")
        
        return frameworks
    
    async def _extract_python_requirements(self, requirements_path: Path) -> List[Dict[str, Any]]:
        """
        Extract dependencies from requirements.txt.
        
        Args:
            requirements_path: Path to requirements.txt
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        try:
            with open(requirements_path, "r") as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    
                    # Parse requirement
                    parts = re.split(r"[>=<~!]", line, 1)
                    name = parts[0].strip()
                    version_spec = line[len(name):].strip() if len(parts) > 1 else ""
                    
                    dependencies.append({
                        "name": name,
                        "version_spec": version_spec,
                        "type": "python",
                        "source": "requirements.txt"
                    })
        except Exception as e:
            self._logger.error(f"Error extracting Python requirements: {str(e)}")
        
        return dependencies
    
    async def _extract_python_setup_dependencies(self, setup_py_path: Path) -> List[Dict[str, Any]]:
        """
        Extract dependencies from setup.py.
        
        Args:
            setup_py_path: Path to setup.py
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        try:
            with open(setup_py_path, "r") as f:
                setup_content = f.read()
            
            # Look for install_requires
            install_requires_match = re.search(r"install_requires\s*=\s*\[(.*?)\]", setup_content, re.DOTALL)
            if install_requires_match:
                requires_text = install_requires_match.group(1)
                
                # Extract individual requirements
                for req_match in re.finditer(r"[\"']([^\"']+)[\"']", requires_text):
                    req = req_match.group(1)
                    
                    # Parse requirement
                    parts = re.split(r"[>=<~!]", req, 1)
                    name = parts[0].strip()
                    version_spec = req[len(name):].strip() if len(parts) > 1 else ""
                    
                    dependencies.append({
                        "name": name,
                        "version_spec": version_spec,
                        "type": "python",
                        "source": "setup.py"
                    })
        except Exception as e:
            self._logger.error(f"Error extracting setup.py dependencies: {str(e)}")
        
        return dependencies
    
    async def _extract_pyproject_dependencies(self, pyproject_path: Path) -> List[Dict[str, Any]]:
        """
        Extract dependencies from pyproject.toml.
        
        Args:
            pyproject_path: Path to pyproject.toml
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        try:
            # Simple parsing of dependencies from pyproject.toml
            with open(pyproject_path, "r") as f:
                content = f.read()
            
            # Look for dependencies section
            deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if deps_match:
                deps_text = deps_match.group(1)
                
                # Extract individual dependencies
                for dep_match in re.finditer(r"[\"']([^\"']+)[\"']", deps_text):
                    dep = dep_match.group(1)
                    
                    # Parse requirement
                    parts = re.split(r"[>=<~!]", dep, 1)
                    name = parts[0].strip()
                    version_spec = dep[len(name):].strip() if len(parts) > 1 else ""
                    
                    dependencies.append({
                        "name": name,
                        "version_spec": version_spec,
                        "type": "python",
                        "source": "pyproject.toml"
                    })
        except Exception as e:
            self._logger.error(f"Error extracting pyproject.toml dependencies: {str(e)}")
        
        return dependencies
    
    async def _extract_node_dependencies(self, package_json_path: Path) -> List[Dict[str, Any]]:
        """
        Extract dependencies from package.json.
        
        Args:
            package_json_path: Path to package.json
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        try:
            with open(package_json_path, "r") as f:
                package_data = json.load(f)
            
            # Process dependencies
            for dep_type in ["dependencies", "devDependencies"]:
                deps = package_data.get(dep_type, {})
                for name, version in deps.items():
                    dependencies.append({
                        "name": name,
                        "version_spec": version,
                        "type": "node",
                        "dev": dep_type == "devDependencies",
                        "source": "package.json"
                    })
        except Exception as e:
            self._logger.error(f"Error extracting Node.js dependencies: {str(e)}")
        
        return dependencies

# Global project inference instance
project_inference = ProjectInference()
