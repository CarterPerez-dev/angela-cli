**AI Terminal Coder: Project Analysis**

This document provides a comprehensive analysis of the "AI Terminal Coder" project, based strictly on the provided codebase and directory structure. It aims to explain the project's architecture, components, logic, and workflows to a technical individual new to this codebase.

**1. High-Level Project Architecture & Purpose**

*   **Overall Goal & Purpose (Based on Code):**
    The primary goal derived from the code is to create a sophisticated command-line interface (CLI) application named "Angela" that acts as an AI-powered assistant. It interprets natural language user requests, translates them into executable plans (ranging from single shell commands to complex multi-step workflows involving code execution, API calls, and file operations), executes these plans safely within the user's terminal environment, and manages the context of the interaction. Key aspects include safety checks, user confirmation for risky operations, error recovery, context management (history, preferences, project structure), and integration with external tools like Git and package managers.

*   **Core Functionalities & Capabilities:**
    *   **Natural Language Processing:** Interprets user requests using an AI model (Google Gemini).
    *   **Command Generation & Execution:** Translates requests into shell commands and executes them via `execution/engine.py` and `execution/adaptive_engine.py`.
    *   **Task Planning:** Decomposes complex requests into multi-step plans (`intent/planner.py`, `intent/enhanced_task_planner.py`). Supports basic sequential plans and advanced plans with dependencies, conditions, loops, code execution, and API calls.
    *   **Context Management:** Maintains awareness of the current working directory, Git project root/type, command history, user preferences, and session state (`context/`). Includes advanced context enhancement (`context/enhancer.py`) using project inference (`context/project_inference.py`), file activity tracking (`context/file_activity.py`), and reference resolution (`context/file_resolver.py`).
    *   **Safety & Confirmation:** Classifies command risk (`safety/classifier.py`), validates operations (`safety/validator.py`), and uses an adaptive confirmation system based on risk and user history/preferences (`safety/adaptive_confirmation.py`). Includes command previews (`safety/preview.py`).
    *   **File System Operations:** Provides an abstraction layer for safe file/directory operations (create, read, write, delete, copy, move) with rollback capability (`execution/filesystem.py`, `execution/rollback.py`).
    *   **Code Generation & Manipulation:** Generates project structures, code files for various frameworks (`generation/`), documentation (`generation/documentation.py`), and refines code based on feedback (`review/feedback.py`). Includes code validation (`generation/validators.py`).
    *   **Rollback:** Supports undoing operations and entire transactions (`execution/rollback.py`, `execution/rollback_commands.py`).
    *   **Workflow Management:** Allows users to define, save, execute, import, and export reusable command sequences (`workflows/`).
    *   **Toolchain Integration:** Interacts with Git (`toolchain/git.py`), package managers (`toolchain/package_managers.py`), and CI/CD systems (`toolchain/ci_cd.py`).
    *   **Monitoring:** Includes modules for background monitoring of network and system status (`monitoring/`).
    *   **Rich CLI:** Provides a user-friendly interface using Typer and Rich (`cli/`, `shell/`).

*   **Architectural Pattern(s):**
    The architecture is best described as a **Modular Monolith**. While it's a single application, it's clearly divided into distinct functional modules (`ai`, `context`, `execution`, `safety`, `generation`, `intent`, `toolchain`, etc.) with relatively well-defined responsibilities.
    *   **Layered:** There's a clear layering: CLI -> Orchestrator -> Intent/Planning -> Execution/AI -> System Interaction.
    *   **Service Locator:** The `core/registry.py` acts as a simple service locator pattern to decouple components and manage dependencies (e.g., accessing `rollback_manager` or `execution_engine` without direct imports everywhere).
    *   **Component-Based:** Each directory under `angela/` represents a major component.
    *   **Event-Driven (Conceptual):** User input triggers a processing pipeline, but it doesn't use a formal event bus/queue system.
    *   **Orchestration:** The `Orchestrator` class plays a central role in coordinating the flow between different modules.

*   **Key Technology Choices:**
    *   **Language:** Python (>=3.9, based on `pyproject.toml`)
    *   **AI Model:** Google Gemini (via `google-generativeai` library)
    *   **CLI Framework:** Typer
    *   **Rich Terminal UI:** Rich
    *   **Data Validation/Modeling:** Pydantic
    *   **Asynchronous Programming:** `asyncio` is used extensively for I/O-bound tasks (API calls, command execution).
    *   **Configuration:** TOML (`config.toml`), `.env` files (via `python-dotenv`)
    *   **Logging:** Loguru
    *   **Shell Integration:** Custom Bash and Zsh scripts.
    *   **HTTP Client:** `aiohttp` (for API steps in advanced planner)
    *   **Build/Package:** Setuptools, Pip, Make (`Makefile`)
    *   **Testing:** Pytest, pytest-asyncio

**2. Directory and File Structure Breakdown**

*   **(Root Directory)**
    *   **Purpose:** Contains the main project configuration, documentation, scripts, and the core `angela` package.
    *   **Files:** `.env.example`, `.gitignore`, `Makefile`, `pyproject.toml`, `pytest.ini`, `README.md`, `requirements.txt`, `setup.py`.
    *   **Subdirectories:** `angela/`, `integrations/`, `MD/`, `scripts/`, `tests/` (implicitly, though excluded).

*   **`angela/`**
    *   **Purpose:** The main Python package containing all the application's source code.
    *   **Files:** `__init__.py` (initializes application), `__main__.py` (main entry point), `config.py`, `constants.py`, `orchestrator.py`.
    *   **Subdirectories:** `ai/`, `cli/`, `context/`, `core/`, `execution/`, `generation/`, `intent/`, `interfaces/`, `monitoring/`, `review/`, `safety/`, `shell/`, `toolchain/`, `utils/`, `workflows/`.

