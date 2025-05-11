Okay, let's dive into the `orchestrator.py` file and break down each function's role, purpose, job, and a typical scenario.

Remember, the **Orchestrator** is the central coordinator. It receives user requests, figures out what kind of request it is, gathers necessary information (context), delegates to specialized modules (AI, planners, execution engines), and then presents the result to the user.

---

**File: `angela/orchestrator.py`**

**Class: `Orchestrator`**

*   **`__init__(self)`**
    *   **Purpose:** To initialize the Orchestrator instance.
    *   **Job:**
        *   Sets up a logger (`self._logger`).
        *   Initializes a set to keep track of background tasks (`self._background_tasks`), although it's not heavily used in the provided snippet for this specific class but might be intended for future use or by inherited classes.
        *   Initializes `self._error_recovery_manager` to `None`. This will be lazily loaded when needed to avoid circular dependencies.
        *   Initializes `self._background_monitor` and `self._network_monitor` by assigning the global instances.
        *   Crucially, it registers a callback (`self._handle_monitoring_insight`) with the `_background_monitor`. This means whenever the background monitor detects something interesting (like low disk space, or a Git status change), it will call this orchestrator's method.
    *   **Scenario:** This function is called once when the `orchestrator` global instance is created (usually at application startup). It sets up the basic state for the orchestrator.

*   **`_get_error_recovery_manager(self)`**
    *   **Purpose:** To provide access to the `ErrorRecoveryManager` instance, loading it lazily if it hasn't been loaded yet.
    *   **Job:**
        1.  Checks if `self._error_recovery_manager` is already initialized.
        2.  If not, it imports `ErrorRecoveryManager` from `angela.execution.error_recovery` and creates an instance.
        3.  Returns the instance.
    *   **Scenario:** When a multi-step plan execution fails, a method within the orchestrator (or a planner it calls) might need the `ErrorRecoveryManager` to attempt to fix the issue. It would call `self._get_error_recovery_manager()` to get the manager instance. This lazy loading helps prevent circular import issues if `ErrorRecoveryManager` itself needs components that are initialized around the same time as the orchestrator.

