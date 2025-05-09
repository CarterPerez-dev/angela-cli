# tests/test_basic.py

import pytest
import asyncio
from pathlib import Path

async def test_simple_command(mock_terminal, mock_gemini_api, mock_execution_engine, mock_safety_check):
    """Test a simple command execution."""
    from angela.orchestrator import orchestrator
    
    # Set up the expected response
    mock_gemini_api.generate_content.return_value.text = '{"command": "ls -la"}'
    
    # Process the request
    await orchestrator.process_request("list all files", mock_terminal)
    
    # Verify the API was called with the correct prompt
    assert mock_gemini_api.generate_content.called
    
    # Verify the execution engine was called
    mock_execution_engine.execute_command.assert_called_once_with("ls -la")
    
    # Verify the expected output in the terminal
    assert mock_terminal.contains_output("Command executed successfully")

async def test_file_operation(python_project, mock_terminal, mock_gemini_api, mock_safety_check):
    """Test a file operation request."""
    from angela.orchestrator import orchestrator
    
    # Set up the expected response for file creation
    mock_gemini_api.generate_content.return_value.text = '{"file_operation": {"action": "create", "path": "test_file.txt", "content": "Test content"}}'
    
    # Process the request
    await orchestrator.process_request("create a file called test_file.txt with content 'Test content'", mock_terminal)
    
    # Verify the file was created
    created_file = Path(python_project) / "test_file.txt"
    assert created_file.exists()
    assert created_file.read_text() == "Test content"
    
    # Verify the terminal showed success
    assert mock_terminal.contains_output("created successfully")