*   **`angela/ai/`**
    *   **Purpose:** Handles all interactions with the AI model (Gemini), including prompt engineering, API calls, response parsing, intent analysis, and content analysis.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `analyzer.py`: (`ErrorAnalyzer`) Analyzes command errors, suggests fixes by matching patterns and checking command/file structure.
        *   `client.py`: (`GeminiClient`) Manages communication with the Google Gemini API, handles requests and responses.
        *   `confidence.py`: (`ConfidenceScorer`) Scores the AI's confidence in command suggestions based on history, complexity, and entity matching.
        *   `content_analyzer.py`: (`ContentAnalyzer`) Base class for understanding and manipulating file content using AI.
        *   `content_analyzer_extensions.py`: (`EnhancedContentAnalyzer`) Extends `ContentAnalyzer` with support for specific languages (TS, JSON, etc.) and file types. Routes analysis to specialized handlers.
        *   `file_integration.py`: Extracts file system operations (mkdir, rm, cp, mv, etc.) from command strings and provides functions to execute them via the `execution/filesystem.py` module.
        *   `intent_analyzer.py`: (`IntentAnalyzer`, `IntentAnalysisResult`) Performs enhanced Natural Language Understanding (NLU) on user requests, normalizes input, handles ambiguity, and extracts entities. Uses fuzzy matching.
        *   `parser.py`: (`CommandSuggestion`, `parse_ai_response`) Parses JSON responses from the AI into structured `CommandSuggestion` objects. Includes fallback logic.
        *   `prompts.py`: Centralizes prompt engineering. Contains templates and functions (`build_prompt`, `build_file_operation_prompt`, etc.) to construct detailed prompts for the AI, incorporating context (project info, history, file activity, etc.).

*   **`angela/cli/`**
    *   **Purpose:** Defines the command-line interface using Typer, handling user commands and arguments.
    *   **Files:**
        *   `__init__.py`: Initializes the CLI sub-package and registers subcommands.
        *   `files.py`: Defines file system operation commands (`ls`, `mkdir`, `rm`, `cp`, `mv`, `cat`, `write`, `find`, `info`) using `rich` for output and interacting with `execution/filesystem.py` and `context/manager.py`. Includes `rollback` command integration.
        *   `files_extensions.py`: Extends `files.py` with advanced commands (`resolve`, `extract`, `recent`, `active`, `project`) interacting with `context/file_resolver.py`, `context/file_activity.py`, and `context/enhancer.py`.
        *   `generation.py`: Defines CLI commands for code generation (`create-project`, `add-feature`, `refine-code`, `refine-project`, `generate-ci`, `generate-tests`) interacting with `generation/` and `toolchain/` modules.
        *   `main.py`: The main entry point for the Typer application. Defines the root command, global options (`--debug`, `--version`, `--monitor`), and the `request` command, which delegates processing to the `Orchestrator`. Also includes `init` and `status` commands.
        *   `workflows.py`: Defines CLI commands for managing workflows (`list`, `create`, `run`, `delete`, `show`, `export`, `import`) interacting with `workflows/manager.py` and `workflows/sharing.py`.

*   **`angela/context/`**
    *   **Purpose:** Manages the application's understanding of the user's environment, project state, history, and preferences.
    *   **Files:**
        *   `__init__.py`: Initializes the context package, exposes key components, and sets up background project inference.
        *   `enhancer.py`: (`ContextEnhancer`) Enriches the basic context with detailed project info (type, frameworks, dependencies, structure), recent file activity, and file references using other context modules. Includes caching.
        *   `file_activity.py`: (`ActivityType`, `FileActivity`, `FileActivityTracker`) Tracks file system events (create, modify, delete, view), stores activity history, and integrates with the session manager.
        *   `file_detector.py`: (`detect_file_type`, `get_content_preview`) Detects file types and programming languages based on extension, name, MIME type, and content (including shebangs). Provides content previews.
        *   `file_resolver.py`: (`FileResolver`) Resolves potentially ambiguous file references from natural language using exact paths, fuzzy matching, recent files, and context awareness. Extracts references from text.
        *   `history.py`: (`CommandRecord`, `CommandPattern`, `HistoryManager`) Manages command execution history (success/failure, output, errors), calculates command frequency/success rates, and identifies error/fix patterns. Persists history to JSON.
        *   `manager.py`: (`ContextManager`) Core context provider. Tracks CWD, detects project root/type using markers, manages current file context, provides directory listings and file info lookups. Caches file info.
        *   `preferences.py`: (`TrustPreferences`, `UIPreferences`, `ContextPreferences`, `UserPreferences`, `PreferencesManager`) Manages user settings (trust levels, auto-execution, UI behavior, history limits) stored in `preferences.json`.
        *   `project_inference.py`: (`ProjectInference`) Performs deep analysis of project directories to infer type, frameworks, dependencies, important files, and structure. Caches results.
        *   `session.py`: (`EntityReference`, `SessionMemory`, `SessionManager`) Manages short-term conversational memory, tracking entities (files, commands, results) mentioned or used within a session. Handles session expiration.

*   **`angela/core/`**
    *   **Purpose:** Provides core application utilities, like the service registry.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `registry.py`: (`ServiceRegistry`, `registry`) Implements a simple singleton service locator pattern to break circular dependencies between modules by allowing registration and retrieval of services by name.

*   **`angela/execution/`**
    *   **Purpose:** Handles the execution of shell commands and file system operations, including safety checks, rollback, and error recovery.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `adaptive_engine.py`: (`AdaptiveExecutionEngine`) Orchestrates command execution with context-awareness. Integrates risk classification, adaptive confirmation, feedback, history logging, and error analysis/recovery.
        *   `engine.py`: (`ExecutionEngine`) Core engine for running shell commands using `asyncio.create_subprocess_exec`. Captures stdout, stderr, and return code. Records successful operations for rollback.
        *   `error_recovery.py`: (`RecoveryStrategy`, `ErrorRecoveryManager`) Manages error recovery for multi-step plans. Analyzes errors, generates recovery strategies (retry, modify, alternative, etc.) using AI or predefined patterns, and handles guided/automatic recovery.
        *   `filesystem.py`: (`FileSystemError`, `_ensure_backup_dir`, `create_directory`, etc.) Provides high-level, safe functions for common file system operations (create, delete, read, write, copy, move). Includes safety checks and backup creation for rollback.
        *   `hooks.py`: (`ExecutionHooks`) Defines pre- and post-execution hooks for commands and file operations. Used to track file activities via `file_activity_tracker` based on command execution/output or direct file operations.
        *   `rollback.py`: (`OperationRecord`, `Transaction`, `RollbackManager`) Implements the enhanced, transaction-based rollback system. Records various operation types (filesystem, content, command, plan) with necessary undo information (backups, diffs, compensating actions). Manages transaction lifecycle and performs rollback of individual operations or entire transactions.
        *   `rollback_commands.py`: Defines CLI commands (`list`, `operation`, `transaction`, `last`) for interacting with the `RollbackManager`.

