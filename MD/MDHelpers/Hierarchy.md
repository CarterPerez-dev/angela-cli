### To give an AI the best possible understanding of Angela-CLI with a limited set of files, prioritize files that provide:

1.  **High-level overview and goals.**
2.  **Core architecture and orchestration.**
3.  **Key data structures and interfaces.**
4.  **Entry points and primary control flow.**
5.  **Crucial business logic for unique features.**

Here's a ranked list of files, from **most important** to **less critical for initial overall context**. The idea is to provide a "slice" of the project that gives the AI the best chance to grasp its essence.

**Tier 1: Essential Overview & Core Orchestration (Must-Haves)**

1.  **`README.md`**
    *   **Why:** This is the primary human-readable description of the project's vision, goals, and high-level features. It sets the stage for everything else. The AI needs to understand *what* you're trying to build.
2.  **Roadmap Files (e.g., `Phase_8_12.md` or a consolidated roadmap if available)**
    *   **Why:** These outline the intended functionality, development phases, and key components. This gives the AI insight into the project's evolution and the purpose of different modules.
3.  **`angela/__main__.py`**
    *   **Why:** The main entry point of the application. It shows how the CLI is invoked and initialized.
4.  **`angela/orchestrator.py`**
    *   **Why:** This is the central nervous system. Understanding how it determines request types and dispatches to various sub-modules is critical for grasping the overall application flow.
5.  **`angela/config.py`**
    *   **Why:** Shows how the application is configured, including API keys and user preferences. Configuration is fundamental to how an application behaves.
6.  **`pyproject.toml`**
    *   **Why:** Defines project dependencies, build system, and metadata. Crucial for understanding the project's ecosystem and how it's packaged.

**Tier 2: Core Architectural Pillars & Key Logic**

7.  **`angela/ai/client.py`**
    *   **Why:** Shows how Angela interacts with the core AI (Gemini). This is a fundamental capability.
8.  **`angela/ai/prompts.py` (or `enhanced_prompts.py` if it's the primary one)**
    *   **Why:** Reveals how Angela formulates requests to the LLM, which is key to its "intelligence."
9.  **`angela/context/manager.py`**
    *   **Why:** Manages the runtime context (CWD, project root, etc.). Essential for understanding how Angela perceives its environment.
10. **`angela/intent/planner.py` (and `angela/intent/enhanced_task_planner.py` due to its integration)**
    *   **Why:** Core to decomposing user requests into actionable steps. The `EnhancedTaskPlanner` is particularly important for advanced features. Showing both might be necessary if their roles are distinct or if the patching mechanism is key. If `EnhancedTaskPlanner` fully supersedes, prioritize it.
11. **`angela/execution/engine.py` (and `angela/execution/adaptive_engine.py`)**
    *   **Why:** Shows how commands are actually executed and how safety/adaptability are layered on top.
12. **`angela/shell/angela_enhanced.bash` (or `.zsh` depending on primary target)**
    *   **Why:** Demonstrates the deep shell integration logic, which is a core design goal.
13. **`angela/intent/models.py`**
    *   **Why:** Defines core data structures like `Intent` and `ActionPlan`, which are fundamental to how requests are processed.
14. **`angela/safety/validator.py` and `angela/safety/confirmation.py` (or `adaptive_confirmation.py`)**
    *   **Why:** Safety is a key concern. These show how it's implemented.

**Tier 3: Important Supporting Modules & Unique Features**

15. **`angela/__init__.py` (top-level)**
    *   **Why:** Shows how the main application components are initialized and registered (via `init_application`).
16. **`angela/ai/parser.py`**
    *   **Why:** How AI responses are translated back into structured data.
17. **`angela/ai/intent_analyzer.py`**
    *   **Why:** Crucial for the initial understanding of user input.
18. **`angela/generation/engine.py` (if massive code generation is a current focus)**
    *   **Why:** The core of the autonomous code generation capability.
19. **`angela/toolchain/universal_cli.py` (if universal tool translation is a current focus)**
    *   **Why:** Key to the "universal translator" goal.
20. **`angela/constants.py`**
    *   **Why:** Provides context on fixed values used throughout the application.
21. **`angela/core/registry.py` and `angela/core/events.py`**
    *   **Why:** Show fundamental patterns for decoupling and communication.
22. **`angela/context/semantic_context_manager.py` (if deep semantic understanding is a current focus)**
    *   **Why:** Central to the advanced contextual awareness.
23. **`angela/execution/rollback.py`**
    *   **Why:** Important for safety and complex operations.

**Tier 4: Representative Examples of Other Modules (Pick 1-2 from key areas if space allows)**

24. **`angela/cli/main.py`**
    *   **Why:** Shows how the various subcommands are structured using Typer.
25. **One specific toolchain integration, e.g., `angela/toolchain/docker.py` or `angela/toolchain/git.py`**
    *   **Why:** To give an example of how Angela interacts with external developer tools.
26. **One specific generation module, e.g., `angela/generation/planner.py` or `angela/generation/architecture.py`**
    *   **Why:** To illustrate the depth of the code generation capabilities.
27. **`angela/utils/logging.py` (and `enhanced_logging.py`)**
    *   **Why:** Shows how logging, a crucial utility, is handled.

**Less Critical for Initial *Overall* Context (Provide if AI asks or if focusing on these areas):**

*   **Individual CLI command files (`angela/cli/files.py`, `angela/cli/workflows.py`, etc.):** While important for their specific commands, `angela/cli/main.py` gives the structural overview.
*   **Most other `__init__.py` files (beyond the top-level and maybe 1-2 key packages):** Useful for understanding package exports, but the directory structure itself implies packaging.
*   **Shell scripts for other shells if one primary one is already provided.**
*   **Specific `content_analyzer_extensions.py` unless a particular language analysis is key.**
*   **Detailed files within `monitoring/`, `review/` unless these are the immediate focus.**
*   **Test files (`tests/`)**: Crucial for development and understanding how modules *should* behave, but for initial project overview, the source code of the features themselves is higher priority. The AI can be told tests exist and can be provided later if needed.
*   **`Makefile`, `setup.py`**: `pyproject.toml` often covers the most critical build/dependency info for modern Python projects. `setup.py` might be redundant or for specific build backend needs. `Makefile` shows build/dev tasks but might be less about core logic.

**Reasoning for this Ranking:**

*   **Top-Down Understanding:** The AI first needs the "what" and "why" (README, Roadmap) before diving into the "how."
*   **Central Control Flow:** `__main__.py` and `orchestrator.py` show how the application is driven.
*   **Core Capabilities:** Modules directly responsible for AI interaction, context, intent, and execution are next.
*   **Unique Selling Points:** Files related to deep shell integration, code generation, and universal translation are important for understanding the project's ambition.
*   **Supporting Infrastructure:** Config, constants, core patterns (registry, events), and safety mechanisms.
*   **Representative Examples:** If the AI needs to understand how, for example, CLI commands are built, `cli/main.py` is more important initially than every single command file.

This list should give the AI a strong foundation. If its context window is *extremely* limited (e.g., only 5-10 files), you'd have to be even more ruthless, likely focusing on README, Roadmap, `__main__.py`, `orchestrator.py`, and perhaps `ai/client.py` and `intent/planner.py`.

Always tell the AI that this is a *subset* and that you can provide more files as needed for specific areas of inquiry.
