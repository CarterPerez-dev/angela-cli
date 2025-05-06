"""
Prompt engineering for Angela CLI.

This module provides functions to build prompts for the Gemini API
with context information about the current environment.
"""
from typing import Dict, Any

from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Base system instructions
SYSTEM_INSTRUCTIONS = """
You are Angela, an AI-powered command-line assistant integrated into the user's terminal shell.
Your goal is to help users by interpreting their natural language requests and translating them into appropriate shell commands or file operations.

Follow these guidelines:
1. Only suggest commands that are safe and appropriate.
2. Prioritize standard Linux shell commands.
3. Focus on practical solutions that work in a terminal environment.
4. You can now suggest commands that modify the system, but be explicit about what they will do.
5. For file operations, prefer using built-in commands like mkdir, touch, rm, etc.
6. Format your responses in a structured JSON format.
7. When suggesting destructive operations, include a warning in your explanation.
"""

# Examples for few-shot learning
EXAMPLES = [
    {
        "request": "Find all Python files in this project",
        "context": {"project_root": "/home/user/project", "project_type": "python"},
        "response": {
            "intent": "search_files",
            "command": "find . -name '*.py'",
            "explanation": "This command searches for files with the .py extension in the current directory and all subdirectories."
        }
    },
    {
        "request": "Show me disk usage for the current directory",
        "context": {"cwd": "/home/user/project"},
        "response": {
            "intent": "disk_usage",
            "command": "du -sh .",
            "explanation": "This command shows the disk usage (-s) in a human-readable format (-h) for the current directory."
        }
    },
    {
        "request": "Create a directory called 'test' and a file inside it",
        "context": {"cwd": "/home/user/project"},
        "response": {
            "intent": "file_creation",
            "command": "mkdir -p test && touch test/example.txt",
            "explanation": "This command creates a directory named 'test' and an empty file named 'example.txt' inside it. The -p flag ensures parent directories are created if needed."
        }
    },
    {
        "request": "Delete all temporary files in the current directory",
        "context": {"cwd": "/home/user/project"},
        "response": {
            "intent": "file_deletion",
            "command": "find . -name '*.tmp' -type f -delete",
            "explanation": "This command finds and deletes all files with the .tmp extension in the current directory and its subdirectories. Be careful as this will permanently delete matching files."
        }
    },
    {
        "request": "Move all JavaScript files to the src directory",
        "context": {"cwd": "/home/user/project", "project_type": "node"},
        "response": {
            "intent": "file_movement",
            "command": "mkdir -p src && find . -maxdepth 1 -name '*.js' -type f -exec mv {} src/ \\;",
            "explanation": "This command creates the src directory if it doesn't exist, then finds all JavaScript files in the current directory and moves them to the src directory."
        }
    }
]

# Additional examples for file operations
FILE_OPERATION_EXAMPLES = [
    {
        "request": "Edit a file and change all instances of 'old' to 'new'",
        "context": {"cwd": "/home/user/project"},
        "response": {
            "intent": "file_edit",
            "command": "sed -i 's/old/new/g' filename.txt",
            "explanation": "This command uses sed to replace all occurrences of 'old' with 'new' in the file. The -i flag makes the changes in-place."
        }
    },
    {
        "request": "Display the first 10 lines of a log file",
        "context": {"cwd": "/home/user/project"},
        "response": {
            "intent": "file_view",
            "command": "head -n 10 logfile.log",
            "explanation": "This command displays the first 10 lines of the specified log file."
        }
    },
    {
        "request": "Create a backup of my configuration file",
        "context": {"cwd": "/home/user"},
        "response": {
            "intent": "file_backup",
            "command": "cp ~/.config/app/config.yaml ~/.config/app/config.yaml.bak",
            "explanation": "This command creates a backup copy of the configuration file by appending .bak to the filename."
        }
    }
]

def build_prompt(request: str, context: Dict[str, Any]) -> str:
    """Build a prompt for the Gemini API with context information."""
    # Create a context description
    context_str = "Current context:\n"
    if context.get("cwd"):
        context_str += f"- Current working directory: {context['cwd']}\n"
    if context.get("project_root"):
        context_str += f"- Project root: {context['project_root']}\n"
    if context.get("project_type"):
        context_str += f"- Project type: {context['project_type']}\n"
    if context.get("relative_path"):
        context_str += f"- Path relative to project root: {context['relative_path']}\n"
    
    # Add information about the current file if available
    if context.get("current_file"):
        file_info = context["current_file"]
        context_str += f"- Current file: {file_info.get('path')}\n"
        if file_info.get("language"):
            context_str += f"- File language: {file_info.get('language')}\n"
        if file_info.get("type"):
            context_str += f"- File type: {file_info.get('type')}\n"
    
    # Add examples for few-shot learning
    examples_str = "Examples:\n"
    
    # Add standard examples
    for example in EXAMPLES:
        examples_str += f"\nUser request: {example['request']}\n"
        examples_str += f"Context: {example['context']}\n"
        examples_str += f"Response: {example['response']}\n"
    
    # Add file operation examples
    for example in FILE_OPERATION_EXAMPLES:
        examples_str += f"\nUser request: {example['request']}\n"
        examples_str += f"Context: {example['context']}\n"
        examples_str += f"Response: {example['response']}\n"
    
    # Define the expected response format
    response_format = """
Expected response format (valid JSON):
{
    "intent": "the_classified_intent",
    "command": "the_suggested_command",
    "explanation": "explanation of what the command does",
    "additional_info": "any additional information (optional)"
}
"""
    
    # Build the complete prompt
    prompt = f"{SYSTEM_INSTRUCTIONS}\n\n{context_str}\n\n{examples_str}\n\n{response_format}\n\nUser request: {request}\n\nResponse:"
    
    logger.debug(f"Built prompt with length: {len(prompt)}")
    return prompt


def build_file_operation_prompt(operation: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
    """
    Build a prompt for generating a file operation command.
    
    Args:
        operation: The type of file operation (e.g., 'create_file', 'delete_directory').
        parameters: Parameters for the operation.
        context: Context information about the current environment.
        
    Returns:
        A prompt string for the Gemini API.
    """
    # Create a description of the requested operation
    operation_str = f"Requested file operation: {operation}\n"
    operation_str += "Parameters:\n"
    for key, value in parameters.items():
        operation_str += f"- {key}: {value}\n"
    
    # Create a context description
    context_str = "Current context:\n"
    if context.get("cwd"):
        context_str += f"- Current working directory: {context['cwd']}\n"
    if context.get("project_root"):
        context_str += f"- Project root: {context['project_root']}\n"
    if context.get("project_type"):
        context_str += f"- Project type: {context['project_type']}\n"
    
    # Define the task
    task_str = f"""
Your task is to generate a shell command that will perform the requested file operation.
The command should be safe, efficient, and follow best practices for Linux/Unix shell environments.
"""
    
    # Define the expected response format
    response_format = """
Expected response format (valid JSON):
{
    "command": "the_shell_command",
    "explanation": "explanation of what the command does",
    "risk_level": "SAFE|LOW|MEDIUM|HIGH|CRITICAL",
    "destructive": true|false
}
"""
    
    # Build the complete prompt
    prompt = f"{SYSTEM_INSTRUCTIONS}\n\n{operation_str}\n\n{context_str}\n\n{task_str}\n\n{response_format}\n\nResponse:"
    
    logger.debug(f"Built file operation prompt with length: {len(prompt)}")
    return prompt
