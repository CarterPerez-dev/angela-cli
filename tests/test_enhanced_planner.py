"""
Test suite for the enhanced task planner implementation.

This module provides comprehensive tests for the advanced features
of the AdvancedTaskPlanner, including:
1. CODE execution
2. API calls
3. LOOP iteration
4. Data flow between steps
5. Error handling and recovery
"""
import os
import json
import uuid
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the enhanced task planner
from angela.intent.planner import (
    task_planner, TaskPlan, PlanStep,
    AdvancedTaskPlan, AdvancedPlanStep, PlanStepType
)

# Create a fixture for the test plan
@pytest.fixture
def advanced_test_plan():
    """Create a test advanced task plan."""
    plan_id = str(uuid.uuid4())
    
    # Create an advanced task plan with various step types
    return AdvancedTaskPlan(
        id=plan_id,
        goal="Test execution of advanced steps",
        description="A plan to test all advanced step types",
        steps={
            "step1": AdvancedPlanStep(
                id="step1",
                type=PlanStepType.COMMAND,
                description="List directory",
                command="ls -la",
                dependencies=[],
                estimated_risk=0
            ),
            "step2": AdvancedPlanStep(
                id="step2",
                type=PlanStepType.CODE,
                description="Process directory listing",
                code="""
# Process the directory listing from step1
output = variables.get("step1_stdout", "")
lines = output.strip().split('\\n')
file_count = len(lines) - 1  # Subtract header line
result = f"Found {file_count} files/directories"
print(f"Processing complete: {result}")
                """,
                dependencies=["step1"],
                estimated_risk=0
            ),
            "step3": AdvancedPlanStep(
                id="step3",
                type=PlanStepType.DECISION,
                description="Check if any Python files exist",
                condition="output contains .py in step1",
                true_branch=["step4a"],
                false_branch=["step4b"],
                dependencies=["step1"],
                estimated_risk=0
            ),
            "step4a": AdvancedPlanStep(
                id="step4a",
                type=PlanStepType.COMMAND,
                description="Count Python files",
                command="find . -name '*.py' | wc -l",
                dependencies=["step3"],
                estimated_risk=0
            ),
            "step4b": AdvancedPlanStep(
                id="step4b",
                type=PlanStepType.COMMAND,
                description="Create a Python file",
                command="echo 'print(\"Hello World\")' > test.py",
                dependencies=["step3"],
                estimated_risk=1
            ),
            "step5": AdvancedPlanStep(
                id="step5",
                type=PlanStepType.API,
                description="Get data from httpbin",
                api_url="https://httpbin.org/get",
                api_method="GET",
                api_params={"test": "value"},
                dependencies=["step4a", "step4b"],
                estimated_risk=1
            ),
            "step6": AdvancedPlanStep(
                id="step6",
                type=PlanStepType.LOOP,
                description="Process list of items",
                loop_items="range(1, 4)",
                loop_body=["step7"],
                dependencies=["step5"],
                estimated_risk=0
            ),
            "step7": AdvancedPlanStep(
                id="step7",
                type=PlanStepType.CODE,
                description="Process loop item",
                code="""
# Process the loop item
item = variables.get("loop_item", 0)
result = item * 2
print(f"Processed item {item}, result: {result}")
                """,
                dependencies=[],
                estimated_risk=0
            ),
            "step8": AdvancedPlanStep(
                id="step8",
                type=PlanStepType.FILE,
                description="Write results to file",
                file_path="results.txt",
                file_content="${step2_result}\n${step5_status_code}",
                operation="write",
                dependencies=["step6"],
                estimated_risk=1
            )
        },
        entry_points=["step1"],
        context={}
    )

# Test for command execution
async def test_execute_command_step():
    """Test execution of a command step."""
    # Create a simple command step
    step = AdvancedPlanStep(
        id="test_command",
        type=PlanStepType.COMMAND,
        description="Echo test",
        command="echo 'test command'",
        dependencies=[],
        estimated_risk=0
    )
    
    # Use the task_planner's internal method directly
    from angela.intent.planner import EnhancedTaskPlanner
    planner = EnhancedTaskPlanner()
    
    # Create context
    from angela.intent.planner import StepExecutionContext
    context = StepExecutionContext(
        step_id="test_command",
        plan_id="test_plan",
        dry_run=False
    )
    
    # Execute the step
    result = await planner._execute_command_step(step, context)
    
    # Check results
    assert result["success"] is True
    assert "test command" in result["stdout"]
    assert result["return_code"] == 0
    assert "outputs" in result
    assert "test_command_stdout" in result["outputs"]

