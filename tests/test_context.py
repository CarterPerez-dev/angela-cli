# tests/test_context.py
"""
Tests for the context module.
"""
import os
import tempfile
from pathlib import Path

import pytest

from angela.context.manager import ContextManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)
        yield Path(tmp_dir)
        os.chdir(old_dir)


def test_context_manager_init():
    """Test ContextManager initialization."""
    cm = ContextManager()
    assert cm.cwd == Path.cwd()
    assert cm.project_root is None
    assert cm.project_type is None
    assert not cm.is_in_project
    assert cm.relative_path is None


def test_context_manager_refresh(temp_dir):
    """Test ContextManager context refresh."""
    cm = ContextManager()
    assert cm.cwd == temp_dir
    
    # Create a subdirectory and change to it
    sub_dir = temp_dir / "subdir"
    sub_dir.mkdir()
    os.chdir(sub_dir)
    
    # Context should still show the old directory
    assert cm.cwd == temp_dir
    
    # After refresh, context should be updated
    cm.refresh_context()
    assert cm.cwd == sub_dir


def test_project_root_detection(temp_dir):
    """Test project root detection."""
    # Create a mock project structure
    git_dir = temp_dir / ".git"
    git_dir.mkdir()
    
    sub_dir = temp_dir / "src"
    sub_dir.mkdir()
    
    # Initialize context manager in the project root
    cm = ContextManager()
    assert cm.project_root == temp_dir
    assert cm.project_type == "git"
    assert cm.is_in_project
    assert cm.relative_path == Path(".")
    
    # Change to subdirectory
    os.chdir(sub_dir)
    cm.refresh_context()
    
    assert cm.cwd == sub_dir
    assert cm.project_root == temp_dir
    assert cm.project_type == "git"
    assert cm.is_in_project
    assert cm.relative_path == Path("src")


def test_get_context_dict(temp_dir):
    """Test getting context as dictionary."""
    # Create a mock project structure
    git_dir = temp_dir / ".git"
    git_dir.mkdir()
    
    # Initialize context manager in the project root
    cm = ContextManager()
    context_dict = cm.get_context_dict()
    
    assert context_dict["cwd"] == str(temp_dir)
    assert context_dict["project_root"] == str(temp_dir)
    assert context_dict["project_type"] == "git"
    assert context_dict["is_in_project"] is True
    assert context_dict["relative_path"] == "."
