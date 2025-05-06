"""
Tests for file system operations.
"""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from angela.execution.filesystem import (
    create_directory, delete_directory, create_file, read_file,
    write_file, delete_file, copy_file, move_file, FileSystemError
)


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_create_directory(temp_test_dir):
    """Test directory creation."""
    # Test creating a simple directory
    test_dir = temp_test_dir / "test_dir"
    result = await create_directory(test_dir, dry_run=False)
    
    assert result is True
    assert test_dir.exists()
    assert test_dir.is_dir()
    
    # Test creating nested directories with parents=True
    nested_dir = temp_test_dir / "parent" / "child" / "grandchild"
    result = await create_directory(nested_dir, parents=True, dry_run=False)
    
    assert result is True
    assert nested_dir.exists()
    assert nested_dir.is_dir()
    
    # Test dry run (should not create the directory)
    dry_run_dir = temp_test_dir / "dry_run_dir"
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await create_directory(dry_run_dir, dry_run=True)
        
        assert result is True
        assert not dry_run_dir.exists()


@pytest.mark.asyncio
async def test_delete_directory(temp_test_dir):
    """Test directory deletion."""
    # Create a test directory
    test_dir = temp_test_dir / "test_dir"
    test_dir.mkdir()
    
    # Test deleting the directory
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await delete_directory(test_dir, dry_run=False)
        
        assert result is True
        assert not test_dir.exists()
    
    # Test deleting a nested directory
    nested_dir = temp_test_dir / "parent" / "child"
    nested_dir.mkdir(parents=True)
    
    # Create a file in the nested directory
    test_file = nested_dir / "test.txt"
    test_file.write_text("Test content")
    
    # Test delete with recursive=False (should fail because directory not empty)
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with pytest.raises(FileSystemError):
            await delete_directory(nested_dir.parent, recursive=False)
        
        assert nested_dir.parent.exists()
    
    # Test delete with recursive=True
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_directory", new=AsyncMock()):
            result = await delete_directory(nested_dir.parent, recursive=True)
            
            assert result is True
            assert not nested_dir.parent.exists()


@pytest.mark.asyncio
async def test_create_file(temp_test_dir):
    """Test file creation."""
    # Test creating an empty file (touch)
    test_file = temp_test_dir / "test.txt"
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await create_file(test_file, content=None)
        
        assert result is True
        assert test_file.exists()
        assert test_file.is_file()
        assert test_file.read_text() == ""
    
    # Test creating a file with content
    content_file = temp_test_dir / "content.txt"
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await create_file(content_file, content="Hello, world!")
        
        assert result is True
        assert content_file.exists()
        assert content_file.is_file()
        assert content_file.read_text() == "Hello, world!"
    
    # Test dry run (should not create the file)
    dry_run_file = temp_test_dir / "dry_run.txt"
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await create_file(dry_run_file, content="Test", dry_run=True)
        
        assert result is True
        assert not dry_run_file.exists()


@pytest.mark.asyncio
async def test_read_file(temp_test_dir):
    """Test reading file content."""
    # Create a test file
    test_file = temp_test_dir / "test.txt"
    test_content = "Hello, world!"
    test_file.write_text(test_content)
    
    # Test reading the file
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        content = await read_file(test_file)
        
        assert content == test_content
    
    # Test reading nonexistent file (should raise an exception)
    nonexistent_file = temp_test_dir / "nonexistent.txt"
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with pytest.raises(FileSystemError):
            await read_file(nonexistent_file)
    
    # Test reading binary file
    binary_file = temp_test_dir / "binary.bin"
    binary_content = b"\x00\x01\x02\x03"
    with open(binary_file, "wb") as f:
        f.write(binary_content)
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        content = await read_file(binary_file, binary=True)
        
        assert content == binary_content