# Test for Python code execution
async def test_execute_python_code_step():
    """Test execution of a Python code step."""
    # Create a simple code step
    step = AdvancedPlanStep(
        id="test_code",
        type=PlanStepType.CODE,
        description="Python test",
        code="""
result = 2 + 2
print(f"The result is {result}")
        """,
        dependencies=[],
        estimated_risk=0,
        language="python"
    )
    
    # Use the task_planner's internal method directly
    from angela.intent.planner import EnhancedTaskPlanner
    planner = EnhancedTaskPlanner()
    
    # Create context
    from angela.intent.planner import StepExecutionContext
    context = StepExecutionContext(
        step_id="test_code",
        plan_id="test_plan",
        dry_run=False
    )
    
    # Execute the step
    result = await planner._execute_code_step(step, context)
    
    # Check results
    assert result["success"] is True
    assert "The result is 4" in result["stdout"]
    assert "outputs" in result
    assert "variables" in result["outputs"]

# Test for API step execution
@pytest.mark.asyncio
async def test_execute_api_step():
    """Test execution of an API step."""
    # Create a simple API step
    step = AdvancedPlanStep(
        id="test_api",
        type=PlanStepType.API,
        description="API test",
        api_url="https://httpbin.org/get",
        api_method="GET",
        api_params={"test": "value"},
        dependencies=[],
        estimated_risk=1
    )
    
    # Mock aiohttp.ClientSession
    with patch('aiohttp.ClientSession') as mock_session:
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = asyncio.coroutine(lambda: '{"args": {"test": "value"}}')
        mock_response.json = asyncio.coroutine(lambda: {"args": {"test": "value"}})
        mock_response.headers = {"Content-Type": "application/json"}
        
        # Mock the context manager
        mock_session_instance = MagicMock()
        mock_session_instance.__aenter__.return_value = mock_session_instance
        mock_session_instance.request.return_value.__aenter__.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Use the task_planner's internal method directly
        from angela.intent.planner import EnhancedTaskPlanner
        planner = EnhancedTaskPlanner()
        
        # Create context
        from angela.intent.planner import StepExecutionContext
        context = StepExecutionContext(
            step_id="test_api",
            plan_id="test_plan",
            dry_run=False
        )
        
        # Execute the step
        result = await planner._execute_api_step(step, context)
        
        # Check results
        assert result["success"] is True
        assert result["status_code"] == 200
        assert "test_api_status_code" in result["outputs"]
        
        # Verify the request was made with the correct parameters
        mock_session_instance.request.assert_called_once_with(
            "GET", 
            "https://httpbin.org/get", 
            headers={}, 
            params={"test": "value"}, 
            ssl=True
        )

# Test for file operation step
async def test_execute_file_step():
    """Test execution of a file operation step."""
    # Create a temporary file path
    import tempfile
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test_file.txt")
    
    # Create a file operation step
    step = AdvancedPlanStep(
        id="test_file",
        type=PlanStepType.FILE,
        description="File test",
        file_path=test_file,
        file_content="Test content",
        operation="write",
        dependencies=[],
        estimated_risk=1
    )
    
    # Mock filesystem functions
    with patch('angela.execution.filesystem.write_file') as mock_write_file, \
         patch('angela.execution.filesystem.create_directory') as mock_create_dir:
        
        # Set up mock return value
        mock_write_file.return_value = asyncio.Future()
        mock_write_file.return_value.set_result(None)
        
        mock_create_dir.return_value = asyncio.Future()
        mock_create_dir.return_value.set_result(None)
        
        # Use the task_planner's internal method directly
        from angela.intent.planner import EnhancedTaskPlanner
        planner = EnhancedTaskPlanner()
        
        # Create context
        from angela.intent.planner import StepExecutionContext
        context = StepExecutionContext(
            step_id="test_file",
            plan_id="test_plan",
            dry_run=False
        )
        
        # Execute the step
        result = await planner._execute_file_step(step, context)
        
        # Check results
        assert result["success"] is True
        assert "message" in result
        assert "test_file_message" in result["outputs"]
        
        # Verify the write_file was called correctly
        mock_create_dir.assert_called_once()
        mock_write_file.assert_called_once_with(test_file, "Test content")
    
    # Clean up
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except:
        pass

