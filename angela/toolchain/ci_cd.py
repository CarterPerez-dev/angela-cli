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
        
        # Get configuration settings
        settings = {}
        if custom_settings:
            settings.update(custom_settings)
        
        # Set default settings based on project type
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
        
        # Update with custom settings
        if settings:
            # Use recursive update function (not shown) or libraries
            # This is a simplified approach
            if "jobs" in settings and "build" in settings["jobs"] and "steps" in settings["jobs"]["build"]:
                # Append custom steps
                workflow["jobs"]["build"]["steps"].extend(settings["jobs"]["build"]["steps"])
        
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
        
        # Get configuration settings
        settings = {}
        if custom_settings:
            settings.update(custom_settings)
        
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
        
        # Update with custom settings
        if settings:
            # Use recursive update function or libraries
            # This is a simplified approach
            for key, value in settings.items():
                if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                    config[key].update(value)
                else:
                    config[key] = value
        
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
        
        # Get configuration settings
        settings = {}
        if custom_settings:
            settings.update(custom_settings)
        
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
        
        # Update with custom settings
        if settings:
            for key, value in settings.items():
                if isinstance(value, list) and key in config and isinstance(config[key], list):
                    config[key].extend(value)
                else:
                    config[key] = value
        
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
        
        # Get configuration settings
        settings = {}
        if custom_settings:
            settings.update(custom_settings)
        
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
        
        # Update with custom settings
        if settings:
            # This is a simplified approach; in a real implementation, 
            # we'd need more sophisticated merging
            if "jobs" in settings and "build-and-test" in settings["jobs"] and "steps" in settings["jobs"]["build-and-test"]:
                config["jobs"]["build-and-test"]["steps"].extend(settings["jobs"]["build-and-test"]["steps"])
        
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

# Global CI/CD integration instance
ci_cd_integration = CiCdIntegration()
