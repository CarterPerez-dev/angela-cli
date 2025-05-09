# angela/intent/enhanced_task_planner.py

```python
"""
Enhanced execution system for complex task orchestration in Angela CLI.

This module extends the TaskPlanner with robust support for advanced execution steps,
including code execution, API integration, looping constructs, and intelligent
data flow between steps.
"""
import os
import re
import json
import shlex
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union, Callable
from datetime import datetime
import uuid
import logging
import aiohttp
from enum import Enum

from pydantic import BaseModel, Field, ValidationError, validator

from angela.intent.models import ActionPlan, Intent, IntentType
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.context.file_resolver import file_resolver
from angela.utils.logging import get_logger
from angela.execution.error_recovery import ErrorRecoveryManager
from angela.execution.engine import execution_engine
from angela.safety.validator import validate_command_safety
from angela.safety.classifier import classify_command_risk
from angela.core.registry import registry

# Reuse existing models from angela/intent/planner.py
from angela.intent.planner import (
    PlanStep, TaskPlan, PlanStepType, AdvancedPlanStep, AdvancedTaskPlan,
    task_planner
)

logger = get_logger(__name__)


class StepExecutionContext(BaseModel):
    """Context for step execution with data flow capabilities."""
    step_id: str = Field(..., description="ID of the step being executed")
    plan_id: str = Field(..., description="ID of the plan being executed")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables available to the step")
    results: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Results of previously executed steps")
    transaction_id: Optional[str] = Field(None, description="Transaction ID for rollback")
    dry_run: bool = Field(False, description="Whether this is a dry run")
    parent_context: Optional[Dict[str, Any]] = Field(None, description="Parent context (e.g., for loops)")
    execution_path: List[str] = Field(default_factory=list, description="Execution path taken so far")

class DataFlowVariable(BaseModel):
    """Model for a variable in the data flow system."""
    name: str = Field(..., description="Name of the variable")
    value: Any = Field(..., description="Value of the variable")
    source_step: Optional[str] = Field(None, description="ID of the step that set this variable")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the variable was set/updated")

class ExecutionResult(BaseModel):
    """Enhanced model for execution results with data flow information."""
    step_id: str = Field(..., description="ID of the executed step")
    type: PlanStepType = Field(..., description="Type of the executed step")
    success: bool = Field(..., description="Whether execution was successful")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Output values from execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Time taken for execution in seconds")
    retried: bool = Field(False, description="Whether the step was retried")
    recovery_applied: bool = Field(False, description="Whether error recovery was applied")
    recovery_strategy: Optional[Dict[str, Any]] = Field(None, description="Recovery strategy that was applied")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw execution data")

# Data flow operators for variable references
class DataFlowOperator(Enum):
    """Operators for data flow expressions."""
    GET = "get"        # Get a value
    SET = "set"        # Set a value
    CONCAT = "concat"  # Concatenate values
    FORMAT = "format"  # Format a string with values
    JSON = "json"      # Parse or stringify JSON
    REGEX = "regex"    # Apply a regex pattern
    MATH = "math"      # Perform a math operation

# StepStatus enum from the second file - useful for tracking step execution state
class StepStatus(str, Enum):
    """Status of a task step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class EnhancedTaskPlanner:
    """
    Enhanced task planner with robust execution capabilities for complex steps.
    
    This class extends the original TaskPlanner with:
    1. Full support for CODE, API, LOOP execution
    2. Formal data flow mechanism between steps
    3. Enhanced error handling with ErrorRecoveryManager integration
    4. Comprehensive logging and debugging
    5. Security measures for code execution
    """
    
    def __init__(self):
        """Initialize the enhanced task planner."""
        self._logger = logger
        self._error_recovery_manager = registry.get("error_recovery_manager")
        if not self._error_recovery_manager:
            self._error_recovery_manager = ErrorRecoveryManager()
        
        # Initialize variable store for data flow
        self._variables: Dict[str, DataFlowVariable] = {}
        
        # Track execution statistics
        self._execution_stats = {
            "executed_plans": 0,
            "executed_steps": 0,
            "errors": 0,
            "recoveries": 0,
            "code_executions": 0,
            "api_calls": 0,
            "loops_executed": 0,
        }
        
        # Set up the sandbox environment for code execution
        self._setup_code_sandbox()
    
    def _setup_code_sandbox(self):
        """Set up the sandbox environment for code execution."""
        # Create a temp directory for code execution if it doesn't exist
        self._sandbox_dir = Path(tempfile.gettempdir()) / "angela_sandbox"
        self._sandbox_dir.mkdir(exist_ok=True)
        
        # Set up allowed imports for code execution
        self._allowed_imports = {
            # Standard library
            "os", "sys", "re", "json", "csv", "datetime", "math", "random",
            "collections", "itertools", "functools", "pathlib", "uuid",
            "time", "tempfile", "shutil", "hashlib", "base64", "hmac",
            "urllib", "http", "typing",
            
            # Common third-party libs (would need to be installed in the sandbox)
            "requests", "aiohttp", "bs4", "pandas", "numpy", "matplotlib",
        }
        
        # Set up banned function patterns
        self._banned_functions = [
            r"__import__\(",
            r"eval\(",
            r"exec\(",
            r"compile\(",
            r"globals\(\)",
            r"locals\(\)",
            r"getattr\(",
            r"setattr\(",
            r"delattr\(",
            r"subprocess\.",
            r"os\.system",
            r"os\.popen",
            r"open\(.+,\s*['\"]w['\"]",  # Writing to files
        ]
        
        self._logger.debug(f"Code sandbox set up at {self._sandbox_dir}")

```
 # AND THEN SO AFTER THIS THERES ALOT MORE FUNCTIONS SO HERES WHAT TEH FILE HAS WITH EACH ONE EXPLAINED AND BRIEF CODE SNIPPETS


        """
        ```python
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )
        response = await gemini_client.generate_text(api_request)
        ```
        ```python
        plan_data = json.loads(json_str)
        return plan_data
        ```

4.  **`async def _create_fallback_plan(self, request: str, context: Dict[str, Any]) -> AdvancedTaskPlan:`**
    *   **Name:** `_create_fallback_plan`
    *   **Purpose:** This function is called if the primary advanced plan generation (`_generate_plan_data`) fails (e.g., due to an AI error or parsing issue). It creates a simpler, single-step plan, typically by asking the AI for just a single command suggestion for the given request.
    *   **Snippets:**
        ```python
        prompt = build_prompt(request, context) # A simpler prompt for a single command
        api_request = GeminiRequest(...)
        response = await gemini_client.generate_text(api_request)
        suggestion = parse_ai_response(response.text)
        ```
        ```python
        step = AdvancedPlanStep(
            id=step_id,
            type=PlanStepType.COMMAND,
            description=suggestion.explanation or "Execute command",
            command=suggestion.command,
            # ...
        )
        ```

5.  **`async def _execute_advanced_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_advanced_step`
    *   **Purpose:** This is a core dispatcher function for executing a single step from an `AdvancedTaskPlan`. It first resolves any variables within the step's parameters, then, based on the `step.type`, it calls the appropriate specialized execution method (e.g., `_execute_command_step`, `_execute_code_step`). It also handles retries if configured for the step.
    *   **Snippets:**
        ```python
        processed_step = await self._resolve_step_variables(step, context)
        ```
        ```python
        if processed_step.type == PlanStepType.COMMAND:
            step_result = await self._execute_command_step(processed_step, context)
        elif processed_step.type == PlanStepType.CODE:
            step_result = await self._execute_code_step(processed_step, context)
        # ... and so on for other types
        ```
        ```python
        if step.retry and step.retry > 0:
            # ... retry logic ...
            retry_result = await self._execute_advanced_step(step, context) # Recursive call for retry
        ```

6.  **`async def _resolve_step_variables(self, step: AdvancedPlanStep, context: StepExecutionContext) -> AdvancedPlanStep:`**
    *   **Name:** `_resolve_step_variables`
    *   **Purpose:** This function iterates through the parameters of a given plan step and replaces any variable placeholders (e.g., `${variable_name}`) with their actual values from the current `StepExecutionContext`. It works recursively for nested dictionaries and lists within the step's definition.
    *   **Snippets:**
        ```python
        # Check for variable references like ${var_name}
        var_pattern = r'\${([^}]+)}'
        matches = re.findall(var_pattern, value)
        ```
        ```python
        var_value = self._get_variable_value(var_name, context)
        if var_value is not None:
            result = result.replace(f"${{{var_name}}}", str(var_value))
        ```

7.  **`def _get_variable_value(self, var_name: str, context: StepExecutionContext) -> Any:`**
    *   **Name:** `_get_variable_value`
    *   **Purpose:** Retrieves the value of a specified variable. It can fetch values from the planner's global variable store (`self._variables`) or from the current step's execution context (`context.variables`). It also supports accessing outputs of previous steps using a dot notation like `results.step_id.output_field`.
    *   **Snippets:**
        ```python
        if "." in var_name: # e.g., results.step1.stdout
            parts = var_name.split(".")
            if parts[0] == "result" or parts[0] == "results":
                # ... logic to access context.results ...
        ```
        ```python
        if var_name in self._variables:
            return self._variables[var_name].value
        ```

8.  **`def _set_variable(self, name: str, value: Any, source_step: str) -> None:`**
    *   **Name:** `_set_variable`
    *   **Purpose:** Stores or updates a variable in the planner's central variable store (`self._variables`). Each variable is stored as a `DataFlowVariable` object, which includes its name, value, the ID of the step that produced it, and a timestamp.
    *   **Snippets:**
        ```python
        self._variables[name] = DataFlowVariable(
            name=name,
            value=value,
            source_step=source_step,
            timestamp=datetime.now()
        )
        ```
        ```python
        self._logger.debug(f"Variable '{name}' set to value from step {source_step}")
        ```

9.  **`def _replace_variables(self, text: str, variables: Dict[str, Any]) -> str:`**
    *   **Name:** `_replace_variables`
    *   **Purpose:** This function replaces variable placeholders in a given text string. It supports two syntaxes: `${var_name}` and `$var_name`. It includes logic to avoid incorrectly replacing parts of longer variable names when using the `$var_name` syntax.
    *   **Snippets:**
        ```python
        # Replace ${var} syntax
        for var_name, var_value in variables.items():
            placeholder = f"${{{var_name}}}"
            result = result.replace(placeholder, str(var_value))
        ```
        ```python
        # Replace $var syntax (with logic to avoid partial matches)
        # if part and part[-1].isalnum() or (i < len(parts) - 1 and parts[i+1] and parts[i+1][0].isalnum()):
        #     new_parts.append(placeholder) # Don't replace, it's part of a larger var
        ```

10. **`def _extract_variables_from_output(self, output: str) -> Dict[str, Any]:`**
    *   **Name:** `_extract_variables_from_output`
    *   **Purpose:** Parses the string output (typically `stdout`) from a command execution to find and extract any declared variables. It looks for lines formatted as `VARIABLE=value` (optionally prefixed with `export`) and also attempts to parse the entire output as JSON if it seems to be a JSON object.
    *   **Snippets:**
        ```python
        # Look for lines like "VARIABLE=value" or "export VARIABLE=value"
        if line.startswith("export "):
            line = line[7:] # Remove "export "
        parts = line.split("=", 1)
        ```
        ```python
        # Look for JSON output pattern
        if output.strip().startswith("{") and output.strip().endswith("}"):
            try:
                json_data = json.loads(output)
                # ... add to variables
            except json.JSONDecodeError:
                pass
        ```

11. **`async def _execute_command_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_command_step`
    *   **Purpose:** Executes a shell command specified in a plan step. It handles dry runs (simulating execution), performs command safety validation, runs the command using the `execution_engine`, captures its `stdout`, `stderr`, and `return_code`, and then extracts any variables set in the output.
    *   **Snippets:**
        ```python
        if context.dry_run:
            return {"success": True, "stdout": f"[DRY RUN] Would execute: {step.command}"}
        ```
        ```python
        is_safe, error_message = validate_func(step.command)
        if not is_safe:
            # ... return error
        ```
        ```python
        stdout, stderr, return_code = await execution_engine.execute_command(
            command=step.command,
            check_safety=not skip_safety
        )
        ```

12. **`async def _execute_code_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_code_step`
    *   **Purpose:** Manages the execution of a code snippet (e.g., Python, JavaScript, Shell). It first performs a security validation on the code. Then, based on the specified language, it dispatches the execution to a language-specific handler like `_execute_python_code`.
    *   **Snippets:**
        ```python
        is_safe, validation_error = self._validate_code_security(step.code)
        if not is_safe:
            return {"success": False, "error": f"Code security validation failed: {validation_error}"}
        ```
        ```python
        language = getattr(step, "language", "python").lower()
        if language == "python":
            code_result = await self._execute_python_code(step.code, context)
        # ... elif for javascript, shell ...
        ```

13. **`def _validate_code_security(self, code: str) -> Tuple[bool, Optional[str]]:`** (This was your example)
    *   **Name:** `_validate_code_security`
    *   **Purpose:** Validates a string of code for potential security concerns before execution. It checks against a list of banned function call patterns (e.g., `eval(`, `os.system`) and disallowed import statements to prevent malicious or unintended operations.
    *   **Snippets:**
        ```python
        for pattern in self._banned_functions:
            if re.search(pattern, code):
                return False, f"Code contains potentially unsafe pattern: {pattern}"
        ```
        ```python
        if base_module and base_module not in self._allowed_imports:
            return False, f"Import of module '{base_module}' is not allowed"
        ```

14. **`async def _execute_python_code(self, code: str, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_python_code`
    *   **Purpose:** Securely executes a given Python code string. It creates a temporary directory and script, writes the context variables to a JSON file accessible by the script, and then runs the Python script in a separate subprocess. It uses wrapper code to inject variables, capture `stdout`, `stderr`, and any resulting variables or errors, which are then returned as a JSON object.
    *   **Snippets:**
        ```python
        # Write variables to file (serializing complex objects to JSON)
        with open(variables_file, 'w') as f:
            json.dump(context_vars, f)
        ```
        ```python
        wrapper_code = f'''
# Generated wrapper for secure code execution
import json
# ...
globals().update(variables) # Make variables available
{code} # Execute user code
# ... capture outputs ...
'''
        ```
        ```python
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(temp_file), # Runs 'python temp_file.py'
            # ...
        )
        ```

15. **`async def _execute_javascript_code(self, code: str, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_javascript_code`
    *   **Purpose:** Securely executes a given JavaScript code string using Node.js. Similar to Python execution, it sets up a temporary environment, passes context variables via a JSON file, uses wrapper JavaScript code to load variables and capture outputs/errors, and runs the script as a Node.js subprocess.
    *   **Snippets:**
        ```javascript
        // Inside wrapper_code:
        const variables = JSON.parse(fs.readFileSync("{variables_file}", "utf8"));
        Object.assign(global, variables); // Make variables available
        ```
        ```python
        # Python code calling Node.js
        process = await asyncio.create_subprocess_exec(
            "node", str(temp_file), # Runs 'node temp_file.js'
            # ...
        )
        ```

16. **`async def _execute_shell_code(self, code: str, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_shell_code`
    *   **Purpose:** Securely executes a given shell script (bash). It writes the script to a temporary executable file, exports context variables as environment variables available to the script, and then runs the script as a subprocess. It captures `stdout`, `stderr`, the return code, and any environment variables set by the script.
    *   **Snippets:**
        ```python
        # Inside the Python function, writing to the shell script file:
        f.write(f"export {var_name}=\"{str(var.value)}\"\n") # Export context vars
        f.write(code) # User's shell code
        ```
        ```python
        process = await asyncio.create_subprocess_exec(
            str(script_file), # Runs './script.sh'
            # ...
        )
        ```

17. **`async def _execute_file_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_file_step`
    *   **Purpose:** Performs various file system operations as defined by a plan step. Supported operations include reading from a file, writing content to a file, deleting a file/directory, copying, and moving. It uses helper functions from `angela.execution.filesystem`.
    *   **Snippets:**
        ```python
        if operation == "read":
            content = await read_file(step.file_path)
            # ...
        elif operation == "write":
            await write_file(step.file_path, step.file_content)
            # ...
        ```
        ```python
        elif operation == "copy":
            destination = getattr(step, "destination", None)
            await copy_file(step.file_path, destination)
        ```

18. **`async def _execute_decision_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_decision_step`
    *   **Purpose:** Evaluates a condition specified in a decision step to determine the flow of execution (i.e., which branch, true or false, to take next). The condition can be a simple expression (evaluated by `_evaluate_expression`) or a piece of code that returns a boolean result.
    *   **Snippets:**
        ```python
        if condition_type == "expression":
            condition_result = await self._evaluate_expression(step.condition, context)
        elif condition_type == "code":
            # ... create a temporary code step and execute it ...
            condition_result = bool(code_result["result"])
        ```
        ```python
        result = {
            "success": True,
            "condition_result": condition_result,
            "next_branch": "true_branch" if condition_result else "false_branch",
        }
        ```

19. **`async def _evaluate_expression(self, expression: str, context: StepExecutionContext) -> bool:`**
    *   **Name:** `_evaluate_expression`
    *   **Purpose:** Parses and evaluates simple conditional expressions used in decision steps. It supports various checks like file existence (`file exists /path/file`), command success from a previous step (`command success step_id`), whether a previous step's output contains a certain string (`output contains "text" in step_id`), and comparisons of variables (`variable X == Y`).
    *   **Snippets:**
        ```python
        file_exists_match = re.search(r'file(?:\s+)exists(?:[:=\s]+)(.+)', expression, re.IGNORECASE)
        if file_exists_match:
            # ... return Path(file_path).exists()
        ```
        ```python
        var_match = re.search(r'variable(?:\s+)(.+?)(?:\s*)([=!<>]=|[<>])(?:\s*)(.+)', expression, re.IGNORECASE)
        if var_match:
            var_value = self._get_variable_value(var_name, context)
            # ... perform comparison ...
        ```

20. **`async def _resolve_variables_in_string(self, text: str, context: StepExecutionContext) -> str:`**
    *   **Name:** `_resolve_variables_in_string`
    *   **Purpose:** Specifically designed to find and replace variable placeholders (e.g., `${variable_name}`) within a single string, using values from the current execution context. This is often used for resolving variables in paths or patterns within expressions.
    *   **Snippets:**
        ```python
        var_pattern = r'\${([^}]+)}'
        matches = re.findall(var_pattern, text)
        ```
        ```python
        for var_name in matches:
            var_value = self._get_variable_value(var_name, context)
            if var_value is not None:
                result = result.replace(f"${{{var_name}}}", str(var_value))
        ```

21. **`async def _execute_api_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_api_step`
    *   **Purpose:** Executes an HTTP API call as defined in a plan step. It handles the HTTP method (GET, POST, etc.), URL, headers, query parameters, and request payload. It uses the `aiohttp` library for making asynchronous HTTP requests and returns the API response status, headers, and body.
    *   **Snippets:**
        ```python
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.request(method, step.api_url, **request_kwargs) as response:
                response_text = await response.text()
        ```
        ```python
        result = {
            "success": 200 <= response.status < 300,
            "status_code": response.status,
            "text": response_text,
            # ...
        }
        ```

22. **`async def _execute_loop_step(self, step: AdvancedPlanStep, context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_execute_loop_step`
    *   **Purpose:** Manages the execution of a loop. It first resolves the list of items to iterate over (using `_resolve_loop_items`). Then, for each item, it executes the sequence of steps defined in the `loop_body`. A new, nested execution context is created for each iteration, making the current loop item and index available as variables.
    *   **Snippets:**
        ```python
        loop_items = await self._resolve_loop_items(step.loop_items, context)
        ```
        ```python
        for i, item in enumerate(loop_items):
            iteration_context = StepExecutionContext(
                # ...
                variables={
                    **context.variables,
                    "loop_item": item,
                    "loop_index": i,
                },
                # ...
            )
            # ... (execute steps in step.loop_body using iteration_context) ...
        ```

23. **`async def _resolve_loop_items(self, loop_items_expr: str, context: StepExecutionContext) -> List[Any]:`**
    *   **Name:** `_resolve_loop_items`
    *   **Purpose:** Determines the actual list of items that a loop step should iterate over. The `loop_items_expr` can be a direct reference to a list variable (e.g., `${my_list}`), a `range()` expression (e.g., `range(5)`), a file glob pattern (e.g., `files(*.txt)`), a JSON array string, or a simple comma-separated string.
    *   **Snippets:**
        ```python
        var_match = re.match(r'\${([^}]+)}$', loop_items_expr)
        if var_match:
            var_value = self._get_variable_value(var_name, context)
            # ... return var_value if list, or split if string ...
        ```
        ```python
        range_match = re.match(r'range\((\d+)(?:,\s*(\d+))?(?:,\s*(\d+))?\)', loop_items_expr)
        if range_match:
            # ... return list(range(...)) ...
        ```
        ```python
        files_match = re.match(r'files\(([^)]+)\)', loop_items_expr)
        if files_match:
            # ... return glob(resolved_pattern) ...
        ```

24. **`async def _attempt_recovery(self, step: AdvancedPlanStep, result: Dict[str, Any], context: StepExecutionContext) -> Dict[str, Any]:`**
    *   **Name:** `_attempt_recovery`
    *   **Purpose:** This function is invoked when a step execution fails. It interfaces with an `ErrorRecoveryManager` to try and automatically handle or suggest fixes for the error. It passes details of the failed step, the error result, and the current execution context to the recovery manager.
    *   **Snippets:**
        ```python
        if not self._error_recovery_manager:
            return { # ... indicate recovery not available ... }
        ```
        ```python
        recovery_result = await self._error_recovery_manager.handle_error(
            step_dict, result, {"context": context.dict()}
        )
        ```
        ```python
        if recovery_result.get("recovery_success", False):
            result["success"] = True
            result["recovery_applied"] = True
            # ... update result with recovery outputs ...
        ```

```python
# Create an instance of the enhanced task planner

enhanced_task_planner = EnhancedTaskPlanner()

# Replace the global task_planner with the enhanced version
task_planner = enhanced_task_planner
```



**File 1: `angela/intent/complex_workflow_planner.py`**

"""
Complex Workflow Orchestration for Angela CLI.

