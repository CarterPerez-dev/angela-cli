# tests/usage_examples/command_execution.py

def test_basic_command():
    """EXAMPLE: Execute a simple command
    DESCRIPTION: Use Angela to run a basic shell command and see the output.
    COMMAND: list all files in the current directory
    RESULT:
    Executing command: ls -la
    total 40
    drwxr-xr-x  5 user  staff   160 May  9 10:15 .
    drwxr-xr-x  3 user  staff    96 May  9 10:12 ..
    -rw-r--r--  1 user  staff  1240 May  9 10:15 README.md
    -rw-r--r--  1 user  staff   432 May  9 10:15 setup.py
    drwxr-xr-x  8 user  staff   256 May  9 10:15 angela
    """
    pass

def test_command_with_argument():
    """EXAMPLE: Pass arguments to a command
    DESCRIPTION: Execute a command with specific arguments or parameters.
    COMMAND: show disk usage for the current directory
    RESULT:
    Executing command: du -sh .
    4.2M    .
    """
    pass

def test_pipe_command():
    """EXAMPLE: Piped commands
    DESCRIPTION: Execute a command that uses pipes to filter output.
    COMMAND: find all Python files and count them
    RESULT:
    Executing command: find . -name "*.py" | wc -l
    42
    """
    pass

def test_sudo_command():
    """EXAMPLE: Command requiring elevated privileges
    DESCRIPTION: Angela warns before executing commands that require system privileges.
    COMMAND: update system packages
    RESULT:
    ⚠️  This command requires elevated privileges: apt update
    
    This command has HIGH risk and could make significant changes to your system.
    Do you want to proceed? [y/N]: 
    """
    pass
