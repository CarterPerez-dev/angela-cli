# 2-sentence explanations for each file in the /angela directory and its subdirectories

1.  `angela/ai/analyzer.py`
    Defines the `ErrorAnalyzer` class to diagnose command execution errors by matching stderr against predefined patterns and historical data. It provides structured analysis and generates actionable fix suggestions based on error type, command structure, and file reference checks.

2.  `angela/ai/confidence.py`
    Introduces the `ConfidenceScorer` class to assess the reliability of AI-generated command suggestions using heuristics. It calculates a score based on factors like command history frequency/success (`history_manager`), complexity matching the request, entity presence, and flag validity.

3.  `angela/ai/content_analyzer_extensions.py`
    Introduces `EnhancedContentAnalyzer` extending the base analyzer with specialized handlers for various languages like TypeScript and data formats like JSON. It routes analysis based on detected file type, using custom AI prompts and parsing logic (e.g., regex for TS types, schema inference for JSON) or falling back to generic analysis.

4.  `angela/ai/file_integration.py`
    Provides functions to parse shell command strings (like `mkdir`, `cp`, `rm`, `echo >`) using regex and shlex to identify file system operation intent and parameters. It translates these parsed commands into structured requests that are then executed safely via functions in the `angela.execution.filesystem` module.

5.  `angela/ai/intent_analyzer.py`
    Defines the `IntentAnalyzer` to interpret the user's goal from natural language requests, normalizing input and using fuzzy matching against predefined patterns. It extracts relevant entities based on the identified intent and can initiate interactive clarification dialogs via `prompt_toolkit` if the user's intent is ambiguous.

6.  `angela/ai/parser.py`
    Provides the `parse_ai_response` function to convert potentially unstructured text responses from the AI into a structured `CommandSuggestion` Pydantic model. It intelligently searches for JSON within markdown code blocks or the raw response, validates against the model, and includes fallback logic using regex to extract at least the command string if parsing fails.

7.  `angela/cli/files_extensions.py`
    Extends the file commands with advanced features like resolving ambiguous file references (`resolve`), extracting paths from text (`extract`), and viewing file usage history (`recent`, `active`). It integrates closely with `file_resolver`, `file_activity_tracker`, and `context_enhancer` to provide these context-aware file operations.

8.  `angela/cli/files.py`
    Defines core file system commands (`ls`, `mkdir`, `rm`, `cp`, `cat`, `write`, `find`, `info`, `rollback`) for the Angela CLI using Typer and Rich. It leverages `angela.execution.filesystem` for operations, `angela.context.manager` for file info, and `angela.execution.rollback` for undo functionality, enhancing standard utilities with context and safety.

9.  `angela/context/enhancer.py`
    Defines the `ContextEnhancer` class responsible for augmenting the basic execution context with richer information. It integrates data from `project_inference` (type, frameworks, dependencies, structure) and `file_activity_tracker` (recent files) to provide a comprehensive understanding of the user's environment.

10. `angela/context/file_activity.py`
    Implements the `FileActivityTracker` to log file system events (create, modify, delete, view) using the `FileActivity` model and `ActivityType` enum. It maintains an in-memory history of recent activities, provides methods to query this history (e.g., `get_recent_activities`, `get_most_active_files`), and integrates with `session_manager`.

11. `angela/context/file_resolver.py`
    Implements the `FileResolver` class to translate natural language file references (e.g., "main file", "config.tx") into actual file paths. It employs multiple strategies including exact path matching, fuzzy name matching, pattern matching, and context from recent files or the project structure, also extracting potential references from text.

12. `angela/context/history.py`
    Defines the `HistoryManager` to persist and analyze command execution history using `CommandRecord` objects stored in JSON. It calculates command usage patterns (`CommandPattern`), success rates, identifies common error/fix sequences, and provides methods to search history.

13. `angela/context/preferences.py`
    Defines the `PreferencesManager` and associated Pydantic models (`UserPreferences`, etc.) to load, save, and manage user-specific settings from `preferences.json`. It determines behavior like command auto-execution based on configured trust levels and maintains lists of explicitly trusted/untrusted commands.

14. `angela/context/project_inference.py`
    Contains the `ProjectInference` class for in-depth analysis of project directories to deduce type, frameworks (`FRAMEWORK_SIGNATURES`), dependencies, structure, and important files. It uses file/directory pattern matching (`PROJECT_SIGNATURES`), dependency file parsing (e.g., `requirements.txt`, `package.json`), and structural analysis, caching results for efficiency.

15. `angela/context/session.py`
    Implements the `SessionManager` and `SessionMemory` class to maintain short-term conversational state, tracking entities (like files or commands) mentioned or used during an interaction. It handles session expiration and provides the current session context (recent commands, results, entities) to other modules like the `Orchestrator`.

16. `angela/core/__init__.py`
    Initializes the 'angela.core' sub-package. Contains essential utilities like the service registry.