This module extends the existing enhanced task planner with specialized
capabilities for orchestrating workflows across multiple CLI tools and
services, enabling end-to-end automation of complex development and
deployment pipelines.
"""
import asyncio
import json
import re
import shlex
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable

from pydantic import BaseModel, Field, validator

from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.core.registry import registry
from angela.intent.enhanced_task_planner import (
    EnhancedTaskPlanner, StepExecutionContext, 
    AdvancedTaskPlan, AdvancedPlanStep, PlanStepType,
    ExecutionResult
)
from angela.toolchain.universal_cli import universal_cli_translator
from angela.execution.adaptive_engine import adaptive_engine

logger = get_logger(__name__)

class WorkflowStepType(str, Enum):
    """Types of steps in a complex workflow."""
    COMMAND = "command"              # Standard shell command
    TOOL = "tool"                    # External CLI tool command
    API = "api"                      # API call
    DECISION = "decision"            # Decision point
    WAIT = "wait"                    # Wait for a condition
    PARALLEL = "parallel"            # Parallel execution
    CUSTOM_CODE = "custom_code"      # Custom code execution
    NOTIFICATION = "notification"    # Send notification
    VALIDATION = "validation"        # Validate a condition

class WorkflowVariable(BaseModel):
    """Model for a variable in a workflow."""
    name: str = Field(..., description="Name of the variable")
    description: Optional[str] = Field(None, description="Description of the variable")
    default_value: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(False, description="Whether the variable is required")
    type: str = Field("string", description="Data type (string, number, boolean)")
    scope: str = Field("global", description="Variable scope (global, step, local)")
    source_step: Optional[str] = Field(None, description="Step that produces this variable")

class WorkflowStepDependency(BaseModel):
    """Model for a dependency between workflow steps."""
    step_id: str = Field(..., description="ID of the dependent step")
    type: str = Field("success", description="Type of dependency (success, completion, failure)")
    condition: Optional[str] = Field(None, description="Optional condition for the dependency")

class WorkflowStep(BaseModel):
    """Model for a step in a complex workflow."""
    id: str = Field(..., description="Unique identifier for this step")
    name: str = Field(..., description="Human-readable name for the step")
    type: WorkflowStepType = Field(..., description="Type of workflow step")
    description: str = Field(..., description="Detailed description of what this step does")
    tool: Optional[str] = Field(None, description="Tool name for TOOL type")
    command: Optional[str] = Field(None, description="Command to execute")
    api_url: Optional[str] = Field(None, description="URL for API call")
    api_method: Optional[str] = Field("GET", description="HTTP method for API call")
    api_headers: Dict[str, str] = Field(default_factory=dict, description="Headers for API call")
    api_data: Optional[Any] = Field(None, description="Data payload for API call")
    code: Optional[str] = Field(None, description="Custom code to execute")
    condition: Optional[str] = Field(None, description="Condition for DECISION or VALIDATION type")
    wait_condition: Optional[str] = Field(None, description="Condition to wait for in WAIT type")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry: Optional[int] = Field(None, description="Number of retry attempts")
    parallel_steps: List[str] = Field(default_factory=list, description="Steps to execute in parallel")
    dependencies: List[WorkflowStepDependency] = Field(default_factory=list, description="Dependencies on other steps")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input values for the step")
    outputs: List[str] = Field(default_factory=list, description="Output variables produced by this step")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables for this step")
    working_dir: Optional[str] = Field(None, description="Working directory for this step")
    on_success: Optional[str] = Field(None, description="Step to execute on success")
    on_failure: Optional[str] = Field(None, description="Step to execute on failure")
    estimated_risk: int = Field(0, description="Risk level (0-4)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

class ComplexWorkflowPlan(BaseModel):
    """Model for a complex workflow plan."""
    id: str = Field(..., description="Unique identifier for this workflow")
    name: str = Field(..., description="Name of the workflow")
    description: str = Field(..., description="Detailed description of the workflow")
    goal: str = Field(..., description="Original goal that prompted this workflow")
    steps: Dict[str, WorkflowStep] = Field(..., description="Steps of the workflow")
    variables: Dict[str, WorkflowVariable] = Field(default_factory=dict, description="Workflow variables")
    entry_points: List[str] = Field(..., description="Step IDs to start execution with")
    exit_points: List[str] = Field(default_factory=list, description="Step IDs that conclude the workflow")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    created: datetime = Field(default_factory=datetime.now, description="When the workflow was created")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ComplexWorkflowPlanner(EnhancedTaskPlanner):
    """
    Planner specialized for creating and executing complex workflows that
    orchestrate multiple tools and services in a controlled, reliable manner.
    """
    
    def __init__(self):
        """Initialize the complex workflow planner."""
        super().__init__()
        self._logger = logger
        
        # Track currently executing workflows
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Register supported workflow step handlers
        self._step_handlers = {
            WorkflowStepType.COMMAND: self._execute_command_step,
            WorkflowStepType.TOOL: self._execute_tool_step,
            WorkflowStepType.API: self._execute_api_step,
            WorkflowStepType.DECISION: self._execute_decision_step,
            WorkflowStepType.WAIT: self._execute_wait_step,
            WorkflowStepType.PARALLEL: self._execute_parallel_step,
            WorkflowStepType.CUSTOM_CODE: self._execute_custom_code_step,
            WorkflowStepType.NOTIFICATION: self._execute_notification_step,
            WorkflowStepType.VALIDATION: self._execute_validation_step,
        }
    

1.  **`async def _generate_workflow_plan(self, request: str, context: Dict[str, Any], max_steps: int) -> Dict[str, Any]:`**
    *   **Name:** `_generate_workflow_plan`
    *   **Purpose:** This asynchronous function interacts with an AI model (Gemini) to generate a detailed workflow plan in JSON format based on a natural language request and context. It constructs a comprehensive prompt that guides the AI to define steps, variables, dependencies, and other workflow elements.
    *   **Snippets:**
        ```python
        prompt = f"""
