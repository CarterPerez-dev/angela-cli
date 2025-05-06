# Angela-CLI: Detailed Technical Blueprint

## Technology Stack Specification

### Core Foundation
- **Python 3.9+**: Primary implementation language
- **Bash/Zsh**: Target shells for integration
- **Google Gemini API**: AI service backbone
- **Ubuntu Linux**: Primary target platform

### Key Technical Components

1. **Shell Integration Libraries**
   - `pexpect`/`pty`: Terminal interaction and process control
   - `prompt_toolkit`: Rich terminal user interfaces
   - Native shell hooks (PROMPT_COMMAND, preexec, DEBUG trap)

2. **Core Framework**
   - `typer`/`click`: Command-line argument processing
   - `rich`: Terminal formatting and display
   - `asyncio`: Asynchronous operation support

3. **AI & NLP**
   - `google-generativeai`: Official Gemini SDK
   - `aiohttp`: Async API communication
   - Custom prompt engineering framework

4. **Execution & Safety**
   - `subprocess`: Safe command execution
   - `shlex`: Command parsing and escaping
   - `difflib`: File diff generation
   - `pathlib`: Modern file path handling

5. **Configuration & Context**
   - `configparser`/`tomli`: Configuration management
   - `python-dotenv`: Environment variable handling
   - Custom project detection logic

## Detailed Roadmap

### Phase 1: Foundation & Shell Integration 
**Milestone 1A: Core Setup **
- Project scaffolding and environment setup
- Configuration management implementation
- Basic CLI structure with argument processing
- Shell hook mechanism (bash/zsh function)
- Simple request echo pipeline

**Milestone 1B: Context & Pipeline**
- Working directory tracking
- Basic project root detection (git/marker files)
- Command history integration
- Logging and telemetry framework
- Test infrastructure

### Phase 2: AI Integration
**Milestone 2A: Gemini Integration)**
- Gemini API client implementation
- Initial prompt engineering
- Response parsing framework
- Basic intent classification
- Command suggestion (non-executing)

**Milestone 2B: Read-Only Operations**
- Safe command execution engine
- Support for info retrieval commands (find, grep, etc.)
- Output formatting and display
- Enhanced error handling
- Command validation

### Phase 3: File Operations
**Milestone 3A: Safety System)**
- Operation risk classification system
- Confirmation interface with previews
- Command impact analysis
- Permission model implementation
- Dry-run capability

**Milestone 3B: Basic File Operations**
- Directory operations (mkdir, ls enhancements)
- File creation operations (touch, basic content)
- Simple content viewing
- Enhanced context with file type detection
- Basic rollback capability

### Phase 4: Enhanced Context & Developer Tool
**Milestone 4A: Project Context**
- Project type inference (Python, Node.js)
- Basic dependency awareness
- Configuration file understanding
- Improved natural language file references
- Recent activity tracking

**Milestone 4B: Developer Workflows)**
- Git operations integration
- Docker basic support
- Simple code snippet generation
- Multi-step workflow execution
- Performance optimization

## Implementation File Structure