17. `angela/core/events.py`
    Defines a simple `EventBus` class for decoupled communication between different parts of the application. It allows components to subscribe to specific event types and publish events with associated data, facilitating asynchronous notifications.

18. `angela/core/registry.py`
    Implements a singleton `ServiceRegistry` class acting as a service locator. It allows components to register themselves by name and be retrieved by other components, breaking circular dependencies.

19. `angela/execution/__init__.py`
    Initializes the 'angela.execution' sub-package. Exposes core execution components.

20. `angela/execution/adaptive_engine.py`
    Defines the `AdaptiveExecutionEngine` which orchestrates command execution with awareness of user context, preferences, and command risk. It integrates safety classification, adaptive confirmation, rich feedback using `Progress`, history logging, and error analysis/recovery suggestions.

21. `angela/execution/filesystem.py`
    Provides high-level, safe functions (e.g., `create_directory`, `delete_file`, `read_file`, `write_file`, `copy_file`, `move_file`) for interacting with the file system. It integrates safety checks via `check_operation_safety` and automatically creates backups in `BACKUP_DIR` before potentially destructive operations to support rollback.

22. `angela/execution/hooks.py`
    Defines the `ExecutionHooks` class to intercept command and file operation execution events. It uses pre/post execution hooks to analyze commands and outcomes, automatically tracking file views, modifications, creations, or deletions via the `file_activity_tracker`.

23. `angela/execution/rollback_commands.py`
    Defines Typer commands for interacting with the enhanced rollback system (`list`, `operation`, `transaction`, `last`). It interfaces with the `RollbackManager` to display operation/transaction history and trigger rollbacks, using `rich` for formatted output.

24. `angela/generation/__init__.py`
    Initializes the 'angela.generation' sub-package containing code generation logic. Makes components like the `CodeGenerationEngine` and `FrameworkGenerator` available.

25. `angela/generation/architecture.py`
    Provides the `ArchitecturalAnalyzer` class and pattern/anti-pattern models (`MvcPattern`, `SingleResponsibilityAntiPattern`, `GodObjectAntiPattern`) to analyze project structure. It detects architectural patterns and anti-patterns using heuristics and AI, generating recommendations for improvement.

26. `angela/generation/planner.py`
    Defines the `ProjectPlanner` and `ProjectArchitecture` models to design the high-level structure and components of a *new* software project before code generation. It interacts with AI (`_build_architecture_prompt`, `_parse_architecture`) to determine components, layers, patterns, and data flow based on a project description.

27. `angela/generation/validators.py`
    Provides code validation functions (`validate_code`, `validate_python`, `validate_javascript`, etc.) for various programming languages. It uses external tools (like `py_compile`, `node --check`, `tsc`) via `subprocess` or basic regex checks to ensure generated code is syntactically correct.

28. `angela/integrations/__init__.py`
    Initializes the 'angela.integrations' sub-package. It triggers the main application initialization via `init_application`.

29. `angela/integrations/enhanced_planner_integration.py`
    Implements the integration of the `EnhancedTaskPlanner` into the main `Orchestrator`. It achieves this by patching methods (like `_process_multi_step_request`) onto the `Orchestrator` class at runtime to enable advanced plan execution.

30. `angela/intent/__init__.py`
    Initializes the 'angela.intent' sub-package related to understanding user intent and planning actions. Exposes core models and the task planner instance.

31. `angela/intent/models.py`
    Defines core Pydantic models `Intent` and `ActionPlan` used primarily in the basic request processing flow. It includes an `IntentType` enum for classifying user requests.

32. `angela/interfaces/__init__.py`
    Initializes the 'angela.interfaces' sub-package. Defines abstract base classes for key components.

33. `angela/interfaces/execution.py`
    Defines Abstract Base Classes (ABCs) for execution components. Includes `CommandExecutor` for basic command execution and `AdaptiveExecutor` for context-aware execution.

34. `angela/interfaces/safety.py`
    Defines the Abstract Base Class (ABC) `SafetyValidator`. Specifies the contract for components responsible for checking command safety and validating operations.

35. `angela/monitoring/__init__.py`
    Initializes the 'angela.monitoring' sub-package for background monitoring. Exposes the main `background_monitor` instance.

36. `angela/monitoring/network_monitor.py`
    Defines the `NetworkMonitor` class to specifically track network connectivity, local service availability (via port checks), and project dependency updates. It runs asynchronous checks and generates proactive suggestions regarding network issues or available package updates.

37. `angela/review/diff_manager.py`
    Provides the `DiffManager` class for generating unified or HTML diffs between text strings, files, or entire directories. It also includes a method (`apply_diff`) to attempt applying a unified diff patch to original content.

38. `angela/review/feedback.py`
    Defines the `FeedbackManager` to process user feedback on generated or existing code. It uses AI (`_build_improvement_prompt`, `_extract_improved_code`) to generate refined code, can orchestrate refinement across multiple files (`refine_project`), and apply the resulting changes (`apply_refinements`).