You are an expert DevOps engineer and workflow automation specialist. Create a detailed workflow plan for this request:

REQUEST: "{request}"
# ... more prompt details ...
Return a structured JSON object with:
# ... JSON structure definition ...
"""
        ```
        ```python
        api_request = GeminiRequest(prompt=prompt, max_tokens=4000)
        response = await gemini_client.generate_text(api_request)
        ```
        ```python
        plan_data = json.loads(json_str)
        return plan_data
        ```

2.  **`def _convert_step_data_to_models(self, steps_data: Dict[str, Dict[str, Any]]) -> Dict[str, WorkflowStep]:`**
    *   **Name:** `_convert_step_data_to_models`
    *   **Purpose:** This function takes the raw step data (a dictionary) received from the AI and converts each step into a `WorkflowStep` Pydantic model. It handles default values for missing fields and ensures dependencies are correctly formatted.
    *   **Snippets:**
        ```python
        for step_id, step_data in steps_data.items():
            # ... ensure required fields, format dependencies ...
            step_data["dependencies"] = dependencies
            result[step_id] = WorkflowStep(**step_data)
        ```
        ```python
        # Fallback for error during model creation
        result[step_id] = WorkflowStep(
            id=step_id,
            name=step_data.get("name", f"Step {step_id}"),
            type=WorkflowStepType.COMMAND,
            # ...
        )
        ```

3.  **`def _convert_variable_data_to_models(self, variables_data: Dict[str, Dict[str, Any]]) -> Dict[str, WorkflowVariable]:`**
    *   **Name:** `_convert_variable_data_to_models`
    *   **Purpose:** Similar to `_convert_step_data_to_models`, this function converts raw variable data from the AI into `WorkflowVariable` Pydantic models.
    *   **Snippets:**
        ```python
        for var_name, var_data in variables_data.items():
            var_data["name"] = var_name
            result[var_name] = WorkflowVariable(**var_data)
        ```

4.  **`def _create_fallback_workflow(self, request: str, context: Dict[str, Any]) -> ComplexWorkflowPlan:`**
    *   **Name:** `_create_fallback_workflow`
    *   **Purpose:** If the AI-driven workflow plan generation fails, this function creates a very simple, minimal `ComplexWorkflowPlan` as a fallback. This plan usually contains a single step indicating the failure.
    *   **Snippets:**
        ```python
        step = WorkflowStep(
            id=step_id,
            name="Fallback Step",
            type=WorkflowStepType.COMMAND,
            description="Fallback step due to workflow planning error",
            command=f"echo 'Failed to create complex workflow for: {request}'",
        )
        ```
        ```python
        return ComplexWorkflowPlan(
            id=workflow_id,
            name=f"Fallback Workflow {workflow_id[:8]}",
            # ...
            steps={step_id: step},
            entry_points=[step_id],
        )
        ```

5.  **`def _is_dependency_satisfied(self, dependency: WorkflowStepDependency, execution_state: Dict[str, Any]) -> bool:`**
    *   **Name:** `_is_dependency_satisfied`
    *   **Purpose:** Checks if a specific `WorkflowStepDependency` is met based on the current `execution_state`. It looks at whether the depended-upon step has completed and, if so, whether it met the success/failure/completion criteria of the dependency.
    *   **Snippets:**
        ```python
        if step_id not in execution_state["completed_steps"]:
            return False
        ```
        ```python
        if dependency.type == "success":
            return result.get("success", False)
        elif dependency.type == "failure":
            return not result.get("success", False)
        ```

6.  **`async def _execute_command_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_command_step`
    *   **Purpose:** Executes a shell command defined in a `WorkflowStep`. It substitutes variables in the command string, handles dry runs, sets the working directory and environment variables, and uses the `adaptive_engine` for actual execution. It then formats the result, including any extracted output variables.
    *   **Snippets:**
        ```python
        command = self._substitute_variables(step.command, execution_state["variables"])
        ```
        ```python
        if execution_state["dry_run"]:
            return { "success": True, "stdout": f"[DRY RUN] Would execute: {command}" }
        ```
        ```python
        result = await adaptive_engine.execute_command(
            command=command,
            # ...
            working_dir=working_dir,
            environment=env if env else None
        )
        ```

7.  **`async def _execute_tool_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_tool_step`
    *   **Purpose:** Executes a command for an external CLI tool, as specified in a `WorkflowStep`. It's similar to `_execute_command_step` but might involve specific handling or translation via `universal_cli_translator` (though in the provided snippet, it uses `adaptive_engine` directly like `_execute_command_step`).
    *   **Snippets:**
        ```python
        tool = self._substitute_variables(step.tool, execution_state["variables"])
        command = self._substitute_variables(step.command or "", execution_state["variables"])
        full_command = f"{tool} {command}".strip()
        ```
        ```python
        result = await adaptive_engine.execute_command(
            command=full_command,
            # ...
        )
        ```

8.  **`async def _execute_api_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_api_step`
    *   **Purpose:** Performs an HTTP API call defined in a `WorkflowStep`. It substitutes variables in the URL, headers, and payload. It uses `aiohttp` to make the asynchronous request and processes the response.
    *   **Snippets:**
        ```python
        api_url = self._substitute_variables(step.api_url, execution_state["variables"])
        # ... substitute variables in headers and data ...
        ```
        ```python
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, api_url, headers=headers, json=data_if_json, data=data_if_form) as response:
                status = response.status
                response_text = await response.text()
        ```

9.  **`async def _execute_decision_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_decision_step`
    *   **Purpose:** Evaluates a conditional expression defined in a `WorkflowStep` of type `DECISION`. The result of this evaluation (true/false) can then be used by the workflow engine to determine the next step or branch.
    *   **Snippets:**
        ```python
        condition = self._substitute_variables(step.condition, execution_state["variables"])
        ```
        ```python
        condition_result = await self._evaluate_condition(
            condition,
            execution_state["variables"]
        )
        ```
        ```python
        return {
            "success": True,
            "condition_result": condition_result,
            # ...
        }
        ```

10. **`async def _execute_wait_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_wait_step`
    *   **Purpose:** Pauses workflow execution. It can either wait for a specific duration (if `step.timeout` is set and `step.wait_condition` is not) or wait until a `step.wait_condition` evaluates to true, polling periodically up to a timeout.
    *   **Snippets:**
        ```python
        # For condition-based wait
        condition = self._substitute_variables(step.wait_condition, execution_state["variables"])
        for attempt in range(max_attempts):
            condition_result = await self._evaluate_condition(condition, execution_state["variables"])
            if condition_result:
                # ... success ...
            await asyncio.sleep(wait_interval)
        ```
        ```python
        # For time-based wait
        wait_time = step.timeout or 10
        await asyncio.sleep(wait_time)
        ```

11. **`async def _execute_parallel_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_parallel_step`
    *   **Purpose:** Executes multiple defined workflow steps concurrently. It gathers the specified `parallel_steps`, creates an `asyncio` task for each, and runs them using `asyncio.gather`.
    *   **Snippets:**
        ```python
        for parallel_step_id in step.parallel_steps:
            # ... get parallel_step from workflow.steps ...
            tasks.append(handler(parallel_step, step_execution_state))
        ```
        ```python
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
        # ... process results ...
        ```

12. **`async def _execute_custom_code_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_custom_code_step`
    *   **Purpose:** Executes a snippet of Python code defined in a `WorkflowStep`. It substitutes variables into the code string and then runs it using `exec()`. **Note:** The provided implementation is explicitly marked as potentially unsafe and would require proper sandboxing in a production system.
    *   **Snippets:**
        ```python
        code = self._substitute_variables(step.code, execution_state["variables"])
        ```
        ```python
        sandbox = {
            "variables": execution_state["variables"].copy(),
            "results": {},
            # ... other safe utilities ...
            "outputs": {}
        }
        exec(code, sandbox)
        ```

13. **`async def _execute_notification_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_notification_step`
    *   **Purpose:** Sends a notification. In the current implementation, this logs the message and prints it to the console (using `rich` if available). In a more complete system, it would integrate with actual notification services (email, Slack, etc.).
    *   **Snippets:**
        ```python
        message = step.command or "Workflow notification"
        message = self._substitute_variables(message, execution_state["variables"])
        self._logger.info(f"NOTIFICATION: {message}")
        ```
        ```python
        # rich console output
        console.print(Panel(message, title=f"Workflow Notification - ..."))
        ```

14. **`async def _execute_validation_step(self, step: WorkflowStep, execution_state: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_validation_step`
    *   **Purpose:** Evaluates a condition defined in a `WorkflowStep` to validate a state or outcome. The `success` field of the result indicates if the validation check itself ran correctly, while a `validated` field in the output shows the boolean result of the condition.
    *   **Snippets:**
        ```python
        condition = self._substitute_variables(step.condition, execution_state["variables"])
        ```
        ```python
        validation_result = await self._evaluate_condition(
            condition,
            execution_state["variables"]
        )
        return { "success": True, "validated": validation_result, ... }
        ```

15. **`def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:`**
    *   **Name:** `_substitute_variables`
    *   **Purpose:** Replaces variable placeholders in a given text string. It supports `${var}` syntax and `$var` syntax (with word boundary checks for the latter to avoid partial replacements).
    *   **Snippets:**
        ```python
        # Replace ${var} syntax
        placeholder = f"${{{var_name}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(var_value))
        ```
        ```python
        # Replace $var syntax (only for word boundaries)
        result = re.sub(r'\$' + var_name + r'\b', str(variables[var_name]), result)
        ```

16. **`def _extract_variables_from_output(self, output: str) -> Dict[str, Any]:`**
    *   **Name:** `_extract_variables_from_output`
    *   **Purpose:** Parses string output (e.g., from a command) to find and extract variable declarations. It looks for `VARIABLE=value` patterns (optionally with `export`) and also tries to parse the output as JSON.
    *   **Snippets:**
        ```python
        # Look for lines like "VARIABLE=value" or "export VARIABLE=value"
        if line.startswith("export "):
            line = line[7:]
        parts = line.split("=", 1)
        ```
        ```python
        # Look for JSON output pattern
        if output.strip().startswith("{") and output.strip().endswith("}"):
            json_data = json.loads(output)
        ```

17. **`async def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:`**
    *   **Name:** `_evaluate_condition`
    *   **Purpose:** Evaluates a simple conditional expression string. It supports basic comparisons (`==`, `!=`), string containment (`'x' in $var`), file existence checks (`file exists /path/to/file`), and checking if a command succeeds. **Note:** The command success check executes the command, which could have side effects.
    *   **Snippets:**
        ```python
        # Variable equals value: $var == value
        var_equals_match = re.search(r'\$\{?([a-zA-Z0-9_]+)\}?\s*==\s*(.+)', condition)
        if var_equals_match:
            # ... comparison logic ...
        ```
        ```python
        # File exists pattern
        file_exists_match = re.search(r'file\s+exists\s+(.+)', condition, re.IGNORECASE)
        if file_exists_match:
            file_path = self._substitute_variables(file_path, variables)
            return Path(file_path).exists()
        ```
        ```python
        # Command success pattern
        command_success_match = re.search(r'command\s+(.+?)\s+succeeds', condition, re.IGNORECASE)
        if command_success_match:
            process = await asyncio.create_subprocess_shell(...)
            return process.returncode == 0
        ```
complex_workflow_planner = ComplexWorkflowPlanner()
---

**File 2: `angela/intent/semantic_task_planner.py`**
"""
Semantic task planning and intent decomposition for Angela CLI.

