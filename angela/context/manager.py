"""
Context management for Angela CLI.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from angela.constants import PROJECT_MARKERS
from angela.utils.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """
    Manages context information about the current environment.
    
    The context includes:
    - Current working directory
    - Project root (if detected)
    - Project type (if detected)
    """
    
    def __init__(self):
        self._cwd: Path = Path.cwd()
        self._project_root: Optional[Path] = None
        self._project_type: Optional[str] = None
        
        # Initialize context
        self.refresh_context()
    
    def refresh_context(self) -> None:
        """Refresh all context information."""
        self._update_cwd()
        self._detect_project_root()
        logger.debug(f"Context refreshed: cwd={self._cwd}, project_root={self._project_root}")
    
    def _update_cwd(self) -> None:
        """Update the current working directory."""
        self._cwd = Path.cwd()
    
    def _detect_project_root(self) -> None:
        """
        Detect the project root by looking for marker files.
        
        Traverses up from the current directory until a marker is found or
        the filesystem root is reached.
        """
        self._project_root = None
        self._project_type = None
        
        # Start from current directory
        current_dir = self._cwd
        
        # Walk up the directory tree
        while current_dir != current_dir.parent:  # Stop at filesystem root
            # Check for project markers
            for marker in PROJECT_MARKERS:
                marker_path = current_dir / marker
                if marker_path.exists():
                    self._project_root = current_dir
                    self._project_type = self._determine_project_type(marker)
                    logger.debug(f"Project detected: {self._project_type} at {self._project_root}")
                    return
            
            # Move up to parent directory
            current_dir = current_dir.parent
    
    def _determine_project_type(self, marker: str) -> str:
        """
        Determine the project type based on the marker file.
        
        Args:
            marker: The marker file that was found.
            
        Returns:
            A string representing the project type.
        """
        marker_to_type = {
            ".git": "git",
            "package.json": "node",
            "requirements.txt": "python",
            "Cargo.toml": "rust",
            "pom.xml": "maven",
            "build.gradle": "gradle",
            "Dockerfile": "docker",
            "docker-compose.yml": "docker-compose",
            "CMakeLists.txt": "cmake",
            "Makefile": "make",
        }
        
        return marker_to_type.get(marker, "unknown")
    
    @property
    def cwd(self) -> Path:
        """Get the current working directory."""
        return self._cwd
    
    @property
    def project_root(self) -> Optional[Path]:
        """Get the detected project root."""
        return self._project_root
    
    @property
    def project_type(self) -> Optional[str]:
        """Get the detected project type."""
        return self._project_type
    
    @property
    def is_in_project(self) -> bool:
        """Check if the current directory is within a project."""
        return self._project_root is not None
    
    @property
    def relative_path(self) -> Optional[Path]:
        """Get the path relative to the project root."""
        if not self._project_root:
            return None
        
        return self._cwd.relative_to(self._project_root)
    
    def get_context_dict(self) -> Dict[str, Any]:
        """
        Get a dictionary representation of the current context.
        
        Returns:
            A dictionary with context information.
        """
        return {
            "cwd": str(self._cwd),
            "project_root": str(self._project_root) if self._project_root else None,
            "project_type": self._project_type,
            "is_in_project": self.is_in_project,
            "relative_path": str(self.relative_path) if self.relative_path else None,
        }


# Global context manager instance
context_manager = ContextManager()
