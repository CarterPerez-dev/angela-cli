# angela/workflows/sharing.py

import os
import sys
import json
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import uuid
import hashlib

from pydantic import BaseModel, Field

from angela.config import config_manager  # Changed from angela.api.config import get_config_manager
from angela.utils.logging import get_logger
from angela.api.workflows import get_workflow_manager, get_workflow_model_classes

logger = get_logger(__name__)


Workflow, _ = get_workflow_model_classes()

# Constants
WORKFLOW_EXPORT_DIR = config_manager.CONFIG_DIR / "exported_workflows"
WORKFLOW_IMPORT_DIR = config_manager.CONFIG_DIR / "imported_workflows"

class WorkflowExportMetadata(BaseModel):
    """Metadata for an exported workflow package."""
    id: str = Field(..., description="Unique identifier for this workflow package")
    name: str = Field(..., description="Name of the workflow")
    version: str = Field("1.0.0", description="Version of the workflow")
    description: str = Field(..., description="Description of the workflow")
    author: Optional[str] = Field(None, description="Author of the workflow")
    created: str = Field(..., description="Creation timestamp")
    exported: str = Field(..., description="Export timestamp")
    checksum: str = Field(..., description="SHA-256 checksum of the workflow data")
    tags: List[str] = Field(default_factory=list, description="Tags for the workflow")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="External dependencies")