This module extends the enhanced task planner with semantic code understanding
and improved intent decomposition for handling complex, ambiguous, multi-stage goals.
"""
import re
import json
import uuid
import asyncio
from typing import Dict, Any, List, Tuple, Optional, Set, Union
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from angela.ai.client import gemini_client, GeminiRequest
from angela.ai.semantic_analyzer import semantic_analyzer
from angela.context import context_manager
from angela.context.project_state_analyzer import project_state_analyzer
from angela.intent.enhanced_task_planner import EnhancedTaskPlanner, AdvancedTaskPlan, PlanStepType
from angela.utils.logging import get_logger
from angela.core.registry import registry
from angela.shell.inline_feedback import inline_feedback

logger = get_logger(__name__)

class IntentClarification(BaseModel):
    """Model for intent clarification information."""
    
    original_request: str = Field(..., description="The original user request")
    ambiguity_type: str = Field(..., description="Type of ambiguity detected")
    ambiguity_details: str = Field(..., description="Details about the ambiguity")
    clarification_question: str = Field(..., description="Question to ask the user")
    options: List[str] = Field(default_factory=list, description="Possible options to present to the user")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context for resolving the ambiguity")


class SemanticTaskPlanner:
    """
    Enhanced task planner with semantic code understanding and improved intent decomposition.
    
    This class extends the existing EnhancedTaskPlanner with:
    1. Integration with semantic code analysis
    2. Improved handling of ambiguous requests
    3. Multi-stage goal decomposition with sub-goals
    4. Interactive clarification for uncertain intents
    """
    
    def __init__(self):
        """Initialize the semantic task planner."""
        self._logger = logger
        self._enhanced_planner = EnhancedTaskPlanner()
        self._clarification_handlers = {
            "file_reference": self._clarify_file_reference,
            "entity_reference": self._clarify_entity_reference,
            "action_type": self._clarify_action_type,
            "operation_scope": self._clarify_operation_scope,
            "step_ordering": self._clarify_step_ordering,
            "parameter_value": self._clarify_parameter_value
        }
    
    async def plan_task(
        self, 
        request: str, 
        context: Dict[str, Any],
        enable_clarification: bool = True,
        semantic_context: bool = True
    ) -> Dict[str, Any]:
        """
        Plan a task with semantic understanding and potential user clarification.
        
        Args:
            request: User request
            context: Task context
            enable_clarification: Whether to enable interactive clarification
            semantic_context: Whether to include semantic code understanding
            
        Returns:
            Dictionary with planning results including a task plan
        """
        self._logger.info(f"Planning semantic task: {request}")
        
        # Enhance context with semantic information if requested
        if semantic_context:
            context = await self._enhance_context_with_semantics(context)
        
        # First, analyze the request for potential ambiguities
        intent_analysis = await self._analyze_intent(request, context)
        
        # Check if clarification is needed and enabled
        if intent_analysis.get("needs_clarification", False) and enable_clarification:
            clarification = await self._create_clarification(request, intent_analysis, context)
            
            if clarification:
                # Get user clarification
                clarified_request = await self._get_user_clarification(clarification)
                
                if clarified_request:
                    # Update the request and intent analysis
                    self._logger.info(f"Using clarified request: {clarified_request}")
                    request = clarified_request
                    intent_analysis = await self._analyze_intent(request, context)
        
        # Decompose the goal into sub-goals if complex
        goal_decomposition = await self._decompose_goal(request, intent_analysis, context)
        
        # Create an execution plan
        plan_result = await self._create_execution_plan(request, goal_decomposition, context)
        
        # Return the planning results
        return {
            "original_request": request,
            "intent_analysis": intent_analysis,
            "goal_decomposition": goal_decomposition,
            "execution_plan": plan_result.get("plan"),
            "plan_type": plan_result.get("plan_type", "simple"),
            "plan_id": plan_result.get("plan_id"),
            "estimated_steps": plan_result.get("estimated_steps", 0),
            "max_risk_level": plan_result.get("max_risk_level", 0),
            "clarification_needed": intent_analysis.get("needs_clarification", False),
            "clarification_performed": intent_analysis.get("needs_clarification", False) and enable_clarification
        }



1.  **`async def _analyze_intent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_analyze_intent`
    *   **Purpose:** This function sends a user's request and relevant project context to an AI model (Gemini) to get a detailed semantic analysis of the user's intent. The AI is prompted to identify the primary goal, entities involved, sub-tasks, potential ambiguities, complexity, and risk.
    *   **Snippets:**
        ```python
        project_context = self._extract_project_context(context)
        prompt = f"""
