# angela/toolchain/ci_cd.py
"""
CI/CD configuration generation for Angela CLI.

This module provides functionality for generating CI/CD configurations
for common CI platforms.
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import yaml
import json
import re
from collections.abc import MutableMapping, Sequence

from angela.utils.logging import get_logger
from angela.context import context_manager

logger = get_logger(__name__)

# Common deep merge utility for all configuration merging
def deep_update(d, u):
    """
    Recursively update a nested dictionary structure.
    
    Args:
        d: The original dictionary to update
        u: The dictionary with updates to apply
        
    Returns:
        Updated dictionary
    """
    result = d.copy()
    for k, v in u.items():
        if isinstance(v, MutableMapping) and isinstance(result.get(k, {}), MutableMapping):
            result[k] = deep_update(result.get(k, {}), v)
        elif isinstance(v, (list, tuple)) and isinstance(result.get(k, []), (list, tuple)):
            # Check for __REPLACE__ marker for list replacement
            if v and isinstance(v, list) and v[0] == "__REPLACE__":
                result[k] = v[1:]
            else:
                result[k] = result.get(k, []) + list(v)
        else:
            result[k] = v
    return result

class CiCdIntegration:
    """
    Integration for CI/CD platforms.
    """
    
    def __init__(self):
        """Initialize the CI/CD integration."""
        self._logger = logger
        
        # Supported CI/CD platforms
        self._supported_platforms = [
            "github_actions",
            "gitlab_ci",
            "jenkins",
            "travis",
            "circle_ci",
            "azure_pipelines",  # Additional platform
            "bitbucket_pipelines"  # Additional platform
        ]
    
    async def detect_project_type(
        self, 
        path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Detect the project type for CI/CD configuration.
        
        Args:
            path: Path to the project
            
        Returns:
            Dictionary with the detected project info
        """
        self._logger.info(f"Detecting project type in {path}")
        
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists() or not path_obj.is_dir():
            return {
                "detected": False,
                "error": f"Path does not exist or is not a directory: {path}",
                "project_type": None
            }
        
        # Check for project type indicators
        project_type = None
        framework = None
        
        # Python indicators
        if (path_obj / "requirements.txt").exists() or (path_obj / "setup.py").exists() or (path_obj / "pyproject.toml").exists():
            project_type = "python"
            # Check for specific Python frameworks
            if (path_obj / "manage.py").exists():
                framework = "django"
            elif (path_obj / "app.py").exists() or (path_obj / "wsgi.py").exists() or any(f.name == 'flask' for f in (path_obj / "requirements.txt").open().readlines() if hasattr(f, 'name')) if (path_obj / "requirements.txt").exists() else False:
                framework = "flask"
            elif (path_obj / "fastapi").exists() or any(f.name == 'fastapi' for f in (path_obj / "requirements.txt").open().readlines() if hasattr(f, 'name')) if (path_obj / "requirements.txt").exists() else False:
                framework = "fastapi"
        
        # Node.js indicators
        elif (path_obj / "package.json").exists():
            project_type = "node"
            # Check for specific JS frameworks
            try:
                with open(path_obj / "package.json") as f:
                    package_data = json.load(f)
                    dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                    if "react" in dependencies:
                        framework = "react"
                    elif "vue" in dependencies:
                        framework = "vue"
                    elif "angular" in dependencies:
                        framework = "angular"
                    elif "next" in dependencies:
                        framework = "nextjs"
                    elif "express" in dependencies:
                        framework = "express"
            except (json.JSONDecodeError, IOError):
                pass
        
        # Go indicators
        elif (path_obj / "go.mod").exists():
            project_type = "go"
            # Check for go frameworks like gin, echo, etc.
            try:
                with open(path_obj / "go.mod") as f:
                    content = f.read()
                    if "github.com/gin-gonic/gin" in content:
                        framework = "gin"
                    elif "github.com/labstack/echo" in content:
                        framework = "echo"
            except IOError:
                pass
        
        # Rust indicators
        elif (path_obj / "Cargo.toml").exists():
            project_type = "rust"
            try:
                with open(path_obj / "Cargo.toml") as f:
                    content = f.read()
                    if "rocket" in content:
                        framework = "rocket"
                    elif "actix-web" in content:
                        framework = "actix"
            except IOError:
                pass
        
        # Java indicators
        elif (path_obj / "pom.xml").exists():
            project_type = "java"
            framework = "maven"
            # Check for Spring Framework
            try:
                with open(path_obj / "pom.xml") as f:
                    content = f.read()
                    if "org.springframework" in content:
                        framework = "spring"
            except IOError:
                pass
        elif (path_obj / "build.gradle").exists() or (path_obj / "build.gradle.kts").exists():
            project_type = "java"
            framework = "gradle"
            # Check for Spring Framework
            gradle_file = path_obj / "build.gradle" if (path_obj / "build.gradle").exists() else path_obj / "build.gradle.kts"
            try:
                with open(gradle_file) as f:
                    content = f.read()
                    if "org.springframework" in content:
                        framework = "spring"
            except IOError:
                pass
        
        # Ruby indicators
        elif (path_obj / "Gemfile").exists():
            project_type = "ruby"
            # Check for Rails
            try:
                with open(path_obj / "Gemfile") as f:
                    content = f.read()
                    if "rails" in content.lower():
                        framework = "rails"
            except IOError:
                pass
        
        # PHP indicators
        elif any(f.suffix == '.php' for f in path_obj.glob('**/*.php')):
            project_type = "php"
            # Check for Laravel or Symfony
            if (path_obj / "artisan").exists():
                framework = "laravel"
            elif (path_obj / "bin" / "console").exists():
                framework = "symfony"
            elif (path_obj / "composer.json").exists():
                try:
                    with open(path_obj / "composer.json") as f:
                        composer_data = json.load(f)
                        require = composer_data.get("require", {})
                        if "laravel/framework" in require:
                            framework = "laravel"
                        elif "symfony/symfony" in require:
                            framework = "symfony"
                except (json.JSONDecodeError, IOError):
                    pass
        
        # .NET indicators
        elif any(f.suffix == '.csproj' for f in path_obj.glob('**/*.csproj')) or any(f.suffix == '.fsproj' for f in path_obj.glob('**/*.fsproj')):
            project_type = "dotnet"
            # Check for ASP.NET Core
            for proj_file in path_obj.glob('**/*.csproj'):
                try:
                    with open(proj_file) as f:
                        content = f.read()
                        if "Microsoft.AspNetCore" in content:
                            framework = "aspnet"
                            break
                except IOError:
                    continue
        
        # C/C++ with CMake
        elif (path_obj / "CMakeLists.txt").exists():
            project_type = "cpp"
            framework = "cmake"
        
        if project_type:
            result = {
                "detected": True,
                "project_type": project_type,
                "project_path": str(path_obj)
            }
            if framework:
                result["framework"] = framework
            return result
        
        # Try from context
        context = context_manager.get_context_dict()
        if context.get("project_type"):
            return {
                "detected": True,
                "project_type": context["project_type"],
                "project_path": str(path_obj),
                "from_context": True
            }
        
        return {
            "detected": False,
            "error": "Could not detect project type",
            "project_type": None
        }
    
    async def generate_ci_configuration(
        self, 
        path: Union[str, Path],
        platform: str,
        project_type: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a CI/CD configuration file.
        
        Args:
            path: Path to the project
            platform: CI/CD platform to generate for
            project_type: Optional project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating CI configuration for {platform}")
        
        path_obj = Path(path)
        
        # Check if platform is supported
        if platform not in self._supported_platforms:
            return {
                "success": False,
                "error": f"Unsupported CI/CD platform: {platform}",
                "platform": platform
            }
        
        # Detect project type if not provided
        if project_type is None:
            detection_result = await self.detect_project_type(path_obj)
            project_type = detection_result.get("project_type")
            
            if not project_type:
                return {
                    "success": False,
                    "error": f"Could not detect project type: {detection_result.get('error', 'Unknown error')}",
                    "platform": platform
                }
        
        # Generate configuration based on platform
        if platform == "github_actions":
            return await self._generate_github_actions(path_obj, project_type, custom_settings)
        elif platform == "gitlab_ci":
            return await self._generate_gitlab_ci(path_obj, project_type, custom_settings)
        elif platform == "jenkins":
            return await self._generate_jenkins(path_obj, project_type, custom_settings)
        elif platform == "travis":
            return await self._generate_travis(path_obj, project_type, custom_settings)
        elif platform == "circle_ci":
            return await self._generate_circle_ci(path_obj, project_type, custom_settings)
        elif platform == "azure_pipelines":
            return await self._generate_azure_pipelines(path_obj, project_type, custom_settings)
        elif platform == "bitbucket_pipelines":
            return await self._generate_bitbucket_pipelines(path_obj, project_type, custom_settings)
        
        return {
            "success": False,
            "error": f"Unsupported CI/CD platform: {platform}",
            "platform": platform
        }
    
    async def _generate_github_actions(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate GitHub Actions configuration.
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating GitHub Actions configuration for {project_type}")
        
        # Create .github/workflows directory
        workflows_dir = path / ".github" / "workflows"
        if not workflows_dir.exists():
            os.makedirs(workflows_dir, exist_ok=True)
        
        # Set default settings based on project type
        workflow: Dict[str, Any] = {} # Ensure workflow is initialized
        if project_type == "python":
            workflow = {
                "name": "Python CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "strategy": {
                            "matrix": {
                                "python-version": ["3.8", "3.9", "3.10"]
                            }
                        },
                        "steps": [
                            {
                    "step": {
                        "name": "Build and test",
                        "caches": ["cargo"],
                        "script": [
                            "rustup component add clippy",
                            "cargo build --verbose",
                            "cargo test --verbose",
                            "cargo clippy -- -D warnings"
                        ]
                    }
                }
            ]
        elif project_type == "java":
            if (path / "pom.xml").exists():
                config["image"] = "maven:latest"
                default_pipe = [
                    {
                        "step": {
                            "name": "Build and test",
                            "caches": ["maven"],
                            "script": [
                                "mvn clean package"
                            ]
                        }
                    }
                ]
            else:
                config["image"] = "gradle:latest"
                default_pipe = [
                    {
                        "step": {
                            "name": "Build and test",
                            "caches": ["gradle"],
                            "script": [
                                "gradle build"
                            ]
                        }
                    }
                ]
        elif project_type == "ruby":
            config["image"] = "ruby:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["bundler"],
                        "script": [
                            "bundle install",
                            "bundle exec rake test"
                        ]
                    }
                }
            ]
        elif project_type == "php":
            config["image"] = "php:8.0"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["composer"],
                        "script": [
                            "apt-get update && apt-get install -y git unzip",
                            "curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer",
                            "composer install",
                            "vendor/bin/phpunit"
                        ]
                    }
                }
            ]
        elif project_type == "dotnet":
            config["image"] = "mcr.microsoft.com/dotnet/sdk:6.0"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "dotnet restore",
                            "dotnet build",
                            "dotnet test"
                        ]
                    }
                }
            ]
        elif project_type == "cpp":
            config["image"] = "gcc:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "apt-get update && apt-get install -y cmake",
                            "cmake -B build -DCMAKE_BUILD_TYPE=Release",
                            "cmake --build build",
                            "cd build && ctest -V"
                        ]
                    }
                }
            ]
        else:
            config["image"] = "alpine:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "echo 'Add your build commands here'",
                            "echo 'Add your test commands here'"
                        ]
                    }
                }
            ]
        
        # Set up the pipeline steps
        config["pipelines"]["default"] = default_pipe
        config["pipelines"]["branches"]["main"] = default_pipe
        config["pipelines"]["branches"]["master"] = default_pipe
        config["pipelines"]["pull-requests"] = default_pipe
        
        # Add deployment step for tags
        deploy_pipe = list(default_pipe)
        deploy_pipe.append({
            "step": {
                "name": "Deploy on tag",
                "deployment": "production",
                "script": [
                    "echo 'Deploying to production...'"
                ]
            }
        })
        config["pipelines"]["tags"] = deploy_pipe
        
        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = path / "bitbucket-pipelines.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "bitbucket_pipelines",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write Bitbucket Pipelines config: {str(e)}",
                "platform": "bitbucket_pipelines",
                "project_type": project_type
            }
                    "step": {
                        "name": "Build and test",
                        "caches": ["cargo"],
                        "script": [
                            "rustup component add clippy",
                            "cargo build --verbose",
                            "cargo test --verbose",
                            "cargo clippy -- -D warnings"
                        ]
                    }
                }
            ]
        elif project_type == "java":
            if (path / "pom.xml").exists():
                config["image"] = "maven:latest"
                default_pipe = [
                    {
                        "step": {
                            "name": "Build and test",
                            "caches": ["maven"],
                            "script": [
                                "mvn clean package"
                            ]
                        }
                    }
                ]
            else:
                config["image"] = "gradle:latest"
                default_pipe = [
                    {
                        "step": {
                            "name": "Build and test",
                            "caches": ["gradle"],
                            "script": [
                                "gradle build"
                            ]
                        }
                    }
                ]
        elif project_type == "ruby":
            config["image"] = "ruby:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["bundler"],
                        "script": [
                            "bundle install",
                            "bundle exec rake test"
                        ]
                    }
                }
            ]
        elif project_type == "php":
            config["image"] = "php:8.0"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["composer"],
                        "script": [
                            "apt-get update && apt-get install -y git unzip",
                            "curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer",
                            "composer install",
                            "vendor/bin/phpunit"
                        ]
                    }
                }
            ]
        elif project_type == "dotnet":
            config["image"] = "mcr.microsoft.com/dotnet/sdk:6.0"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "dotnet restore",
                            "dotnet build",
                            "dotnet test"
                        ]
                    }
                }
            ]
        elif project_type == "cpp":
            config["image"] = "gcc:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "apt-get update && apt-get install -y cmake",
                            "cmake -B build -DCMAKE_BUILD_TYPE=Release",
                            "cmake --build build",
                            "cd build && ctest -V"
                        ]
                    }
                }
            ]
        else:
            config["image"] = "alpine:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "echo 'Add your build commands here'",
                            "echo 'Add your test commands here'"
                        ]
                    }
                }
            ]
        
        # Set up the pipeline steps
        config["pipelines"]["default"] = default_pipe
        config["pipelines"]["branches"]["main"] = default_pipe
        config["pipelines"]["branches"]["master"] = default_pipe
        config["pipelines"]["pull-requests"] = default_pipe
        
        # Add deployment step for tags
        deploy_pipe = list(default_pipe)
        deploy_pipe.append({
            "step": {
                "name": "Deploy on tag",
                "deployment": "production",
                "script": [
                    "echo 'Deploying to production...'"
                ]
            }
        })
        config["pipelines"]["tags"] = deploy_pipe
        
        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = path / "bitbucket-pipelines.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "bitbucket_pipelines",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write Bitbucket Pipelines config: {str(e)}",
                "platform": "bitbucket_pipelines",
                "project_type": project_type
            }
    
    async def create_complete_pipeline(
        self,
        project_path: Union[str, Path],
        platform: str,
        pipeline_type: str = "full",  # "full", "build-only", "deploy-only"
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete CI/CD pipeline for a project.
        
        Args:
            project_path: Path to the project
            platform: CI/CD platform to use
            pipeline_type: Type of pipeline to create
            custom_settings: Custom settings for the pipeline
            
        Returns:
            Dictionary with the creation result
        """
        project_path = Path(project_path)
        self._logger.info(f"Creating complete {pipeline_type} pipeline for {project_path} on {platform}")
        
        # Detect project type
        detection_result = await self.detect_project_type(project_path)
        if not detection_result.get("detected"):
            return {
                "success": False,
                "error": detection_result.get("error", "Could not detect project type"),
                "platform": platform
            }
        
        project_type = detection_result["project_type"]
        
        # Determine pipeline steps based on project type and pipeline type
        pipeline_steps = await self._determine_pipeline_steps(
            project_type, 
            platform, 
            pipeline_type
        )
        
        # Merge with custom settings
        if custom_settings:
            pipeline_steps = deep_update(pipeline_steps, custom_settings)
        
        # Generate configuration
        result = await self.generate_ci_configuration(
            path=project_path,
            platform=platform,
            project_type=project_type,
            custom_settings=pipeline_steps
        )
        
        if not result.get("success"):
            return result
        
        # Set up additional required files
        if pipeline_type == "full" or pipeline_type == "deploy-only":
            # Set up deployment configuration if needed
            deploy_result = await self._setup_deployment_config(
                project_path, 
                platform, 
                project_type,
                pipeline_steps
            )
            
            if deploy_result:
                result["deployment_config"] = deploy_result
        
        # Set up testing configurations if needed
        if pipeline_type == "full" or pipeline_type == "build-only":
            testing_result = await self._setup_testing_config(
                project_path,
                project_type,
                pipeline_steps
            )
            
            if testing_result:
                result["testing_config"] = testing_result
        
        return result
    
    async def _determine_pipeline_steps(
        self,
        project_type: str,
        platform: str,
        pipeline_type: str
    ) -> Dict[str, Any]:
        """
        Determine the steps for a CI/CD pipeline.
        
        Args:
            project_type: Type of project
            platform: CI/CD platform
            pipeline_type: Type of pipeline
            
        Returns:
            Dictionary with pipeline steps
        """
        self._logger.debug(f"Determining pipeline steps for {project_type} on {platform} ({pipeline_type})")
        
        # Base steps common to all pipelines
        pipeline_steps = {
            "build": True,
            "test": True,
            "lint": True,
            "security_scan": pipeline_type == "full",
            "package": pipeline_type != "build-only",
            "deploy": pipeline_type != "build-only",
            "notify": pipeline_type == "full"
        }
        
        # Add platform-specific settings
        if platform == "github_actions":
            # GitHub Actions specific settings
            pipeline_steps["triggers"] = {
                "push": ["main", "master"],
                "pull_request": ["main", "master"],
                "manual": pipeline_type != "build-only"
            }
            
            # Add deployment environment based on pipeline type
            if pipeline_type != "build-only":
                pipeline_steps["environments"] = ["staging"]
                if pipeline_type == "full":
                    pipeline_steps["environments"].append("production")
        
        elif platform == "gitlab_ci":
            # GitLab CI specific settings
            pipeline_steps["stages"] = ["build", "test", "package"]
            if pipeline_type != "build-only":
                pipeline_steps["stages"].extend(["deploy", "verify"])
            
            pipeline_steps["cache"] = True
            pipeline_steps["artifacts"] = True
        
        # Add project-type specific settings
        if project_type == "python":
            pipeline_steps["python_versions"] = ["3.8", "3.9", "3.10"]
            pipeline_steps["test_command"] = "pytest --cov"
            pipeline_steps["lint_command"] = "flake8"
        
        elif project_type == "node":
            pipeline_steps["node_versions"] = ["14", "16", "18"]
            pipeline_steps["test_command"] = "npm test"
            pipeline_steps["lint_command"] = "npm run lint"
        
        elif project_type == "go":
            pipeline_steps["go_versions"] = ["1.18", "1.19"]
            pipeline_steps["test_command"] = "go test ./..."
            pipeline_steps["lint_command"] = "golangci-lint run"
        
        elif project_type == "java":
            pipeline_steps["java_versions"] = ["11", "17"]
            pipeline_steps["test_command"] = "mvn test"
            pipeline_steps["lint_command"] = "mvn checkstyle:check"
        
        elif project_type == "rust":
            pipeline_steps["rust_versions"] = ["stable", "beta"]
            pipeline_steps["test_command"] = "cargo test"
            pipeline_steps["lint_command"] = "cargo clippy -- -D warnings"
            
        elif project_type == "ruby":
            pipeline_steps["ruby_versions"] = ["2.7", "3.0", "3.1"]
            pipeline_steps["test_command"] = "bundle exec rake test"
            pipeline_steps["lint_command"] = "bundle exec rubocop"
            
        elif project_type == "php":
            pipeline_steps["php_versions"] = ["7.4", "8.0", "8.1"]
            pipeline_steps["test_command"] = "vendor/bin/phpunit"
            pipeline_steps["lint_command"] = "vendor/bin/phpcs"
            
        elif project_type == "dotnet":
            pipeline_steps["dotnet_versions"] = ["6.0", "7.0"]
            pipeline_steps["test_command"] = "dotnet test"
            pipeline_steps["lint_command"] = "dotnet format --verify-no-changes"
            
        elif project_type == "cpp":
            pipeline_steps["compilers"] = ["gcc", "clang"]
            pipeline_steps["test_command"] = "ctest -V"
            pipeline_steps["lint_command"] = "cppcheck ."
            
        return pipeline_steps
    
    async def _setup_deployment_config(
        self,
        project_path: Path,
        platform: str,
        project_type: str,
        pipeline_steps: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up deployment configuration files.
        
        Args:
            project_path: Path to the project
            platform: CI/CD platform
            project_type: Type of project
            pipeline_steps: Pipeline steps configuration
            
        Returns:
            Dictionary with deployment configuration result
        """
        self._logger.info(f"Setting up deployment configuration for {project_type}")
        
        # Create deployment configuration based on project type
        if project_type == "python":
            # For Python, create a simple deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for Python project
echo "Deploying Python application..."

# Install dependencies
pip install -r requirements.txt

# Check for common deployment frameworks
if [ -f "manage.py" ]; then
    echo "Django project detected"
    python manage.py migrate
    python manage.py collectstatic --noinput
elif [ -f "app.py" ] || [ -f "wsgi.py" ]; then
    echo "Flask/WSGI project detected"
else
    echo "Generic Python project"
fi

# Reload application (depends on hosting)
if [ -f "gunicorn.pid" ]; then
    echo "Reloading Gunicorn..."
    kill -HUP $(cat gunicorn.pid)
elif command -v systemctl &> /dev/null && systemctl list-units --type=service | grep -q "$(basename $(pwd))"; then
    echo "Restarting service..."
    systemctl restart $(basename $(pwd))
else
    echo "Starting application..."
    # Add your start command here
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "node":
            # For Node.js, create a deployment configuration
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.js"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""// Deployment script for Node.js project
console.log('Deploying Node.js application...');

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Execute shell command and print output
function exec(command) {
    console.log(`> ${command}`);
    try {
        const output = execSync(command, { encoding: 'utf8' });
        if (output) console.log(output);
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
}

// Install dependencies
exec('npm ci --production');

// Check for common frameworks
const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const dependencies = packageJson.dependencies || {};

if (dependencies.next) {
    console.log('Next.js project detected');
    exec('npm run build');
} else if (dependencies.react) {
    console.log('React project detected');
    exec('npm run build');
} else if (dependencies.vue) {
    console.log('Vue.js project detected');
    exec('npm run build');
} else if (dependencies.express) {
    console.log('Express.js project detected');
} else {
    console.log('Generic Node.js project');
}

// Restart application
try {
    if (fs.existsSync('process.pid')) {
        console.log('Reloading application...');
        const pid = fs.readFileSync('process.pid', 'utf8').trim();
        try {
            process.kill(pid, 'SIGUSR2');
            console.log(`Sent SIGUSR2 to process ${pid}`);
        } catch (err) {
            console.log(`Process ${pid} not found, starting fresh`);
            // Start application
            if (fs.existsSync('ecosystem.config.js')) {
                exec('npx pm2 reload ecosystem.config.js');
            } else {
                // Determine main file
                const mainFile = packageJson.main || 'index.js';
                exec(`npx pm2 start ${mainFile} --name ${path.basename(process.cwd())}`);
            }
        }
    } else if (fs.existsSync('ecosystem.config.js')) {
        console.log('Starting with PM2...');
        exec('npx pm2 reload ecosystem.config.js');
    } else {
        console.log('Starting application...');
        // Determine main file
        const mainFile = packageJson.main || 'index.js';
        exec(`npx pm2 start ${mainFile} --name ${path.basename(process.cwd())}`);
    }
} catch (error) {
    console.error(`Error managing application process: ${error.message}`);
}

console.log('Deployment complete!');
""")
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "go":
            # For Go, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for Go project
echo "Deploying Go application..."

# Build the application
go build -o bin/app

# Check if systemd service exists
SERVICE_NAME=$(basename $(pwd))
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Create a systemd service file if needed
    if [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        echo "Creating systemd service..."
        cat > /tmp/$SERVICE_NAME.service <<EOL
[Unit]
Description=$SERVICE_NAME
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/bin/app
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
        sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        sudo systemctl start $SERVICE_NAME
    else
        # Start directly if no service exists and we can't create one
        nohup bin/app > logs/app.log 2>&1 &
        echo $! > app.pid
        echo "Application started with PID $(cat app.pid)"
    fi
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "java":
            # For Java, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                if (project_path / "pom.xml").exists():
                    # Maven project
                    f.write("""#!/bin/bash
set -e

# Deployment script for Java Maven project
echo "Deploying Java Maven application..."

# Build the application
mvn clean package

# Get the JAR file
JAR_FILE=$(find target -name "*.jar" | head -1)
if [ -z "$JAR_FILE" ]; then
    echo "No JAR file found in target directory."
    exit 1
fi

# Check if running as a service
SERVICE_NAME=$(basename $(pwd))
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Check if there's a running instance
    if [ -f "app.pid" ]; then
        OLD_PID=$(cat app.pid)
        if ps -p $OLD_PID > /dev/null; then
            echo "Stopping previous instance (PID: $OLD_PID)..."
            kill $OLD_PID
            sleep 2
        fi
    fi
    
    # Start the application
    mkdir -p logs
    nohup java -jar $JAR_FILE > logs/app.log 2>&1 &
    PID=$!
    echo $PID > app.pid
    echo "Application started with PID $PID"
fi

echo "Deployment complete!"
""")
                else:
                    # Gradle project
                    f.write("""#!/bin/bash
set -e

# Deployment script for Java Gradle project
echo "Deploying Java Gradle application..."

# Build the application
./gradlew build

# Get the JAR file
JAR_FILE=$(find build/libs -name "*.jar" | head -1)
if [ -z "$JAR_FILE" ]; then
    echo "No JAR file found in build/libs directory."
    exit 1
fi

# Check if running as a service
SERVICE_NAME=$(basename $(pwd))
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Check if there's a running instance
    if [ -f "app.pid" ]; then
        OLD_PID=$(cat app.pid)
        if ps -p $OLD_PID > /dev/null; then
            echo "Stopping previous instance (PID: $OLD_PID)..."
            kill $OLD_PID
            sleep 2
        fi
    fi
    
    # Start the application
    mkdir -p logs
    nohup java -jar $JAR_FILE > logs/app.log 2>&1 &
    PID=$!
    echo $PID > app.pid
    echo "Application started with PID $PID"
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "rust":
            # For Rust, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for Rust project
echo "Deploying Rust application..."

# Build the application in release mode
cargo build --release

# Get the binary name from Cargo.toml
BINARY_NAME=$(grep -m 1 "name" Cargo.toml | cut -d '"' -f 2 | tr -d '[:space:]')
if [ -z "$BINARY_NAME" ]; then
    BINARY_NAME=$(basename $(pwd))
fi

# Check if systemd service exists
SERVICE_NAME=$BINARY_NAME
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Create a systemd service file if needed
    if [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        echo "Creating systemd service..."
        cat > /tmp/$SERVICE_NAME.service <<EOL
[Unit]
Description=$SERVICE_NAME
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/target/release/$BINARY_NAME
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
        sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        sudo systemctl start $SERVICE_NAME
    else
        # Start directly if no service exists and we can't create one
        mkdir -p logs
        nohup target/release/$BINARY_NAME > logs/app.log 2>&1 &
        echo $! > app.pid
        echo "Application started with PID $(cat app.pid)"
    fi
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
            
        elif project_type == "php":
            # For PHP, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for PHP project
echo "Deploying PHP application..."

# Install dependencies
composer install --no-dev --optimize-autoloader

# Check for Laravel
if [ -f "artisan" ]; then
    echo "Laravel project detected"
    php artisan migrate --force
    php artisan config:cache
    php artisan route:cache
    php artisan view:cache
fi

# Check for Symfony
if [ -f "bin/console" ]; then
    echo "Symfony project detected"
    php bin/console cache:clear --env=prod
    php bin/console doctrine:migrations:migrate --no-interaction
fi

# Reload PHP-FPM if available
if command -v systemctl &> /dev/null && systemctl list-units --type=service | grep -q "php.*-fpm"; then
    echo "Reloading PHP-FPM..."
    sudo systemctl reload php*-fpm.service
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
            
        # Add more project types as needed
        
        return {
            "success": False,
            "message": f"No deployment configuration available for {project_type}"
        }
    
    async def _setup_testing_config(
        self,
        project_path: Path,
        project_type: str,
        pipeline_steps: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up testing configuration files.
        
        Args:
            project_path: Path to the project
            project_type: Type of project
            pipeline_steps: Pipeline steps configuration
            
        Returns:
            Dictionary with testing configuration result
        """
        self._logger.info(f"Setting up testing configuration for {project_type}")
        
        created_files = []
        
        if project_type == "python":
            # Check if pytest.ini exists, create if not
            pytest_ini = project_path / "pytest.ini"
            if not pytest_ini.exists():
                with open(pytest_ini, "w") as f:
                    f.write("""[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --verbose --cov=./ --cov-report=term-missing
""")
                created_files.append(str(pytest_ini))
            
            # Create a basic test directory and example test if not exists
            tests_dir = project_path / "tests"
            if not tests_dir.exists():
                os.makedirs(tests_dir, exist_ok=True)
                
                # Create __init__.py
                with open(tests_dir / "__init__.py", "w") as f:
                    f.write("# Test package initialization")
                created_files.append(str(tests_dir / "__init__.py"))
                
                # Create an example test
                with open(tests_dir / "test_example.py", "w") as f:
                    f.write("""import unittest

class TestExample(unittest.TestCase):
    def test_simple_assertion(self):
        self.assertEqual(1 + 1, 2)
        
    def test_truth_value(self):
        self.assertTrue(True)
""")
                created_files.append(str(tests_dir / "test_example.py"))
            
            return {
                "success": True,
                "files_created": created_files,
                "message": "Created testing configuration",
                "framework": "pytest"
            }
        
        elif project_type == "node":
            # Check if jest configuration exists in package.json
            package_json_path = project_path / "package.json"
            if package_json_path.exists():
                try:
                    import json
                    with open(package_json_path, "r") as f:
                        package_data = json.load(f)
                    
                    # Check if jest is configured
                    has_jest = False
                    if "jest" not in package_data and "scripts" in package_data:
                        # If not in scripts.test, add jest configuration
                        if "test" not in package_data["scripts"] or "jest" not in package_data["scripts"]["test"]:
                            package_data["scripts"]["test"] = "jest"
                            has_jest = True
                            
                            # Save the updated package.json
                            with open(package_json_path, "w") as f:
                                json.dump(package_data, f, indent=2)
                            
                    # Create jest.config.js if needed
                    jest_config = project_path / "jest.config.js"
                    if not jest_config.exists() and has_jest:
                        with open(jest_config, "w") as f:
                            f.write("""module.exports = {
  testEnvironment: 'node',
  coverageDirectory: 'coverage',
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/index.js',
    '!**/node_modules/**',
  ],
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
};
""")
                        created_files.append(str(jest_config))
                    
                    # Create tests directory if needed
                    tests_dir = project_path / "__tests__"
                    if not tests_dir.exists() and has_jest:
                        os.makedirs(tests_dir, exist_ok=True)
                        
                        # Create an example test
                        with open(tests_dir / "example.test.js", "w") as f:
                            f.write("""describe('Example Test Suite', () => {
  test('adds 1 + 2 to equal 3', () => {
    expect(1 + 2).toBe(3);
  });
  
  test('true is truthy', () => {
    expect(true).toBeTruthy();
  });
});
""")
                        created_files.append(str(tests_dir / "example.test.js"))
                    
                    return {
                        "success": True,
                        "files_created": created_files,
                        "message": "Created testing configuration",
                        "framework": "jest"
                    }
                    
                except (json.JSONDecodeError, IOError) as e:
                    self._logger.error(f"Error reading or updating package.json: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to update package.json: {str(e)}"
                    }
                    
        elif project_type == "java":
            if (project_path / "pom.xml").exists():
                # Maven project, check for surefire plugin
                pom_path = project_path / "pom.xml"
                try:
                    with open(pom_path, "r") as f:
                        pom_content = f.read()
                        
                    if "maven-surefire-plugin" not in pom_content:
                        # Create a sample test if tests directory doesn't exist
                        test_dir = project_path / "src" / "test" / "java"
                        if not test_dir.exists():
                            os.makedirs(test_dir, exist_ok=True)
                            
                            # Create a simple test class
                            with open(test_dir / "ExampleTest.java", "w") as f:
                                f.write("""import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ExampleTest {
    @Test
    void simpleAssertion() {
        assertEquals(2, 1 + 1);
    }
    
    @Test
    void truthValue() {
        assertTrue(true);
    }
}
""")
                            created_files.append(str(test_dir / "ExampleTest.java"))
                            
                    return {
                        "success": True,
                        "files_created": created_files,
                        "message": "Created testing configuration",
                        "framework": "junit"
                    }
                except IOError as e:
                    self._logger.error(f"Error reading pom.xml: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to read pom.xml: {str(e)}"
                    }
            else:
                # Gradle project, check for test directory
                test_dir = project_path / "src" / "test" / "java"
                if not test_dir.exists():
                    os.makedirs(test_dir, exist_ok=True)
                    
                    # Create a simple test class
                    with open(test_dir / "ExampleTest.java", "w") as f:
                        f.write("""import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ExampleTest {
    @Test
    void simpleAssertion() {
        assertEquals(2, 1 + 1);
    }
    
    @Test
    void truthValue() {
        assertTrue(true);
    }
}
""")
                    created_files.append(str(test_dir / "ExampleTest.java"))
                    
                return {
                    "success": True,
                    "files_created": created_files,
                    "message": "Created testing configuration",
                    "framework": "junit"
                }
                
        elif project_type == "go":
            # Go tests are typically in the same package as the code
            # Create a simple test file if none exists
            main_go = None
            for file in project_path.glob("*.go"):
                if file.name == "main.go":
                    main_go = file
                    break
                    
            if main_go:
                test_file = project_path / (main_go.stem + "_test.go")
                if not test_file.exists():
                    with open(test_file, "w") as f:
                        f.write("""package main

import (
	"testing"
)

func TestExample(t *testing.T) {
	if 1+1 != 2 {
		t.Error("1+1 should equal 2")
	}
}

func TestTruthValue(t *testing.T) {
	if !true {
		t.Error("true should be true")
	}
}
""")
                    created_files.append(str(test_file))
                    
                return {
                    "success": True,
                    "files_created": created_files,
                    "message": "Created testing configuration",
                    "framework": "go-test"
                }
                
        elif project_type == "rust":
            # Check if tests directory exists in the src directory
            src_dir = project_path / "src"
            if src_dir.exists():
                # Create a tests directory if it doesn't exist
                tests_dir = src_dir / "tests"
                if not tests_dir.exists():
                    os.makedirs(tests_dir, exist_ok=True)
                    
                    # Create a simple test file
                    with open(tests_dir / "example_test.rs", "w") as f:
                        f.write("""#[cfg(test)]
mod tests {
    #[test]
    fn test_simple_assertion() {
        assert_eq!(2, 1 + 1);
    }
    
    #[test]
    fn test_truth_value() {
        assert!(true);
    }
}
""")
                    created_files.append(str(tests_dir / "example_test.rs"))
                    
                # Add test module to lib.rs if it exists
                lib_rs = src_dir / "lib.rs"
                if lib_rs.exists():
                    with open(lib_rs, "r") as f:
                        content = f.read()
                        
                    if "#[cfg(test)]" not in content and "mod tests" not in content:
                        with open(lib_rs, "a") as f:
                            f.write("""
#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2, 1 + 1);
    }
}
""")
                
                return {
                    "success": True,
                    "files_created": created_files,
                    "message": "Created testing configuration",
                    "framework": "cargo-test"
                }
        
        # Add more project types as needed
        
        return {
            "success": False,
            "message": f"No testing configuration available for {project_type}"
        }
    
    def _merge_configs(self, base_config: Dict[str, Any], custom_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge base configuration with custom configuration recursively.
        
        Args:
            base_config: Base configuration
            custom_config: Custom configuration to merge in
            
        Returns:
            Merged configuration
        """
        return deep_update(base_config, custom_config)
        
    async def setup_ci_cd_pipeline(
        self,
        request: str,
        project_dir: Union[str, Path],
        repository_url: Optional[str] = None,
        platform: Optional[str] = None,
        deployment_targets: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Set up a complete CI/CD pipeline based on a natural language request.
        
        Args:
            request: Natural language request
            project_dir: Project directory
            repository_url: Optional repository URL
            platform: Optional CI/CD platform override
            deployment_targets: Optional deployment targets override
            custom_config: Optional custom configuration
            
        Returns:
            Dictionary with the setup result
        """
        self._logger.info(f"Setting up CI/CD pipeline from request: {request}")
        
        # Analyze request to extract key information if not explicitly provided
        parsed_request = await self._parse_ci_cd_request(request)
        
        # Use provided values or fall back to parsed values
        repository_url = repository_url or parsed_request.get("repository_url")
        platform = platform or parsed_request.get("platform")
        deployment_targets = deployment_targets or parsed_request.get("deployment_targets")
        
        # If repository URL is not provided, try to infer from git config
        if not repository_url:
            try:
                git_output = await self._run_git_command(["remote", "get-url", "origin"], cwd=project_dir)
                if git_output:
                    repository_url = git_output.strip()
            except Exception as e:
                self._logger.warning(f"Could not determine repository URL from git: {str(e)}")
        
        # Determine repository provider
        repository_provider = "unknown"
        if repository_url:
            repository_provider = self.get_repository_provider_from_url(repository_url)
        
        # If platform is not specified, try to determine from repository provider
        if not platform:
            if repository_provider == "github":
                platform = "github_actions"
            elif repository_provider == "gitlab":
                platform = "gitlab_ci"
            elif repository_provider == "bitbucket":
                platform = "bitbucket_pipelines"
            elif repository_provider == "azure_devops":
                platform = "azure_pipelines"
            else:
                # Default to GitHub Actions
                platform = "github_actions"
        
        # Create repository info dictionary
        repository_info = {
            "url": repository_url,
            "provider": repository_provider
        }
        
        # Create the complete pipeline
        result = await self._create_complete_pipeline(
            project_dir=project_dir,
            repository_info=repository_info,
            platform=platform,
            deployment_targets=deployment_targets,
            custom_config=custom_config
        )
        
        # Add parsed request information to the result
        result["parsed_request"] = parsed_request
        
        return result
    
    async def _parse_ci_cd_request(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language CI/CD setup request to extract key information.
        
        Args:
            request: Natural language request
            
        Returns:
            Dictionary with extracted information
        """
        self._logger.info(f"Parsing CI/CD request: {request}")
        
        # Use AI to parse the request
        prompt = f"""
Extract key information from this CI/CD setup request:
"{request}"

Return a JSON object with these fields:
1. platform: The CI/CD platform name (github_actions, gitlab_ci, jenkins, etc.)
2. repository_url: Repository URL if mentioned
3. deployment_targets: List of deployment environments to set up
4. testing_requirements: Any specific testing requirements
5. build_requirements: Any specific build requirements
6. security_requirements: Any security scanning requirements
"""
    
        try:
            # Call AI service
            from angela.ai.client import gemini_client, GeminiRequest
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            parsed_info = json.loads(json_str)
            
            # Ensure expected keys exist
            expected_keys = ["platform", "repository_url", "deployment_targets", 
                            "testing_requirements", "build_requirements", "security_requirements"]
            for key in expected_keys:
                if key not in parsed_info:
                    parsed_info[key] = None
            
            return parsed_info
            
        except Exception as e:
            self._logger.error(f"Error parsing CI/CD request: {str(e)}")
            # Return minimal information on error
            return {
                "platform": None,
                "repository_url": None,
                "deployment_targets": None,
                "testing_requirements": None,
                "build_requirements": None,
                "security_requirements": None
            }
    
    async def _run_git_command(self, args: List[str], cwd: Union[str, Path] = ".") -> str:
        """
        Run a git command and return the output.
        
        Args:
            args: Git command arguments
            cwd: Working directory
            
        Returns:
            Command output as a string
        """
        try:
            from angela.execution.engine import execution_engine
            command = ["git"] + args
            command_str = " ".join(command)
            
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=command_str,
                check_safety=True,
                working_dir=str(cwd)
            )
            
            if return_code != 0:
                raise RuntimeError(f"Git command failed: {stderr}")
            
            return stdout
        except Exception as e:
            self._logger.error(f"Error running git command: {str(e)}")
            raise
            
    async def _create_complete_pipeline(
        self, 
        project_dir: Union[str, Path], 
        repository_info: Dict[str, Any],
        platform: str,
        deployment_targets: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete CI/CD pipeline for a project.
        
        Args:
            project_dir: Project directory
            repository_info: Repository information (URL, provider, etc.)
            platform: CI/CD platform (github_actions, gitlab_ci, etc.)
            deployment_targets: Optional list of deployment targets
            custom_config: Optional custom configuration
            
        Returns:
            Dictionary with the pipeline creation result
        """
        self._logger.info(f"Creating complete CI/CD pipeline on {platform}")
        
        # Detect project type if not provided
        detection_result = await self.detect_project_type(project_dir)
        project_type = detection_result.get("project_type")
        
        if not project_type:
            return {
                "success": False,
                "error": f"Could not detect project type: {detection_result.get('error', 'Unknown error')}",
                "platform": platform
            }
        
        # Determine pipeline steps
        pipeline_steps = await self._determine_pipeline_steps(
            project_type=project_type,
            platform=platform,
            pipeline_type="full"
        )
        
        # Set up testing configuration
        testing_config = await self._setup_testing_config(
            project_path=project_dir,
            project_type=project_type,
            pipeline_steps=pipeline_steps
        )
        
        # Set up deployment configuration if targets are specified
        deployment_config = None
        if deployment_targets:
            deployment_config = await self._setup_deployment_config(
                project_path=project_dir,
                platform=platform,
                project_type=project_type,
                pipeline_steps=pipeline_steps
            )
        
        # Generate the final pipeline configuration
        config = {
            "pipeline_steps": pipeline_steps
        }
        
        if testing_config and testing_config.get("success", False):
            config["testing_config"] = testing_config
        
        if deployment_config and deployment_config.get("success", False):
            config["deployment_config"] = deployment_config
        
        if custom_config:
            config = deep_update(config, custom_config)
        
        # Generate the actual CI/CD configuration file
        result = await self.generate_ci_configuration(
            path=project_dir,
            platform=platform,
            project_type=project_type,
            custom_settings=config
        )
        
        # Add pipeline metadata to the result
        result["pipeline_info"] = {
            "project_type": project_type,
            "platform": platform,
            "repository": repository_info,
            "testing": testing_config.get("framework") if testing_config and testing_config.get("success", False) else None,
            "deployment": deployment_targets if deployment_targets else []
        }
        
        return result

# Global CI/CD integration instance
ci_cd_integration = CiCdIntegration()
            "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Set up Python ${{ matrix.python-version }}",
                                "uses": "actions/setup-python@v4",
                                "with": {
                                    "python-version": "${{ matrix.python-version }}"
                                }
                            },
                            {
                                "name": "Install dependencies",
                                "run": "python -m pip install --upgrade pip\npip install -r requirements.txt\npip install pytest pytest-cov flake8"
                            },
                            {
                                "name": "Lint with flake8",
                                "run": "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics"
                            },
                            {
                                "name": "Test with pytest",
                                "run": "pytest --cov=. --cov-report=xml"
                            },
                            {
                                "name": "Upload coverage to Codecov",
                                "uses": "codecov/codecov-action@v3",
                                "with": {
                                    "file": "./coverage.xml",
                                    "fail_ci_if_error": "false"
                                }
                            }
                        ]
                    }
                }
            }
        elif project_type == "node":
            workflow = {
                "name": "Node.js CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "strategy": {
                            "matrix": {
                                "node-version": ["14.x", "16.x", "18.x"]
                            }
                        },
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Use Node.js ${{ matrix.node-version }}",
                                "uses": "actions/setup-node@v3",
                                "with": {
                                    "node-version": "${{ matrix.node-version }}",
                                    "cache": "npm"
                                }
                            },
                            {
                                "name": "Install dependencies",
                                "run": "npm ci"
                            },
                            {
                                "name": "Run linting",
                                "run": "npm run lint --if-present"
                            },
                            {
                                "name": "Build",
                                "run": "npm run build --if-present"
                            },
                            {
                                "name": "Test",
                                "run": "npm test"
                            }
                        ]
                    }
                }
            }
        elif project_type == "go":
            workflow = {
                "name": "Go CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Set up Go",
                                "uses": "actions/setup-go@v3",
                                "with": {
                                    "go-version": "1.18"
                                }
                            },
                            {
                                "name": "Build",
                                "run": "go build -v ./..."
                            },
                            {
                                "name": "Test",
                                "run": "go test -v ./..."
                            }
                        ]
                    }
                }
            }
        elif project_type == "rust":
            workflow = {
                "name": "Rust CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Install Rust",
                                "uses": "actions-rs/toolchain@v1",
                                "with": {
                                    "profile": "minimal",
                                    "toolchain": "stable",
                                    "override": "true",
                                    "components": "rustfmt, clippy"
                                }
                            },
                            {
                                "name": "Check formatting",
                                "uses": "actions-rs/cargo@v1",
                                "with": {
                                    "command": "fmt",
                                    "args": "-- --check"
                                }
                            },
                            {
                                "name": "Clippy",
                                "uses": "actions-rs/cargo@v1",
                                "with": {
                                    "command": "clippy",
                                    "args": "-- -D warnings"
                                }
                            },
                            {
                                "name": "Build",
                                "uses": "actions-rs/cargo@v1",
                                "with": {
                                    "command": "build"
                                }
                            },
                            {
                                "name": "Test",
                                "uses": "actions-rs/cargo@v1",
                                "with": {
                                    "command": "test"
                                }
                            }
                        ]
                    }
                }
            }
        elif project_type == "java":
            workflow = {
                "name": "Java CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "strategy": {
                            "matrix": {
                                "java-version": ["11", "17"]
                            }
                        },
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Set up JDK ${{ matrix.java-version }}",
                                "uses": "actions/setup-java@v3",
                                "with": {
                                    "java-version": "${{ matrix.java-version }}",
                                    "distribution": "temurin",
                                    "cache": "maven"
                                }
                            },
                            {
                                "name": "Build with Maven",
                                "run": "mvn -B package --file pom.xml"
                            },
                            {
                                "name": "Test",
                                "run": "mvn test"
                            }
                        ]
                    }
                }
            }
            # Check if it's Gradle
            if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
                workflow["jobs"]["build"]["steps"][2] = {
                    "name": "Build with Gradle",
                    "uses": "gradle/gradle-build-action@v2",
                    "with": {
                        "arguments": "build"
                    }
                }
                workflow["jobs"]["build"]["steps"][3] = {
                    "name": "Test",
                    "uses": "gradle/gradle-build-action@v2",
                    "with": {
                        "arguments": "test"
                    }
                }
        elif project_type == "ruby":
            workflow = {
                "name": "Ruby CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "strategy": {
                            "matrix": {
                                "ruby-version": ["2.7", "3.0", "3.1"]
                            }
                        },
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Set up Ruby ${{ matrix.ruby-version }}",
                                "uses": "ruby/setup-ruby@v1",
                                "with": {
                                    "ruby-version": "${{ matrix.ruby-version }}",
                                    "bundler-cache": "true"
                                }
                            },
                            {
                                "name": "Install dependencies",
                                "run": "bundle install"
                            },
                            {
                                "name": "Run tests",
                                "run": "bundle exec rake test"
                            }
                        ]
                    }
                }
            }
        elif project_type == "php":
            workflow = {
                "name": "PHP CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "strategy": {
                            "matrix": {
                                "php-version": ["7.4", "8.0", "8.1"]
                            }
                        },
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Set up PHP ${{ matrix.php-version }}",
                                "uses": "shivammathur/setup-php@v2",
                                "with": {
                                    "php-version": "${{ matrix.php-version }}",
                                    "extensions": "mbstring, xml, ctype, iconv, intl, pdo_sqlite",
                                    "coverage": "xdebug"
                                }
                            },
                            {
                                "name": "Install Composer dependencies",
                                "run": "composer install --prefer-dist --no-progress"
                            },
                            {
                                "name": "Run tests",
                                "run": "vendor/bin/phpunit"
                            }
                        ]
                    }
                }
            }
        elif project_type == "dotnet":
            workflow = {
                "name": ".NET CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "strategy": {
                            "matrix": {
                                "dotnet-version": ["6.0.x", "7.0.x"]
                            }
                        },
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Setup .NET ${{ matrix.dotnet-version }}",
                                "uses": "actions/setup-dotnet@v3",
                                "with": {
                                    "dotnet-version": "${{ matrix.dotnet-version }}"
                                }
                            },
                            {
                                "name": "Restore dependencies",
                                "run": "dotnet restore"
                            },
                            {
                                "name": "Build",
                                "run": "dotnet build --no-restore"
                            },
                            {
                                "name": "Test",
                                "run": "dotnet test --no-build --verbosity normal"
                            }
                        ]
                    }
                }
            }
        elif project_type == "cpp":
            workflow = {
                "name": "C/C++ CI",
                "on": {
                    "push": {
                        "branches": ["main", "master"]
                    },
                    "pull_request": {
                        "branches": ["main", "master"]
                    }
                },
                "jobs": {
                    "build": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {
                                "name": "Checkout code",
                                "uses": "actions/checkout@v3"
                            },
                            {
                                "name": "Configure CMake",
                                "run": "cmake -B ${{github.workspace}}/build -DCMAKE_BUILD_TYPE=Debug"
                            },
                            {
                                "name": "Build",
                                "run": "cmake --build ${{github.workspace}}/build"
                            },
                            {
                                "name": "Test",
                                "working-directory": "${{github.workspace}}/build",
                                "run": "ctest -C Debug"
                            }
                        ]
                    }
                }
            }
        else: # Default empty workflow if project_type is not recognized
             workflow = {
                 "name": f"{project_type} CI", 
                 "on": {
                     "push": {
                         "branches": ["main", "master"]
                     },
                     "pull_request": {
                         "branches": ["main", "master"]
                     }
                 }, 
                 "jobs": {
                     "build": {
                         "runs-on": "ubuntu-latest",
                         "steps": [
                             {
                                 "name": "Checkout code", 
                                 "uses": "actions/checkout@v3"
                             },
                             {
                                 "name": "Build",
                                 "run": "echo 'Add your build commands here'"
                             },
                             {
                                 "name": "Test",
                                 "run": "echo 'Add your test commands here'"
                             }
                         ]
                     }
                 }
             }
    
        # Update with custom settings using deep merge
        if custom_settings:
            workflow = deep_update(workflow, custom_settings)
    
        # Write the workflow file
        workflow_file = workflows_dir / f"{project_type}-ci.yml"
        try:
            with open(workflow_file, 'w') as f:
                yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "github_actions",
                "project_type": project_type,
                "config_file": str(workflow_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write GitHub Actions workflow: {str(e)}",
                "platform": "github_actions",
                "project_type": project_type
            }
    
    async def _generate_gitlab_ci(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate GitLab CI configuration.
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating GitLab CI configuration for {project_type}")
        
        config: Dict[str, Any] = {} # Ensure config is initialized
        # Set default settings based on project type
        if project_type == "python":
            config = {
                "image": "python:3.9",
                "stages": ["test", "build", "deploy"],
                "before_script": [
                    "python -V",
                    "pip install -r requirements.txt"
                ],
                "test": {
                    "stage": "test",
                    "script": [
                        "pip install pytest pytest-cov",
                        "pytest --cov=. --cov-report=xml",
                    ],
                    "artifacts": {
                        "reports": {
                            "coverage_report": {
                                "coverage_format": "cobertura",
                                "path": "coverage.xml"
                            }
                        }
                    }
                },
                "lint": {
                    "stage": "test",
                    "script": [
                        "pip install flake8",
                        "flake8 ."
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "echo 'Building package'",
                        "pip install build",
                        "python -m build"
                    ],
                    "artifacts": {
                        "paths": ["dist/"]
                    }
                }
            }
        elif project_type == "node":
            config = {
                "image": "node:16",
                "stages": ["test", "build", "deploy"],
                "cache": {
                    "paths": ["node_modules/"]
                },
                "install_dependencies": {
                    "stage": "test",
                    "script": ["npm ci"]
                },
                "test": {
                    "stage": "test",
                    "script": ["npm test"]
                },
                "lint": {
                    "stage": "test",
                    "script": ["npm run lint"]
                },
                "build": {
                    "stage": "build",
                    "script": ["npm run build"],
                    "artifacts": {
                        "paths": ["dist/", "build/"]
                    }
                }
            }
        elif project_type == "go":
            config = {
                "image": "golang:1.18",
                "stages": ["test", "build", "deploy"],
                "before_script": [
                    "go version",
                    "go mod download"
                ],
                "test": {
                    "stage": "test",
                    "script": [
                        "go test -v ./..."
                    ]
                },
                "lint": {
                    "stage": "test",
                    "image": "golangci/golangci-lint:latest",
                    "script": [
                        "golangci-lint run"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "go build -o bin/app"
                    ],
                    "artifacts": {
                        "paths": ["bin/"]
                    }
                }
            }
        elif project_type == "rust":
            config = {
                "image": "rust:latest",
                "stages": ["test", "build", "deploy"],
                "cache": {
                    "paths": ["target/"]
                },
                "test": {
                    "stage": "test",
                    "script": [
                        "cargo test"
                    ]
                },
                "lint": {
                    "stage": "test",
                    "script": [
                        "rustup component add clippy",
                        "cargo clippy -- -D warnings"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "cargo build --release"
                    ],
                    "artifacts": {
                        "paths": ["target/release/"]
                    }
                }
            }
        elif project_type == "java":
            config = {
                "image": "maven:latest",
                "stages": ["test", "build", "deploy"],
                "cache": {
                    "paths": [".m2/repository"]
                },
                "test": {
                    "stage": "test",
                    "script": [
                        "mvn test"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "mvn package"
                    ],
                    "artifacts": {
                        "paths": ["target/*.jar"]
                    }
                }
            }
            # Check if it's Gradle
            if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
                config["image"] = "gradle:latest"
                config["cache"]["paths"] = [".gradle"]
                config["test"]["script"] = ["gradle test"]
                config["build"]["script"] = ["gradle build"]
                config["build"]["artifacts"]["paths"] = ["build/libs/*.jar"]
        elif project_type == "ruby":
            config = {
                "image": "ruby:latest",
                "stages": ["test", "build", "deploy"],
                "before_script": [
                    "ruby -v",
                    "bundle install"
                ],
                "test": {
                    "stage": "test",
                    "script": [
                        "bundle exec rake test"
                    ]
                },
                "lint": {
                    "stage": "test",
                    "script": [
                        "bundle exec rubocop"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "bundle exec rake build"
                    ],
                    "artifacts": {
                        "paths": ["pkg/*.gem"]
                    }
                }
            }
        elif project_type == "php":
            config = {
                "image": "php:8.0",
                "stages": ["test", "build", "deploy"],
                "before_script": [
                    "php -v",
                    "composer install"
                ],
                "test": {
                    "stage": "test",
                    "script": [
                        "vendor/bin/phpunit"
                    ]
                },
                "lint": {
                    "stage": "test",
                    "script": [
                        "vendor/bin/phpcs"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "echo 'Building PHP application'"
                    ]
                }
            }
        elif project_type == "dotnet":
            config = {
                "image": "mcr.microsoft.com/dotnet/sdk:6.0",
                "stages": ["test", "build", "deploy"],
                "before_script": [
                    "dotnet restore"
                ],
                "test": {
                    "stage": "test",
                    "script": [
                        "dotnet test"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "dotnet build --no-restore",
                        "dotnet publish -c Release -o publish"
                    ],
                    "artifacts": {
                        "paths": ["publish/"]
                    }
                }
            }
        elif project_type == "cpp":
            config = {
                "image": "gcc:latest",
                "stages": ["test", "build", "deploy"],
                "before_script": [
                    "apt-get update && apt-get install -y cmake"
                ],
                "test": {
                    "stage": "test",
                    "script": [
                        "cmake -B build -DCMAKE_BUILD_TYPE=Debug",
                        "cmake --build build",
                        "cd build && ctest -V"
                    ]
                },
                "build": {
                    "stage": "build",
                    "script": [
                        "cmake -B build -DCMAKE_BUILD_TYPE=Release",
                        "cmake --build build"
                    ],
                    "artifacts": {
                        "paths": ["build/"]
                    }
                }
            }
        else: # Default empty config if project_type is not recognized
            config = {
                "image": "alpine", 
                "stages": ["build", "test"], 
                "build": {
                    "stage": "build",
                    "script": ["echo 'No build defined'"]
                },
                "test": {
                    "stage": "test",
                    "script": ["echo 'No tests defined'"]
                }
            }

        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = path / ".gitlab-ci.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "gitlab_ci",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write GitLab CI config: {str(e)}",
                "platform": "gitlab_ci",
                "project_type": project_type
            }
    
    async def _generate_jenkins(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Jenkins configuration (Jenkinsfile).
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating Jenkins configuration for {project_type}")
        
        # Set Jenkinsfile content based on project type
        content = ""
        
        if project_type == "python":
            content = """
pipeline {
    agent {
        docker {
            image 'python:3.9'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pip install pytest pytest-cov'
                sh 'pytest --cov=. --cov-report=xml'
            }
            post {
                always {
                    junit 'pytest-results.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }
        stage('Lint') {
            steps {
                sh 'pip install flake8'
                sh 'flake8 .'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "node":
            content = """
pipeline {
    agent {
        docker {
            image 'node:16'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'npm ci'
                sh 'npm run build --if-present'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
        stage('Lint') {
            steps {
                sh 'npm run lint --if-present'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "go":
            content = """
pipeline {
    agent {
        docker {
            image 'golang:1.18'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'go mod download'
                sh 'go build -o bin/app'
            }
        }
        stage('Test') {
            steps {
                sh 'go test -v ./...'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "rust":
            content = """
pipeline {
    agent {
        docker {
            image 'rust:latest'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'cargo build --release'
            }
        }
        stage('Test') {
            steps {
                sh 'cargo test'
            }
        }
        stage('Lint') {
            steps {
                sh 'rustup component add clippy'
                sh 'cargo clippy -- -D warnings'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "java":
            if (path / "pom.xml").exists():
                content = """
pipeline {
    agent {
        docker {
            image 'maven:latest'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
        stage('Test') {
            steps {
                sh 'mvn test'
            }
            post {
                always {
                    junit '**/target/surefire-reports/*.xml'
                }
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
            else:
                content = """
pipeline {
    agent {
        docker {
            image 'gradle:latest'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'gradle build'
            }
        }
        stage('Test') {
            steps {
                sh 'gradle test'
            }
            post {
                always {
                    junit '**/build/test-results/**/*.xml'
                }
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "ruby":
            content = """
pipeline {
    agent {
        docker {
            image 'ruby:latest'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'bundle install'
            }
        }
        stage('Test') {
            steps {
                sh 'bundle exec rake test'
            }
        }
        stage('Lint') {
            steps {
                sh 'bundle exec rubocop'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "php":
            content = """
pipeline {
    agent {
        docker {
            image 'php:8.0-cli'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'apt-get update && apt-get install -y git unzip'
                sh 'php -r "copy(\\'https://getcomposer.org/installer\\', \\'composer-setup.php\\');"'
                sh 'php composer-setup.php --install-dir=/usr/local/bin --filename=composer'
                sh 'composer install'
            }
        }
        stage('Test') {
            steps {
                sh 'vendor/bin/phpunit'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "dotnet":
            content = """
pipeline {
    agent {
        docker {
            image 'mcr.microsoft.com/dotnet/sdk:6.0'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'dotnet restore'
                sh 'dotnet build'
            }
        }
        stage('Test') {
            steps {
                sh 'dotnet test --logger:"trx;LogFileName=testresults.trx"'
            }
            post {
                always {
                    mstest testResultsFile: 'testresults.trx'
                }
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        elif project_type == "cpp":
            content = """
pipeline {
    agent {
        docker {
            image 'gcc:latest'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'apt-get update && apt-get install -y cmake'
                sh 'cmake -B build -DCMAKE_BUILD_TYPE=Release'
                sh 'cmake --build build'
            }
        }
        stage('Test') {
            steps {
                sh 'cd build && ctest -V'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying to production...'
                // Add deployment steps here
            }
        }
    }
}
"""
        else:
            content = """
pipeline {
    agent any
    
    stages {
        stage('Build') {
            steps {
                echo 'Building...'
                // Add build steps here
            }
        }
        stage('Test') {
            steps {
                echo 'Testing...'
                // Add test steps here
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying...'
                // Add deployment steps here
            }
        }
    }
}
"""

        # Update with custom settings for Jenkins
        if custom_settings:
            # For Jenkins, we need to do template-based modification since it's a raw string
            content = self._apply_jenkins_customizations(content, custom_settings)
        
        # Write the Jenkinsfile
        jenkinsfile_path = path / "Jenkinsfile"
        try:
            with open(jenkinsfile_path, 'w') as f:
                f.write(content.strip())
            
            return {
                "success": True,
                "platform": "jenkins",
                "project_type": project_type,
                "config_file": str(jenkinsfile_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write Jenkinsfile: {str(e)}",
                "platform": "jenkins",
                "project_type": project_type
            }
    
    def _apply_jenkins_customizations(self, content: str, custom_settings: Dict[str, Any]) -> str:
        """
        Apply customizations to a Jenkinsfile content.
        
        Args:
            content: Original Jenkinsfile content
            custom_settings: Custom settings to apply
            
        Returns:
            Modified Jenkinsfile content
        """
        modified_content = content
        
        # Handle agent customization
        if "agent" in custom_settings:
            agent_value = custom_settings["agent"]
            if isinstance(agent_value, str):
                if agent_value in ["any", "none"]:
                    # Replace the agent block with simple value
                    modified_content = re.sub(r'agent\s+\{[^}]*\}', f'agent {agent_value}', modified_content)
                else:
                    # Custom agent string (like a label)
                    modified_content = re.sub(r'agent\s+\{[^}]*\}', f'agent {{ label "{agent_value}" }}', modified_content)
            elif isinstance(agent_value, dict):
                # Create custom agent block
                agent_type = list(agent_value.keys())[0]
                agent_config = agent_value[agent_type]
                if agent_type == "docker":
                    if isinstance(agent_config, str):
                        # Simple docker image
                        agent_block = f'agent {{\n        docker {{\n            image \'{agent_config}\'\n        }}\n    }}'
                    else:
                        # Detailed docker configuration
                        agent_block = f'agent {{\n        docker {{\n'
                        for k, v in agent_config.items():
                            if isinstance(v, str):
                                agent_block += f'            {k} \'{v}\'\n'
                            else:
                                agent_block += f'            {k} {v}\n'
                        agent_block += '        }\n    }'
                    modified_content = re.sub(r'agent\s+\{[^}]*\}', agent_block, modified_content)
        
        # Handle stages customization
        if "stages" in custom_settings:
            # For each custom stage, find the corresponding stage in the original content
            for stage_name, stage_config in custom_settings["stages"].items():
                # Look for the stage in the content
                stage_pattern = rf'stage\([\'"]({stage_name}|{stage_name.title()})[\'"])\s*\{{[^{{}}]*}}'
                stage_match = re.search(stage_pattern, modified_content)
                
                if stage_match:
                    # If stage exists, modify it
                    original_stage = stage_match.group(0)
                    
                    # Create modified stage
                    if "steps" in stage_config:
                        # Replace steps
                        steps_block = "            steps {\n"
                        for step in stage_config["steps"]:
                            if isinstance(step, str):
                                steps_block += f'                {step}\n'
                            elif isinstance(step, dict):
                                step_type = list(step.keys())[0]
                                step_value = step[step_type]
                                if isinstance(step_value, str):
                                    steps_block += f'                {step_type} \'{step_value}\'\n'
                                else:
                                    steps_block += f'                {step_type} {json.dumps(step_value)}\n'
                        steps_block += "            }"
                        
                        # Replace steps in original stage
                        modified_stage = re.sub(r'steps\s*\{[^{}]*\}', steps_block, original_stage)
                        modified_content = modified_content.replace(original_stage, modified_stage)
                else:
                    # If stage doesn't exist, add it
                    new_stage = f"""
        stage('{stage_name}') {{
            steps {{
"""
                    if "steps" in stage_config:
                        for step in stage_config["steps"]:
                            if isinstance(step, str):
                                new_stage += f'                {step}\n'
                            elif isinstance(step, dict):
                                step_type = list(step.keys())[0]
                                step_value = step[step_type]
                                if isinstance(step_value, str):
                                    new_stage += f'                {step_type} \'{step_value}\'\n'
                                else:
                                    new_stage += f'                {step_type} {json.dumps(step_value)}\n'
                    new_stage += """            }
        }"""
                    
                    # Find the last stage and add the new stage after it
                    last_stage_match = re.search(r'(stage\([^\)]+\)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*\n\s*\}', modified_content)
                    if last_stage_match:
                        last_stage = last_stage_match.group(1)
                        modified_content = modified_content.replace(last_stage, last_stage + new_stage)
        
        # Handle additional pipeline options
        if "options" in custom_settings:
            options_block = "    options {\n"
            for option_name, option_value in custom_settings["options"].items():
                if isinstance(option_value, bool):
                    if option_value:
                        options_block += f"        {option_name}()\n"
                elif isinstance(option_value, (int, float)):
                    options_block += f"        {option_name}({option_value})\n"
                elif isinstance(option_value, str):
                    options_block += f"        {option_name}('{option_value}')\n"
                else:
                    options_block += f"        {option_name}({json.dumps(option_value)})\n"
            options_block += "    }\n"
            
            # Add options block after agent block
            agent_end = re.search(r'agent\s+(?:\{[^}]*\}|any|none)\s*', modified_content)
            if agent_end:
                insert_point = agent_end.end()
                modified_content = modified_content[:insert_point] + "\n" + options_block + modified_content[insert_point:]
        
        return modified_content
    
    async def _generate_travis(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Travis CI configuration.
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating Travis CI configuration for {project_type}")
        
        config: Dict[str, Any] = {} # Ensure config is initialized
        # Set default settings based on project type
        if project_type == "python":
            config = {
                "language": "python",
                "python": ["3.8", "3.9", "3.10"],
                "install": [
                    "pip install -r requirements.txt",
                    "pip install pytest pytest-cov flake8"
                ],
                "script": [
                    "flake8 .",
                    "pytest --cov=."
                ],
                "after_success": [
                    "bash <(curl -s https://codecov.io/bash)"
                ]
            }
        elif project_type == "node":
            config = {
                "language": "node_js",
                "node_js": ["14", "16", "18"],
                "cache": "npm",
                "install": [
                    "npm ci"
                ],
                "script": [
                    "npm run lint --if-present",
                    "npm run build --if-present",
                    "npm test"
                ]
            }
        elif project_type == "go":
            config = {
                "language": "go",
                "go": ["1.17.x", "1.18.x"],
                "install": [
                    "go mod download"
                ],
                "script": [
                    "go build -v ./...",
                    "go test -v -race ./..."
                ]
            }
        elif project_type == "rust":
            config = {
                "language": "rust",
                "rust": ["stable", "beta"],
                "cache": "cargo",
                "before_script": [
                    "rustup component add clippy"
                ],
                "script": [
                    "cargo build --verbose",
                    "cargo test --verbose",
                    "cargo clippy -- -D warnings"
                ]
            }
        elif project_type == "java":
            if (path / "pom.xml").exists():
                config = {
                    "language": "java",
                    "jdk": ["openjdk11", "openjdk17"],
                    "script": [
                        "mvn clean verify"
                    ],
                    "cache": {
                        "directories": ["$HOME/.m2"]
                    }
                }
            else:
                config = {
                    "language": "java",
                    "jdk": ["openjdk11", "openjdk17"],
                    "before_cache": [
                        "rm -f  $HOME/.gradle/caches/modules-2/modules-2.lock",
                        "rm -fr $HOME/.gradle/caches/*/plugin-resolution/"
                    ],
                    "cache": {
                        "directories": [
                            "$HOME/.gradle/caches/",
                            "$HOME/.gradle/wrapper/"
                        ]
                    },
                    "script": [
                        "./gradlew build"
                    ]
                }
        elif project_type == "ruby":
            config = {
                "language": "ruby",
                "rvm": ["2.7", "3.0", "3.1"],
                "install": [
                    "bundle install"
                ],
                "script": [
                    "bundle exec rake test"
                ]
            }
        elif project_type == "php":
            config = {
                "language": "php",
                "php": ["7.4", "8.0", "8.1"],
                "install": [
                    "composer install"
                ],
                "script": [
                    "vendor/bin/phpunit"
                ]
            }
        elif project_type == "dotnet":
            config = {
                "language": "csharp",
                "mono": "none",
                "dotnet": ["6.0", "7.0"],
                "script": [
                    "dotnet restore",
                    "dotnet build",
                    "dotnet test"
                ]
            }
        elif project_type == "cpp":
            config = {
                "language": "cpp",
                "compiler": ["gcc", "clang"],
                "before_script": [
                    "mkdir -p build",
                    "cd build",
                    "cmake .."
                ],
                "script": [
                    "cmake --build .",
                    "ctest -V"
                ]
            }
        else: # Default empty config if project_type is not recognized
            config = {
                "language": "generic", 
                "script": ["echo 'No script defined'"]
            }
        
        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = path / ".travis.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "travis",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write Travis CI config: {str(e)}",
                "platform": "travis",
                "project_type": project_type
            }
    
    async def _generate_circle_ci(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate CircleCI configuration.
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating CircleCI configuration for {project_type}")
        
        # Create .circleci directory
        circleci_dir = path / ".circleci"
        if not circleci_dir.exists():
            os.makedirs(circleci_dir, exist_ok=True)
        
        config: Dict[str, Any] = {} # Ensure config is initialized
        # Set default settings based on project type
        if project_type == "python":
            config = {
                "version": 2.1,
                "orbs": {
                    "python": "circleci/python@1.5"
                },
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "cimg/python:3.9"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "python/install-packages": {
                                    "pkg-manager": "pip",
                                    "packages": [
                                        "pytest",
                                        "pytest-cov"
                                    ]
                                }
                            },
                            {
                                "run": {
                                    "name": "Install dependencies",
                                    "command": "pip install -r requirements.txt"
                                }
                            },
                            {
                                "run": {
                                    "name": "Run tests",
                                    "command": "pytest --cov=. --cov-report=xml"
                                }
                            },
                            {
                                "store_artifacts": {
                                    "path": "coverage.xml"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "node":
            config = {
                "version": 2.1,
                "orbs": {
                    "node": "circleci/node@5.0.0"
                },
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "cimg/node:16.14"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "node/install-packages": {
                                    "pkg-manager": "npm"
                                }
                            },
                            {
                                "run": {
                                    "name": "Run tests",
                                    "command": "npm test"
                                }
                            },
                            {
                                "run": {
                                    "name": "Run lint",
                                    "command": "npm run lint --if-present"
                                }
                            },
                            {
                                "run": {
                                    "name": "Build",
                                    "command": "npm run build --if-present"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "go":
            config = {
                "version": 2.1,
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "cimg/go:1.18"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "run": {
                                    "name": "Download dependencies",
                                    "command": "go mod download"
                                }
                            },
                            {
                                "run": {
                                    "name": "Build",
                                    "command": "go build -v ./..."
                                }
                            },
                            {
                                "run": {
                                    "name": "Run tests",
                                    "command": "go test -v -race ./..."
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "rust":
            config = {
                "version": 2.1,
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "cimg/rust:1.60"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "run": {
                                    "name": "Version information",
                                    "command": "rustc --version; cargo --version; rustup --version"
                                }
                            },
                            {
                                "run": {
                                    "name": "Build",
                                    "command": "cargo build --verbose"
                                }
                            },
                            {
                                "run": {
                                    "name": "Run tests",
                                    "command": "cargo test --verbose"
                                }
                            },
                            {
                                "run": {
                                    "name": "Lint",
                                    "command": "rustup component add clippy && cargo clippy -- -D warnings"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "java":
            if (path / "pom.xml").exists():
                config = {
                    "version": 2.1,
                    "jobs": {
                        "build-and-test": {
                            "docker": [
                                {"image": "cimg/openjdk:17.0"}
                            ],
                            "steps": [
                                "checkout",
                                {
                                    "run": {
                                        "name": "Build",
                                        "command": "mvn -B -DskipTests clean package"
                                    }
                                },
                                {
                                    "run": {
                                        "name": "Test",
                                        "command": "mvn test"
                                    }
                                },
                                {
                                    "store_test_results": {
                                        "path": "target/surefire-reports"
                                    }
                                }
                            ]
                        }
                    },
                    "workflows": {
                        "main": {
                            "jobs": [
                                "build-and-test"
                            ]
                        }
                    }
                }
            else:
                config = {
                    "version": 2.1,
                    "jobs": {
                        "build-and-test": {
                            "docker": [
                                {"image": "cimg/openjdk:17.0"}
                            ],
                            "steps": [
                                "checkout",
                                {
                                    "run": {
                                        "name": "Build",
                                        "command": "./gradlew build -x test"
                                    }
                                },
                                {
                                    "run": {
                                        "name": "Test",
                                        "command": "./gradlew test"
                                    }
                                },
                                {
                                    "store_test_results": {
                                        "path": "build/test-results/test"
                                    }
                                }
                            ]
                        }
                    },
                    "workflows": {
                        "main": {
                            "jobs": [
                                "build-and-test"
                            ]
                        }
                    }
                }
        elif project_type == "ruby":
            config = {
                "version": 2.1,
                "orbs": {
                    "ruby": "circleci/ruby@1.4"
                },
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "cimg/ruby:3.1-node"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "ruby/install-deps": {}
                            },
                            {
                                "run": {
                                    "name": "Run tests",
                                    "command": "bundle exec rake test"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "php":
            config = {
                "version": 2.1,
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "cimg/php:8.1"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "run": {
                                    "name": "Install dependencies",
                                    "command": "composer install"
                                }
                            },
                            {
                                "run": {
                                    "name": "Run tests",
                                    "command": "vendor/bin/phpunit"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "dotnet":
            config = {
                "version": 2.1,
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "mcr.microsoft.com/dotnet/sdk:6.0"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "run": {
                                    "name": "Restore",
                                    "command": "dotnet restore"
                                }
                            },
                            {
                                "run": {
                                    "name": "Build",
                                    "command": "dotnet build --no-restore"
                                }
                            },
                            {
                                "run": {
                                    "name": "Test",
                                    "command": "dotnet test --no-build --verbosity normal"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        elif project_type == "cpp":
            config = {
                "version": 2.1,
                "jobs": {
                    "build-and-test": {
                        "docker": [
                            {"image": "gcc:latest"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "run": {
                                    "name": "Install dependencies",
                                    "command": "apt-get update && apt-get install -y cmake"
                                }
                            },
                            {
                                "run": {
                                    "name": "Configure",
                                    "command": "cmake -B build -DCMAKE_BUILD_TYPE=Release"
                                }
                            },
                            {
                                "run": {
                                    "name": "Build",
                                    "command": "cmake --build build"
                                }
                            },
                            {
                                "run": {
                                    "name": "Test",
                                    "command": "cd build && ctest -V"
                                }
                            }
                        ]
                    }
                },
                "workflows": {
                    "main": {
                        "jobs": [
                            "build-and-test"
                        ]
                    }
                }
            }
        else: # Default empty config if project_type is not recognized
            config = {
                "version": 2.1, 
                "jobs": {
                    "build": {
                        "docker": [
                            {"image": "cimg/base:stable"}
                        ],
                        "steps": [
                            "checkout",
                            {
                                "run": {
                                    "name": "Build and test",
                                    "command": "echo 'Add your build commands here'"
                                }
                            }
                        ]
                    }
                }, 
                "workflows": {
                    "main": {
                        "jobs": [
                            "build"
                        ]
                    }
                }
            }
        
        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = circleci_dir / "config.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "circle_ci",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write CircleCI config: {str(e)}",
                "platform": "circle_ci",
                "project_type": project_type
            }
    
    async def _generate_azure_pipelines(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Azure Pipelines configuration.
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating Azure Pipelines configuration for {project_type}")
        
        config: Dict[str, Any] = {
            "trigger": ["main", "master"],
            "pr": ["main", "master"]
        }
        
        # Set up pool
        config["pool"] = {"vmImage": "ubuntu-latest"}
        
        # Set up stages based on project type
        if project_type == "python":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "task": "UsePythonVersion@0",
                                    "inputs": {
                                        "versionSpec": "3.9",
                                        "addToPath": "true"
                                    },
                                    "displayName": "Use Python 3.9"
                                },
                                {
                                    "script": "python -m pip install --upgrade pip",
                                    "displayName": "Install pip"
                                },
                                {
                                    "script": "pip install -r requirements.txt",
                                    "displayName": "Install dependencies"
                                },
                                {
                                    "script": "pip install pytest pytest-cov pytest-azurepipelines",
                                    "displayName": "Install testing tools"
                                },
                                {
                                    "script": "pytest --cov=.",
                                    "displayName": "Run tests with coverage"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "node":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "task": "NodeTool@0",
                                    "inputs": {
                                        "versionSpec": "16.x"
                                    },
                                    "displayName": "Install Node.js"
                                },
                                {
                                    "script": "npm ci",
                                    "displayName": "Install dependencies"
                                },
                                {
                                    "script": "npm run lint --if-present",
                                    "displayName": "Lint"
                                },
                                {
                                    "script": "npm run build --if-present",
                                    "displayName": "Build"
                                },
                                {
                                    "script": "npm test",
                                    "displayName": "Test"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "dotnet":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "task": "UseDotNet@2",
                                    "inputs": {
                                        "packageType": "sdk",
                                        "version": "6.0.x"
                                    },
                                    "displayName": "Use .NET 6.0"
                                },
                                {
                                    "task": "DotNetCoreCLI@2",
                                    "inputs": {
                                        "command": "restore"
                                    },
                                    "displayName": "Restore NuGet packages"
                                },
                                {
                                    "task": "DotNetCoreCLI@2",
                                    "inputs": {
                                        "command": "build",
                                        "arguments": "--configuration Release"
                                    },
                                    "displayName": "Build"
                                },
                                {
                                    "task": "DotNetCoreCLI@2",
                                    "inputs": {
                                        "command": "test",
                                        "arguments": "--configuration Release --collect:\"XPlat Code Coverage\""
                                    },
                                    "displayName": "Test"
                                },
                                {
                                    "task": "PublishCodeCoverageResults@1",
                                    "inputs": {
                                        "codeCoverageTool": "Cobertura",
                                        "summaryFileLocation": "$(Agent.TempDirectory)/**/coverage.cobertura.xml"
                                    },
                                    "displayName": "Publish code coverage"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "java":
            maven_config = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "MavenBuildAndTest",
                            "steps": [
                                {
                                    "task": "JavaToolInstaller@0",
                                    "inputs": {
                                        "versionSpec": "11",
                                        "jdkArchitectureOption": "x64",
                                        "jdkSourceOption": "PreInstalled"
                                    },
                                    "displayName": "Set up JDK 11"
                                },
                                {
                                    "task": "Maven@3",
                                    "inputs": {
                                        "mavenPomFile": "pom.xml",
                                        "goals": "package",
                                        "options": "-B",
                                        "publishJUnitResults": "true",
                                        "testResultsFiles": "**/surefire-reports/TEST-*.xml"
                                    },
                                    "displayName": "Build with Maven"
                                }
                            ]
                        }
                    ]
                }
            ]
            
            gradle_config = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "GradleBuildAndTest",
                            "steps": [
                                {
                                    "task": "JavaToolInstaller@0",
                                    "inputs": {
                                        "versionSpec": "11",
                                        "jdkArchitectureOption": "x64",
                                        "jdkSourceOption": "PreInstalled"
                                    },
                                    "displayName": "Set up JDK 11"
                                },
                                {
                                    "task": "Gradle@2",
                                    "inputs": {
                                        "gradleWrapperFile": "gradlew",
                                        "tasks": "build",
                                        "publishJUnitResults": "true",
                                        "testResultsFiles": "**/TEST-*.xml"
                                    },
                                    "displayName": "Build with Gradle"
                                }
                            ]
                        }
                    ]
                }
            ]
            
            # Check if it's Gradle or Maven
            if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
                config["stages"] = gradle_config
            else:
                config["stages"] = maven_config
                
        elif project_type == "go":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "task": "GoTool@0",
                                    "inputs": {
                                        "version": "1.18"
                                    },
                                    "displayName": "Set up Go"
                                },
                                {
                                    "script": "go mod download",
                                    "displayName": "Download dependencies"
                                },
                                {
                                    "script": "go build -v ./...",
                                    "displayName": "Build"
                                },
                                {
                                    "script": "go test -v -race ./...",
                                    "displayName": "Test"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "rust":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "script": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
                                    "displayName": "Install Rust"
                                },
                                {
                                    "script": "source $HOME/.cargo/env && rustup component add clippy",
                                    "displayName": "Add Clippy"
                                },
                                {
                                    "script": "source $HOME/.cargo/env && cargo build --verbose",
                                    "displayName": "Build"
                                },
                                {
                                    "script": "source $HOME/.cargo/env && cargo test --verbose",
                                    "displayName": "Test"
                                },
                                {
                                    "script": "source $HOME/.cargo/env && cargo clippy -- -D warnings",
                                    "displayName": "Lint"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "php":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "script": "sudo apt-get update && sudo apt-get install -y php-cli php-xml php-mbstring",
                                    "displayName": "Install PHP"
                                },
                                {
                                    "script": "php -r \"copy('https://getcomposer.org/installer', 'composer-setup.php');\"",
                                    "displayName": "Download Composer"
                                },
                                {
                                    "script": "php composer-setup.php --install-dir=/usr/local/bin --filename=composer",
                                    "displayName": "Install Composer"
                                },
                                {
                                    "script": "composer install",
                                    "displayName": "Install dependencies"
                                },
                                {
                                    "script": "vendor/bin/phpunit",
                                    "displayName": "Run tests"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "ruby":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "task": "UseRubyVersion@0",
                                    "inputs": {
                                        "versionSpec": "3.1",
                                        "addToPath": "true"
                                    },
                                    "displayName": "Use Ruby 3.1"
                                },
                                {
                                    "script": "gem install bundler",
                                    "displayName": "Install bundler"
                                },
                                {
                                    "script": "bundle install",
                                    "displayName": "Install dependencies"
                                },
                                {
                                    "script": "bundle exec rake test",
                                    "displayName": "Run tests"
                                }
                            ]
                        }
                    ]
                }
            ]
        elif project_type == "cpp":
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "BuildAndTest",
                            "steps": [
                                {
                                    "script": "sudo apt-get update && sudo apt-get install -y build-essential cmake",
                                    "displayName": "Install dependencies"
                                },
                                {
                                    "script": "cmake -B build -DCMAKE_BUILD_TYPE=Release",
                                    "displayName": "Configure CMake"
                                },
                                {
                                    "script": "cmake --build build",
                                    "displayName": "Build"
                                },
                                {
                                    "script": "cd build && ctest -V",
                                    "displayName": "Run tests"
                                }
                            ]
                        }
                    ]
                }
            ]
        else:
            config["stages"] = [
                {
                    "stage": "Build",
                    "jobs": [
                        {
                            "job": "DefaultBuild",
                            "steps": [
                                {
                                    "script": "echo 'Add build commands for your project type'",
                                    "displayName": "Build placeholder"
                                },
                                {
                                    "script": "echo 'Add test commands for your project type'",
                                    "displayName": "Test placeholder"
                                }
                            ]
                        }
                    ]
                }
            ]
        
        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = path / "azure-pipelines.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "azure_pipelines",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write Azure Pipelines config: {str(e)}",
                "platform": "azure_pipelines",
                "project_type": project_type
            }
    
    async def _generate_bitbucket_pipelines(
        self, 
        path: Path,
        project_type: str,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Bitbucket Pipelines configuration.
        
        Args:
            path: Path to the project
            project_type: Project type
            custom_settings: Optional custom settings
            
        Returns:
            Dictionary with the generation result
        """
        self._logger.info(f"Generating Bitbucket Pipelines configuration for {project_type}")
        
        config: Dict[str, Any] = {
            "image": "", # Will be set based on project type
            "pipelines": {
                "default": [],
                "branches": {
                    "main": [],
                    "master": []
                },
                "pull-requests": [],
                "tags": []
            }
        }
        
        # Set config based on project type
        if project_type == "python":
            config["image"] = "python:3.9"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["pip"],
                        "script": [
                            "pip install -r requirements.txt",
                            "pip install pytest pytest-cov",
                            "pytest --cov=."
                        ],
                        "after-script": [
                            "pip install codecov",
                            "codecov"
                        ]
                    }
                }
            ]
        elif project_type == "node":
            config["image"] = "node:16"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["node"],
                        "script": [
                            "npm ci",
                            "npm run lint --if-present",
                            "npm run build --if-present",
                            "npm test"
                        ]
                    }
                }
            ]
        elif project_type == "go":
            config["image"] = "golang:1.18"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "go mod download",
                            "go build -v ./...",
                            "go test -v -race ./..."
                        ]
                    }
                }
            ]
        elif project_type == "rust":
            config["image"] = "rust:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["cargo"],
                        "script": [
                            "rustup component add clippy",
                            "cargo build --verbose",
                            "cargo test --verbose",
                            "cargo clippy -- -D warnings"
                        ]
                    }
                }
            ]
        elif project_type == "java":
            if (path / "pom.xml").exists():
                config["image"] = "maven:latest"
                default_pipe = [
                    {
                        "step": {
                            "name": "Build and test",
                            "caches": ["maven"],
                            "script": [
                                "mvn clean package"
                            ]
                        }
                    }
                ]
            else:
                config["image"] = "gradle:latest"
                default_pipe = [
                    {
                        "step": {
                            "name": "Build and test",
                            "caches": ["gradle"],
                            "script": [
                                "gradle build"
                            ]
                        }
                    }
                ]
        elif project_type == "ruby":
            config["image"] = "ruby:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["bundler"],
                        "script": [
                            "bundle install",
                            "bundle exec rake test"
                        ]
                    }
                }
            ]
        elif project_type == "php":
            config["image"] = "php:8.0"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "caches": ["composer"],
                        "script": [
                            "apt-get update && apt-get install -y git unzip",
                            "curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer",
                            "composer install",
                            "vendor/bin/phpunit"
                        ]
                    }
                }
            ]
        elif project_type == "dotnet":
            config["image"] = "mcr.microsoft.com/dotnet/sdk:6.0"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "dotnet restore",
                            "dotnet build",
                            "dotnet test"
                        ]
                    }
                }
            ]
        elif project_type == "cpp":
            config["image"] = "gcc:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "apt-get update && apt-get install -y cmake",
                            "cmake -B build -DCMAKE_BUILD_TYPE=Release",
                            "cmake --build build",
                            "cd build && ctest -V"
                        ]
                    }
                }
            ]
        else:
            config["image"] = "alpine:latest"
            default_pipe = [
                {
                    "step": {
                        "name": "Build and test",
                        "script": [
                            "echo 'Add your build commands here'",
                            "echo 'Add your test commands here'"
                        ]
                    }
                }
            ]
        
        # Set up the pipeline steps
        config["pipelines"]["default"] = default_pipe
        config["pipelines"]["branches"]["main"] = default_pipe
        config["pipelines"]["branches"]["master"] = default_pipe
        config["pipelines"]["pull-requests"] = default_pipe
        
        # Add deployment step for tags
        deploy_pipe = list(default_pipe)
        deploy_pipe.append({
            "step": {
                "name": "Deploy on tag",
                "deployment": "production",
                "script": [
                    "echo 'Deploying to production...'"
                ]
            }
        })
        config["pipelines"]["tags"] = deploy_pipe
        
        # Update with custom settings using deep merge
        if custom_settings:
            config = deep_update(config, custom_settings)
        
        # Write the config file
        config_file = path / "bitbucket-pipelines.yml"
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            return {
                "success": True,
                "platform": "bitbucket_pipelines",
                "project_type": project_type,
                "config_file": str(config_file)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write Bitbucket Pipelines config: {str(e)}",
                "platform": "bitbucket_pipelines",
                "project_type": project_type
            }
    
    async def create_complete_pipeline(
        self,
        project_path: Union[str, Path],
        platform: str,
        pipeline_type: str = "full",  # "full", "build-only", "deploy-only"
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete CI/CD pipeline for a project.
        
        Args:
            project_path: Path to the project
            platform: CI/CD platform to use
            pipeline_type: Type of pipeline to create
            custom_settings: Custom settings for the pipeline
            
        Returns:
            Dictionary with the creation result
        """
        project_path = Path(project_path)
        self._logger.info(f"Creating complete {pipeline_type} pipeline for {project_path} on {platform}")
        
        # Detect project type
        detection_result = await self.detect_project_type(project_path)
        if not detection_result.get("detected"):
            return {
                "success": False,
                "error": detection_result.get("error", "Could not detect project type"),
                "platform": platform
            }
        
        project_type = detection_result["project_type"]
        
        # Determine pipeline steps based on project type and pipeline type
        pipeline_steps = await self._determine_pipeline_steps(
            project_type, 
            platform, 
            pipeline_type
        )
        
        # Merge with custom settings
        if custom_settings:
            pipeline_steps = deep_update(pipeline_steps, custom_settings)
        
        # Generate configuration
        result = await self.generate_ci_configuration(
            path=project_path,
            platform=platform,
            project_type=project_type,
            custom_settings=pipeline_steps
        )
        
        if not result.get("success"):
            return result
        
        # Set up additional required files
        if pipeline_type == "full" or pipeline_type == "deploy-only":
            # Set up deployment configuration if needed
            deploy_result = await self._setup_deployment_config(
                project_path, 
                platform, 
                project_type,
                pipeline_steps
            )
            
            if deploy_result:
                result["deployment_config"] = deploy_result
        
        # Set up testing configurations if needed
        if pipeline_type == "full" or pipeline_type == "build-only":
            testing_result = await self._setup_testing_config(
                project_path,
                project_type,
                pipeline_steps
            )
            
            if testing_result:
                result["testing_config"] = testing_result
        
        return result
    
    async def _determine_pipeline_steps(
        self,
        project_type: str,
        platform: str,
        pipeline_type: str
    ) -> Dict[str, Any]:
        """
        Determine the steps for a CI/CD pipeline.
        
        Args:
            project_type: Type of project
            platform: CI/CD platform
            pipeline_type: Type of pipeline
            
        Returns:
            Dictionary with pipeline steps
        """
        self._logger.debug(f"Determining pipeline steps for {project_type} on {platform} ({pipeline_type})")
        
        # Base steps common to all pipelines
        pipeline_steps = {
            "build": True,
            "test": True,
            "lint": True,
            "security_scan": pipeline_type == "full",
            "package": pipeline_type != "build-only",
            "deploy": pipeline_type != "build-only",
            "notify": pipeline_type == "full"
        }
        
        # Add platform-specific settings
        if platform == "github_actions":
            # GitHub Actions specific settings
            pipeline_steps["triggers"] = {
                "push": ["main", "master"],
                "pull_request": ["main", "master"],
                "manual": pipeline_type != "build-only"
            }
            
            # Add deployment environment based on pipeline type
            if pipeline_type != "build-only":
                pipeline_steps["environments"] = ["staging"]
                if pipeline_type == "full":
                    pipeline_steps["environments"].append("production")
        
        elif platform == "gitlab_ci":
            # GitLab CI specific settings
            pipeline_steps["stages"] = ["build", "test", "package"]
            if pipeline_type != "build-only":
                pipeline_steps["stages"].extend(["deploy", "verify"])
            
            pipeline_steps["cache"] = True
            pipeline_steps["artifacts"] = True
        
        # Add project-type specific settings
        if project_type == "python":
            pipeline_steps["python_versions"] = ["3.8", "3.9", "3.10"]
            pipeline_steps["test_command"] = "pytest --cov"
            pipeline_steps["lint_command"] = "flake8"
        
        elif project_type == "node":
            pipeline_steps["node_versions"] = ["14", "16", "18"]
            pipeline_steps["test_command"] = "npm test"
            pipeline_steps["lint_command"] = "npm run lint"
        
        elif project_type == "go":
            pipeline_steps["go_versions"] = ["1.18", "1.19"]
            pipeline_steps["test_command"] = "go test ./..."
            pipeline_steps["lint_command"] = "golangci-lint run"
        
        elif project_type == "java":
            pipeline_steps["java_versions"] = ["11", "17"]
            pipeline_steps["test_command"] = "mvn test"
            pipeline_steps["lint_command"] = "mvn checkstyle:check"
        
        elif project_type == "rust":
            pipeline_steps["rust_versions"] = ["stable", "beta"]
            pipeline_steps["test_command"] = "cargo test"
            pipeline_steps["lint_command"] = "cargo clippy -- -D warnings"
            
        elif project_type == "ruby":
            pipeline_steps["ruby_versions"] = ["2.7", "3.0", "3.1"]
            pipeline_steps["test_command"] = "bundle exec rake test"
            pipeline_steps["lint_command"] = "bundle exec rubocop"
            
        elif project_type == "php":
            pipeline_steps["php_versions"] = ["7.4", "8.0", "8.1"]
            pipeline_steps["test_command"] = "vendor/bin/phpunit"
            pipeline_steps["lint_command"] = "vendor/bin/phpcs"
            
        elif project_type == "dotnet":
            pipeline_steps["dotnet_versions"] = ["6.0", "7.0"]
            pipeline_steps["test_command"] = "dotnet test"
            pipeline_steps["lint_command"] = "dotnet format --verify-no-changes"
            
        elif project_type == "cpp":
            pipeline_steps["compilers"] = ["gcc", "clang"]
            pipeline_steps["test_command"] = "ctest -V"
            pipeline_steps["lint_command"] = "cppcheck ."
            
        return pipeline_steps
    
    async def _setup_deployment_config(
        self,
        project_path: Path,
        platform: str,
        project_type: str,
        pipeline_steps: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up deployment configuration files.
        
        Args:
            project_path: Path to the project
            platform: CI/CD platform
            project_type: Type of project
            pipeline_steps: Pipeline steps configuration
            
        Returns:
            Dictionary with deployment configuration result
        """
        self._logger.info(f"Setting up deployment configuration for {project_type}")
        
        # Create deployment configuration based on project type
        if project_type == "python":
            # For Python, create a simple deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for Python project
echo "Deploying Python application..."

# Install dependencies
pip install -r requirements.txt

# Check for common deployment frameworks
if [ -f "manage.py" ]; then
    echo "Django project detected"
    python manage.py migrate
    python manage.py collectstatic --noinput
elif [ -f "app.py" ] || [ -f "wsgi.py" ]; then
    echo "Flask/WSGI project detected"
else
    echo "Generic Python project"
fi

# Reload application (depends on hosting)
if [ -f "gunicorn.pid" ]; then
    echo "Reloading Gunicorn..."
    kill -HUP $(cat gunicorn.pid)
elif command -v systemctl &> /dev/null && systemctl list-units --type=service | grep -q "$(basename $(pwd))"; then
    echo "Restarting service..."
    systemctl restart $(basename $(pwd))
else
    echo "Starting application..."
    # Add your start command here
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "node":
            # For Node.js, create a deployment configuration
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.js"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""// Deployment script for Node.js project
console.log('Deploying Node.js application...');

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Execute shell command and print output
function exec(command) {
    console.log(`> ${command}`);
    try {
        const output = execSync(command, { encoding: 'utf8' });
        if (output) console.log(output);
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
}

// Install dependencies
exec('npm ci --production');

// Check for common frameworks
const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const dependencies = packageJson.dependencies || {};

if (dependencies.next) {
    console.log('Next.js project detected');
    exec('npm run build');
} else if (dependencies.react) {
    console.log('React project detected');
    exec('npm run build');
} else if (dependencies.vue) {
    console.log('Vue.js project detected');
    exec('npm run build');
} else if (dependencies.express) {
    console.log('Express.js project detected');
} else {
    console.log('Generic Node.js project');
}

// Restart application
try {
    if (fs.existsSync('process.pid')) {
        console.log('Reloading application...');
        const pid = fs.readFileSync('process.pid', 'utf8').trim();
        try {
            process.kill(pid, 'SIGUSR2');
            console.log(`Sent SIGUSR2 to process ${pid}`);
        } catch (err) {
            console.log(`Process ${pid} not found, starting fresh`);
            // Start application
            if (fs.existsSync('ecosystem.config.js')) {
                exec('npx pm2 reload ecosystem.config.js');
            } else {
                // Determine main file
                const mainFile = packageJson.main || 'index.js';
                exec(`npx pm2 start ${mainFile} --name ${path.basename(process.cwd())}`);
            }
        }
    } else if (fs.existsSync('ecosystem.config.js')) {
        console.log('Starting with PM2...');
        exec('npx pm2 reload ecosystem.config.js');
    } else {
        console.log('Starting application...');
        // Determine main file
        const mainFile = packageJson.main || 'index.js';
        exec(`npx pm2 start ${mainFile} --name ${path.basename(process.cwd())}`);
    }
} catch (error) {
    console.error(`Error managing application process: ${error.message}`);
}

console.log('Deployment complete!');
""")
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "go":
            # For Go, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for Go project
echo "Deploying Go application..."

# Build the application
go build -o bin/app

# Check if systemd service exists
SERVICE_NAME=$(basename $(pwd))
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Create a systemd service file if needed
    if [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        echo "Creating systemd service..."
        cat > /tmp/$SERVICE_NAME.service <<EOL
[Unit]
Description=$SERVICE_NAME
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/bin/app
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
        sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        sudo systemctl start $SERVICE_NAME
    else
        # Start directly if no service exists and we can't create one
        nohup bin/app > logs/app.log 2>&1 &
        echo $! > app.pid
        echo "Application started with PID $(cat app.pid)"
    fi
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "java":
            # For Java, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                if (project_path / "pom.xml").exists():
                    # Maven project
                    f.write("""#!/bin/bash
set -e

# Deployment script for Java Maven project
echo "Deploying Java Maven application..."

# Build the application
mvn clean package

# Get the JAR file
JAR_FILE=$(find target -name "*.jar" | head -1)
if [ -z "$JAR_FILE" ]; then
    echo "No JAR file found in target directory."
    exit 1
fi

# Check if running as a service
SERVICE_NAME=$(basename $(pwd))
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Check if there's a running instance
    if [ -f "app.pid" ]; then
        OLD_PID=$(cat app.pid)
        if ps -p $OLD_PID > /dev/null; then
            echo "Stopping previous instance (PID: $OLD_PID)..."
            kill $OLD_PID
            sleep 2
        fi
    fi
    
    # Start the application
    mkdir -p logs
    nohup java -jar $JAR_FILE > logs/app.log 2>&1 &
    PID=$!
    echo $PID > app.pid
    echo "Application started with PID $PID"
fi

echo "Deployment complete!"
""")
                else:
                    # Gradle project
                    f.write("""#!/bin/bash
set -e

# Deployment script for Java Gradle project
echo "Deploying Java Gradle application..."

# Build the application
./gradlew build

# Get the JAR file
JAR_FILE=$(find build/libs -name "*.jar" | head -1)
if [ -z "$JAR_FILE" ]; then
    echo "No JAR file found in build/libs directory."
    exit 1
fi

# Check if running as a service
SERVICE_NAME=$(basename $(pwd))
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Check if there's a running instance
    if [ -f "app.pid" ]; then
        OLD_PID=$(cat app.pid)
        if ps -p $OLD_PID > /dev/null; then
            echo "Stopping previous instance (PID: $OLD_PID)..."
            kill $OLD_PID
            sleep 2
        fi
    fi
    
    # Start the application
    mkdir -p logs
    nohup java -jar $JAR_FILE > logs/app.log 2>&1 &
    PID=$!
    echo $PID > app.pid
    echo "Application started with PID $PID"
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
        
        elif project_type == "rust":
            # For Rust, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for Rust project
echo "Deploying Rust application..."

# Build the application in release mode
cargo build --release

# Get the binary name from Cargo.toml
BINARY_NAME=$(grep -m 1 "name" Cargo.toml | cut -d '"' -f 2 | tr -d '[:space:]')
if [ -z "$BINARY_NAME" ]; then
    BINARY_NAME=$(basename $(pwd))
fi

# Check if systemd service exists
SERVICE_NAME=$BINARY_NAME
if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "Restarting service $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting application..."
    # Create a systemd service file if needed
    if [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        echo "Creating systemd service..."
        cat > /tmp/$SERVICE_NAME.service <<EOL
[Unit]
Description=$SERVICE_NAME
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/target/release/$BINARY_NAME
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
        sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        sudo systemctl start $SERVICE_NAME
    else
        # Start directly if no service exists and we can't create one
        mkdir -p logs
        nohup target/release/$BINARY_NAME > logs/app.log 2>&1 &
        echo $! > app.pid
        echo "Application started with PID $(cat app.pid)"
    fi
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
            
        elif project_type == "php":
            # For PHP, create a deployment script
            scripts_dir = project_path / "scripts"
            deploy_script = scripts_dir / "deploy.sh"
            
            # Create scripts directory if it doesn't exist
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Write deployment script
            with open(deploy_script, "w") as f:
                f.write("""#!/bin/bash
set -e

# Deployment script for PHP project
echo "Deploying PHP application..."

# Install dependencies
composer install --no-dev --optimize-autoloader

# Check for Laravel
if [ -f "artisan" ]; then
    echo "Laravel project detected"
    php artisan migrate --force
    php artisan config:cache
    php artisan route:cache
    php artisan view:cache
fi

# Check for Symfony
if [ -f "bin/console" ]; then
    echo "Symfony project detected"
    php bin/console cache:clear --env=prod
    php bin/console doctrine:migrations:migrate --no-interaction
fi

# Reload PHP-FPM if available
if command -v systemctl &> /dev/null && systemctl list-units --type=service | grep -q "php.*-fpm"; then
    echo "Reloading PHP-FPM..."
    sudo systemctl reload php*-fpm.service
fi

echo "Deployment complete!"
""")
            
            # Make the script executable
            deploy_script.chmod(0o755)
            
            return {
                "success": True,
                "files_created": [str(deploy_script)],
                "message": "Created deployment script"
            }
            
        # Add more project types as needed
        
        return {
            "success": False,
            "message": f"No deployment configuration available for {project_type}"
        }
    
    async def _setup_testing_config(
        self,
        project_path: Path,
        project_type: str,
        pipeline_steps: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up testing configuration files.
        
        Args:
            project_path: Path to the project
            project_type: Type of project
            pipeline_steps: Pipeline steps configuration
            
        Returns:
            Dictionary with testing configuration result
        """
        self._logger.info(f"Setting up testing configuration for {project_type}")
        
        created_files = []
        
        if project_type == "python":
            # Check if pytest.ini exists, create if not
            pytest_ini = project_path / "pytest.ini"
            if not pytest_ini.exists():
                with open(pytest_ini, "w") as f:
                    f.write("""[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --verbose --cov=./ --cov-report=term-missing
""")
                created_files.append(str(pytest_ini))
            
            # Create a basic test directory and example test if not exists
            tests_dir = project_path / "tests"
            if not tests_dir.exists():
                os.makedirs(tests_dir, exist_ok=True)
                
                # Create __init__.py
                with open(tests_dir / "__init__.py", "w") as f:
                    f.write("# Test package initialization")
                created_files.append(str(tests_dir / "__init__.py"))
                
                # Create an example test
                with open(tests_dir / "test_example.py", "w") as f:
                    f.write("""import unittest

class TestExample(unittest.TestCase):
    def test_simple_assertion(self):
        self.assertEqual(1 + 1, 2)
        
    def test_truth_value(self):
        self.assertTrue(True)
""")
                created_files.append(str(tests_dir / "test_example.py"))
            
            return {
                "success": True,
                "files_created": created_files,
                "message": "Created testing configuration",
                "framework": "pytest"
            }
        
        elif project_type == "node":
            # Check if jest configuration exists in package.json
            package_json_path = project_path / "package.json"
            if package_json_path.exists():
                try:
                    import json
                    with open(package_json_path, "r") as f:
                        package_data = json.load(f)
                    
                    # Check if jest is configured
                    has_jest = False
                    if "jest" not in package_data and "scripts" in package_data:
                        # If not in scripts.test, add jest configuration
                        if "test" not in package_data["scripts"] or "jest" not in package_data["scripts"]["test"]:
                            package_data["scripts"]["test"] = "jest"
                            has_jest = True
                            
                            # Save the updated package.json
                            with open(package_json_path, "w") as f:
                                json.dump(package_data, f, indent=2)
                            
                    # Create jest.config.js if needed
                    jest_config = project_path / "jest.config.js"
                    if not jest_config.exists() and has_jest:
                        with open(jest_config, "w") as f:
                            f.write("""module.exports = {
  testEnvironment: 'node',
  coverageDirectory: 'coverage',
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/index.js',
    '!**/node_modules/**',
  ],
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
};
""")
                        created_files.append(str(jest_config))
                    
                    # Create tests directory if needed
                    tests_dir = project_path / "__tests__"
                    if not tests_dir.exists() and has_jest:
                        os.makedirs(tests_dir, exist_ok=True)
                        
                        # Create an example test
                        with open(tests_dir / "example.test.js", "w") as f:
                            f.write("""describe('Example Test Suite', () => {
  test('adds 1 + 2 to equal 3', () => {
    expect(1 + 2).toBe(3);
  });
  
  test('true is truthy', () => {
    expect(true).toBeTruthy();
  });
});
""")
                        created_files.append(str(tests_dir / "example.test.js"))
                    
                    return {
                        "success": True,
                        "files_created": created_files,
                        "message": "Created testing configuration",
                        "framework": "jest"
                    }
                    
                except (json.JSONDecodeError, IOError) as e:
                    self._logger.error(f"Error reading or updating package.json: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to update package.json: {str(e)}"
                    }
                    
        elif project_type == "java":
            if (project_path / "pom.xml").exists():
                # Maven project, check for surefire plugin
                pom_path = project_path / "pom.xml"
                try:
                    with open(pom_path, "r") as f:
                        pom_content = f.read()
                        
                    if "maven-surefire-plugin" not in pom_content:
                        # Create a sample test if tests directory doesn't exist
                        test_dir = project_path / "src" / "test" / "java"
                        if not test_dir.exists():
                            os.makedirs(test_dir, exist_ok=True)
                            
                            # Create a simple test class
                            with open(test_dir / "ExampleTest.java", "w") as f:
                                f.write("""import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ExampleTest {
    @Test
    void simpleAssertion() {
        assertEquals(2, 1 + 1);
    }
    
    @Test
    void truthValue() {
        assertTrue(true);
    }
}
""")
                            created_files.append(str(test_dir / "ExampleTest.java"))
                            
                    return {
                        "success": True,
                        "files_created": created_files,
                        "message": "Created testing configuration",
                        "framework": "junit"
                    }
                except IOError as e:
                    self._logger.error(f"Error reading pom.xml: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to read pom.xml: {str(e)}"
                    }
            else:
                # Gradle project, check for test directory
                test_dir = project_path / "src" / "test" / "java"
                if not test_dir.exists():
                    os.makedirs(test_dir, exist_ok=True)
                    
                    # Create a simple test class
                    with open(test_dir / "ExampleTest.java", "w") as f:
                        f.write("""import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ExampleTest {
    @Test
    void simpleAssertion() {
        assertEquals(2, 1 + 1);
    }
    
    @Test
    void truthValue() {
        assertTrue(true);
    }
}
""")
                    created_files.append(str(test_dir / "ExampleTest.java"))
                    
                return {
                    "success": True,
                    "files_created": created_files,
                    "message": "Created testing configuration",
                    "framework": "junit"
                }
                
        elif project_type == "go":
            # Go tests are typically in the same package as the code
            # Create a simple test file if none exists
            main_go = None
            for file in project_path.glob("*.go"):
                if file.name == "main.go":
                    main_go = file
                    break
                    
            if main_go:
                test_file = project_path / (main_go.stem + "_test.go")
                if not test_file.exists():
                    with open(test_file, "w") as f:
                        f.write("""package main

import (
	"testing"
)

func TestExample(t *testing.T) {
	if 1+1 != 2 {
		t.Error("1+1 should equal 2")
	}
}

func TestTruthValue(t *testing.T) {
	if !true {
		t.Error("true should be true")
	}
}
""")
                    created_files.append(str(test_file))
                    
                return {
                    "success": True,
                    "files_created": created_files,
                    "message": "Created testing configuration",
                    "framework": "go-test"
                }
                
        elif project_type == "rust":
            # Check if tests directory exists in the src directory
            src_dir = project_path / "src"
            if src_dir.exists():
                # Create a tests directory if it doesn't exist
                tests_dir = src_dir / "tests"
                if not tests_dir.exists():
                    os.makedirs(tests_dir, exist_ok=True)
                    
                    # Create a simple test file
                    with open(tests_dir / "example_test.rs", "w") as f:
                        f.write("""#[cfg(test)]
mod tests {
    #[test]
    fn test_simple_assertion() {
        assert_eq!(2, 1 + 1);
    }
    
    #[test]
    fn test_truth_value() {
        assert!(true);
    }
}
""")
                    created_files.append(str(tests_dir / "example_test.rs"))
                    
                # Add test module to lib.rs if it exists
                lib_rs = src_dir / "lib.rs"
                if lib_rs.exists():
                    with open(lib_rs, "r") as f:
                        content = f.read()
                        
                    if "#[cfg(test)]" not in content and "mod tests" not in content:
                        with open(lib_rs, "a") as f:
                            f.write("""
#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2, 1 + 1);
    }
}
""")
                
                return {
                    "success": True,
                    "files_created": created_files,
                    "message": "Created testing configuration",
                    "framework": "cargo-test"
                }
        
        # Add more project types as needed
        
        return {
            "success": False,
            "message": f"No testing configuration available for {project_type}"
        }
    
    def _merge_configs(self, base_config: Dict[str, Any], custom_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge base configuration with custom configuration recursively.
        
        Args:
            base_config: Base configuration
            custom_config: Custom configuration to merge in
            
        Returns:
            Merged configuration
        """
        return deep_update(base_config, custom_config)
        
    async def setup_ci_cd_pipeline(
        self,
        request: str,
        project_dir: Union[str, Path],
        repository_url: Optional[str] = None,
        platform: Optional[str] = None,
        deployment_targets: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Set up a complete CI/CD pipeline based on a natural language request.
        
        Args:
            request: Natural language request
            project_dir: Project directory
            repository_url: Optional repository URL
            platform: Optional CI/CD platform override
            deployment_targets: Optional deployment targets override
            custom_config: Optional custom configuration
            
        Returns:
            Dictionary with the setup result
        """
        self._logger.info(f"Setting up CI/CD pipeline from request: {request}")
        
        # Analyze request to extract key information if not explicitly provided
        parsed_request = await self._parse_ci_cd_request(request)
        
        # Use provided values or fall back to parsed values
        repository_url = repository_url or parsed_request.get("repository_url")
        platform = platform or parsed_request.get("platform")
        deployment_targets = deployment_targets or parsed_request.get("deployment_targets")
        
        # If repository URL is not provided, try to infer from git config
        if not repository_url:
            try:
                git_output = await self._run_git_command(["remote", "get-url", "origin"], cwd=project_dir)
                if git_output:
                    repository_url = git_output.strip()
            except Exception as e:
                self._logger.warning(f"Could not determine repository URL from git: {str(e)}")
        
        # Determine repository provider
        repository_provider = "unknown"
        if repository_url:
            repository_provider = self.get_repository_provider_from_url(repository_url)
        
        # If platform is not specified, try to determine from repository provider
        if not platform:
            if repository_provider == "github":
                platform = "github_actions"
            elif repository_provider == "gitlab":
                platform = "gitlab_ci"
            elif repository_provider == "bitbucket":
                platform = "bitbucket_pipelines"
            elif repository_provider == "azure_devops":
                platform = "azure_pipelines"
            else:
                # Default to GitHub Actions
                platform = "github_actions"
        
        # Create repository info dictionary
        repository_info = {
            "url": repository_url,
            "provider": repository_provider
        }
        
        # Create the complete pipeline
        result = await self._create_complete_pipeline(
            project_dir=project_dir,
            repository_info=repository_info,
            platform=platform,
            deployment_targets=deployment_targets,
            custom_config=custom_config
        )
        
        # Add parsed request information to the result
        result["parsed_request"] = parsed_request
        
        return result
    
    async def _parse_ci_cd_request(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language CI/CD setup request to extract key information.
        
        Args:
            request: Natural language request
            
        Returns:
            Dictionary with extracted information
        """
        self._logger.info(f"Parsing CI/CD request: {request}")
        
        # Use AI to parse the request
        prompt = f"""
Extract key information from this CI/CD setup request:
"{request}"

Return a JSON object with these fields:
1. platform: The CI/CD platform name (github_actions, gitlab_ci, jenkins, etc.)
2. repository_url: Repository URL if mentioned
3. deployment_targets: List of deployment environments to set up
4. testing_requirements: Any specific testing requirements
5. build_requirements: Any specific build requirements
6. security_requirements: Any security scanning requirements
"""
    
        try:
            # Call AI service
            from angela.ai.client import gemini_client, GeminiRequest
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            parsed_info = json.loads(json_str)
            
            # Ensure expected keys exist
            expected_keys = ["platform", "repository_url", "deployment_targets", 
                            "testing_requirements", "build_requirements", "security_requirements"]
            for key in expected_keys:
                if key not in parsed_info:
                    parsed_info[key] = None
            
            return parsed_info
            
        except Exception as e:
            self._logger.error(f"Error parsing CI/CD request: {str(e)}")
            # Return minimal information on error
            return {
                "platform": None,
                "repository_url": None,
                "deployment_targets": None,
                "testing_requirements": None,
                "build_requirements": None,
                "security_requirements": None
            }
    
    async def _run_git_command(self, args: List[str], cwd: Union[str, Path] = ".") -> str:
        """
        Run a git command and return the output.
        
        Args:
            args: Git command arguments
            cwd: Working directory
            
        Returns:
            Command output as a string
        """
        try:
            from angela.execution.engine import execution_engine
            command = ["git"] + args
            command_str = " ".join(command)
            
            stdout, stderr, return_code = await execution_engine.execute_command(
                command=command_str,
                check_safety=True,
                working_dir=str(cwd)
            )
            
            if return_code != 0:
                raise RuntimeError(f"Git command failed: {stderr}")
            
            return stdout
        except Exception as e:
            self._logger.error(f"Error running git command: {str(e)}")
            raise
            
    async def _create_complete_pipeline(
        self, 
        project_dir: Union[str, Path], 
        repository_info: Dict[str, Any],
        platform: str,
        deployment_targets: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete CI/CD pipeline for a project.
        
        Args:
            project_dir: Project directory
            repository_info: Repository information (URL, provider, etc.)
            platform: CI/CD platform (github_actions, gitlab_ci, etc.)
            deployment_targets: Optional list of deployment targets
            custom_config: Optional custom configuration
            
        Returns:
            Dictionary with the pipeline creation result
        """
        self._logger.info(f"Creating complete CI/CD pipeline on {platform}")
        
        # Detect project type if not provided
        detection_result = await self.detect_project_type(project_dir)
        project_type = detection_result.get("project_type")
        
        if not project_type:
            return {
                "success": False,
                "error": f"Could not detect project type: {detection_result.get('error', 'Unknown error')}",
                "platform": platform
            }
        
        # Determine pipeline steps
        pipeline_steps = await self._determine_pipeline_steps(
            project_type=project_type,
            platform=platform,
            pipeline_type="full"
        )
        
        # Set up testing configuration
        testing_config = await self._setup_testing_config(
            project_path=project_dir,
            project_type=project_type,
            pipeline_steps=pipeline_steps
        )
        
        # Set up deployment configuration if targets are specified
        deployment_config = None
        if deployment_targets:
            deployment_config = await self._setup_deployment_config(
                project_path=project_dir,
                platform=platform,
                project_type=project_type,
                pipeline_steps=pipeline_steps
            )
        
        # Generate the final pipeline configuration
        config = {
            "pipeline_steps": pipeline_steps
        }
        
        if testing_config and testing_config.get("success", False):
            config["testing_config"] = testing_config
        
        if deployment_config and deployment_config.get("success", False):
            config["deployment_config"] = deployment_config
        
        if custom_config:
            config = deep_update(config, custom_config)
        
        # Generate the actual CI/CD configuration file
        result = await self.generate_ci_configuration(
            path=project_dir,
            platform=platform,
            project_type=project_type,
            custom_settings=config
        )
        
        # Add pipeline metadata to the result
        result["pipeline_info"] = {
            "project_type": project_type,
            "platform": platform,
            "repository": repository_info,
            "testing": testing_config.get("framework") if testing_config and testing_config.get("success", False) else None,
            "deployment": deployment_targets if deployment_targets else []
        }
        
        return result
    
    def get_repository_provider_from_url(self, url: str) -> str:
        """
        Determine the repository provider from a repository URL.
        
        Args:
            url: Repository URL
            
        Returns:
            Repository provider name
        """
        url = url.lower()
        
        if "github.com" in url:
            return "github"
        elif "gitlab.com" in url:
            return "gitlab"
        elif "bitbucket.org" in url:
            return "bitbucket"
        elif "dev.azure.com" in url or "visualstudio.com" in url:
            return "azure_devops"
        else:
            return "unknown"

# Global CI/CD integration instance
ci_cd_integration = CiCdIntegration()
