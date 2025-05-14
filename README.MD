# Angela CLI: Worlds First Command-Line AGI
---
```
 █████╗  ███╗   ██╗ ██████╗ ███████╗██╗      █████╗ 
 ██╔══██╗████╗  ██║██╔════╝ ██╔════╝██║     ██╔══██╗
 ███████║██╔██╗ ██║██║  ███╗█████╗  ██║     ███████║
 ██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██║     ██╔══██║
 ██║  ██║██║ ╚████║╚██████╔╝███████╗███████╗██║  ██║
 ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝
```
----
<div align="center">
  <img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/angela.webp" alt="Angela CLI Logo" width="200" height="200">
  <h3>Worlds First AGI Command Line Intelligence</h3>
  <p><em>Your ambient-intelligence terminal companion that understands natural language and your development context</em></p>
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![Gemini API](https://img.shields.io/badge/AI-Gemini_API-orange)](https://ai.google.dev/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/CarterPerez-dev/angela-cli)
[![Code Coverage](https://img.shields.io/badge/coverage-87%25-green)](https://github.com/CarterPerez-dev/angela-cli)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
----

[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/UI.png" width="100" alt="Angela UI Example">](#angela-ui-example)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/angela.webp" width="100" alt="Angela Logo/Mascot">](#angela-logo)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/confirmation.png" width="100" alt="Confirmation Prompt">](#confirmation-prompt)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/flow.svg" width="100" alt="Angela Workflow Diagram">](#angela-workflow-diagram)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/generate-help.png" width="100" alt="Generate Help Command">](#generate-help-command)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/help.png" width="100" alt="Angela Help Output">](#angela-help-output)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/loading.png" width="100" alt="Loading Animation">](#loading-animation)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/output.png" width="100" alt="Command Output Example">](#command-output-example)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part1.png" width="100" alt="Screenshot Part 1">](#screenshot-part-1)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part2.png" width="100" alt="Screenshot Part 2">](#screenshot-part-2)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part3.png" width="100" alt="Screenshot Part 3">](#screenshot-part-3)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part4.png" width="100" alt="Screenshot Part 4">](#screenshot-part-4)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/react.png" width="100" alt="React Project Generation">](#react-project-generation)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/safety.png" width="100" alt="Safety Confirmation">](#safety-confirmation)
[<img src="https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/status.png" width="100" alt="Angela Status Output">](#angela-status-output)

---
**Project Vision:** Angela CLI is not just another command-line tool; she's the worlds first AGI (will be), but lives inside a place named `shell`, designed to understand your natural language, execute commands intelligently, manage complex workflows, and even help you write and refactor code. She's your terminal's new best friend, learning your habits and proactively assisting you.

---
## 🧠 Philosophy

Angela CLI is built on several core principles:

1. **Ambient Intelligence**: Angela should feel like a natural extension of your shell, not a separate tool you have to invoke. The boundary between standard commands and AI assistance should be minimal.

2. **Contextual Understanding**: True assistance requires understanding the user's environment, project structure, and goals. Angela prioritizes deep context awareness.

3. **Multi-Level Abstraction**: Users should be able to communicate at any level of abstraction, from specific commands to high-level goals, and get appropriate responses.

4. **Progressive Disclosure**: Simple tasks should be simple, while complex capabilities should be available when needed but not overwhelming.

5. **Learning Over Time**: The system should learn from user interactions to improve its suggestions and adaptations over time.
---

**Current Status: Solid Foundation Laid, Core Execution Loop Getting Polished!**

I've successfully built the skeleton and much of the nervous system of Angela. Here's what's looking good and what we've recently tuned up:

**What's Done / Recently Improved (The "Angela Can Already Do This" List):**

1.  **Core Structure & Imports (The Blueprint is Solid):**
    *   The entire file structure is in place.
    *   The `api/` layer was a smart but PAINFULL refactor, acting as a clean interface to all the `components/`. This keeps things tidy and avoids import spaghetti, which completly FRIES my brain managing.
    *   All `__init__.py` files are set up, making the Python packaging organized and clean.
    *   The `core/registry.py` is the central switchboard, making sure components can find each other without getting fu****.

2.  **Basic Command Request Lifecycle (Angela's Basic Conversation):**
    *   **Input:** `angela request "do something simple"` (via `components/cli/main.py`).
    *   **Orchestration (`orchestrator.py`):** This is Angela's brain. It takes your request and starts figuring out what to do. The `_process_command_request` is getting pretty good at handling straightforward commands.
    *   **AI Suggestion (`components/ai/client.py`, `prompts.py`, `parser.py`):** Angela talks to her AI friend (Gemini, specifically 2.5 pro preview) to get a command suggestion. The client and basic prompts are working, and the parser can understand what the AI says. I've defualt the safety settings to permissive / NONE,  allowing for a wider range of command suggestions.
    *   **Safety 95% done (`components/safety/`):**
        *   `classifier.py`: Can categorize commands by risk (SAFE, LOW, MEDIUM, HIGH, CRITICAL).
        *   `validator.py`: Checks for obviously dangerous patterns.
        *   `preview.py`: Can generate previews for many common commands, helping you see what will happen.
        *   `confirmation.py`: Handles the basic "Are you sure?" for risky things.
        *   **`adaptive_confirmation.py` (Recently Tuned!):** This is getting smarter and is bascially completed! It now better handles when to ask for confirmation versus when to auto-execute based on command trust, risk, and history. The double "Auto-Executed" panel issue for trusted commands should be much improved or resolved. The UI for it is looking fantastic as well.
    *   **Execution (`components/execution/`):**
        *   **`adaptive_engine.py` (Recently Tuned!):** This engine now has a clearer flow for when to display auto-execution notices versus full confirmation prompts. It's also getting better at ensuring actual command output is shown after execution.
        *   `engine.py`: The underlying workhorse that actually runs the commands.
    *   **UI & Feedback (`components/shell/formatter.py`):**
        *   The basic theme (colors, boxes) is established, theme, UI, Rich Styling.
        *   Angela can display suggested commands, previews, risk warnings, and confirmation prompts with a consistent look.
        *   The "Angela Initialized" and success/failure messages after command execution are now more reliably displayed.
        *   The loading/execution timer is in place and is working amazing. It randomly outputs 1/50 philosophy quotes....because philosophy is cool. Im kinda going for that 'Her' Movie vibe, I mean, this is essentially what Angela is.....am I in love with her you ask?!.....no......of course not.....why would you think that?......😅😅 
        * Anyway, here is an example of what the UI is looking like at the moment --->

PICTURE HERE

3.  **Context is Key (`components/context/`):**
    *   `preferences.py` & `history.py`: Angela remembers your settings and what you've done before, which feeds into adaptive confirmation.
    *   `manager.py`: Knows where you are (`cwd`) and if you're in a project.
    *   **`file_resolver.py` (Majorly Enhanced!):** Angela's "File Detective" is now quite skilled at figuring out *which* file you mean, even if you're a bit vague.

4.  **Utilities (`components/utils/`):**
    *   `logging.py` & `enhanced_logging.py`: Angela keeps a good diary of what she's doing, especially useful for debugging.

5.  **Interactive Command Handling (`utils/command_utils.py`):**
    *   Angela now politely tells you to run interactive commands (like `vim` or `top`) yourself, as she can't really "drive" those for you.

6.  **Basic CLI Functionality (`components/cli/main.py`):**
    *   `angela --help`, `angela --version`, `angela init` are up and running.

7.  **Development Setup:**
    *   `pytest.ini`, `Makefile` are ready, making development smoother.

**The "Angela is Learning & Growing" Roadmap (What's Next):**

Think of this as Angela going to different schools to learn new skills. Each "family" or "department" in her brain (`components/`) needs attention.

**Overall Theme for Next Steps:** *From Baseline to Brilliance*. We have the structures; now we need to flesh them out, make them robust, and ensure they all talk to each other seamlessly. I'll focus on **testing, refining, and debugging** existing components while **incrementally building out** new functionalities.

**Phase 1: Strengthening the Core & Understanding**

*   **The "Analyzer Family" (`components/ai/analyzer*.py` files):**
    *   **Goal:** Make Angela a true "code whisperer."
    *   **Files:** `analyzer.py` (error analysis), `content_analyzer.py` (understanding file content), `content_analyzer_extensions.py` (handling more file types), `intent_analyzer.py` (figuring out *what* you want), `semantic_analyzer.py` (deep code understanding).
    *   **What to do:**
        1.  **Error Analyzer (`analyzer.py`):** Enhance its pattern matching for common errors. Test its suggestions. Does it give useful advice when commands fail?
        2.  **Intent Analyzer (`intent_analyzer.py`):** This is crucial. Refine its ability to correctly classify your requests. Test with ambiguous phrasings. How well does it pick the right `RequestType` in `orchestrator.py`?
        3.  **Content Analyzer (`content_analyzer.py` & `extensions`):**
            *   Flesh out the `_analyze_python`, `_analyze_typescript`, `_analyze_json` methods.
            *   Implement the other `_analyze_*` methods for different languages and data formats. This will be key for context.
        4.  **Semantic Analyzer (`semantic_analyzer.py`):** This is a big one for advanced features.
            *   Start by thoroughly testing `analyze_file` for Python and JavaScript.
            *   Ensure `_analyze_python_file` and `_analyze_javascript_file` correctly extract functions, classes, imports.
            *   The `_analyze_with_llm` is a good fallback but will be slower and less precise; prioritize native parsers.
    *   **Fun Explanation:** The Analyzers are Angela's senses and deductive reasoning. `IntentAnalyzer` is her ears, figuring out the gist. `ContentAnalyzer` is her eyes, reading the files. `SemanticAnalyzer` is her deep-thinking brain, understanding the *meaning* of the code. `ErrorAnalyzer` is her troubleshooter.

*   **The "Prompts Department" (`components/ai/prompts.py`, `enhanced_prompts.py`):**
    *   **Goal:** Craft perfect instructions for Angela's AI backend.
    *   **What to do:** As I enhance the analyzers, refine the prompts to *use* that new contextual information. For example, if `SemanticAnalyzer` can identify a class, the prompt for "refactor this class" should include that semantic info.
    *   Test how different phrasings in my prompts affect the AI's output quality for suggestions and plans.

**Phase 2: Mastering Complex Tasks & Workflows**

*   **The "Planner Posse" (`components/intent/planner.py`, `enhanced_task_planner.py`, `complex_workflow_planner.py`, `semantic_task_planner.py`):**
    *   **Goal:** Enable Angela to handle multi-step operations and user-defined workflows flawlessly.
    *   **Files & What will I do:**
        1.  **`planner.py` (Basic):** Ensure `_create_basic_plan` and `_execute_basic_plan` are robust for simple sequences identified by the `Orchestrator`. Test how it handles dependencies.
        2.  **`enhanced_task_planner.py`:** This is the workhorse for more complex, *single-tool* or *single-domain* plans.
            *   Thoroughly test `_execute_advanced_step` for each `PlanStepType` (COMMAND, CODE, FILE, DECISION, API, LOOP).
            *   Focusing on data flow (`_resolve_step_variables`, `_get_variable_value`, `_set_variable`). Does data pass correctly between steps?
            *   Test `_execute_code_step` and its sandboxing carefully.
        3.  **`semantic_task_planner.py`:**
            *   Integrate its `_analyze_intent` more deeply if it offers advantages over the basic `IntentAnalyzer`.
            *   Testing the `_create_clarification` and `_get_user_clarification` flow. This is key for ambiguous requests.
        4.  **`complex_workflow_planner.py` (and `components/toolchain/cross_tool_workflow_engine.py`):** This is for orchestrating *multiple different tools* (e.g., git -> docker -> aws).
            *   Test `create_workflow` and `execute_workflow`.
            *   Focus on `_execute_step` within this planner, ensuring it correctly calls the `EnhancedUniversalCLI` or specific tool integrations.
            *   Data flow (`_apply_data_flow`) between different tools is critical here.
    *   **Fun Explanation:** The Planners are Angela's strategists. `TaskPlanner` handles simple to-do lists. `EnhancedTaskPlanner` is like a project manager for more involved tasks within one "department" (e.g., a series of Git commands). `SemanticTaskPlanner` is the diplomat, asking for clarification. `ComplexWorkflowPlanner` is the grand conductor, making different orchestras (tools) play together in harmony.

*   **The "Workflow Brigade" (`components/cli/workflows.py`, `components/workflows/manager.py`, `sharing.py`):**
    *   **Goal:** Allow users to create, save, run, and share their own automated sequences.
    *   **What I'll do:**
        1.  Test `angela workflows create` (both interactive and from file).
        2.  Test `angela workflows run` with and without variables.
        3.  Test `angela workflows export` and `import`.
        4.  Ensure `WorkflowManager._substitute_variables` works correctly.

**Phase 3: Supercharging Code Generation**

*   **The "Generation Guild" (ALL files in `components/generation/`):**
    *   **Goal:** This is Angela's superpower – creating code, from single files to entire projects. This will be a major focus.
    *   **Files & What I'll do (Iterative Process):**
        1.  **`models.py`:** Already good, defines `CodeFile`, `CodeProject`.
        2.  **`validators.py`:** Add more validators for other languages (Ruby, Rust, PHP, C++, C#, Swift, Kotlin). Make existing ones more robust.
        3.  **`architecture.py` (`ArchitecturalAnalyzer`):**
            *   Implement more `ArchitecturalPattern` and `AntiPattern` detectors (e.g., Layered, Microservices, Spaghetti Code, Lava Flow).
            *   Test `analyze_project_architecture` thoroughly.
        4.  **`planner.py` (`ProjectPlanner` - this one is for *code generation* planning):**
            *   This is critical. Testing `create_detailed_project_architecture` and `create_project_plan_from_architecture`. The quality of the AI's output here dictates the quality of the generated project.
            *   Refine prompts in `_build_detailed_architecture_prompt`.
        5.  **`context_manager.py` (`GenerationContextManager`):**
            *   Testing how well it tracks entities and dependencies *during a generation process*.
            *   Ensure the `enhance_prompt_with_context` provides useful, non-redundant context to the AI when it's generating subsequent files.
        6.  **`frameworks.py` (`FrameworkGenerator`):**
            *   Flesh out `_generate_react`, `_generate_django`, etc.
            *   Implement the `_generate_enhanced_*` methods for more production-ready structures.
            *   The `_generate_content` (which calls `_generate_file_content`) is key. It needs robust prompting.
        7.  **`engine.py` (`CodeGenerationEngine`):**
            *   This is the main engine. `generate_project` and `generate_complex_project` are the top-level entry points.
            *   `_create_project_plan` and `_generate_file_contents` (and their complex counterparts) are the core loops. Debugging these will involve looking at the AI prompts and responses for each file.
            *   Test `add_feature_to_project` – this is complex as it involves understanding existing code.
        8.  **`documentation.py` (`DocumentationGenerator`):**
            *   Implement and test README, API doc, and guide generation for various project types.
        9.  **`refiner.py` (`InteractiveRefiner`):**
            *   Test `process_refinement_feedback`. How well does it understand feedback and apply it to specific files?
    *   **Explanation:** The Generation Guild is Angela's construction crew. `ProjectPlanner` and `ArchitecturalAnalyzer` are the architects. `FrameworkGenerator` provides the blueprints for common building types. `CodeGenerationEngine` is the master builder, and `GenerationContextManager` is the site foreman making sure everyone has the right info. `InteractiveRefiner` is the quality inspector and renovation expert.

**Phase 4: Enhancing System Awareness & Proactivity**

*   **The "Monitoring Squad" (`components/monitoring/`):**
    *   **Goal:** Make Angela a watchful guardian.
    *   **Files & What I'll do:**
        1.  **`background.py` (`BackgroundMonitor`):**
            *   Testing `_monitor_git_status`, `_monitor_file_changes`, `_monitor_system_resources`. Are they triggering correctly?
            *   Refining the conditions under which suggestions are made (e.g., `_can_show_suggestion`).
        2.  **`network_monitor.py` (`NetworkMonitor`):**
            *   Testing service detection and status checking.
            *   Improve dependency update checks for more project types.
        3.  **`notification_handler.py`:** Test integration with shell hooks. Are `pre_exec`, `post_exec`, `dir_change` notifications handled correctly and updating context?
        4.  **`proactive_assistant.py`:**
            *   This ties it all together. Testing the `_handle_monitoring_event` and individual `_handle_*_insight` methods.
            *   Implementing more `_pattern_detectors` for common issues.
            *   Refining the actual suggestions made – are they helpful and actionable?
    *   **Fun Explanation:** The Monitoring Squad are Angela's spies and sensors, always keeping an eye on your system and how you work, ready to offer a helpful tip through the `ProactiveAssistant`.

**Phase 5: Fine-tuning Execution and Context**

*   **The "Execution Excellence" Team (`components/execution/`):**
    *   **Goal:** Flawless command execution and robust error handling.
    *   **Files & What I'll do:**
        1.  **`error_recovery.py`:** This is vital and complex.
            *   Test `handle_error`. Does it correctly analyze errors and suggest/apply sensible recovery strategies?
            *   The learning aspect (`_learn_from_recovery_result`) needs careful testing.
        2.  **`filesystem.py`:** This seems to be working well, which is great! However, I will do a quick review for edge cases.
        3.  **`hooks.py`:** What specific actions are these hooks meant to trigger beyond basic file activity tracking? I will ensure they are registered and firing correctly.
        4.  **`rollback.py` & `rollback_commands.py`:** Critical for safety.
            *   Test recording operations for each type (filesystem, content, command, plan).
            *   Test `rollback_operation` and `rollback_transaction`. Do they correctly revert changes?
            *   Test the CLI commands in `rollback_commands.py`.

*   **The "Contextual Masters" (`components/context/`):**
    *   **Goal:** Ensure Angela always has the richest, most relevant context.
    *   **Files & What I'll do:**
        1.  **`file_activity.py` & `enhanced_file_activity.py`:** Testing that activities are being tracked correctly, especially the enhanced entity tracking.
        2.  **`file_detector.py`:** Add more `LANGUAGE_EXTENSIONS` and `FILENAME_MAPPING` as needed.
        3.  **`project_state_analyzer.py`:** This is a big one.
            *   Testing `_analyze_git_state`, `_analyze_test_status`, `_analyze_build_status`, etc., for various project types. Are they accurate?
            *   The `_find_todo_items` is a nice touch (for me lol).
        4.  **`enhancer.py` (`ContextEnhancer`):** This glues many context pieces together. I need to Verify that `enrich_context` correctly calls and integrates info from `ProjectInference`, `FileActivityTracker`, etc.
        5.  **`project_inference.py` (`ProjectInference`):** This is the cousin to the AI analyzers. Its job is to figure out what *kind* of project it's in.
            *   Test `infer_project_info` with diverse project structures.
            *   Refine `PROJECT_SIGNATURES` and `FRAMEWORK_SIGNATURES`.
            *   Ensure dependency detection (`_detect_dependencies`) is accurate for more languages.
        6.  **`semantic_context_manager.py`:** This is the "semantic family" head for context.
            *   Test `refresh_context` and how it integrates `ProjectStateAnalyzer` and `SemanticAnalyzer`.
            *   Test `get_entity_info`, `find_related_code`, `get_code_summary`, `get_project_summary`. These are powerful features that need robust backing from the semantic analyzer. As you can tell I'm into Semantics.

**Phase 6: Polishing the User Experience**

*   **The "Shell Wizards" (`components/shell/`):**
    *   **Goal:** Make Angela feel like a natural, seamless part of the terminal.
    *   **Files & What I'll do:**
        1.  **`enhanced_formatter.py` (To be developed alongside planners/generators):** As I build out `AdvancedTaskPlan` display, `ComplexWorkflowPlan` display, and code generation result displays, I'll implement the corresponding methods here. This should be done *iteratively* as the things it needs to format are developed.
        2.  **`inline_feedback.py`:** Flesh this out. Test `show_message` and `suggest_command`. The `_get_edited_command` with `prompt_toolkit` is a nice touch for a good UX.
        3.  **`completion.py`:** Testing `get_completions` for various commands and contexts. Refine `_get_ai_completions` for natural language command parts.
        4.  **`.bash` & `.zsh` Shell Integration Scripts:** Test these thoroughly in their respective shells. Ensure hooks fire correctly and don't slow down the terminal. Test completions.

*   **The "Review Crew" (`components/review/`):**
    *   **Goal:** Enable effective review and application of changes.
    *   **Files & What I'll do:**
        1.  **`diff_manager.py`:** Test `generate_diff` and `apply_diff`.
        2.  **`feedback.py` (`FeedbackManager`):** Crucial for iterative code generation and refinement.
            *   Test `process_feedback` – how well does it understand textual feedback and translate it into code changes via the AI?
            *   Test `refine_project` for broader, project-wide feedback.
            *   Test `apply_refinements` to ensure changes are written correctly.



---

## Want to Help Build Angela? Awesome! 🚀

Contributing is easy:

1.  **Fork It:** Click "Fork" on the main Angela CLI project page to make your own copy.
2.  **Clone It:** Download your forked copy to your computer:
    `git clone https://[YourGitPlatform]/[YourUsername]/angela-cli.git`
3.  **Branch Out:** Create a new branch for your changes:
    `git checkout -b my-cool-angela-feature`
4.  **Code Away:** Make your awesome changes, add tests, and write docs!
5.  **Push It:** Save your work back to *your* forked copy:
    `git push origin my-cool-angela-feature`
6.  **Pull Request (PR) Time:** Go to the *original* Angela CLI project and open a "Pull Request" from your new branch. Explain what you did.
7.  **Chat & Merge:** Angela and I will look it over, maybe chat a bit, and then merge your great work in!

**Quick Tips:**
*   Small, focused PRs are best.
*   If it's a big idea, open an "issue" to chat first.
*   Make sure tests pass!

Thanks for helping make Angela smarter! ✨

---

# KEEP IN MIND-- ANGELA IS NOT COMPLETE YET, SHE'S IS IN ITS VERY BEGINING STAGES, SHE's STILL A MINOR!!
-----

## Screenshots & Examples

#### Angela UI Example
<a id="angela-ui-example"></a>
![Angela UI Example](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/UI.png)

#### Angela Logo
<a id="angela-logo"></a>
![Angela Logo/Mascot](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/angela.webp)

#### Confirmation Prompt
<a id="confirmation-prompt"></a>
![Confirmation Prompt](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/confirmation.png)

#### Angela Workflow Diagram
<a id="angela-workflow-diagram"></a>
![Angela Workflow Diagram](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/flow.svg)

#### Generate Help Command
<a id="generate-help-command"></a>
![Generate Help Command](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/generate-help.png)

#### Angela Help Output
<a id="angela-help-output"></a>
![Angela Help Output](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/help.png)

#### Loading Animation
<a id="loading-animation"></a>
![Loading Animation](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/loading.png)

#### Command Output Example
<a id="command-output-example"></a>
![Command Output Example](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/output.png)

#### Code Project Generation 
<a id="screenshot-part-1"></a>
![Screenshot Part 1](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part1.png)

#### Code Project Generation Part 2
<a id="screenshot-part-2"></a>
![Screenshot Part 2](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part2.png)

#### Code Project Generation Part 3
<a id="screenshot-part-3"></a>
![Screenshot Part 3](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part3.png)

#### Code Project Generation 4
<a id="screenshot-part-4"></a>
![Screenshot Part 4](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/part4.png)

#### Code Project Generation part 5
<a id="react-project-generation"></a>
![React Project Generation](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/react.png)

#### Safety Confirmation
<a id="safety-confirmation"></a>
![Safety Confirmation](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/safety.png)

#### Angela Status Output
<a id="angela-status-output"></a>
![Angela Status Output](https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/MD/assets/status.png)