39. `angela/safety/adaptive_confirmation.py`
    Implements the `get_adaptive_confirmation` function to dynamically decide whether user confirmation is needed before executing a command. It considers command risk, user preferences (`preferences_manager`), command history (`history_manager`), and offers interactive learning (`offer_command_learning`) to adjust trust levels.

40. `angela/safety/classifier.py`
    Provides `classify_command_risk` to categorize shell commands into risk levels (SAFE to CRITICAL) using predefined regex patterns (`RISK_PATTERNS`, `OVERRIDE_PATTERNS`). Includes `analyze_command_impact` to heuristically determine potential effects like file modifications or deletions.

41. `angela/shell/__init__.py`
    Initializes the 'angela.shell' sub-package containing shell integration scripts and formatting utilities. Imports and makes the `terminal_formatter` available.

42. `angela/shell/advanced_formatter.py`
    Provides extensions to the `TerminalFormatter` specifically for displaying complex `AdvancedTaskPlan` objects. It includes methods to render plans, execution results, step details, and errors using `rich` Tables and Trees.

43. `angela/toolchain/ci_cd.py`
    Implements the `CiCdIntegration` class to automatically generate basic CI/CD configuration files for various platforms (GitHub Actions, GitLab CI, Jenkins, etc.). It detects the project type and uses predefined templates or structures (like YAML/Jenkinsfile content) specific to the target platform and project language.

44. `angela/toolchain/git.py`
    Provides the `GitIntegration` class for interacting with Git repositories programmatically. It includes methods to initialize repositories (`init_repository`), stage files (`stage_files`), commit changes (`commit_changes`), create branches (`create_branch`), check status (`get_repository_status`), and generate `.gitignore` files.

45. `angela/toolchain/package_managers.py`
    Defines the `PackageManagerIntegration` class to interact with various language-specific package managers (pip, npm, yarn, poetry, cargo). It detects the appropriate manager based on project files (`detect_package_manager`) and provides a unified interface (`install_dependencies`) to install runtime and development dependencies.

46. `angela/utils/__init__.py`
    Initializes the 'angela.utils' sub-package containing utility functions. Exposes key utilities like the logging setup function.

47. `angela/utils/enhanced_logging.py`
    Defines an `EnhancedLogger` class intended for structured JSON logging with added context tracking. This logger doesn't appear to be actively used in the rest of the codebase, which primarily uses the Loguru setup from `logging.py`.

48. `angela/workflows/__init__.py`
    Initializes the 'angela.workflows' sub-package for managing reusable command sequences. Exposes the main `workflow_manager` instance.

49. `angela/workflows/sharing.py`
    Implements the `WorkflowSharingManager` to enable exporting workflows into packaged `.angela-workflow` zip files and importing them. It manages metadata (`WorkflowExportMetadata`), checksum verification for integrity, and interacts with the `WorkflowManager` to add imported workflows.

50. `MD/ImplemenationsMD/Phase_5_implementation.md`
    Contains Markdown documentation describing the integration and features implemented around Phase 5.5 of development. It details the initialization of features like project inference and network monitoring, and how components like error recovery and enhanced content analysis interact.

51. `MD/ImplemenationsMD/Phase_6_implementation.md`
    Contains Markdown documentation detailing the integration steps and code snippets for implementing Phase 6 features. It focuses on incorporating enhanced project context (enhancer, resolver, activity tracker, hooks) into the orchestrator and prompt system.

52. `MD/ImplemenationsMD/planner_implementation.md`
    Provides Markdown documentation explaining the design and usage of the Advanced Task Planner. It details the enhanced step types (CODE, API, LOOP, etc.), the data flow system, error handling mechanisms, and provides examples of creating and executing complex plans.

53. `MD/ImplemenationsMD/rollback_implementation.md`
    Contains Markdown documentation explaining the enhanced transaction-based rollback system. It describes how operations are grouped, how different operation types (filesystem, content, command) are reverted, and how users interact with the rollback functionality via the CLI.

54. `MD/MDHelpers/context.md`
    A helper Markdown file providing supplementary context and summaries for Python files not included directly in the main codebase package. It serves as a reference to understand the purpose and functionality of modules like `workflow/sharing.py`, `ai/parser.py`, etc.

55. `MD/MDHelpers/Info.md`
    A comprehensive Markdown document providing a high-level analysis of the Angela-CLI project's architecture, purpose, components, and workflows. It acts as an onboarding guide for understanding the codebase structure and core logic based on the provided files.

56. `MD/MDHelpers/tree.md`
    Contains a shell command (`tree`) intended to generate a textual representation of the project's directory structure. This helps visualize the file hierarchy, excluding common noise directories.

57. `MD/PhasesMD/Phase1.md`
    Documents the objectives, implementation details, and test results for Phase 1 (Foundation & Shell Integration) of the Angela-CLI project. It covers the initial project setup, configuration, basic CLI structure, shell hooks, and context management foundation.

