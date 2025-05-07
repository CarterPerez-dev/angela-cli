# angela/toolchain/git.py
"""
Enhanced Git integration for Angela CLI.

This module provides advanced Git functionality for the code generation lifecycle,
such as automatic repository initialization, commit management, and feature branch creation.
"""
import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import re

from angela.utils.logging import get_logger
from angela.execution.engine import execution_engine

logger = get_logger(__name__)

class GitIntegration:
    """
    Enhanced Git integration for the code generation lifecycle.
    """
    
    def __init__(self):
        """Initialize the Git integration."""
        self._logger = logger
    
    async def init_repository(
        self, 
        path: Union[str, Path], 
        initial_branch: str = "main",
        gitignore_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize a Git repository.
        
        Args:
            path: Path to initialize the repository in
            initial_branch: Name of the initial branch
            gitignore_template: Optional template for .gitignore (e.g., 'python', 'node')
            
        Returns:
            Dictionary with the operation result
        """
        self._logger.info(f"Initializing Git repository in {path}")
        
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists():
            return {
                "success": False,
                "error": f"Path does not exist: {path}",
                "command": None,
                "stdout": "",
                "stderr": f"Path does not exist: {path}"
            }
        
        # Check if already a Git repository
        if (path_obj / ".git").exists():
            return {
                "success": True,
                "message": "Repository already initialized",
                "command": None,
                "stdout": "Repository already initialized",
                "stderr": ""
            }
        
        # Initialize the repository
        init_command = f"git init -b {initial_branch}"
        
        # Execute the command
        stdout, stderr, return_code = await execution_engine.execute_command(
            init_command,
            check_safety=True,
            working_dir=str(path_obj)
        )
        
        if return_code != 0:
            return {
                "success": False,
                "error": f"Failed to initialize repository: {stderr}",
                "command": init_command,
                "stdout": stdout,
                "stderr": stderr
            }
        
        # Create .gitignore if requested
        if gitignore_template:
            gitignore_result = await self._create_gitignore(path_obj, gitignore_template)
            if not gitignore_result["success"]:
                # Continue even if gitignore creation fails
                self._logger.warning(f"Failed to create .gitignore: {gitignore_result['error']}")
        
        return {
            "success": True,
            "message": "Repository initialized successfully",
            "command": init_command,
            "stdout": stdout,
            "stderr": stderr
        }
    
    async def stage_files(
        self, 
        path: Union[str, Path], 
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Stage files for a Git commit.
        
        Args:
            path: Path to the Git repository
            files: List of files to stage (all files if None)
            
        Returns:
            Dictionary with the operation result
        """
        self._logger.info(f"Staging files in {path}")
        
        path_obj = Path(path)
        
        # Check if path is a Git repository
        if not (path_obj / ".git").exists():
            return {
                "success": False,
                "error": f"Not a Git repository: {path}",
                "command": None,
                "stdout": "",
                "stderr": f"Not a Git repository: {path}"
            }
        
        # Build the git add command
        if files:
            # Quote file paths to handle spaces
            quoted_files = [f'"{f}"' for f in files]
            add_command = f"git add {' '.join(quoted_files)}"
        else:
            add_command = "git add ."
        
        # Execute the command
        stdout, stderr, return_code = await execution_engine.execute_command(
            add_command,
            check_safety=True,
            working_dir=str(path_obj)
        )
        
        if return_code != 0:
            return {
                "success": False,
                "error": f"Failed to stage files: {stderr}",
                "command": add_command,
                "stdout": stdout,
                "stderr": stderr
            }
        
        return {
            "success": True,
            "message": "Files staged successfully",
            "command": add_command,
            "stdout": stdout,
            "stderr": stderr
        }
    
    async def commit_changes(
        self, 
        path: Union[str, Path], 
        message: str,
        files: Optional[List[str]] = None,
        auto_stage: bool = True
    ) -> Dict[str, Any]:
        """
        Commit changes to a Git repository.
        
        Args:
            path: Path to the Git repository
            message: Commit message
            files: Optional list of files to commit (all staged files if None)
            auto_stage: Whether to automatically stage files before committing
            
        Returns:
            Dictionary with the operation result
        """
        self._logger.info(f"Committing changes in {path}")
        
        path_obj = Path(path)
        
        # Check if path is a Git repository
        if not (path_obj / ".git").exists():
            return {
                "success": False,
                "error": f"Not a Git repository: {path}",
                "command": None,
                "stdout": "",
                "stderr": f"Not a Git repository: {path}"
            }
        
        # Stage files if requested
        if auto_stage:
            stage_result = await self.stage_files(path_obj, files)
            if not stage_result["success"]:
                return stage_result
        
        # Build the git commit command
        commit_command = f'git commit -m "{message}"'
        
        # Add specific files if provided and not auto-staging
        if files and not auto_stage:
            # Quote file paths to handle spaces
            quoted_files = [f'"{f}"' for f in files]
            commit_command += f" {' '.join(quoted_files)}"
        
        # Execute the command
        stdout, stderr, return_code = await execution_engine.execute_command(
            commit_command,
            check_safety=True,
            working_dir=str(path_obj)
        )
        
        if return_code != 0:
            return {
                "success": False,
                "error": f"Failed to commit changes: {stderr}",
                "command": commit_command,
                "stdout": stdout,
                "stderr": stderr
            }
        
        return {
            "success": True,
            "message": "Changes committed successfully",
            "command": commit_command,
            "stdout": stdout,
            "stderr": stderr
        }
    
    async def create_branch(
        self, 
        path: Union[str, Path], 
        branch_name: str,
        checkout: bool = True,
        start_point: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Git branch.
        
        Args:
            path: Path to the Git repository
            branch_name: Name of the branch to create
            checkout: Whether to check out the new branch
            start_point: Optional starting point for the branch
            
        Returns:
            Dictionary with the operation result
        """
        self._logger.info(f"Creating branch {branch_name} in {path}")
        
        path_obj = Path(path)
        
        # Check if path is a Git repository
        if not (path_obj / ".git").exists():
            return {
                "success": False,
                "error": f"Not a Git repository: {path}",
                "command": None,
                "stdout": "",
                "stderr": f"Not a Git repository: {path}"
            }
        
        # Build the git branch command
        if checkout:
            branch_command = f"git checkout -b {branch_name}"
        else:
            branch_command = f"git branch {branch_name}"
        
        # Add start point if provided
        if start_point:
            branch_command += f" {start_point}"
        
        # Execute the command
        stdout, stderr, return_code = await execution_engine.execute_command(
            branch_command,
            check_safety=True,
            working_dir=str(path_obj)
        )
        
        if return_code != 0:
            return {
                "success": False,
                "error": f"Failed to create branch: {stderr}",
                "command": branch_command,
                "stdout": stdout,
                "stderr": stderr
            }
        
        return {
            "success": True,
            "message": f"Branch {branch_name} created successfully",
            "command": branch_command,
            "stdout": stdout,
            "stderr": stderr
        }
    
    async def get_repository_status(
        self, 
        path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Get the status of a Git repository.
        
        Args:
            path: Path to the Git repository
            
        Returns:
            Dictionary with the repository status
        """
        path_obj = Path(path)
        
        # Check if path is a Git repository
        if not (path_obj / ".git").exists():
            return {
                "is_repo": False,
                "error": f"Not a Git repository: {path}",
                "command": None,
                "stdout": "",
                "stderr": f"Not a Git repository: {path}"
            }
        
        # Get current branch
        branch_command = "git branch --show-current"
        branch_stdout, branch_stderr, branch_code = await execution_engine.execute_command(
            branch_command,
            check_safety=True,
            working_dir=str(path_obj)
        )
        
        current_branch = branch_stdout.strip() if branch_code == 0 else "unknown"
        
        # Get status
        status_command = "git status --porcelain"
        status_stdout, status_stderr, status_code = await execution_engine.execute_command(
            status_command,
            check_safety=True,
            working_dir=str(path_obj)
        )
        
        if status_code != 0:
            return {
                "is_repo": True,
                "current_branch": current_branch,
                "error": f"Failed to get status: {status_stderr}",
                "command": status_command,
                "stdout": status_stdout,
                "stderr": status_stderr
            }
        
        # Parse status output
        status_lines = status_stdout.strip().split('\n') if status_stdout.strip() else []
        
        modified_files = []
        untracked_files = []
        staged_files = []
        
        for line in status_lines:
            if not line:
                continue
                
            status_code = line[:2]
            file_path = line[3:]
            
            if status_code.startswith('??'):
                untracked_files.append(file_path)
            elif status_code.startswith('M'):
                modified_files.append(file_path)
            elif status_code.startswith('A'):
                staged_files.append(file_path)
        
        return {
            "is_repo": True,
            "current_branch": current_branch,
            "modified_files": modified_files,
            "untracked_files": untracked_files,
            "staged_files": staged_files,
            "clean": len(status_lines) == 0,
            "command": status_command,
            "stdout": status_stdout,
            "stderr": status_stderr
        }
    
    async def _create_gitignore(
        self, 
        path: Union[str, Path], 
        template: str
    ) -> Dict[str, Any]:
        """
        Create a .gitignore file from a template.
        
        Args:
            path: Path to the Git repository
            template: Template to use (e.g., 'python', 'node')
            
        Returns:
            Dictionary with the operation result
        """
        self._logger.info(f"Creating .gitignore with template {template} in {path}")
        
        path_obj = Path(path)
        
        # Check if .gitignore already exists
        gitignore_path = path_obj / ".gitignore"
        if gitignore_path.exists():
            return {
                "success": True,
                "message": ".gitignore already exists",
                "path": str(gitignore_path),
                "modified": False
            }
        
        # Get template content
        if template == "python":
            content = """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
dist/
build/
*.egg-info/

# Virtual environments
venv/
env/
.env/
.venv/

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
coverage.xml
*.cover

# Local development settings
.env
.env.local

# IDE specific files
.idea/
.vscode/
*.swp
*.swo
"""
        elif template == "node":
            content = """
# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Dependency directories
node_modules/
jspm_packages/

# Build output
dist/
build/

# Environment variables
.env
.env.local
.env.development
.env.test
.env.production

# IDE specific files
.idea/
.vscode/
*.swp
*.swo

# OS specific files
.DS_Store
Thumbs.db
"""
        else:
            # Generic gitignore
            content = """
# IDE specific files
.idea/
.vscode/
*.swp
*.swo

# OS specific files
.DS_Store
Thumbs.db

# Local development settings
.env
.env.local

# Logs
*.log
"""
        
        # Write the .gitignore file
        try:
            with open(gitignore_path, 'w') as f:
                f.write(content.strip())
            
            return {
                "success": True,
                "message": ".gitignore created successfully",
                "path": str(gitignore_path),
                "modified": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create .gitignore: {str(e)}",
                "path": str(gitignore_path),
                "modified": False
            }

# Global Git integration instance
git_integration = GitIntegration()
