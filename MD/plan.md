
**Angela CLI: Incremental Testing & Refinement Plan**

**Phase 1: Core AI Interaction & Basic Command Execution**

*   **Goal:** Ensure Angela can understand simple requests, get a command from the AI, and execute it safely.
*   **Focus Modules:** `cli/main.py` (request command), `orchestrator.py` (`process_request`, `_determine_request_type` for COMMAND, `_process_command_request`, `_get_ai_suggestion`), `ai/client.py`, `ai/prompts.py` (basic prompts), `ai/parser.py`, `safety/` (basic classifier, validator, confirmation), `execution/engine.py`.
*   **Testing Steps & Scenarios:**
    1.  **1.1. AI Client & Basic Prompting:**
        *   **Test:** Directly call `ai.client.gemini_client.generate_text()` with a very simple prompt from `ai.prompts.build_prompt()` (e.g., "translate 'hello world' to French").
        *   **Verify:** AI responds correctly. API key is working.
        *   **Refine:** Prompt structure, API error handling in `ai.client`.
    2.  **1.2. AI Response Parsing:**
        *   **Test:** Feed a sample JSON response (as if from Gemini for a command suggestion) to `ai.parser.parse_ai_response()`.
        *   **Verify:** It correctly parses into a `CommandSuggestion` object. Handles malformed JSON gracefully.
        *   **Refine:** JSON parsing logic, error handling in `ai.parser`.
    3.  **1.3. Basic Command Suggestion (Orchestrator Path):**
        *   **Test:** `angela request "list files"`
        *   **Verify:**
            *   `orchestrator._determine_request_type` correctly identifies `RequestType.COMMAND`.
            *   `orchestrator._get_ai_suggestion` is called.
            *   A reasonable command (e.g., `ls`) is suggested.
            *   Explanation is present.
        *   **Refine:** `_determine_request_type` logic for simple commands, basic prompt in `ai.prompts.py`.
    4.  **1.4. Safety Validation & Classification (No Execution):**
        *   **Test:**
            *   `angela request "list files" --suggest-only` (Safe)
            *   `angela request "delete all temp files" --suggest-only` (Medium/High Risk)
            *   `angela request "sudo rm -rf /" --suggest-only` (Critical/Blocked)
        *   **Verify:**
            *   `safety.classifier.classify_command_risk` assigns appropriate risk.
            *   `safety.validator.validate_command_safety` blocks dangerous commands.
        *   **Refine:** Risk patterns in `safety.classifier`, dangerous patterns in `safety.validator`.
    5.  **1.5. Basic Command Execution with Confirmation:**
        *   **Test:**
            *   `angela request "list files"` (should execute if low risk confirmation is off by default)
            *   `angela request "create a test directory"` (AI suggests `mkdir test_dir`).
        *   **Verify:**
            *   `safety.confirmation.get_confirmation` is called for appropriate risk levels.
            *   User is prompted correctly.
            *   Command executes successfully via `execution.engine.execute_command` if confirmed.
            *   Output is displayed.
        *   **Refine:** Confirmation logic, `execution.engine` reliability.
    6.  **1.6. Context Management (CWD, Basic Project):**
        *   **Test:** Run `angela request "list files"` in different directories, including one with a `.git` folder.
        *   **Verify:** `context.manager.ContextManager` correctly identifies CWD and project root/type. This context is used in the AI prompt.
        *   **Refine:** `ContextManager._detect_project_root`, `_determine_project_type`.

**Phase 2: Enhanced Context & Adaptive Execution**