58. `MD/PhasesMD/Phase2.md`
    Documents the objectives, implementation details, and test results for Phase 2 (AI Integration & Basic Suggestions). It details the integration of the Gemini API client, prompt engineering, response parsing, and the initial safe execution engine.

59. `MD/PhasesMD/Phase3.md`
    Documents the objectives, implementation details, and test results for Phase 3 (Safety System & File Operations). It covers the implementation of risk classification, command previews, impact analysis, permission checks, dry-run capabilities, file/directory operations, and basic rollback.

60. `MD/PhasesMD/Phase4.md`
    Documents the objectives and implementation details for Phase 4 (Intelligent Interaction & Contextual Execution), split into two parts. It covers enhancements like tolerant NLU, adaptive confirmation, session context, error analysis, and richer feedback mechanisms.

61. `MD/PhasesMD/Phase5.md`
    Documents the objectives and high-level implementation details for Phase 5 (Autonomous Task Orchestration & Proactive Assistance). It covers goal decomposition, content understanding, workflow management, and background monitoring.

62. `MD/PhasesMD/Phase6.md`
    Provides a Markdown guide detailing the implementation steps for Phase 6 (Enhanced Project Context). It outlines how to add new context modules (enhancer, resolver, activity tracker) and integrate them into the orchestrator and prompt system.

63. `MD/PhasesMD/Phase7.md`
    Documents the high-level objectives and components implemented in Phase 7 (Developer Tool Integration). It covers the advanced code generation engine, toolchain integration (Git, package managers, CI/CD), and interactive code review features.

64. `MD/Next-Steps.md`
    Presents a Principal Architect's audit report and strategic recommendations for the Angela-CLI project based on the codebase review. It identifies key areas for improvement, such as packaging, import resolution, consistency, modularity, integration completeness, and provides prioritized suggestions for stabilization and future development.

65. `scripts/install.sh`
    Provides a Bash script to automate the installation of the Angela CLI application. It installs the Python package using pip in editable mode and sets up the necessary shell integration hooks for Bash or Zsh.

66. `scripts/uninstall.sh`
    Provides a Bash script to cleanly uninstall the Angela CLI application. It removes the shell integration hooks from user configuration files (`.bashrc`/`.zshrc`) and optionally removes the configuration directory and the Python package.

67. `.env.example`
    Provides an example structure for the `.env` file. It lists necessary environment variables like `GEMINI_API_KEY` and optional ones like `DEBUG`.

68. `.gitignore`
    Configures Git to ignore specific files and patterns. In this case, it primarily ignores the `.env` file containing sensitive API keys.

69. `Makefile`
    Defines common development tasks like installation (`install`), testing (`test`), linting (`lint`), formatting (`format`), and cleaning (`clean`). It simplifies setting up the development environment (`dev-setup`) and running checks.

70. `pyproject.toml`
    Defines project metadata, build system requirements, and dependencies according to modern Python packaging standards (PEP 517/518). It specifies the project name, version, Python requirement (>=3.9), dependencies (like typer, rich, pydantic, google-generativeai), optional dev dependencies, and configurations for tools like black, isort, mypy, and pytest.

71. `pytest.ini`
    Configures the behavior of the pytest testing framework. Specifies asyncio mode (`strict`) and default fixture scope.

72. `requirements.txt`
    Lists the Python packages required for the project to run. It includes core libraries like `typer`, `rich`, `pydantic`, `google-generativeai`, `loguru`, and testing tools.

73. `setup.py`
    Provides a minimal `setup.py` for compatibility with older build systems or workflows. It primarily delegates the actual configuration to `pyproject.toml`.

74. `angela/ai/__init__.py`
    Initializes the 'angela.ai' sub-package, making AI-related components importable. Exports key classes and instances like `gemini_client`, `content_analyzer`, and `error_analyzer` for use by other modules.

75. `angela/context/file_detector.py`
    Provides the `detect_file_type` function to determine file characteristics like type (source code, image, etc.), language, MIME type, and binary status. It uses a combination of file extensions, filenames (`FILENAME_MAPPING`), shebang lines (`SHEBANG_PATTERNS`), and content analysis (binary checks) for accurate detection.

76. `angela/context/manager.py`
    Implements the `ContextManager`, the core provider of environmental context like the current working directory (CWD) and project root/type detection based on `PROJECT_MARKERS`. It also manages information about the currently focused file and provides cached access to file metadata and directory listings.

77. `angela/execution/error_recovery.py`
    Provides the `ErrorRecoveryManager` to intelligently handle failures during multi-step plan execution using `RecoveryStrategy` enums. It analyzes errors (using `error_analyzer`), generates recovery options (retry, modify, skip) via heuristics or AI, learns from past successes (`_recovery_history`), and supports both automatic and user-guided recovery.