*   **`angela/generation/`**
    *   **Purpose:** Contains modules responsible for generating code, project structures, documentation, and related artifacts.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `architecture.py`: (`ArchitecturalPattern`, `AntiPattern`, `MvcPattern`, etc., `ArchitecturalAnalyzer`) Analyzes project architecture, detects patterns (like MVC) and anti-patterns (like Single Responsibility Violation, God Object), and suggests improvements using heuristics and AI.
        *   `documentation.py`: (`DocumentationGenerator`) Generates project documentation like READMEs, API docs (basic structure, relies on AI for details), user guides, and CONTRIBUTING guides using AI based on project analysis.
        *   `engine.py`: (`CodeFile`, `CodeProject`, `CodeGenerationEngine`) Core engine for generating multi-file code projects. Plans project structure (`_create_project_plan`), generates content for each file (`_generate_file_contents`) potentially using AI, manages dependencies, and creates the actual files. Also handles adding features to existing projects.
        *   `frameworks.py`: (`FrameworkGenerator`) Provides specialized generators for creating boilerplate project structures for specific frameworks (React, Next.js, Django, Flask, Spring, Express, FastAPI, Vue, Angular). Uses AI (`_generate_content`) for file content. Includes a generic fallback.
        *   `planner.py`: (`ProjectPlanner`, `ArchitectureComponent`, `ProjectArchitecture`) Focuses on planning the high-level architecture and structure of a *new* project before code generation begins, interacting with AI to design components and their relationships. (Note: Distinct from `intent/planner.py` which plans *tasks*).
        *   `validators.py`: (`validate_code`, `validate_python`, etc.) Provides functions to validate the syntax and basic correctness of generated code for various languages using external tools (like `py_compile`, `node --check`, `tsc`, `javac`) or basic checks.

*   **`angela/intent/`**
    *   **Purpose:** Deals with understanding user intent and planning sequences of actions to fulfill that intent.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `enhanced_task_planner.py`: (`StepExecutionContext`, `DataFlowVariable`, `ExecutionResult`, `EnhancedTaskPlanner`) Extends `TaskPlanner` to execute advanced plans. Manages complex step types (CODE, API, LOOP, DECISION), handles data flow between steps using variables, integrates error recovery, and includes secure code execution sandboxing.
        *   `models.py`: (`IntentType`, `Intent`, `ActionPlan`) Defines Pydantic models for representing user intent and basic action plans (primarily used by older/simpler parts of the system).
        *   `planner.py`: (`PlanStep`, `TaskPlan`, `PlanStepType`, `AdvancedPlanStep`, `AdvancedTaskPlan`, `TaskPlanner`) Core task planning module. Determines task complexity, generates basic (`TaskPlan`) or advanced (`AdvancedTaskPlan`) plans using AI, and provides basic plan execution logic. The `EnhancedTaskPlanner` inherits/replaces parts of this.

*   **`angela/interfaces/`**
    *   **Purpose:** Defines Abstract Base Classes (ABCs) to enforce contracts for key components, promoting modularity.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `execution.py`: (`CommandExecutor`, `AdaptiveExecutor`) Defines interfaces for command execution components.
        *   `safety.py`: (`SafetyValidator`) Defines interfaces for safety validation components.

*   **`angela/monitoring/`**
    *   **Purpose:** Implements background monitoring capabilities for proactive assistance.
    *   **Files:**
        *   `__init__.py`: Package initializer, exposes `background_monitor`.
        *   `background.py`: (`BackgroundMonitor`) Orchestrates various background monitoring tasks (Git status, file changes, system resources). Manages suggestions and cooldowns.
        *   `network_monitor.py`: (`NetworkMonitor`) Specifically monitors network status, local services (ports), external APIs, and dependency updates. Provides network-related suggestions.

*   **`angela/review/`**
    *   **Purpose:** Handles code review aspects, including diff generation and processing user feedback.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `diff_manager.py`: (`DiffManager`) Generates unified and HTML diffs between strings or files. Can also apply diffs (though potentially simplified). Handles directory diffs.
        *   `feedback_manager.py`: (`FeedbackManager`) Processes user feedback on code. Uses AI to generate improved code based on feedback, generates diffs, and can apply refinements to single files or entire projects.

*   **`angela/safety/`**
    *   **Purpose:** Enforces safety constraints, classifies risk, and manages user confirmations.
    *   **Files:**
        *   `__init__.py`: Package initializer, registers safety functions with the core registry.
        *   `adaptive_confirmation.py`: (`get_adaptive_confirmation`, `offer_command_learning`) Implements the context-aware confirmation logic. Decides whether to prompt the user based on risk level, preferences, and command history. Handles different confirmation UI levels (simple vs. detailed). Offers to trust commands after successful high-risk executions.
        *   `classifier.py`: (`classify_command_risk`, `analyze_command_impact`) Classifies command risk based on predefined regex patterns (critical, high, medium, low, safe). Analyzes potential command impact (affected files, operations, destructive nature).
        *   `confirmation.py`: (`requires_confirmation`, `format_impact_analysis`, `get_confirmation`) Provides the core user confirmation UI logic using `rich` and `prompt_toolkit`. Displays command, risk, impact, and preview before asking for confirmation. (Note: Largely superseded/wrapped by `adaptive_confirmation.py`).
        *   `preview.py`: (`generate_preview`, `preview_mkdir`, etc.) Generates previews of what specific commands (`ls`, `rm`, `cp`, `mv`, etc.) are likely to do by analyzing arguments and checking the file system. Includes a generic fallback using `--dry-run` flags where possible.
        *   `validator.py`: (`ValidationError`, `validate_command_safety`, `requires_superuser`, etc.) Performs stricter validation checks against dangerous patterns (e.g., `rm -rf /`, `chmod 777`), checks for required superuser privileges, and validates file permissions for operations.

*   **`angela/shell/`**
    *   **Purpose:** Contains shell integration scripts and terminal formatting logic.
    *   **Files:**
        *   `__init__.py`: Package initializer, imports formatters.
        *   `advanced_formatter.py`: Extends `TerminalFormatter` with methods specifically for displaying advanced task plans (`display_advanced_plan`), execution results (`display_execution_results`), step details, and step errors using `rich` components like Tables and Trees.
        *   `angela.bash`: Bash shell integration script. Defines the `angela` function, handles flags (`--debug`, `--version`, `--help`), and routes commands/requests to the Python backend (`python -m angela ...`).
        *   `angela.zsh`: Zsh shell integration script (similar functionality to `angela.bash`).
        *   `formatter.py`: (`OutputType`, `TerminalFormatter`) Core terminal output formatting class using `rich`. Provides methods for printing commands, outputs (stdout, stderr, info, errors), error analysis, task plans, workflows, file analysis/manipulation results, and suggestions with appropriate styling and syntax highlighting. Includes async output streaming.