*   **Goal:** Improve AI suggestions using richer context and make execution smarter.
*   **Focus Modules:** `context/` (enhancer, session, history, file_resolver, project_inference, project_state_analyzer), `ai/enhanced_prompts.py`, `ai/confidence.py`, `ai/analyzer.py` (ErrorAnalyzer), `execution/adaptive_engine.py`, `safety/adaptive_confirmation.py`.
*   **Testing Steps & Scenarios:**
    1.  **2.1. Context Enhancement:**
        *   **Test:** `angela request "list python files in my project"` (inside a Python project).
        *   **Verify:**
            *   `context.enhancer.enrich_context` is called.
            *   `project_inference` and `project_state_analyzer` provide data.
            *   The AI prompt built by `ai.enhanced_prompts.build_enhanced_prompt` includes project type, Git status, etc.
        *   **Refine:** Logic in all `context/` modules, prompt construction in `enhanced_prompts`.
    2.  **2.2. Session Context & History:**
        *   **Test:**
            *   `angela request "show content of readme.md"`
            *   `angela request "now summarize it"`
        *   **Verify:**
            *   `context.session.session_manager` tracks "readme.md" as a recent entity.
            *   The second request correctly refers to "readme.md" due to session context.
            *   `context.history.history_manager` records commands.
        *   **Refine:** `session_manager` entity tracking, `history_manager` recording and retrieval.
    3.  **2.3. File Resolution:**
        *   **Test:** `angela request "edit my main config file"` (where "main config file" is ambiguous).
        *   **Verify:** `context.file_resolver.resolve_reference` is used. If ambiguous, it might ask for clarification (if that part of `IntentAnalyzer` is ready) or pick the best match.
        *   **Refine:** `FileResolver` strategies.
    4.  **2.4. Confidence Scoring & Adaptive Confirmation:**
        *   **Test:** Various requests, some clear, some ambiguous.
        *   **Verify:**
            *   `ai.confidence.confidence_scorer` provides reasonable scores.
            *   `safety.adaptive_confirmation.get_adaptive_confirmation` uses this score, user preferences (`context.preferences`), and history to decide on prompting.
        *   **Refine:** `ConfidenceScorer` heuristics, `AdaptiveConfirmation` logic.
    5.  **2.5. Error Analysis & Recovery (Basic):**
        *   **Test:** `angela request "run non_existent_command"`
        *   **Verify:**
            *   `execution.adaptive_engine` catches the error.
            *   `ai.analyzer.ErrorAnalyzer` is called.
            *   Basic fix suggestions are provided.
        *   **Refine:** `ErrorAnalyzer` patterns and suggestion logic.
    6.  **2.6. Shell Formatting & Inline Feedback (Basic):**
        *   **Test:** Various commands, errors, suggestions.
        *   **Verify:** `shell.formatter.terminal_formatter` displays output clearly (colors, panels). `shell.inline_feedback` can show a simple message.
        *   **Refine:** Formatting rules, inline message display.

**Phase 3: File Content Operations & Workflows**