78. `angela/generation/documentation.py`
    Defines the `DocumentationGenerator` for creating project documentation like READMEs, API docs, user guides, and contributing guides. It analyzes the project structure and content, potentially using AI (`_generate_file_docs_with_ai`, `_build_readme_prompt`) to generate comprehensive Markdown documentation.

79. `angela/generation/frameworks.py`
    Provides the `FrameworkGenerator` class with specialized methods (`_generate_react`, `_generate_django`, etc.) for creating standard project boilerplate for various frameworks. It uses predefined structures and AI (`_generate_content`) to generate framework-specific files and configurations, falling back to a generic AI-driven approach if needed.

80. `angela/intent/enhanced_task_planner.py`
    Defines the `EnhancedTaskPlanner` which extends the basic planner to execute `AdvancedTaskPlan` objects containing complex steps like code execution, API calls, loops, and conditional decisions. It manages a `StepExecutionContext` for data flow between steps using variable substitution and includes robust error handling integrated with the `ErrorRecoveryManager`.

81. `angela/review/__init__.py`
    Initializes the 'angela.review' sub-package containing code review related functionalities. Exposes the `diff_manager` and `feedback_manager` instances.

82. `angela/safety/__init__.py`
    Initializes the 'angela.safety' sub-package, consolidating safety-related components. It registers key functions like `check_command_safety` and `validate_command_safety` with the core service registry.

83. `angela/safety/confirmation.py`
    Implements the core user confirmation logic (`get_confirmation`, `requires_confirmation`) using the `rich` library. It displays command details, risk level, impact analysis (`format_impact_analysis`), and previews before prompting the user with `rich.Confirm`. (Largely wrapped by `adaptive_confirmation`).

84. `angela/safety/preview.py`
    Defines the `generate_preview` function and specific previewers (e.g., `preview_rm`, `preview_ls`, `preview_cp`) registered in `PREVIEWABLE_COMMANDS`. It analyzes command arguments and file system state to predict and describe the likely outcome of commands without executing them, using `--dry-run` flags as a fallback.

85. `angela/safety/validator.py`
    Provides functions (`validate_command_safety`, `validate_operation`) to enforce safety policies before execution. It checks commands against `DANGEROUS_PATTERNS`, verifies superuser requirements (`requires_superuser`), and validates file permissions using `os.access`.

86. `angela/shell/angela.zsh`
    Defines the `angela` zsh function providing the shell integration for Zsh users. Its logic mirrors `angela.bash`, capturing user input and invoking the main Python application.

87. `angela/toolchain/__init__.py`
    Initializes the 'angela.toolchain' sub-package, grouping integrations with developer tools. Makes tool integration instances available.

88. `angela/__main__.py`
    Acts as the main executable entry point when running the package with `python -m angela`. It initializes the application using `init_application` and then starts the command-line interface defined in `angela.cli.app`.

89. `angela/config.py`
    Manages application configuration using Pydantic models, loading settings from environment variables (`.env`) and a TOML file (`config.toml`). It provides a global `config_manager` instance for accessing settings like API keys and debug mode throughout the application.

90. `angela/constants.py`
    Defines global constants used throughout the application. Includes application metadata (name, version), file paths (config, logs), API settings (model name, defaults), and safety definitions (risk levels, confirmation requirements).

91. `angela/ai/client.py`
    Implements the `GeminiClient` class to manage interactions with the Google Gemini API, handling request structuring (`GeminiRequest`) and response parsing (`GeminiResponse`). It uses the configured API key and model constants to asynchronously send prompts and receive generated text via the `google-generativeai` library.

92. `angela/ai/content_analyzer.py`
    Defines the base `ContentAnalyzer` class for AI-powered understanding and manipulation of file content. It provides asynchronous methods to analyze, summarize, search within, and modify file text using prompts tailored to file type and user requests, interacting with the `gemini_client`.

93. `angela/context/__init__.py`
    Initializes the 'angela.context' package, making core managers like `context_manager`, `session_manager`, and `history_manager` easily importable. It also schedules the background initialization of project inference via `initialize_project_inference` for improved context awareness.

94. `angela/execution/rollback.py`
    Implements the enhanced `RollbackManager` using `OperationRecord` and `Transaction` models to track filesystem changes, content manipulations (via diffs), and command executions (with compensating actions). It persists history to JSON, manages transaction lifecycles, and provides methods to roll back individual operations or entire transactions.

95. `angela/intent/planner.py`
    Defines core planning models like `PlanStep`, `TaskPlan`, `AdvancedPlanStep`, `AdvancedTaskPlan`, and the `PlanStepType` enum. It includes the base `TaskPlanner` class responsible for generating basic sequential plans or triggering advanced plan generation based on request complexity.

96. `angela/monitoring/background.py`
    Implements the `BackgroundMonitor` class to manage various background monitoring tasks using `asyncio`. It periodically checks Git status, file changes (triggering syntax/lint checks), and system resources, providing proactive suggestions via `terminal_formatter` while managing cooldowns.

