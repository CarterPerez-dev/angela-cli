# Angela-CLI: Comprehensive System Architecture Overview
STEPS -1-5
## Project Purpose and Vision

Angela-CLI is an advanced AI-powered command-line assistant that integrates directly into your terminal shell. It fundamentally transforms how you interact with the command line by allowing you to express complex intentions in natural language rather than memorizing exact command syntax.

The system aims to serve as an intelligent "copilot" for terminal operations with these core capabilities:
- Translating natural language requests into shell commands
- Breaking down complex tasks into executable steps
- Understanding and manipulating file content
- Learning from user interactions to improve over time
- Providing rich, contextual feedback and suggestions

## High-Level Architecture

Angela-CLI follows a modular architecture with clear separation of concerns:

```
angela-cli/
├── angela/          # Core package containing all functionality
├── scripts/         # Installation and utility scripts
├── shell/           # Shell integration files
├── tests/           # Test suite (mentioned in roadmap)
├── pyproject.toml   # Project configuration
├── setup.py         # Package installation
└── Makefile         # Build automation
```

## Core System Components

### 1. `/angela/` - Core Package

This is the heart of the system, containing all functional modules. Each subdirectory serves a specific purpose in the system's operation.

#### `/angela/ai/` - AI Integration Layer

Handles all interaction with the Gemini API and processes natural language:

- **`client.py`**: Manages communication with Google's Gemini API with error handling and retry logic
- **`prompts.py`**: Sophisticated prompt engineering that incorporates context into AI queries
- **`parser.py`**: Transforms AI responses into structured command suggestions
- **`analyzer.py`**: Analyzes command errors and generates fix suggestions
- **`confidence.py`**: Scores confidence in AI suggestions to determine when to seek clarification
- **`intent_analyzer.py`**: Enhanced NLU with tolerance for variations and misspellings
- **`content_analyzer.py`**: Analyzes and manipulates file content based on natural language requests
- **`file_integration.py`**: Bridges AI suggestions with actual file system operations

#### `/angela/context/` - Context Management System

Maintains awareness of the user's environment for more relevant suggestions:

- **`manager.py`**: Central orchestrator of all context information
- **`file_detector.py`**: Sophisticated file type and language detection
- **`history.py`**: Tracks command history and success patterns
- **`preferences.py`**: Manages user-specific settings and preferences
- **`session.py`**: Maintains conversational memory within and between sessions
- **`trust.py`**: Progressive trust system that adapts confirmation requirements based on history

#### `/angela/execution/` - Command Execution System

Safely executes commands with rich feedback:

- **`engine.py`**: Core execution engine for running shell commands
- **`adaptive_engine.py`**: Context-aware execution with dynamic behavior based on history
- **`filesystem.py`**: High-level file operations with safety checks and rollback capabilities
- **`rollback.py`**: Sophisticated undo functionality for operations

#### `/angela/intent/` - Intent Understanding System

Models and processes user intentions:

- **`models.py`**: Data models for structured representation of intent
- **`planner.py`**: Task planning for breaking complex goals into actionable steps

#### `/angela/safety/` - Safety System

Ensures operations are safe and appropriate:

- **`classifier.py`**: Risk classification for commands and operations
- **`validator.py`**: Validation against safety rules and constraints
- **`confirmation.py`**: User confirmation for potentially risky operations
- **`adaptive_confirmation.py`**: Context-aware confirmation that adapts based on history
- **`preview.py`**: Command preview generation to show expected outcomes

#### `/angela/shell/` - Shell Integration

Connects Angela with the terminal environment:

- **`formatter.py`**: Rich terminal formatting with async support and interactive elements
- **`angela.bash`**: Integration with Bash shell
- **`angela.zsh`**: Integration with Zsh shell

#### `/angela/cli/` - Command Line Interface

Provides the user-facing interface:

- **`main.py`**: Primary CLI entry point and command handling
- **`files.py`**: File operation commands with rich formatting
- **`workflows.py`**: Workflow management for defining and running command sequences

#### `/angela/workflows/` - Workflow Management

Handles user-defined sequences of commands (mentioned but implementation files may not be visible in the provided code)

#### `/angela/utils/` - Utilities

Support functionality:

- **`logging.py`**: Logging setup and configuration

### 2. Core Files and Their Functions

- **`orchestrator.py`**: Central coordinator that manages the flow from user request to execution
- **`config.py`**: Configuration management using TOML format
- **`constants.py`**: System-wide constants and settings
- **`__main__.py`**: Entry point when module is executed directly

### 3. `/scripts/` - Installation Scripts

- **`install.sh`**: Installs the package and shell integration
- **`uninstall.sh`**: Removes the package and shell integration

## System Data Flow

1. **Input Reception**: User input is received through the shell integration
2. **Intent Analysis**: The `intent_analyzer` determines what the user is trying to accomplish
3. **Context Gathering**: The `context_manager` gathers relevant information about the environment
4. **AI Processing**: The `gemini_client` generates command suggestions based on intent and context
5. **Risk Analysis**: The `safety` system assesses and classifies risk
6. **Confirmation**: The `adaptive_confirmation` system gets user approval when needed
7. **Execution**: The `adaptive_engine` executes the command with appropriate safeguards
8. **Feedback**: The `formatter` provides rich terminal feedback about the execution
9. **Learning**: The system updates history and patterns based on execution outcome

## Implementation Phases

According to the project documentation, implementation follows these phases:

1. **Basic Setup & Shell Hook** (Completed)
2. **Orchestration & Context** (Completed)
3. **Gemini API Integration** (Completed)
4. **Intelligent Interaction & Contextual Execution** (Completed)
   - Enhanced NLU with tolerance for variations
   - Rich terminal feedback with async streaming
   - Context-aware adaptive confirmation
   - Error analysis and fix suggestions
   - Enhanced file operations

5. **Autonomous Task Orchestration & Proactive Assistance** (In Progress)
   - High-level goal decomposition
   - Multi-step orchestration
   - Conversational context and session memory
   - AI-powered file content comprehension
   - User-defined workflows

6. **Enhanced Project Context** (Planned)
   - Project type inference
   - Dependency detection
   - File reference resolution
   - Activity tracking

7. **Developer Tool Integration** (Planned)
   - Git integration
   - Docker support
   - Advanced code generation
   - Multi-step workflow execution

## Key Technical Features

1. **Progressive Trust System**: Learns which commands are safe and reduces confirmation requirements over time

2. **Adaptive Execution**: Adjusts behavior based on command history and patterns

3. **Rich Error Analysis**: When commands fail, analyzes errors and suggests fixes

4. **Task Planning**: Breaks down complex goals into actionable steps with dependencies

5. **File Content Manipulation**: Can analyze and modify file content based on natural language instructions

6. **Session Memory**: Maintains context between commands for natural conversations

7. **Workflow Definition**: Allows creating and executing multi-step workflows

## Configuration and Customization

The system uses:
- TOML configuration files in `~/.config/angela/`
- Command history and patterns stored for learning
- User preferences for customizing behavior
- Workflow definitions for reusable command sequences

## Safety and Security Considerations

Angela-CLI prioritizes safety with:
- Risk classification for all operations
- Command validation against safety rules
- Adaptive confirmation based on risk level
- Command previews to show expected outcomes
- Rollback capabilities for undoing changes
- Backup creation before destructive operations

This system creates a seamless, intelligent interface to the terminal that feels like "having AGI in your terminal" - understanding your intentions and translating them into effective actions while constantly learning and adapting to your workflow.
--------------------
# STEPS 1-7 COMPLETE
....