You are an expert assistant analyzing a user's request...
USER REQUEST: "{request}"
CONTEXT:
{project_context}
Return your analysis as a JSON object with this structure:
# ... JSON structure definition ...
"""
        ```
        ```python
        api_request = GeminiRequest(prompt=prompt, temperature=0.1, max_tokens=3000)
        response = await gemini_client.generate_text(api_request)
        intent_analysis = json.loads(response_text)
        ```

2.  **`def _extract_project_context(self, context: Dict[str, Any]) -> str:`**
    *   **Name:** `_extract_project_context`
    *   **Purpose:** Compiles a string summary of the current project context. This includes information like the current working directory, project type, recently accessed files, key code entities from semantic analysis, and Git status. This summary is used to give the AI better context for intent analysis.
    *   **Snippets:**
        ```python
        if "cwd" in context:
            lines.append(f"Current Directory: {context['cwd']}")
        ```
        ```python
        if "semantic_code" in context:
            # ... append info about modules and key entities ...
        ```
        ```python
        if "project_state" in context and "git_state" in project_state:
            # ... append Git branch and status ...
        ```

3.  **`async def _create_clarification(self, request: str, intent_analysis: Dict[str, Any], context: Dict[str, Any]) -> Optional[IntentClarification]:`**
    *   **Name:** `_create_clarification`
    *   **Purpose:** If the `_analyze_intent` step identifies ambiguities (`needs_clarification` is true), this function generates an `IntentClarification` object. It selects an ambiguity and uses a corresponding handler (from `self._clarification_handlers`) to formulate a question and options for the user.
    *   **Snippets:**
        ```python
        if not intent_analysis.get("needs_clarification", False):
            return None
        ambiguity = ambiguities[0] # Takes the first ambiguity
        ```
        ```python
        if ambiguity_type in self._clarification_handlers:
            return await self._clarification_handlers[ambiguity_type](
                request, ambiguity, interpretations, context
            )
        ```

4.  **`async def _get_user_clarification(self, clarification: IntentClarification) -> Optional[str]:`**
    *   **Name:** `_get_user_clarification`
    *   **Purpose:** Presents the `IntentClarification` (question and options) to the user, typically using an `inline_feedback` mechanism. It then returns the user's response, which might be a selection from options or free-form text.
    *   **Snippets:**
        ```python
        if inline_feedback:
            response = await inline_feedback.ask_question(
                question,
                choices=options,
                allow_free_text=True
            )
        ```
        ```python
        if clarification.ambiguity_type in ["file_reference", ...]:
            return self._update_request_with_clarification(...)
        else:
            return response
        ```

5.  **`def _update_request_with_clarification(self, original_request: str, clarification: str, intent_clarification: IntentClarification) -> str:`**
    *   **Name:** `_update_request_with_clarification`
    *   **Purpose:** Modifies the original user request string by incorporating the clarification provided by the user. For example, it might replace an ambiguous file reference with the user's chosen file or append a clarified parameter.
    *   **Snippets:**
        ```python
        if ambiguity_type == "file_reference":
            ambiguous_ref = context["file_reference"]
            return original_request.replace(ambiguous_ref, clarification)
        ```
        ```python
        elif ambiguity_type == "parameter_value":
            # ... logic to find and replace or append parameter ...
            return f"{original_request} {param_name}={clarification}"
        ```

6.  **`async def _clarify_file_reference(self, request: str, ambiguity: Dict[str, Any], interpretations: List[str], context: Dict[str, Any]) -> IntentClarification:`**
    *   **Name:** `_clarify_file_reference`
    *   **Purpose:** A specialized handler for creating an `IntentClarification` when a file reference is ambiguous. It tries to extract the ambiguous reference and may use `file_resolver` or existing context to suggest possible file options to the user.
    *   **Snippets:**
        ```python
        match = re.search(r'(?:file|directory|folder|path|docs?)\s+["\']?([^"\']+)["\']?', description)
        if match:
            file_reference = match.group(1)
        ```
        ```python
        question = f"I'm not sure which file '{file_reference}' refers to. Which one did you mean?"
        return IntentClarification(...)
        ```

7.  **`async def _clarify_entity_reference(self, request: str, ambiguity: Dict[str, Any], interpretations: List[str], context: Dict[str, Any]) -> IntentClarification:`**
    *   **Name:** `_clarify_entity_reference`
    *   **Purpose:** Creates an `IntentClarification` for ambiguous references to code entities (functions, classes, etc.). If semantic code information is available in the context, it attempts to find similar entities to offer as clarification options.
    *   **Snippets:**
        ```python
        match = re.search(r'(?:function|class|method|variable|object|module|component)\s+["\']?([^"\']+)["\']?', description)
        # ...
        if "semantic_code" in context and entity_reference:
            # ... use difflib to find similar entities from semantic_code info ...
            interpretations = [f"{e['name']} ({e['type']} in {Path(e['file']).name})" for e in similar_entities[:5]]
        ```

8.  **`async def _clarify_action_type(self, ...)`**, **`async def _clarify_operation_scope(self, ...)`**, **`async def _clarify_step_ordering(self, ...)`**, **`async def _clarify_parameter_value(self, ...)`**
    *   **Name(s):** `_clarify_action_type`, `_clarify_operation_scope`, `_clarify_step_ordering`, `_clarify_parameter_value`
    *   **Purpose:** These are all specialized handlers similar to `_clarify_file_reference`. Each one is responsible for generating an appropriate `IntentClarification` (question and options) when the AI detects ambiguity related to the action type, operation scope, step ordering, or a missing/unclear parameter value, respectively. They often provide default options if the AI's analysis doesn't include specific interpretations.
    *   **Snippets (Example from `_clarify_action_type`):**
        ```python
        if not interpretations: # Default interpretations if AI didn't provide any
            interpretations = [
                "Show/display the content",
                "Edit/modify the content",
                # ...
            ]
        question = f"I'm not sure what action you want to perform: {description}. What would you like to do?"
        return IntentClarification(...)
        ```

9.  **`async def _decompose_goal(self, request: str, intent_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_decompose_goal`
    *   **Purpose:** If the initial intent analysis deems the user's request to be complex, this function asks the AI (Gemini) to break down the main goal into smaller, more manageable sub-goals. The AI is prompted to define these sub-goals, their dependencies, and complexity.
    *   **Snippets:**
        ```python
        if intent_analysis.get("complexity", "simple") == "simple":
            return { "main_goal": ..., "sub_goals": [request], ... } # No decomposition needed
        ```
        ```python
        prompt = f"""
