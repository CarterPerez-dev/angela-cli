"""
Tests for file activity tracker functionality.
"""
import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from angela.context.file_activity import (
    FileActivity, ActivityType, file_activity_tracker
)


def test_file_activity_creation():
    """Test creating a file activity."""
    path = Path("/test/file.txt")
    activity_type = ActivityType.VIEWED
    timestamp = time.time()
    command = "cat file.txt"
    details = {"key": "value"}
    
    activity = FileActivity(path, activity_type, timestamp, command, details)
    
    assert activity.path == path
    assert activity.activity_type == activity_type
    assert activity.timestamp == timestamp
    assert activity.command == command
    assert activity.details == details


def test_file_activity_to_dict():
    """Test converting a file activity to a dictionary."""
    path = Path("/test/file.txt")
    activity_type = ActivityType.VIEWED
    timestamp = time.time()
    
    activity = FileActivity(path, activity_type, timestamp)
    activity_dict = activity.to_dict()
    
    assert activity_dict["path"] == str(path)
    assert activity_dict["name"] == path.name
    assert activity_dict["activity_type"] == activity_type.value
    assert activity_dict["timestamp"] == timestamp
    assert "datetime" in activity_dict


def test_file_activity_from_dict():
    """Test creating a file activity from a dictionary."""
    data = {
        "path": "/test/file.txt",
        "activity_type": "viewed",
        "timestamp": time.time(),
        "command": "cat file.txt",
        "details": {"key": "value"}
    }
    
    activity = FileActivity.from_dict(data)
    
    assert activity.path == Path(data["path"])
    assert activity.activity_type == ActivityType(data["activity_type"])
    assert activity.timestamp == data["timestamp"]
    assert activity.command == data["command"]
    assert activity.details == data["details"]


def test_track_activity():
    """Test tracking a file activity."""
    # Create a clean tracker for this test
    tracker = FileActivity(Path("/test/file.txt"), ActivityType.VIEWED)
    
    with patch('angela.context.session.session_manager.add_entity') as mock_add_entity:
        file_activity_tracker.track_activity(
            path="/test/file.txt",
            activity_type=ActivityType.VIEWED,
            command="cat file.txt",
            details={"test": True}
        )
        
        # Check that session was updated
        assert mock_add_entity.call_count == 2
        
        # Get the tracked activities
        activities = file_activity_tracker.get_recent_activities(limit=1)
        
        # Should have at least one activity
        assert len(activities) >= 1
        
        # Latest activity should match what we tracked
        latest = activities[0]
        assert latest["path"] == "/test/file.txt"
        assert latest["activity_type"] == "viewed"
        assert latest["command"] == "cat file.txt"
        assert "details" in latest and latest["details"].get("test") is True


def test_track_specific_activities():
    """Test tracking specific types of file activities."""
    with patch('angela.context.file_activity.file_activity_tracker.track_activity') as mock_track:
        # Test tracking file creation
        file_activity_tracker.track_file_creation("/test/file.txt", "touch file.txt")
        mock_track.assert_called_with(
            path="/test/file.txt",
            activity_type=ActivityType.CREATED,
            command="touch file.txt",
            details=None
        )
        
        # Test tracking file modification
        file_activity_tracker.track_file_modification("/test/file.txt", "echo 'text' > file.txt")
        mock_track.assert_called_with(
            path="/test/file.txt",
            activity_type=ActivityType.MODIFIED,
            command="echo 'text' > file.txt",
            details=None
        )
        
        # Test tracking file deletion
        file_activity_tracker.track_file_deletion("/test/file.txt", "rm file.txt")
        mock_track.assert_called_with(
            path="/test/file.txt",
            activity_type=ActivityType.DELETED,
            command="rm file.txt",
            details=None
        )
        
        # Test tracking file viewing
        file_activity_tracker.track_file_viewing("/test/file.txt", "cat file.txt")
        mock_track.assert_called_with(
            path="/test/file.txt",
            activity_type=ActivityType.VIEWED,
            command="cat file.txt",
            details=None
        )


def test_get_recent_activities():
    """Test getting recent file activities."""
    # Create a clean tracker for this test
    tracker = FileActivity(Path("/test/file.txt"), ActivityType.VIEWED)
    
    # Track multiple activities
    file_activity_tracker.track_file_viewing("/test/file1.txt", "cat file1.txt")
    file_activity_tracker.track_file_creation("/test/file2.txt", "touch file2.txt")
    file_activity_tracker.track_file_modification("/test/file3.txt", "echo 'text' > file3.txt")
    
    # Get all recent activities
    activities = file_activity_tracker.get_recent_activities(limit=10)
    
    # Should have at least 3 activities
    assert len(activities) >= 3
    
    # Check that they're sorted by timestamp (newest first)
    for i in range(len(activities) - 1):
        assert activities[i]["timestamp"] >= activities[i+1]["timestamp"]
    
    # Get activities filtered by type
    viewed_activities = file_activity_tracker.get_recent_activities(
        limit=10,
        activity_types=[ActivityType.VIEWED]
    )
    
    # Should have at least 1 viewed activity
    assert len(viewed_activities) >= 1
    assert all(a["activity_type"] == "viewed" for a in viewed_activities)


def test_get_activities_for_path():
    """Test getting activities for a specific path."""
    # Create a clean tracker for this test
    tracker = FileActivity(Path("/test/file.txt"), ActivityType.VIEWED)
    
    # Track multiple activities for the same file
    file_activity_tracker.track_file_viewing("/test/specific_file.txt", "cat specific_file.txt")
    file_activity_tracker.track_file_modification("/test/specific_file.txt", "echo 'text' > specific_file.txt")
    
    # Also track an activity for a different file
    file_activity_tracker.track_file_viewing("/test/other_file.txt", "cat other_file.txt")
    
    # Get activities for the specific file
    activities = file_activity_tracker.get_activities_for_path("/test/specific_file.txt")
    
    # Should have at least 2 activities
    assert len(activities) >= 2
    
    # All activities should be for the specific file
    assert all(a["path"] == "/test/specific_file.txt" for a in activities)
    
    # Activities should be sorted by timestamp (newest first)
    for i in range(len(activities) - 1):
        assert activities[i]["timestamp"] >= activities[i+1]["timestamp"]


def test_get_most_active_files():
    """Test getting the most actively used files."""
    # Create a clean tracker for this test
    tracker = FileActivity(Path("/test/file.txt"), ActivityType.VIEWED)
    
    # Track multiple activities for different files
    for i in range(5):
        file_activity_tracker.track_file_viewing(f"/test/file{i}.txt", f"cat file{i}.txt")
    
    # Track extra activities for one file to make it the most active
    for i in range(3):
        file_activity_tracker.track_file_modification("/test/file0.txt", f"echo '{i}' > file0.txt")
    
    # Get most active files
    active_files = file_activity_tracker.get_most_active_files(limit=3)
    
    # Should have at least 1 active file
    assert len(active_files) >= 1
    
    # First file should be the most active one
    assert active_files[0]["path"] == "/test/file0.txt"
    assert active_files[0]["count"] >= 4  # 1 view + 3 modifications
    
    # Files should be sorted by count (highest first)
    for i in range(len(active_files) - 1):
        assert active_files[i]["count"] >= active_files[i+1]["count"]
