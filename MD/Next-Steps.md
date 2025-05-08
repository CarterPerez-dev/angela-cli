**Phase 8: Seamless Shell Integration & Enhanced Interaction**

*   **Goal:** Make Angela feel like an intrinsic part of the shell, blurring the lines between standard commands and AI interactions. Improve the core user experience for invoking and interacting with Angela.
*   **Key Objectives:**
    *   **Advanced Shell Hooking:** Investigate and implement deeper shell integration beyond simple aliases. Explore options like:
        *   Zsh/Bash plugins for more sophisticated input interception or pre-command hooks.
        *   Potential integration with terminal multiplexers (like tmux or Zellij) if feasible.
        *   Using `PROMPT_COMMAND` (Bash) or `precmd`/`preexec` (Zsh) hooks for contextual awareness *before* a command is run or *after* it finishes.
    *   **Natural Invocation:** Design mechanisms where Angela can be invoked more naturally, perhaps even implicitly based on command patterns or specific keywords within a command line, rather than always requiring the `angela` prefix. (e.g., detecting `git commit -m "refactor login logic based on ticket #123"` and offering AI assistance).
    *   **Inline Feedback & Interaction:** Enhance `shell/formatter.py` to allow Angela to provide feedback or ask clarifying questions *inline* within the terminal session, potentially modifying the current command line or presenting interactive prompts without breaking the user's flow entirely.
    *   **Contextual Auto-Completion:** Develop AI-powered auto-completion suggestions that leverage Angela's understanding of the project context, recent files, and user intent.

**Phase 9: Deep Contextual Understanding & Semantic Awareness**

*   **Goal:** Elevate Angela's understanding from file paths and types to the *semantic meaning* of code, project state, and complex user intentions.
*   **Key Objectives:**
    *   **Code Semantic Analysis:** Integrate more advanced static analysis tools (like tree-sitter or language servers) or leverage the LLM's code understanding capabilities more deeply to parse functions, classes, dependencies within code files.
    *   **Project State Inference:** Move beyond basic type detection. Infer the *state* of the project (e.g., current Git branch status, pending migrations, test coverage status, build health).
    *   **Fine-Grained Activity Tracking:** Enhance `context/file_activity.py` to track not just file access, but potentially specific function/class modifications (might require IDE integration or file watching with parsing).
    *   **Advanced Intent Decomposition:** Improve `intent/enhanced_task_planner.py` to handle more ambiguous, multi-stage goals. Develop strategies for the LLM to ask clarifying questions when decomposition is uncertain.
    *   **Contextual Prompting V2:** Refine `ai/prompts.py` to feed semantic code information, detailed project state, and nuanced user history to the LLM for significantly more informed responses.

**Phase 10: Expanded Ecosystem Integration (Core Developer Tools)**

*   **Goal:** Enable Angela to understand and interact with a wider range of essential developer tools beyond basic Git and package managers.
*   **Key Objectives:**
    *   **Docker Integration:** Implement understanding and execution of common Docker commands (`build`, `run`, `ps`, `logs`, `stop`, `rm`). Allow requests like "Angela, show me the logs for the webserver container" or "Rebuild the backend Docker image". Requires specific command generation logic and potentially parsing Docker output.
  
    *   **Toolchain Module Enhancement:** Refactor and expand `angela/toolchain/` to include dedicated modules for Docker, abstracting the interaction logic.

**Phase 11: Autonomous Multi-File Code Generation & Refinement**

*   **Goal:** Enable Angela to generate and modify entire multi-file codebases based on high-level descriptions, including interactive refinement.
*   **Key Objectives:**
    *   **Multi-File Planning:** Enhance `generation/planner.py` and `generation/architecture.py` to plan complex directory structures and inter-file dependencies for larger projects (e.g., full web applications).
    *   **Coherent Code Generation:** Improve `generation/engine.py` to generate consistent code across multiple files, ensuring imports, function calls, and data structures align. This likely involves iterative generation and passing context between file generation steps.
    *   **Massive Context Handling:** Implement strategies (e.g., RAG with code context, summarization, iterative prompting) to manage the large context required for generating substantial codebases with the LLM.
    *   **Interactive Refinement Loop:** Integrate `review/feedback.py` and `review/diff_manager.py` more deeply. After generation, present a summary/diff to the user and allow natural language feedback (e.g., "Change the database model to include an email field", "Use functional components instead of class components in React") to trigger regeneration/modification cycles.
    *   **Framework Specialization:** Enhance `generation/frameworks.py` to support generating more complete and idiomatic code for the specific frameworks detected in Phase 9/10.

**Phase 12: Advanced Orchestration & Universal Tool Translation**

*   **Goal:** Achieve near-AGI capability within the terminal by enabling complex task orchestration across *any* CLI tool and automating full CI/CD pipelines.
*   **Key Objectives:**
    *   **Universal CLI Translator:** Develop a robust mechanism (likely LLM-driven with sophisticated prompting and validation) to translate natural language requests into commands for *arbitrary* CLI tools, leveraging `--help` output, man pages, or general knowledge. This requires strong safety validation (`safety/validator.py`).
    *   **Complex Workflow Orchestration:** Enhance the `Orchestrator` and `EnhancedTaskPlanner` to handle workflows involving sequences of commands across different tools (e.g., Git -> Docker -> Cloud CLI -> kubectl).
    *   **Automated CI/CD Pipeline Execution:** Integrate `toolchain/ci_cd.py` fully. Allow requests like "Set up a full CI/CD pipeline for this Node.js project on GitHub Actions, including build, test, lint, and deploy to staging". This involves generating complex configuration *and* potentially triggering initial pipeline runs or setup commands.
    *   **Self-Correction & Learning:** Implement mechanisms for Angela to learn from failed commands or workflows, potentially attempting self-correction or refining its understanding of specific tools based on error messages and successful outcomes.
    *   **Proactive Assistance V2:** Enhance `monitoring/background.py` to offer more complex suggestions based on combined context (e.g., "Your tests failed after the last commit, want me to try reverting and rerunning?", "Your cloud deployment seems to be unhealthy, want me to check the logs?").

These 5 phases provide a structured approach to tackling the remaining challenges, moving from foundational UX improvements and deeper understanding towards complex actions and broad tool integration, culminating in the advanced orchestration required for the AGI-like vision.
