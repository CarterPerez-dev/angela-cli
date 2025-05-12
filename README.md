# Angela CLI

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

## 📚 Table of Contents

- [Overview](#-overview)
- [Philosophy](#-philosophy)
- [Key Features](#-key-features)
- [Installation](#-installation)
- [Initial Configuration](#-initial-configuration)
- [Basic Usage](#-basic-usage)
- [Advanced Usage Examples](#-advanced-usage-examples)
- [Command Categories](#-command-categories)
- [Safety Features](#-safety-features)
- [Architecture & Technical Overview](#-architecture--technical-overview)
- [Shell Integration](#-shell-integration)
- [Project Context Awareness](#-project-context-awareness)
- [AI Integration](#-ai-integration)
- [Error Handling & Recovery](#-error-handling--recovery)
- [Workflows](#-workflows)
- [Code Generation](#-code-generation)
- [Toolchain Integration](#-toolchain-integration)
- [Configuration Options](#-configuration-options)
- [Advanced Customization](#-advanced-customization)
- [Comparison with Similar Tools](#-comparison-with-similar-tools)
- [Performance Considerations](#-performance-considerations)
- [Troubleshooting](#-troubleshooting)
- [FAQs](#-frequently-asked-questions)
- [Roadmap](#-roadmap)
- [Security Considerations](#-security-considerations)
- [Contributing](#-contributing)
- [Development Guide](#-development-guide)
- [License](#-license)
- [Acknowledgements](#-acknowledgements)
- [Contact & Support](#-contact--support)

## 🌟 Overview

Angela CLI represents a paradigm shift in command-line interaction. It's an AI-powered command-line assistant deeply integrated into your terminal shell that blurs the boundary between traditional command-line tools and intelligent assistants. 

Unlike conventional CLI tools that require exact syntax or chatbots that operate in isolation, Angela understands natural language within your development context and can perform complex multi-step operations spanning multiple tools and systems. It functions as a bridge between natural language intent and terminal execution, handling everything from simple file manipulations to complex development workflows involving multiple technologies.

Angela doesn't just execute commands – it acts as an intelligent copilot for your terminal operations, enhancing productivity, reducing errors, and lowering the barrier to entry for complex tasks. It can analyze your project structure, understand your code semantically, and provide contextual assistance that evolves with your workflow.

## 🧠 Philosophy

Angela CLI is built on several core principles:

1. **Ambient Intelligence**: Angela should feel like a natural extension of your shell, not a separate tool you have to invoke. The boundary between standard commands and AI assistance should be minimal.

2. **Contextual Understanding**: True assistance requires understanding the user's environment, project structure, and goals. Angela prioritizes deep context awareness.

3. **Multi-Level Abstraction**: Users should be able to communicate at any level of abstraction, from specific commands to high-level goals, and get appropriate responses.

4. **Progressive Disclosure**: Simple tasks should be simple, while complex capabilities should be available when needed but not overwhelming.

5. **Safety First**: Angela should never execute dangerous operations without appropriate safeguards and user confirmation.

6. **Learning Over Time**: The system should learn from user interactions to improve its suggestions and adaptations over time.

7. **Augmentation, Not Replacement**: Angela aims to enhance the power of the command line, not replace the skills and knowledge of developers.

## ✨ Key Features

### 🔄 Core Capabilities

- **Natural Language Understanding**: Angela interprets human language to extract intent, parameters, and goals. You can ask for "a list of all Python files created in the last week" rather than remembering complex `find` syntax.

- **Project Context Awareness**: Automatically detects project types (Python, Node.js, etc.), dependencies, frameworks in use, and key project files. This context powers intelligent suggestions and accurate command generation.

- **Command Generation & Execution**: Translates natural language to appropriate shell commands with proper flags and arguments, executing them safely after user confirmation when needed.

- **Multi-Step Operation Planning**: Decomposes complex requests like "create a feature branch, implement a login form, and commit the changes" into a coherent sequence of steps with dependencies and error handling.

- **Safety Mechanisms**: Command previews, risk assessment (from SAFE to CRITICAL), impact analysis, permission checking, and comprehensive rollback capabilities to protect against mistakes.

- **Enhanced Shell Integration**: Deeply integrates with Bash, Zsh, and Tmux for a seamless experience, including preexec/precmd hooks, keybindings, status indicators, and auto-completion.

- **Adaptive Learning**: Learns from your command history, project patterns, and explicit feedback to improve suggestions and adapt to your personal workflow style.

### 🛠️ Development Operations

- **File System Operations**: Rich file manipulation capabilities including intelligent search, bulk operations, content analysis, and directory structure creation.

- **Git Integration**: Natural language interface to Git operations like commit, branch, merge, stash, rebase, and blame, with detailed history visualization and conflict resolution assistance.

- **Docker Support**: Manage containers, images, volumes, and networks; generate Dockerfiles and docker-compose configurations; troubleshoot container issues.

- **Package Management**: Detect and use appropriate package managers (pip, npm, yarn, etc.) to add, update, remove, or audit dependencies based on project type.

- **Code Generation**: Create functions, classes, components, boilerplate, or entire projects based on natural language descriptions, with semantic consistency across multiple files.

- **Workflow Automation**: Define, save, edit, and execute complex workflows, with support for parameters, conditions, error handling, and cross-project sharing.

### 🧠 Advanced Features

- **Semantic Code Understanding**: Analyzes your codebase to understand functions, classes, APIs, and their relationships, providing context-aware assistance and refactoring suggestions.

- **Proactive Suggestions**: Monitors command errors, Git state, file changes, and system resources to offer timely advice and automated fixes when appropriate.

- **Cross-Tool Orchestration**: Coordinates complex sequences across multiple development tools (Git, Docker, cloud CLIs, CI/CD) maintaining context and data flow between steps.

- **Automatic Error Recovery**: Intelligently recovers from command failures by analyzing error messages, suggesting fixes, and offering guided or automatic recovery options.

- **Transaction-Based Rollbacks**: Creates an undo history for all operations, enabling complete rollback of multi-step changes, content modifications, and command executions.

- **Interactive Refinement**: Supports iterative improvement of generated code or complex tasks through natural language feedback and visual diffs.

- **Context-Aware Documentation**: Generates README files, API documentation, and usage guides tailored to your specific project and codebase.

## 📥 Installation

Angela CLI offers several installation methods depending on your preferences and requirements.

### Quick Install (Recommended)

The quickest way to get started is with our installation script:

```bash
curl -sSL https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/scripts/install-quick.sh | bash
```

This script will:
1. Check for Python 3.9+ and required system dependencies
2. Download the Angela CLI package
3. Install the package and its dependencies
4. Set up shell integration for your default shell (Bash or Zsh)
5. Create configuration directories
6. Build documentation
7. Prompt you to configure your API key

### Manual Installation

For more control over the installation process:

1. Clone the repository:

```bash
git clone https://github.com/CarterPerez-dev/angela-cli.git
cd angela-cli
```

2. Install the package:

```bash
# In editable mode (recommended for development)
pip install -e .

# Or as a regular package
pip install .
```

3. Set up shell integration:

```bash
# For Bash
echo 'source "$(python -c "import os, angela; print(os.path.join(os.path.dirname(angela.__file__), \"shell/angela.bash\"))")"' >> ~/.bashrc
source ~/.bashrc

# For Zsh
echo 'source "$(python -c "import os, angela; print(os.path.join(os.path.dirname(angela.__file__), \"shell/angela.zsh\"))")"' >> ~/.zshrc
source ~/.zshrc

# For Tmux (optional enhanced integration)
echo 'source "$(python -c "import os, angela; print(os.path.join(os.path.dirname(angela.__file__), \"shell/angela.tmux\"))")"' >> ~/.tmux.conf
tmux source-file ~/.tmux.conf
```

### Installation with Virtualenv

For a more isolated installation:

```bash
# Create a virtual environment
python -m venv ~/angela-env

# Activate it
source ~/angela-env/bin/activate

# Install Angela
pip install angela-cli

# Set up shell integration (pointing to the virtualenv)
echo 'source ~/angela-env/lib/python3.9/site-packages/angela/shell/angela.bash' >> ~/.bashrc
source ~/.bashrc
```

### Docker Installation

For trying Angela CLI without installing:

```bash
docker pull angela-cli/angela:latest
docker run -it --rm -v $(pwd):/workspace angela-cli/angela:latest
```

### System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Linux, macOS, WSL (Windows Subsystem for Linux)
- **Shell**: Bash or Zsh (primary support), Fish (limited support)
- **Terminal**: Any modern terminal emulator with UTF-8 support
- **API Access**: Internet connection for Gemini API access

## ⚙️ Initial Configuration

After installing Angela CLI, you need to set up your initial configuration:

```bash
angela init
```

This interactive setup will guide you through:

1. **API Key Configuration**: You'll be prompted to enter your Google Gemini API key, which you can obtain from [Google AI Studio](https://makersuite.google.com/). This key is stored securely in your configuration directory.

2. **Safety Settings**: Configure confirmation requirements for different risk levels of operations. You can choose to automatically execute low-risk commands while requiring confirmation for higher-risk operations.

3. **Project Defaults**: Optionally set a default project root directory that Angela will use when not explicitly specified.

4. **Shell Integration Options**: Choose between basic and enhanced shell integration, including options for command tracking, auto-completion, and Tmux integration.

The configuration is stored in `~/.config/angela/config.toml` and can be edited manually or updated later using the `angela init` command again.

## 🚀 Basic Usage

Angela CLI is invoked using the `angela` command followed by your natural language request:

```bash
angela "your request in natural language"
```

For example:

```bash
angela "find all JavaScript files modified in the last week"
```

This will:
1. Parse your request to understand your intent
2. Gather context from your current directory and project
3. Generate an appropriate command (e.g., `find . -name "*.js" -mtime -7 -type f`)
4. Show you the command it plans to execute and explain what it will do
5. Execute the command after confirmation (if required)
6. Display the results in a formatted manner

### Global Options

You can use various flags to modify Angela's behavior:

```bash
# Preview what would happen without executing
angela --dry-run "delete all temporary files"

# Get more detailed information
angela --debug "create a feature branch for the user authentication module"

# Force Angela to skip confirmation (only works for lower-risk operations)
angela --force "commit all changes with message 'Update dependencies'"

# Just get a suggestion without execution
angela --suggest-only "find large log files"
```

### Getting Help

For information on Angela's capabilities:

```bash
# General help
angela --help

# See version information
angela --version

# Get help with specific subcommands
angela files --help
angela workflows --help
```

## 📋 Advanced Usage Examples

### Basic Operations

```bash
# Help and information
angela "help"
angela "what can you do?"
angela "show me examples of file operations"

# File operations
angela "create a new directory called 'src' with subdirectories for 'models', 'views', and 'controllers'"
angela "find all Python files modified in the last week containing the word 'authentication'"
angela "show me the content of config.json with syntax highlighting"
angela "create a backup of the config directory with today's date in the filename"

# Shell commands
angela "how much disk space do I have left on each partition?"
angela "find processes using port 3000 and kill them"
angela "check the system load average for the last hour"
angela "monitor the CPU usage of the node server process"
```

### Git Operations

```bash
# Status and changes
angela "what's the status of my repository?"
angela "show me what files I've changed since the last commit"
angela "visualize the commit history of this repository"
angela "who last modified the authentication module and when?"

# Branch management
angela "create a new branch called feature/user-auth and switch to it"
angela "merge develop into main and resolve conflicts interactively"
angela "show me all branches containing fixes for the login issue"
angela "sync my feature branch with the latest changes from main"

# Committing changes
angela "commit all changes with a descriptive message based on what changed"
angela "stash my changes with a note about what I was working on"
angela "create a commit that closes issue #123 on GitHub"
angela "amend my last commit to add the forgotten test files"
```

### Multi-Step Workflows

```bash
# Project initialization
angela "create a new React project with TypeScript, ESLint, Prettier, set up git, add a README, and make an initial commit"

# Feature development
angela "create a feature branch, implement a user profile component in src/components with proper styling, add unit tests for all functionality, and commit the changes"

# Deployment preparation
angela "update the version number in package.json, create a changelog entry for the new version, tag the release, and push to origin"

# Bug investigation
angela "find which commit introduced the memory leak, create a fix branch from that point, apply the necessary changes, and prepare a pull request"
```

### Docker Management

```bash
# Container operations
angela "list all running containers and show their resource usage"
angela "stop the database container, create a backup volume, and restart it"
angela "view the last 50 error logs from the web container with timestamps"
angela "execute a shell inside the API container and install debugging tools"

# Image management
angela "build a docker image from the current directory, tag it as myapp:latest, and optimize for size"
angela "scan the myapp:latest image for security vulnerabilities"
angela "push the recently built image to our private registry with proper tags"
angela "show the layer breakdown of our application image"

# Docker Compose
angela "start all services defined in docker-compose.yml except the monitoring service"
angela "scale the worker service to 3 instances and the web service to 2"
angela "update the database service to use the latest postgres image and apply the change"
```

### Code Generation

```bash
# File generation
angela "create a Python function that validates email addresses with comprehensive regex and handling for international domains"

# Component creation
angela "generate a React component for a user settings form with fields for name, email, password change, and notification preferences"
angela "create a RESTful controller for user management with CRUD operations and proper error handling"

# Project scaffolding
angela "create a new Express API project with MongoDB integration, authentication middleware, rate limiting, and Swagger documentation"
angela "set up a Flask microservice with SQLAlchemy models, Alembic migrations, Pydantic schemas, and FastAPI-style router"
```

## 🧩 Command Categories

Angela CLI supports various command categories, each accessible through natural language or specific subcommands.

### File Operations

Access via `angela files` or natural language:

```bash
# List files
angela files ls --all --long ./docs
angela "show me all files in the docs directory with details"

# Create files/directories
angela files mkdir data/processed --parents
angela "create a folder structure for a Python package with tests"

# Find files
angela files find "*.log" --larger-than 10MB --modified-after "3 days ago"
angela "find large log files created this week"

# Read/Write files
angela files cat config.json --highlight
angela "show me the content of the main configuration file"

# Copy/Move/Delete
angela files cp templates/base.html templates/about.html
angela "create a copy of the homepage template named about.html"

# Bulk operations
angela files rename "*.jsx" "*.tsx" --recursive
angela "convert all JavaScript files to TypeScript in the src directory"
```

### Git Operations

Access via natural language intents:

```bash
# Repository information
angela "show me the git status"
angela "what branch am I on and what's its relation to origin?"

# Branching and switching
angela "create a new branch called feature/payment-integration"
angela "switch to the development branch and pull latest changes"

# Staging and committing
angela "stage the changes to the user authentication module"
angela "commit with a message describing what changed in the payment processor"

# History and logs
angela "show me the commit history for this file"
angela "who made changes to the login functionality and when?"

# Remote operations
angela "push my changes to the remote repository"
angela "set up this local branch to track origin/feature-branch"
```

### Docker Operations

Access via `angela docker` or natural language:

```bash
# Container management
angela docker ps --all --format table
angela "show me all docker containers including stopped ones"

# Image operations
angela docker build . --tag myapp:latest
angela "build a docker image from the current directory"

# Docker Compose
angela docker compose up --detach
angela "start all services in docker-compose in the background"

# Dockerfile generation
angela docker generate-dockerfile --type python-flask
angela "create a Dockerfile for a Flask application optimized for production"
```

### Workflow Management

Access via `angela workflows` or natural language:

```bash
# List workflows
angela workflows list
angela "show me all my defined workflows"

# Create workflow
angela workflows create deploy "Build, test, and deploy the application"
angela "define a new workflow for the release process"

# Run workflow
angela workflows run deploy --var version=1.2.3
angela "execute the deployment workflow for version 1.2.3"

# Export/Import workflow
angela workflows export deploy --output ./workflows/
angela "share my deployment workflow with the team"
```

### Code Generation

Access via `angela generate` or natural language:

```bash
# Create project
angela generate create-project --type react --typescript --output ./web-app
angela "create a new React project with TypeScript support"

# Add feature
angela generate add-feature "user authentication with JWT" --project-dir ./api
angela "implement JWT authentication in my Express API"

# Create component
angela generate component user-profile --framework react
angela "generate a React component for displaying user profiles"

# Generate documentation
angela generate docs --type api --output ./docs/api
angela "create API documentation based on my endpoints"
```

### Shell Operations

Direct shell integration:

```bash
# Interactive shell
angela shell
# Then type natural language commands interactively

# System information
angela "check system resources usage"
angela "monitor network connections on port 80"

# Process management
angela "find and kill zombie processes"
angela "show me the process tree for the node server"
```

## 🛡️ Safety Features

Angela CLI includes comprehensive safety features to prevent accidental or harmful operations.

### Risk Classification

Commands are classified into risk levels:

- **SAFE**: Read-only operations like listing files or viewing content
- **LOW**: Operations with minimal impact like creating empty directories
- **MEDIUM**: Operations that modify files or configuration
- **HIGH**: Operations that could cause data loss or system changes
- **CRITICAL**: Potentially dangerous operations affecting system stability

### Adaptive Confirmation

The confirmation system adapts based on risk level and your history:

```bash
# Low-risk commands might execute directly
angela "list files in the current directory"

# Medium-risk commands show a simple confirmation
angela "create a new configuration file"
# > Confirm: Create file 'config.json'? [y/N]

# High-risk commands show detailed impact analysis
angela "delete all log files older than 30 days"
# > [WARNING] This operation will delete approximately 25 files
# > Affected directories: ./logs, ./archive/logs
# > Confirm this DESTRUCTIVE operation? [y/N]
```

You can configure confirmation requirements in your preferences or use the `--force` flag to skip confirmation for lower-risk operations.

### Command Preview

Before executing commands, Angela shows what will happen:

```bash
angela "rename all .js files to .ts in the src directory"
# > I'll execute: find ./src -name "*.js" -type f | rename 's/\.js$/\.ts/'
# > This will rename approximately 47 JavaScript files to TypeScript
```

Using the `--dry-run` flag provides a complete execution preview without making any changes.

### Transaction-Based Rollback

Angela tracks operations in transactions that can be undone:

```bash
# Execute a multi-step operation
angela "refactor the authentication module by splitting it into smaller files"

# View recent transactions
angela rollback list

# Rollback the entire operation
angela rollback transaction abc123

# Or rollback a specific operation
angela rollback operation def456
```

When modifying files, Angela automatically creates backups that can be restored if needed.

### File Backups

For operations that modify or delete files:

```bash
# Angela automatically creates backups before modifications
angela "update the configuration in settings.py"

# List recent backups
angela "show recent backups"

# Restore from backup
angela "restore the previous version of settings.py"
```

Backups are stored in `~/.config/angela/backups/` with timestamps for easy restoration.

## 🏗️ Architecture & Technical Overview

Angela CLI is built with a modular architecture designed for extensibility and robustness.

### High-Level Architecture

The system is organized into several key subsystems:

1. **Shell Integration**: Hooks into the shell environment to provide a seamless experience
2. **Context Management**: Gathers and maintains information about the user's environment
3. **Intent Processing**: Understands natural language requests and extracts goals
4. **Planning**: Breaks down complex goals into executable steps
5. **Execution**: Safely runs commands and manages their output
6. **AI Integration**: Leverages Gemini AI for natural language understanding and code generation
7. **Toolchain Integration**: Connects with development tools like Git, Docker, etc.

### Core Components

```
├── MD/                          # Documentation files
│   ├── MDHelpers/               # Helper docs
│   │   ├── Files.md             # File explanations
│   │   ├── commands.md          # Commands to run
│   │   └── dependency_map.md    # Dependency map
│   └── assets/                  # Image assets
│       └── angela.webp          # Angela readme.md image asset
├── Makefile                     # Build automation
├── QUICKSTART.md                # Fast setup guide
├── README.md                    # Project overview
├── angela/                      # Main application
│   ├── __init__.py              # Package initializer
│   ├── __main__.py              # Executable entry
│   ├── api/                     # API definitions
│   │   ├── __init__.py          # API package init
│   │   ├── ai.py                # AI module API
│   │   ├── cli.py               # CLI module API
│   │   ├── context.py           # Context module API
│   │   ├── execution.py         # Execution API
│   │   ├── generation.py        # Generation API
│   │   ├── intent.py            # Intent module API
│   │   ├── interfaces.py        # Interfaces API
│   │   ├── monitoring.py        # Monitoring API
│   │   ├── review.py            # Review module API
│   │   ├── safety.py            # Safety module API
│   │   ├── shell.py             # Shell module API
│   │   ├── toolchain.py         # Toolchain API
│   │   └── workflows.py         # Workflows API
│   ├── cli/                     # Main CLI logic
│   │   └── __init__.py          # Main CLI package
│   ├── components/              # Core components
│   │   ├── ai/                  # AI components
│   │   │   ├── __init__.py          # AI package
│   │   │   ├── analyzer.py          # Error analysis
│   │   │   ├── client.py            # Gemini client
│   │   │   ├── confidence.py        # Suggestion confidence
│   │   │   ├── content_analyzer.py  # File content AI
│   │   │   ├── content_analyzer_extensions.py # Content AI extras
│   │   │   ├── enhanced_prompts.py  # Advanced AI prompts
│   │   │   ├── file_integration.py  # AI file ops
│   │   │   ├── intent_analyzer.py   # User intent AI
│   │   │   ├── parser.py            # AI response parsing
│   │   │   ├── prompts.py           # AI prompt templates
│   │   │   └── semantic_analyzer.py # Code semantics AI
│   │   ├── cli/                 # Command-line interface (component)
│   │   │   ├── __init__.py          # CLI package
│   │   │   ├── docker.py            # Docker commands
│   │   │   ├── files.py             # File commands
│   │   │   ├── files_extensions.py  # Advanced file cmds
│   │   │   ├── generation.py        # Code gen commands
│   │   │   ├── main.py              # Main CLI app
│   │   │   └── workflows.py         # Workflow commands
│   │   ├── context/             # Environmental awareness
│   │   │   ├── __init__.py          # Context package
│   │   │   ├── enhanced_file_activity.py # Advanced file track
│   │   │   ├── enhancer.py          # Context enrichment
│   │   │   ├── file_activity.py     # File activity log
│   │   │   ├── file_detector.py     # File type detection
│   │   │   ├── file_resolver.py     # File path resolution
│   │   │   ├── history.py           # Command history
│   │   │   ├── manager.py           # Core context
│   │   │   ├── preferences.py       # User settings
│   │   │   ├── project_inference.py # Project type ID
│   │   │   ├── project_state_analyzer.py # Project state
│   │   │   ├── semantic_context_manager.py # Code context
│   │   │   └── session.py           # User session data
│   │   ├── execution/           # Command execution
│   │   │   ├── __init__.py          # Execution package
│   │   │   ├── adaptive_engine.py   # Smart cmd exec
│   │   │   ├── engine.py            # Command executor
│   │   │   ├── error_recovery.py    # Error handling
│   │   │   ├── filesystem.py        # File operations
│   │   │   ├── hooks.py             # Execution hooks
│   │   │   ├── rollback.py          # Undo operations
│   │   │   └── rollback_commands.py # Rollback CLI
│   │   ├── generation/          # Code generation
│   │   │   ├── __init__.py          # Generation package
│   │   │   ├── architecture.py      # Arch analysis
│   │   │   ├── context_manager.py   # Gen context
│   │   │   ├── documentation.py     # Doc generation
│   │   │   ├── engine.py            # Code gen engine
│   │   │   ├── frameworks.py        # Framework templates
│   │   │   ├── models.py            # Gen data models
│   │   │   ├── planner.py           # Project planning
│   │   │   ├── refiner.py           # Code refinement
│   │   │   └── validators.py        # Code validation
│   │   ├── intent/              # Intent understanding
│   │   │   ├── __init__.py          # Intent package
│   │   │   ├── complex_workflow_planner.py # Complex workflows
│   │   │   ├── enhanced_task_planner.py # Advanced planning
│   │   │   ├── models.py            # Intent data models
│   │   │   ├── planner.py           # Task planning
│   │   │   └── semantic_task_planner.py # Semantic planning
│   │   ├── interfaces/          # Component interfaces
│   │   │   ├── __init__.py          # Interfaces pkg
│   │   │   ├── execution.py         # Exec interfaces
│   │   │   └── safety.py            # Safety interfaces
│   │   ├── monitoring/          # Background monitoring
│   │   │   ├── __init__.py          # Monitoring pkg
│   │   │   ├── background.py        # Background tasks
│   │   │   ├── network_monitor.py   # Network checks
│   │   │   ├── notification_handler.py # Shell notifications
│   │   │   └── proactive_assistant.py # Proactive help
│   │   ├── review/              # Code review & feedback
│   │   │   ├── __init__.py          # Review package
│   │   │   ├── diff_manager.py      # Code diffs
│   │   │   └── feedback.py          # Feedback processing
│   │   ├── safety/              # Safety mechanisms
│   │   │   ├── __init__.py          # Safety package
│   │   │   ├── adaptive_confirmation.py # Smart confirms
│   │   │   ├── classifier.py        # Risk assessment
│   │   │   ├── confirmation.py      # User confirms
│   │   │   ├── preview.py           # Command preview
│   │   │   └── validator.py         # Command validation
│   │   ├── shell/               # Shell integration
│   │   │   ├── __init__.py          # Shell package
│   │   │   ├── advanced_formatter.py # Rich CLI output
│   │   │   ├── angela.bash          # Bash integration
│   │   │   ├── angela.tmux          # Tmux integration
│   │   │   ├── angela.zsh           # Zsh integration
│   │   │   ├── angela_enhanced.bash # Adv Bash hooks
│   │   │   ├── angela_enhanced.zsh  # Adv Zsh hooks
│   │   │   ├── completion.py        # CLI completion
│   │   │   ├── formatter.py         # CLI output format
│   │   │   └── inline_feedback.py   # Terminal feedback
│   │   ├── toolchain/           # Tool integrations
│   │   │   ├── __init__.py          # Toolchain pkg
│   │   │   ├── ci_cd.py             # CI/CD tools
│   │   │   ├── cross_tool_workflow_engine.py # Multi-tool flows
│   │   │   ├── docker.py            # Docker tools
│   │   │   ├── enhanced_universal_cli.py # Adv CLI translation
│   │   │   ├── git.py               # Git tools
│   │   │   ├── package_managers.py  # Pkg manager tools
│   │   │   ├── test_frameworks.py   # Test tool integration
│   │   │   └── universal_cli.py     # CLI translation
│   │   ├── utils/               # Utilities (component)
│   │   │   ├── __init__.py          # Utils package
│   │   │   ├── enhanced_logging.py  # Advanced logging
│   │   │   └── logging.py           # Logging setup
│   │   └── workflows/           # Workflow management (component)
│   │       ├── __init__.py          # Workflows pkg
│   │       ├── manager.py           # Workflow exec
│   │       └── sharing.py           # Workflow sharing
│   ├── config.py                # App configuration
│   ├── constants.py             # Global constants
│   ├── core/                    # Core infrastructure (app level)
│   │   ├── __init__.py          # Core package
│   │   ├── events.py            # Event bus
│   │   └── registry.py          # Service locator
│   ├── orchestrator.py          # Core coordinator
│   └── utils/                   # Utilities (app level)
│       ├── async_utils.py       # Async utilities
│       └── logging.py           # App-level logging
├── docs/                        # Documentation sources
│   ├── Makefile                 # Docs build script
│   ├── make.bat                 # Docs build (Win)
│   └── source/                  # Sphinx source files
│       ├── _static/             # Static doc assets
│       ├── _templates/          # Doc templates
│       │   └── example-template.rst # Docs example template
│       ├── conf.py              # Sphinx config
│       ├── contributing.rst     # Contributing guide
│       ├── examples.rst         # Examples documentation
│       ├── ext/                 # Sphinx extensions
│       │   └── usage_examples.py  # Docs extension
│       ├── index.rst            # Docs main page
│       ├── installation.rst     # Installation guide
│       ├── introduction.rst     # Introduction guide
│       ├── quickstart.rst       # Quickstart guide
│       └── usage.rst            # Usage guide
├── pyproject.toml               # Python packaging
├── pytest.ini                   # Test configuration
├── requirements.txt             # Python dependencies
├── scripts/                     # Utility scripts
│   ├── generate_docs.sh         # Docs generation
│   ├── install-quick.sh         # Quick install
│   ├── install.sh               # Main installer
│   └── uninstall.sh             # Uninstaller
└── tests/                       # Test suite
    ├── __init__.py              # Tests package
    ├── conftest.py              # Pytest fixtures
    ├── test_ai_client.py        # AI client tests
    ├── test_basic.py            # Basic app tests
    ├── test_context.py          # Context module tests
    ├── test_context_enhancer.py # Context enhancer tests
    ├── test_enhanced_planner.py # Planner tests
    ├── test_enhanced_rollback.py # Rollback tests
    ├── test_execution.py        # Execution tests
    ├── test_file_activity.py    # File activity tests
    ├── test_file_detector.py    # File detector tests
    ├── test_file_resolver.py    # File resolver tests
    ├── test_filesystem.py       # Filesystem tests
    ├── test_integration.py      # Core integration tests
    ├── test_integrations.py     # Component integration tests
    ├── test_multi_step.py       # Multi-step tests
    ├── test_orchestration.py    # Orchestration tests
    ├── test_prompt_building.py  # Prompt building tests
    ├── test_response_parsing.py # Response parsing tests
    ├── test_safety.py           # Safety module tests
    └── usage_examples/          # Test usage examples
        ├── advanced_features.py   # Adv features examples
        ├── command_execution.py   # Cmd exec examples
        ├── context_awareness.py   # Context aware examples
        ├── error_recovery.py      # Error recovery examples
        ├── file_operations.py     # File ops examples
        ├── git_operations.py      # Git ops examples
        ├── safety_features.py     # Safety features examples
        ├── testing_debugging.py   # Test/debug examples
        ├── tools_integration.py   # Tool integration examples
        └── workflows.py           # Workflow examples
```

### Key Design Patterns

Angela CLI utilizes several key design patterns:

- **Service Registry**: Core components register themselves with a central registry for dependency injection
- **Event Bus**: For decoupled communication between components
- **Command Pattern**: For encapsulating and executing operations
- **Strategy Pattern**: For supporting different execution strategies based on context
- **Adapter Pattern**: For integrating with various external tools
- **Decorator Pattern**: For enhancing basic operations with safety checks and logging

### Data Flow

When processing a natural language request:

1. The user's input is received via the shell integration
2. The `orchestrator` module determines the request type and dispatches it
3. The `context_manager` provides environmental information
4. For complex requests, the `task_planner` breaks down the goal into steps
5. The `execution_engine` runs commands with appropriate safety checks
6. Results are displayed via the `terminal_formatter`

## 🐚 Shell Integration

Angela CLI integrates deeply with your shell environment to provide a seamless experience.

### Basic Integration

The basic shell integration provides the `angela` command and fundamental context tracking:

```bash
# In .bashrc or .zshrc
source /path/to/angela/shell/angela.bash  # or angela.zsh
```

This gives you access to the core `angela` command and basic completion.

### Enhanced Integration

The enhanced integration provides additional features:

```bash
# In .bashrc or .zshrc
source /path/to/angela/shell/angela_enhanced.bash  # or angela_enhanced.zsh
```

Enhanced features include:

- **Command Tracking**: Angela observes commands you run to build context
- **Error Monitoring**: Angela notices failed commands and can suggest fixes
- **Directory Change Tracking**: Angela updates context when you change directories
- **Contextual Auto-Completion**: Smarter completions based on your project

### Tmux Integration

For Tmux users, Angela provides additional integration:

```bash
# In .tmux.conf
source /path/to/angela/shell/angela.tmux
```

This adds:

- **Status Bar Integration**: Shows Angela's status in your Tmux status bar
- **Key Bindings**: Quick access to Angela features via key combinations
- **Pane Interaction**: Send pane content to Angela for processing

### Custom Keybindings

You can set up custom keybindings for frequent interactions:

```bash
# For Bash
bind '"\C-a": "angela "\C-b'  # Ctrl+A triggers Angela

# For Zsh
bindkey -s '^A' 'angela '     # Ctrl+A triggers Angela
```

### Shell Completion

Angela provides intelligent tab completion:

```bash
# Complete Angela commands
angela <tab>

# Complete workflow names
angela workflows run <tab>

# Context-aware file completion
angela "open the main <tab>
```

Completions are powered by Angela's context understanding and can suggest relevant files, commands, and parameters based on your project.

## 🔍 Project Context Awareness

Angela CLI builds a comprehensive understanding of your project to provide more relevant assistance.

### Project Type Detection

Angela automatically detects various project types:

- **Python**: Based on `requirements.txt`, `setup.py`, `pyproject.toml`, etc.
- **Node.js**: Based on `package.json`, `node_modules/`, etc.
- **Ruby**: Based on `Gemfile`, `.ruby-version`, etc.
- **Java/Kotlin**: Based on `pom.xml`, `build.gradle`, etc.
- **Go**: Based on `go.mod`, `go.sum`, etc.
- **Rust**: Based on `Cargo.toml`, etc.
- **And many more**: C#, PHP, Swift, Dart, etc.

### Framework Recognition

Within each language, Angela detects frameworks:

- **Python**: Django, Flask, FastAPI, Pytest, etc.
- **JavaScript**: React, Vue, Angular, Express, Next.js, etc.
- **Java**: Spring, Hibernate, JUnit, etc.

### Dependency Analysis

Angela analyzes your project dependencies:

```bash
angela "what dependencies am I using?"
# > Your project uses:
# > - express (^4.17.1): Web framework for Node.js
# > - mongoose (^5.12.3): MongoDB object modeling
# > - jsonwebtoken (^8.5.1): JWT implementation
# > ...
```

### File Awareness

Angela tracks files you interact with and understands their purpose:

```bash
angela "what files have I been working on today?"
# > Recent files:
# > - src/controllers/auth.js (modified 10 minutes ago)
# > - src/models/user.js (viewed 25 minutes ago)
# > - src/middleware/auth.js (created 1 hour ago)
```

### Project Structure Understanding

Angela can navigate and reason about your project structure:

```bash
angela "where are my API routes defined?"
# > Based on your Express.js project structure, API routes are defined in:
# > - src/routes/auth.js: Authentication routes
# > - src/routes/users.js: User management routes
# > - src/routes/index.js: Main router configuration
```

### Git Integration

Angela understands your Git repository state:

```bash
angela "what's the status of my repository?"
# > Current branch: feature/user-auth (ahead of origin/feature/user-auth by 2 commits)
# > Modified files:
# > - src/controllers/user.js
# > - src/models/user.js
# > Untracked files:
# > - src/middleware/validation.js
```

## 🧠 AI Integration

Angela CLI uses advanced AI capabilities to understand and assist with your tasks.

### Model Details

Angela uses the Google Gemini model:
- **Primary Model**: Gemini 2.5-pro-exp-03-25
- **Fallback Model**: Gemini 1.5-pro

The models are accessed via the Google Generative AI API with fine-tuned prompts specific to command-line assistance.

### Prompt Engineering

Angela uses sophisticated prompt engineering to:
1. Include relevant context about your project and recent activities
2. Structure requests to get consistently formatted responses
3. Provide examples of good command generation
4. Guide the model to consider safety implications
5. Request structured output for multi-step plans

### Response Parsing

Responses from the AI are parsed into structured formats:
- **Command Suggestions**: Contains the command, explanation, and risk assessment
- **Multi-Step Plans**: Contains individual steps with dependencies and rollback plans
- **Content Analysis**: Structured understanding of file content
- **Code Generation**: Well-structured and consistent code across multiple files

### Offline Capabilities

While Angela's AI features require internet access, many core functions work offline:
- **File operations** work without AI when using the explicit `angela files` subcommand
- **History-based suggestions** can be provided without new AI queries
- **Workflow execution** works offline once workflows are defined
- **Rollback operations** are fully functional without internet access

## 🔄 Error Handling & Recovery

Angela CLI provides sophisticated error handling and recovery mechanisms.

### Error Analysis

When a command fails, Angela analyzes the error:

```bash
angela "run the backend tests"
# > Command failed: npm run test:backend
# > Error: Cannot find module 'jest'
# > 
# > Analysis: This error indicates Jest is not installed in this project.
# > Suggested fixes:
# > 1. Install Jest: npm install --save-dev jest
# > 2. Check if package.json includes the test:backend script
```

### Automatic Recovery

In some cases, Angela can automatically recover from errors:

```bash
angela "add a new React component"
# > Error: Directory 'src/components' does not exist
# > 
# > I'll create the missing directory and try again.
# > 
# > Creating directory: src/components
# > Successfully created component: src/components/NewComponent.jsx
```

### Guided Recovery

For more complex issues, Angela guides you through recovery:

```bash
angela "deploy to production"
# > Command failed: git push heroku main
# > Error: Updates were rejected because the remote contains work that you do not have locally
# > 
# > Recommended actions:
# > 1. Pull latest changes: git pull heroku main
# > 2. Resolve any conflicts
# > 3. Push again: git push heroku main
# > 
# > Would you like me to execute these recovery steps? [Y/n]
```

### Error Learning

Angela learns from errors to improve future suggestions:

- Records frequently encountered errors and successful fixes
- Adapts suggestions to avoid known problematic patterns
- Builds up a database of project-specific error patterns

## 🔄 Workflows

Angela CLI allows you to define, save, and execute complex workflows.

### Creating Workflows

Workflows can be created interactively or from natural language descriptions:

```bash
# Interactive creation
angela workflows create deploy

# From description
angela "define a workflow called publish that builds the docs, commits changes, and pushes to GitHub"
```

### Workflow Structure

Workflows consist of:
- **Name**: A unique identifier for the workflow
- **Description**: A human-readable explanation
- **Steps**: Ordered commands to execute
- **Variables**: Parameterized values that can be provided at runtime
- **Conditions**: Optional logic to control execution flow
- **Error Handling**: Steps to take if something fails

### Executing Workflows

Run workflows with optional parameters:

```bash
# Basic execution
angela workflows run deploy

# With variables
angela workflows run deploy --var environment=staging --var version=1.2.3

# Via natural language
angela "run the deployment workflow for the staging environment with version 1.2.3"
```

### Managing Workflows

Workflows can be listed, edited, exported, and imported:

```bash
# List all workflows
angela workflows list

# Show workflow details
angela workflows show deploy

# Edit workflow
angela workflows edit deploy

# Export workflow for sharing
angela workflows export deploy --output ./workflows/

# Import shared workflow
angela workflows import ./workflows/deploy.angela-workflow
```

### Example Workflow

```yaml
name: deploy
description: Build, test, and deploy the application
variables:
  - name: environment
    description: Target environment (staging or production)
    default: staging
  - name: version
    description: Version to deploy
    required: true
steps:
  - command: git checkout main
    explanation: Switch to the main branch
    requires_confirmation: false
  - command: git pull
    explanation: Get latest changes
    requires_confirmation: false
  - command: npm test
    explanation: Run all tests
    requires_confirmation: false
    on_error: prompt
  - command: npm version ${version}
    explanation: Update version number
    requires_confirmation: true
  - command: npm run build
    explanation: Build the application
    requires_confirmation: false
  - command: git push origin main
    explanation: Push version change to GitHub
    requires_confirmation: false
  - command: npm run deploy:${environment}
    explanation: Deploy to ${environment}
    requires_confirmation: true
```

## 💻 Code Generation

Angela CLI includes powerful code generation capabilities.

### Single-File Generation

Generate individual code files based on natural language descriptions:

```bash
angela "create a JavaScript function to calculate the Fibonacci sequence recursively"
angela "generate a React component for a user settings form with all fields"
angela "create a Python class for a REST API client with proper error handling"
```

### Multi-File Generation

Generate complex, interconnected code spanning multiple files:

```bash
angela "create a Node.js authentication module with routes, controllers, models, and middleware"
```

This will generate a complete set of files with consistent imports, exports, and dependencies.

### Project Scaffolding

Create entire project structures with appropriate configurations:

```bash
angela "create a new React project with TypeScript, ESLint, Jest, and React Router"
angela "scaffold a Flask API with SQLAlchemy, migrations, JWT authentication, and Swagger docs"
```

### Framework-Specific Generation

Templates and patterns tailored to popular frameworks:

```bash
angela generate create-project --framework next.js
angela "create a Django app for a blog with comments and user profiles"
```

### Code Refinement

Iteratively improve generated code through natural language feedback:

```bash
angela "refine the auth module to use refresh tokens and improve security"
```

### Code Analysis and Documentation

Generate documentation and analyze existing code:

```bash
angela "generate API documentation for my Express routes"
angela "analyze the architecture of this project and suggest improvements"
```

## 🛠️ Toolchain Integration

Angela CLI integrates with various development tools to provide a seamless experience.

### Git Integration

Comprehensive Git support with intuitive commands:

```bash
angela "show me what files have changed since the last commit"
angela "create a feature branch for user authentication"
angela "commit all changes with a detailed message"
angela "resolve merge conflicts in the auth controller"
```

Advanced Git features:
- Interactive staging of partial changes
- Visualizing complex branch structures
- Automating Git Flow operations
- Smart commit message generation

### Docker Integration

Docker and Docker Compose support:

```bash
angela "list all running containers and their port mappings"
angela "build a production-ready Docker image for this Node.js app"
angela "generate a Docker Compose setup for a MERN stack"
angela "debug why my container keeps crashing"
```

Features include:
- Dockerfile generation based on project type
- Container health monitoring
- Volume and network management
- Multi-stage build optimization

### Package Management

Automatic detection and use of the appropriate package manager:

```bash
angela "add lodash and axios to this project"
angela "update all dependencies to their latest versions"
angela "audit packages for security vulnerabilities"
```

Supports:
- npm, yarn, pnpm (JavaScript)
- pip, poetry, pipenv (Python)
- gem (Ruby)
- composer (PHP)
- cargo (Rust)
- maven, gradle (Java)

### CI/CD Integration

Generate and manage CI/CD configurations:

```bash
angela "set up GitHub Actions for this project"
angela "create a GitLab CI pipeline for testing and deployment"
angela "generate a Jenkins pipeline for this Java application"
```

Features:
- Template generation for popular CI systems
- Environment variable management
- Test and build optimization
- Deployment automation

### Cloud CLI Integration

Interface with cloud provider CLIs:

```bash
angela "list my AWS S3 buckets"
angela "deploy this application to Google App Engine"
angela "create an Azure resource group in the East US region"
```

Supports:
- AWS CLI
- GCloud CLI
- Azure CLI
- Heroku CLI
- Digital Ocean CLI

### Database Tools

Database management and migration tools:

```bash
angela "create a new migration for the users table"
angela "run database migrations"
angela "generate a database schema diagram"
```

## ⚙️ Configuration Options

Angela CLI offers extensive configuration options to customize its behavior.

### Configuration File

The main configuration file is located at `~/.config/angela/config.toml`:

```toml
[api]
gemini_api_key = "your-api-key-here"

[user]
default_project_root = "/path/to/projects"
confirm_all_actions = false

[safety]
auto_execute_safe_commands = true
auto_execute_low_risk_commands = true
require_confirmation_for_medium_risk = true
require_confirmation_for_high_risk = true
require_warning_for_critical_risk = true

[trust]
trusted_commands = [
    "git status",
    "git pull",
    "ls -la"
]
untrusted_commands = [
    "git push --force",
    "rm -rf"
]

[ui]
show_command_preview = true
colorize_output = true
verbose_explanations = true

[context]
max_history_items = 100
activity_tracking_enabled = true
scan_project_on_startup = true
```

### Environment Variables

You can also configure Angela using environment variables:

```bash
# API Keys
export GEMINI_API_KEY="your-api-key-here"

# Feature flags
export ANGELA_DEBUG=1
export ANGELA_CONFIRM_ALL=1

# Paths
export ANGELA_CONFIG_DIR="/custom/config/path"
export ANGELA_PROJECT_ROOT="/default/project/path"
```

### Command-Line Configuration

Some settings can be configured via command-line flags:

```bash
# Enable debug mode
angela --debug "your request"

# Force confirmation for all actions
angela --confirm-all "your request"

# Skip confirmation (for trusted operations)
angela --force "your request"
```

### Per-Project Configuration

Project-specific settings can be defined in `.angela.toml` in your project root:

```toml
[project]
type = "python"
test_command = "pytest"
lint_command = "flake8"

[preferences]
package_manager = "poetry"
style_guide = "pep8"

[context]
ignored_directories = ["venv", ".cache"]
main_file = "app.py"
```

## 🔧 Advanced Customization

For power users, Angela CLI offers several advanced customization options.

### Custom Workflows

Create complex workflows with branching logic and error handling:

```yaml
name: complex-deploy
description: Advanced deployment workflow with error handling
variables:
  - name: environment
    description: Target environment
    default: staging
  - name: version
    description: Version to deploy
    required: true
steps:
  - id: tests
    command: npm test
    explanation: Run all tests
    on_error:
      - command: npm run lint -- --fix
        explanation: Try to auto-fix linting issues
      - command: npm test
        explanation: Run tests again after fixes

  - id: version_update
    command: npm version ${version}
    explanation: Update version number
    depends_on: [tests]

  - id: build
    command: npm run build
    explanation: Build the application
    depends_on: [version_update]

  - id: backup
    command: tar -czf backup-${version}.tar.gz dist/
    explanation: Create backup of build artifacts
    depends_on: [build]

  - id: deploy
    command: npm run deploy:${environment}
    explanation: Deploy to ${environment}
    depends_on: [backup]
    on_error:
      - command: npm run deploy:${environment} -- --force
        explanation: Try force deployment
        requires_confirmation: true
      - command: npm run rollback:${environment} -- --to-last-stable
        explanation: Roll back to last stable version
        requires_confirmation: true
```

### Prompt Customization

Customize the AI prompts used by Angela for specific tasks:

```bash
# Create custom prompt templates
mkdir -p ~/.config/angela/prompts/
nano ~/.config/angela/prompts/code_generation.txt

# Use custom prompts
angela --prompt-template code_generation "generate a React component"
```

### Plugin System

Extend Angela with custom plugins:

```python
# ~/.config/angela/plugins/my_plugin.py

from angela.core.registry import registry

class MyCustomTool:
    def __init__(self):
        self.name = "my_tool"
    
    async def execute(self, command, context):
        # Custom implementation
        return {"result": "Success!"}

# Register the plugin
my_tool = MyCustomTool()
registry.register("my_tool", my_tool)
```

Then use it:

```bash
angela "use my custom tool to do something"
```

### Shell Function Customization

Customize the shell integration with your own hooks:

```bash
# In your .bashrc or .zshrc
angela_custom_hook() {
    # Custom pre-command hook
    # This runs before Angela processes a command
    command="$1"
    # Custom logic here
}

# Register the hook
export ANGELA_PRE_COMMAND_HOOK=angela_custom_hook
```

### Output Formatting

Customize how Angela formats its output:

```bash
# Create custom formatter configuration
cat > ~/.config/angela/formatters.toml << EOF
[command]
color = "blue"
prefix = "→ "

[output]
max_height = 20
syntax_highlight = true

[error]
color = "red"
prefix = "✖ "
EOF
```

## 🔄 Comparison with Similar Tools

Here's how Angela CLI compares to other command-line assistants:

| Feature | Angela CLI | GitHub Copilot CLI | OpenAI's ChatGPT | Traditional CLI tools |
|---------|------------|-------------------|-----------------|----------------------|
| **Natural Language Support** | ✅ Comprehensive | ✅ Good | ✅ Basic | ❌ None |
| **Project Context Awareness** | ✅ Deep understanding | ✅ Basic | ❌ Limited | ❌ None |
| **Multi-Step Operations** | ✅ Advanced planning | ✅ Basic | ❌ Limited | ❌ Scripting only |
| **Tool Integration** | ✅ Git, Docker, Cloud | ✅ Limited | ❌ None | ✅ Via plugins |
| **Shell Integration** | ✅ Deep (Bash, Zsh, Tmux) | ✅ Basic | ❌ None | ✅ Native |
| **Safety Features** | ✅ Advanced (risk, rollback) | ✅ Basic | ❌ None | ❌ Manual |
| **Code Generation** | ✅ Multi-file, project-aware | ✅ Single-file focus | ✅ Basic | ❌ None |
| **Offline Capability** | ✅ Partial | ❌ Requires internet | ❌ Requires internet | ✅ Complete |
| **Learning From History** | ✅ Adaptive suggestions | ✅ Basic | ❌ No persistence | ❌ None |
| **Open Source** | ✅ Yes | ❌ No | ❌ No | ✅ Mostly |
| **Cost** | ✅ API usage only | ❌ Subscription | ❌ Subscription | ✅ Free |

### Why Choose Angela CLI?

- **More Contextual**: Understands your project structure and history better than alternatives
- **More Integrated**: Works seamlessly with your shell and developer tools
- **More Safe**: Comprehensive safety features to prevent mistakes
- **More Customizable**: Extensive configuration and extension options
- **More Autonomous**: Can handle complex multi-step tasks with minimal intervention

## ⚡ Performance Considerations

Optimizing Angela CLI for performance:

### Network Optimization

- **API Caching**: Angela caches similar requests to reduce API calls
- **Offline Mode**: Core features work without internet access
- **Compression**: Request/response compression to minimize bandwidth

### Memory Management

- **Contextual Pruning**: Only relevant context is included in prompts
- **History Trimming**: Old command history is automatically pruned
- **Resource Monitoring**: Angela monitors its own resource usage

### Configuration Tips

For faster operation:

```bash
# Reduce context gathering for simpler operations
angela --light-context "simple file operations"

# Pre-cache project information
angela precache

# Disable intensive features for quicker response
angela --no-project-scan "quick request"
```

### Large Project Handling

For very large projects:

```bash
# Define a project scope to limit analysis
angela project set-scope "src/"

# Use Git-based context limiting
angela project use-git-scope
```

## 🛠️ Troubleshooting

Solutions to common issues with Angela CLI:

### Installation Issues

**Problem**: Package installation fails with dependency errors.

**Solution**:
```bash
# Create a clean virtual environment
python -m venv angela-env
source angela-env/bin/activate

# Install with verbose output
pip install -e . -v
```

**Problem**: Shell integration doesn't work after installation.

**Solution**:
```bash
# Check if the shell script exists
ls -la $(python -c "import os, angela; print(os.path.join(os.path.dirname(angela.__file__), 'shell'))")

# Manually source the script
source $(python -c "import os, angela; print(os.path.join(os.path.dirname(angela.__file__), 'shell/angela.bash'))")
```

### API Connection Issues

**Problem**: Cannot connect to the Gemini API.

**Solution**:
```bash
# Verify your API key
angela config show api.gemini_api_key

# Manually set the API key
angela config set api.gemini_api_key "your-key-here"

# Check network connectivity
curl https://generativelanguage.googleapis.com/healthz
```

### Command Execution Problems

**Problem**: Angela refuses to execute a command.

**Solution**:
```bash
# Run with debug output
angela --debug "your request"

# Try with forcing execution (only for trusted commands)
angela --force "your request"

# Check if the command is in the untrusted list
angela config show trust.untrusted_commands
```

**Problem**: Angela misunderstands your request.

**Solution**:
```bash
# Be more specific
angela "specifically, I want to..."

# Use the --clarify flag to enable interactive clarification
angela --clarify "ambiguous request"

# Provide more context
angela "in the context of user authentication, create a..."
```

### Performance Issues

**Problem**: Angela is slow to respond.

**Solution**:
```bash
# Reduce context gathering
angela --light-context "your request"

# Check for large project issues
angela diagnosis report

# Disable heavy features temporarily
angela --no-project-scan "your request"
```

## ❓ Frequently Asked Questions

### General Questions

**Q: How is Angela different from just using ChatGPT or another AI assistant?**

A: Angela is deeply integrated with your terminal environment, understands your project context, and can safely execute commands. Unlike general AI assistants, Angela is specifically designed for command-line productivity with safety features, rollback capabilities, and developer tool integrations.

**Q: Does Angela require internet access?**

A: For AI-powered features like natural language understanding and code generation, internet access is required to connect to the Gemini API. However, many core features like file operations, workflow execution, and rollback functionality work offline.

**Q: Can Angela access or modify files outside my current directory?**

A: By default, Angela operates within your current directory and project scope. It can access other directories if explicitly requested, but it performs safety checks and requires confirmation for operations outside the current context.

### Technical Questions

**Q: How does Angela determine my project type?**

A: Angela looks for key indicator files (like `package.json`, `requirements.txt`, etc.), directory structures, and file patterns to infer the project type. It uses a scoring system to handle mixed-type projects and can detect frameworks within each language ecosystem.

**Q: Can Angela be used in scripts or CI/CD pipelines?**

A: Yes, Angela can be used in non-interactive contexts with the `--non-interactive` flag. You can define workflows for common operations and execute them programmatically:

```bash
angela workflows run deploy --var version=1.2.3 --non-interactive
```

**Q: How secure is Angela? Does it send my code to external servers?**

A: Angela sends context information and snippets of your code to the Gemini API as needed to process your requests. It minimizes the data sent by focusing only on relevant files and truncating large content. Your API key and sensitive configuration are stored locally and never transmitted. All API communications are encrypted using HTTPS.

### Usage Questions

**Q: Can I use Angela with languages other than English?**

A: Currently, Angela's primary language is English, but it can understand and generate commands for systems in any language. Future versions will include broader natural language support.

**Q: How do I contribute to Angela CLI?**

A: See our [Contributing Guide](CONTRIBUTING.md) for details on how to contribute code, documentation, or bug reports.

**Q: Can I use Angela on Windows?**

A: Angela is primarily designed for Unix-like systems (Linux, macOS). It can be used on Windows through WSL (Windows Subsystem for Linux). Native Windows support is on our roadmap.

## 🛣️ Roadmap

Our development roadmap for upcoming features:

### Short-term (Next 3 Months)

- **Enhanced Docker Integration**: Deeper Docker Compose support and container debugging
- **Improved Code Generation**: Better multi-file consistency and framework awareness
- **Language Server Protocol**: Integration with LSP for better code understanding
- **Advanced Git Operations**: Visual branch management and interactive conflict resolution
- **Performance Optimizations**: Faster response times and reduced API usage

### Medium-term (3-6 Months)

- **Windows Native Support**: Full Windows shell integration without WSL
- **Additional Shell Support**: Fish shell and PowerShell integration
- **Expanded Cloud CLI Support**: More cloud providers and services
- **Team Collaboration**: Sharing workflows and configurations with team members
- **IDE Integration Plugins**: VS Code and JetBrains IDE plugins

### Long-term (6-12 Months)

- **Local AI Models**: Option to use local LLMs for enhanced privacy and offline use
- **Learning Customization**: Fine-tuning of AI with your specific patterns and preferences
- **Advanced Project Insights**: Codebase health metrics and refactoring recommendations
- **Cross-Machine Synchronization**: Sync configuration and history across devices
- **Enterprise Features**: Role-based access control and compliance features

### Experimental Areas

- **Voice Interaction**: Voice commands and responses for hands-free operation
- **Multi-modal Context**: Understanding screenshots and diagrams as part of context
- **AR Terminal Integration**: Augmented reality visualizations for complex operations

## 🔒 Security Considerations

### Data Privacy

- **Local Configuration**: All configuration is stored locally on your machine
- **API Keys**: Your API keys are stored securely in config files with appropriate permissions
- **Code Transmission**: Only relevant snippets are sent to the API, not your entire codebase
- **History Storage**: Command history is stored locally and never transmitted to external servers

### Command Safety

- **Risk Assessment**: All commands are classified by risk level before execution
- **Permission Checking**: Angela verifies file and directory permissions before operations
- **Dangerous Command Detection**: Known dangerous patterns are identified and blocked
- **Confirmation System**: High-risk operations require explicit user confirmation

### Authentication

- **API Authentication**: API requests use your personal API key for authentication
- **No Remote Authentication**: Angela has no remote authentication system of its own
- **No Account Required**: Angela works without creating accounts on external services

### Best Practices

- **Use Latest Version**: Always use the latest version of Angela to get security updates
- **Review Commands**: Always review commands before allowing execution
- **Limit Project Scope**: Use project scoping features to limit access to sensitive directories
- **Regular Backups**: Although Angela creates automatic backups, maintain your own backup system

## 🤝 Contributing

We welcome contributions to Angela CLI! See our detailed [Contributing Guide](CONTRIBUTING.md) for more information.

### Getting Started

1. Fork the repository
2. Clone your fork
3. Set up the development environment:

```bash
# Clone your fork
git clone https://github.com/your-username/angela-cli.git
cd angela-cli

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests to verify setup
pytest
```

### Development Process

1. Create a branch for your feature:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes with appropriate tests and documentation
3. Ensure all tests pass:

```bash
pytest
```

4. Format your code:

```bash
black angela tests
isort angela tests
```

5. Check for type errors:

```bash
mypy angela
```

6. Submit a pull request

### Code Structure

For new components, follow the existing patterns:
- Place core logic in appropriate modules under `angela/`
- Add corresponding test files in `tests/`
- Document public APIs with docstrings
- Update the README and documentation as necessary

## 🔧 Development Guide

### Project Setup

```bash
# Clone the repository
git clone https://github.com/CarterPerez-dev/angela-cli.git
cd angela-cli

# Install in development mode
make dev-setup

# Run tests
make test
```

### Setting Up API Keys for Development

```bash
# Create .env file
cp .env.example .env

# Edit .env with your Gemini API key
echo "GEMINI_API_KEY=your-key-here" >> .env
```

### Running the Test Suite

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_orchestrator.py

# Run with coverage
pytest --cov=angela
```

### Build and Distribution

```bash
# Create a source distribution
python -m build --sdist

# Create a wheel
python -m build --wheel

# Local installation in development mode
pip install -e .
```

### Debugging Tips

- Use the `--debug` flag for verbose logging
- Check logs in `~/.config/angela/logs/` for detailed information
- Set `ANGELA_DEBUG=1` environment variable for development builds

## 📜 License

Angela CLI is released under the MIT License. See the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Angela CLI Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 👏 Acknowledgements

Angela CLI is built on the shoulders of giants:

- **Google Gemini API**: Powers the natural language understanding and generation
- **Typer and Click**: The foundation of our command-line interface
- **Rich**: Creates beautiful terminal output and visualizations
- **Pydantic**: Handles data validation and settings management
- **AsyncIO**: Enables non-blocking operations and concurrency
- **Python-dotenv**: Manages environment variables and configuration
- **Open Source Community**: For the countless libraries and tools we depend on

Special thanks to all our contributors and early adopters who have helped shape this project.

## 📞 Contact & Support

- **GitHub Issues**: [Submit bugs and feature requests](https://github.com/CarterPerez-dev/angela-cli/issues)
- **Documentation**: [Official documentation site](https://docs.angela-cli.dev)
- **Community Discussion**: [Join our Discord server](https://discord.gg/angela-cli)
- **Twitter**: [@AngelaCLI](https://twitter.com/AngelaCLI)
- **Email**: support@angela-cli.dev

For security issues, please email security@angela-cli.dev instead of using the public issue tracker.

---

<div align="center">
  <p>Built with ❤️ by the Angela CLI Team</p>
  <p>
    <a href="https://docs.angela-cli.dev">Documentation</a> •
    <a href="https://github.com/CarterPerez-dev/angela-cli/issues">Report Bug</a> •
    <a href="https://github.com/CarterPerez-dev/angela-cli/issues">Request Feature</a> •
    <a href="https://discord.gg/angela-cli">Community</a>
  </p>
</div>