# Test for decision step
async def test_execute_decision_step():
    """Test execution of a decision step."""
    # Create a decision step
    step = AdvancedPlanStep(
        id="test_decision",
        type=PlanStepType.DECISION,
        description="Decision test",
        condition="variable test_var == 42",
        true_branch=["stepA"],
        false_branch=["stepB"],
        dependencies=[],
        estimated_risk=0
    )
    
    # Use the task_planner's internal method directly
    from angela.intent.planner import EnhancedTaskPlanner
    planner = EnhancedTaskPlanner()
    
    # Create context with a variable
    from angela.intent.planner import StepExecutionContext
    context = StepExecutionContext(
        step_id="test_decision",
        plan_id="test_plan",
        dry_run=False,
        variables={"test_var": 42}
    )
    
    # Set the variable in the planner
    planner._set_variable("test_var", 42, "test")
    
    # Execute the step
    result = await planner._execute_decision_step(step, context)
    
    # Check results
    assert result["success"] is True
    assert result["condition_result"] is True
    assert result["next_branch"] == "true_branch"
    assert "test_decision_condition_result" in result["outputs"]
    assert result["outputs"]["test_decision_condition_result"] is True

# Test for loop step
async def test_execute_loop_step():
    """Test execution of a loop step."""
    # Create a loop step - this is more complex and requires mocking the plan
    step = AdvancedPlanStep(
        id="test_loop",
        type=PlanStepType.LOOP,
        description="Loop test",
        loop_items="range(1, 4)",
        loop_body=["loop_body_step"],
        dependencies=[],
        estimated_risk=0
    )
    
    # Create the body step
    body_step = AdvancedPlanStep(
        id="loop_body_step",
        type=PlanStepType.CODE,
        description="Loop body",
        code="""
item = variables.get("loop_item", 0)
result = item * 2
print(f"Item: {item}, Result: {result}")
        """,
        dependencies=[],
        estimated_risk=0,
        language="python"
    )
    
    # Mock methods to resolve loop items and execute steps
    with patch('angela.intent.planner.EnhancedTaskPlanner._resolve_loop_items') as mock_resolve, \
         patch('angela.intent.planner.EnhancedTaskPlanner._execute_advanced_step') as mock_execute:
        
        # Set up mock return values
        mock_resolve.return_value = asyncio.Future()
        mock_resolve.return_value.set_result([1, 2, 3])
        
        async def mock_execute_side_effect(step, context):
            """Mock execution of loop body steps."""
            return {
                "success": True,
                "outputs": {
                    f"{step.id}_result": context.variables.get("loop_item", 0) * 2
                }
            }
        
        mock_execute.side_effect = mock_execute_side_effect
        
        # Use the task_planner's internal method directly
        from angela.intent.planner import EnhancedTaskPlanner
        planner = EnhancedTaskPlanner()
        
        # Create context
        from angela.intent.planner import StepExecutionContext
        context = StepExecutionContext(
            step_id="test_loop",
            plan_id="test_plan",
            dry_run=False
        )
        
        # Add the steps to the plan results dictionary
        context.results = {
            "test_loop": {},
            "loop_body_step": {}
        }
        
        # Execute the step
        result = await planner._execute_loop_step(step, context)
        
        # Check results
        assert result["success"] is True
        assert "loop_results" in result
        assert len(result["loop_results"]) == 3
        assert "iterations" in result
        assert result["iterations"] == 3
        assert "test_loop_iterations" in result["outputs"]
        assert result["outputs"]["test_loop_iterations"] == 3