You need to decompose a complex user request into clear, logical sub-goals...
USER REQUEST: "{request}"
ANALYZED INTENT: ...
Return your decomposition as a JSON object with this structure:
# ... JSON structure for sub-goals, dependencies, etc. ...
"""
        api_request = GeminiRequest(...)
        response = await gemini_client.generate_text(api_request)
        decomposition = json.loads(response_text)
        ```

10. **`async def _create_execution_plan(self, request: str, goal_decomposition: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_create_execution_plan`
    *   **Purpose:** Based on the (potentially decomposed) goal, this function generates an actual executable plan. If the goal is simple, it calls `self._enhanced_planner.plan_task` directly. If complex and decomposed into sub-goals, it constructs a request for the `_enhanced_planner` that reflects the sequence or dependencies of these sub-goals to generate an `AdvancedTaskPlan`.
    *   **Snippets:**
        ```python
        if goal_decomposition.get("complexity", "simple") == "simple":
            plan = await self._enhanced_planner.plan_task(request=request, context=context, complexity="auto")
            # ...
        ```
        ```python
        # For sequential complex goals
        combined_request = f"{request}\n\nExecute these steps in order:\n"
        for i, sub_goal in enumerate(sub_goals):
            combined_request += f"{i+1}. {sub_goal.get('description', '')}\n"
        plan = await self._enhanced_planner.plan_task(request=combined_request, context=context, complexity="advanced")
        ```

11. **`async def _enhance_context_with_semantics(self, context: Dict[str, Any]) -> Dict[str, Any]:`**
    *   **Name:** `_enhance_context_with_semantics`
    *   **Purpose:** Augments the provided `context` dictionary with richer semantic information about the current project. This involves using `semantic_analyzer` to analyze recently accessed files (to find functions, classes) and `project_state_analyzer` to get information like Git status or TODO items. This enhanced context is then used for more accurate AI interactions.
    *   **Snippets:**
        ```python
        for file_path in recent_files[:3]: # Analyze a few recent files
            module = await semantic_analyzer.analyze_file(file_path)
            if module:
                semantic_info["modules"].append(module.get_summary())
                # ... extract key_entities (functions, classes) ...
        ```
        ```python
        project_state = await project_state_analyzer.get_project_state(project_root)
        enhanced_context["semantic_code"] = semantic_info
        enhanced_context["project_state"] = project_state
        ```



semantic_task_planner = SemanticTaskPlanner()
---

**File 3: `angela/intent/planner.py`**

"""
Task planning and goal decomposition for Angela CLI.

