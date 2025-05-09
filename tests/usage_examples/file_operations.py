# tests/usage_examples/file_operations.py
import pytest
from unittest.mock import patch, MagicMock
from angela.orchestrator import orchestrator
from tests.conftest import MockTerminal

@pytest.mark.asyncio
async def test_file_listing():
    """EXAMPLE: List files in current directory
    DESCRIPTION: Use Angela to list all files in the current directory with details.
    COMMAND: list all files in current directory with size and date
    RESULT:
    Executing command: ls -la
    total 40
    drwxr-xr-x  5 user  staff   160 May  9 10:15 .
    drwxr-xr-x  3 user  staff    96 May  9 10:12 ..
    -rw-r--r--  1 user  staff  1240 May  9 10:15 README.md
    -rw-r--r--  1 user  staff   432 May  9 10:15 setup.py
    drwxr-xr-x  8 user  staff   256 May  9 10:15 angela
    """
    # The actual test that verifies this example works
    with patch("angela.ai.client.gemini_client") as mock_client:
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.text = '{"command": "ls -la"}'
        mock_client.generate_text.return_value = mock_response
        
        # Create mock terminal
        terminal = MockTerminal()
        
        # Set expected terminal output
        terminal.add_output("Executing command: ls -la")
        terminal.add_output("total 40")
        terminal.add_output("drwxr-xr-x  5 user  staff   160 May  9 10:15 .")
        # ... more output lines
        
        # Process the request
        result = await orchestrator.process_request(
            "list all files in current directory with size and date",
            execute=True
        )
        
        # Verify the command matches
        assert result["command"] == "ls -la"
        
        # Other assertions to verify correct behavior
