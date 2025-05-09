# Angela CLI Setup and Usage Guide

## Question 1: Dependency Management and Import Errors

The import errors you're seeing (`Unable to import 'pydantic'`, etc.) are occurring because you haven't installed the package dependencies. The good news is that all the required dependencies are correctly defined in both `pyproject.toml` and `requirements.txt`.

**Solution:**
Run one of these commands from the project root:

```bash
# Option 1: Use make
make dev-setup

# Option 2: Use pip directly 
pip install -e ".[dev]"
```

This installs Angela CLI in development mode with all dependencies. The `-e` flag ensures changes to the code are reflected without reinstalling.

## Question 2: User Flow - From Fresh Installation to Using Angela

Here's the complete flow for a user starting with a fresh Linux environment:

1. **Prerequisites Installation**:
   ```bash
   # Install Python if not already present
   sudo apt update
   sudo apt install python3 python3-pip git

   # Ensure Python 3.9+ is available
   python3 --version
   ```

2. **Angela Installation**:
   ```bash
   # Clone the repository
   git clone https://github.com/your-repo/angela-cli.git
   cd angela-cli

   # Run the installation script
   bash scripts/install.sh
   
   # Restart shell or source config file
   source ~/.bashrc  # or ~/.zshrc
   ```

3. **Initialization**:
   ```bash
   # Initialize Angela, providing the Gemini API key when prompted
   angela init
   ```

4. **Usage Examples**:
   ```bash
   # Ask Angela to help with a command
   angela "show me all files modified in the last week"
   
   # Get help with Git operations
   angela "create a new branch called feature/user-auth and switch to it"
   
   # File operations
   angela "find all Python files containing the word 'error'"
   
   # Multi-step operations
   angela "create a virtual environment, install Flask, and create a basic app.py file"
   
   # Docker operations
   angela "setup Docker for this Python project"
   
   # Define workflows
   angela "define a workflow called deploy that builds Docker image and pushes to registry"
   
   # Execute workflows
   angela "run deploy workflow"
   ```

Inside the terminal, they would see rich output with colored syntax highlighting, progress indicators, explanations, and interactive confirmations for risky operations.

## Question 3: Development Testing Flow

Here's the development testing flow:

1. **Initial Setup**:
   ```bash
   # Clone the repository
   git clone https://github.com/your-repo/angela-cli.git
   cd angela-cli
   
   # Setup development environment
   make dev-setup
   # OR
   pip install -e ".[dev]"
   ```

2. **Create Environment File**:
   ```bash
   # Copy example .env file
   cp .env.example .env
   
   # Edit to add your Gemini API key
   nano .env
   ```

3. **Initialize for Testing**:
   ```bash
   # Run initialization
   python -m angela init
   ```

4. **Run Tests**:
   ```bash
   # Run test suite
   make test
   
   # OR run specific tests
   pytest tests/test_specific_file.py
   ```

5. **Manual Testing**:
   ```bash
   # Test a command directly
   python -m angela request "list all files in current directory"
   
   # Test shell integration
   angela "create a sample Python file"
   ```

6. **Code Quality**:
   ```bash
   # Run linting
   make lint
   
   # Format code
   make format
   ```

7. **Cleanup**:
   ```bash
   # Clean up build artifacts
   make clean
   ```
