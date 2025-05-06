"""
Integration tests for Angela CLI.

These tests verify that all components work together correctly.
"""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from angela.orchestrator import orchestrator
from angela.ai.file_integration import extract_file_operation, execute_file_operation
from angela.context import context_manager


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_dir = os.getcwd()
        os.chdir(tmpdir)
        
        # Create a test project structure
        test_dir = Path(tmpdir)
        
        # Create a .git directory to mark as project root
        git_dir = test_dir / ".git"
        git_dir.mkdir()
        
        # Create some test files
        test_file = test_dir / "test.txt"
        test_file.write_text("This is a test file.")
        
        # Create a src directory
        src_dir = test_dir / "src"
        src_dir.mkdir()
        
        # Create a Python file
        py_file = src_dir / "example.py"
        py_file.write_text('print("Hello, world!")')
        
        # Refresh context
        context_manager.refresh_context()
        
        yield test_dir
        
        # Restore original directory
        os.chdir(old_dir)


@pytest.mark.asyncio
async def test_extract_file_operation():
    """Test extracting file operations from commands."""
    # Test mkdir command
    operation = await extract_file_operation("mkdir -p test/nested")
    assert operation is not None
    assert operation[0] == "create_directory"
    assert operation[1]["path"] == "test/nested"
    assert operation[1]["parents"] is True
    
    # Test touch command
    operation = await extract_file_operation("touch newfile.txt")
    assert operation is not None
    assert operation[0] == "create_file"
    assert operation[1]["path"] == "newfile.txt"
    
    # Test rm command
    operation = await extract_file_operation("rm -f oldfile.txt")
    assert operation is not None
    assert operation[0] == "delete_file"
    assert operation[1]["path"] == "oldfile.txt"
    assert operation[1]["force"] is True
    
    # Test echo write command
    operation = await extract_file_operation('echo "Hello, world!" > output.txt')
    assert operation is not None
    assert operation[0] == "write_file"
    assert operation[1]["path"] == "output.txt"
    assert "Hello, world!" in operation[1]["content"]
    
    # Test cat command
    operation = await extract_file_operation("cat input.txt")
    assert operation is not None
    assert operation[0] == "read_file"
    assert operation[1]["path"] == "input.txt"
    
    # Test cp command
    operation = await extract_file_operation("cp source.txt dest.txt")
    assert operation is not None
    assert operation[0] == "copy_file"
    assert operation[1]["source"] == "source.txt"
    assert operation[1]["destination"] == "dest.txt"
    
    # Test mv command
    operation = await extract_file_operation("mv old.txt new.txt")
    assert operation is not None
    assert operation[0] == "move_file"
    assert operation[1]["source"] == "old.txt"
    assert operation[1]["destination"] == "new.txt"
    
    # Test command that is not a file operation
    operation = await extract_file_operation("ls -la")
    assert operation is None


@pytest.mark.asyncio
async def test_file_operation_integration(temp_test_dir):
    """Test integration of file operation extraction and execution."""
    # Test creating a directory
    operation, params = await extract_file_operation("mkdir -p new/nested")
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert (temp_test_dir / "new" / "nested").exists()
    
    # Test creating a file
    operation, params = await extract_file_operation("touch new/nested/test.txt")
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert (temp_test_dir / "new" / "nested" / "test.txt").exists()
    
    # Test writing to a file
    operation, params = await extract_file_operation('echo "Hello, world!" > new/nested/test.txt')
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert (temp_test_dir / "new" / "nested" / "test.txt").read_text() == "Hello, world!"
    
    # Test reading a file
    operation, params = await extract_file_operation("cat new/nested/test.txt")
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert result["content"] == "Hello, world!"
    
    # Test copying a file
    operation, params = await extract_file_operation("cp new/nested/test.txt new/copy.txt")
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert (temp_test_dir / "new" / "copy.txt").exists()
    assert (temp_test_dir / "new" / "copy.txt").read_text() == "Hello, world!"
    
    # Test moving a file
    operation, params = await extract_file_operation("mv new/copy.txt new/moved.txt")
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert not (temp_test_dir / "new" / "copy.txt").exists()
    assert (temp_test_dir / "new" / "moved.txt").exists()
    
    # Test deleting a file
    operation, params = await extract_file_operation("rm new/moved.txt")
    result = await execute_file_operation(operation, params)
    
    assert result["success"] is True
    assert not (temp_test_dir / "new" / "moved.txt").exists()


@pytest.mark.asyncio
async def test_orchestrator_with_file_operations(temp_test_dir):
    """Test orchestrator with file operations."""
    # Mock the AI suggestion to return a file operation command
    with patch("angela.orchestrator._get_ai_suggestion", new=AsyncMock()) as mock_suggestion:
        # Set up the suggestion
        suggestion = MagicMock()
        suggestion.command = "mkdir -p test/orchestrator"
        suggestion.explanation = "Creating a test directory"
        mock_suggestion.return_value = suggestion
        
        # Process the request with execution
        result = await orchestrator.process_request(
            "Create a test directory for the orchestrator",
            execute=True
        )
        
        # Check that the operation was executed
        assert "execution" in result
        assert result["execution"]["success"] is True
        assert (temp_test_dir / "test" / "orchestrator").exists()
        
        # Check for a write operation
        suggestion.command = 'echo "Test content" > test/orchestrator/test.txt'
        
        result = await orchestrator.process_request(
            "Create a test file for the orchestrator",
            execute=True
        )
        
        # Check that the file was created
        assert "execution" in result
        assert result["execution"]["success"] is True
        assert (temp_test_dir / "test" / "orchestrator" / "test.txt").exists()
        assert (temp_test_dir / "test" / "orchestrator" / "test.txt").read_text() == "Test content"
        
        # Test a dry run
        suggestion.command = "rm test/orchestrator/test.txt"
        
        result = await orchestrator.process_request(
            "Delete the test file for the orchestrator",
            dry_run=True
        )
        
        # Check that the file was not deleted (dry run)
        assert "execution" in result
        assert result["execution"]["dry_run"] is True
        assert (temp_test_dir / "test" / "orchestrator" / "test.txt").exists()