*   **Goal:** Enable AI-driven file content analysis/manipulation and user-defined workflows.
*   **Focus Modules:** `ai/content_analyzer.py` (and extensions), `ai/file_integration.py`, `workflows/manager.py`, `cli/files.py`, `cli/workflows.py`, `execution/filesystem.py`, `execution/rollback.py`.
*   **Testing Steps & Scenarios:**
    1.  **3.1. File Content Analysis (Read-only):**
        *   **Test:**
            *   `angela request "summarize my_script.py"`
            *   `angela request "analyze the structure of config.json"`
            *   `angela request "search for 'TODO' in all .py files"`
        *   **Verify:**
            *   `orchestrator._determine_request_type` identifies `RequestType.FILE_CONTENT`.
            *   `_process_file_content_request` calls appropriate `ContentAnalyzer` methods.
            *   Results are accurate and well-formatted.
        *   **Refine:** `ContentAnalyzer` prompts and parsing for different analysis types. `file_resolver` robustness.
    2.  **3.2. File Content Manipulation (with Confirmation & Rollback):**
        *   **Test:** `angela request "in settings.py, change DEBUG from True to False"`
        *   **Verify:**
            *   `ContentAnalyzer.manipulate_content` generates the change.
            *   Diff is shown, user confirms.
            *   `execution.filesystem.write_file` is used.
            *   `execution.rollback.rollback_manager` records the operation (with original content or diff).
            *   `angela rollback last` can revert the change.
        *   **Refine:** `ContentAnalyzer` manipulation prompts, diff generation, rollback for content changes.
    3.  **3.3. Basic Workflow Definition & Execution:**
        *   **Test:**
            *   `angela request "define workflow 'cleanup' to remove *.tmp and *.log files"`
            *   `angela workflows run cleanup`
        *   **Verify:**
            *   `_process_workflow_definition` uses `workflow_manager.define_workflow_from_natural_language` (which uses `TaskPlanner`).
            *   Workflow is saved correctly.
            *   `_process_workflow_execution` runs the workflow steps.
        *   **Refine:** `workflow_manager` logic, AI prompts for converting natural language to steps, variable identification.
    4.  **3.4. Rollback for File System Operations:**
        *   **Test:**
            *   `angela files mkdir test_rollback`
            *   `angela files rm some_file_to_backup` (ensure it's backed up)
            *   `angela rollback last` (for both operations).
        *   **Verify:** `execution.filesystem` correctly calls `rollback_manager` to backup/record. Rollback restores state.
        *   **Refine:** Backup mechanisms in `filesystem.py`, rollback logic in `rollback.py`.

**Phase 4: Basic Code Generation & Toolchain Integration**

*   **Goal:** Enable generation of single files/simple projects and basic interaction with dev tools.
*   **Focus Modules:** `generation/engine.py` (for single files), `generation/frameworks.py`, `generation/validators.py`, `toolchain/` (git, package_managers, docker basic), `cli/generation.py`, `cli/docker.py`.
*   **Testing Steps & Scenarios:**
    1.  **4.1. Single Code File Generation:** (Covered partly in Scenario 2)
        *   **Test:** `angela request "generate a python function to calculate factorial and save as factorial.py"`
        *   **Verify:** `CodeGenerationEngine` generates valid, functional Python code. `validators.validate_python` passes.
        *   **Refine:** AI prompts for single function/class generation. Validator accuracy.
    2.  **4.2. Basic Framework Project Scaffolding (e.g., React CRA-like):**
        *   **Test:** `angela generate create-framework-project react "my test react app"`
        *   **Verify:** `generation.frameworks.FrameworkGenerator` creates the correct directory structure and boilerplate files for a simple React app. Content of boilerplate files is reasonable.
        *   **Refine:** Framework-specific templates and generation logic in `FrameworkGenerator`.
    3.  **4.3. Git Integration:**
        *   **Test:**
            *   `angela request "initialize a git repository here"`
            *   (After generating a project) `angela request "stage all files and commit them with message 'initial commit'"`
        *   **Verify:** `toolchain.git.git_integration` methods are called and Git commands execute correctly.
        *   **Refine:** `GitIntegration` command construction and error handling.
    4.  **4.4. Package Manager Integration (Install):**
        *   **Test:** (After generating a Python project with `requests` in `requirements.txt`) `angela request "install dependencies for this project"`
        *   **Verify:** `toolchain.package_managers.package_manager_integration` detects `pip` and runs `pip install -r requirements.txt`.
        *   **Refine:** Package manager detection, install command construction.
    5.  **4.5. Basic Docker Operations (CLI & Toolchain):**
        *   **Test:**
            *   `angela docker ps`
            *   `angela request "generate a simple python dockerfile"` (should use `DockerIntegration.generate_dockerfile`)
            *   `angela request "build the docker image in the current directory and tag it myapp:latest"`
        *   **Verify:** `cli/docker.py` commands work. `toolchain.docker.DockerIntegration` methods correctly generate Dockerfiles and execute Docker commands.
        *   **Refine:** `DockerIntegration` methods, Dockerfile templates.

**Phase 5: Advanced Code Generation & Semantic Understanding**

*   **Goal:** Generate complex multi-file projects with architectural planning and leverage deep code understanding.
*   **Focus Modules:** `generation/` (engine, planner, architecture, context_manager, refiner), `ai/semantic_analyzer.py`, `context/semantic_context_manager.py`, `review/feedback.py`, `review/diff_manager.py`.
*   **Testing Steps & Scenarios:**
    1.  **5.1. Semantic Analysis Core:**
        *   **Test:** Point `ai.semantic_analyzer.analyze_file()` at various Python, JS, Java files.
        *   **Verify:** Correctly identifies classes, functions, methods, imports, docstrings, basic dependencies.
        *   **Refine:** Language-specific parsing logic in `SemanticAnalyzer`.
    2.  **5.2. Project Architecture Planning:**
        *   **Test:** `angela generate create-complex-project "a blog platform with user auth and posts"`
        *   **Verify:**
            *   `generation.planner.ProjectPlanner.create_detailed_project_architecture()` is called.
            *   The AI-generated `ProjectArchitecture` (components, layers, patterns) is reasonable.
            *   `ProjectPlanner.create_project_plan_from_architecture()` converts this into a `CodeProject` with a plausible file list.
        *   **Refine:** Prompts for architectural planning. Logic for converting architecture to file plan.
    3.  **5.3. Multi-File Code Generation with Context:**
        *   **Test:** Execute the plan from 5.2 (or a smaller multi-file plan).
        *   **Verify:**
            *   `generation.engine.CodeGenerationEngine._generate_complex_file_contents()` iterates through files.
            *   `generation.context_manager.generation_context_manager` is used to pass context (e.g., already defined classes) between file generation steps.
            *   Generated files have consistent naming, imports, and inter-dependencies.
        *   **Refine:** `GenerationContextManager` logic. Prompts for file content generation, ensuring they use provided context.
    4.  **5.4. Code Refinement with Feedback:**
        *   **Test:** After generating a file, `angela generate refine-code "add more robust error handling to the save_user function" --file users.py --apply`
        *   **Verify:**
            *   `generation.refiner.InteractiveRefiner` (using `review.feedback.FeedbackManager`) processes the feedback.
            *   AI suggests relevant code changes.
            *   `review.diff_manager` shows a correct diff.
            *   Changes are applied correctly.
        *   **Refine:** `FeedbackManager` prompts. Diff application logic.
    5.  **5.5. Documentation Generation:**
        *   **Test:** `angela generate readme .` for a generated project.
        *   **Verify:** `generation.documentation.DocumentationGenerator` produces a sensible README.
        *   **Refine:** Prompts for README, API docs, etc.

**Phase 6: Advanced Planning, Workflows & Universal CLI**

*   **Goal:** Enable complex, multi-tool workflows and natural language control over arbitrary CLIs.
*   **Focus Modules:** `intent/` (enhanced_task_planner, complex_workflow_planner, semantic_task_planner), `toolchain/universal_cli.py` (and enhanced), `toolchain/cross_tool_workflow_engine.py`, `integrations/enhanced_planner_integration.py`, `integrations/phase12_integration.py`.
*   **Testing Steps & Scenarios:**
    1.  **6.1. Advanced Task Planning (Loops, Decisions):**
        *   **Test:** `angela request "for each .txt file in reports/, if it contains 'ERROR', move it to errors/"`
        *   **Verify:**
            *   `EnhancedTaskPlanner` (or `SemanticTaskPlanner`) creates an `AdvancedTaskPlan` with LOOP and DECISION steps.
            *   `EnhancedTaskPlanner.execute_advanced_plan` correctly executes the logic.
            *   Data flow (e.g., filename from loop item to decision condition) works.
        *   **Refine:** `EnhancedTaskPlanner` step execution logic, condition evaluation, variable substitution.
    2.  **6.2. Semantic Task Planning & Clarification:**
        *   **Test:** `angela request "refactor the main User class to use the new Address interface"` (in a project with multiple User classes or Address interfaces).
        *   **Verify:**
            *   `SemanticTaskPlanner` detects ambiguity.
            *   Uses `shell.inline_feedback` to ask for clarification (e.g., "Which User class? Which Address interface?").
            *   Uses the clarified request to generate a precise plan.
        *   **Refine:** `SemanticTaskPlanner` ambiguity detection, clarification question generation, integration with semantic context.
    3.  **6.3. Universal CLI Translator (Single Tool):**
        *   **Test:** `angela request "using kubectl, get all pods in the 'dev' namespace sorted by name"`
        *   **Verify:**
            *   `Orchestrator` identifies `RequestType.UNIVERSAL_CLI`.
            *   `toolchain.universal_cli.UniversalCLITranslator` (via `EnhancedUniversalCLI`):
                *   Gets `kubectl help get pods`.
                *   Parses help into a `CommandDefinition`.
                *   Generates the command `kubectl get pods -n dev --sort-by=.metadata.name`.
            *   Command executes correctly.
        *   **Refine:** Help text parsing, command generation prompts for `UniversalCLITranslator`. `EnhancedUniversalCLI` context injection.
    4.  **6.4. Complex Workflow Planner & Cross-Tool Engine:**
        *   **Test:** `angela request "build my node app, then dockerize it, push the image to my-repo/my-app, and then deploy it to staging using kubectl apply -f k8s/staging.yaml"`
        *   **Verify:**
            *   `Orchestrator` identifies `RequestType.COMPLEX_WORKFLOW`.
            *   `integrations.phase12_integration` (or orchestrator directly) uses `intent.complex_workflow_planner.ComplexWorkflowPlanner` to create a `ComplexWorkflowPlan`.
            *   The plan has steps for `npm run build`, `docker build`, `docker push`, `kubectl apply`.
            *   `toolchain.cross_tool_workflow_engine.CrossToolWorkflowEngine` executes this plan, managing data flow (e.g., image tag from docker build to docker push).
        *   **Refine:** `ComplexWorkflowPlanner` plan generation, `CrossToolWorkflowEngine` execution logic and data flow management.

**Phase 7: Monitoring, Proactive Assistance & Shell Integration**

*   **Goal:** Provide a seamless shell experience with background help and robust command completion.
*   **Focus Modules:** `monitoring/` (background, network_monitor, notification_handler, proactive_assistant), `shell/` (enhanced scripts, completion, inline_feedback).
*   **Testing Steps & Scenarios:**
    1.  **7.1. Shell Hooks & Notification Handling:**
        *   **Test:** Source `angela_enhanced.zsh`. Run various commands (e.g., `ls`, `cd new_dir`, `git status`, a failing command).
        *   **Verify:**
            *   `angela --notify pre_exec ...` and `post_exec ...` are called.
            *   `monitoring.notification_handler` correctly processes these, updating session and history.
        *   **Refine:** Shell hook scripts, `NotificationHandler` logic.
    2.  **7.2. Background Monitoring & Basic Insights:**
        *   **Test:** Enable monitoring (`angela --monitor`). Make Git changes, let disk space get low (in a VM).
        *   **Verify:**
            *   `monitoring.background.BackgroundMonitor` tasks run.
            *   It detects Git changes or low disk space.
            *   It calls `ProactiveAssistant` (via callback/event).
        *   **Refine:** `BackgroundMonitor` detection logic (e.g., for Git status, file changes).
    3.  **7.3. Proactive Assistant & Suggestions:**
        *   **Test:** Based on insights from 7.2, or after a command fails.
        *   **Verify:**
            *   `monitoring.proactive_assistant.ProactiveAssistant` generates relevant suggestions (e.g., "commit your changes", "fix permission error with sudo").
            *   Suggestions are displayed via `shell.formatter` or `shell.inline_feedback`.
            *   Cooldown periods are respected.
        *   **Refine:** `ProactiveAssistant` suggestion logic, pattern detectors, interaction with formatter/inline feedback.
    4.  **7.4. Command Completion:**
        *   **Test:** Type `angela <TAB>`, `angela files <TAB>`, `angela files ls <TAB>`, `angela fix git <TAB>`.
        *   **Verify:** `shell.completion.CompletionHandler` (called via `angela --completions`) provides correct static and dynamic completions (file paths, workflow names, contextual natural language snippets).
        *   **Refine:** `CompletionHandler` logic for different contexts, AI prompts for contextual completions.

**General Refinement Loop for Each Step/Phase:**

1.  **Implement:** Write the code for the feature.
2.  **Unit Test:** Write unit tests for individual functions/classes.
3.  **Integration Test:** Test how the new feature interacts with existing components it depends on or that depend on it.
4.  **Scenario Test:** Run the end-to-end scenarios outlined above.
5.  **Observe & Debug:** Check logs, observe behavior.
6.  **Refine Prompts:** If AI output is not as expected, tweak the prompts in `ai/prompts.py`, `ai/enhanced_prompts.py`, or specific generation/planning modules.
7.  **Refine Logic:** Improve parsing, context gathering, decision-making logic in Python code.
8.  **Refine Safety:** Add new risk patterns or validation rules if unsafe behavior is observed.
9.  **Refine Formatting:** Improve how information is presented to the user.
10. **Iterate:** Go back to step 5 if issues persist or improvements are needed.

This plan provides a structured way to build out Angela's capabilities. Remember that some features will naturally overlap or be developed in parallel. The key is to always have a working core and build upon it. Good luck!