97. `angela/shell/angela.bash`
    Defines the `angela` bash function which acts as the primary user interface hook for Bash shells. It handles argument parsing for global flags like `--debug` and routes the user's request to the Python backend (`python -m angela request ...`).

98. `angela/shell/formatter.py`
    Defines the `TerminalFormatter` class using the `rich` library to provide styled and structured console output for various events like commands, results, errors, plans, and suggestions. It supports different output types (`OutputType` enum) and asynchronous streaming (`stream_output`) for real-time feedback.

99. `angela/execution/engine.py`
    Implements the core `ExecutionEngine` for running shell commands asynchronously using `asyncio.create_subprocess_exec`. It captures stdout, stderr, return codes, and records successful operations with the `RollbackManager` via the service registry.

100. `angela/workflows/manager.py`
    Implements the `WorkflowManager` class, using `Workflow` and `WorkflowStep` models, to manage user-defined workflows stored in `workflows.json`. It handles creation (interactively or from natural language via AI), listing, searching, deletion, and execution of workflows, including variable substitution.

101. `angela/generation/engine.py`
    Implements the `CodeGenerationEngine` along with `CodeFile` and `CodeProject` models to manage the generation of entire projects or adding features to existing ones based on descriptions. It plans the structure (`_create_project_plan`), generates content for multiple files in dependency order (`_generate_file_contents`, `_get_ordered_files`), validates the output, and creates the files on disk.

102. `angela/cli/generation.py`
    Defines Typer commands for code generation tasks, such as creating new projects (`create-project`), adding features (`add-feature`), and refining code based on feedback (`refine-code`, `refine-project`). It orchestrates interactions with the `CodeGenerationEngine`, `FeedbackManager`, `GitIntegration`, `PackageManagerIntegration`, `TestFrameworkIntegration`, and `CiCdIntegration` modules to fulfill user generation requests.

103. `angela/cli/workflows.py`
    Implements the command-line interface for managing Angela workflows (`list`, `create`, `run`, `delete`, `show`, `export`, `import`) using Typer and Rich. It interacts with the `WorkflowManager` for core logic and the `WorkflowSharingManager` for import/export functionality, handling user input and variable substitution.

104. `angela/cli/main.py`
    Defines the main Typer application entry point, handling global options like `--debug` and `--version`, and registering primary commands like `request`, `init`, `status`, and `shell`. The crucial `request` command delegates natural language processing to the `Orchestrator`, while `shell` provides an interactive loop.

105. `angela/orchestrator.py`
    Acts as the central coordinator, receiving user requests, determining the request type (`RequestType` enum), and dispatching tasks to appropriate modules (AI client, planners, execution engines, context managers, safety checkers). It integrates enhanced context, file resolution, adaptive execution, workflow management, code generation, and error handling to process user inputs effectively.
    
