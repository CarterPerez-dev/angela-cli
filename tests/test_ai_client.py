# tests/test_ai_client.py
"""Tests for the Gemini API client."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from angela.ai.client import GeminiClient, GeminiRequest


@pytest.fixture
def mock_genai():
    """Mock the google.generativeai module."""
    with patch("angela.ai.client.genai") as mock:
        mock.GenerativeModel.return_value.generate_content.return_value = MagicMock(
            text="Mocked response",
            candidates=[{"content": "Mocked response"}],
        )
        yield mock


@pytest.fixture
def client(mock_genai):
    """Create a test client with mocked API."""
    return GeminiClient()


@pytest.mark.asyncio
async def test_client_initialization(mock_genai):
    """Test the client initialization."""
    # Set up config manager mock
    with patch("angela.ai.client.config_manager") as mock_config:
        mock_config.config.api.gemini_api_key = "test_key"
        
        # Initialize client
        client = GeminiClient()
        
        # Check if the API was configured correctly
        mock_genai.configure.assert_called_once_with(api_key="test_key")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.5-pro-exp-03-25")


@pytest.mark.asyncio
async def test_generate_text(client):
    """Test the generate_text method."""
    request = GeminiRequest(prompt="Test prompt")
    response = await client.generate_text(request)
    
    assert response.text == "Mocked response"
    assert response.generated_text == "Mocked response"
    assert response.raw_response == {"content": "Mocked response"}


@pytest.mark.asyncio
async def test_error_handling(mock_genai, client):
    """Test error handling in generate_text."""
    # Make the mock raise an exception
    mock_genai.GenerativeModel.return_value.generate_content.side_effect = Exception("API error")
    
    request = GeminiRequest(prompt="Test prompt")
    
    # Check if the exception is propagated correctly
    with pytest.raises(RuntimeError) as excinfo:
        await client.generate_text(request)
    
    assert "Failed to generate text with Gemini API" in str(excinfo.value)


@pytest.mark.asyncio
async def test_empty_response(mock_genai, client):
    """Test handling of empty responses."""
    # Make the mock return an empty response
    mock_genai.GenerativeModel.return_value.generate_content.return_value = MagicMock(
        text="",
        candidates=[{"content": ""}],
    )
    
    request = GeminiRequest(prompt="Test prompt")
    
    # Check if the empty response is handled correctly
    with pytest.raises(ValueError) as excinfo:
        await client.generate_text(request)
    
    assert "Empty response from Gemini API" in str(excinfo.value)
