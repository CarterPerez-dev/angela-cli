# angela/generation/models.py
"""
Data models for code generation.

This module defines the data models used throughout the code generation system,
extracted to avoid circular dependencies between modules.
"""
from typing import Dict, Any, List, Optional, Set, Union
from pathlib import Path
from pydantic import BaseModel, Field

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