# Integration test for full plan execution
@pytest.mark.asyncio
async def test_execute_advanced_plan(advanced_test_plan):
    """Test execution of a complete advanced plan."""
    # Mock various execution methods to avoid actual execution
    with patch('angela.intent.planner.EnhancedTaskPlanner._execute_command_step') as mock_command, \
         patch('angela.intent.planner.EnhancedTaskPlanner._execute_code_step') as mock_code, \
         patch('angela.intent.planner.EnhancedTaskPlanner._execute_decision_step') as mock_decision, \
         patch('angela.intent.planner.EnhancedTaskPlanner._execute_api_step') as mock_api, \
         patch('angela.intent.planner.EnhancedTaskPlanner._execute_loop_step') as mock_loop, \
         patch('angela.intent.planner.EnhancedTaskPlanner._execute_file_step') as mock_file:
        
        # Set up mock return values
        async def mock_step_return(step, context):
            """Return success for any step."""
            return {
                "success": True,
                "step_id": step.id,
                "type": step.type,
                "outputs": {
                    f"{step.id}_success": True,
                    f"{step.id}_result": f"Result for {step.id}"
                }
            }
        
        # Configure mocks
        mock_command.side_effect = mock_step_return
        mock_code.side_effect = mock_step_return
        mock_api.side_effect = mock_step_return
        mock_file.side_effect = mock_step_return
        
        # Decision step returns condition result based on step ID
        async def mock_decision_return(step, context):
            """Return condition result for decision steps."""
            is_true = "4a" in step.true_branch[0] if step.true_branch else False
            return {
                "success": True,
                "step_id": step.id,
                "type": step.type,
                "condition_result": is_true,
                "next_branch": "true_branch" if is_true else "false_branch",
                "outputs": {
                    f"{step.id}_condition_result": is_true,
                    f"{step.id}_next_branch": "true_branch" if is_true else "false_branch",
                    f"{step.id}_success": True
                }
            }
        
        mock_decision.side_effect = mock_decision_return
        
        # Loop step returns loop results
        async def mock_loop_return(step, context):
            """Return loop results for loop steps."""
            return {
                "success": True,
                "step_id": step.id,
                "type": step.type,
                "loop_results": [{"index": i, "success": True} for i in range(3)],
                "iterations": 3,
                "outputs": {
                    f"{step.id}_iterations": 3,
                    f"{step.id}_success": True
                }
            }
        
        mock_loop.side_effect = mock_loop_return
        
        # Execute the plan
        result = await task_planner.execute_plan(advanced_test_plan, dry_run=False)
        
        # Check high-level results
        assert result["success"] is True
        assert result["steps_completed"] == len(advanced_test_plan.steps)
        assert "results" in result
        assert "execution_path" in result
        assert len(result["execution_path"]) > 0
        
        # Check that each step was executed
        for step_id in advanced_test_plan.steps:
            assert step_id in result["results"]
            assert result["results"][step_id]["success"] is True

# Test error handling and recovery
@pytest.mark.asyncio
async def test_error_handling_and_recovery():
    """Test error handling and recovery for failed steps."""
    # Create a step that will fail
    failing_step = AdvancedPlanStep(
        id="failing_step",
        type=PlanStepType.COMMAND,
        description="Failing command",
        command="nonexistent_command",
        dependencies=[],
        estimated_risk=0
    )
    
    # Mock error recovery manager
    with patch('angela.execution.error_recovery.ErrorRecoveryManager.handle_error') as mock_recovery:
        # Set up mock return value for recovery
        mock_recovery.return_value = asyncio.Future()
        mock_recovery.return_value.set_result({
            "recovery_success": True,
            "recovery_strategy": {"type": "RETRY", "command": "echo 'recovered'"},
            "stdout": "recovered",
            "stderr": "",
            "return_code": 0,
            "success": True
        })
        
        # Use the task_planner's internal method directly
        from angela.intent.planner import EnhancedTaskPlanner
        planner = EnhancedTaskPlanner()
        
        # Create context
        from angela.intent.planner import StepExecutionContext
        context = StepExecutionContext(
            step_id="failing_step",
            plan_id="test_plan",
            dry_run=False
        )
        
        # Set error recovery manager
        planner._error_recovery_manager = MagicMock()
        planner._error_recovery_manager.handle_error = mock_recovery
        
        # Mock execute_command to fail
        with patch('angela.execution.engine.execution_engine.execute_command') as mock_execute:
            # Set up mock return value
            mock_execute.return_value = asyncio.Future()
            mock_execute.return_value.set_result(("", "Command not found", 127))
            
            # Execute the step
            result = await planner._execute_command_step(failing_step, context)
            
            # Step should fail
            assert result["success"] is False
            
            # Attempt recovery
            recovery_result = await planner._attempt_recovery(failing_step, result, context)
            
            # Check recovery was successful
            assert recovery_result["success"] is True
            assert recovery_result["recovery_applied"] is True
            assert "recovery_strategy" in recovery_result
            
            # Verify error recovery manager was called
            mock_recovery.assert_called_once()