class WorkflowSharingManager:
    """Manager for workflow sharing, importing, and exporting."""
    
    def __init__(self, workflow_manager=None):
        """
        Initialize the workflow sharing manager.
        
        Args:
            workflow_manager: Optional workflow manager instance (for testing)
        """
        # Get workflow_manager through API if not provided
        self._workflow_manager = workflow_manager or get_workflow_manager()
        self._logger = logger
        
        # Ensure directories exist
        WORKFLOW_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        WORKFLOW_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    async def export_workflow(
        self, 
        workflow_name: str,
        output_path: Optional[Path] = None,
        include_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Export a workflow to a shareable package.
        
        Args:
            workflow_name: Name of the workflow to export
            output_path: Optional custom output path
            include_dependencies: Whether to include external dependencies
            
        Returns:
            Dictionary with export results
        """
        # Get the workflow
        workflow = self._workflow_manager.get_workflow(workflow_name)
        if not workflow:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_name}"
            }
        
        try:
            # Create a temporary directory for packaging
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Convert workflow to serializable dict
                workflow_dict = workflow.dict()
                # Handle datetime serialization
                workflow_dict["created"] = workflow_dict["created"].isoformat()
                workflow_dict["modified"] = workflow_dict["modified"].isoformat()
                
                # Create workflow data file
                workflow_data_path = temp_path / "workflow.json"
                with open(workflow_data_path, "w") as f:
                    json.dump(workflow_dict, f, indent=2)
                
                # Generate checksum
                checksum = self._generate_checksum(workflow_data_path)
                
                # Create metadata
                metadata = WorkflowExportMetadata(
                    id=str(uuid.uuid4()),
                    name=workflow.name,
                    description=workflow.description,
                    author=workflow.author,
                    created=workflow.created.isoformat(),
                    exported=datetime.now().isoformat(),
                    checksum=checksum,
                    tags=workflow.tags
                )
                
                # Detect dependencies if requested
                if include_dependencies:
                    dependencies = await self._detect_dependencies(workflow)
                    metadata.dependencies = dependencies
                
                # Write metadata
                metadata_path = temp_path / "metadata.json"
                with open(metadata_path, "w") as f:
                    json.dump(metadata.dict(), f, indent=2)
                
                # Create README with information
                readme_path = temp_path / "README.md"
                with open(readme_path, "w") as f:
                    f.write(f"# {workflow.name}\n\n")
                    f.write(f"{workflow.description}\n\n")
                    if workflow.author:
                        f.write(f"Author: {workflow.author}\n\n")
                    f.write(f"Created: {workflow.created.isoformat()}\n")
                    f.write(f"Exported: {datetime.now().isoformat()}\n\n")
                    f.write("## Steps\n\n")
                    for i, step in enumerate(workflow.steps, 1):
                        f.write(f"### Step {i}: {step.command}\n")
                        f.write(f"{step.explanation}\n\n")
                
                # Determine output path
                if not output_path:
                    safe_name = workflow.name.replace(" ", "_").lower()
                    output_path = WORKFLOW_EXPORT_DIR / f"{safe_name}.angela-workflow"
                
                # Create zip archive
                with zipfile.ZipFile(output_path, "w") as zip_file:
                    for file_path in [workflow_data_path, metadata_path, readme_path]:
                        zip_file.write(file_path, arcname=file_path.name)
                
                return {
                    "success": True,
                    "workflow": workflow.name,
                    "output_path": str(output_path),
                    "metadata": metadata.dict()
                }
                
        except Exception as e:
            self._logger.exception(f"Error exporting workflow {workflow_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Export failed: {str(e)}"
            }
    
    async def import_workflow(
        self, 
        workflow_path: Union[str, Path],
        rename: Optional[str] = None,
        replace_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Import a workflow from a package.
        
        Args:
            workflow_path: Path to the workflow package
            rename: Optional new name for the workflow
            replace_existing: Whether to replace existing workflow with same name
            
        Returns:
            Dictionary with import results
        """
        path_obj = Path(workflow_path)
        
        # Check if file exists
        if not path_obj.exists():
            return {
                "success": False,
                "error": f"File not found: {path_obj}"
            }
        
        try:
            # Create a temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract the zip archive
                with zipfile.ZipFile(path_obj, "r") as zip_file:
                    zip_file.extractall(temp_path)
                
                # Check metadata
                metadata_path = temp_path / "metadata.json"
                if not metadata_path.exists():
                    return {
                        "success": False,
                        "error": "Invalid workflow package: missing metadata.json"
                    }
                
                # Load metadata
                with open(metadata_path, "r") as f:
                    metadata = WorkflowExportMetadata(**json.load(f))
                
                # Check workflow data
                workflow_data_path = temp_path / "workflow.json"
                if not workflow_data_path.exists():
                    return {
                        "success": False,
                        "error": "Invalid workflow package: missing workflow.json"
                    }
                
                # Verify checksum
                computed_checksum = self._generate_checksum(workflow_data_path)
                if computed_checksum != metadata.checksum:
                    return {
                        "success": False,
                        "error": "Checksum verification failed. The workflow package may be corrupted."
                    }
                
                # Load workflow data
                with open(workflow_data_path, "r") as f:
                    workflow_data = json.load(f)
                
                # Apply rename if provided
                if rename:
                    workflow_data["name"] = rename
                
                # Check if workflow already exists
                existing_workflow = self._workflow_manager.get_workflow(workflow_data["name"])
                if existing_workflow and not replace_existing:
                    return {
                        "success": False,
                        "error": f"Workflow '{workflow_data['name']}' already exists. Use replace_existing=True to replace it."
                    }
                
                # Import the workflow
                workflow = await self._workflow_manager.define_workflow_from_data(
                    workflow_data,
                    source=f"Imported from {path_obj.name}"
                )
                
                return {
                    "success": True,
                    "workflow": workflow.name,
                    "metadata": metadata.dict()
                }
                
        except Exception as e:
            self._logger.exception(f"Error importing workflow from {workflow_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Import failed: {str(e)}"
            }
    
    def _generate_checksum(self, file_path: Path) -> str:
        """
        Generate SHA-256 checksum of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of the checksum
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def _detect_dependencies(self, workflow: Workflow) -> Dict[str, str]:
        """
        Detect external dependencies of a workflow.
        
        Args:
            workflow: The workflow to analyze
            
        Returns:
            Dictionary of dependencies
        """
        dependencies = {}
        
        # Check for tool dependencies in commands
        for step in workflow.steps:
            command = step.command.split()[0] if step.command else ""
            
            # Common tools to check
            if command in ["python", "python3"]:
                # Check Python version
                result = await self._run_command("python --version")
                if result["success"]:
                    dependencies["python"] = result["stdout"].strip().replace("Python ", "")
            elif command in ["node", "npm"]:
                # Check Node.js/npm version
                result = await self._run_command("node --version")
                if result["success"]:
                    dependencies["node"] = result["stdout"].strip().replace("v", "")
            elif command == "docker":
                # Check Docker version
                result = await self._run_command("docker --version")
                if result["success"]:
                    dependencies["docker"] = result["stdout"].strip()
            # Add more tool checks as needed
        
        return dependencies
    
    async def _run_command(self, command: str) -> Dict[str, Any]:
        """
        Run a shell command and return its output.
        
        Args:
            command: The command to run
            
        Returns:
            Dictionary with command results
        """
        import asyncio
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "command": command,
                "stdout": stdout.decode('utf-8', errors='replace').strip(),
                "stderr": stderr.decode('utf-8', errors='replace').strip(),
                "return_code": process.returncode,
                "success": process.returncode == 0
            }
        except Exception as e:
            self._logger.error(f"Error running command '{command}': {str(e)}")
            return {
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "success": False
            }

# Global workflow sharing manager instance
workflow_sharing_manager = WorkflowSharingManager(get_workflow_manager)
