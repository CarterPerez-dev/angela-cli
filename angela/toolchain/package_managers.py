# angela/toolchain/package_managers.py

"""
Package manager integration for Angela CLI.

This module provides functionality for interacting with package managers
to install dependencies required by generated code.
"""
import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import re

from angela.utils.logging import get_logger
from angela.execution.engine import execution_engine
from angela.context import context_manager

logger = get_logger(__name__)

class PackageManagerIntegration:
    """
    Integration with package managers for dependency management.
    """
    
    def __init__(self):
        """Initialize the package manager integration."""
        self._logger = logger
        
        # Map of project types to package managers
        self._package_managers = {
            "python": ["pip", "pipenv", "poetry"],
            "node": ["npm", "yarn", "pnpm"],
            "ruby": ["gem", "bundler"],
            "php": ["composer"],
            "go": ["go"],
            "rust": ["cargo"],
            "java": ["maven", "gradle"]
        }
    
    async def detect_package_manager(
        self, 
        path: Union[str, Path],
        project_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect the package manager used in a project.
        
        Args:
            path: Path to the project
            project_type: Optional type of project
            
        Returns:
            Dictionary with the detected package manager info
        """
        self._logger.info(f"Detecting package manager in {path}")
        
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists() or not path_obj.is_dir():
            return {
                "detected": False,
                "error": f"Path does not exist or is not a directory: {path}",
                "package_manager": None,
                "project_type": project_type
            }
        
        # Determine project type if not provided
        if project_type is None:
            # Try to detect from context
            context = context_manager.get_context_dict()
            if context.get("project_type"):
                project_type = context["project_type"]
            else:
                # Try to infer from files
                project_type = await self._infer_project_type(path_obj)
        
        # Files that indicate package managers
        package_manager_files = {
            "python": {
                "requirements.txt": "pip",
                "Pipfile": "pipenv",
                "pyproject.toml": "poetry"  # Could also be other tools
            },
            "node": {
                "package.json": "npm",  # Could also be yarn or pnpm
                "yarn.lock": "yarn",
                "pnpm-lock.yaml": "pnpm"
            },
            "ruby": {
                "Gemfile": "bundler"
            },
            "php": {
                "composer.json": "composer"
            },
            "go": {
                "go.mod": "go"
            },
            "rust": {
                "Cargo.toml": "cargo"
            },
            "java": {
                "pom.xml": "maven",
                "build.gradle": "gradle",
                "build.gradle.kts": "gradle"
            }
        }
        
        # Check for package manager files based on project type
        if project_type in package_manager_files:
            for file_name, manager in package_manager_files[project_type].items():
                if (path_obj / file_name).exists():
                    # For Python, check if poetry is actually used in pyproject.toml
                    if file_name == "pyproject.toml" and manager == "poetry":
                        # Check if [tool.poetry] section exists
                        try:
                            with open(path_obj / file_name, 'r') as f:
                                content = f.read()
                                if "[tool.poetry]" not in content:
                                    # Might be another tool, default to pip
                                    manager = "pip"
                        except Exception:
                            manager = "pip"
                    
                    # For Node.js, check if yarn or pnpm is used
                    if file_name == "package.json" and manager == "npm":
                        # If yarn.lock or pnpm-lock.yaml exists, use that instead
                        if (path_obj / "yarn.lock").exists():
                            manager = "yarn"
                        elif (path_obj / "pnpm-lock.yaml").exists():
                            manager = "pnpm"
                    
                    return {
                        "detected": True,
                        "package_manager": manager,
                        "project_type": project_type,
                        "indicator_file": file_name
                    }
        
        # If no specific package manager detected, use default for project type
        if project_type in self._package_managers:
            default_manager = self._package_managers[project_type][0]
            return {
                "detected": False,
                "package_manager": default_manager,
                "project_type": project_type,
                "indicator_file": None,
                "message": f"No package manager detected, defaulting to {default_manager}"
            }
        
        return {
            "detected": False,
            "error": f"Unable to detect package manager for project type: {project_type}",
            "package_manager": None,
            "project_type": project_type
        }
    
    async def install_dependencies(
        self, 
        path: Union[str, Path],
        dependencies: List[str],
        dev_dependencies: Optional[List[str]] = None,
        package_manager: Optional[str] = None,
        project_type: Optional[str] = None,
        update_dependency_file: bool = True,
        virtual_env: bool = False
    ) -> Dict[str, Any]:
        """
        Install dependencies using the appropriate package manager.
        
        Args:
            path: Path to the project
            dependencies: List of dependencies to install
            dev_dependencies: Optional list of development dependencies
            package_manager: Optional package manager to use
            project_type: Optional project type
            update_dependency_file: Whether to update dependency file
            virtual_env: Whether to use a virtual environment for Python
            
        Returns:
            Dictionary with the installation result
        """
        self._logger.info(f"Installing dependencies in {path}")
        
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists() or not path_obj.is_dir():
            return {
                "success": False,
                "error": f"Path does not exist or is not a directory: {path}",
                "package_manager": package_manager,
                "project_type": project_type
            }
        
        # Detect package manager if not provided
        if package_manager is None or project_type is None:
            detection_result = await self.detect_package_manager(path_obj, project_type)
            package_manager = detection_result.get("package_manager")
            project_type = detection_result.get("project_type")
            
            if not package_manager:
                return {
                    "success": False,
                    "error": f"Unable to detect package manager: {detection_result.get('error', 'Unknown error')}",
                    "package_manager": None,
                    "project_type": project_type
                }
        
        # Install dependencies based on package manager
        if package_manager == "pip":
            return await self._install_pip_dependencies(
                path_obj, dependencies, dev_dependencies, update_dependency_file, virtual_env
            )
        elif package_manager == "npm":
            return await self._install_npm_dependencies(
                path_obj, dependencies, dev_dependencies, update_dependency_file
            )
        elif package_manager == "yarn":
            return await self._install_yarn_dependencies(
                path_obj, dependencies, dev_dependencies, update_dependency_file
            )
        elif package_manager == "poetry":
            return await self._install_poetry_dependencies(
                path_obj, dependencies, dev_dependencies, update_dependency_file
            )
        elif package_manager == "cargo":
            return await self._install_cargo_dependencies(
                path_obj, dependencies, dev_dependencies, update_dependency_file
            )
        # Add other package managers as needed
        
        return {
            "success": False,
            "error": f"Unsupported package manager: {package_manager}",
            "package_manager": package_manager,
            "project_type": project_type
        }
    
    async def _install_pip_dependencies(
        self, 
        path: Path,
        dependencies: List[str],
        dev_dependencies: Optional[List[str]] = None,
        update_dependency_file: bool = True,
        virtual_env: bool = False
    ) -> Dict[str, Any]:
        """
        Install Python dependencies using pip.
        
        Args:
            path: Path to the project
            dependencies: List of dependencies to install
            dev_dependencies: Optional list of development dependencies
            update_dependency_file: Whether to update requirements.txt
            virtual_env: Whether to use a virtual environment
            
        Returns:
            Dictionary with the installation result
        """
        self._logger.info(f"Installing Python dependencies with pip in {path}")
        
        results = {
            "success": True,
            "package_manager": "pip",
            "project_type": "python",
            "commands": [],
            "outputs": [],
            "errors": []
        }
        
        # Create virtual environment if requested
        if virtual_env and not (path / "venv").exists():
            venv_command = "python -m venv venv"
            venv_stdout, venv_stderr, venv_code = await execution_engine.execute_command(
                venv_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(venv_command)
            results["outputs"].append(venv_stdout)
            
            if venv_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to create virtual environment: {venv_stderr}")
                return results
        
        # Determine pip command
        pip_cmd = "venv/bin/pip" if virtual_env and (path / "venv").exists() else "pip"
        
        # Install dependencies
        if dependencies:
            deps_str = " ".join(dependencies)
            install_command = f"{pip_cmd} install {deps_str}"
            
            install_stdout, install_stderr, install_code = await execution_engine.execute_command(
                install_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(install_command)
            results["outputs"].append(install_stdout)
            
            if install_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to install dependencies: {install_stderr}")
                return results
        
        # Install dev dependencies
        if dev_dependencies:
            dev_deps_str = " ".join(dev_dependencies)
            dev_install_command = f"{pip_cmd} install {dev_deps_str}"
            
            dev_stdout, dev_stderr, dev_code = await execution_engine.execute_command(
                dev_install_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(dev_install_command)
            results["outputs"].append(dev_stdout)
            
            if dev_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to install dev dependencies: {dev_stderr}")
                return results
        
        # Update requirements.txt if requested
        if update_dependency_file:
            # Check if requirements.txt already exists
            req_file = path / "requirements.txt"
            existing_deps = []
            
            if req_file.exists():
                try:
                    with open(req_file, 'r') as f:
                        existing_deps = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                except Exception as e:
                    results["errors"].append(f"Failed to read requirements.txt: {str(e)}")
            
            # Combine existing and new dependencies
            all_deps = list(set(existing_deps + dependencies))
            
            # Write back to requirements.txt
            try:
                with open(req_file, 'w') as f:
                    for dep in sorted(all_deps):
                        f.write(f"{dep}\n")
                
                results["updated_files"] = [str(req_file)]
            except Exception as e:
                results["errors"].append(f"Failed to update requirements.txt: {str(e)}")
        
        return results
    
    async def _install_npm_dependencies(
        self, 
        path: Path,
        dependencies: List[str],
        dev_dependencies: Optional[List[str]] = None,
        update_dependency_file: bool = True
    ) -> Dict[str, Any]:
        """
        Install Node.js dependencies using npm.
        
        Args:
            path: Path to the project
            dependencies: List of dependencies to install
            dev_dependencies: Optional list of development dependencies
            update_dependency_file: Whether to update package.json
            
        Returns:
            Dictionary with the installation result
        """
        self._logger.info(f"Installing Node.js dependencies with npm in {path}")
        
        results = {
            "success": True,
            "package_manager": "npm",
            "project_type": "node",
            "commands": [],
            "outputs": [],
            "errors": []
        }
        
        # Initialize npm project if package.json doesn't exist
        package_json = path / "package.json"
        if not package_json.exists() and update_dependency_file:
            init_command = "npm init -y"
            init_stdout, init_stderr, init_code = await execution_engine.execute_command(
                init_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(init_command)
            results["outputs"].append(init_stdout)
            
            if init_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to initialize npm project: {init_stderr}")
                return results
        
        # Install dependencies
        if dependencies:
            deps_str = " ".join(dependencies)
            install_command = f"npm install --save {deps_str}"
            
            install_stdout, install_stderr, install_code = await execution_engine.execute_command(
                install_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(install_command)
            results["outputs"].append(install_stdout)
            
            if install_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to install dependencies: {install_stderr}")
                return results
        
        # Install dev dependencies
        if dev_dependencies:
            dev_deps_str = " ".join(dev_dependencies)
            dev_install_command = f"npm install --save-dev {dev_deps_str}"
            
            dev_stdout, dev_stderr, dev_code = await execution_engine.execute_command(
                dev_install_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(dev_install_command)
            results["outputs"].append(dev_stdout)
            
            if dev_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to install dev dependencies: {dev_stderr}")
                return results
        
        # Update package.json directly if using npm doesn't work
        if update_dependency_file and package_json.exists() and (dependencies or dev_dependencies):
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                # Make sure dependencies sections exist
                if dependencies and "dependencies" not in package_data:
                    package_data["dependencies"] = {}
                
                if dev_dependencies and "devDependencies" not in package_data:
                    package_data["devDependencies"] = {}
                
                # Update package.json
                with open(package_json, 'w') as f:
                    json.dump(package_data, f, indent=2)
                
                results["updated_files"] = [str(package_json)]
            except Exception as e:
                results["errors"].append(f"Failed to update package.json: {str(e)}")
        
        return results
    
    async def _install_yarn_dependencies(
        self, 
        path: Path,
        dependencies: List[str],
        dev_dependencies: Optional[List[str]] = None,
        update_dependency_file: bool = True # This param is not directly used by yarn add
                                            # as it always updates package.json and yarn.lock
    ) -> Dict[str, Any]:
        """
        Install Node.js dependencies using yarn.
        
        Args:
            path: Path to the project
            dependencies: List of dependencies to install
            dev_dependencies: Optional list of development dependencies
            update_dependency_file: Whether to update package.json (yarn add does this by default)
            
        Returns:
            Dictionary with the installation result
        """
        self._logger.info(f"Installing Node.js dependencies with yarn in {path}")
        
        results = {
            "success": True,
            "package_manager": "yarn",
            "project_type": "node",
            "commands": [],
            "outputs": [],
            "errors": []
        }
        
        # Initialize yarn project if package.json doesn't exist
        package_json = path / "package.json"
        if not package_json.exists(): # Yarn init creates package.json
            init_command = "yarn init -y"
            init_stdout, init_stderr, init_code = await execution_engine.execute_command(
                init_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(init_command)
            results["outputs"].append(init_stdout)
            
            if init_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to initialize yarn project: {init_stderr}")
                return results
        
        # Install dependencies
        if dependencies:
            deps_str = " ".join(dependencies)
            install_command = f"yarn add {deps_str}"
            
            install_stdout, install_stderr, install_code = await execution_engine.execute_command(
                install_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(install_command)
            results["outputs"].append(install_stdout)
            
            if install_code != 0:
                results["success"] = False # Fixed: Added = False
                results["errors"].append(f"Failed to install dependencies: {install_stderr}") # Fixed: Added error reporting
                return results # Fixed: Added early return
        
        # Install dev dependencies
        if dev_dependencies:
            dev_deps_str = " ".join(dev_dependencies)
            dev_install_command = f"yarn add --dev {dev_deps_str}" # or yarn add -D
            
            dev_stdout, dev_stderr, dev_code = await execution_engine.execute_command(
                dev_install_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(dev_install_command)
            results["outputs"].append(dev_stdout)
            
            if dev_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to install dev dependencies: {dev_stderr}")
                return results
        
        if update_dependency_file and package_json.exists():
             results["updated_files"] = [str(package_json), str(path / "yarn.lock")]

        return results
    
    async def _install_poetry_dependencies(
        self, 
        path: Path,
        dependencies: List[str],
        dev_dependencies: Optional[List[str]] = None,
        update_dependency_file: bool = True
    ) -> Dict[str, Any]:
        """
        Install Python dependencies using Poetry.
        
        Args:
            path: Path to the project
            dependencies: List of dependencies to install
            dev_dependencies: Optional list of development dependencies
            update_dependency_file: Whether to update pyproject.toml
            
        Returns:
            Dictionary with the installation result
        """
        self._logger.info(f"Installing Python dependencies with Poetry in {path}")
        
        results = {
            "success": True,
            "package_manager": "poetry",
            "project_type": "python",
            "commands": [],
            "outputs": [],
            "errors": []
        }
        
        # Initialize poetry project if pyproject.toml doesn't exist
        pyproject_toml = path / "pyproject.toml"
        if not pyproject_toml.exists() and update_dependency_file:
            init_command = "poetry init --no-interaction"
            init_stdout, init_stderr, init_code = await execution_engine.execute_command(
                init_command,
                check_safety=True,
                working_dir=str(path)
            )
            
            results["commands"].append(init_command)
            results["outputs"].append(init_stdout)
            
            if init_code != 0:
                results["success"] = False
                results["errors"].append(f"Failed to initialize Poetry project: {init_stderr}")
                return results
        
        # Install dependencies
        if dependencies:
            for dep in dependencies:
                install_command = f"poetry add {dep}"
                
                install_stdout, install_stderr, install_code = await execution_engine.execute_command(
                    install_command,
                    check_safety=True,
                    working_dir=str(path)
                )
                
                results["commands"].append(install_command)
                results["outputs"].append(install_stdout)
                
                if install_code != 0:
                    results["success"] = False
                    results["errors"].append(f"Failed to install dependency {dep}: {install_stderr}")
                    return results
        
        # Install dev dependencies
        if dev_dependencies:
            for dev_dep in dev_dependencies:
                dev_install_command = f"poetry add --dev {dev_dep}"
                
                dev_stdout, dev_stderr, dev_code = await execution_engine.execute_command(
                    dev_install_command,
                    check_safety=True,
                    working_dir=str(path)
                )
                
                results["commands"].append(dev_install_command)
                results["outputs"].append(dev_stdout)
                
                if dev_code != 0:
                    results["success"] = False
                    results["errors"].append(f"Failed to install dev dependency {dev_dep}: {dev_stderr}")
                    return results
        
        return results
    
    async def _install_cargo_dependencies(
        self, 
        path: Path,
        dependencies: List[str],
        dev_dependencies: Optional[List[str]] = None,
        update_dependency_file: bool = True
    ) -> Dict[str, Any]:
        """
        Install Rust dependencies using Cargo.
        
        Args:
            path: Path to the project
            dependencies: List of dependencies to install
            dev_dependencies: Optional list of development dependencies
            update_dependency_file: Whether to update Cargo.toml
            
        Returns:
            Dictionary with the installation result
        """
        self._logger.info(f"Installing Rust dependencies with Cargo in {path}")
        
        results = {
            "success": True,
            "package_manager": "cargo",
            "project_type": "rust",
            "commands": [],
            "outputs": [],
            "errors": []
        }
        
        # Check if this is a Cargo project
        cargo_toml = path / "Cargo.toml"
        if not cargo_toml.exists():
            if update_dependency_file:
                # Initialize a new Cargo project
                project_name = path.name.replace("-", "_").lower()
                init_command = f"cargo init --name {project_name}"
                
                init_stdout, init_stderr, init_code = await execution_engine.execute_command(
                    init_command,
                    check_safety=True,
                    working_dir=str(path)
                )
                
                results["commands"].append(init_command)
                results["outputs"].append(init_stdout)
                
                if init_code != 0:
                    results["success"] = False
                    results["errors"].append(f"Failed to initialize Cargo project: {init_stderr}")
                    return results
            else:
                results["success"] = False
                results["errors"].append("Not a Cargo project and update_dependency_file is False")
                return results
        
        # Add dependencies to Cargo.toml
        if (dependencies or dev_dependencies) and update_dependency_file:
            try:
                with open(cargo_toml, 'r') as f:
                    cargo_content = f.read()
                
                # Add [dependencies] section if it doesn't exist
                if dependencies and "[dependencies]" not in cargo_content:
                    cargo_content += "\n[dependencies]\n"
                
                # Add dependencies
                if dependencies:
                    for dep in dependencies:
                        # Check if dependency is already in the file
                        if dep not in cargo_content:
                            # Parse dependency name and version (if provided)
                            if "=" in dep:
                                dep_name, dep_version = dep.split("=", 1)
                                cargo_content += f'{dep_name.strip()} = {dep_version.strip()}\n'
                            else:
                                cargo_content += f'{dep.strip()} = "*"\n'
                
                # Add [dev-dependencies] section if it doesn't exist
                if dev_dependencies and "[dev-dependencies]" not in cargo_content:
                    cargo_content += "\n[dev-dependencies]\n"
                
                # Add dev dependencies
                if dev_dependencies:
                    for dep in dev_dependencies:
                        # Check if dependency is already in the file
                        if dep not in cargo_content:
                            # Parse dependency name and version (if provided)
                            if "=" in dep:
                                dep_name, dep_version = dep.split("=", 1)
                                cargo_content += f'{dep_name.strip()} = {dep_version.strip()}\n'
                            else:
                                cargo_content += f'{dep.strip()} = "*"\n'
                
                # Write back to Cargo.toml
                with open(cargo_toml, 'w') as f:
                    f.write(cargo_content)
                
                results["updated_files"] = [str(cargo_toml)]
            except Exception as e:
                results["errors"].append(f"Failed to update Cargo.toml: {str(e)}")
        
        # Run cargo build to install dependencies
        build_command = "cargo build"
        build_stdout, build_stderr, build_code = await execution_engine.execute_command(
            build_command,
            check_safety=True,
            working_dir=str(path)
        )
        
        results["commands"].append(build_command)
        results["outputs"].append(build_stdout)
        
        if build_code != 0:
            results["success"] = False
            results["errors"].append(f"Failed to build project: {build_stderr}")
            return results
        
        return results
    
    async def _infer_project_type(self, path: Path) -> Optional[str]:
        """
        Infer the project type from the files in the directory.
        
        Args:
            path: Path to the project
            
        Returns:
            Inferred project type, or None if unable to infer
        """
        # Check for key files that indicate project type
        if (path / "requirements.txt").exists() or (path / "setup.py").exists() or (path / "pyproject.toml").exists():
            return "python"
        elif (path / "package.json").exists():
            return "node"
        elif (path / "Gemfile").exists() or (path / "Gemfile.lock").exists():
            return "ruby"
        elif (path / "composer.json").exists():
            return "php"
        elif (path / "go.mod").exists():
            return "go"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "pom.xml").exists() or (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
            return "java"
        
        # Count file extensions to guess project type
        extensions = {}
        for file_path in path.glob("**/*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
        
        # Determine project type based on most common extension
        if extensions:
            py_exts = extensions.get(".py", 0)
            js_exts = extensions.get(".js", 0) + extensions.get(".jsx", 0) + extensions.get(".ts", 0) + extensions.get(".tsx", 0)
            rb_exts = extensions.get(".rb", 0)
            php_exts = extensions.get(".php", 0)
            go_exts = extensions.get(".go", 0)
            rs_exts = extensions.get(".rs", 0)
            java_exts = extensions.get(".java", 0)
            
            max_ext = max([
                ("python", py_exts),
                ("node", js_exts),
                ("ruby", rb_exts),
                ("php", php_exts),
                ("go", go_exts),
                ("rust", rs_exts),
                ("java", java_exts)
            ], key=lambda x: x[1])
            
            if max_ext[1] > 0:
                return max_ext[0]
        
        return None

# Global package manager integration instance
package_manager_integration = PackageManagerIntegration()                
