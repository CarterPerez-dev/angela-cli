"""
Tests for context enhancer functionality.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from angela.context.enhancer import context_enhancer


# Fixture for context mock
@pytest.fixture
def mock_context():
    return {
        "cwd": "/test/cwd",
        "project_root": "/test/project",
        "project_type": "python",
        "session": {
            "entities": {
                "file:test.py": {
                    "type": "file",
                    "value": "/test/project/test.py"
                }
            }
        }
    }


# Fixture for project info mock
@pytest.fixture
def mock_project_info():
    return {
        "project_root": "/test/project",
        "project_type": "python",
        "detected_frameworks": {
            "flask": 0.9,
            "pytest": 0.8
        },
        "dependencies": [
            {"name": "flask", "version_spec": ">=2.0.0", "type": "python"},
            {"name": "pytest", "version_spec": ">=6.0.0", "type": "python"},
            {"name": "requests", "version_spec": ">=2.25.0", "type": "python"}
        ],
        "detected_files": [
            {"path": "app.py", "type": "entry_point"},
            {"path": "requirements.txt", "type": "signature_file"}
        ],
        "structure": {
            "file_counts": {".py": 10, ".txt": 2},
            "main_directories": ["app", "tests"],
            "total_files": 15
        }
    }


@pytest.mark.asyncio
async def test_enrich_context_basic(mock_context):
    """Test basic context enrichment."""
    with patch('angela.context.enhancer.context_enhancer._add_project_info', 
               new_callable=AsyncMock) as mock_add_project:
        with patch('angela.context.enhancer.context_enhancer._add_recent_file_activity', 
                   new_callable=AsyncMock) as mock_add_file_activity:
            with patch('angela.context.enhancer.context_enhancer._add_file_reference_context', 
                       new_callable=AsyncMock) as mock_add_file_ref:
                
                result = await context_enhancer.enrich_context(mock_context)
                
                # Verify all enhancement methods were called
                mock_add_project.assert_called_once()
                mock_add_file_activity.assert_called_once()
                mock_add_file_ref.assert_called_once()
                
                # Verify the context is returned
                assert result is not None
                assert "cwd" in result
                assert result["cwd"] == "/test/cwd"


@pytest.mark.asyncio
async def test_add_project_info(mock_context, mock_project_info):
    """Test adding project information to context."""
    # Create a copy of the context that will be modified
    context = dict(mock_context)
    
    with patch('angela.context.project_inference.project_inference.infer_project_info', 
               new_callable=AsyncMock, return_value=mock_project_info):
        await context_enhancer._add_project_info(context, "/test/project")
        
        # Verify the enhanced project info was added
        assert "enhanced_project" in context
        project_info = context["enhanced_project"]
        
        assert project_info["type"] == "python"
        assert "frameworks" in project_info
        assert "dependencies" in project_info
        assert "important_files" in project_info
        assert "structure" in project_info
        
        # Verify dependencies are formatted correctly
        assert "types" in project_info["dependencies"]
        assert "python" in project_info["dependencies"]["types"]
        assert project_info["dependencies"]["total"] == 3
        
        # Verify framework info
        assert "flask" in project_info["frameworks"]
        assert "pytest" in project_info["frameworks"]
        
        # Verify structure info
        assert project_info["structure"]["total_files"] == 15
        assert "main_directories" in project_info["structure"]
        assert "app" in project_info["structure"]["main_directories"]


@pytest.mark.asyncio
async def test_add_file_reference_context(mock_context):
    """Test adding file reference context to context."""
    # Create a copy of the context that will be modified
    context = dict(mock_context)
    
    test_files = [
        MagicMock(name="file1.py", is_file=lambda: True, is_dir=lambda: False),
        MagicMock(name="file2.txt", is_file=lambda: True, is_dir=lambda: False),
        MagicMock(name="dir1", is_file=lambda: False, is_dir=lambda: True)
    ]
    
    with patch('pathlib.Path.glob', return_value=test_files):
        await context_enhancer._add_file_reference_context(context)
        
        # Verify the file reference context was added
        assert "file_reference" in context
        file_ref = context["file_reference"]
        
        assert "files" in file_ref
        assert "directories" in file_ref
        assert len(file_ref["files"]) == 2  # Two files
        assert len(file_ref["directories"]) == 1  # One directory
        assert file_ref["total"] == 3  # Total


@pytest.mark.asyncio
async def test_add_recent_file_activity(mock_context):
    """Test adding recent file activity to context."""
    # Create a copy of the context that will be modified
    context = dict(mock_context)
    
    # No need to patch anything, should use the session data in the mock_context
    await context_enhancer._add_recent_file_activity(context)
    
    # Verify the recent files context was added
    assert "recent_files" in context
    recent_files = context["recent_files"]
    
    assert "accessed" in recent_files
    assert len(recent_files["accessed"]) == 1  # One file in the mock session
    assert "/test/project/test.py" in recent_files["accessed"]


def test_format_dependencies(mock_project_info):
    """Test formatting dependencies."""
    dependencies = mock_project_info["dependencies"]
    result = context_enhancer._format_dependencies(dependencies)
    
    assert "types" in result
    assert "python" in result["types"]
    assert result["total"] == 3
    assert len(result["top_dependencies"]) == 3
    assert "flask" in result["top_dependencies"]
    assert "pytest" in result["top_dependencies"]
    assert "requests" in result["top_dependencies"]


def test_format_important_files(mock_project_info):
    """Test formatting important files."""
    files = mock_project_info["detected_files"]
    result = context_enhancer._format_important_files(files)
    
    assert "types" in result
    assert "entry_point" in result["types"]
    assert "signature_file" in result["types"]
    assert result["total"] == 2
    assert len(result["paths"]) == 2
    assert "app.py" in result["paths"]
    assert "requirements.txt" in result["paths"]


def test_summarize_structure(mock_project_info):
    """Test summarizing structure."""
    structure = mock_project_info["structure"]
    result = context_enhancer._summarize_structure(structure)
    
    assert "file_counts" in result
    assert ".py" in result["file_counts"]
    assert result["file_counts"][".py"] == 10
    assert result["total_files"] == 15
    assert "main_directories" in result
    assert "app" in result["main_directories"]
    assert "tests" in result["main_directories"]
