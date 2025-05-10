# Angela CLI Quick Start Guide

Angela CLI is an AI-powered command-line assistant that integrates with your terminal shell to understand natural language requests and execute appropriate commands. It helps developers streamline workflows, reduce time spent on repetitive tasks, and lower the barrier to complex operations.

## Installation

### Quick Installation (Recommended)
Install Angela CLI with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/scripts/install-quick.sh | bash
```

This script will:
- Check for Python 3.9+ and required dependencies
- Download and install the Angela CLI package
- Set up shell integration for Bash or Zsh
- Create necessary configuration directories

### Manual Installation

For more control over the installation process:

```bash
# Clone the repository
git clone https://github.com/CarterPerez-dev/angela-cli.git
cd angela-cli

# Install the package
pip install -e .

# Set up shell integration manually
echo 'source "$(python -c "import os, angela; print(os.path.join(os.path.dirname(angela.__file__), \"shell/angela.bash\"))")"' >> ~/.bashrc
source ~/.bashrc
```

### System Requirements
- Python 3.9 or higher
- Bash or Zsh shell
- Internet connection for AI capabilities

## Setup

1. **Initialize Angela** and set up your API key:

   ```bash
   angela init
   ```

   This interactive setup will:
   - Prompt for your Gemini API key (obtain one at [makersuite.google.com](https://makersuite.google.com/))
   - Configure safety preferences
   - Optionally set default project directories
   - Test the API connection
   
   Your API key is stored securely in `~/.config/angela/config.toml`.

2. **Verify Installation** with a simple command:

   ```bash
   angela "hello world"
   ```

   Angela should respond with a greeting and information about its capabilities.

3. **Try a practical command**:

   ```bash
   angela "list all files in this directory"
   ```

   Angela will translate this into the appropriate command (`ls -la`), explain what it does, and execute it.

## Command Structure

Angela commands follow this basic pattern:

```bash
angela [options] "your natural language request"
```

Common options include:
- `--dry-run`: Preview commands without executing them
- `--debug`: Show detailed debug information
- `--suggest-only`: Get command suggestions without execution
- `--force`: Skip confirmation for low-risk operations

## Common Use Cases

### File Operations

```bash
# Create files with content
angela "create a new file called app.py with a basic Flask app"
# Angela will generate a Flask application template and write it to app.py

# Find files by various criteria
angela "find all Python files containing the word 'import'"
# Angela will use a combination of find and grep to locate matching files

# Find files modified recently
angela "show me JavaScript files modified in the last 3 days"
# Angela will generate and execute the appropriate find command

# Edit file content
angela "add a logging setup to main.py"
# Angela will parse main.py, add appropriate logging code, and save the changes

# Create directory structures
angela "create a folder structure for a React project with components, pages, and styles"
# Angela will create the appropriate nested directory structure
```

### Git Commands

```bash
# Git status and changes
angela "show me what files I've changed"
# Angela will run git status and present the results in a readable format

# Create branches
angela "create a new branch called feature/user-auth and switch to it"
# Angela will run git checkout -b feature/user-auth

# Commit changes
angela "commit all my changes with a good commit message"
# Angela will analyze your changes and generate a descriptive commit message

# View history
angela "show me the commit history for this file"
# Angela will run git log with appropriate formatting for the specified file

# Resolve conflicts
angela "help me resolve merge conflicts in user.js"
# Angela will guide you through the conflict resolution process
```

### Project Management

```bash
# Initialize a new project
angela "create a new React project in the directory frontend"
# Angela will scaffold a complete React application in the frontend directory

# Add dependencies
angela "add express and mongodb as dependencies"
# Angela will use the appropriate package manager (npm, yarn, etc.) based on your project

# Run tests
angela "run all tests in the test directory"
# Angela will identify and run the appropriate test command for your project

# Check code quality
angela "lint the src directory and fix common issues"
# Angela will run the appropriate linter with auto-fix options

# Build and package
angela "build the project for production"
# Angela will identify and run the appropriate build command
```

### Docker Operations

```bash
# List containers
angela "show me all running docker containers"
# Angela will run docker ps with appropriate formatting

# Build images
angela "build a docker image from the current directory and tag it as myapp:latest"
# Angela will create the docker build command with proper tagging

# Manage containers
angela "restart the database container"
# Angela will identify and restart the specified container

# Docker Compose
angela "start all services defined in docker-compose.yml"
# Angela will run docker-compose up with appropriate options
```

### Creating Workflows

Define reusable sequences of commands that can be executed with a single instruction:

```bash
# Define a new workflow
angela workflows create deploy "build docker image and push to registry"
# Angela will guide you through defining the steps interactively

# List existing workflows
angela workflows list
# Shows all defined workflows

# View workflow details
angela workflows show deploy
# Shows the steps in the deploy workflow

# Run a workflow
angela workflows run deploy
# Executes all steps in the deploy workflow sequentially

# Run with parameters
angela workflows run deploy --var version=1.2.3
# Runs the workflow with variable substitution
```

## Advanced Features

### Multi-Step Operations

Angela can handle complex requests involving multiple steps:

```bash
angela "create a feature branch, implement a login component, add tests, and commit the changes"
```

Angela will break this down into individual steps, show you the plan, and execute each step after confirmation.

### Safety Features

Angela includes safety mechanisms to prevent accidental data loss:

```bash
# Preview commands without execution
angela --dry-run "delete all log files older than 7 days"

# Operations with potential risk require confirmation
angela "remove the build directory and all its contents"
# Angela will warn about the destructive operation and ask for confirmation
```

### Operation Rollback

Angela tracks operations that modify files and provides rollback capabilities:

```bash
# View recent operations
angela rollback list

# Undo specific operation
angela rollback operation abc123

# Undo last operation
angela rollback last
```

## Troubleshooting

### Common Issues

**API Key Problems**:
```bash
# Reset your API key
angela init
```

**Shell Integration Issues**:
```bash
# Manually source the shell script
source ~/.config/angela/shell/angela.bash
```

**Command Execution Failures**:
```bash
# Run with debug information
angela --debug "your command"
```

### Getting Help

Access Angela's help system:

```bash
# General help
angela --help

# Specific command help
angela workflows --help

# Get usage examples
angela "show me examples of git commands"
```

## Learning More

- **Documentation**: Visit [docs.angela-cli.dev](https://docs.angela-cli.dev) for comprehensive guides
- **GitHub Repository**: [github.com/your-repo/angela-cli](https://github.com/your-repo/angela-cli) for source code and issues
- **Interactive Tutorial**: Run `angela tutorial` for an interactive learning experience
- **Command Reference**: Run `angela commands` to see a list of all available command categories

## Architecture Overview

Angela CLI is built with a modular architecture:

- **Shell Integration**: Interfaces with your terminal
- **Context Management**: Understands your project and environment
- **Intent Analysis**: Interprets your natural language requests
- **Command Generation**: Creates appropriate shell commands
- **Execution Engine**: Safely runs commands with proper feedback
- **Safety System**: Prevents accidental data loss
- **Tool Integrations**: Connects with Git, Docker, package managers, etc.

```
Each component is designed to work together, supporting a robust development and user experience for Angela CLI.
```