@pytest.mark.asyncio
async def test_write_file(temp_test_dir):
    """Test writing to a file."""
    # Test writing to a new file
    test_file = temp_test_dir / "test.txt"
    test_content = "Hello, world!"
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_file", new=AsyncMock()):
            result = await write_file(test_file, test_content)
            
            assert result is True
            assert test_file.exists()
            assert test_file.read_text() == test_content
    
    # Test appending to a file
    append_content = "\nAppended content"
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_file", new=AsyncMock()):
            result = await write_file(test_file, append_content, append=True)
            
            assert result is True
            assert test_file.read_text() == test_content + append_content
    
    # Test writing binary content
    binary_file = temp_test_dir / "binary.bin"
    binary_content = b"\x00\x01\x02\x03"
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await write_file(binary_file, binary_content)
        
        assert result is True
        with open(binary_file, "rb") as f:
            assert f.read() == binary_content
    
    # Test dry run (should not write to the file)
    dry_run_file = temp_test_dir / "dry_run.txt"
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await write_file(dry_run_file, "Test", dry_run=True)
        
        assert result is True
        assert not dry_run_file.exists()


@pytest.mark.asyncio
async def test_delete_file(temp_test_dir):
    """Test file deletion."""
    # Create a test file
    test_file = temp_test_dir / "test.txt"
    test_file.write_text("Test content")
    
    # Test deleting the file
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_file", new=AsyncMock()):
            result = await delete_file(test_file)
            
            assert result is True
            assert not test_file.exists()
    
    # Test deleting a nonexistent file (should raise an exception)
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with pytest.raises(FileSystemError):
            await delete_file(test_file)
    
    # Test deleting a nonexistent file with force=True (should not raise)
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await delete_file(test_file, force=True)
        
        assert result is True
    
    # Test dry run (should not delete the file)
    dry_run_file = temp_test_dir / "dry_run.txt"
    dry_run_file.write_text("Test content")
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await delete_file(dry_run_file, dry_run=True)
        
        assert result is True
        assert dry_run_file.exists()


@pytest.mark.asyncio
async def test_copy_file(temp_test_dir):
    """Test copying a file."""
    # Create a test file
    source_file = temp_test_dir / "source.txt"
    source_content = "Test content"
    source_file.write_text(source_content)
    
    destination_file = temp_test_dir / "destination.txt"
    
    # Test copying the file
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await copy_file(source_file, destination_file)
        
        assert result is True
        assert destination_file.exists()
        assert destination_file.read_text() == source_content
    
    # Test copying to an existing destination (should fail without overwrite)
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with pytest.raises(FileSystemError):
            await copy_file(source_file, destination_file)
    
    # Test copying with overwrite=True
    new_source = temp_test_dir / "new_source.txt"
    new_content = "New content"
    new_source.write_text(new_content)
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_file", new=AsyncMock()):
            result = await copy_file(new_source, destination_file, overwrite=True)
            
            assert result is True
            assert destination_file.read_text() == new_content
    
    # Test dry run (should not copy the file)
    dry_run_dest = temp_test_dir / "dry_run_dest.txt"
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await copy_file(source_file, dry_run_dest, dry_run=True)
        
        assert result is True
        assert not dry_run_dest.exists()


@pytest.mark.asyncio
async def test_move_file(temp_test_dir):
    """Test moving a file."""
    # Create a test file
    source_file = temp_test_dir / "source.txt"
    source_content = "Test content"
    source_file.write_text(source_content)
    
    destination_file = temp_test_dir / "destination.txt"
    
    # Test moving the file
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_file", new=AsyncMock()):
            result = await move_file(source_file, destination_file)
            
            assert result is True
            assert not source_file.exists()
            assert destination_file.exists()
            assert destination_file.read_text() == source_content
    
    # Test moving to an existing destination (should fail without overwrite)
    source_file.write_text(source_content)  # Recreate the source file
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with pytest.raises(FileSystemError):
            await move_file(source_file, destination_file)
    
    # Test moving with overwrite=True
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        with patch("angela.execution.filesystem._backup_file", new=AsyncMock()):
            result = await move_file(source_file, destination_file, overwrite=True)
            
            assert result is True
            assert not source_file.exists()
            assert destination_file.exists()
    
    # Test dry run (should not move the file)
    source_file.write_text(source_content)  # Recreate the source file
    dry_run_dest = temp_test_dir / "dry_run_dest.txt"
    
    with patch("angela.safety.check_operation_safety", new=AsyncMock(return_value=True)):
        result = await move_file(source_file, dry_run_dest, dry_run=True)
        
        assert result is True
        assert source_file.exists()
        assert not dry_run_dest.exists()
