"""
File activity tracking for Angela CLI.

This module provides functionality to track file activities such as access,
modification, and creation, and to maintain a history of these activities.
"""
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Union

from angela.context.session import session_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class ActivityType(str, Enum):
    """Types of file activities."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    VIEWED = "viewed"
    EXECUTED = "executed"
    ANALYZED = "analyzed"
    OTHER = "other"

class FileActivity:
    """Represents a file activity with related metadata."""
    
    def __init__(
        self,
        path: Union[str, Path],
        activity_type: ActivityType,
        timestamp: Optional[float] = None,
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a file activity.
        
        Args:
            path: Path to the file/directory
            activity_type: Type of activity
            timestamp: Optional timestamp (defaults to current time)
            command: Optional command that triggered the activity
            details: Optional additional details
        """
        self.path = Path(path) if isinstance(path, str) else path
        self.activity_type = activity_type
        self.timestamp = timestamp or time.time()
        self.command = command
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": str(self.path),
            "name": self.path.name,
            "activity_type": self.activity_type.value,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "command": self.command,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileActivity':
        """Create from dictionary."""
        return cls(
            path=data["path"],
            activity_type=ActivityType(data["activity_type"]),
            timestamp=data["timestamp"],
            command=data.get("command"),
            details=data.get("details", {})
        )


class FileActivityTracker:
    """
    Tracker for file activities with session integration.
    
    Provides methods to:
    1. Track file activities (creation, modification, etc.)
    2. Retrieve recent file activities
    3. Integrate with session management
    """
    
    def __init__(self, max_activities: int = 100):
        """
        Initialize the file activity tracker.
        
        Args:
            max_activities: Maximum number of activities to track
        """
        self._logger = logger
        self._activities: List[FileActivity] = []
        self._max_activities = max_activities
    
    def track_activity(
        self,
        path: Union[str, Path],
        activity_type: ActivityType,
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a file activity.
        
        Args:
            path: Path to the file/directory
            activity_type: Type of activity
            command: Optional command that triggered the activity
            details: Optional additional details
        """
        # Create a new activity
        activity = FileActivity(
            path=path,
            activity_type=activity_type,
            command=command,
            details=details
        )
        
        # Add to the activity list
        self._activities.append(activity)
        
        # Trim if needed
        if len(self._activities) > self._max_activities:
            self._activities = self._activities[-self._max_activities:]
        
        # Update session
        self._update_session(activity)
        
        self._logger.debug(f"Tracked {activity_type.value} activity for {path}")
    
    def track_file_creation(
        self,
        path: Union[str, Path],
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track file creation.
        
        Args:
            path: Path to the created file
            command: Optional command that triggered the creation
            details: Optional additional details
        """
        self.track_activity(
            path=path,
            activity_type=ActivityType.CREATED,
            command=command,
            details=details
        )
    
    def track_file_modification(
        self,
        path: Union[str, Path],
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track file modification.
        
        Args:
            path: Path to the modified file
            command: Optional command that triggered the modification
            details: Optional additional details
        """
        self.track_activity(
            path=path,
            activity_type=ActivityType.MODIFIED,
            command=command,
            details=details
        )
    
    def track_file_deletion(
        self,
        path: Union[str, Path],
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track file deletion.
        
        Args:
            path: Path to the deleted file
            command: Optional command that triggered the deletion
            details: Optional additional details
        """
        self.track_activity(
            path=path,
            activity_type=ActivityType.DELETED,
            command=command,
            details=details
        )
    
    def track_file_viewing(
        self,
        path: Union[str, Path],
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track file viewing.
        
        Args:
            path: Path to the viewed file
            command: Optional command that triggered the viewing
            details: Optional additional details
        """
        self.track_activity(
            path=path,
            activity_type=ActivityType.VIEWED,
            command=command,
            details=details
        )
    
    def get_recent_activities(
        self,
        limit: int = 10,
        activity_types: Optional[List[ActivityType]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent file activities.
        
        Args:
            limit: Maximum number of activities to return
            activity_types: Optional filter for activity types
            
        Returns:
            List of activities as dictionaries
        """
        # Apply filters
        filtered = self._activities
        if activity_types:
            filtered = [a for a in filtered if a.activity_type in activity_types]
        
        # Sort by timestamp (newest first)
        sorted_activities = sorted(filtered, key=lambda a: a.timestamp, reverse=True)
        
        # Convert to dictionaries
        return [a.to_dict() for a in sorted_activities[:limit]]
    
    def get_activities_for_path(
        self,
        path: Union[str, Path],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get activities for a specific path.
        
        Args:
            path: Path to get activities for
            limit: Maximum number of activities to return
            
        Returns:
            List of activities as dictionaries
        """
        path_obj = Path(path) if isinstance(path, str) else path
        
        # Filter by path
        path_activities = [a for a in self._activities if a.path == path_obj]
        
        # Sort by timestamp (newest first)
        sorted_activities = sorted(path_activities, key=lambda a: a.timestamp, reverse=True)
        
        # Convert to dictionaries
        return [a.to_dict() for a in sorted_activities[:limit]]
    
    def get_most_active_files(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most actively used files.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of files with activity counts
        """
        # Count activities by path
        path_counts = {}
        for activity in self._activities:
            path_str = str(activity.path)
            if path_str not in path_counts:
                path_counts[path_str] = {
                    "path": path_str,
                    "name": activity.path.name,
                    "count": 0,
                    "last_activity": None,
                    "activities": set()
                }
            
            path_counts[path_str]["count"] += 1
            path_counts[path_str]["activities"].add(activity.activity_type.value)
            
            # Update last activity if newer
            if path_counts[path_str]["last_activity"] is None or \
               activity.timestamp > path_counts[path_str]["last_activity"]:
                path_counts[path_str]["last_activity"] = activity.timestamp
        
        # Convert to list and sort by count (highest first)
        result = []
        for path_info in path_counts.values():
            # Convert activities set to list
            path_info["activities"] = list(path_info["activities"])
            result.append(path_info)
        
        result.sort(key=lambda x: x["count"], reverse=True)
        
        return result[:limit]
    
    def clear_activities(self) -> None:
        """Clear all tracked activities."""
        self._activities.clear()
        self._logger.debug("Cleared all file activities")
    
    def _update_session(self, activity: FileActivity) -> None:
        """
        Update session with file activity.
        
        Args:
            activity: The file activity to add to the session
        """
        try:
            # Add to session as an entity
            path_name = activity.path.name
            entity_name = f"file:{path_name}"
            
            session_manager.add_entity(
                name=entity_name,
                entity_type="file",
                value=str(activity.path)
            )
            
            # Also add with activity type
            activity_entity_name = f"{activity.activity_type.value}_file:{path_name}"
            session_manager.add_entity(
                name=activity_entity_name,
                entity_type=f"{activity.activity_type.value}_file",
                value=str(activity.path)
            )
        except Exception as e:
            self._logger.error(f"Error updating session with file activity: {str(e)}")

# Global file activity tracker instance
file_activity_tracker = FileActivityTracker()
