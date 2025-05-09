# tests/test_multi_step.py

import pytest
import os
import asyncio
from pathlib import Path

async def test_git_workflow(python_project, mock_terminal, mock_gemini_api, mock_safety_check):
    """Test a multi-step git workflow."""
    from angela.orchestrator import orchestrator
    from angela.intent.enhanced_task_planner import enhanced_task_planner
    
    # Configure multi-step plan response
    mock_gemini_api.generate_content.return_value.text = '''
    {
        "plan": {
            "steps": [
                {"type": "COMMAND", "command": "git branch feature/test"},
                {"type": "COMMAND", "command": "git checkout feature/test"},
                {"type": "FILE_OPERATION", "action": "create", "path": "feature.py", "content": "# New feature"},
                {"type": "COMMAND", "command": "git add feature.py"},
                {"type": "COMMAND", "command": "git commit -m 'Add new feature file'"}
            ]
        }
    }
    '''
    
    # Process the request
    await orchestrator.process_request(
        "create a feature branch, add a feature.py file, and commit it", 
        mock_terminal
    )
    
    # Verify the branch was created and file exists
    branch_output = os.popen("git branch").read()
    assert "feature/test" in branch_output
    
    feature_file = Path(python_project) / "feature.py"
    assert feature_file.exists()
    assert feature_file.read_text() == "# New feature"
    
    # Verify commit was made
    log_output = os.popen("git log -1").read()
    assert "Add new feature file" in log_output

async def test_error_recovery(python_project, mock_terminal, mock_gemini_api, mock_safety_check):
    """Test recovery from an error in a multi-step operation."""
    from angela.orchestrator import orchestrator
    from angela.execution.error_recovery import ErrorRecoveryManager
    
    # Configure a plan with an error
    mock_gemini_api.generate_content.side_effect = [
        # Initial plan
        MagicMock(text='''
        {
            "plan": {
                "steps": [
                    {"type": "COMMAND", "command": "mkdir test_dir"},
                    {"type": "COMMAND", "command": "invalid_command_that_will_fail"},
                    {"type": "COMMAND", "command": "echo 'Final step'"}
                ]
            }
        }
        '''),
        # Recovery suggestion
        MagicMock(text='''
        {
            "recovery": {
                "strategy": "MODIFY",
                "modified_command": "echo 'This is a valid replacement command'"
            }
        }
        ''')
    ]
    
    # Add user input to select recovery option
    mock_terminal.add_input("y")  # Yes, attempt recovery
    
    # Process the request with error recovery
    await orchestrator.process_request(
        "create a directory and run some commands",
        mock_terminal
    )
    
    # Verify the directory was created
    test_dir = Path(python_project) / "test_dir"
    assert test_dir.exists()
    
    # Verify the recovery was attempted
    assert mock_terminal.contains_output("Recovery strategy: MODIFY")
    assert mock_terminal.contains_output("This is a valid replacement command")
    
    # Verify execution continued after recovery
    assert mock_terminal.contains_output("Final step")
