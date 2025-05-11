# angela/context/manager.py
"""
Context management for Angela CLI.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from angela.constants import PROJECT_MARKERS
from angela.utils.logging import get_logger
from angela.api.context import get_file_detector

logger = get_logger(__name__)


class ContextManager:
    """
    Manages context information about the current environment.
    
    The context includes:
    - Current working directory
    - Project root (if detected)
    - Project type (if detected)
    - File details for current or specified path
    """
    
    def __init__(self):
        self._cwd: Path = Path.cwd()
        self._project_root: Optional[Path] = None
        self._project_type: Optional[str] = None
        self._current_file: Optional[Path] = None
        self._file_cache: Dict[str, Dict[str, Any]] = {}
        
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
    
    def set_current_file(self, file_path: Path) -> None:
        """
        Set the current file being worked on.
        
        Args:
            file_path: The path to the current file.
        """
        self._current_file = file_path
    
    def get_file_info(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get information about a file or the current file.
        
        Args:
            path: The path to get information about, or None to use the current file.
            
        Returns:
            A dictionary with file information, or an empty dict if no file is available.
        """
        file_path = path or self._current_file
        if not file_path:
            return {}
        
        # Check if we have cached information
        cache_key = str(file_path)
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]
        
        # If file doesn't exist, return minimal info
        if not file_path.exists():
            return {
                "path": str(file_path),
                "exists": False,
                "name": file_path.name,
                "extension": file_path.suffix,
            }
        
        # Get basic file info
        stat = file_path.stat()
        
        # Get detailed file type info
        file_detector = get_file_detector()
        type_info = file_detector.detect_file_type(file_path)
        
        # Create the result
        result = {
            "path": str(file_path),
            "exists": True,
            "name": file_path.name,
            "extension": file_path.suffix,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_dir": file_path.is_dir(),
            "type": type_info["type"],
            "language": type_info["language"],
            "mime_type": type_info["mime_type"],
            "binary": type_info["binary"],
        }
        
        # Cache the result
        self._file_cache[cache_key] = result
        
        return result
    
    def get_directory_contents(self, path: Optional[Path] = None, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        Get information about the contents of a directory.
        
        Args:
            path: The directory path to examine, or None to use the current directory.
            include_hidden: Whether to include hidden files (starting with .).
            
        Returns:
            A list of dictionaries with information about each item in the directory.
        """
        dir_path = path or self._cwd
        if not dir_path.is_dir():
            return []
        
        result = []
        
        try:
            for item in dir_path.iterdir():
                # Skip hidden files unless requested
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                # Get information about this item
                item_info = self.get_file_info(item)
                result.append(item_info)
            
            # Sort by directories first, then by name
            result.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return result
        
        except Exception as e:
            logger.exception(f"Error getting directory contents for {dir_path}: {str(e)}")
            return []
    
    def get_file_preview(self, path: Optional[Path] = None, max_lines: int = 10) -> Optional[str]:
        """
        Get a preview of a file's contents.
        
        Args:
            path: The file path to preview, or None to use the current file.
            max_lines: Maximum number of lines to preview.
            
        Returns:
            A string with a preview of the file's contents, or None if not available.
        """
        file_path = path or self._current_file
        if not file_path or not file_path.is_file():
            return None
        
        file_detector = get_file_detector()
        return file_detector.get_content_preview(file_path, max_lines=max_lines)
    
    def find_files(
        self, 
        pattern: str, 
        base_dir: Optional[Path] = None, 
        max_depth: int = 10,
        include_hidden: bool = False
    ) -> List[Path]:
        """
        Find files matching a pattern.
        
        Args:
            pattern: The glob pattern to match.
            base_dir: The directory to start from, or None to use the current directory.
            max_depth: Maximum directory depth to search.
            include_hidden: Whether to include hidden files (starting with .).
            
        Returns:
            A list of paths matching the pattern.
        """
        start_dir = base_dir or self._cwd
        if not start_dir.is_dir():
            return []
        
        result = []
        
        try:
            # Use Path.glob for pattern matching
            for path in start_dir.glob(pattern):
                # Skip hidden files unless requested
                if not include_hidden and any(part.startswith('.') for part in path.parts):
                    continue
                
                result.append(path)
            
            return result
        
        except Exception as e:
            logger.exception(f"Error finding files with pattern {pattern}: {str(e)}")
            return []
    
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
    
    @property
    def current_file(self) -> Optional[Path]:
        """Get the current file being worked on."""
        return self._current_file
    
    def get_context_dict(self) -> Dict[str, Any]:
        """
        Get a dictionary representation of the current context.
        
        Returns:
            A dictionary with context information.
        """
        context = {
            "cwd": str(self._cwd),
            "project_root": str(self._project_root) if self._project_root else None,
            "project_type": self._project_type,
            "is_in_project": self.is_in_project,
            "relative_path": str(self.relative_path) if self.relative_path else None,
        }
        
        # Add information about the current file if available
        if self._current_file:
            context["current_file"] = self.get_file_info(self._current_file)
        
        return context


# Global context manager instance
context_manager = ContextManager()
