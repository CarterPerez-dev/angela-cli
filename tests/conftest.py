# tests/conftest.py
"""
Common test fixtures for Angela CLI.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from angela.config import AppConfig, ApiConfig, UserConfig


class MockTerminal:
    """Simulates terminal input/output for testing."""
    def __init__(self):
        self.input_queue = []
        self.output_history = []
        
    def add_input(self, *inputs):
        """Add inputs to be returned in sequence."""
        self.input_queue.extend(inputs)
        
    def read_input(self, prompt=None):
        """Simulate user input."""
        if prompt:
            self.output_history.append(prompt)
        if not self.input_queue:
            return ""
        return self.input_queue.pop(0)
    
    def write_output(self, text):
        """Simulate terminal output."""
        self.output_history.append(str(text))
        
    def clear_output(self):
        self.output_history = []
        
    @property
    def full_output(self):
        """Get all output as a single string."""
        return "\n".join(self.output_history)
    
    def contains_output(self, text):
        """Check if output contains specific text."""
        return any(text in out for out in self.output_history)


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for project testing."""
    temp_dir = tempfile.mkdtemp()
    old_dir = os.getcwd()
    os.chdir(temp_dir)
    yield Path(temp_dir)
    os.chdir(old_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def python_project(temp_project_dir):
    """Create a simple Python project structure."""
    # Create Python project files
    (temp_project_dir / "requirements.txt").touch()
    (temp_project_dir / "setup.py").touch()
    
    # Create src directory with sample code
    src_dir = temp_project_dir / "myproject"
    src_dir.mkdir()
    (src_dir / "__init__.py").touch()
    (src_dir / "main.py").write_text(
        "def main():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    main()"
    )
    
    # Create tests directory
    tests_dir = temp_project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        "def test_main():\n    assert True"
    )
    
    # Initialize git
    os.system("git init >/dev/null 2>&1")
    os.system("git config user.email 'test@example.com' >/dev/null 2>&1")
    os.system("git config user.name 'Test User' >/dev/null 2>&1")
    
    return temp_project_dir

@pytest.fixture
def node_project(temp_project_dir):
    """Create a simple Node.js project structure."""
    # Create a package.json file
    (temp_project_dir / "package.json").write_text(
        '{\n  "name": "test-project",\n  "version": "1.0.0",\n  "main": "index.js"\n}'
    )
    
    # Create index.js
    (temp_project_dir / "index.js").write_text("console.log('Hello, world!');")
    
    # Create node_modules directory
    (temp_project_dir / "node_modules").mkdir()
    
    # Initialize git
    os.system("git init >/dev/null 2>&1")
    
    return temp_project_dir
        
        
@pytest.fixture
def mock_terminal():
    """Returns a MockTerminal instance."""
    return MockTerminal()

@pytest.fixture
def mock_gemini_api():
    """Mock the Gemini API client."""
    with patch("angela.ai.client.gemini_client") as mock_client:
        mock_response = MagicMock()
        mock_response.text = '{"command": "ls -la"}'
        mock_client.generate_content.return_value = mock_response
        yield mock_client

@pytest.fixture
def mock_execution_engine():
    """Mock the execution engine."""
    with patch("angela.execution.engine.execution_engine") as mock_engine:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"Command executed successfully"
        mock_result.stderr = b""
        
        async def mock_execute(*args, **kwargs):
            return mock_result
            
        mock_engine.execute_command.side_effect = mock_execute
        yield mock_engine

@pytest.fixture
def mock_safety_check():
    """Mock the safety checker to always approve commands."""
    with patch("angela.safety.check_command_safety") as mock_safety:
        async def mock_check(*args, **kwargs):
            return True
            
        mock_safety.side_effect = mock_check
        yield mock_safety        
        
        
