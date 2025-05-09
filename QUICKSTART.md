# Angela CLI Quick Start Guide

## Installation

Install Angela CLI with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/CarterPerez-dev/angela-cli/main/scripts/install-quick.sh | bash
```

## Setup

1. **Initialize Angela** and set up your API key:

   ```bash
   angela init
   ```

   When prompted, enter your Gemini API key. You can get one at [makersuite.google.com](https://makersuite.google.com/).

2. **Try a simple command**:

   ```bash
   angela "list all files in this directory"
   ```

## Common Use Cases

### File Operations

```bash
# Create files
angela "create a new file called app.py with a basic Flask app"

# Find files
angela "find all Python files containing the word 'import'"

# Edit files
angela "add a logging setup to main.py"
```

### Git Commands

```bash
# Git status and changes
angela "show me what files I've changed"

# Create branches
angela "create a new branch called feature/user-auth and switch to it"

# Commit changes
angela "commit all my changes with a good commit message"
```

### Project Management

```bash
# Initialize a new project
angela "create a new React project in the directory frontend"

# Add dependencies
angela "add express and mongodb as dependencies"

# Run tests
angela "run all tests in the test directory"
```

### Creating Workflows

```bash
# Define reusable workflows
angela workflows create deploy "build docker image and push to registry"

# Run workflows
angela workflows run deploy
```

## Learning More

For detailed documentation, visit [docs.angela-cli.dev](https://docs.angela-cli.dev).

For troubleshooting and support, see our GitHub repository at [github.com/your-repo/angela-cli](https://github.com/your-repo/angela-cli).
```

Each component is designed to work together, supporting a robust development and user experience for Angela CLI.