```
angela-cli/
├── README.md                   # Project documentation
├── pyproject.toml              # Project metadata & build config
├── requirements.txt            # Python dependencies
├── setup.py                    # Package installation
├── Makefile                    # Build automation
├── .env.example                # Environment variable template
│
├── scripts/                    # Installation scripts
│   ├── install.sh              # Install shell integration
│   └── uninstall.sh            # Clean removal
│
├── angela/                     # Main package
│   ├── __init__.py             # Package initialization
│   ├── __main__.py             # CLI entry point
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # Configuration management
│   ├── constants.py            # Global constants
│   ├── orchestrator.py         # Main orchestration service
│   │
│   ├── shell/                  # Shell integration
│   │   ├── __init__.py
│   │   ├── hooks.py            # Shell hook implementations
│   │   ├── processor.py        # Request preprocessing
│   │   └── formatter.py        # Terminal output formatting
│   │
│   ├── ai/                     # AI service interaction
│   │   ├── __init__.py
│   │   ├── client.py           # Gemini API client
│   │   ├── prompts.py          # Prompt engineering templates
│   │   ├── parser.py           # Response parsing
│   │   └── models.py           # AI data models
│   │
│   ├── context/                # Context management
│   │   ├── __init__.py
│   │   ├── manager.py          # Context orchestration
│   │   ├── project.py          # Project detection
│   │   ├── filesystem.py       # File system understanding
│   │   └── history.py          # Command history
│   │
│   ├── intent/                 # Intent understanding
│   │   ├── __init__.py
│   │   ├── analyzer.py         # Intent classification
│   │   ├── planner.py          # Action planning
│   │   └── models.py           # Intent data structures
│   │
│   ├── execution/              # Execution engine
│   │   ├── __init__.py
│   │   ├── engine.py           # Main execution controller
│   │   ├── commands.py         # Shell command execution
│   │   ├── filesystem.py       # File operations
│   │   └── tools/              # Tool integrations
│   │       ├── __init__.py
│   │       ├── git.py          # Git operations
│   │       └── docker.py       # Docker operations
│   │
│   ├── safety/                 # Safety framework
│   │   ├── __init__.py
│   │   ├── classifier.py       # Risk classification
│   │   ├── confirmation.py     # User confirmation UI
│   │   ├── preview.py          # Action preview generation
│   │   └── validator.py        # Safety validation
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── logging.py          # Logging setup
│       ├── exceptions.py       # Custom exception classes
│       └── helpers.py          # Misc helpers
│
├── shell/                      # Shell integration files
│   ├── angela.bash             # Bash integration
│   └── angela.zsh              # Zsh integration
│
└── tests/                      # Test suite
    ├── __init__.py
    ├── conftest.py             # Test fixtures
    ├── test_cli.py
    ├── test_shell.py
    ├── test_context.py
    ├── test_execution.py
    └── test_safety.py
```

## Step-by-Step Implementation Plan

### Step 1: Project Setup & Shell Hook
1. Initialize project structure with core directories
2. Implement basic configuration loading (API keys)
3. Create shell function in `angela.bash`/`angela.zsh`:
   ```bash
   # Basic shell hook
   angela() {
     python -m angela "$@"
   }
   ```
4. Implement CLI entry point with argument parsing
5. Create simple echo capability that passes request to Python backend

### Step 2: Orchestration & Context
1. Build orchestrator to manage request flow
2. Implement working directory tracking
3. Create project root detection via markers (.git, etc.)
4. Add basic logging and error handling
5. Design data models for requests/responses
6. Implement testing framework

### Step 3: Gemini API Integration
1. Create Gemini API client class
2. Design initial prompt templates with context injection
3. Implement response parsing and error handling
4. Build basic intent classification (command vs. file operation)
5. Add simple command suggestion capability (non-executing)

