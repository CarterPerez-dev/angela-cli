# tests/conftest.py
"""
Common test fixtures for Angela CLI.
"""
import os
import tempfile
from pathlib import Path

import pytest

from angela.config import AppConfig, ApiConfig, UserConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return AppConfig(
        api=ApiConfig(gemini_api_key="test_api_key"),
        user=UserConfig(default_project_root=None, confirm_all_actions=False),
        debug=True,
    )


@pytest.fixture
def temp_project_dir():
    """
    Create a temporary directory with a mock project structure for testing.
    
    Creates a basic structure with:
    - .git directory (to mark it as a Git repository)
    - src/ directory
    - tests/ directory
    - README.md file
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Store original directory to restore it later
        original_dir = os.getcwd()
        
        # Create project structure
        tmp_path = Path(tmp_dir)
        
        # Create .git directory to mark as Git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        
        # Create some standard directories
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        # Create a README file
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test project for Angela CLI.")
        
        # Change to the temporary directory for testing
        os.chdir(tmp_path)
        
        yield tmp_path
        
        # Restore original directory
        os.chdir(original_dir)