*   **`angela/toolchain/`**
    *   **Purpose:** Integrates with common developer tools like Git, package managers, and CI/CD systems.
    *   **Files:**
        *   `__init__.py`: Package initializer.
        *   `ci_cd.py`: (`CiCdIntegration`) Detects project type and generates basic CI/CD configuration files (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.travis.yml`, `.circleci/config.yml`) based on project type and platform.
        *   `git.py`: (`GitIntegration`) Provides functions for interacting with Git repositories (init, stage, commit, branch creation, status checking). Includes `.gitignore` generation.
        *   `package_managers.py`: (`PackageManagerIntegration`) Detects and interacts with package managers (pip, npm, yarn, poetry, cargo) to install project dependencies.

*   **`angela/utils/`**
    *   **Purpose:** Contains utility functions, primarily logging setup.
    *   **Files:**
        *   `__init__.py`: Package initializer, exposes logging functions.
        *   `logging.py`: (`setup_logging`, `get_logger`) Configures application-wide logging using Loguru, setting up console and file handlers with specified formats and rotation.

*   **`angela/workflows/`**
    *   **Purpose:** Manages user-defined, reusable sequences of commands (workflows).
    *   **Files:**
        *   `__init__.py`: Package initializer, exposes `workflow_manager`.
        *   `manager.py`: (`WorkflowStep`, `Workflow`, `WorkflowManager`) Defines workflow models. Manages loading, saving, creating (interactively or from natural language via AI), listing, searching, deleting, and executing workflows. Persists workflows to JSON. Handles variable substitution during execution.
        *   `sharing.py`: (`WorkflowExportMetadata`, `WorkflowSharingManager`) Handles exporting workflows to shareable package files (`.angela-workflow` zip archives containing metadata and workflow data) and importing them. Includes checksum verification.

*   **`integrations/`**
    *   **Purpose:** Contains integration code, potentially for specific phases or external systems. (Note: The content provided suggests these might be for orchestrating features added in specific development phases or integrating the enhanced planner).
    *   **Files:**
        *   `__init__.py`: Package initializer, appears to call `init_application`.
        *   `enhanced_planner_integration.py`: *Crucial integration point*. Patches the `Orchestrator._process_multi_step_request` method to use the `EnhancedTaskPlanner`. Adds helper methods to the Orchestrator for handling advanced plan execution, display, confirmation, and variable extraction. Ensures the advanced planner is used for complex tasks.
        *   `integrations5.py`: (`PhaseIntegration`) Seems designed to initialize and manage features introduced around Phase 5/5.5 (Project Inference, Network Monitoring, Error Recovery, Enhanced Content Analysis). Provides status checks and context gathering related to these features.
        *   `integrations6.py`: Appears to contain *code snippets* and instructions for integrating Phase 6 features (Context Enhancer, File Resolver, File Activity, Execution Hooks) into the existing codebase, particularly updating the `Orchestrator` and `prompts.py`.

*   **`MD/`**
    *   **Purpose:** Contains Markdown documentation files describing the project, its phases, and specific features like the planner and rollback system.
    *   **Files:** `Info.md`, `NextSteps.md`, `Phase[1-7].md`, `context.md`, `planner_implementation.md`, `planner.py` (duplicate?), `rollback.md`, `tree.md`.

*   **`scripts/`**
    *   **Purpose:** Contains shell scripts for installation and uninstallation.
    *   **Files:** `install.sh`, `uninstall.sh`.

**3. Core Logic & Data Flow ("The Flow Explanation")**

*   **Application Initiation:**
    1.  The user types `angela <command> <args>` in their terminal.
    2.  The shell integration (`angela.bash` or `angela.zsh`) captures this.
    3.  It executes `python -m angela <command> <args>`.
    4.  `angela/__main__.py` runs.
    5.  `angela.init_application()` is called (from `angela/__init__.py`). This registers services (like `execution_engine`, `orchestrator`, `rollback_manager`) with the `core/registry.py` and crucially applies the `enhanced_planner_integration` patch.
    6.  The Typer app (`angela/cli/main.py:app`) is invoked.
    7.  Typer parses the command and arguments.
    8.  If it's the `request` command, `cli/main.py:request` function is called.
    9.  This function calls `orchestrator.process_request(...)`.

*   **Use Case 1: User asks AI to code a Python script (`angela generate create-project "simple flask api" --project-type python`)**
    1.  **Input:** CLI parses the command (`generate create-project`) and arguments. `cli/generation.py:create_project` is called.
    2.  **Processing:** `create_project` calls `generation/engine.py:code_generation_engine.generate_project`.
    3.  **Planning:** `generate_project` calls `_create_project_plan`. This involves:
        *   Determining project type (`python`).
        *   Building a prompt (`_build_project_planning_prompt`) describing the request and project type.
        *   Calling Gemini API (`ai/client.py`).
        *   Parsing the response (`_parse_project_plan`) into a `CodeProject` object (a list of `CodeFile` objects with paths and purposes, but empty content initially).
    4.  **Content Generation:** `generate_project` then calls `_generate_file_contents`. This iterates through the planned `CodeFile` objects (potentially in batches based on dependencies):
        *   For each file, it builds a specific prompt (`_build_file_content_prompt`) including file path, purpose, project context, and potentially content of dependency files already generated.
        *   Calls Gemini API (`ai/client.py`) for each file's content.
        *   Extracts the code (`_extract_code_from_response`).
        *   Validates the code (`generation/validators.py`). If invalid, it might attempt a fix using another AI call.
        *   Stores the generated content in the `CodeFile` object within the `CodeProject`.
    5.  **File Creation:** `create_project` (if not `--dry-run`) calls `code_generation_engine.create_project_files`.
        *   This function iterates through the `CodeFile` objects in dependency order (`_get_ordered_files`).
        *   It uses `execution/filesystem.py:create_directory` and `execution/filesystem.py:write_file` to create the actual directory structure and write the generated content to disk.
    6.  **Toolchain (Optional):** `create_project` might call `toolchain/git.py:git_integration.init_repository`, `toolchain/package_managers.py:package_manager_integration.install_dependencies`, etc., based on flags.
    7.  **Output:** Confirmation messages are printed to the console via `rich`.

*   **Use Case 2: User asks AI to deploy a web app (`angela request "deploy the project in staging"`)**
    1.  **Input:** `cli/main.py:request` gets the request string.
    2.  **Orchestration:** `orchestrator.process_request` is called.
    3.  **Context:** `ContextManager` provides CWD, project info. `ContextEnhancer` adds details. `SessionManager` provides conversation history. `FileResolver` looks for file mentions (likely none here).
    4.  **Request Type:** `_determine_request_type` likely identifies this as `MULTI_STEP` due to complexity.
    5.  **Planning:** `_process_multi_step_request` (patched by `enhanced_planner_integration.py`) is called.
        *   It calls `task_planner.plan_task` (which is actually `EnhancedTaskPlanner`).
        *   `plan_task` determines complexity (`advanced`).
        *   It builds a planning prompt (`_build_advanced_planning_prompt`) including the goal and context.
        *   Calls Gemini API (`ai/client.py`).
        *   Parses the response (`_parse_advanced_plan_response`) into an `AdvancedTaskPlan` object containing steps (likely `COMMAND` type for git, ssh, docker etc.).
    6.  **Confirmation:** The plan is displayed (`advanced_formatter.py:display_advanced_plan`). User confirmation is sought (`_confirm_advanced_plan`).
    7.  **Execution:** If confirmed, `task_planner.execute_plan` (actually `EnhancedTaskPlanner.execute_advanced_plan`) runs the `AdvancedTaskPlan`.
        *   It iterates through steps based on dependencies and `entry_points`.
        *   For each `COMMAND` step, `_execute_command_step` calls `execution/engine.py` to run the command (e.g., `git push`, `ssh server 'docker restart container'`).
        *   Results (stdout, stderr, success) are stored. Variables might be set/read.
        *   Error recovery (`error_recovery.py`) is triggered if a step fails.
        *   Rollback information is recorded (`rollback.py`).
    8.  **Output:** Execution results are displayed (`advanced_formatter.py:display_execution_results`).

*   **Use Case 3: User asks AI to organize files (`angela request "find all .log files in ~/logs older than 7 days and move them to ~/old_logs"`)**
    1.  **Input:** `cli/main.py:request`.
    2.  **Orchestration:** `orchestrator.process_request`.
    3.  **Context:** CWD, project info, etc. `FileResolver` identifies paths `~/logs`, `~/old_logs`.
    4.  **Request Type:** Likely `MULTI_STEP`.
    5.  **Planning:** `_process_multi_step_request` -> `task_planner.plan_task`.
        *   AI generates a plan (likely `AdvancedTaskPlan`). Steps might include:
            *   A `COMMAND` step: `find ~/logs -name '*.log' -type f -mtime +7 -print0` (or similar, maybe using Python code). Output saved to a variable (e.g., `found_files`).
            *   A `COMMAND` or `FILE` step: `mkdir -p ~/old_logs`.
            *   A `LOOP` step iterating over `found_files`. Loop body contains a `COMMAND` or `FILE` step: `mv ${loop_item} ~/old_logs`.
    6.  **Confirmation:** Plan displayed, user confirms.
    7.  **Execution:** `EnhancedTaskPlanner.execute_advanced_plan` runs the plan.
        *   Executes `find` command, stores output in `found_files` variable.
        *   Executes `mkdir`.
        *   Enters `LOOP` step. `_execute_loop_step` iterates:
            *   For each item (`${loop_item}`), executes `mv` command (`_execute_command_step`).
        *   Error recovery and rollback are active.
    8.  **Output:** Execution results displayed.

*   **Central Data Structures / State Management:**
    *   `context/manager.py:ContextManager`: Holds CWD, project root/type, current file. Refreshed per request.
    *   `context/session.py:SessionManager`: Holds `SessionMemory` (entities, recent commands/results) for conversational context. Persists between requests within a timeout period.
    *   `context/history.py:HistoryManager`: Persists long-term command history (`CommandRecord`) and derived patterns (`CommandPattern`) to JSON files.
    *   `context/preferences.py:PreferencesManager`: Loads/saves user preferences (`UserPreferences` model) from JSON.
    *   `intent/enhanced_task_planner.py:EnhancedTaskPlanner._variables`: Dictionary holding `DataFlowVariable` objects during the execution of an *advanced* plan. Used to pass data between steps.
    *   `execution/rollback.py:RollbackManager`: Stores `OperationRecord` objects (in memory, loaded from JSON) and `Transaction` objects (in memory/JSON files) to enable undo functionality.

*   **Component Communication:**
    *   **Direct Function/Method Calls:** Most communication is direct (e.g., Orchestrator calls TaskPlanner, TaskPlanner calls AIClient, AdaptiveEngine calls ExecutionEngine).
    *   **Service Registry (`core/registry.py`):** Used to decouple components and avoid circular imports. Key components (`orchestrator`, `execution_engine`, `rollback_manager`, safety functions) register themselves, and others retrieve them using `registry.get("service_name")`.
    *   **Data Objects:** Pydantic models (`CommandSuggestion`, `TaskPlan`, `CodeProject`, etc.) are used to pass structured data between components.
    *   **Context Dictionary:** The `context` dictionary is passed around extensively to provide environmental information to various components.

**4. Inter-Module/Component Integration & Dependencies**

*   **Conceptual Map (Text-Based):**
    *   **`CLI (cli/)`** -> `Orchestrator` (Processes user input)
    *   **`Orchestrator`** -> `ContextManager` (Gets environment info)
    *   **`Orchestrator`** -> `ContextEnhancer` (Gets enhanced project/activity info)
    *   **`Orchestrator`** -> `SessionManager` (Gets/updates conversational context)
    *   **`Orchestrator`** -> `FileResolver` (Extracts/resolves file paths from request)
    *   **`Orchestrator`** -> `RequestType Determination Logic` (Uses regex/keywords)
    *   **`Orchestrator`** -> `AIClient` (For simple command suggestions via `_get_ai_suggestion`)
    *   **`Orchestrator`** -> `IntentAnalyzer` (For intent classification via `_get_ai_suggestion`)
    *   **`Orchestrator`** -> `ConfidenceScorer` (For suggestion confidence via `_process_command_request`)
    *   **`Orchestrator`** -> `AdaptiveEngine` (For executing single commands)
    *   **`Orchestrator`** -> `TaskPlanner` (`EnhancedTaskPlanner`) (For planning/executing multi-step tasks)
    *   **`Orchestrator`** -> `ContentAnalyzer` (`EnhancedContentAnalyzer`) (For file content operations)
    *   **`Orchestrator`** -> `WorkflowManager` (For defining/executing workflows)
    *   **`TaskPlanner` (`EnhancedTaskPlanner`)** -> `AIClient` (Generates plan steps)
    *   **`TaskPlanner` (`EnhancedTaskPlanner`)** -> `ExecutionEngine` / `AdaptiveEngine` / Specific Executors (Runs plan steps)
    *   **`TaskPlanner` (`EnhancedTaskPlanner`)** -> `RollbackManager` (Records steps within transactions)
    *   **`TaskPlanner` (`EnhancedTaskPlanner`)** -> `ErrorRecoveryManager` (Handles step failures)
    *   **`AdaptiveEngine`** -> `Safety/Classifier` (Gets risk level)
    *   **`AdaptiveEngine`** -> `Safety/Preview` (Generates command preview)
    *   **`AdaptiveEngine`** -> `Safety/AdaptiveConfirmation` (Gets user confirmation)
    *   **`AdaptiveEngine`** -> `ExecutionEngine` (Runs the actual command)
    *   **`AdaptiveEngine`** -> `HistoryManager` (Logs command execution)
    *   **`AdaptiveEngine`** -> `ErrorAnalyzer` (Analyzes failures)
    *   **`ExecutionEngine`** -> `RollbackManager` (Via registry, records successful operations)
    *   **`FileSystem`** -> `Safety/Validator` (Checks permissions)
    *   **`FileSystem`** -> `RollbackManager` (Via registry, records file operations, uses backups)
    *   **`GenerationEngine`** -> `AIClient` (Generates plan/content)
    *   **`GenerationEngine`** -> `FrameworkGenerator` (Generates framework structures)
    *   **`GenerationEngine`** -> `Validators` (Validates generated code)
    *   **`GenerationEngine`** -> `FileSystem` (Creates project files)
    *   **`FeedbackManager`** -> `AIClient` (Generates code refinements)
    *   **`FeedbackManager`** -> `DiffManager` (Generates/applies diffs)
    *   **`FeedbackManager`** -> `FileSystem` (Applies refined code)
    *   **`ContextEnhancer`** -> `ProjectInference`, `FileActivityTracker`
    *   **Many Modules** -> `ConfigManager` (Access settings)
    *   **Many Modules** -> `Logger` (Write logs)
    *   **Registry** -> Used by various modules to get instances of others (e.g., `RollbackManager`, `ExecutionEngine`, safety functions).

*   **Critical Dependencies:**
    *   **Orchestrator:** Highly dependent on almost all other major components (AI, Context, Execution, Intent, Safety).
    *   **AI Client (`ai/client.py`):** Requires `config` for the API key. Central to suggestion, planning, and generation.
    *   **Context (`context/`):** Foundation for relevant AI responses and adaptive behavior. `manager.py` is central.
    *   **Execution (`execution/`):** Core for performing actions. `engine.py` is the base executor.
    *   **Safety (`safety/`):** Crucial for preventing dangerous operations. `classifier.py` and `adaptive_confirmation.py` are key.
    *   **Configuration (`config.py`):** Needed early for API keys and behavior flags.
    *   **Registry (`core/registry.py`):** Essential for decoupling and allowing modules like `ExecutionEngine` or `EnhancedTaskPlanner` to access `RollbackManager` without direct cyclic imports.

*   **Configuration Handling:**
    *   Managed by `angela/config.py:ConfigManager`.
    *   Loads settings from environment variables (via `python-dotenv` loading `.env`) and the TOML file (`~/.config/angela/config.toml`). Environment variables likely override file settings (standard `dotenv` behavior).
    *   Uses Pydantic models (`AppConfig`, `ApiConfig`, `UserConfig`) for structure and validation.
    *   Configuration is accessed globally via the `config_manager` instance (e.g., `config_manager.config.api.gemini_api_key`).
    *   User preferences are handled separately by `angela/context/preferences.py:PreferencesManager`, loading from `~/.config/angela/preferences.json`.

*   **Error Handling:**
    *   Standard Python `try...except` blocks are used throughout the code to catch exceptions during I/O, API calls, command execution, etc.
    *   Errors are logged using `loguru` via `utils/logging.py`.
    *   Specific exceptions like `FileSystemError` (`execution/filesystem.py`) and `ValidationError` (`safety/validator.py`) are defined.
    *   The `Orchestrator` has a top-level `try...except` to catch errors during request processing and provide a fallback response.
    *   `ai/analyzer.py:ErrorAnalyzer` specifically analyzes command execution errors (`stderr`) to provide explanations and potential fixes.
    *   `execution/error_recovery.py:ErrorRecoveryManager` provides more sophisticated error handling for multi-step plans generated by the `EnhancedTaskPlanner`, allowing for retries or alternative strategies.
    *   Execution results dictionaries typically include a `success` boolean and an `error` field.

**5. Code Explanation (Dumbed Down but Still Technical)**

*   **Example 1: `safety/adaptive_confirmation.py:get_adaptive_confirmation`**
    *   **Goal:** Decide whether to ask the user "Are you sure?" before running a command. Avoid bothering the user for safe or frequently used commands but ensure dangerous ones are confirmed.
    *   **Logic:**
        1.  **Dry Run Check:** If it's just a preview (`dry_run=True`), don't ask, just show the preview (`_show_dry_run_preview`) and stop.
        2.  **Preferences Check:** Ask `preferences_manager` if this `risk_level` and specific `command` are set to auto-execute (`should_auto_execute`).
        3.  **History Check (if auto-execute allowed):** If preferences allow auto-execution, check `history_manager` how often (`frequency`) this *exact* command was run successfully (`success_rate`).
        4.  **Auto-Execute Decision:** If the command is allowed to auto-execute *and* it has been used successfully many times (e.g., >= 5 times with >80% success), assume the user trusts it. Show a quick notice (`_show_auto_execution_notice`) and return `True` (meaning "yes, run it").
        5.  **Manual Confirmation Needed:** If it wasn't auto-executed, proceed to ask the user.
        6.  **Simple vs. Detailed Prompt:** If the risk is `HIGH` or `CRITICAL`, use a detailed confirmation dialog (`_get_detailed_confirmation`) showing command, risk, reason, impact analysis, and preview. Otherwise, use a simpler dialog (`_get_simple_confirmation`) showing command, risk, reason, and maybe preview.
        7.  **User Response:** The dialogs (using `prompt_toolkit`) return `True` if the user selects "Yes", `False` otherwise. This boolean is returned by the function.
        8.  **(Learning - `offer_command_learning`):** Separately, after a *successful* high-risk command, this function might ask the user if they want to trust this command in the future, updating preferences if they agree.
    *   **Analogy:** Think of it like parental controls. You might let your kid browse safe websites automatically. For new or potentially risky sites, you might ask them "Are you sure?" with varying levels of warning depending on the site's rating. If they visit a slightly risky site often without issues, you might eventually stop asking for confirmation for *that specific site*.

*   **Example 2: `intent/enhanced_task_planner.py:EnhancedTaskPlanner._execute_advanced_plan`**
    *   **Goal:** Execute a complex plan involving different types of steps (commands, code, decisions, loops) in the correct order, passing data between them.
    *   **Logic:**
        1.  **Initialization:** Reset internal `_variables` (data storage for this run). Set up the initial `StepExecutionContext`. Identify starting steps (`entry_points`).
        2.  **Execution Loop (`while pending_steps`):** Keep running as long as there are steps waiting to be executed.
        3.  **Find Ready Steps:** Inside the loop, check all `pending_steps`. A step is "ready" if all the steps listed in its `dependencies` have already `completed`.
        4.  **Stuck Check:** If no steps are ready, but some are still pending, it means there's a problem (like a circular dependency), so break the loop.
        5.  **Execute Ready Steps:** For each ready step:
            *   Log the step being executed.
            *   Update the `context` for this specific step.
            *   Call `_execute_advanced_step` to actually run the step (this function figures out *how* based on `step.type`).
            *   Store the `result` (output, success/failure) from the step.
            *   Mark the step as `completed`.
            *   Update execution statistics.
            *   **Error Handling:** If the step failed (`result["success"] == False`):
                *   Log the error.
                *   Attempt recovery using `_error_recovery_manager.handle_error`.
                *   If recovery succeeds, update the result and continue.
                *   If recovery fails, stop the entire plan execution and return failure.
        6.  **Update Pending List:** Remove the just-completed steps from the `pending_steps` list. Add any *new* steps that might have become ready because their dependencies are now met (e.g., steps listed in the `true_branch` or `false_branch` of a `DECISION` step, or steps that depended on the ones just completed).
        7.  **Loop Continuation:** Go back to step 3 to find the next ready steps.
        8.  **Completion:** Once the loop finishes (no more pending steps or stuck), check if all steps in the original plan were completed successfully. Return the final results, including success status, step results, execution time, and final variable values.
    *   **Analogy:** Imagine executing a complex recipe with optional steps and loops. You have a list of steps. You constantly check which steps you *can* do now (e.g., "mix ingredients" requires "measure ingredients" to be done first). You perform all ready steps. If a step involves a choice ("if dough is sticky, add flour"), you follow the correct path. If a step says "knead for 10 minutes", you do that. If you make a mistake (spill flour), you might try to recover (clean up, measure again). You keep track of what's done and what's ready next until the recipe is complete or you hit an unrecoverable error. The `_variables` are like bowls holding intermediate results (e.g., measured flour, mixed dough) needed for later steps.

**6. User Workflow Scenarios (Illustrative Examples)**

*   **Scenario 1: Generate Flask Boilerplate**
    1.  **User:** `angela generate create-project "simple api backend" --framework flask --git-init --install-deps`
    2.  **Angela (Internal):**
        *   CLI parses command, calls `cli/generation.py:create_project`.
        *   `CodeGenerationEngine` gets request.
        *   Identifies framework (`flask`). Calls `FrameworkGenerator._generate_flask`.
        *   `_generate_flask` defines the standard file structure (app.py, requirements.txt, etc.) and uses AI (`_generate_content`) to fill them with basic Flask boilerplate.
        *   Returns `CodeProject` plan to `create_project`.
        *   `create_project` displays the plan (list of files).
        *   `create_project` calls `CodeGenerationEngine.create_project_files` to write files using `FileSystem`.
        *   `create_project` calls `GitIntegration.init_repository` (creates `.git`, `.gitignore`).
        *   `create_project` calls `PackageManagerIntegration.install_dependencies` (detects `pip`, runs `pip install -r requirements.txt`).
        *   `create_project` calls `GitIntegration.commit_changes` for the initial commit.
    3.  **Angela (Output):** Shows project plan, confirms actions (if needed), prints progress messages ("Creating files...", "Initializing Git...", "Installing dependencies...", "Creating initial commit..."), finishes with "Project generated successfully in ./simple_api_backend".

*   **Scenario 2: Debug Python Code**
    1.  **User:** `angela refine-code "Fix the NameError in process_data" --file src/data_processor.py --apply`
    2.  **Angela (Internal):**
        *   CLI parses command, calls `cli/generation.py:refine_code`.
        *   Reads `src/data_processor.py` content.
        *   Calls `FeedbackManager.process_feedback` with the code and feedback.
        *   `process_feedback` builds a prompt (`_build_improvement_prompt`) asking the AI to fix the `NameError`.
        *   Calls Gemini API.
        *   Extracts the improved code (`_extract_improved_code`).
        *   Generates a diff (`DiffManager.generate_diff`).
        *   Returns the result (original, improved, diff, explanation) to `refine_code`.
        *   `refine_code` displays the diff and explanation.
        *   Since `--apply` was used, calls `FeedbackManager.apply_refinements`.
        *   `apply_refinements` writes the `improved_code` back to `src/data_processor.py` (potentially creating a `.bak` file).
    3.  **Angela (Output):** Shows "Processing feedback...", displays the diff of changes, explains the fix (e.g., "Added import for 'x' or defined 'x' before use"), shows "Applying changes...", confirms "Changes applied successfully".

*   **Scenario 3: File Organization**
    1.  **User:** `angela request "move all files ending in .log from ~/project/logs to ~/project/archived_logs older than 1 month"`
    2.  **Angela (Internal):**
        *   CLI calls `Orchestrator.process_request`.
        *   Context/Resolver identify paths. Determined as `MULTI_STEP`.
        *   `TaskPlanner` generates an `AdvancedTaskPlan`:
            *   Step 1 (COMMAND): `find ~/project/logs -maxdepth 1 -name '*.log' -type f -mtime +30 -print0` (Output -> `log_files` variable).
            *   Step 2 (COMMAND/FILE): `mkdir -p ~/project/archived_logs`.
            *   Step 3 (LOOP): Iterate over `${log_files}` (split by null char).
            *   Step 4 (COMMAND/FILE, inside loop): `mv ${loop_item} ~/project/archived_logs`.
        *   Plan displayed, user confirms.
        *   `EnhancedTaskPlanner` executes the plan: runs `find`, `mkdir`, then loops through results running `mv` for each. Rollback data recorded.
    3.  **Angela (Output):** Displays the plan, asks for confirmation, shows execution progress/results for each step. Finishes with "Plan executed successfully".

**7. System Operational Scenarios (Internal Workings)**

*   **Scenario 1: Complex Coding Request Breakdown**
    *   User request: `angela generate create-project "Flask API with JWT auth and user CRUD"`
    *   `CodeGenerationEngine._create_project_plan` calls Gemini with a prompt describing the request and project type (`python`).
    *   Gemini returns a JSON plan listing files: `app.py`, `models.py`, `routes/auth.py`, `routes/users.py`, `requirements.txt`, `config.py`, `tests/test_auth.py`, etc., along with their purposes.
    *   `CodeGenerationEngine._generate_file_contents` iterates through this plan.
    *   For `models.py`, it prompts Gemini: "Generate content for models.py (purpose: Define User model with SQLAlchemy)..."
    *   For `routes/auth.py`, it prompts: "Generate content for routes/auth.py (purpose: Implement JWT login/register endpoints)... Use User model from models.py (content provided)..." (passing relevant context).
    *   This continues, potentially generating files concurrently in batches based on dependencies, until all file contents are generated.

*   **Scenario 2: External API Interaction (within Advanced Plan)**
    *   An `AdvancedPlanStep` has `type=PlanStepType.API`, `api_url="https://api.example.com/data"`, `api_method="POST"`, `api_payload={"key": "${some_variable}"}`.
    *   `EnhancedTaskPlanner._execute_advanced_step` calls `_execute_api_step`.
    *   `_execute_api_step` resolves `${some_variable}` using `_get_variable_value`.
    *   It uses `aiohttp.ClientSession` to make an asynchronous POST request to the URL.
    *   The resolved variable value is included in the JSON payload (`request_kwargs["json"]`). Headers (e.g., `Content-Type: application/json`) are set. SSL verification is handled. Timeout is applied.
    *   Waits for the response using `await response.text()` or `await response.json()`.
    *   Parses the status code, headers, and body (text/JSON).
    *   Stores results (`status_code`, `response_text`, `response_json`) in the step result dictionary and potentially sets output variables like `${api_step_id}_status_code`.
    *   Handles potential `aiohttp.ClientError` or `TimeoutError`.

*   **Scenario 3: Learning/Adaptation Feedback Loop**
    *   User runs `angela request "sudo apt update && sudo apt upgrade -y"`.
    *   `AdaptiveEngine` gets the command.
    *   `Safety/Classifier` identifies risk as HIGH/CRITICAL.
    *   `Safety/AdaptiveConfirmation` checks preferences/history. Since it's a risky command, likely not auto-executed initially. It calls `_get_detailed_confirmation`.
    *   User confirms execution.
    *   `AdaptiveEngine` executes the command successfully.
    *   `HistoryManager.add_command` records the successful execution.
    *   `AdaptiveEngine` calls `offer_command_learning`.
    *   Since the command was successful and high-risk, `offer_command_learning` might prompt the user: "You've used 'sudo apt update ...' successfully. Trust similar commands in the future?"
    *   If user agrees, `PreferencesManager.add_trusted_command` updates `preferences.json`.
    *   Next time, `AdaptiveConfirmation.should_auto_execute` might return `True` for this specific command, skipping the confirmation prompt.

**8. Potential Areas for Clarification or Further Development**

*   **Error Recovery Depth:** The `ErrorRecoveryManager` is present, but its specific strategies and AI integration (`_generate_ai_recovery_strategies`) seem complex and might need refinement/testing. How well does it handle diverse failures?
*   **Code Sandbox:** The `EnhancedTaskPlanner._setup_code_sandbox` defines allowed imports and banned functions, but the actual sandboxing mechanism (e.g., using separate processes, `restrictedpython`, or containers) isn't explicitly detailed in the execution logic shown (`_execute_python_code`, etc. seem to run directly via subprocess). This is a critical security area.
*   **Generic Framework Generation:** The `_generate_generic` function relies heavily on AI to determine structure and content. Its reliability might vary compared to specialized generators. The prompt asks for a structure first, then generates content file-by-file; how well does it maintain consistency?
*   **Dependency Resolution in Generation:** While `CodeGenerationEngine` builds a dependency graph for file creation order, the prompts for generating *content* rely on passing previously generated content. This might hit token limits for complex dependencies. How does it handle generating code that requires imports from files not yet generated in the same batch?
*   **Testing (`tests/`):** The directory exists but was excluded. The quality and coverage of tests are unknown but crucial for such a complex system.
*   **`integrations/` Files:** The purpose of `integrations5.py` and `integrations6.py` seems to be related to bootstrapping features from different development phases. Their current role and necessity in the final integrated codebase could be clarified. `integrations6.py` looks more like instructions than runnable code.
*   **Content Analyzer Extensions:** The `content_analyzer_extensions.py` defines many language handlers (`_analyze_typescript`, `_analyze_java`, etc.) but only `_analyze_typescript` and `_analyze_json` have implementation snippets provided. Others are likely placeholders.
*   **Rollback for Commands/Content:** While the `RollbackManager` has methods to record command/content operations (with compensating actions or diffs), the implementation details of *applying* these rollbacks (`_rollback_command_execution`, `_rollback_content_manipulation`) seem complex and rely on accurate compensating actions or reversible diffs.
*   **Prompt Size Limits:** Complex planning, generation, and refinement tasks create very large prompts. How the system handles potential context window limits of the Gemini API isn't explicitly detailed (though truncation hints exist).