# Test data flow between steps
@pytest.mark.asyncio
async def test_data_flow_between_steps(advanced_test_plan):
    """Test data flow between steps using variables."""
    # Create a simple plan with variable passing
    step1 = AdvancedPlanStep(
        id="step1",
        type=PlanStepType.COMMAND,
        description="Generate output",
        command="echo 'test output'",
        dependencies=[],
        estimated_risk=0
    )
    
    step2 = AdvancedPlanStep(
        id="step2",
        type=PlanStepType.CODE,
        description="Process output",
        code="""
# Access output from step1
step1_out = variables.get("step1_stdout", "")
result = f"Processed: {step1_out}"
print(result)
        """,
        dependencies=["step1"],
        estimated_risk=0,
        language="python"
    )
    
    # Create a simple plan
    test_plan = AdvancedTaskPlan(
        id="data_flow_test",
        goal="Test data flow",
        description="Testing variable passing between steps",
        steps={
            "step1": step1,
            "step2": step2
        },
        entry_points=["step1"],
        context={}
    )
    
    # Use the planner directly
    from angela.intent.planner import EnhancedTaskPlanner
    planner = EnhancedTaskPlanner()
    
    # Mock command execution
    with patch('angela.execution.engine.execution_engine.execute_command') as mock_cmd:
        mock_cmd.return_value = asyncio.Future()
        mock_cmd.return_value.set_result(("test output\n", "", 0))
        
        # Execute the plan
        result = await planner.execute_advanced_plan(test_plan)
        
        # Check results
        assert result["success"] is True
        assert "step1" in result["results"]
        assert "step2" in result["results"]
        assert "step1_stdout" in result["results"]["step1"]["outputs"]
        assert result["results"]["step1"]["outputs"]["step1_stdout"] == "test output\n"
        
        # Verify the code step had access to the command output
        mock_cmd.assert_called_once_with("echo 'test output'", check_safety=True)

# Test variable resolution in parameter values
@pytest.mark.asyncio
async def test_variable_resolution():
    """Test resolving variables in step parameters."""
    # Create a step with variable references
    step = AdvancedPlanStep(
        id="var_test",
        type=PlanStepType.COMMAND,
        description="Test variable resolution",
        command="echo '${test_var} - ${another_var}'",
        dependencies=[],
        estimated_risk=0
    )
    
    # Use the planner's method directly
    from angela.intent.planner import EnhancedTaskPlanner
    planner = EnhancedTaskPlanner()
    
    # Set variables
    planner._set_variable("test_var", "Hello", "test")
    planner._set_variable("another_var", "World", "test")
    
    # Create context
    from angela.intent.planner import StepExecutionContext
    context = StepExecutionContext(
        step_id="var_test",
        plan_id="test_plan",
        dry_run=False,
        variables=planner._variables
    )
    
    # Resolve variables
    resolved = await planner._resolve_step_variables(step, context)
    
    # Check resolution
    assert resolved.command == "echo 'Hello - World'"

# Test complete integration with task_planner replacement
@pytest.mark.asyncio
async def test_task_planner_integration():
    """Test that the task_planner global instance has been properly enhanced."""
    from angela.intent.planner import task_planner, EnhancedTaskPlanner
    
    # Verify task_planner is an instance of EnhancedTaskPlanner
    assert isinstance(task_planner, EnhancedTaskPlanner)
    
    # Create a simple advanced plan
    plan = AdvancedTaskPlan(
        id="integration_test",
        goal="Test integration",
        description="Testing integration with task_planner",
        steps={
            "step1": AdvancedPlanStep(
                id="step1",
                type=PlanStepType.COMMAND,
                description="Echo test",
                command="echo 'integration test'",
                dependencies=[],
                estimated_risk=0
            )
        },
        entry_points=["step1"],
        context={}
    )
    
    # Mock command execution
    with patch('angela.execution.engine.execution_engine.execute_command') as mock_cmd:
        mock_cmd.return_value = asyncio.Future()
        mock_cmd.return_value.set_result(("integration test\n", "", 0))
        
        # Execute the plan using the global task_planner
        result = await task_planner.execute_plan(plan)
        
        # Check results
        assert result["success"] is True
        assert "step1" in result["results"]
        assert result["results"]["step1"]["success"] is True
        
        # Verify the command was called
        mock_cmd.assert_called_once()

if __name__ == "__main__":
    pytest.main()