106. `angela/ai/semantic_analyzer.py`
    Defines the `SemanticAnalyzer` class responsible for deep code understanding by parsing source files (e.g., Python, JavaScript) to extract entities like functions, classes, and their relationships. It uses language-specific parsers (like Python's `ast`) or LLM-based analysis to build a semantic model of the codebase, enabling features like entity usage tracking and code summarization.

107. `angela/ai/prompts.py`
    Serves as a centralized module for constructing and managing various prompt templates used to interact with the Gemini API. It defines base system instructions, few-shot examples, and specialized prompt structures for tasks like command generation, error analysis, code generation, and file operations, ensuring consistent and effective AI communication.

108. `angela/ai/enhanced_prompts.py`
    Extends the basic prompt engineering by incorporating richer contextual information, such as semantic code understanding from `SemanticAnalyzer` and detailed project state from `ProjectStateAnalyzer`. This module crafts more sophisticated prompts (e.g., `ENHANCED_SYSTEM_INSTRUCTIONS`, `SEMANTIC_CODE_CONTEXT`) to enable the LLM to generate highly context-aware and precise responses.

109. `angela/cli/__init__.py`
    Initializes the 'angela.cli' sub-package, which forms the command-line interface layer of the application. It aggregates and registers various Typer sub-command groups (like `files_app`, `workflows_app`, `generation_app`, `docker_app`) into the main `main_app`, making them accessible to the user.

110. `angela/cli/docker.py`
    Defines the user-facing CLI commands for Docker and Docker Compose interactions using Typer and Rich for formatted output. It provides commands like `ps`, `logs`, `build`, `run`, `compose-up`, and Dockerfile/compose generation, delegating the actual Docker interactions to the `angela.toolchain.docker.docker_integration` module.

111. `angela/context/semantic_context_manager.py`
    Implements the `SemanticContextManager` to act as a central hub for all semantic information within the Angela CLI. It integrates and orchestrates data from code analysis (`SemanticAnalyzer`), project state (`ProjectStateAnalyzer`), and file activity, providing a unified and rich contextual view for AI components and decision-making processes.

112. `angela/context/project_state_analyzer.py`
    Defines the `ProjectStateAnalyzer` class to provide a detailed, real-time understanding of the current project's status beyond basic type detection. It analyzes Git state (branch, changes), test status (framework, coverage), build health, pending migrations, dependency health (outdated packages), and code quality issues (linting, TODOs).

113. `angela/generation/context_manager.py`
    Implements the `GenerationContextManager` specifically designed to manage and track context *during multi-file code generation tasks*. It ensures coherence and consistency across newly generated files by registering shared entities (like API endpoints or database models), inter-file dependencies, and import statements relevant to the ongoing generation process.

114. `angela/integrations/phase12_integration.py`
    Orchestrates the most advanced, AGI-like capabilities of Angela-CLI by integrating Phase 12 components. It ties together the Universal CLI Translator, Complex Workflow Orchestration, CI/CD Pipeline Automation, and Proactive Assistance V2, enabling complex cross-tool workflows and intelligent automation.

115. `angela/integrations/semantic_integration.py`
    Provides the `SemanticIntegration` class to bridge various semantic analysis components (code analysis, project state, file activity) into the main application workflow. It enhances the core context system by making deep code understanding readily available to other modules for more informed decision-making and AI interactions.

116. `angela/intent/complex_workflow_planner.py`
    Defines the `ComplexWorkflowPlanner` which extends the `EnhancedTaskPlanner` to specifically orchestrate workflows spanning multiple, disparate CLI tools and services. It manages the planning, execution, and data flow (via `WorkflowStep`, `DataFlow` models) for these heterogeneous, end-to-end automation tasks.

117. `angela/intent/semantic_task_planner.py`
    Implements the `SemanticTaskPlanner` to elevate task planning by deeply integrating semantic code understanding from `SemanticAnalyzer` and project state from `ProjectStateAnalyzer`. This allows for improved intent decomposition for complex, ambiguous, or multi-stage user goals, including interactive clarification loops with the user.

118. `angela/monitoring/proactive_assistant.py`
    Defines the `ProactiveAssistant` class, which forms the core of Angela's proactive help system by monitoring system events, command history, and project state via the `event_bus` and `background_monitor`. It uses registered insight handlers (`_insight_handlers`) and pattern detectors (`_pattern_detectors`) to offer timely, contextual suggestions and warnings to the user.

119. `angela/shell/angela.tmux`
    Provides a Bash script designed to integrate Angela CLI functionalities within a Tmux (terminal multiplexer) session. It likely defines custom Tmux status bar elements to show Angela's status and sets up key bindings for quick invocation of Angela commands or sending pane content to Angela.

120. `angela/shell/completion.py`
    Implements the `CompletionHandler` to provide AI-powered, context-aware command-line auto-completion suggestions for Angela CLI commands. It leverages command history, project context, recent file activity, and potentially LLM interactions (`_get_ai_completions`) to offer relevant completions as the user types.

121. `angela/shell/inline_feedback.py`
    Defines the `InlineFeedback` class to enable Angela to provide messages, ask questions, or suggest commands directly within the active terminal session without disrupting the user's flow. It manages displaying these messages (e.g., with color-coding for type) and can handle user input for interactive prompts or command editing.

122. `angela/toolchain/__init__.py`
    Initializes the 'angela.toolchain' sub-package, which groups various modules responsible for integrating Angela CLI with external developer tools. This makes tool-specific integration classes like `GitIntegration`, `DockerIntegration`, and `PackageManagerIntegration` accessible.

123. `angela/toolchain/cross_tool_workflow_engine.py`
    Implements the `CrossToolWorkflowEngine` for orchestrating complex sequences of operations that span multiple, potentially unrelated, CLI tools and services. It manages the definition (`CrossToolWorkflow`, `CrossToolStep` models), execution, and data flow (`DataFlow` model) between these heterogeneous steps to achieve end-to-end automation.

124. `angela/toolchain/docker.py`
    Provides the backend `DockerIntegration` class, which encapsulates the logic for interacting with the Docker daemon and Docker Compose. It offers methods to list containers/images, start/stop/restart containers, build images, manage Docker Compose services, and generate Docker-related files (Dockerfiles, docker-compose.yml), serving as the core Docker interaction layer for other modules (like `angela/cli/docker.py`).

125. `angela/toolchain/enhanced_universal_cli.py`
    Defines the `EnhancedUniversalCLI` class, which acts as a more context-aware layer on top of the basic `UniversalCLITranslator`. It enriches translation requests with project-specific context (e.g., Git status for `git` commands, running containers for `docker` commands) to help the AI generate more accurate and relevant commands for arbitrary CLI tools.

126. `angela/toolchain/unviversal_cli.py` (Assuming typo, should be `universal_cli.py`)
    Implements the `UniversalCLITranslator`, responsible for the core task of translating natural language requests into commands for *arbitrary* CLI tools, even those not explicitly integrated. It likely achieves this by analyzing a tool's `--help` output and applying general knowledge of CLI conventions, potentially using an LLM to parse help text and map requests to command structures.

127. `angela/__init__.py`
    Serves as the main entry point for the `angela` Python package, defining the `init_application` function. This function is responsible for initializing and registering all core services and components (like execution engines, safety validators, orchestrator, context enhancers) with the central service registry, ensuring they are available throughout the application.
---
# Project Tree
```
.
├── Makefile
├── QUICKSTART.md
├── README.md
├── angela
│   ├── __init__.py
│   ├── __main__.py
│   ├── ai
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── client.py
│   │   ├── confidence.py
│   │   ├── content_analyzer.py
│   │   ├── content_analyzer_extensions.py
│   │   ├── enhanced_prompts.py
│   │   ├── file_integration.py
│   │   ├── intent_analyzer.py
│   │   ├── parser.py
│   │   ├── prompts.py
│   │   └── semantic_analyzer.py
│   ├── cli
│   │   ├── __init__.py
│   │   ├── docker.py
│   │   ├── files.py
│   │   ├── files_extensions.py
│   │   ├── generation.py
│   │   ├── main.py
│   │   └── workflows.py
│   ├── config.py
│   ├── constants.py
│   ├── context
│   │   ├── __init__.py
│   │   ├── enhanced_file_activity.py
│   │   ├── enhancer.py
│   │   ├── file_activity.py
│   │   ├── file_detector.py
│   │   ├── file_resolver.py
│   │   ├── history.py
│   │   ├── manager.py
│   │   ├── preferences.py
│   │   ├── project_inference.py
│   │   ├── project_state_analyzer.py
│   │   ├── semantic_context_manager.py
│   │   └── session.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── events.py
│   │   └── registry.py
│   ├── execution
│   │   ├── __init__.py
│   │   ├── adaptive_engine.py
│   │   ├── engine.py
│   │   ├── error_recovery.py
│   │   ├── filesystem.py
│   │   ├── hooks.py
│   │   ├── rollback.py
│   │   └── rollback_commands.py
│   ├── generation
│   │   ├── __init__.py
│   │   ├── architecture.py
│   │   ├── context_manager.py
│   │   ├── documentation.py
│   │   ├── engine.py
│   │   ├── frameworks.py
│   │   ├── planner.py
│   │   ├── refiner.py
│   │   └── validators.py
│   ├── integrations
│   │   ├── __init__.py
│   │   ├── enhanced_planner_integration.py
│   │   ├── phase12_integration.py
│   │   └── semantic_integration.py
│   ├── intent
│   │   ├── __init__.py
│   │   ├── complex_workflow_planner.py
│   │   ├── enhanced_task_planner.py
│   │   ├── models.py
│   │   ├── planner.py
│   │   └── semantic_task_planner.py
│   ├── interfaces
│   │   ├── __init__.py
│   │   ├── execution.py
│   │   └── safety.py
│   ├── monitoring
│   │   ├── __init__.py
│   │   ├── background.py
│   │   ├── network_monitor.py
│   │   ├── notification_handler.py
│   │   └── proactive_assistant.py
│   ├── orchestrator.py
│   ├── repomix-output.xml
│   ├── review
│   │   ├── __init__.py
│   │   ├── diff_manager.py
│   │   └── feedback.py
│   ├── safety
│   │   ├── __init__.py
│   │   ├── adaptive_confirmation.py
│   │   ├── classifier.py
│   │   ├── confirmation.py
│   │   ├── preview.py
│   │   └── validator.py
│   ├── shell
│   │   ├── __init__.py
│   │   ├── advanced_formatter.py
│   │   ├── angela.bash
│   │   ├── angela.tmux
│   │   ├── angela.zsh
│   │   ├── angela_enhanced.bash
│   │   ├── angela_enhanced.zsh
│   │   ├── completion.py
│   │   ├── formatter.py
│   │   └── inline_feedback.py
│   ├── toolchain
│   │   ├── __init__.py
│   │   ├── ci_cd.py
│   │   ├── cross_tool_workflow_engine.py
│   │   ├── docker.py
│   │   ├── enhanced_universal_cli.py
│   │   ├── git.py
│   │   ├── package_managers.py
│   │   └── universal_cli.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── enhanced_logging.py
│   │   └── logging.py
│   └── workflows
│       ├── __init__.py
│       ├── manager.py
│       └── sharing.py
├── docs
│   ├── Makefile
│   ├── make.bat
│   └── source
│       ├── _static
│       ├── _templates
│       ├── conf.py
│       ├── ext
│       │   └── usage_examples.py
│       └── index.rst
├── pyproject.toml
├── pytest.ini
├── requirements.txt
├── scripts
│   ├── generate_docs.sh
│   ├── install-quick.sh
│   ├── install.sh
│   └── uninstall.sh
├── setup.py

```