### Step 4: Intelligent Interaction & Contextual Execution
(Focus: Make single commands/simple sequences smarter, faster, and provide richer feedback. Enhance immediate context use.)
Enhanced NLU & Tolerant Parsing: Implement more sophisticated Natural Language Understanding (ai/parser.py, intent/analyzer.py) to handle more complex or slightly misspelled/ambiguous single commands or simple sequences. Introduce interactive clarification (safety/confirmation.py using prompt_toolkit) but only when confidence is low (e.g., below ~70% match or high ambiguity); otherwise, attempt the most likely interpretation to maintain flow.
Rich Feedback & Asynchronous Streaming: Integrate rich and asyncio deeply (execution/engine.py, shell/formatter.py) for real-time, well-formatted feedback during command execution. Provide progress indicators (spinners/bars), stream stdout/stderr asynchronously, and give clear status updates, making Angela feel highly responsive. Capture all output cleanly.
Context-Aware Adaptive Confirmation: Leverage project type, recent activity, and command history (context/manager.py) to dynamically adjust confirmation needs (safety/classifier.py, orchestrator.py). Frequently used, low-risk commands in familiar contexts execute with minimal friction, while riskier operations still get detailed previews (safety/preview.py), balancing seamlessness with safety. Add detailed command history tracking (context/history.py).
Intelligent Error Analysis & Basic Fix Suggestions: When commands fail, use the AI (ai/parser.py, execution/engine.py) to analyze stderr in context. Proactively suggest potential fixes, relevant commands (e.g., ls if a file isn't found, permission checks), or documentation lookups based on the error message and command attempted.
Enhanced File/Directory Operations & Context: Implement more robust and complex file/directory operations (execution/filesystem.py) building on Phase 3 basics (e.g., recursive operations, pattern matching). Enhance context (context/filesystem.py) with reliable file type detection and basic metadata understanding to inform AI suggestions and operations.

### Step 5: Autonomous Task Orchestration & Proactive Assistance
(Focus: Enable high-level goal execution, deep content understanding, learning user workflows, and proactive behaviour.)
High-Level Goal Decomposition & Multi-Step Orchestration: Empower the AI (intent/planner.py, orchestrator.py) to break down complex user goals ("Deploy latest dev to staging") into sequences of commands/actions. Plan dependencies, visualize the execution flow (shell/formatter.py with rich), gain confirmation, and execute the orchestrated plan, monitoring progress and handling intermediate steps/errors gracefully.
Conversational Context & Session Memory: Implement robust session memory (context/manager.py, orchestrator.py) allowing Angela to understand follow-up commands referencing entities (files, outputs, errors) from the current interaction ("Try that again with sudo", "Analyze those errors").
AI-Powered File Content Comprehension & Manipulation: Integrate AI (ai/client.py, potentially new ai/content_analyzer.py) to understand the content of files (code functions, config values, text). Enable natural language requests for content-aware tasks like refactoring simple functions, updating configuration entries, or summarizing logs (execution/filesystem.py, safety/preview.py showing diffs). Create underlying utilities for safe content manipulation.
User-Defined Workflows via Natural Language: Allow users to teach Angela reusable multi-step workflows ("Define 'publish package' as: run tests, bump version, build, upload"). Angela (intent/planner.py, new workflows/manager.py) translates, confirms, saves, and allows invocation by the user-defined name.
Proactive Monitoring, Suggestions & Advanced Rollback: Implement optional background monitoring (orchestrator.py, asyncio) for contextual nudges (lint errors, git status, process crashes) via shell/formatter.py. Offer proactive suggestions/autofill based on deeper context (context/*, ai/*). Enhance rollback mechanisms (safety/*, execution/*) to specifically support undoing multi-step or content-manipulation actions where feasible, maintaining safety without hindering the autonomous capabilities.

### Step 7: Enhanced Project Context
1. Implement project type inference
2. Add dependency detection in projects
3. Create file reference resolution from natural language
4. Implement recent activity tracking
5. massivly Enhance prompt engineering with project context

### Step 8: Developer Tool Integration (MAIN ASPECTY OF THIS WHOLE THING WERE IT COMES ALL TOGETHOR)
1. Add Git commands integration
2. Implement Docker support
3. Create code generation flow. it shoudl be able to create 8000 word code files, or small websites/apps etc etc. its essntially a code agent capapbale of great coding stregths. if teh user sasy "create me a porfolio website" it shoud be able to udnertand that and go ahead and create a whole directory/tree structure with files and even code those files in full and have it fully ready for developement.
4. Build multi-step workflow execution
5. Perform final testing, optimization, and documentation, containeriziation and even CI/CD if needed

## Initial Implementation Focus

For the immediate first steps, focus on:

1. Setting up the project structure exactly as outlined above
2. Implementing the shell integration mechanism
3. Creating the basic configuration and orchestration pipeline
4. Establishing a simple echo service that confirms Angela received the request
5. Building the foundation for context tracking

This will establish the core infrastructure before integrating AI capabilities, ensuring a solid foundation for the more complex features to follow.
