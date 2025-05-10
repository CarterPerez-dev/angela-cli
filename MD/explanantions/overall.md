Okay, this is a big request! I'll break down the codebase you've provided, directory by directory, and file by file, explaining their purpose and how they fit into potential user scenarios and CLI commands.

This will be a **very high-level overview** focusing on the *role* and *connections* of each part, as a line-by-line code explanation would be immense.

Let's start with the overall flow:

1.  **User Input:** You type a command like `angela show me all python files` or `angela files ls`.
2.  **CLI Handling (`cli/`):** The `cli/main.py` (and its submodules like `cli/files.py`) receives this. Typer (the CLI framework) figures out which function to call based on the command.
3.  **Orchestration (`orchestrator.py`):** This is the central brain. It takes the user's request, gathers context, decides what kind of request it is (e.g., simple command, file operation, code generation), and then delegates to the appropriate system.
4.  **Context Gathering (`context/`):** Before doing anything complex, Angela needs to understand the environment (current directory, project type, recent files, etc.). Modules in `context/` provide this.
5.  **AI Processing (`ai/`):** For natural language requests, the orchestrator uses AI components to:
    *   Understand intent (`ai/intent_analyzer.py`).
    *   Build a prompt for the LLM (`ai/prompts.py`).
    *   Send the prompt to the LLM and get a response (`ai/client.py`).
    *   Parse the LLM's response into an actionable command or plan (`ai/parser.py`).
