# tests/test_enhanced_rollback.py
"""
Tests for the enhanced rollback system.
"""
import os
import pytest
import tempfile
import asyncio
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

from angela.execution.rollback import (
    rollback_manager, OperationRecord, Transaction,
    OP_FILE_SYSTEM, OP_CONTENT, OP_COMMAND, OP_PLAN
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def test_file(temp_dir):
    """Create a test file with content."""
    file_path = temp_dir / "test_file.txt"
    with open(file_path, 'w') as f:
        f.write("Original content")
    return file_path

@pytest.fixture
def test_dir(temp_dir):
    """Create a test directory with files."""
    dir_path = temp_dir / "test_dir"
    dir_path.mkdir()
    
    # Add some files
    (dir_path / "file1.txt").write_text("File 1 content")
    (dir_path / "file2.txt").write_text("File 2 content")
    
    return dir_path

@pytest.mark.asyncio
async def test_transaction_management():
    """Test starting and ending transactions."""
    # Start a transaction
    transaction_id = await rollback_manager.start_transaction("Test transaction")
    assert transaction_id is not None
    
    # End the transaction
    result = await rollback_manager.end_transaction(transaction_id, "completed")
    assert result is True
    
    # Try to end a non-existent transaction
    result = await rollback_manager.end_transaction("non-existent-id", "completed")
    assert result is False

@pytest.mark.asyncio
async def test_record_file_operation(test_file):
    """Test recording a file operation."""
    # Start a transaction
    transaction_id = await rollback_manager.start_transaction("Test file operation")
    
    # Record a file operation
    operation_id = await rollback_manager.record_file_operation(
        operation_type="create_file",
        params={"path": str(test_file)},
        backup_path=None,
        transaction_id=transaction_id
    )
    
    assert operation_id is not None
    
    # End the transaction
    await rollback_manager.end_transaction(transaction_id, "completed")
    
    # Get recent operations
    operations = await rollback_manager.get_recent_operations()
    
    # Find our operation
    found = False
    for op in operations:
        if op["id"] == operation_id:
            found = True
            assert op["operation_type"] == OP_FILE_SYSTEM
            assert "create_file" in op["description"]
            break
    
    assert found, "Operation not found in recent operations"

@pytest.mark.asyncio
async def test_record_content_manipulation(test_file):
    """Test recording a content manipulation."""
    # Start a transaction
    transaction_id = await rollback_manager.start_transaction("Test content manipulation")
    
    # Original and modified content
    original_content = "Original content"
    modified_content = "Modified content"
    
    # Record a content manipulation
    operation_id = await rollback_manager.record_content_manipulation(
        file_path=test_file,
        original_content=original_content,
        modified_content=modified_content,
        instruction="Change the content",
        transaction_id=transaction_id
    )
    
    assert operation_id is not None
    
    # End the transaction
    await rollback_manager.end_transaction(transaction_id, "completed")
    
    # Get recent operations
    operations = await rollback_manager.get_recent_operations()
    
    # Find our operation
    found = False
    for op in operations:
        if op["id"] == operation_id:
            found = True
            assert op["operation_type"] == OP_CONTENT
            assert "Modified content" in op["description"]
            break
    
    assert found, "Operation not found in recent operations"

@pytest.mark.asyncio
async def test_record_command_execution():
    """Test recording a command execution."""
    # Start a transaction
    transaction_id = await rollback_manager.start_transaction("Test command execution")
    
    # Record a command execution
    operation_id = await rollback_manager.record_command_execution(
        command="echo 'Hello, world!'",
        return_code=0,
        stdout="Hello, world!",
        stderr="",
        transaction_id=transaction_id
    )
    
    assert operation_id is not None
    
    # End the transaction
    await rollback_manager.end_transaction(transaction_id, "completed")
    
    # Get recent operations
    operations = await rollback_manager.get_recent_operations()
    
    # Find our operation
    found = False
    for op in operations:
        if op["id"] == operation_id:
            found = True
            assert op["operation_type"] == OP_COMMAND
            assert "echo" in op["description"]
            break
    
    assert found, "Operation not found in recent operations"

@pytest.mark.asyncio
async def test_rollback_file_operation(test_file):
    """Test rolling back a file operation."""
    # Create a backup of the file
    backup_path = await rollback_manager.create_backup_file(test_file)
    assert backup_path is not None
    
    # Record a file operation
    operation_id = await rollback_manager.record_file_operation(
        operation_type="write_file",
        params={"path": str(test_file)},
        backup_path=backup_path
    )
    
    assert operation_id is not None
    
    # Modify the file
    with open(test_file, 'w') as f:
        f.write("Changed content")
    
    # Verify the content changed
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == "Changed content"
    
    # Roll back the operation
    result = await rollback_manager.rollback_operation(operation_id)
    assert result is True
    
    # Verify the content was restored
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == "Original content"

@pytest.mark.asyncio
async def test_rollback_content_manipulation(test_file):
    """Test rolling back a content manipulation."""
    # Original and modified content
    original_content = "Original content"
    modified_content = "Modified content"
    
    # Update the file with modified content
    with open(test_file, 'w') as f:
        f.write(modified_content)
    
    # Record a content manipulation
    operation_id = await rollback_manager.record_content_manipulation(
        file_path=test_file,
        original_content=original_content,
        modified_content=modified_content,
        instruction="Change the content"
    )
    
    assert operation_id is not None
    
    # Verify the content changed
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == modified_content
    
    # Roll back the operation
    result = await rollback_manager.rollback_operation(operation_id)
    assert result is True
    
    # Verify the content was restored
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == original_content

@pytest.mark.asyncio
async def test_rollback_command_execution():
    """Test rolling back a command execution."""
    # Mock the execution_engine
    with patch('angela.execution.engine.execution_engine.execute_command') as mock_execute:
        # Set up the mock to return success
        mock_execute.return_value = ("", "", 0)
        
        # Record a command execution
        operation_id = await rollback_manager.record_command_execution(
            command="mkdir test_dir",
            return_code=0,
            stdout="",
            stderr="",
            undo_info={"compensating_action": "rmdir test_dir"}
        )
        
        assert operation_id is not None
        
        # Roll back the operation
        result = await rollback_manager.rollback_operation(operation_id)
        assert result is True
        
        # Verify that the compensating action was executed
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[0] == "rmdir test_dir"
        assert kwargs["check_safety"] is False

@pytest.mark.asyncio
async def test_rollback_transaction(test_file):
    """Test rolling back an entire transaction."""
    # Start a transaction
    transaction_id = await rollback_manager.start_transaction("Test transaction rollback")
    
    # Create a backup of the file
    backup_path = await rollback_manager.create_backup_file(test_file)
    
    # Record multiple operations
    file_op_id = await rollback_manager.record_file_operation(
        operation_type="write_file",
        params={"path": str(test_file)},
        backup_path=backup_path,
        transaction_id=transaction_id
    )
    
    content_op_id = await rollback_manager.record_content_manipulation(
        file_path=test_file,
        original_content="Original content",
        modified_content="Modified content",
        instruction="Change the content",
        transaction_id=transaction_id
    )
    
    # End the transaction
    await rollback_manager.end_transaction(transaction_id, "completed")
    
    # Modify the file
    with open(test_file, 'w') as f:
        f.write("Modified content")
    
    # Verify the content changed
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == "Modified content"
    
    # Roll back the transaction
    result = await rollback_manager.rollback_transaction(transaction_id)
    assert result["success"] is True
    assert result["rolled_back"] > 0
    assert result["failed"] == 0
    
    # Verify the content was restored
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == "Original content"

@pytest.mark.asyncio
async def test_identify_compensating_action():
    """Test identifying compensating actions for commands."""
    # Test with a git add command
    compensating_action = await rollback_manager._identify_compensating_action(
        command="git add file.txt",
        stdout="",
        stderr=""
    )
    assert compensating_action == "git reset file.txt"
    
    # Test with an npm install command
    compensating_action = await rollback_manager._identify_compensating_action(
        command="npm install express",
        stdout="",
        stderr=""
    )
    assert compensating_action == "npm uninstall express"
    
    # Test with a git commit command
    compensating_action = await rollback_manager._identify_compensating_action(
        command="git commit -m 'Initial commit'",
        stdout="",
        stderr=""
    )
    assert compensating_action == "git reset --soft HEAD~1"
    
    # Test with an unknown command
    compensating_action = await rollback_manager._identify_compensating_action(
        command="some_unknown_command arg1 arg2",
        stdout="",
        stderr=""
    )
    assert compensating_action is None

@pytest.mark.asyncio
async def test_get_recent_transactions():
    """Test getting recent transactions."""
    # Start and end a few transactions
    transaction_ids = []
    for i in range(3):
        transaction_id = await rollback_manager.start_transaction(f"Test transaction {i}")
        transaction_ids.append(transaction_id)
        await rollback_manager.end_transaction(transaction_id, "completed")
    
    # Get recent transactions
    transactions = await rollback_manager.get_recent_transactions()
    
    # Verify transactions are returned
    assert len(transactions) > 0
    
    # Verify our transactions are included
    for transaction_id in transaction_ids:
        found = False
        for transaction in transactions:
            if transaction["id"] == transaction_id:
                found = True
                break
        assert found, f"Transaction {transaction_id} not found in recent transactions"

@pytest.mark.asyncio
async def test_backup_functions(test_file, test_dir):
    """Test backup functions."""
    # Test backup file
    backup_file = await rollback_manager.create_backup_file(test_file)
    assert backup_file is not None
    assert backup_file.exists()
    
    # Verify backup content
    with open(backup_file, 'r') as f:
        content = f.read()
    assert content == "Original content"
    
    # Test backup directory
    backup_dir = await rollback_manager.create_backup_directory(test_dir)
    assert backup_dir is not None
    assert backup_dir.exists()
    
    # Verify backup files
    assert (backup_dir / "file1.txt").exists()
    assert (backup_dir / "file2.txt").exists()
    
    # Verify backup content
    with open(backup_dir / "file1.txt", 'r') as f:
        content = f.read()
    assert content == "File 1 content"