This module handles breaking down complex high-level goals into
executable action plans with dependencies and execution flow.
It provides two levels of planning capability:
1. Basic planning - For straightforward sequential tasks
2. Advanced planning - For complex tasks with branching, conditionals, and various step types
"""
import os
import re
import json
import shlex
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from angela.intent.models import ActionPlan, Intent, IntentType
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

#######################
# Basic Planning Models
#######################

class PlanStep(BaseModel):
    """Model for a single step in a basic plan."""
    command: str = Field(..., description="The command to execute")
    explanation: str = Field(..., description="Explanation of the command")
    dependencies: List[int] = Field(default_factory=list, description="Indices of steps this step depends on")
    estimated_risk: int = Field(0, description="Estimated risk level (0-4)")


class TaskPlan(BaseModel):
    """Model for a complete basic task plan."""
    goal: str = Field(..., description="The original high-level goal")
    steps: List[PlanStep] = Field(..., description="Steps to achieve the goal")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")

#######################
# Advanced Planning Models
#######################

class PlanStepType(str, Enum):
    """Types of plan steps for advanced planning."""
    COMMAND = "command"  # Shell command
    CODE = "code"        # Code to execute or save
    FILE = "file"        # File operation
    DECISION = "decision"  # Decision point, may branch execution
    API = "api"          # API call
    LOOP = "loop"        # Looping construct


class AdvancedPlanStep(BaseModel):
    """Model for an advanced plan step with additional capabilities."""
    id: str = Field(..., description="Unique identifier for this step")
    type: PlanStepType = Field(..., description="Type of step")
    description: str = Field(..., description="Human-readable description")
    command: Optional[str] = Field(None, description="Command to execute (for command type)")
    code: Optional[str] = Field(None, description="Code to execute or save (for code type)")
    file_path: Optional[str] = Field(None, description="Path for file operations (for file type)")
    file_content: Optional[str] = Field(None, description="Content for file operations (for file type)")
    condition: Optional[str] = Field(None, description="Condition for decision steps (for decision type)")
    true_branch: Optional[List[str]] = Field(None, description="Steps to execute if condition is true")
    false_branch: Optional[List[str]] = Field(None, description="Steps to execute if condition is false")
    api_url: Optional[str] = Field(None, description="URL for API calls (for api type)")
    api_method: Optional[str] = Field(None, description="HTTP method for API calls (for api type)")
    api_payload: Optional[Dict[str, Any]] = Field(None, description="Payload for API calls (for api type)")
    loop_items: Optional[str] = Field(None, description="Items to loop over (for loop type)")
    loop_body: Optional[List[str]] = Field(None, description="Steps to execute in loop (for loop type)")
    dependencies: List[str] = Field(default_factory=list, description="IDs of steps this step depends on")
    estimated_risk: int = Field(0, description="Estimated risk level (0-4)")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry: Optional[int] = Field(None, description="Number of retries on failure")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class AdvancedTaskPlan(BaseModel):
    """Model for an advanced task plan with branching and complex steps."""
    id: str = Field(..., description="Unique identifier for this plan")
    goal: str = Field(..., description="The original high-level goal")
    description: str = Field(..., description="Detailed description of the plan")
    steps: Dict[str, AdvancedPlanStep] = Field(..., description="Steps to achieve the goal, indexed by ID")
    entry_points: List[str] = Field(..., description="Step IDs to start execution with")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    created: datetime = Field(default_factory=datetime.now, description="When the plan was created")


#######################
# Unified Task Planner
#######################

class TaskPlanner:
    """
    Task planner for breaking down complex goals into actionable steps.
    
    This planner can generate two types of plans:
    1. Basic plans (TaskPlan) - For simple sequential tasks
    2. Advanced plans (AdvancedTaskPlan) - For complex tasks with branching execution
    
    The planner automatically determines the appropriate plan type based on the
    complexity of the goal and request context.
    """
    
    def __init__(self):
        """Initialize the task planner."""
        self._logger = logger
    
    async def plan_task(
        self, 
        goal: str, 
        context: Dict[str, Any],
        complexity: str = "auto"
    ) -> Union[TaskPlan, AdvancedTaskPlan]:
        """
        Plan a task by breaking it down into actionable steps.
        
        Args:
            goal: The high-level goal description
            context: Context information
            complexity: Planning complexity level ("simple", "advanced", or "auto")
            
        Returns:
            Either a basic TaskPlan or an advanced AdvancedTaskPlan based on complexity
        """
        self._logger.info(f"Planning task: {goal} (complexity: {complexity})")
        
        # Determine planning complexity if auto
        if complexity == "auto":
            complexity = await self._determine_complexity(goal)
            self._logger.info(f"Determined complexity: {complexity}")
        
        # Use the appropriate planning strategy
        if complexity == "simple":
            # Use basic planning for simple tasks
            return await self._create_basic_plan(goal, context)
        else:
            # Use advanced planning for complex tasks
            return await self._generate_advanced_plan(goal, context)
    
    async def _determine_complexity(self, goal: str) -> str:
        """
        Determine the appropriate planning complexity for a goal.
        
        Args:
            goal: The high-level goal
            
        Returns:
            Complexity level ("simple" or "advanced")
        """
        # Simple heuristics based on goal text
        complexity_indicators = [
            "if", "when", "based on", "for each", "foreach", "loop", "iterate",
            "depending on", "decision", "alternative", "otherwise", "create file",
            "write to file", "dynamic", "api", "request", "conditionally",
            "advanced", "complex", "multiple steps", "error handling"
        ]
        
        # Count indicators
        indicator_count = sum(1 for indicator in complexity_indicators 
                              if indicator in goal.lower())
        
        # Check goal length and complexity indicators
        if len(goal.split()) > 20 or indicator_count >= 2:
            return "advanced"
        else:
            return "simple"



1.  **`async def _determine_complexity(self, goal: str) -> str:`**
    *   **Name:** `_determine_complexity`
    *   **Purpose:** This function uses simple heuristics (keywords in the goal string and goal length) to make a basic guess about whether a user's goal requires "simple" or "advanced" planning.
    *   **Snippets:**
        ```python
        complexity_indicators = [
            "if", "when", "based on", "for each", # ... and others
        ]
        indicator_count = sum(1 for indicator in complexity_indicators if indicator in goal.lower())
        ```
        ```python
        if len(goal.split()) > 20 or indicator_count >= 2:
            return "advanced"
        else:
            return "simple"
        ```

2.  **`async def _create_basic_plan(self, goal: str, context: Dict[str, Any]) -> TaskPlan:`**
    *   **Name:** `_create_basic_plan`
    *   **Purpose:** Generates a `TaskPlan` (a simpler, sequential list of commands) for a given goal. It builds a prompt for the AI (Gemini), sends the request, and parses the AI's response into `PlanStep` objects.
    *   **Snippets:**
        ```python
        prompt = self._build_planning_prompt(goal, context)
        api_request = GeminiRequest(prompt=prompt, max_tokens=4000)
        response = await gemini_client.generate_text(api_request)
        plan = self._parse_plan_response(response.text, goal, context)
        ```

3.  **`def _build_planning_prompt(self, goal: str, context: Dict[str, Any]) -> str:`**
    *   **Name:** `_build_planning_prompt`
    *   **Purpose:** Constructs the specific prompt string to send to the AI when requesting a *basic* plan. The prompt instructs the AI to break the goal into shell commands and provide explanations, dependencies, and risk levels in a specific JSON format.
    *   **Snippets:**
        ```python
        prompt = f"""
