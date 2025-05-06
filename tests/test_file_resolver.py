"""
Tests for file resolver functionality.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from angela.context.file_resolver import file_resolver


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
                },
                "recent_file:data.csv": {
                    "type": "recent_file",
                    "value": "/test/project/data/data.csv"
                }
            }
        }
    }


# Tests for resolve_reference
@pytest.mark.asyncio
async def test_resolve_exact_path_absolute(mock_context):
    """Test resolving an absolute path."""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.is_absolute', return_value=True):
            result = await file_resolver._resolve_exact_path("/test/file.txt", mock_context)
            assert result == Path("/test/file.txt")


@pytest.mark.asyncio
async def test_resolve_exact_path_relative_cwd(mock_context):
    """Test resolving a path relative to CWD."""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.is_absolute', return_value=False):
            result = await file_resolver._resolve_exact_path("file.txt", mock_context)
            assert result == Path("/test/cwd/file.txt")


@pytest.mark.asyncio
async def test_resolve_exact_path_relative_project(mock_context):
    """Test resolving a path relative to project root."""
    def exists_side_effect(path):
        return str(path) == "/test/project/file.txt"
    
    with patch('pathlib.Path.exists', side_effect=exists_side_effect):
        with patch('pathlib.Path.is_absolute', return_value=False):
            result = await file_resolver._resolve_exact_path("file.txt", mock_context)
            assert result == Path("/test/project/file.txt")


@pytest.mark.asyncio
async def test_resolve_special_reference_current_file(mock_context):
    """Test resolving 'current file' reference."""
    current_file_context = dict(mock_context)
    current_file_context["current_file"] = {"path": "/test/current.py"}
    
    result = await file_resolver._resolve_special_reference("current file", current_file_context)
    assert result == Path("/test/current.py")


@pytest.mark.asyncio
async def test_resolve_special_reference_last_file(mock_context):
    """Test resolving 'last file' reference."""
    result = await file_resolver._resolve_special_reference("last file", mock_context)
    assert result == Path("/test/project/data/data.csv") or result == Path("/test/project/test.py")


@pytest.mark.asyncio
async def test_resolve_recent_file(mock_context):
    """Test resolving a reference against recently used files."""
    result = await file_resolver._resolve_recent_file("data.csv", mock_context)
    assert result == Path("/test/project/data/data.csv")


@pytest.mark.asyncio
async def test_resolve_fuzzy_match(mock_context):
    """Test resolving a fuzzy match."""
    test_files = [
        Path("/test/cwd/testfile.py"),
        Path("/test/cwd/otherfile.txt")
    ]
    
    with patch('pathlib.Path.glob', return_value=test_files):
        # Should match testfile.py
        result = await file_resolver._resolve_fuzzy_match("testfile", mock_context, None)
        assert result == Path("/test/cwd/testfile.py")


@pytest.mark.asyncio
async def test_resolve_pattern_match(mock_context):
    """Test resolving a pattern match."""
    test_matches = [Path("/test/cwd/test_data.csv")]
    
    with patch('pathlib.Path.glob', return_value=test_matches):
        result = await file_resolver._resolve_pattern_match("*data*", mock_context, None)
        assert result == Path("/test/cwd/test_data.csv")


@pytest.mark.asyncio
async def test_resolve_reference_integration(mock_context):
    """Test the resolve_reference method with mocks."""
    # Mock the individual resolution methods
    with patch('angela.context.file_resolver.file_resolver._resolve_exact_path', 
               return_value=None) as mock_exact:
        with patch('angela.context.file_resolver.file_resolver._resolve_special_reference', 
                   return_value=None) as mock_special:
            with patch('angela.context.file_resolver.file_resolver._resolve_recent_file', 
                      return_value=None) as mock_recent:
                with patch('angela.context.file_resolver.file_resolver._resolve_fuzzy_match', 
                          return_value=Path("/test/found.py")) as mock_fuzzy:
                    with patch('angela.context.file_resolver.file_resolver._resolve_pattern_match', 
                              return_value=None) as mock_pattern:
                        with patch('angela.context.file_resolver.file_resolver._record_resolution') as mock_record:
                            
                            # Test that it tries each method in order
                            result = await file_resolver.resolve_reference("test.py", mock_context)
                            
                            # Check that it returned the result from fuzzy match
                            assert result == Path("/test/found.py")
                            
                            # Check that it tried each method in order
                            mock_exact.assert_called_once()
                            mock_special.assert_called_once()
                            mock_recent.assert_called_once()
                            mock_fuzzy.assert_called_once()
                            mock_pattern.assert_not_called()  # Should not be called since fuzzy found a result
                            mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_extract_references(mock_context):
    """Test extracting file references from text."""
    # Mock resolve_reference to return a path for 'test.py' and None for others
    async def mock_resolve(ref, ctx, **kwargs):
        if ref == "test.py":
            return Path("/test/project/test.py")
        return None
    
    with patch('angela.context.file_resolver.file_resolver.resolve_reference', 
               side_effect=mock_resolve):
        text = "Please open test.py and check data.csv"
        results = await file_resolver.extract_references(text, mock_context)
        
        # Should find both references but only resolve test.py
        assert len(results) >= 2
        assert any(ref == "test.py" and path == Path("/test/project/test.py") 
                  for ref, path in results)
        assert any(ref == "data.csv" and path is None 
                  for ref, path in results)