*   **`async def process_request(self, request: str, execute: bool = True, dry_run: bool = False) -> Dict[str, Any]`**
    *   **Purpose:** This is the **main public entry point** for the Orchestrator. It takes a raw user request and processes it through Angela's entire pipeline.
    *   **Job:**
        1.  **Context Gathering:** Refreshes and enriches the current context (CWD, project info, session data, resolved file references from the request). This uses `context_manager`, `session_manager`, `context_enhancer`, and `file_resolver`.
        2.  **Request Typing:** Calls `self._determine_request_type()` to figure out what kind of task the user is asking for (e.g., simple command, multi-step operation, file manipulation, code generation).
        3.  **Delegation:** Based on the `request_type`, it calls the appropriate internal processing method (e.g., `_process_command_request`, `_process_multi_step_request`, etc.).
        4.  **Error Handling:** Includes a top-level `try...except` block to catch any unhandled exceptions during processing and return a user-friendly error.
    *   **Scenario:** This is called by `cli/main.py` whenever the user types `angela request "..."`.
        *   User: `angela request "list all python files in src"`
        *   `cli/main.py` calls `orchestrator.process_request("list all python files in src")`.
        *   The orchestrator gathers context (e.g., current project is a Python project).
        *   It determines the request type is likely `RequestType.COMMAND`.
        *   It calls `self._process_command_request(...)`.
        *   The result from `_process_command_request` (which includes the AI's suggested command, explanation, and execution output) is returned.

*   **`async def _determine_request_type(self, request: str, context: Dict[str, Any]) -> RequestType`**
    *   **Purpose:** To analyze the user's natural language request and the current context to classify what kind of operation Angela should perform.
    *   **Job:**
        1.  Uses a series of regular expression patterns to check for keywords and structures indicative of different request types (e.g., "create workflow", "analyze file content", "setup ci/cd", "docker build").
        2.  The order of checks is important, as more specific patterns (like CI/CD or Docker) are checked before more general ones (like multi-step or simple command).
        3.  It considers the presence of tool names (git, docker, aws) to identify `RequestType.UNIVERSAL_CLI` or `RequestType.COMPLEX_WORKFLOW`.
    *   **Scenario:**
        *   Request: `"create a new python project"` -> Matches `code_generation_patterns` -> Returns `RequestType.CODE_GENERATION`.
        *   Request: `"show me the docker logs for my_container"` -> Matches `docker_patterns` -> Returns `RequestType.TOOLCHAIN_OPERATION` (which then gets further processed, or could be `RequestType.UNIVERSAL_CLI` if Docker isn't a primary toolchain operation type yet).
        *   Request: `"what is the meaning of life"` -> Doesn't match specific patterns, might fall through to `RequestType.COMMAND` (where AI might just say it can't help) or `RequestType.UNKNOWN`.

*   **`async def _process_command_request(self, request: str, context: Dict[str, Any], execute: bool, dry_run: bool) -> Dict[str, Any]`**
    *   **Purpose:** To handle requests that are likely to result in a single shell command.
    *   **Job:**
        1.  Analyzes the intent using `intent_analyzer`.
        2.  Checks command history for similar past requests using `history_manager`.
        3.  Calls `self._get_ai_suggestion()` to get a command, explanation, etc., from the LLM.
        4.  Scores the confidence of the suggestion using `confidence_scorer`.
        5.  If confidence is low and not a dry run, it might ask the user for clarification/confirmation before proceeding.
        6.  If `execute` is true or `dry_run` is true, it uses the `adaptive_engine` to execute (or simulate) the command. The adaptive engine handles safety checks and its own confirmation prompts.
        7.  If execution fails, it uses `error_analyzer` to diagnose the error and suggest fixes.
        8.  May trigger background monitoring for failed commands.
    *   **Scenario:** User types `angela request "list files sorted by size"`.
        *   Orchestrator determines `RequestType.COMMAND`.
        *   This function gets an AI suggestion like `ls -lahS`.
        *   Confidence is scored.
        *   `adaptive_engine` executes `ls -lahS`.
        *   The output, command, explanation, etc., are packaged and returned.

*   **`async def _process_multi_step_request(self, request: str, context: Dict[str, Any], execute: bool, dry_run: bool) -> Dict[str, Any]`**
    *   **Purpose:** To handle requests that require a sequence of operations or more complex logic than a single command. This version is specifically designed to integrate with the `EnhancedTaskPlanner` and `ComplexWorkflowPlanner` for advanced plan execution with rollback.
    *   **Job:**
        1.  Determines the complexity of the request (simple vs. advanced) using `task_planner._determine_complexity()`.
        2.  **Starts a rollback transaction** using `rollback_manager` if not a dry run. This is key for undoing multi-step operations.
        3.  If "advanced" complexity:
            *   Uses `task_planner.plan_task()` (which now points to `EnhancedTaskPlanner` or `SemanticTaskPlanner`) to generate an `AdvancedTaskPlan`.
            *   Records the plan itself in the rollback transaction.
            *   Calls `self._handle_advanced_plan_execution()` (a method patched in by `enhanced_planner_integration.py`) to display and execute this advanced plan. This execution will involve the `EnhancedTaskPlanner`'s logic for handling various step types (COMMAND, CODE, API, LOOP, DECISION).
        4.  If "simple" complexity:
            *   Uses `task_planner.plan_task()` to generate a basic `TaskPlan`.
            *   Calls `self._process_basic_multi_step()` to handle its execution.
        5.  **Ends the rollback transaction** with a status of "completed", "failed", or "cancelled" based on the outcome.
        6.  Catches exceptions to ensure the transaction is properly ended.
    *   **Scenario:** User: `angela request "git pull, then if there are no conflicts, run npm install, and finally run npm start"`.
        *   Orchestrator determines `RequestType.MULTI_STEP` (or `COMPLEX_WORKFLOW`).
        *   This function determines "advanced" complexity.
        *   A transaction is started.
        *   An `AdvancedTaskPlan` is generated with steps for `git pull`, a `DECISION` step checking for conflicts, and conditional branches for `npm install` and `npm start`.
        *   `_handle_advanced_plan_execution` (via the integration) executes this plan, with each successful command being recorded in the transaction.
        *   The transaction is ended.

*   **`async def _process_basic_multi_step(self, plan: TaskPlan, request: str, context: Dict[str, Any], execute: bool, dry_run: bool, transaction_id: Optional[str]) -> Dict[str, Any]`**
    *   **Purpose:** To handle the execution of simpler, sequential multi-step plans (`TaskPlan`).
    *   **Job:**
        1.  Records the plan in the rollback transaction (if `transaction_id` is provided).
        2.  Displays the plan to the user using `terminal_formatter`.
        3.  Asks for user confirmation to execute the plan (unless `dry_run`).
        4.  If confirmed, it uses `task_planner.execute_plan()` (which for basic `TaskPlan`s will call `_execute_basic_plan` in `intent/planner.py`) to run the steps. Each successful command within this execution is also recorded in the transaction by the `TaskPlanner`.
        5.  Updates the transaction status.
        6.  If execution fails and not a dry run, it attempts error recovery using `self._handle_execution_errors()`.
    *   **Scenario:** User: `angela request "create a directory 'temp', then create a file 'test.txt' inside it"`.
        *   Orchestrator determines `RequestType.MULTI_STEP`.
        *   `_process_multi_step_request` might determine "simple" complexity.
        *   A `TaskPlan` is generated: 1. `mkdir temp`, 2. `touch temp/test.txt`.
        *   This function is called, displays the two steps, asks for confirmation, and then executes them sequentially.

*   **`async def _process_file_content_request(self, request: str, context: Dict[str, Any], execute: bool, dry_run: bool) -> Dict[str, Any]`**
    *   **Purpose:** To handle requests related to analyzing, summarizing, searching, or manipulating the content of a specific file.
    *   **Job:**
        1.  **Starts a rollback transaction** if `execute` is true and not `dry_run`, as manipulations are involved.
        2.  Uses `self._extract_file_path()` (which uses `file_resolver`) to identify the target file from the request.
        3.  Calls `self._determine_file_operation_type()` to figure out if the user wants to "analyze", "summarize", "search", or "manipulate" the file.
        4.  Delegates to the appropriate method in `ai/content_analyzer.py`:
            *   `content_analyzer.analyze_content()`
            *   `content_analyzer.summarize_content()`
            *   `content_analyzer.search_content()`
            *   `content_analyzer.manipulate_content()`
        5.  For "manipulate":
            *   If `execute` and not `dry_run`, it gets confirmation for the changes (showing a diff).
            *   If confirmed, it records the content manipulation for rollback (original content/diff) using `rollback_manager`.
            *   Writes the modified content to the file.
        6.  **Ends the rollback transaction** appropriately.
    *   **Scenario:** User: `angela request "in my_script.py, change all 'foo' to 'bar'"`
        *   Orchestrator determines `RequestType.FILE_CONTENT`.
        *   This function identifies `my_script.py` and operation type "manipulate".
        *   `content_analyzer.manipulate_content()` gets the original content, asks AI to change "foo" to "bar", and returns the original, modified content, and a diff.
        *   The user is shown the diff and asked to confirm.
        *   If confirmed, the change is written to `my_script.py`, and the original content/diff is logged for rollback.

*   **`async def _process_workflow_definition(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]`**
    *   **Purpose:** To handle requests where the user wants to create a new named workflow.
    *   **Job:**
        1.  Calls `self._extract_workflow_info()` (uses AI) to get the desired workflow name, description, and a natural language description of its steps from the user's request.
        2.  Calls `workflow_manager.define_workflow_from_natural_language()` to:
            *   Convert the natural language steps into a sequence of command steps (using `task_planner`).
            *   Identify potential variables in these steps.
            *   Save the new workflow definition.
    *   **Scenario:** User: `angela request "define a workflow called 'daily_backup' that zips my /docs folder and copies it to /backups"`
        *   Orchestrator determines `RequestType.WORKFLOW_DEFINITION`.
        *   This function extracts name "daily_backup", description, and steps "zips /docs, copies to /backups".
        *   `workflow_manager` converts "zips /docs..." into commands like `zip -r docs_backup.zip /docs` and `cp docs_backup.zip /backups`, then saves this as the "daily_backup" workflow.

*   **`async def _process_workflow_execution(self, request: str, context: Dict[str, Any], execute: bool, dry_run: bool) -> Dict[str, Any]`**
    *   **Purpose:** To handle requests to run an existing, named workflow.
    *   **Job:**
        1.  Calls `self._extract_workflow_execution_info()` (uses AI) to get the name of the workflow to run and any variable values provided by the user (e.g., "run backup_docs with target_dir=/mnt/external").
        2.  Retrieves the named workflow from `workflow_manager`.
        3.  If `execute` or `dry_run`, it displays the workflow steps (with variables substituted) using `terminal_formatter`.
        4.  Asks for user confirmation.
        5.  If confirmed, calls `workflow_manager.execute_workflow()`, which converts the workflow into a `TaskPlan` and runs it.
    *   **Scenario:** User: `angela request "run my 'deploy_staging' workflow with version=1.2.3"`
        *   Orchestrator determines `RequestType.WORKFLOW_EXECUTION`.
        *   This function extracts name "deploy_staging" and variable `version="1.2.3"`.
        *   It retrieves the "deploy_staging" workflow, shows its steps with "1.2.3" substituted, asks for confirmation, and then executes it.

*   **`async def _process_clarification_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]`**
    *   **Purpose:** To handle situations where the user is asking Angela for more information or to explain something.
    *   **Job:**
        1.  Gathers context, especially recent commands from the session.
        2.  Builds a prompt asking the AI to provide a helpful clarification based on the user's question and the recent interaction history.
        3.  Returns the AI's explanation.
    *   **Scenario:**
        *   Angela suggests: `find . -type f -print0 | xargs -0 sed -i 's/old/new/g'`
        *   User: `angela request "what does -print0 and -0 do?"`
        *   Orchestrator determines `RequestType.CLARIFICATION`.
        *   This function sends the question and the previous command to the AI, which then explains the purpose of `-print0` and `-0`.

*   **`async def _process_unknown_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]`**
    *   **Purpose:** To provide a graceful fallback when Angela cannot determine a specific type for the user's request.
    *   **Job:** Builds a generic prompt asking the AI to provide a helpful response or suggest what kind of operations might be relevant to the user's (unclear) request.
    *   **Scenario:** User types `angela request "the internet is a series of tubes"`.
        *   Orchestrator determines `RequestType.UNKNOWN`.
        *   This function asks the AI for a general helpful response. The AI might say it can't help with philosophical statements but can assist with network commands.

*   **`async def _get_ai_suggestion(self, request: str, context: Dict[str, Any], similar_command: Optional[str] = None, intent_result: Optional[Any] = None) -> CommandSuggestion`**
    *   **Purpose:** A helper method to encapsulate the logic of getting a command suggestion from the AI.
    *   **Job:**
        1.  Calls `build_prompt` (from `ai/prompts.py`) to construct the prompt, including the user's request, current context, any similar past command, and the result of intent analysis.
        2.  Sends this prompt to the `GeminiClient`.
        3.  Parses the AI's JSON response into a `CommandSuggestion` object using `parse_ai_response`.
    *   **Scenario:** This is called by `_process_command_request` and potentially other methods when they need the AI to translate natural language into a shell command.

*   **`async def _extract_file_path(self, request: str, context: Dict[str, Any]) -> Optional[Path]`**
    *   **Purpose:** To reliably identify a file path mentioned in a user's request.
    *   **Job:**
        1.  First, it uses `file_resolver.extract_references()` to find any potential file names or paths in the request and try to resolve them.
        2.  If resolved paths are found, it returns the first one and tracks it as viewed.
        3.  If references are found but not resolved, it tries resolving them again with a broader scope (e.g., entire project).
        4.  If `file_resolver` fails, it falls back to simpler regex patterns to find file-like strings in the request and checks if they exist in the CWD or project root.
    *   **Scenario:** Called by `_process_file_content_request` to determine which file the user wants to work on. If the user says "summarize my main script", this function tries to find "main.py" or similar.

*   **`async def _determine_file_operation_type(self, request: str) -> str`**
    *   **Purpose:** To figure out if a file-related request is for analysis, summarization, search, or manipulation.
    *   **Job:** Checks the (lowercase) request string for keywords associated with each operation type (e.g., "change", "modify" for manipulation; "summarize", "overview" for summarization; "find", "search" for search). Defaults to "analyze".
    *   **Scenario:** Called by `_process_file_content_request`.
        *   Request: "change foo to bar in config.json" -> Returns "manipulate".
        *   Request: "give me a summary of readme.md" -> Returns "summarize".

*   **`async def _extract_workflow_info(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]`**
    *   **Purpose:** To parse a user's request for defining a new workflow and extract its name, description, and the natural language description of its steps.
    *   **Job:** Sends a prompt to the AI asking it to identify these components from the user's request and return them as JSON.
    *   **Scenario:** Called by `_process_workflow_definition`. User says "create a workflow called daily_sync to copy /data to /backup and then send an email". This function asks AI to extract `name="daily_sync"`, `description="copies data and sends email"`, `steps="copy /data to /backup and then send an email"`.

*   **`async def _extract_workflow_execution_info(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]`**
    *   **Purpose:** To parse a user's request for running a workflow and extract the workflow's name and any variables the user provided.
    *   **Job:** Sends a prompt to the AI, including a list of available workflows. Asks the AI to identify the target workflow name and any key-value variable pairs from the user's request.
    *   **Scenario:** Called by `_process_workflow_execution`. User says "run backup_docs with target_server=server1". This function asks AI to extract `name="backup_docs"` and `variables={"target_server": "server1"}`.

*   **`async def _display_plan(self, plan: Any) -> None`**
    *   **Purpose:** Helper to display a basic `TaskPlan` using the `terminal_formatter`.
    *   **Job:** Calls `terminal_formatter.display_task_plan(plan)`.
    *   **Scenario:** Used by `_process_basic_multi_step` to show the user the planned steps.

*   **`async def _confirm_plan_execution(self, plan: Any, dry_run: bool) -> bool`**
    *   **Purpose:** Helper to get user confirmation before executing a basic `TaskPlan`.
    *   **Job:** Checks if any steps are high-risk. If so, shows a warning. Then asks the user "Do you want to execute this N-step plan?".
    *   **Scenario:** Used by `_process_basic_multi_step` after displaying the plan.

*   **`async def _display_workflow(self, workflow: Any, variables: Dict[str, Any]) -> None`**
    *   **Purpose:** Helper to display a defined `Workflow` (from `workflows/manager.py`) using the `terminal_formatter`, substituting any provided variables into the command display.
    *   **Job:** Calls `terminal_formatter.display_workflow(workflow, variables)`.
    *   **Scenario:** Used by `_process_workflow_execution` to show the user the workflow they are about to run.

*   **`async def _confirm_workflow_execution(self, workflow: Any, variables: Dict[str, Any], dry_run: bool) -> bool`**
    *   **Purpose:** Helper to get user confirmation before executing a defined `Workflow`.
    *   **Job:** Checks if any steps in the workflow require confirmation. If so, shows a warning. Then asks the user "Do you want to execute workflow 'workflow_name'?".
    *   **Scenario:** Used by `_process_workflow_execution` after displaying the workflow.

*   **`async def _confirm_file_changes(self, file_path: Path, diff: str) -> bool`**
    *   **Purpose:** Helper to get user confirmation before applying AI-generated changes to a file.
    *   **Job:** Displays the diff of proposed changes using `rich.Syntax` and asks "Do you want to apply these changes to file_path?".
    *   **Scenario:** Used by `_process_file_content_request` when the operation type is "manipulate" and changes have been generated.

*   **`def _start_background_monitoring(self, command: str, error_analysis: Dict[str, Any]) -> None`**
    *   **Purpose:** To initiate background monitoring for a failed command, potentially to offer further assistance or track if the user tries a fix.
    *   **Job:** Creates an `asyncio.task` to run `self._monitor_for_suggestions` in the background. This task has a timeout and will be cleaned up when done or if it errors.
    *   **Scenario:** Called by `_process_command_request` if a command fails and error analysis is available.

*   **`async def _monitor_for_suggestions(self, command: str, error_analysis: Dict[str, Any]) -> None`**
    *   **Purpose:** The actual background task that might offer suggestions after a command failure.
    *   **Job:** Waits a couple of seconds (to let the user see the initial error). Then, if it has fix suggestions from the `error_analysis`, it prints the top few to the console, along with instructions on how to try them using Angela (e.g., "angela try fix 1").
    *   **Scenario:** Runs in the background after a command fails. If the user doesn't immediately try something else, this might pop up with suggestions.

*   **`async def process_file_operation(self, operation: str, parameters: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]`**
    *   **Purpose:** A dedicated method to handle direct requests for file system operations (as opposed to those inferred from natural language).
    *   **Job:** Directly calls `execute_file_operation` from `ai/file_integration.py` (which in turn uses `execution/filesystem.py`). This bypasses AI suggestion for the command itself but still goes through safety checks.
    *   **Scenario:** This might be used if another part of Angela programmatically decides a file operation needs to happen, or if a future CLI command like `angela files --ai-create "a text file named report.txt with 'hello' in it"` used AI to determine parameters but then called this method to execute.

*   **`async def _process_code_generation_request(...)`, `async def _process_feature_addition_request(...)`, `async def _process_toolchain_operation(...)`, `async def _process_code_refinement_request(...)`, `async def _process_code_architecture_request(...)`, `async def _process_universal_cli_request(...)`, `async def _process_complex_workflow_request(...)`, `async def _process_ci_cd_pipeline_request(...)`, `async def _process_proactive_suggestion(...)`**
    *   **Purpose:** These are specific handlers for the newer, more advanced `RequestType`s.
    *   **Job:** Each of these methods will:
        1.  Log that they are processing their specific type of request.
        2.  Delegate the core logic to the appropriate specialized module:
            *   `CODE_GENERATION` & `FEATURE_ADDITION` -> `generation/engine.py` (`code_generation_engine`)
            *   `TOOLCHAIN_OPERATION` -> Specific modules in `toolchain/` (like `docker.py`, `ci_cd.py`, `git.py`) or `UniversalCLITranslator`.
            *   `CODE_REFINEMENT` -> `review/feedback.py` (`feedback_manager`)
            *   `CODE_ARCHITECTURE` -> `generation/architecture.py` (`architectural_analyzer`)
            *   `UNIVERSAL_CLI` -> `toolchain/universal_cli.py` (or `enhanced_universal_cli.py`)
            *   `COMPLEX_WORKFLOW` & `CI_CD_PIPELINE` -> `intent/complex_workflow_planner.py` and `toolchain/` modules, often coordinated by `integrations/phase12_integration.py`.
            *   `PROACTIVE_SUGGESTION` -> Likely interacts with `monitoring/proactive_assistant.py` to present or act on a suggestion.
        3.  Handle the `execute` and `dry_run` flags appropriately for their operation.
        4.  Package the results from the specialized module into a consistent dictionary format.
    *   **Scenario (Code Generation):** User: `angela generate create-project "python web app"`.
        *   Orchestrator determines `RequestType.CODE_GENERATION`.
        *   `_process_code_generation_request` is called.
        *   It calls `code_generation_engine.generate_project(...)` to get a `CodeProject` plan.
        *   If `execute` is true, it calls `code_generation_engine.create_project_files(...)` to write the files.
    *   **Scenario (Universal CLI):** User: `angela request "use kubectl to get all pods in namespace 'dev'"`
        *   Orchestrator determines `RequestType.UNIVERSAL_CLI`.
        *   `_process_universal_cli_request` is called.
        *   It calls `universal_cli_translator.translate_request(...)` which might run `kubectl help get pods` to understand its options, then generate `kubectl get pods -n dev`.
        *   This command is then executed via `adaptive_engine`.

*   **`async def execute_command(...)` (redefined/overridden from a base or for specific internal use within Orchestrator):**
    *   **Purpose:** This seems to be a direct command execution method, likely used internally by the orchestrator when it needs to run a command that has already been confirmed or is part of an internal process. It's similar to the one in `AdaptiveExecutionEngine` but might have slight variations or be called at a different stage.
    *   **Job:**
        1.  Calls `execution_hooks.pre_execute_command`.
        2.  Performs risk classification and impact analysis.
        3.  Gets adaptive confirmation.
        4.  If confirmed, calls `self._execute_with_feedback` (which uses `execution_engine`).
        5.  Calls `execution_hooks.post_execute_command`.
        6.  Records in history.
        7.  Analyzes errors if any.
        8.  Offers command learning.
    *   **Scenario:** This might be called by `_process_universal_cli_request` after the `universal_cli_translator` has generated a command and it needs to be run through the full adaptive execution pipeline.

*   **`async def _handle_critical_resource_warning(self, warning_data: Dict[str, Any]) -> None`**
    *   **Purpose:** To react to critical resource warnings received from the monitoring system.
    *   **Job:** Logs the warning and then, based on the `resource_type` (memory, disk, cpu) and `severity`, it prints a warning message to the user's console suggesting potential actions (e.g., free up memory, clean disk, throttle processes).
    *   **Scenario:** `monitoring/background.py` detects disk space is at 95% and publishes an event or calls the registered callback. This function receives that data, sees `resource_type="disk"` and `severity="high"`, and prints a warning to the user like "Low disk space detected... Consider removing temporary files."

This covers the main functions within the `Orchestrator`. It's a complex class acting as the central nervous system for Angela, routing requests and coordinating many other components.