6.  **Planning (`intent/`):** For more complex requests, a planner (`intent/planner.py` and its extensions) breaks the request into multiple steps.
7.  **Safety Checks (`safety/`):** Before executing anything, Angela checks if the command is risky (`safety/classifier.py`, `safety/validator.py`) and asks for confirmation (`safety/confirmation.py`).
8.  **Execution (`execution/`):** If confirmed (or if it's a safe/direct command), the `execution/engine.py` (or `adaptive_engine.py`) runs the command. File operations might go through `execution/filesystem.py`.
9.  **Toolchain (`toolchain/`):** If the command involves specific tools like Git, Docker, or package managers, modules in `toolchain/` handle the interaction.
10. **Generation (`generation/`):** If the request is to generate code or docs, modules here plan the structure and content.
11. **Feedback & Output (`shell/formatter.py`, `shell/inline_feedback.py`):** Results, errors, or suggestions are formatted and shown to the user.
12. **Monitoring & Proactive Help (`monitoring/`):** Background processes watch for common issues or opportunities to help.
13. **Rollback (`execution/rollback.py`):** Operations are recorded so they can be undone.

---

Now, let's go directory by directory:

**Root Level Files:**

*   `__init__.py`:
    *   **Purpose:** Marks the `angela` directory as a Python package. It's the first file Python looks at when you import `angela`.
    *   **Job:** Initializes the application by calling `init_application()`. This function is crucial as it sets up logging, registers core services with the `registry` (see `core/`), and applies integrations.
    *   **Scenario:** When you run any `angela` command, this file's `init_application()` is one of the first things to run, ensuring all parts of Angela are ready.
    *   **Defines/Controls:** The overall application startup sequence.

*   `__main__.py`:
    *   **Purpose:** Allows the `angela` package to be run as a script (e.g., `python -m angela request "list files"`).
    *   **Job:** Calls `init_application()` and then starts the Typer CLI application (`app()`).
    *   **Scenario:** This is the main entry point when you execute Angela from the command line.
    *   **Defines/Controls:** The execution start of the CLI.

*   `config.py`:
    *   **Purpose:** Manages application configuration.
    *   **Job:** Defines Pydantic models for configuration structure (API keys, user preferences, debug mode). Loads configuration from `~/.config/angela/config.toml` and environment variables. Provides a `config_manager` instance to access settings.
    *   **Scenario:**
        *   User runs `angela init`: This file's logic is used to save the API key and preferences to `config.toml`.
        *   Angela starts: It loads the API key from here to talk to Gemini.
        *   Angela decides whether to ask for confirmation: It checks `user.confirm_all_actions` from this config.
    *   **Defines/Controls:** How Angela stores and accesses its settings.

*   `constants.py`:
    *   **Purpose:** Stores global constants used throughout the application.
    *   **Job:** Defines things like API model names, default paths (CONFIG_DIR, LOG_DIR), risk levels, etc. This avoids "magic strings/numbers" scattered in the code.
    *   **Scenario:** When the AI client needs to know which Gemini model to use, it gets it from here. When the safety module classifies a command, it uses `RISK_LEVELS` from here.
    *   **Defines/Controls:** Centralized, unchanging values.

*   `orchestrator.py`:
    *   **Purpose:** The central coordinator of Angela's actions.
    *   **Job:**
        1.  Receives the user's request (e.g., "list all python files").
        2.  Gathers context (current directory, project type, etc.) using `context/` modules.
        3.  Determines the `RequestType` (e.g., simple command, multi-step, file operation).
        4.  Delegates to the appropriate processing function (e.g., `_process_command_request`, `_process_multi_step_request`).
        5.  Interacts with AI components (`ai/`) for understanding, planning, and suggestion generation.
        6.  Uses the `execution/` engine to run commands.
        7.  Formats and returns the result.
    *   **Scenario:** Almost every `angela` command that involves natural language or complex actions goes through the orchestrator.
        *   `angela request "show me python files"`: Orchestrator gets context, determines it's a command request, asks AI for a command (`find . -name '*.py'`), gets confirmation, executes it, and shows output.
        *   `angela request "create a new django project and then add a blog app"`: Orchestrator determines it's multi-step, uses a planner, and executes the planned steps.
    *   **Defines/Controls:** The main logic flow for handling user requests.

*   `check_services.py` & `diagnostic.py`:
    *   **Purpose:** Utility scripts for developers of Angela to check if core services are registered and the application is initialized correctly.
    *   **Job:** Imports and tries to use key components, logging success or failure.
    *   **Scenario:** A developer working on Angela runs `python check_services.py` to ensure their recent changes haven't broken service registration.
    *   **Defines/Controls:** Internal diagnostic checks.

---

**`ai/` Directory:** AI Core Components

*   **Overall Purpose:** Houses all logic related to Artificial Intelligence, primarily interacting with the Gemini LLM, parsing its responses, and analyzing content or errors.
*   `__init__.py`:
    *   **Purpose:** Marks `ai/` as a Python package.
    *   **Job:** Exports the main usable components from this package (like `gemini_client`, `parse_ai_response`, various analyzers) so other parts of Angela can easily import them.
    *   **Defines/Controls:** The public interface of the `ai` package.

*   `analyzer.py` (contains `ErrorAnalyzer`):
    *   **Purpose:** To understand and provide help for command execution errors.
    *   **Job:** Takes a failed command and its error output. Matches against known error patterns (e.g., "Permission denied", "command not found"). Suggests potential fixes or reasons for the error.
    *   **Scenario:** User runs `mkdr new_folder` (typo). Shell returns "command not found". Angela's orchestrator passes this to `ErrorAnalyzer`, which might suggest "Did you mean `mkdir`? The command `mkdr` is not installed."
    *   **Defines/Controls:** Error diagnosis and fix suggestion logic.

*   `client.py` (contains `GeminiClient`):
    *   **Purpose:** To communicate with the Google Gemini API.
    *   **Job:** Takes a prompt (a question or instruction for the AI), sends it to the Gemini API (using the API key from `config.py`), and returns the AI's text response. Handles API request formatting and basic error handling for API calls.
    *   **Scenario:** Any time Angela needs to "think" (e.g., generate a command from "list text files", summarize a file, plan steps), some component will build a prompt and use `GeminiClient` to get an answer from the LLM.
    *   **Defines/Controls:** The interface to the external LLM.

*   `confidence.py` (contains `ConfidenceScorer`):
    *   **Purpose:** To assess how sure Angela (or the AI) is about a generated command or interpretation.
    *   **Job:** Takes a user request, a suggested command, and context. It uses heuristics (e.g., command complexity vs. request complexity, historical success of similar commands) to output a confidence score (0.0-1.0).
    *   **Scenario:** User asks "delete all my work". AI might suggest `rm -rf /home/user`. `ConfidenceScorer` would likely give this a low confidence score (and `safety/classifier.py` would flag it as high risk), prompting more checks.
    *   **Defines/Controls:** Logic for evaluating the reliability of AI outputs.

*   `content_analyzer.py` (contains `ContentAnalyzer`):
    *   **Purpose:** To understand, summarize, or manipulate the content of files using AI.
    *   **Job:** Can read a file, send its content (or parts of it) to the LLM with an instruction (e.g., "summarize this", "find functions related to user authentication", "change variable 'x' to 'y'").
    *   **Scenario:**
        *   User: `angela request "summarize README.md"` -> Orchestrator uses `ContentAnalyzer` to read README.md and ask the LLM for a summary.
        *   User: `angela request "in main.py, rename the function 'calculate' to 'compute_value'"` -> Orchestrator uses `ContentAnalyzer` to get `main.py`'s content, ask the LLM to make the change, and then potentially write the modified content back.
    *   **Defines/Controls:** AI-powered file content operations.

*   `content_analyzer_extensions.py` (contains `EnhancedContentAnalyzer`):
    *   **Purpose:** Extends `ContentAnalyzer` with specialized logic for different file types and programming languages.
    *   **Job:** Adds more sophisticated parsing for specific languages (e.g., using AST for Python, regex for TypeScript interfaces) before or alongside LLM analysis.
    *   **Scenario:** When analyzing a Python file, instead of just sending raw text to the LLM, this might first parse out function and class names using Python's `ast` module to provide more structured context to the LLM.
    *   **Defines/Controls:** Language-specific content analysis enhancements.

*   `enhanced_prompts.py`:
    *   **Purpose:** To create more sophisticated and context-rich prompts for the LLM, especially when dealing with code or project state.
    *   **Job:** Builds on `prompts.py` by incorporating semantic code understanding (from `ai/semantic_analyzer.py`) and detailed project state (from `context/project_state_analyzer.py`) into the prompts sent to the LLM.
    *   **Scenario:** User asks to "refactor the `process_payment` function". This module helps build a prompt that includes not just the request, but also the current code of `process_payment`, its known callers/callees, and relevant project Git status. This allows the LLM to make more informed refactoring suggestions.
    *   **Defines/Controls:** Advanced prompt construction with deep project and code context.

*   `file_integration.py`:
    *   **Purpose:** To bridge AI-suggested file operations with the actual filesystem execution.
    *   **Job:** Parses AI-suggested commands (like "create directory foo" or "copy file a to b") and translates them into structured parameters that `execution/filesystem.py` can understand and execute.
    *   **Scenario:** AI suggests "make a new folder called 'docs'". This module extracts `operation_type="create_directory"` and `parameters={"path": "docs"}`.
    *   **Defines/Controls:** Translation of natural language file operations to structured calls.

*   `intent_analyzer.py` (contains `IntentAnalyzer`):
    *   **Purpose:** To understand the user's underlying goal or intent from their natural language request, even if it's phrased imprecisely.
    *   **Job:** Uses patterns, fuzzy matching (e.g., `difflib`), and potentially AI to classify the request (e.g., "file_search", "git_operation") and extract key entities (e.g., filenames, search terms). It can also handle disambiguation by asking the user for clarification.
    *   **Scenario:** User types "show me pythn fils". `IntentAnalyzer` normalizes "pythn fils" to "python files", identifies the intent as "file_search", and extracts "*.py" as the pattern. If the user typed "manage my project files", it might ask "Do you want to list, create, or delete files?".
    *   **Defines/Controls:** User intent classification and entity extraction.

*   `parser.py` (contains `CommandSuggestion` model and `parse_ai_response`):
    *   **Purpose:** To structure the (often JSON) text response from the LLM into a usable Python object.
    *   **Job:** Takes the raw string output from the LLM (which is expected to be JSON, possibly in a markdown code block) and parses it into a `CommandSuggestion` object (or similar Pydantic model), which has fields like `intent`, `command`, `explanation`.
    *   **Scenario:** The LLM returns `{"command": "ls -l", "explanation": "lists files in long format"}`. `parse_ai_response` converts this string into a `CommandSuggestion` object that the orchestrator can easily work with.
    *   **Defines/Controls:** Structuring of AI responses.

*   `prompts.py`:
    *   **Purpose:** To construct the basic prompts (instructions and context) that are sent to the LLM for various tasks.
    *   **Job:** Contains templates and logic to build effective prompts. This includes system instructions (telling the AI it's "Angela", a CLI assistant), few-shot examples (to guide the AI's response format and style), and context about the current environment.
    *   **Scenario:** When the user asks "find text files", `build_prompt` in this file assembles the necessary instructions, examples, and current directory information to send to the LLM.
    *   **Defines/Controls:** Basic prompt engineering.

*   `semantic_analyzer.py` (contains `SemanticAnalyzer` and code entity classes like `Function`, `Class`):
    *   **Purpose:** To perform deep, language-specific analysis of source code.
    *   **Job:** Parses code files (e.g., Python using `ast`, JavaScript/TypeScript with regex/LLM) to identify functions, classes, variables, imports, their relationships, docstrings, and code metrics (like complexity). It can analyze single files or entire projects.
    *   **Scenario:**
        *   User asks "explain the `calculate_total` function in `billing.py`". `SemanticAnalyzer` parses `billing.py`, finds `calculate_total`, extracts its parameters, docstring, and body, which is then used to generate an explanation.
        *   When generating code for a new feature, this analyzer can provide context about existing classes and functions the new code might need to interact with.
    *   **Defines/Controls:** In-depth code structure and relationship analysis.

---

**`cli/` Directory:** Command-Line Interface

*   **Overall Purpose:** Defines the commands and subcommands that the user interacts with directly in their terminal (e.g., `angela request ...`, `angela files ls`, `angela generate ...`). It uses the Typer library to create a rich CLI experience.
*   `__init__.py`:
    *   **Purpose:** Initializes the `cli` package.
    *   **Job:** Imports the main Typer `app` from `cli/main.py` and then adds other Typer apps (from `cli/files.py`, `cli/workflows.py`, etc.) as subcommands to this main app. For example, it makes `files_app` available as `angela files`.
    *   **Defines/Controls:** The overall structure of the CLI commands and subcommands.

*   `docker.py`:
    *   **Purpose:** Provides CLI commands specifically for Docker and Docker Compose operations.
    *   **Job:** Defines commands like `angela docker status`, `angela docker ps`, `angela docker build`, `angela docker compose-up`, etc. These functions typically call methods in `toolchain/docker.py` to perform the actual Docker interactions and then format the output for the user.
    *   **Scenario:** User types `angela docker ps -a`. The `list_containers` function in this file is called, which in turn calls `docker_integration.list_containers(all_containers=True)`. The result is then formatted into a table and printed.
    *   **Defines/Controls:** The `angela docker ...` subcommand namespace.

*   `files_extensions.py`:
    *   **Purpose:** Extends the basic file operations with more advanced features, particularly around file resolution and activity.
    *   **Job:** Defines commands like `angela files resolve <reference>` (to find a file based on a fuzzy name) and `angela files recent` (to show recently accessed files). These commands use services from the `context/` directory like `file_resolver` and `file_activity_tracker`.
    *   **Scenario:** User types `angela files resolve my_config`. The `resolve_file` function calls `file_resolver.resolve_reference("my_config", ...)` to find the actual path to a configuration file.
    *   **Defines/Controls:** Advanced `angela files ...` subcommands.

*   `files.py`:
    *   **Purpose:** Provides CLI commands for basic file and directory operations.
    *   **Job:** Defines commands like `angela files ls`, `angela files mkdir <dirname>`, `angela files rm <filename>`, `angela files cat <filename>`, etc. These functions usually call the safe file system operations in `execution/filesystem.py`.
    *   **Scenario:** User types `angela files mkdir new_project`. The `make_directory` function in this file is called, which in turn calls `create_directory("new_project", ...)` from `execution/filesystem.py`.
    *   **Defines/Controls:** Basic `angela files ...` subcommands.

*   `generation.py`:
    *   **Purpose:** Provides CLI commands for code and project generation.
    *   **Job:** Defines commands like `angela generate create-project "a simple web server"` or `angela generate add-feature "user login"`. These functions interact with the `generation/engine.py` and other modules in `generation/` to plan and create code.
    *   **Scenario:** User types `angela generate create-project "a python flask app for todos"`. The `create_project` function is called, which uses `code_generation_engine.generate_project(...)` to get a plan, and then `code_generation_engine.create_project_files(...)` to write the files.
    *   **Defines/Controls:** The `angela generate ...` subcommand namespace.

*   `main.py`:
    *   **Purpose:** Defines the main `angela` command, global options, and top-level subcommands.
    *   **Job:**
        *   Initializes the main Typer `app`.
        *   Defines global options like `--debug`, `--version`, `--monitor`. The `--help` option is automatically handled by Typer.
        *   Defines the primary `request` command, which takes natural language input and passes it to the `orchestrator`.
        *   Defines other top-level commands like `init` (to configure Angela), `status` (to show Angela's status), and `shell` (to launch an interactive Angela session).
        *   Includes hidden commands like `--notify` (for shell hooks) and `--completions` (for shell auto-completion).
    *   **Scenario:**
        *   User types `angela --help`: Typer, configured in this file, displays the main help message.
        *   User types `angela "list all text files"`: This is implicitly `angela request "list all text files"`. The `request` function in this file is called, which passes the string to `orchestrator.process_request(...)`.
        *   User types `angela init`: The `init` function in this file is called to guide the user through API key setup.
    *   **Defines/Controls:** The main `angela` command, its global behavior, and top-level actions.

*   `workflows.py`:
    *   **Purpose:** Provides CLI commands for managing user-defined workflows.
    *   **Job:** Defines commands like `angela workflows list`, `angela workflows create <name>`, `angela workflows run <name>`, `angela workflows export <name>`. These functions interact with the `workflows/manager.py` and `workflows/sharing.py`.
    *   **Scenario:** User types `angela workflows run backup_my_documents`. The `run_workflow` function is called, which retrieves the "backup_my_documents" workflow from `workflow_manager` and executes its steps.
    *   **Defines/Controls:** The `angela workflows ...` subcommand namespace.

---

**`context/` Directory:** Context Management

*   **Overall Purpose:** Gathers, manages, and provides all contextual information Angela needs to operate intelligently. This includes information about the user's environment, current project, session activity, and preferences.
*   `__init__.py`:
    *   **Purpose:** Initializes the `context` package.
    *   **Job:** Exports key context managers and utilities like `context_manager`, `session_manager`, `history_manager`, `file_resolver`, `project_inference`, etc., making them easily accessible. It also defines an `initialize_project_inference` function that can be called to start project analysis in the background.
    *   **Defines/Controls:** The public interface of the `context` package.

*   `enhanced_file_activity.py` (contains `EnhancedFileActivityTracker`):
    *   **Purpose:** To track file modifications at a more granular level, understanding changes to specific code entities (functions, classes).
    *   **Job:** Extends `FileActivityTracker`. When a file changes, it can use `ai/semantic_analyzer.py` to compare the old and new versions of the code to identify which functions or classes were added, modified, or deleted.
    *   **Scenario:** User edits a Python file and changes a function. This tracker, when invoked (likely by a file watcher or after a save operation if integrated with an editor), would detect that "function `calculate_total` in `billing.py` was modified."
    *   **Defines/Controls:** Fine-grained tracking of code entity changes.

*   `enhancer.py` (contains `ContextEnhancer`):
    *   **Purpose:** To enrich the basic context with more detailed information from various sources.
    *   **Job:** Takes a base context dictionary (e.g., from `context_manager`) and adds information from `project_inference`, `file_activity_tracker`, `file_resolver`, etc. It acts as an aggregator for creating a comprehensive context snapshot.
    *   **Scenario:** Before the `orchestrator` sends a request to the AI, it calls `context_enhancer.enrich_context(...)` to get the most complete picture of the user's current situation, including project type, recently accessed files, and any resolved file references from the user's query.
    *   **Defines/Controls:** Aggregation and enrichment of contextual data.

*   `file_activity.py` (contains `FileActivityTracker`, `ActivityType`):
    *   **Purpose:** To track basic file system activities like creation, modification, deletion, and viewing.
    *   **Job:** Provides methods like `track_file_creation(...)`, `track_file_modification(...)`. It maintains a list of recent activities and can report on the most active files. This information is used to provide context to the AI (e.g., "user recently modified file X").
    *   **Scenario:**
        *   User runs `angela files rm old.txt`. The `execution/filesystem.py` module, after deleting the file, calls `file_activity_tracker.track_file_deletion("old.txt", ...)`.
        *   User runs `angela request "summarize my_script.py"`. The `ai/content_analyzer.py` calls `file_activity_tracker.track_file_viewing("my_script.py", ...)`.
    *   **Defines/Controls:** Basic file event tracking.

*   `file_detector.py`:
    *   **Purpose:** To identify the type of a file (e.g., Python script, JSON, Markdown, binary) and its programming language if applicable.
    *   **Job:** Uses file extensions, MIME types, and sometimes content analysis (like checking for shebangs `#!/usr/bin/python`) to determine file characteristics.
    *   **Scenario:**
        *   User asks to "analyze `config.json`". `detect_file_type("config.json")` returns that it's a JSON file.
        *   The `ai/content_analyzer.py` uses this to tailor its analysis prompt for JSON content.
    *   **Defines/Controls:** File type and language identification logic.

*   `file_resolver.py` (contains `FileResolver`):
    *   **Purpose:** To find the actual path to a file when the user provides a potentially ambiguous reference (e.g., "my_config_file", "the main script").
    *   **Job:** Uses strategies like exact matching, fuzzy name matching, checking recent files, and searching within the project or current directory to resolve a reference to a `Path` object.
    *   **Scenario:** User types `angela request "edit my_config"`. The orchestrator uses `FileResolver` to find `my_config.json` or `my_config.yaml` in the project.
    *   **Defines/Controls:** Logic for resolving ambiguous file names.

*   `history.py` (contains `HistoryManager`, `CommandRecord`):
    *   **Purpose:** To store and manage the history of commands executed through Angela.
    *   **Job:** Saves each command, the natural language request that led to it, and whether it was successful. It can retrieve recent commands, calculate command frequency/success rates, and find similar past commands. This history is used to improve AI suggestions and provide context.
    *   **Scenario:**
        *   After a command is executed, `HistoryManager` records it.
        *   When a user makes a new request, Angela might check `HistoryManager` for similar past successful commands to help the AI.
        *   If a command fails, `ErrorAnalyzer` might use history to see if a similar error had a known fix.
    *   **Defines/Controls:** Storage and retrieval of command execution history.

*   `manager.py` (contains `ContextManager`):
    *   **Purpose:** To provide basic, frequently needed context about the user's current environment.
    *   **Job:** Detects and provides the current working directory (CWD), the root directory of the current project (if any, by looking for markers like `.git`, `package.json`), and the type of project (e.g., "python", "node"). It can also list directory contents and get basic info about a specific file.
    *   **Scenario:** When any `angela` command starts, `ContextManager` is used to understand where the user is and if they are inside a known project. This info is passed to the AI and other components.
    *   **Defines/Controls:** Core environmental context (CWD, project root/type).

*   `preferences.py` (contains `PreferencesManager`, `UserPreferences`):
    *   **Purpose:** To manage user-specific settings for Angela.
    *   **Job:** Loads and saves user preferences (e.g., default trust levels for command execution, UI settings) from a configuration file (`~/.config/angela/preferences.json`). Other parts of Angela query this manager to tailor their behavior.
    *   **Scenario:**
        *   User runs `angela init` and sets `confirm_all_actions` to true. This preference is saved via `PreferencesManager`.
        *   When Angela suggests a command, `safety/confirmation.py` checks `PreferencesManager` to see if it should ask for confirmation even for low-risk commands.
    *   **Defines/Controls:** User-configurable settings.

*   `project_inference.py` (contains `ProjectInference`):
    *   **Purpose:** To perform a more in-depth analysis of a project to understand its type, structure, dependencies, and frameworks used.
    *   **Job:** Scans project files (e.g., `requirements.txt`, `package.json`, `pom.xml`, source code files) to infer details beyond what `ContextManager` provides. This is more resource-intensive and might be run in the background or on demand.
    *   **Scenario:** When a user enters a project directory, `ProjectInference` might be triggered (perhaps by `ContextEnhancer`) to analyze it. The results (e.g., "This is a Python Django project using PostgreSQL and Celery") are then used to provide more relevant AI suggestions and code generation.
    *   **Defines/Controls:** Detailed project analysis and technology detection.

*   `project_state_analyzer.py` (contains `ProjectStateAnalyzer`):
    *   **Purpose:** To provide real-time, detailed information about the current state of a project.
    *   **Job:** Integrates with tools like Git to get status (current branch, uncommitted changes), checks test status (e.g., from coverage reports), build health (e.g., from CI system or build artifacts), pending database migrations, dependency health (outdated packages), and code quality issues (linting, TODOs).
    *   **Scenario:**
        *   User asks "what should I work on next?". `ProjectStateAnalyzer` might report: "Git branch 'feature-x' has 3 uncommitted files. Tests are failing for `test_payment.py`. There are 2 pending database migrations."
        *   This information is fed to the `ai/enhanced_prompts.py` to give the LLM rich context.
    *   **Defines/Controls:** Real-time analysis of a project's dynamic state.

*   `semantic_context_manager.py` (contains `SemanticContextManager`):
    *   **Purpose:** To be the central hub for all semantic understanding, integrating code analysis, project state, and file activity.
    *   **Job:** Coordinates `ai/semantic_analyzer.py`, `context/project_state_analyzer.py`, and `context/enhanced_file_activity.py` to provide a unified, rich semantic context. It manages caching of analysis results and can answer queries like "get info for entity X" or "find code related to Y".
    *   **Scenario:** When the `orchestrator` needs deep understanding for a complex request (e.g., "refactor the user authentication module"), it queries `SemanticContextManager` to get a comprehensive picture of the relevant code, its dependencies, and the project's current state.
    *   **Defines/Controls:** Centralized access to deep semantic project and code understanding.

*   `session.py` (contains `SessionManager`, `EntityReference`):
    *   **Purpose:** To maintain context within a single, continuous interaction session with Angela.
    *   **Job:** Tracks recently mentioned entities (files, commands, results), recent commands, and recent results. This helps Angela understand pronouns ("it", "that file") and maintain conversational flow. Sessions might expire after a period of inactivity.
    *   **Scenario:**
        *   User: `angela request "list files in /tmp"`
        *   Angela: (lists files)
        *   User: `angela request "now count them"` -> `SessionManager` helps Angela understand "them" refers to the files listed in the previous command.
    *   **Defines/Controls:** Short-term conversational memory.

---

**`core/` Directory:** Core Infrastructure

*   **Overall Purpose:** Provides fundamental, low-level components and patterns used throughout the Angela application, helping with organization and decoupling.
*   `__init__.py`:
    *   **Purpose:** Initializes the `core` package.
    *   **Job:** Exports the `registry` and `event_bus`.
    *   **Defines/Controls:** Public interface of the `core` package.

*   `events.py` (contains `EventBus`):
    *   **Purpose:** Implements a system-wide event bus for decoupled communication.
    *   **Job:** Allows different parts of Angela to publish events (e.g., "command_executed", "file_changed") and other parts to subscribe to these events and react accordingly, without direct dependencies on each other.
    *   **Scenario:**
        *   `monitoring/background.py` detects a Git status change and publishes a `monitoring:git_status` event.
        *   `monitoring/proactive_assistant.py` is subscribed to this event and, upon receiving it, decides whether to show a suggestion to the user.
    *   **Defines/Controls:** A publish-subscribe mechanism for internal communication.

*   `registry.py` (contains `ServiceRegistry`):
    *   **Purpose:** Implements a service locator pattern to manage and provide access to shared service instances, helping to break circular dependencies.
    *   **Job:** Holds a dictionary of named services. Components can register their instances (e.g., `registry.register("execution_engine", my_engine_instance)`) and other components can retrieve them (`engine = registry.get("execution_engine")`).
    *   **Scenario:**
        *   `angela/__init__.py` calls `core/service_registration.py`.
        *   `core/service_registration.py` imports, instantiates, and registers `execution_engine` from `execution/engine.py`.
        *   Later, `orchestrator.py` needs to execute a command. Instead of `from angela.execution.engine import execution_engine` (which might cause a circular import if `execution_engine` also somehow needed `orchestrator`), it does `engine = registry.get("execution_engine")`.
    *   **Defines/Controls:** A central point for accessing shared services.

*   `service_registration.py`:
    *   **Purpose:** To centralize the registration of core services with the `ServiceRegistry`.
    *   **Job:** This file imports various core components (like `execution_engine`, `orchestrator`, `context_enhancer`) and registers them with the global `registry` instance. This is typically called once at application startup.
    *   **Scenario:** When `angela/__init__.py` calls `init_application()`, `init_application()` calls `register_core_services()` from this file. This ensures that all essential services are available in the `registry` before any user commands are processed.
    *   **Defines/Controls:** The process of making core services globally accessible via the registry.

---

**`execution/` Directory:** Command and File Operation Execution

*   **Overall Purpose:** Handles the actual execution of shell commands and file system operations, including safety checks, error handling, and rollback capabilities.
*   `__init__.py`:
    *   **Purpose:** Initializes the `execution` package.
    *   **Job:** Exports key components like `execution_engine`, `adaptive_engine`, `rollback_manager`, and filesystem functions, making them available for other parts of Angela.
    *   **Defines/Controls:** Public interface of the `execution` package.

*   `adaptive_engine.py` (contains `AdaptiveExecutionEngine`):
    *   **Purpose:** To provide a more intelligent and context-aware command execution layer.
    *   **Job:** Wraps the basic `ExecutionEngine`. Before executing a command, it:
        1.  Classifies its risk (`safety/classifier.py`).
        2.  Analyzes its potential impact.
        3.  Generates a preview (`safety/preview.py`).
        4.  Gets adaptive confirmation from the user (`safety/adaptive_confirmation.py`), considering user preferences and command history.
        5.  After execution, it records the command in history and, if it failed, uses `ai/analyzer.py` (ErrorAnalyzer) to suggest fixes.
    *   **Scenario:** User types `angela request "delete all .tmp files"`. The orchestrator gets the command `find . -name '*.tmp' -delete` from the AI. It passes this to `AdaptiveExecutionEngine`. The engine classifies it as high risk, shows a preview of files to be deleted, asks "Are you sure?", and only if confirmed, executes it via `ExecutionEngine`.
    *   **Defines/Controls:** Context-sensitive and safe command execution workflow.

*   `engine.py` (contains `ExecutionEngine`):
    *   **Purpose:** To provide the core functionality for running shell commands.
    *   **Job:** Takes a command string, executes it as a subprocess, captures its `stdout`, `stderr`, and `return_code`. It can optionally perform safety checks (delegating to `safety/validator.py`) before running.
    *   **Scenario:** The `AdaptiveExecutionEngine` (or any other component needing to run a command) calls `ExecutionEngine.execute_command("ls -l")`. This module uses Python's `asyncio.create_subprocess_exec` to run `ls -l`.
    *   **Defines/Controls:** The fundamental mechanism for running external commands.

*   `error_recovery.py` (contains `ErrorRecoveryManager`):
    *   **Purpose:** To handle errors that occur during the execution of multi-step plans or complex workflows and attempt recovery.
    *   **Job:** When a step in a plan fails, this manager:
        1.  Analyzes the error (using `ai/analyzer.py`).
        2.  Generates potential recovery strategies (e.g., retry, modify command, try alternative, prepare environment).
        3.  Can attempt automatic recovery for high-confidence strategies or guide the user through recovery options.
        4.  Learns from successful recoveries to improve future suggestions.
    *   **Scenario:** A multi-step plan includes `pip install my_package` which fails because `my_package` doesn't exist. `ErrorRecoveryManager` might analyze the "package not found" error and suggest searching for similar package names or checking PyPI. If a fix is applied and succeeds, it learns this pattern.
    *   **Defines/Controls:** Automated and guided error recovery logic for complex operations.

*   `filesystem.py`:
    *   **Purpose:** To provide a safe and abstracted way to perform common file system operations.
    *   **Job:** Contains functions like `create_directory`, `delete_file`, `read_file`, `write_file`, `copy_file`, `move_file`. These functions often include safety checks (delegating to `safety/`) and can create backups for rollback purposes (interacting with `execution/rollback.py`).
    *   **Scenario:**
        *   User: `angela files mkdir new_docs` -> `cli/files.py` calls `create_directory("new_docs", ...)` from this module.
        *   The `generation/engine.py` needs to write a generated code file; it uses `write_file(...)` from here.
    *   **Defines/Controls:** Abstracted and safe file system interactions.

*   `hooks.py` (contains `ExecutionHooks`):
    *   **Purpose:** To allow other parts of Angela to react to events before and after commands or file operations are executed.
    *   **Job:** Provides a registration mechanism for pre-execution and post-execution hooks. For example, before a command runs, it might analyze the command for file paths. After a command runs, it might track which files were created, modified, or deleted based on the command type (e.g., `touch` creates, `rm` deletes).
    *   **Scenario:**
        *   The `AdaptiveExecutionEngine` is about to run `cat my_file.txt`. It calls `execution_hooks.pre_execute_command(...)`.
        *   A registered hook in `ExecutionHooks` might then call `file_activity_tracker.track_file_viewing("my_file.txt", ...)` because `cat` is a viewing command.
    *   **Defines/Controls:** A system for triggering actions around command/file executions, primarily for context tracking.

*   `rollback_commands.py`:
    *   **Purpose:** Defines the CLI commands for interacting with the rollback system.
    *   **Job:** Implements commands like `angela rollback list`, `angela rollback operation <id>`, `angela rollback transaction <id>`. These functions use the `RollbackManager` to list and perform rollbacks.
    *   **Scenario:** User runs `angela files rm important_doc`. Later, they realize it was a mistake and run `angela rollback last`. The `rollback_last` function (which calls `rollback_operation`) in this file interacts with `RollbackManager` to restore the file.
    *   **Defines/Controls:** The `angela rollback ...` subcommand namespace.

*   `rollback.py` (contains `RollbackManager`, `OperationRecord`, `Transaction`):
    *   **Purpose:** To manage the history of operations and provide the ability to undo them.
    *   **Job:**
        1.  Records operations (file system changes, content manipulations, command executions) with enough detail to undo them. This includes storing backups of files before modification/deletion.
        2.  Groups operations into transactions for undoing multi-step actions.
        3.  Provides functions to list recent operations/transactions and to perform rollbacks.
        4.  For command rollbacks, it might use predefined compensating actions (e.g., `git reset` for `git add`).
    *   **Scenario:**
        *   When `execution/filesystem.py` deletes a file, it first calls `RollbackManager.create_backup_file(...)` and then `RollbackManager.record_file_operation(...)`.
        *   When the user requests a rollback via `cli/rollback_commands.py`, the `RollbackManager` finds the recorded operation and uses its backup/undo info to revert the change.
    *   **Defines/Controls:** The logic for tracking and undoing operations.

---

**`generation/` Directory:** Code and Documentation Generation

*   **Overall Purpose:** Contains all logic related to generating new code, entire projects, documentation, and analyzing/refining software architecture.
*   `__init__.py`:
    *   **Purpose:** Initializes the `generation` package.
    *   **Job:** Exports key components like `code_generation_engine`, `project_planner`, `documentation_generator`, etc.
    *   **Defines/Controls:** Public interface of the `generation` package.

*   `architecture.py` (contains `ArchitecturalAnalyzer`, pattern/anti-pattern classes):
    *   **Purpose:** To analyze the architectural design of a software project.
    *   **Job:** Scans project files and structure to detect common architectural patterns (like MVC) and anti-patterns (like God Objects, Single Responsibility Principle violations). It can then provide recommendations for improvement.
    *   **Scenario:** User runs `angela generate analyze-architecture my_project/`. This module's `ArchitecturalAnalyzer` inspects the project, identifies that it might be a poorly structured MVC or has a class doing too much, and suggests refactoring.
    *   **Defines/Controls:** Logic for architectural analysis and pattern detection.

*   `context_manager.py` (in `generation/`, distinct from `context/manager.py`):
    *   **Purpose:** To manage context specifically during multi-file code generation tasks.
    *   **Job:** Tracks shared entities (classes, functions, interfaces) that are defined in one generated file and might be used or referenced in another generated file. It helps ensure consistency and proper imports/dependencies between newly generated files.
    *   **Scenario:** When `generation/engine.py` is generating a project with a `UserService` and a `UserController`, this manager ensures that if `UserService` is defined first, `UserController` knows how to import and use it correctly when its code is generated.
    *   **Defines/Controls:** Contextual awareness *during* the code generation process itself.

*   `documentation.py` (contains `DocumentationGenerator`):
    *   **Purpose:** To automatically generate documentation for software projects.
    *   **Job:** Can generate README files, API documentation (by parsing source code for comments and structure), user guides, and contributing guides. It uses project information and AI to create these documents.
    *   **Scenario:** User runs `angela generate readme .`. `DocumentationGenerator` analyzes the current project (using `_analyze_project`), builds a prompt, and asks the AI to write a README.md.
    *   **Defines/Controls:** Automated documentation creation.

*   `engine.py` (contains `CodeGenerationEngine`):
    *   **Purpose:** The main engine for orchestrating the generation of code, from single files to entire projects.
    *   **Job:**
        1.  Takes a high-level description (e.g., "create a Python Flask API for a to-do list").
        2.  Uses `generation/planner.py` (or AI directly) to create a `CodeProject` plan, which defines the directory structure and a list of `CodeFile` objects (path, purpose, language, dependencies).
        3.  For each `CodeFile` in the plan, it generates the actual code content, often using AI and the `generation/context_manager.py` to ensure inter-file consistency.
        4.  Uses `execution/filesystem.py` to write the generated files to disk.
        5.  Can also handle adding new features to existing projects by planning new/modified files and generating their content.
    *   **Scenario:** User runs `angela generate create-project "todo app with flask"`. The `cli/generation.py` calls `CodeGenerationEngine.generate_project(...)`. The engine plans the files (`app.py`, `models.py`, `requirements.txt`, etc.), then generates Python code for each, and finally writes them to the specified output directory.
    *   **Defines/Controls:** The core workflow for multi-file code generation.

*   `frameworks.py` (contains `FrameworkGenerator`):
    *   **Purpose:** To provide specialized scaffolding for projects based on popular frameworks (React, Django, Spring, etc.).
    *   **Job:** Contains templates and logic to generate standard directory structures and boilerplate files for specific frameworks. This often involves less AI generation for the basic structure and more template filling, potentially augmented by AI for custom parts.
    *   **Scenario:** User runs `angela generate create-framework-project react "my new frontend"`. `FrameworkGenerator` uses its React-specific logic to create a typical React project structure (`src/`, `public/`, `App.js`, `index.js`, `package.json` with React dependencies).
    *   **Defines/Controls:** Framework-specific project scaffolding.

*   `models.py` (contains `CodeFile`, `CodeProject`):
    *   **Purpose:** Defines the Pydantic data models used by the code generation system.
    *   **Job:** `CodeFile` represents a single file to be generated (its path, content, purpose). `CodeProject` represents the entire project to be generated (name, description, list of `CodeFile`s, dependencies). These models provide structure and validation for the generation process.
    *   **Scenario:** When `generation/planner.py` plans a project, it creates a `CodeProject` instance populated with `CodeFile` instances. The `generation/engine.py` then consumes this `CodeProject` to create the actual files.
    *   **Defines/Controls:** Data structures for representing generated code and projects.

*   `planner.py` (contains `ProjectPlanner`, `ProjectArchitecture`):
    *   **Purpose:** To design the high-level architecture and file structure for new software projects based on a description.
    *   **Job:** Takes a project description and type, and uses AI to propose an architecture (e.g., components, layers, design patterns) and a list of files that should be part of this architecture, along with their purposes and dependencies.
    *   **Scenario:** When `generation/engine.py` needs to generate a new project, it first calls `ProjectPlanner.create_detailed_project_architecture(...)` to get a blueprint. This blueprint (a `ProjectArchitecture` object) is then used to create a `CodeProject` plan.
    *   **Defines/Controls:** AI-driven architectural planning for new projects.

*   `refiner.py` (contains `InteractiveRefiner`):
    *   **Purpose:** To allow users to iteratively improve code that Angela has generated.
    *   **Job:** Takes user feedback on generated code (e.g., "make this function more efficient", "add error handling to this class"), processes this feedback (likely using AI via `review/feedback.py`), and applies the suggested changes to the code.
    *   **Scenario:** Angela generates a Python script. User reviews it and types `angela generate refine-code "add logging to the main function" my_script.py`. `InteractiveRefiner` takes this feedback, the original code of `my_script.py`, and uses AI to generate a new version with logging added.
    *   **Defines/Controls:** Iterative code improvement based on user feedback.

*   `validators.py`:
    *   **Purpose:** To check if the code generated by Angela is syntactically correct for its language.
    *   **Job:** Contains functions like `validate_python`, `validate_javascript`, etc. These functions typically use language-specific tools (e.g., `python -m py_compile` for Python, `node --check` for JavaScript, `tsc --noEmit` for TypeScript) to lint or compile the generated code in a temporary file and report errors.
    *   **Scenario:** After `generation/engine.py` generates the content for `user_service.py`, it calls `validate_code(content, "user_service.py")`. If there's a Python syntax error, the validator reports it, and the engine might try to get the AI to fix it.
    *   **Defines/Controls:** Syntactic validation of generated code.

---

**`integrations/` Directory:** Integration Modules

*   **Overall Purpose:** Contains modules that bridge different major components of Angela, often to avoid circular dependencies or to implement higher-level features that combine functionalities from various parts.
*   `__init__.py`:
    *   **Purpose:** Initializes the `integrations` package.
    *   **Job:** Exports the main integration modules.
    *   **Defines/Controls:** Public interface of the `integrations` package.

*   `enhanced_planner_integration.py`:
    *   **Purpose:** To integrate the `EnhancedTaskPlanner` (from `intent/enhanced_task_planner.py`) into the main `Orchestrator`.
    *   **Job:** It "patches" or extends the orchestrator's `_process_multi_step_request` method to use the more advanced planning and execution capabilities of the `EnhancedTaskPlanner`. This allows the orchestrator to handle more complex step types (like code execution, API calls, loops) defined in `AdvancedTaskPlan`s.
    *   **Scenario:** When the orchestrator determines a user request is multi-step and complex, the patched `_process_multi_step_request` (defined in this integration file) is called. This patched version then uses the `EnhancedTaskPlanner` to create and execute an `AdvancedTaskPlan`.
    *   **Defines/Controls:** How the orchestrator handles advanced, multi-step tasks.

*   `phase12_integration.py` (contains `Phase12Integration`):
    *   **Purpose:** Integrates the most advanced features of Angela, specifically the Universal CLI Translator, Complex Workflow Orchestration, CI/CD Pipeline Automation, and enhanced Proactive Assistance.
    *   **Job:**
        1.  Initializes and verifies these advanced components.
        2.  Provides methods for detecting CI/CD opportunities (`detect_pipeline_opportunities`).
        3.  Suggests and executes complex cross-tool workflows (`suggest_complex_workflow`, `execute_cross_tool_workflow`) by leveraging the `ComplexWorkflowPlanner` and `UniversalCLITranslator`.
        4.  Manages the setup and status of these advanced integrations.
    *   **Scenario:**
        *   User asks `angela "setup a full CI/CD pipeline for my GitHub python project to deploy to AWS S3"`: The orchestrator might route this to `Phase12Integration`. This integration would use `ComplexWorkflowPlanner` to plan steps involving `git`, `aws cli`, and potentially GitHub Actions setup (via `CiCdIntegration`). The `UniversalCLITranslator` would help generate the specific `aws s3 sync` commands.
        *   The `ProactiveAssistant` (V2) might use this integration to suggest automating a sequence of `git`, `docker`, and `kubectl` commands the user frequently runs.
    *   **Defines/Controls:** Orchestration of Angela's most advanced, multi-tool automation capabilities.

*   `semantic_integration.py` (contains `SemanticIntegration`):
    *   **Purpose:** To make semantic code understanding readily available and integrated throughout Angela.
    *   **Job:**
        1.  Coordinates `ai/semantic_analyzer.py`, `context/project_state_analyzer.py`, and `context/file_activity_tracker.py`.
        2.  Provides a unified interface (`get_semantic_context`) for other components to get a rich, semantically-enhanced context.
        3.  Manages caching of semantic analysis to improve performance.
        4.  Can schedule background analysis tasks for projects or files.
        5.  Offers functions like getting summaries of code entities or finding similar code.
    *   **Scenario:**
        *   The `context/enhancer.py` calls `SemanticIntegration.get_semantic_context(...)` to add detailed code and project state understanding to the context before it's used by the AI or planners.
        *   When a user asks to "refactor the `User` class", the `generation/refiner.py` might use `SemanticIntegration` to get the current definition of the `User` class, its methods, and where it's used, to provide better context to the AI for refactoring.
    *   **Defines/Controls:** Centralized access and management of semantic understanding across the application.

---

**`intent/` Directory:** Intent Understanding and Task Planning

*   **Overall Purpose:** Focuses on understanding what the user wants to achieve (their intent) and then planning the necessary steps (actions or commands) to fulfill that intent.
*   `__init__.py`:
    *   **Purpose:** Initializes the `intent` package.
    *   **Job:** Exports core models (`IntentType`, `Intent`, `ActionPlan`) and the base `task_planner`. It also provides lazy loading functions (`get_enhanced_task_planner`, etc.) for more advanced planners to help manage potential circular dependencies if those planners need to import things that also import from `intent/__init__.py`.
    *   **Defines/Controls:** Public interface of the `intent` package.

*   `complex_workflow_planner.py` (contains `ComplexWorkflowPlanner`, `WorkflowStep`, `ComplexWorkflowPlan`):
    *   **Purpose:** To plan and orchestrate very complex, multi-tool workflows that go beyond simple command sequences.
    *   **Job:** Extends `EnhancedTaskPlanner`. It can define workflows with various step types (commands, tool interactions, API calls, decisions, loops, custom code). It manages data flow between these steps, allowing output from one step to be used as input to another.
    *   **Scenario:** User asks `angela "setup my new microservice: create a git repo, scaffold a python flask app, build a docker image, push it to ECR, and then deploy it to my Kubernetes staging cluster."` The `Orchestrator` (likely via `Phase12Integration`) would use `ComplexWorkflowPlanner` to:
        1.  Plan steps involving `git`, `python` (or a code generator), `docker`, `aws ecr`, and `kubectl`.
        2.  Define how data (like the Docker image name or Git commit hash) flows between these steps.
        3.  Execute this entire pipeline.
    *   **Defines/Controls:** Advanced, multi-tool, data-aware workflow orchestration.

*   `enhanced_task_planner.py` (contains `CoreEnhancedTaskPlanner`, `EnhancedTaskPlanner`, `StepExecutionContext`):
    *   **Purpose:** To extend the basic `TaskPlanner` with support for more sophisticated execution steps and data flow.
    *   **Job:**
        1.  Introduces more step types beyond simple commands, such as executing Python/JavaScript/shell code snippets (`PlanStepType.CODE`), making API calls (`PlanStepType.API`), performing file operations (`PlanStepType.FILE`), handling conditional logic (`PlanStepType.DECISION`), and looping (`PlanStepType.LOOP`).
        2.  Manages an `StepExecutionContext` which includes variables that can be passed between steps, allowing for data flow.
        3.  Provides more robust execution logic for these advanced step types, including basic sandboxing for code execution.
    *   **Scenario:** User asks `angela "for each .txt file in 'reports/', count its lines and if it's more than 100 lines, move it to 'large_reports/'."`
        *   The `EnhancedTaskPlanner` (or `SemanticTaskPlanner` which builds upon it) would create an `AdvancedTaskPlan`.
        *   This plan would have a `LOOP` step iterating over `*.txt` files.
        *   Inside the loop, a `COMMAND` step (`wc -l <filename>`) whose output is captured.
        *   A `DECISION` step checking if line count > 100.
        *   A `COMMAND` step (`mv <filename> large_reports/`) executed if the decision is true.
    *   **Defines/Controls:** Execution logic for advanced, structured task plans with diverse step types and data flow.

*   `models.py` (contains `IntentType`, `Intent`, `ActionPlan`):
    *   **Purpose:** Defines the Pydantic data models for representing user intents and basic action plans.
    *   **Job:**
        *   `IntentType`: An enum for different categories of user intent (e.g., file search, system info).
        *   `Intent`: Stores the classified `IntentType`, any extracted entities (like filenames or search terms), and the original request.
        *   `ActionPlan`: Represents a simple plan, usually a list of commands and their explanations, derived from an `Intent`.
    *   **Scenario:**
        *   `ai/intent_analyzer.py` processes "show me text files" and creates an `Intent` object: `type=IntentType.FILE_SEARCH`, `entities={"pattern": "*.txt"}`.
        *   The `Orchestrator` or a simple planner might then create an `ActionPlan`: `commands=["find . -name '*.txt'"]`, `explanations=["finds text files"]`.
    *   **Defines/Controls:** Basic data structures for intent and simple plans.

*   `planner.py` (contains `TaskPlanner`, `PlanStep`, `TaskPlan`, `AdvancedPlanStep`, `AdvancedTaskPlan`):
    *   **Purpose:** Core task planning logic. This file seems to define both basic and advanced planning models and the base `TaskPlanner`.
    *   **Job:**
        *   `TaskPlanner`: The base class. Its `plan_task` method can determine if a request needs simple or advanced planning.
        *   `_create_basic_plan`: Uses AI to generate a simple sequence of `PlanStep`s (command, explanation, dependencies, risk) for straightforward goals.
        *   `_generate_advanced_plan`: Uses AI to generate a more complex `AdvancedTaskPlan` with various `AdvancedPlanStep` types (command, code, file, decision, API, loop) for more involved requests.
        *   `execute_plan`: Can execute both basic `TaskPlan`s and `AdvancedTaskPlan`s (delegating advanced execution to `EnhancedTaskPlanner`'s core logic).
    *   **Scenario:**
        *   User: `angela "create a dir 'test' and a file 'foo.txt' in it"` -> `TaskPlanner` might generate a basic `TaskPlan` with two `PlanStep`s: `mkdir test` and `touch test/foo.txt`.
        *   User: `angela "if 'config.json' exists, print its content, otherwise create it with default settings"` -> `TaskPlanner` would generate an `AdvancedTaskPlan` with a `DECISION` step checking for `config.json`, and two branches with `COMMAND` or `FILE` steps.
    *   **Defines/Controls:** The primary logic for decomposing user goals into executable plans of varying complexity.

*   `semantic_task_planner.py` (contains `SemanticTaskPlanner`, `IntentClarification`):
    *   **Purpose:** To enhance task planning by deeply integrating semantic code understanding and improving how ambiguous requests are handled.
    *   **Job:**
        1.  Extends `EnhancedTaskPlanner`.
        2.  Before planning, it uses `ai/semantic_analyzer.py` and `context/project_state_analyzer.py` to enrich the context with detailed understanding of the code and project.
        3.  Analyzes the user's intent with this richer context.
        4.  If ambiguities are detected (e.g., "which `User` class do you mean?"), it can generate `IntentClarification` questions to ask the user via `shell/inline_feedback.py`.
        5.  Once the intent is clear, it decomposes the goal into sub-goals and then creates a more semantically-aware execution plan.
    *   **Scenario:** User says `angela "refactor the process_data function to use the new UserV2 model"`.
        *   `SemanticTaskPlanner` first gets semantic info: "There are two `process_data` functions, one in `moduleA.py` and one in `moduleB.py`. `UserV2` is defined in `models_v2.py`."
        *   It might then ask for clarification: "Which `process_data` function do you want to refactor? 1. `moduleA.py:process_data` 2. `moduleB.py:process_data`".
        *   Once clarified, it plans the refactoring steps, understanding the function's signature, callers, and the structure of `UserV2`.
    *   **Defines/Controls:** Highly context-aware and interactive task planning using deep code understanding.

---

**`interfaces/` Directory:** Component Interfaces (Abstract Base Classes)

*   **Overall Purpose:** Defines abstract contracts (interfaces) for key components. This promotes loose coupling and allows for different implementations of a component to be used interchangeably as long as they adhere to the defined interface.
*   `__init__.py`: Exports the defined interfaces.
*   `execution.py` (defines `CommandExecutor`, `AdaptiveExecutor`):
    *   **Purpose:** Defines the expected methods for any component that executes commands.
    *   **Job:** `CommandExecutor` likely defines a basic `execute_command` method. `AdaptiveExecutor` might extend this or define a more context-aware execution method.
    *   **Scenario:** `execution/engine.py`'s `ExecutionEngine` would implement `CommandExecutor`. `execution/adaptive_engine.py`'s `AdaptiveExecutionEngine` would implement `AdaptiveExecutor`. The `Orchestrator` could then be programmed to work with any `AdaptiveExecutor` without knowing its specific implementation.
    *   **Defines/Controls:** The contract for command execution services.

*   `safety.py` (defines `SafetyValidator`):
    *   **Purpose:** Defines the expected methods for any component that validates the safety of commands or operations.
    *   **Job:** Likely defines methods like `check_command_safety` or `validate_operation`.
    *   **Scenario:** `safety/validator.py` would implement `SafetyValidator`. The `execution/engine.py` or `adaptive_engine.py` could use any `SafetyValidator` to check commands before running them.
    *   **Defines/Controls:** The contract for safety validation services.

---

**`monitoring/` Directory:** Background Monitoring and Proactive Assistance

*   **Overall Purpose:** Implements features that run in the background to observe the user's environment and actions, offering timely and relevant help or warnings without explicit user requests.
*   `__init__.py`: Exports the main monitoring components.
*   `background.py` (contains `BackgroundMonitor`):
    *   **Purpose:** The core engine for running various background monitoring tasks.
    *   **Job:** Manages a set of asynchronous monitoring tasks (e.g., for Git status, file changes, system resources). It starts, stops, and restarts these tasks as needed, and handles errors within them. It can publish events via the `EventBus` or call registered callbacks when insights are found.
    *   **Scenario:** When Angela starts with the `--monitor` flag, `BackgroundMonitor.start_monitoring()` is called. It then launches tasks like `_monitor_git_status()` which periodically checks `git status`.
    *   **Defines/Controls:** The lifecycle and management of background monitoring processes.

*   `network_monitor.py` (contains `NetworkMonitor`):
    *   **Purpose:** To specifically monitor network-related aspects.
    *   **Job:** Checks local service health (e.g., are `localhost:8000` or `localhost:5432` up?), external API status (not fully shown but implied), general network connectivity, and availability of updates for project dependencies (e.g., new versions of Python packages or npm modules).
    *   **Scenario:**
        *   If the user is working on a web project and their local development server on port 3000 stops responding, `NetworkMonitor` might detect this and `ProactiveAssistant` could suggest checking the server logs or restarting it.
        *   It might periodically check `pip list --outdated` and suggest updating packages.
    *   **Defines/Controls:** Monitoring of network services and dependency updates.

*   `notification_handler.py` (contains `NotificationHandler`):
    *   **Purpose:** To process notifications sent from shell integration hooks.
    *   **Job:** The shell scripts (`angela_enhanced.bash`, `angela_enhanced.zsh`) call `angela --notify <type> <args>` before and after commands execute, or when the directory changes. This file's `NotificationHandler` receives these calls.
        *   `pre_exec`: Records command start time, updates session context.
        *   `post_exec`: Records command duration, exit code, errors. Updates command history and statistics. Might trigger error analysis for failed commands.
        *   `dir_change`: Updates `context_manager` with the new CWD, updates recent directory list.
    *   **Scenario:**
        1.  User types `ls -l` and hits Enter in a shell with enhanced integration.
        2.  `angela_preexec` (in `.zshrc`) calls `angela --notify pre_exec "ls -l"`.
        3.  `NotificationHandler._handle_pre_exec("ls -l")` runs.
        4.  The `ls -l` command executes.
        5.  `angela_precmd` (in `.zshrc`) calls `angela --notify post_exec "ls -l" 0 1` (command, exit code, duration).
        6.  `NotificationHandler._handle_post_exec(...)` runs.
    *   **Defines/Controls:** Processing of real-time events from the user's shell.

*   `proactive_assistant.py` (contains `ProactiveAssistant`):
    *   **Purpose:** To provide intelligent, contextual, and timely suggestions, warnings, or insights to the user. This is the "V2" or enhanced version.
    *   **Job:**
        1.  Subscribes to events from the `EventBus` (e.g., monitoring events, command errors).
        2.  Receives insights directly from `BackgroundMonitor` via callbacks.
        3.  Analyzes these events and insights in conjunction with current context, history, and session information.
        4.  Uses a set of pattern detectors to identify common issues or opportunities (e.g., missing dependencies, permission errors, repeated commands).
        5.  Decides if and what kind of assistance to offer (suggestion, warning, optimization idea).
        6.  Uses `shell/formatter.py` or `shell/inline_feedback.py` to present this assistance to the user, respecting cooldown periods to avoid being annoying.
    *   **Scenario:**
        *   `BackgroundMonitor` detects many uncommitted Git changes and publishes an event. `ProactiveAssistant` receives this, checks if it's an appropriate time to suggest, and then might print "You have many uncommitted changes. Consider running `git commit`."
        *   `NotificationHandler` reports a command failed with "Permission denied". `ProactiveAssistant` detects this pattern and suggests trying the command with `sudo`.
    *   **Defines/Controls:** The logic for generating and delivering proactive help.

---

**`review/` Directory:** Code Review and Feedback Processing

*   **Overall Purpose:** Provides tools for comparing code versions (diffs) and for processing user feedback to improve code, often using AI.
*   `__init__.py`: Exports `diff_manager` and `feedback_manager`.
*   `diff_manager.py` (contains `DiffManager`):
    *   **Purpose:** To generate and apply differences (diffs) between text or code.
    *   **Job:** Can take two strings (or file contents) and produce a unified diff (like `git diff` output) or an HTML diff. It can also attempt to apply a diff patch to an original string to get the modified version.
    *   **Scenario:**
        *   When `ai/content_analyzer.py` modifies a file, it uses `DiffManager` to generate a diff showing the user what changed.
        *   When `review/feedback.py` gets an improved code version from the AI, it uses `DiffManager` to show the changes.
        *   If a rollback needs to revert a content manipulation, `DiffManager` might be used to apply a reversed diff.
    *   **Defines/Controls:** Diff generation and application.

*   `feedback.py` (contains `FeedbackManager`):
    *   **Purpose:** To process natural language feedback from the user about generated code and use AI to refine that code.
    *   **Job:**
        1.  Takes user feedback (e.g., "this function is too complex", "add error handling here"), the original code, and context.
        2.  Builds a prompt for the AI, asking it to improve the code based on the feedback.
        3.  Gets the improved code from the AI.
        4.  Generates a diff between the original and improved code.
        5.  Can also apply these refinements to project files, creating backups.
    *   **Scenario:**
        *   Angela generates a Python function. The user reviews it and says `angela generate refine-code "add a docstring to this function" my_func.py`.
        *   `cli/generation.py` calls `FeedbackManager.process_feedback(...)`.
        *   `FeedbackManager` sends the original code and "add a docstring" to the AI, gets back the code with a docstring, and shows the user the diff. If the user confirms, it writes the new code to `my_func.py`.
    *   **Defines/Controls:** AI-driven code refinement based on user feedback.

---

**`safety/` Directory:** Safety and Confirmation Mechanisms

*   **Overall Purpose:** Ensures that Angela operates safely, especially when suggesting or executing commands that could be destructive or have unintended consequences.
*   `__init__.py`:
    *   **Purpose:** Initializes the `safety` package.
    *   **Job:** Exports key safety functions like `check_command_safety`, `classify_command_risk`, `generate_preview`, `get_confirmation`. It also registers some of these with the `core/registry.py` so they can be accessed without direct imports, preventing circular dependencies (e.g., if `execution/engine.py` needs safety checks, and `safety` modules somehow needed `execution` components).
    *   **Defines/Controls:** The main public interface for safety checks.

*   `adaptive_confirmation.py`:
    *   **Purpose:** To provide a more intelligent confirmation system that adapts to user behavior and preferences.
    *   **Job:** Extends the basic confirmation. It might skip confirmation for commands that the user has run successfully many times and are deemed low risk, or if the user has explicitly trusted a command via `PreferencesManager`. It also offers to "learn" or trust commands after successful high-risk executions if the user agrees.
    *   **Scenario:**
        *   User frequently runs `ls -l` (low risk). After a few times, `AdaptiveConfirmation` might stop asking for confirmation if the user preferences allow.
        *   User confirms and successfully runs a risky command like `sudo apt update`. `AdaptiveConfirmation` might ask, "You ran this risky command successfully. Would you like to trust it for future auto-execution?"
    *   **Defines/Controls:** Smart, context-aware user confirmation logic.

*   `classifier.py` (contains `classify_command_risk`, `analyze_command_impact`):
    *   **Purpose:** To assess the potential risk and impact of a shell command.
    *   **Job:**
        *   `classify_command_risk`: Takes a command string and matches it against a list of predefined `RISK_PATTERNS` (e.g., `rm -rf` is CRITICAL, `ls` is SAFE). It returns a risk level (integer from `constants.RISK_LEVELS`) and a reason.
        *   `analyze_command_impact`: Tries to determine what a command might do (e.g., delete files, create files, modify attributes) by simple lexical analysis of the command and its arguments.
    *   **Scenario:** Before `execution/adaptive_engine.py` runs a command, it calls `classify_command_risk` to determine if it's, say, a HIGH risk operation. This risk level is then used by `safety/confirmation.py` to decide how to ask for user confirmation.
    *   **Defines/Controls:** Risk assessment and impact analysis for commands.

*   `confirmation.py` (contains `get_confirmation`, `requires_confirmation`):
    *   **Purpose:** To handle the basic user confirmation workflow for potentially risky operations.
    *   **Job:**
        *   `requires_confirmation`: Checks user preferences (`config_manager.config.user.confirm_all_actions` or `constants.DEFAULT_CONFIRMATION_REQUIREMENTS`) to see if a given risk level needs confirmation.
        *   `get_confirmation`: If confirmation is needed, it displays the command, its risk level, reason, impact analysis, and any preview using `rich` components. It then prompts the user "Do you want to proceed? (y/n)".
    *   **Scenario:** `AdaptiveExecutionEngine` determines a command is MEDIUM risk. It calls `get_confirmation(...)`. This function displays the command details and asks the user to confirm.
    *   **Defines/Controls:** The user interaction logic for confirming operations.

*   `preview.py` (contains `generate_preview` and specific `preview_` functions):
    *   **Purpose:** To generate a human-readable preview of what a command is likely to do *before* it's executed.
    *   **Job:**
        *   `generate_preview`: Takes a command string. If it's a known command (like `rm`, `mkdir`, `cp`), it calls a specific preview function (e.g., `preview_rm`).
        *   Specific preview functions (e.g., `preview_rm`): Analyze the command's arguments (e.g., files to be deleted by `rm`, directories to be created by `mkdir`) and try to predict the outcome. For `rm`, it might list files that would be deleted. For `mkdir`, it shows which directories would be created.
        *   For unknown commands, it might try to run the command with a `--dry-run` flag if supported by that tool.
    *   **Scenario:** User types `angela request "delete all *.log files"`. AI suggests `rm *.log`. Before asking for confirmation, `generate_preview("rm *.log")` is called. `preview_rm` expands `*.log` to `debug.log`, `error.log` and returns a string like "Will remove file: debug.log\nWill remove file: error.log". This preview is shown to the user.
    *   **Defines/Controls:** Prediction of command effects.

*   `validator.py` (contains `validate_command_safety`, `validate_operation`):
    *   **Purpose:** To perform strict validation of commands and operations against a list of explicitly dangerous patterns.
    *   **Job:**
        *   `validate_command_safety`: Checks a command string against `DANGEROUS_PATTERNS` (e.g., `rm -rf /`, `mkfs /dev/sda`). If a match is found, the command is deemed invalid and unsafe. It also checks if a command requires superuser privileges when Angela isn't running as root.
        *   `validate_operation`: Validates higher-level file operations (like those defined in `execution/filesystem.py`) for safety, e.g., checking permissions before a write operation.
    *   **Scenario:**
        *   AI suggests `sudo rm -rf /some/path`. `validate_command_safety` checks if Angela is running as root. If not, it might block it or require extra caution. If the path was `/`, it would be blocked as dangerous.
        *   Before `execution/filesystem.py` writes to `/etc/hosts`, `validate_operation` would check if Angela has write permission to that file.
    *   **Defines/Controls:** Hard-coded safety rules and permission checks.

---

**`shell/` Directory:** Shell Integration and Terminal User Interface

*   **Overall Purpose:** Manages how Angela integrates with the user's shell (Bash, Zsh, Tmux), how it displays information in the terminal, and how it handles interactive elements like prompts and auto-completion.
*   `__init__.py`: Exports key components like `terminal_formatter`, `inline_feedback`, `completion_handler`.
*   `advanced_formatter.py`:
    *   **Purpose:** Extends the basic `TerminalFormatter` with capabilities to display more complex, structured information, specifically `AdvancedTaskPlan`s.
    *   **Job:** Contains functions like `display_advanced_plan` and `display_execution_results` which use `rich` components (Tables, Trees, Panels) to present detailed plans and their outcomes in a readable way. It "patches" these methods onto the `terminal_formatter` instance.
    *   **Scenario:** When the `Orchestrator` (via `EnhancedPlannerIntegration`) executes an `AdvancedTaskPlan`, it calls `terminal_formatter.display_advanced_plan(...)` to show the user the planned steps, dependencies, and branches. After execution, `terminal_formatter.display_execution_results(...)` shows the outcome of each step.
    *   **Defines/Controls:** Rich display logic for complex plan structures.

*   `angela_enhanced.bash` & `angela_enhanced.zsh`:
    *   **Purpose:** These are shell script files intended to be sourced by the user's `.bashrc` or `.zshrc` respectively, to enable deeper integration with Angela.
    *   **Job:**
        1.  Set up shell hooks:
            *   `preexec` (Zsh) or `DEBUG` trap (Bash): Runs `angela_pre_exec` before each command. This function captures the command and its start time, and notifies Angela's `monitoring/notification_handler.py` (via `angela --notify pre_exec ...`).
            *   `precmd` (Zsh) or `PROMPT_COMMAND` (Bash): Runs `angela_post_exec` after each command. This function captures the exit code and duration, notifies Angela, and checks for directory changes. It also calls `angela_check_command_suggestion` for failed commands.
        2.  Define the main `angela` shell function: This is an alias or wrapper around `python -m angela`. It handles parsing global flags like `--debug`, `--version`, and routes different invocations (e.g., `angela init`, `angela request ...`) to the Python entry point.
        3.  Set up command completion by calling `angela --completions ...`.
    *   **Scenario:** User sources `angela_enhanced.zsh` in their `.zshrc`.
        *   They type `git staus` (typo) and hit Enter.
        *   `angela_preexec` sends `"git staus"` to Angela.
        *   `git staus` fails.
        *   `angela_precmd` sends the failure info to Angela. `angela_check_command_suggestion` might print "[Angela] I noticed your git command failed. Try: `angela fix-git`".
    *   **Defines/Controls:** Shell-level integration, command interception, and completion setup.

*   `angela.bash` & `angela.zsh`:
    *   **Purpose:** Simpler, more basic shell integration scripts.
    *   **Job:** Primarily define the `angela` shell function/alias to call `python -m angela ...`. They might not include the advanced command hooks found in the `_enhanced` versions.
    *   **Scenario:** A user who wants basic Angela functionality without deep shell hooks might source these.
    *   **Defines/Controls:** Basic shell alias/function for running Angela.

*   `angela.tmux`:
    *   **Purpose:** Provides integration with the Tmux terminal multiplexer.
    *   **Job:** Defines functions to:
        *   Show an Angela status indicator in the Tmux status bar.
        *   Set up Tmux key bindings (e.g., Alt+A to activate Angela, Alt+C to send the current pane's last command to Angela).
    *   **Scenario:** User is in Tmux, sources this script. Their Tmux status bar shows "◉ Angela". They press Alt+C, and the last command they typed in the active Tmux pane is sent as a request to Angela.
    *   **Defines/Controls:** Tmux-specific enhancements.

*   `completion.py` (contains `CompletionHandler`):
    *   **Purpose:** To provide intelligent, context-aware command-line auto-completion for `angela` commands.
    *   **Job:** When the user types `angela ` and hits Tab, the shell's completion system (via `angela_enhanced.bash/zsh`) calls `angela --completions <current_words>`. The `CompletionHandler` receives these current words.
        *   It provides static completions for known subcommands (e.g., `angela files <TAB>` -> `ls mkdir rm ...`).
        *   For commands expecting file paths (`angela files cat <TAB>`), it suggests files/directories from the current location.
        *   For commands expecting workflow names (`angela workflows run <TAB>`), it suggests existing workflow names.
        *   For natural language commands (`angela fix <TAB>`), it can use context (recent files, project type, last failed command) and potentially AI to suggest relevant completions (e.g., "last git command", "python import error").
    *   **Scenario:**
        *   User types `angela files l<TAB>` -> `CompletionHandler` returns `ls`.
        *   User types `angela fix git <TAB>` -> `CompletionHandler` might suggest "last commit", "merge conflict", "push error".
    *   **Defines/Controls:** Logic for generating context-sensitive command-line completions.

*   `formatter.py` (contains `TerminalFormatter`, `OutputType`):
    *   **Purpose:** To provide rich, styled output to the terminal using the `rich` library.
    *   **Job:** Contains methods to print commands with syntax highlighting (`print_command`), display general output with different styles based on type (info, error, warning, success - `print_output`), format error analyses into tables, stream command output with spinners, and display task plans and workflows in a structured way.
    *   **Scenario:**
        *   When Angela suggests a command, `Orchestrator` calls `terminal_formatter.print_command(...)` to show it highlighted.
        *   When a command fails, `terminal_formatter.print_output(stderr, OutputType.ERROR)` shows the error in red.
        *   When a multi-step plan is generated, `terminal_formatter.display_task_plan(...)` shows it as a nice table.
    *   **Defines/Controls:** How Angela's output is presented to the user in the terminal.

*   `inline_feedback.py` (contains `InlineFeedback`):
    *   **Purpose:** To allow Angela to display messages and ask for quick user input directly in the terminal flow, without disrupting the user's current command line or requiring a full separate prompt.
    *   **Job:**
        *   `show_message`: Displays a short, potentially auto-clearing message (info, warning, error) inline.
        *   `ask_question`: Asks a question with options (or free-form) and waits for a user's keystroke response, often with a timeout. This is tricky in a CLI and usually involves some lower-level terminal manipulation or a separate input thread.
        *   `suggest_command`: Shows a command suggestion and asks for (y/n/e) to execute or edit it.
    *   **Scenario:**
        *   `ProactiveAssistant` detects the user made a common typo. It calls `inline_feedback.show_message("Did you mean 'git status'?", message_type="info", timeout=5)`. The message appears briefly.
        *   `SemanticTaskPlanner` is unsure about which file the user meant. It calls `inline_feedback.ask_question("Which file? 1. a.py 2. b.py", options=["1","2"])`. Angela waits for the user to press '1' or '2'.
    *   **Defines/Controls:** Non-disruptive, quick interactions and feedback within the terminal.

---

**`toolchain/` Directory:** Integration with External Developer Tools

*   **Overall Purpose:** Contains modules that provide an abstraction layer for Angela to interact with common developer tools like Git, Docker, package managers, CI/CD systems, and test frameworks. It also includes the Universal CLI Translator.
*   `__init__.py`: Exports the main integration instances (e.g., `git_integration`, `docker_integration`).
*   `ci_cd.py` (contains `CiCdIntegration`):
    *   **Purpose:** To automate CI/CD pipeline setup and interaction.
    *   **Job:**
        1.  Detects the project type (Python, Node, etc.).
        2.  Generates CI/CD configuration files for various platforms (GitHub Actions, GitLab CI, Jenkins, Travis, CircleCI, Azure Pipelines, Bitbucket Pipelines) based on project type and best practices.
        3.  Can create complete pipelines including build, test, lint, security scan, package, and deploy stages.
        4.  Can set up deployment and testing configurations.
    *   **Scenario:** User runs `angela generate generate-ci github_actions`. `CiCdIntegration` detects it's a Python project and generates a `.github/workflows/python-ci.yml` file with steps to install dependencies, run linters, and execute tests.
    *   **Defines/Controls:** CI/CD pipeline automation and configuration generation.

*   `cross_tool_workflow_engine.py` (contains `CrossToolWorkflowEngine`, `CrossToolWorkflow`, `CrossToolStep`):
    *   **Purpose:** To orchestrate complex workflows that span multiple different CLI tools and services, managing data flow between them.
    *   **Job:**
        1.  Takes a high-level request (e.g., "build my app, dockerize it, push to registry, and deploy to Kubernetes").
        2.  Uses AI (via `_generate_workflow`) to plan a `CrossToolWorkflow` which consists of `CrossToolStep`s. Each step specifies a tool (e.g., `make`, `docker`, `aws`, `kubectl`) and a command for that tool.
        3.  Manages dependencies between steps and data flow (e.g., output of `docker build` (image ID) is used as input to `docker push`).
        4.  Executes the workflow, calling the appropriate tool for each step (potentially using `EnhancedUniversalCLI` or specific tool integrations).
    *   **Scenario:** This is used by `Phase12Integration` to handle very complex, multi-stage, multi-tool automation tasks. For example, automating a full build-test-deploy pipeline that involves Git, a build tool, Docker, a container registry CLI, and a Kubernetes CLI.
    *   **Defines/Controls:** Orchestration of workflows involving multiple, distinct CLI tools.

*   `docker.py` (contains `DockerIntegration`):
    *   **Purpose:** To provide an interface for Angela to interact with Docker and Docker Compose.
    *   **Job:** Contains methods to:
        *   Check if Docker/Docker Compose are available.
        *   List containers and images (`docker ps`, `docker images`).
        *   Manage containers (start, stop, restart, remove, get logs, exec).
        *   Manage images (build, pull, remove).
        *   Run Docker Compose commands (`compose up`, `compose down`, `compose ps`, `compose logs`).
        *   Generate `Dockerfile`, `docker-compose.yml`, and `.dockerignore` files based on project type and conventions.
    *   **Scenario:**
        *   User: `angela docker ps` -> `cli/docker.py` calls `DockerIntegration.list_containers()`.
        *   User: `angela generate generate-dockerfile .` -> `cli/generation.py` (or a generation command in `cli/docker.py`) calls `DockerIntegration.generate_dockerfile(...)`.
    *   **Defines/Controls:** Interaction logic with the Docker engine and Docker Compose.

*   `enhanced_universal_cli.py` (contains `EnhancedUniversalCLI`):
    *   **Purpose:** To provide a more context-aware layer on top of the `UniversalCLITranslator`.
    *   **Job:**
        1.  Before calling the base translator, it enhances the user's request with relevant context (e.g., if the request is about Git, it adds current Git branch and status; if about Docker, it adds info about running containers or Dockerfiles present).
        2.  It can guess the target tool if not explicitly mentioned by the user.
        3.  Maintains a history of commands used for specific tools to improve future translations.
        4.  Can provide command suggestions for a given tool based on context.
    *   **Scenario:** User types `angela "commit my changes with message 'fix bug'"`.
        *   `EnhancedUniversalCLI` guesses the tool is `git`.
        *   It enhances the request: `"commit my changes with message 'fix bug'\n\nContext: On branch feature/xyz. Working tree has 3 changes."`
        *   This enhanced request is passed to the base `UniversalCLITranslator` which then generates `git commit -m "fix bug"`.
    *   **Defines/Controls:** A smarter interface to the generic CLI translation, leveraging application context.

*   `git.py` (contains `GitIntegration`):
    *   **Purpose:** To provide an interface for Angela to interact with Git.
    *   **Job:** Contains methods to:
        *   Initialize a Git repository (`git init`).
        *   Stage files (`git add`).
        *   Commit changes (`git commit`).
        *   Create branches (`git branch`, `git checkout -b`).
        *   Get repository status.
        *   Create a `.gitignore` file based on a project type template.
    *   **Scenario:**
        *   When `generation/engine.py` creates a new project, it might call `GitIntegration.init_repository(...)` and then `GitIntegration.commit_changes(...)` for an initial commit.
        *   User: `angela request "create a new git branch called 'dev'"` -> Orchestrator might use `GitIntegration.create_branch(...)`.
    *   **Defines/Controls:** Interaction logic with the Git CLI.

*   `package_managers.py` (contains `PackageManagerIntegration`):
    *   **Purpose:** To interact with various package managers (pip, npm, yarn, poetry, cargo, etc.).
    *   **Job:**
        1.  Detects which package manager is being used in a project (e.g., by looking for `requirements.txt`, `package.json`, `Cargo.toml`).
        2.  Installs specified dependencies (runtime and development) using the appropriate command for the detected package manager (e.g., `pip install ...`, `npm install ...`, `poetry add ...`).
        3.  Can optionally update the project's dependency file (e.g., `requirements.txt`, `package.json`).
    *   **Scenario:**
        *   `generation/engine.py` generates a Python project and its `requirements.txt`. It then calls `PackageManagerIntegration.install_dependencies(...)` to install those packages.
        *   User asks `angela "add the 'requests' library to my python project"`. The orchestrator might use this module to run `pip install requests` and update `requirements.txt`.
    *   **Defines/Controls:** Dependency installation logic for various ecosystems.

*   `test_frameworks.py` (contains `TestFrameworkIntegration`):
    *   **Purpose:** To integrate with common testing frameworks.
    *   **Job:**
        1.  Detects which test framework is used in a project (pytest, unittest, Jest, Mocha, etc.) by looking for configuration files or common test file patterns.
        2.  Generates boilerplate test files for given source code files, using conventions appropriate for the detected framework and project type.
    *   **Scenario:**
        *   User runs `angela generate generate-tests .`. `TestFrameworkIntegration` detects it's a Python project using pytest. For each `.py` file in `src/`, it generates a corresponding `test_*.py` file in `tests/` with basic test stubs for its functions and classes.
    *   **Defines/Controls:** Test framework detection and test file scaffolding.

*   `universal_cli.py` (contains `UniversalCLITranslator`, `CommandDefinition`, etc.):
    *   **Purpose:** To translate natural language requests into commands for *any* arbitrary CLI tool, even if Angela doesn't have specific integration for it.
    *   **Job:**
        1.  When asked to translate for a tool (e.g., `aws`, `kubectl`, `ffmpeg`), it first tries to get the tool's help documentation (e.g., by running `aws help`, `aws s3 help`, `aws s3 cp help`).
        2.  It then uses AI to parse this help text into a structured `CommandDefinition` (which includes parameters, options, usage, examples). This definition is cached.
        3.  Given a natural language request (e.g., "copy file my.txt to s3 bucket mybucket") and the `CommandDefinition` for the target tool/command (e.g., `aws s3 cp`), it uses AI to generate the precise command string (`aws s3 cp my.txt s3://mybucket/`).
    *   **Scenario:** User types `angela request "using ffmpeg, convert input.mp4 to output.gif with 10 fps"`.
        *   The `Orchestrator` (likely via `EnhancedUniversalCLI`) identifies the tool as `ffmpeg`.
        *   `UniversalCLITranslator` gets `ffmpeg --help` (or `ffmpeg -h convert` if it can identify subcommands).
        *   It parses this help to understand `ffmpeg`'s options like `-i` (input), `-r` (framerate).
        *   It then generates the command: `ffmpeg -i input.mp4 -r 10 output.gif`.
    *   **Defines/Controls:** Generic, AI-driven translation of natural language to arbitrary CLI commands.

---

**`utils/` Directory:** Utility Functions

*   **Overall Purpose:** Contains shared helper functions and modules used by various parts of the Angela application.
*   `__init__.py`: Exports common utilities.
*   `enhanced_logging.py` (contains `EnhancedLogger`):
    *   **Purpose:** Provides a more advanced logger that can include contextual information in log messages.
    *   **Job:** Wraps Python's standard `logging.Logger`. Allows adding key-value context (e.g., `logger.add_context("user_id", 123)`). When a message is logged, this context is included, often formatted as JSON for structured logging.
    *   **Scenario:** Before processing a user request, the `Orchestrator` might add `request_id` to the logger's context. All subsequent log messages related to processing that request will automatically include this `request_id`.
    *   **Defines/Controls:** Contextual and structured logging capabilities.

*   `logging.py`:
    *   **Purpose:** To configure and provide application-wide logging.
    *   **Job:**
        1.  `setup_logging`: Configures the `loguru` logger (which `EnhancedLogger` might wrap or be used alongside). Sets up handlers to log to `stderr` and to files (`angela.log`, `angela_structured.log`) in the `LOG_DIR`. Configures log format, rotation, and retention.
        2.  `get_logger`: A factory function to obtain an `EnhancedLogger` instance for a given module name.
    *   **Scenario:** At the start of `angela/__init__.py` (via `init_application`), `setup_logging()` is called. Then, any module (e.g., `orchestrator.py`) calls `logger = get_logger(__name__)` to get its own logger instance.
    *   **Defines/Controls:** Application-wide logging setup and logger access.

---

**`workflows/` Directory:** User-Defined Workflow Management

*   **Overall Purpose:** Allows users to define, store, manage, and execute their own named sequences of commands (workflows).
*   `__init__.py`: Exports `workflow_manager` and `workflow_sharing_manager`.
*   `manager.py` (contains `WorkflowManager`, `Workflow`, `WorkflowStep`):
    *   **Purpose:** The core logic for managing user-defined workflows.
    *   **Job:**
        1.  Loads and saves workflow definitions from/to `~/.config/angela/workflows.json`.
        2.  `define_workflow`: Creates a new workflow from a list of steps (command, explanation, options).
        3.  `define_workflow_from_natural_language`: Uses AI (via `intent/planner.py`) to convert a natural language description (e.g., "backup my documents: first zip /docs, then copy to /backup") into a sequence of `WorkflowStep`s.
        4.  `get_workflow`, `list_workflows`, `delete_workflow`: Standard CRUD operations for workflows.
        5.  `execute_workflow`: Takes a workflow name and variable substitutions, converts the workflow into a `TaskPlan`, and uses `intent/planner.py`'s `execute_plan` to run it.
    *   **Scenario:**
        *   User: `angela workflows create backup_docs "zips my important folder and copies it"` (or provides steps interactively). `WorkflowManager` saves this.
        *   User: `angela workflows run backup_docs`. `WorkflowManager` retrieves "backup_docs", substitutes any variables, and executes its steps.
    *   **Defines/Controls:** Creation, storage, retrieval, and execution of user-defined command sequences.

*   `sharing.py` (contains `WorkflowSharingManager`, `WorkflowExportMetadata`):
    *   **Purpose:** To enable users to export their workflows into a shareable format and import workflows shared by others.
    *   **Job:**
        *   `export_workflow`: Takes a workflow name, packages its definition (`workflow.json`), metadata (`metadata.json` including name, description, checksum), and a README into a zip archive (e.g., `my_workflow.angela-workflow`).
        *   `import_workflow`: Takes a workflow package (zip file), extracts its contents, verifies the checksum, and adds the workflow to the user's local `WorkflowManager`. Allows renaming on import to avoid conflicts.
    *   **Scenario:**
        *   User A creates a useful "deploy_app" workflow. They run `angela workflows export deploy_app -o deploy_app.zip`.
        *   User A sends `deploy_app.zip` to User B.
        *   User B runs `angela workflows import deploy_app.zip`. The workflow is now available for User B.
    *   **Defines/Controls:** Sharing and distribution of user-defined workflows.

---

This detailed breakdown should give you a good understanding of how the different parts of Angela CLI are intended to work together to process user commands and provide AI-powered assistance.
