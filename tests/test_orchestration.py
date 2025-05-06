# tests/test_orchestration.py
"""Tests for the orchestrator service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from angela.ai.parser import CommandSuggestion
from angela.orchestrator import Orchestrator


@pytest.fixture
def orchestrator():
    """Create an orchestrator instance for testing."""
    return Orchestrator()


@pytest.mark.asyncio
async def test_process_request_suggestion_only(orchestrator):
    """Test processing a request without execution."""
    # Mock the dependencies
    with patch("angela.orchestrator.context_manager") as mock_context, \
         patch.object(orchestrator, "_get_ai_suggestion", new=AsyncMock()) as mock_suggestion:
        
        # Configure the mocks
        mock_context.get_context_dict.return_value = {"cwd": "/test"}
        mock_suggestion.return_value = CommandSuggestion(
            intent="file_search",
            command="find . -name '*.py'",
            explanation="Search for Python files"
        )
        
        # Process a request
        result = await orchestrator.process_request("Find Python files", execute=False)
        
        # Check that the suggestion is included in the result
        assert result["request"] == "Find Python files"
        assert result["suggestion"].command == "find . -name '*.py'"
        assert "execution" not in result


@pytest.mark.asyncio
async def test_process_request_with_execution(orchestrator):
    """Test processing a request with execution."""
    # Mock the dependencies
    with patch("angela.orchestrator.context_manager") as mock_context, \
         patch.object(orchestrator, "_get_ai_suggestion", new=AsyncMock()) as mock_suggestion, \
         patch("angela.orchestrator.execution_engine.execute_command", new=AsyncMock()) as mock_execute:
        
        # Configure the mocks
        mock_context.get_context_dict.return_value = {"cwd": "/test"}
        mock_suggestion.return_value = CommandSuggestion(
            intent="file_search",
            command="find . -name '*.py'",
            explanation="Search for Python files"
        )
        mock_execute.return_value = ("file1.py\nfile2.py", "", 0)
        
        # Process a request with execution
        result = await orchestrator.process_request("Find Python files", execute=True)
        
        # Check that the execution results are included
        assert "execution" in result
        assert result["execution"]["stdout"] == "file1.py\nfile2.py"
        assert result["execution"]["success"] is True


@pytest.mark.asyncio
async def test_get_ai_suggestion(orchestrator):
    """Test getting a suggestion from the AI service."""
    # Mock the dependencies
    with patch("angela.orchestrator.build_prompt") as mock_build_prompt, \
         patch("angela.orchestrator.gemini_client.generate_text", new=AsyncMock()) as mock_generate, \
         patch("angela.orchestrator.parse_ai_response") as mock_parse:
        
        # Configure the mocks
        mock_build_prompt.return_value = "test prompt"
        mock_generate.return_value = MagicMock(text="AI response")
        mock_parse.return_value = CommandSuggestion(
            intent="file_search",
            command="find . -name '*.py'",
            explanation="Search for Python files"
        )
        
        # Get a suggestion
        context = {"cwd": "/test"}
        suggestion = await orchestrator._get_ai_suggestion("Find Python files", context)
        
        # Check that the dependencies were called correctly
        mock_build_prompt.assert_called_once_with("Find Python files", context)
        assert mock_generate.call_count == 1
        mock_parse.assert_called_once_with("AI response")
        
        # Check the result
        assert suggestion.command == "find . -name '*.py'"


@pytest.mark.asyncio
async def test_process_request_error_handling(orchestrator):
    """Test error handling in process_request."""
    # Mock the dependencies
    with patch("angela.orchestrator.context_manager") as mock_context, \
         patch.object(orchestrator, "_get_ai_suggestion", new=AsyncMock()) as mock_suggestion:
        
        # Configure the mocks
        mock_context.get_context_dict.return_value = {"cwd": "/test"}
        mock_suggestion.side_effect = Exception("Test error")
        
        # Process a request that will cause an error
        result = await orchestrator.process_request("Find Python files")
        
        # Check that the error is handled gracefully
        assert "error" in result
        assert "Test error" in result["error"]
        assert result["response"] == "Echo: Find Python files"  # Fallback behavior
