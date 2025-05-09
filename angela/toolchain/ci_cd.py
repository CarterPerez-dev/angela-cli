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
 
from angela.utils.logging import get_logger
from angela.context import context_manager

logger = get_logger(__name__)

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
            "circle_ci"
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
        
        # Python indicators
        if (path_obj / "requirements.txt").exists() or (path_obj / "setup.py").exists() or (path_obj / "pyproject.toml").exists():
            project_type = "python"
        # Node.js indicators
        elif (path_obj / "package.json").exists():
            project_type = "node"
        # Go indicators
        elif (path_obj / "go.mod").exists():
            project_type = "go"
        # Rust indicators
        elif (path_obj / "Cargo.toml").exists():
            project_type = "rust"
        # Java indicators
        elif (path_obj / "pom.xml").exists():
            project_type = "java"
        elif (path_obj / "build.gradle").exists() or (path_obj / "build.gradle.kts").exists():
            project_type = "java"
        # Ruby indicators
        elif (path_obj / "Gemfile").exists():
            project_type = "ruby"
        
        if project_type:
            return {
                "detected": True,
                "project_type": project_type,
                "project_path": str(path_obj)
            }
        
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
        # Add other project types as needed
        else: # Default empty workflow if project_type is not recognized
             workflow = {"name": f"{project_type} CI", "on": {}, "jobs": {}}
    
    
        # Update with custom settings
        if custom_settings:
            # Use recursive update function (not shown) or libraries
            # This is a simplified approach, ensure keys exist before extending
            if (workflow and "jobs" in workflow and "build" in workflow["jobs"] and "steps" in workflow["jobs"]["build"] and
                isinstance(workflow["jobs"]["build"]["steps"], list) and
                "jobs" in custom_settings and isinstance(custom_settings["jobs"], dict) and
                "build" in custom_settings["jobs"] and isinstance(custom_settings["jobs"]["build"], dict) and
                "steps" in custom_settings["jobs"]["build"] and isinstance(custom_settings["jobs"]["build"]["steps"], list)):
                workflow["jobs"]["build"]["steps"].extend(custom_settings["jobs"]["build"]["steps"])
            # Add more robust merging if needed, or update specific parts carefully
            # For example, to merge the entire custom_settings:
            # from collections.abc import MutableMapping
            # def deep_update(d, u):
            #     for k, v in u.items():
            #         if isinstance(v, MutableMapping):
            #             d[k] = deep_update(d.get(k, {}), v)
            #         else:
            #             d[k] = v
            #     return d
            # deep_update(workflow, custom_settings)
    
    
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
        # Add other project types as needed
        else: # Default empty config if project_type is not recognized
            config = {"image": "alpine", "stages": ["build", "test"], "build": {"script": ["echo 'No build defined'"]}}

        
        # Update with custom settings
        if custom_settings:
            # A more robust deep merge is generally needed for complex configs.
            # This simplified approach attempts to merge dictionaries and lists.
            for key, value in custom_settings.items():
                if key in config:
                    if isinstance(config[key], dict) and isinstance(value, dict):
                        # Recursively update dictionaries if both are dicts
                        # For a true deep merge, a helper function would be better.
                        # This is a shallow update for the top-level dict value.
                        # A proper deep merge:
                        # from collections.abc import MutableMapping
                        # def deep_update(d, u):
                        #     for k_u, v_u in u.items():
                        #         if isinstance(v_u, MutableMapping):
                        #             d[k_u] = deep_update(d.get(k_u, {}), v_u)
                        #         else:
                        #             d[k_u] = v_u
                        #     return d
                        # if isinstance(config[key], dict) and isinstance(value, dict):
                        #    deep_update(config[key], value)
                        # else:
                        #    config[key] = value # or handle list merging etc.
                        config[key].update(value) # Simple update, might not be deep enough
                    elif isinstance(config[key], list) and isinstance(value, list):
                        config[key].extend(value) # Extend lists
                    else:
                        config[key] = value # Overwrite if types don't match for merge/extend
                else:
                    config[key] = value # Add new key
        
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
        # Add other project types as needed
        
        # Update with custom settings
        # For Jenkins, we'd need more sophisticated templating to properly merge
        # custom settings into the Jenkinsfile
        
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
        # Add other project types as needed
        else: # Default empty config if project_type is not recognized
            config = {"language": "generic", "script": ["echo 'No script defined'"]}

        
        # Update with custom settings
        if custom_settings:
            for key, value in custom_settings.items():
                if key in config:
                    if isinstance(config[key], list) and isinstance(value, list):
                        config[key].extend(value) # Extend lists
                    elif isinstance(config[key], dict) and isinstance(value, dict):
                        # A proper deep merge would be better here.
                        config[key].update(value) # Simple update for dicts
                    else:
                        config[key] = value # Overwrite if types don't match for merge/extend
                else:
                    config[key] = value # Add new key
        
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
        # Add other project types as needed
        else: # Default empty config if project_type is not recognized
            config = {"version": 2.1, "jobs": {}, "workflows": {}}

        
        # Update with custom settings
        if custom_settings:
            # This is a simplified approach; in a real implementation, 
            # we'd need more sophisticated merging
            if (config and "jobs" in config and "build-and-test" in config["jobs"] and 
                isinstance(config["jobs"]["build-and-test"], dict) and 
                "steps" in config["jobs"]["build-and-test"] and 
                isinstance(config["jobs"]["build-and-test"]["steps"], list) and
                "jobs" in custom_settings and isinstance(custom_settings["jobs"], dict) and
                "build-and-test" in custom_settings["jobs"] and 
                isinstance(custom_settings["jobs"]["build-and-test"], dict) and
                "steps" in custom_settings["jobs"]["build-and-test"] and 
                isinstance(custom_settings["jobs"]["build-and-test"]["steps"], list)):
                config["jobs"]["build-and-test"]["steps"].extend(custom_settings["jobs"]["build-and-test"]["steps"])
            # Add more robust merging if needed
            # For example, to merge the entire custom_settings:
            # from collections.abc import MutableMapping
            # def deep_update(d, u):
            #     for k, v in u.items():
            #         if isinstance(v, MutableMapping):
            #             d[k] = deep_update(d.get(k, {}), v)
            #         else:
            #             d[k] = v
            #     return d
            # deep_update(config, custom_settings)

        
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
            pipeline_steps.update(custom_settings)
        
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
                "message": "Created testing configuration"
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
                        "message": "Created testing configuration"
                    }
                    
                except (json.JSONDecodeError, IOError) as e:
                    self._logger.error(f"Error reading or updating package.json: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to update package.json: {str(e)}"
                    }
        
        # Add more project types as needed
        
        return {
            "success": False,
            "message": f"No testing configuration available for {project_type}"
        }
    
    def get_repository_provider_from_url(self, url: str) -> str:
        """
        Determine the repository provider from a URL.
        
        Args:
            url: Repository URL
            
        Returns:
            Repository provider name ('github', 'gitlab', etc.) or 'unknown'
        """
        # Support for both HTTPS and SSH URLs
        url = url.lower()
        
        # GitHub detection
        if any(pattern in url for pattern in ["github.com", "github:", "@github.com"]):
            return "github"
        
        # GitLab detection
        elif any(pattern in url for pattern in ["gitlab.com", "gitlab:", "@gitlab.com"]):
            return "gitlab"
        
        # Bitbucket detection
        elif any(pattern in url for pattern in ["bitbucket.org", "bitbucket:", "@bitbucket.org"]):
            return "bitbucket"
        
        # Azure DevOps detection
        elif any(pattern in url for pattern in ["dev.azure.com", "visualstudio.com", "@ssh.dev.azure.com"]):
            return "azure_devops"
        
        # AWS CodeCommit detection
        elif "codecommit" in url:
            return "aws_codecommit"
        
        # Google Cloud Source Repositories
        elif "source.developers.google.com" in url:
            return "google_source_repos"
        
        # Self-hosted detection for common platforms
        elif re.search(r'git@[\w\.-]+:', url):
            # This is an SSH URL to a git repo, try to determine type from structure
            if "/scm/" in url:  # Common in Bitbucket Server
                return "bitbucket_server"
            elif "/gogs/" in url:
                return "gogs"
            elif "/gitea/" in url:
                return "gitea"
            else:
                # Generic self-hosted
                return "self_hosted_git"
        
        # Return unknown if no match
        return "unknown"

    async def _create_complete_pipeline(
        self, 
        project_dir: Union[str, Path], 
        repository_info: Dict[str, Any],
        platform: str,
        project_type: Optional[str] = None,
        deployment_targets: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete CI/CD pipeline for a project.
        
        Args:
            project_dir: Project directory
            repository_info: Repository information (URL, provider, etc.)
            platform: CI/CD platform (github_actions, gitlab_ci, etc.)
            project_type: Optional project type
            deployment_targets: Optional list of deployment targets
            custom_config: Optional custom configuration
            
        Returns:
            Dictionary with the pipeline creation result
        """
        self._logger.info(f"Creating complete CI/CD pipeline for {project_type} on {platform}")
        
        # Detect project type if not provided
        if project_type is None:
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
            repository_info=repository_info,
            deployment_targets=deployment_targets,
            custom_config=custom_config
        )
        
        # Set up testing configuration
        testing_config = await self._setup_testing_config(
            project_type=project_type,
            platform=platform,
            pipeline_steps=pipeline_steps
        )
        
        # Set up deployment configuration if targets are specified
        deployment_config = None
        if deployment_targets:
            deployment_config = await self._setup_deployment_config(
                project_type=project_type,
                platform=platform,
                deployment_targets=deployment_targets,
                repository_info=repository_info
            )
        
        # Generate the final pipeline configuration
        config = {
            "pipeline_steps": pipeline_steps,
            "testing_config": testing_config
        }
        
        if deployment_config:
            config["deployment_config"] = deployment_config
        
        if custom_config:
            config = self._merge_configs(config, custom_config)
        
        # Generate the actual CI/CD configuration file
        result = await self.generate_ci_configuration(
            path=project_dir,
            platform=platform,
            project_type=project_type,
            custom_settings=config
        )
        
        # Add pipeline metadata to the result
        result["pipeline_info"] = {
            "steps": [step["name"] for step in pipeline_steps],
            "testing": testing_config.get("framework"),
            "deployment": [target for target in deployment_targets] if deployment_targets else []
        }
        
        return result
    
    async def _determine_pipeline_steps(
        self,
        project_type: str,
        platform: str,
        repository_info: Dict[str, Any],
        deployment_targets: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Determine the appropriate pipeline steps based on project type and deployment targets.
        
        Args:
            project_type: Project type (python, node, etc.)
            platform: CI/CD platform
            repository_info: Repository information
            deployment_targets: Optional deployment targets
            custom_config: Optional custom configuration
            
        Returns:
            List of pipeline step configurations
        """
        self._logger.info(f"Determining pipeline steps for {project_type} project")
        
        # Initialize basic pipeline steps
        steps = []
        
        # Add checkout step
        steps.append({
            "name": "checkout",
            "description": "Check out the repository code",
            "required": True
        })
        
        # Add setup step based on project type
        setup_step = {
            "name": "setup",
            "description": f"Set up {project_type} environment",
            "required": True
        }
        
        if project_type == "python":
            setup_step["tool"] = "python"
            setup_step["version"] = ["3.8", "3.9", "3.10"]
        elif project_type == "node":
            setup_step["tool"] = "node"
            setup_step["version"] = ["14", "16", "18"]
        elif project_type == "java":
            setup_step["tool"] = "java"
            setup_step["version"] = ["11", "17"]
        elif project_type == "go":
            setup_step["tool"] = "go"
            setup_step["version"] = ["1.18", "1.19"]
        else:
            setup_step["tool"] = project_type
            setup_step["version"] = ["latest"]
        
        steps.append(setup_step)
        
        # Add dependency installation step
        steps.append({
            "name": "install_dependencies",
            "description": "Install project dependencies",
            "required": True,
            "depends_on": ["setup"]
        })
        
        # Add linting step if appropriate for the project type
        if project_type in ["python", "node", "go", "java"]:
            steps.append({
                "name": "lint",
                "description": "Run code linting",
                "required": False,
                "depends_on": ["install_dependencies"]
            })
        
        # Add testing step
        steps.append({
            "name": "test",
            "description": "Run tests",
            "required": True,
            "depends_on": ["install_dependencies"]
        })
        
        # Add build step if needed
        if project_type in ["node", "java", "go"]:
            steps.append({
                "name": "build",
                "description": "Build the project",
                "required": True,
                "depends_on": ["test"]
            })
        
        # Add deployment steps if targets are specified
        if deployment_targets:
            for target in deployment_targets:
                steps.append({
                    "name": f"deploy_to_{target}",
                    "description": f"Deploy to {target} environment",
                    "required": True,
                    "depends_on": ["build"] if "build" in [s["name"] for s in steps] else ["test"],
                    "environment": target
                })
        
        # Override or add steps from custom config if provided
        if custom_config and "steps" in custom_config:
            for custom_step in custom_config["steps"]:
                # Check if this step is overriding an existing one
                existing_steps = [i for i, s in enumerate(steps) if s["name"] == custom_step["name"]]
                if existing_steps:
                    # Update existing step
                    steps[existing_steps[0]].update(custom_step)
                else:
                    # Add new step
                    steps.append(custom_step)
        
        return steps
    
    async def _setup_deployment_config(
        self,
        project_type: str,
        platform: str,
        deployment_targets: List[str],
        repository_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up deployment configuration for specified targets.
        
        Args:
            project_type: Project type
            platform: CI/CD platform
            deployment_targets: List of deployment targets
            repository_info: Repository information
            
        Returns:
            Deployment configuration dictionary
        """
        self._logger.info(f"Setting up deployment configuration for {deployment_targets}")
        
        deployment_config = {
            "environments": {}
        }
        
        for target in deployment_targets:
            env_config = {
                "name": target,
                "protected": target in ["production", "prod"],
                "manual_approval": target in ["production", "prod", "staging", "stage"],
                "url_pattern": f"https://{target}-${{REPO_NAME}}.example.com"
            }
            
            # Add provider-specific configuration
            if "aws" in target or target in ["production", "staging", "dev"]:
                env_config["provider"] = "aws"
                env_config["service"] = "elastic_beanstalk" if project_type in ["node", "python", "java"] else "ec2"
                env_config["region"] = "us-east-1"  # Default region, should be customizable
                env_config["variables"] = [
                    "AWS_ACCESS_KEY_ID",
                    "AWS_SECRET_ACCESS_KEY"
                ]
            elif "azure" in target:
                env_config["provider"] = "azure"
                env_config["service"] = "app_service"
                env_config["variables"] = [
                    "AZURE_CREDENTIALS"
                ]
            elif "gcp" in target:
                env_config["provider"] = "gcp"
                env_config["service"] = "app_engine" if project_type in ["node", "python", "java", "go"] else "compute_engine"
                env_config["variables"] = [
                    "GCP_SERVICE_ACCOUNT_KEY"
                ]
            elif "heroku" in target:
                env_config["provider"] = "heroku"
                env_config["variables"] = [
                    "HEROKU_API_KEY"
                ]
            else:
                # Generic environment
                env_config["provider"] = "generic"
                env_config["variables"] = [
                    f"{target.upper()}_DEPLOY_URL",
                    f"{target.upper()}_DEPLOY_TOKEN"
                ]
            
            deployment_config["environments"][target] = env_config
        
        # Add deployment triggers - deploy to dev on every push to develop branch,
        # to staging on tags or releases, to production on specific approval
        deployment_config["triggers"] = {
            "dev": {
                "branches": ["develop", "dev", "feature/*"],
            },
            "staging": {
                "branches": ["main", "master", "release/*"],
                "tags": ["v*-beta", "v*-rc*"]
            },
            "production": {
                "branches": ["main", "master"],
                "tags": ["v*"],
                "requires_approval": True
            }
        }
        
        return deployment_config
    
    async def _setup_testing_config(
        self,
        project_type: str,
        platform: str,
        pipeline_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Set up testing configuration based on project type.
        
        Args:
            project_type: Project type
            platform: CI/CD platform
            pipeline_steps: Pipeline steps
            
        Returns:
            Testing configuration dictionary
        """
        self._logger.info(f"Setting up testing configuration for {project_type}")
        
        testing_config = {
            "enabled": True,
            "requires_framework": True
        }
        
        # Determine testing framework based on project type
        if project_type == "python":
            testing_config["framework"] = "pytest"
            testing_config["commands"] = [
                "pytest --cov=. --cov-report=xml"
            ]
            testing_config["coverage_tool"] = "pytest-cov"
            testing_config["report_file"] = "coverage.xml"
        elif project_type == "node":
            testing_config["framework"] = "jest"
            testing_config["commands"] = [
                "npm test -- --coverage"
            ]
            testing_config["coverage_tool"] = "jest"
            testing_config["report_file"] = "coverage/lcov.info"
        elif project_type == "java":
            if os.path.exists(os.path.join(os.getcwd(), "pom.xml")):
                testing_config["framework"] = "junit"
                testing_config["commands"] = [
                    "mvn test"
                ]
                testing_config["coverage_tool"] = "jacoco"
                testing_config["report_file"] = "target/site/jacoco/jacoco.xml"
            else:
                testing_config["framework"] = "junit"
                testing_config["commands"] = [
                    "./gradlew test"
                ]
                testing_config["coverage_tool"] = "jacoco"
                testing_config["report_file"] = "build/reports/jacoco/test/jacocoTestReport.xml"
        elif project_type == "go":
            testing_config["framework"] = "go-test"
            testing_config["commands"] = [
                "go test -v ./... -coverprofile=coverage.out"
            ]
            testing_config["coverage_tool"] = "go-cover"
            testing_config["report_file"] = "coverage.out"
        else:
            testing_config["requires_framework"] = False
            testing_config["framework"] = "custom"
            testing_config["commands"] = [
                "# Add your test commands here"
            ]
        
        # Add coverage thresholds
        testing_config["coverage_thresholds"] = {
            "line": 80,
            "function": 80,
            "branch": 70,
            "statement": 80
        }
        
        return testing_config
    
    def _merge_configs(self, base_config: Dict[str, Any], custom_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge base configuration with custom configuration recursively.
        
        Args:
            base_config: Base configuration
            custom_config: Custom configuration to merge in
            
        Returns:
            Merged configuration
        """
        result = base_config.copy()
        
        for key, value in custom_config.items():
            if (
                key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)
            ):
                # Recursively merge dictionaries
                result[key] = self._merge_configs(result[key], value)
            elif (
                key in result and 
                isinstance(result[key], list) and 
                isinstance(value, list)
            ):
                # For lists, either concatenate or replace based on special marker
                if value and value[0] == "__REPLACE__":
                    result[key] = value[1:]
                else:
                    result[key] = result[key] + value
            else:
                # Simple value replacement
                result[key] = value
        
        return result
    
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

# Global CI/CD integration instance
ci_cd_integration = CiCdIntegration()