You are Angela, an AI terminal assistant. Your task is to create a detailed plan for achieving the following goal:
GOAL: {goal}
{context_str} # Context like CWD, project type, files
Format your response as JSON:
{{
  "steps": [ # ... step structure for basic plan ... ]
}}
"""
        ```

4.  **`def _parse_plan_response(self, response: str, goal: str, context: Dict[str, Any]) -> TaskPlan:`**
    *   **Name:** `_parse_plan_response`
    *   **Purpose:** Parses the JSON response received from the AI (for a *basic* plan request) and converts it into a `TaskPlan` Pydantic model. It handles potential errors by creating a fallback plan.
    *   **Snippets:**
        ```python
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        # ... extract json_str ...
        plan_data = json.loads(json_str)
        ```
        ```python
        steps = []
        for step_data in plan_data.get("steps", []):
            step = PlanStep(**step_data) # Create PlanStep model
            steps.append(step)
        return TaskPlan(goal=goal, steps=steps, context=context)
        ```

5.  **`async def _execute_basic_plan(self, plan: TaskPlan, dry_run: bool = False, transaction_id: Optional[str] = None) -> List[Dict[str, Any]]:`**
    *   **Name:** `_execute_basic_plan`
    *   **Purpose:** Executes the steps of a `TaskPlan` sequentially. For each step, it uses `execution_engine.execute_command`. If a `transaction_id` is provided and the command succeeds, it records the execution with a `rollback_manager`.
    *   **Snippets:**
        ```python
        for i, step in enumerate(plan.steps):
            result = await execution_engine.execute_command(
                command=step.command, check_safety=True, dry_run=dry_run
            )
        ```
        ```python
        if not dry_run and transaction_id and result[2] == 0: # return_code == 0
            await rollback_manager.record_command_execution(...)
        ```

6.  **`async def _generate_advanced_plan(self, goal: str, context: Dict[str, Any]) -> AdvancedTaskPlan:`**
    *   **Name:** `_generate_advanced_plan`
    *   **Purpose:** Generates an `AdvancedTaskPlan` (which can include branching, different step types, etc.) for a given goal. It builds a specific prompt for advanced planning, calls the AI, and parses the response.
    *   **Snippets:**
        ```python
        prompt = self._build_advanced_planning_prompt(goal, context)
        api_request = GeminiRequest(prompt=prompt, max_tokens=4000)
        api_response = await gemini_client.generate_text(api_request)
        plan = self._parse_advanced_plan_response(api_response.text, goal, context)
        ```

7.  **`def _build_advanced_planning_prompt(self, goal: str, context: Dict[str, Any]) -> str:`**
    *   **Name:** `_build_advanced_planning_prompt`
    *   **Purpose:** Constructs the prompt string for requesting an *advanced* plan from the AI. This prompt asks for a more sophisticated plan structure, including different step types (command, file, decision, loop, code, API), dependencies, and entry points, all formatted as JSON.
    *   **Snippets:**
        ```python
        prompt = f"""
You are Angela, an AI terminal assistant with advanced planning capabilities...
GOAL: {goal}
{context_str}
Format your response as JSON:
{{
  "id": "generate a unique plan ID",
  "steps": {{ # Note: steps is a dictionary here, keyed by step ID
    "step1": {{ "type": "command", ... }},
    "step3": {{ "type": "decision", "condition": "...", "true_branch": ["step4a"], ... }}
    # ... other advanced step types ...
  }},
  "entry_points": ["step1"]
}}
"""
        ```

8.  **`def _parse_advanced_plan_response(self, response: str, goal: str, context: Dict[str, Any]) -> AdvancedTaskPlan:`**
    *   **Name:** `_parse_advanced_plan_response`
    *   **Purpose:** Parses the JSON response from the AI for an *advanced* plan request and converts it into an `AdvancedTaskPlan` Pydantic model.
    *   **Snippets:**
        ```python
        # ... (similar JSON extraction as _parse_plan_response) ...
        plan_data = json.loads(json_str)
        return AdvancedTaskPlan(
            id=plan_data.get("id", ...),
            goal=goal,
            description=plan_data.get("description", ...),
            steps=plan_data["steps"], # Expects a dict of steps
            entry_points=plan_data.get("entry_points", ...),
            # ...
        )
        ```

9.  **`async def _execute_advanced_plan(self, plan: AdvancedTaskPlan, dry_run: bool = False, transaction_id: Optional[str] = None) -> Dict[str, Any]:`**
    *   **Name:** `_execute_advanced_plan`
    *   **Purpose:** Executes an `AdvancedTaskPlan`. This implementation is more complex than `_execute_basic_plan` as it needs to handle dependencies and potentially different step types (though the provided snippet mainly shows command execution and a placeholder for other types). It iterates through executable steps based on satisfied dependencies.
    *   **Snippets:**
        ```python
        while pending_steps:
            # Find steps that can be executed (all dependencies satisfied)
            if all(dep in completed_steps for dep in step.dependencies):
                executable_steps[step_id] = step
        ```
        ```python
        if step.type == "command":
            result = await execution_engine.execute_command(...)
            # ... record transaction ...
        else:
            # Unsupported step type in this specific snippet
            execution_result = { "error": f"Unsupported step type: {step.type}", "success": False }
        ```

10. **`def _select_next_step(self, plan: AdvancedTaskPlan, pending_steps: Set[str], executed_steps: Set[str]) -> Optional[str]:`**
    *   **Name:** `_select_next_step`
    *   **Purpose:** (This method is part of the `TaskPlanner` but seems intended for use with `AdvancedTaskPlan` execution logic). It iterates through `pending_steps` and returns the ID of the first step whose dependencies (listed in `step.dependencies`) are all present in `executed_steps`.
    *   **Snippets:**
        ```python
        for step_id in pending_steps:
            step = plan.steps[step_id]
            if all(dep in executed_steps for dep in step.dependencies):
                return step_id
        return None
        ```

11. **`async def _execute_step(self, step: AdvancedPlanStep, previous_results: Dict[str, Dict[str, Any]], dry_run: bool) -> Dict[str, Any]:`**
    *   **Name:** `_execute_step`
    *   **Purpose:** (This method is part of the `TaskPlanner` but seems to be a more detailed, type-aware execution logic for a single `AdvancedPlanStep`. It's likely an alternative or more granular version of parts of `_execute_advanced_plan`). It dispatches execution based on `step.type` (COMMAND, FILE, CODE, DECISION, API, LOOP) and handles dry runs and retries. **Note:** Some step type executions are placeholders (e.g., CODE, LOOP, API).
    *   **Snippets:**
        ```python
        if step.type == PlanStepType.COMMAND:
            stdout, stderr, return_code = await execution_engine.execute_command(...)
        elif step.type == PlanStepType.FILE:
            if step.file_content: await self._write_file(...)
            else: content = await self._read_file(...)
        elif step.type == PlanStepType.DECISION:
            condition_result = await self._evaluate_condition(...)
        # ... (other types with placeholders) ...
        ```
        ```python
        if step.retry and step.retry > 0:
            # ... retry logic (simplified in snippet) ...
            retry_result = await self._execute_step(step, previous_results, dry_run)
        ```

12. **`def _update_pending_steps(self, plan: AdvancedTaskPlan, executed_step: AdvancedPlanStep, result: Dict[str, Any], pending_steps: Set[str], executed_steps: Set[str]) -> None:`**
    *   **Name:** `_update_pending_steps`
    *   **Purpose:** (Part of `TaskPlanner`, for `AdvancedTaskPlan` execution). After a step is executed, this method updates the `pending_steps` set. If the executed step was a DECISION, it adds steps from the true/false branch. For other steps, it checks if any other steps in the plan depended on the just-executed step and if all their *other* dependencies are now also met, adding them to `pending_steps`.
    *   **Snippets:**
        ```python
        if executed_step.type == PlanStepType.DECISION:
            condition_result = result.get("condition_result", False)
            if condition_result and executed_step.true_branch:
                pending_steps.add(step_id_from_true_branch)
            # ...
        ```
        ```python
        # For normal steps, add all steps that depend on this one
        for step_id, step in plan.steps.items():
            if executed_step.id in step.dependencies and ... : # and all other deps met
                pending_steps.add(step_id)
        ```

13. **`async def _read_file(self, path: str) -> str:`** and **`async def _write_file(self, path: str, content: str) -> bool:`**
    *   **Name(s):** `_read_file`, `_write_file`
    *   **Purpose:** Helper methods that wrap file system operations (reading and writing files), likely by calling functions from `angela.execution.filesystem`.
    *   **Snippets:**
        ```python
        # _read_file
        from angela.execution.filesystem import read_file
        return await read_file(path)
        ```
        ```python
        # _write_file
        from angela.execution.filesystem import write_file
        return await write_file(path, content)
        ```

14. **`async def _execute_code(self, code: str) -> Dict[str, Any]:`**
    *   **Name:** `_execute_code`
    *   **Purpose:** Placeholder for executing arbitrary code. The comment explicitly states it would need a sandboxed environment in a real system.
    *   **Snippets:**
        ```python
        return {
            "message": f"Code execution not implemented: {len(code)} characters",
            "success": True
        }
        ```

15. **`async def _evaluate_condition(self, condition: str, previous_results: Dict[str, Dict[str, Any]], dry_run: bool) -> bool:`**
    *   **Name:** `_evaluate_condition` (This is a different `_evaluate_condition` than in `ComplexWorkflowPlanner`)
    *   **Purpose:** Placeholder for evaluating a condition string. It has some very basic regex checks for "file exists" and "command success" (based on `previous_results`).
    *   **Snippets:**
        ```python
        if re.search(r'file exists', condition, re.IGNORECASE):
            # ... extract file_path and check Path(file_path).exists() ...
        ```
        ```python
        if re.search(r'command success', condition, re.IGNORECASE):
            # ... extract step_id and check previous_results.get(step_id, {}).get("success", False) ...
        ```

16. **`async def _execute_api_call(self, url: str, method: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:`**
    *   **Name:** `_execute_api_call`
    *   **Purpose:** Placeholder for making an API call.
    *   **Snippets:**
        ```python
        return {
            "message": f"API call not implemented: {method} {url}",
            "success": True
        }
        ```
task_planner = TaskPlanner()
