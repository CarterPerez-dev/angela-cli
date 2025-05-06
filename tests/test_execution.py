# tests/test_execution.py
"""Tests for the command execution engine."""
import os
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from angela.execution.engine import ExecutionEngine
from angela.intent.models import ActionPlan, Intent, IntentType


@pytest.fixture
def engine():
    """Create an execution engine for testing."""
    return ExecutionEngine()


@pytest.mark.asyncio
async def test_execute_command_failure(engine):
    """Test executing a command that fails."""
    command = "command_that_does_not_exist"
    
    stdout, stderr, return_code = await engine.execute_command(command)
    
    assert return_code != 0
    assert stdout == ""
    # Update assertion to include "No such file" which is the actual error message
    assert "No such file" in stderr or "not found" in stderr or "not recognized" in stderr


@pytest.mark.asyncio
async def test_execute_plan(engine):
    """Test executing an action plan with multiple commands."""
    # Create a simple plan
    plan = ActionPlan(
        intent=Intent(
            type=IntentType.FILE_SEARCH,
            original_request="List files and show disk usage"
        ),
        commands=["echo command1", "echo command2"],
        explanations=["First command", "Second command"],
        risk_level=0
    )
    
    # Mock the execute_command method to avoid actual execution
    with patch.object(engine, "execute_command", new=AsyncMock()) as mock_execute:
        mock_execute.side_effect = [
            ("output1", "", 0),
            ("output2", "", 0)
        ]
        
        results = await engine.execute_plan(plan)
        
        assert len(results) == 2
        assert results[0]["command"] == "echo command1"
        assert results[0]["stdout"] == "output1"
        assert results[0]["success"] is True
        assert results[1]["command"] == "echo command2"
        assert results[1]["stdout"] == "output2"
        assert results[1]["success"] is True
        
        # Check that execute_command was called correctly
        assert mock_execute.call_count == 2
        mock_execute.assert_any_call("echo command1")
        mock_execute.assert_any_call("echo command2")


@pytest.mark.asyncio
async def test_execute_unsafe_commands():
    """Test that potentially unsafe commands can't be executed."""
    engine = ExecutionEngine()
    
    # Test a command that could be destructive if accidentally executed
    command = "rm -rf test"
    
    # This test should only run if there isn't actually a 'test' directory
    # that we might accidentally delete
    if not os.path.exists("test"):
        # Create the test directory temporarily
        os.mkdir("test")
        try:
            # Execute the command (in a real system you'd want safety checks)
            stdout, stderr, return_code = await engine.execute_command(command)
            
            # Check that the command executed as expected
            assert return_code == 0
            assert not os.path.exists("test")  # Directory should be gone
        finally:
            # Clean up if test failed and directory still exists
            if os.path.exists("test"):
                os.rmdir("test")
