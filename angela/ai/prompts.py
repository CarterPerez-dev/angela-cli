# angela/ai/prompts.py
"""
Prompt engineering for Angela CLI.

This module provides a comprehensive collection of prompts and templates for the Gemini API
with enhanced context information about the current environment, project structure, file activities,
and resolved references. All prompt building functionality is centralized in this file.

The module offers various specialized prompt templates for different use cases, including:
- Command generation with rich context awareness
- File operation prompts with project-specific knowledge
- Multi-step operation planning
- Error analysis and recovery suggestions
- Code generation and manipulation prompts
"""
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import logging

from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Base system instructions
SYSTEM_INSTRUCTIONS = """
You are Angela, an AI-powered command-line assistant integrated into the user's terminal shell.
Your goal is to help users by interpreting their natural language requests and translating them into appropriate shell commands or file operations.

Follow these guidelines:
1. Prioritize standard Linux shell commands that work across different distributions.
2. Focus on practical and efficient solutions that work in a terminal environment.
3. Be clear and direct about what suggested commands will do.
4. For file operations, prefer using built-in commands like mkdir, touch, rm, etc.
5. Format your responses in a structured JSON format for consistent parsing.
6. Consider the user's context, history, and project environment in your suggestions.
7. Offer informative explanations that help users learn terminal skills over time.
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

# Enhanced project context template
ENHANCED_PROJECT_CONTEXT = """
## Enhanced Project Information
Project Type: {project_type}
Frameworks: {frameworks}
Main Dependencies: {dependencies}
Important Files: {important_files}
Project Structure:
- Main Directories: {main_directories}
- Total Files: {total_files}
"""

# Error analysis prompts - for generating error explanations and fixes
ERROR_ANALYSIS_PROMPT = """
Analyze the following command error and provide helpful debugging information:

Command: {command}
Error Output:
{error_output}

Consider:
1. Common syntax errors or misused flags
2. Missing dependencies or prerequisites
3. Permission issues or path problems
4. Similar commands that might work instead
5. Step-by-step debugging approach

Provide a concise explanation of the error and actionable suggestions to fix it.
"""

# Multi-step operation prompt - for complex tasks requiring multiple commands
MULTI_STEP_OPERATION_PROMPT = """
Your task is to create a sequence of commands to accomplish this goal:
{goal}

Project context:
{project_context}

Consider creating a plan that:
1. Breaks down the task into clear sequential steps
2. Handles potential errors or edge cases
3. Uses variables or temporary files when needed
4. Incorporates proper checks between steps
5. Follows best practices for the user's environment

Return a JSON object with an array of command objects, each having:
- command: the shell command to execute
- purpose: brief explanation of this step
- dependencies: list of previous step indices this depends on
- estimated_risk: number from 0-4 indicating risk level
"""

# Code generation prompt - for creating code files or snippets
CODE_GENERATION_PROMPT = """
Create code for the following purpose:
{purpose}

Language: {language}
Project Type: {project_type}
File Path: {file_path}

Requirements:
{requirements}

Include:
- Appropriate imports and dependencies
- Clear documentation and comments
- Error handling and input validation
- Best practices for {language}
- Consistency with the project's coding style

The code should be production-ready, following modern standards and design patterns.
"""

# Workflow automation prompt - for creating sequences of reusable operations
WORKFLOW_AUTOMATION_PROMPT = """
Create a reusable workflow for this scenario:
{scenario}

User's environment:
{environment}

The workflow should:
1. Be parameterizable with variables like ${FILE} or ${DIR}
2. Include appropriate error handling
3. Be efficient and avoid unnecessary steps
4. Follow best practices for shell scripting
5. Include clear documentation for each step

Format the workflow as a sequence of commands with explanations.
"""

# Recent file activity template 
RECENT_FILES_CONTEXT = """
## Recent File Activity
Recently Accessed Files:
{recent_files}

Most Active Files:
{active_files}
"""

# Resolved file references template
RESOLVED_FILES_CONTEXT = """
## Resolved File References
The following file references were resolved from your request:
{resolved_files}
"""

# Enhanced file operation prompt template
FILE_OPERATION_PROMPT_TEMPLATE = """
You are asked to perform an operation on a file with enhanced context awareness.

## File Information
Path: {file_path}
Type: {file_type}
Language: {language}
Size: {size}

## Project Context
Project Type: {project_type}
Project Root: {project_root}

## Request
{request}

Consider all this context when generating your response. If the file is part of a project,
consider how this operation might affect the project as a whole.
"""

# Advanced debugging prompt - for complex system troubleshooting
ADVANCED_DEBUGGING_PROMPT = """
Help debug this complex system issue:
{issue_description}

System Information:
- OS: {os_info}
- Environment: {environment}
- Related Components: {components}

Error logs:
{error_logs}

Recent system changes:
{recent_changes}

Provide a comprehensive debugging approach including:
1. Root cause analysis with multiple potential explanations
2. Diagnostic commands to gather more information
3. Potential solutions ranked by likelihood of success
4. Prevention strategies for future occurrences
5. Explanation of the underlying system mechanisms
"""

# Data transformation prompt - for processing and converting data
DATA_TRANSFORMATION_PROMPT = """
Transform the data according to these requirements:
{requirements}

Source data format: {source_format}
Target data format: {target_format}

Sample data:
{sample_data}

Generate a command or script that will:
1. Handle the full data set efficiently
2. Validate input and provide error handling
3. Produce the output in exactly the specified format
4. Preserve data integrity and type safety
5. Include appropriate logging or progress indication
"""

# Security audit prompt - for analyzing security implications
SECURITY_AUDIT_PROMPT = """
Perform a security audit of this command or script:
{command_or_script}

Context:
{context}

In your audit, consider:
1. Potential injection vulnerabilities or escape issues
2. Permissions and privilege escalation risks
3. Data exposure or leakage concerns
4. Resource exhaustion possibilities
5. Best practice recommendations for secure usage

Provide a security risk assessment and suggested improvements.
"""

def build_prompt(
    request: str, 
    context: Dict[str, Any],
    similar_command: Optional[str] = None,
    intent_result: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a prompt for the Gemini API with enhanced context information.
    
    Args:
        request: The user request
        context: Context information about the current environment
        similar_command: Optional similar command from history
        intent_result: Optional intent analysis result
        
    Returns:
        A prompt string for the AI service
    """
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
    
    # Add enhanced project information if available
    if context.get("enhanced_project"):
        project_info = context["enhanced_project"]
        
        # Format frameworks information
        frameworks_str = "None detected"
        if project_info.get("frameworks"):
            framework_names = list(project_info["frameworks"].keys())
            frameworks_str = ", ".join(framework_names[:5])
            if len(framework_names) > 5:
                frameworks_str += f" and {len(framework_names) - 5} more"
        
        # Format dependencies information
        dependencies_str = "None detected"
        if project_info.get("dependencies") and project_info["dependencies"].get("top_dependencies"):
            dependencies_str = ", ".join(project_info["dependencies"]["top_dependencies"][:5])
            if len(project_info["dependencies"]["top_dependencies"]) > 5:
                dependencies_str += f" and {len(project_info['dependencies']['top_dependencies']) - 5} more"
            
            # Add counts information
            if project_info["dependencies"].get("counts"):
                dependencies_str += f" (Total: {project_info['dependencies'].get('total', 0)})"
        
        # Format important files information
        important_files_str = "None detected"
        if project_info.get("important_files") and project_info["important_files"].get("paths"):
            important_files_str = ", ".join(project_info["important_files"]["paths"][:5])
            if len(project_info["important_files"]["paths"]) > 5:
                important_files_str += f" and {len(project_info['important_files']['paths']) - 5} more"
        
        # Format main directories information
        main_directories_str = "None detected"
        if project_info.get("structure") and project_info["structure"].get("main_directories"):
            main_directories_str = ", ".join(project_info["structure"]["main_directories"])
        
        # Format total files information
        total_files_str = "Unknown"
        if project_info.get("structure") and "total_files" in project_info["structure"]:
            total_files_str = str(project_info["structure"]["total_files"])
        
        # Add to context string
        context_str += ENHANCED_PROJECT_CONTEXT.format(
            project_type=project_info.get("type", "Unknown"),
            frameworks=frameworks_str,
            dependencies=dependencies_str,
            important_files=important_files_str,
            main_directories=main_directories_str,
            total_files=total_files_str
        )
    
    # Add recent file activity if available
    if context.get("recent_files"):
        recent_files = context["recent_files"]
        
        # Format recent files information
        recent_files_str = "None"
        if recent_files.get("accessed"):
            # Extract filenames only for brevity
            recent_filenames = [Path(path).name for path in recent_files["accessed"][:5]]
            recent_files_str = ", ".join(recent_filenames)
            if len(recent_files["accessed"]) > 5:
                recent_files_str += f" and {len(recent_files['accessed']) - 5} more"
        
        # Format active files information
        active_files_str = "None"
        if recent_files.get("activities"):
            active_files_str = ", ".join([a.get("name", "unknown") for a in recent_files["activities"][:3]])
            if len(recent_files["activities"]) > 3:
                active_files_str += f" and {len(recent_files['activities']) - 3} more"
        
        # Add to context string
        context_str += RECENT_FILES_CONTEXT.format(
            recent_files=recent_files_str,
            active_files=active_files_str
        )
    
    # Add resolved file references if available
    if context.get("resolved_files"):
        resolved_files = context["resolved_files"]
        
        # Format resolved files information
        resolved_files_str = ""
        for ref_info in resolved_files:
            reference = ref_info.get("reference", "")
            path = ref_info.get("path", "Not found")
            resolved_files_str += f"- '{reference}' → {path}\n"
        
        # Add to context string
        if resolved_files_str:
            context_str += RESOLVED_FILES_CONTEXT.format(
                resolved_files=resolved_files_str
            )
    
    # Add conversation context
    if "session" in context:
        session = context["session"]
        
        # Add recent commands for continuity
        if session.get("recent_commands"):
            context_str += "Recent commands:\n"
            for i, cmd in enumerate(session.get("recent_commands", []), 1):
                context_str += f"- Command {i}: {cmd}\n"
        
        # Add recent results for reference
        if session.get("recent_results"):
            context_str += "Recent command results:\n"
            for i, result in enumerate(session.get("recent_results", []), 1):
                # Truncate long results
                if len(result) > 200:
                    result = result[:200] + "..."
                context_str += f"- Result {i}: {result}\n"
        
        # Add entities for reference resolution
        if session.get("entities"):
            context_str += "Referenced entities:\n"
            for name, entity in session.get("entities", {}).items():
                context_str += f"- {name}: {entity.get('type')} - {entity.get('value')}\n"
    
    # Add intent analysis if available
    if intent_result:
        context_str += "\nIntent analysis:\n"
        context_str += f"- Intent type: {intent_result.get('intent_type', 'unknown')}\n"
        context_str += f"- Confidence: {intent_result.get('confidence', 0.0):.2f}\n"
        
        # Add extracted entities
        if intent_result.get("entities"):
            context_str += "- Extracted entities:\n"
            for key, value in intent_result.get("entities", {}).items():
                context_str += f"  - {key}: {value}\n"
    
    # Add similar command suggestion if available
    if similar_command:
        context_str += f"\nYou previously suggested this similar command: {similar_command}\n"
    
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
    
    # Define the expected response format - now with confidence indicator
    response_format = """
Expected response format (valid JSON):
{
    "intent": "the_classified_intent",
    "command": "the_suggested_command",
    "explanation": "explanation of what the command does",
    "confidence": 0.85, /* Optional confidence score from 0.0 to 1.0 */
    "additional_info": "any additional information (optional)"
}
"""
    
    # Build the complete prompt
    prompt = f"{SYSTEM_INSTRUCTIONS}\n\n{context_str}\n\n{examples_str}\n\n{response_format}\n\nUser request: {request}\n\nResponse:"
    
    logger.debug(f"Built prompt with length: {len(prompt)}")
    return prompt


# Terminal customization prompt - for personalized environment setup
TERMINAL_CUSTOMIZATION_PROMPT = """
Create a customization plan for the user's terminal environment:

Current setup:
{current_setup}

User preferences:
{preferences}

Usage patterns:
{usage_patterns}

The customization should include:
1. Shell configuration recommendations (.bashrc, .zshrc, etc.)
2. Prompt styling and information display
3. Aliases and functions for common operations
4. Productivity tools and utilities
5. Performance optimization settings

Provide detailed implementation instructions with code snippets.
"""

# System administration prompt - for advanced system tasks
SYSTEM_ADMINISTRATION_PROMPT = """
Provide a solution for this system administration task:
{task_description}

System details:
{system_details}

Requirements:
{requirements}

The solution should:
1. Be robust and handle edge cases
2. Include appropriate logging and monitoring
3. Consider security implications
4. Be efficient and scalable
5. Follow system administration best practices

Provide detailed implementation steps with commands and configuration.
"""

# Project analysis prompt - for codebase understanding
PROJECT_ANALYSIS_PROMPT = """
Analyze this software project:
{project_summary}

Key files:
{key_files}

Key questions:
{questions}

Provide an in-depth analysis covering:
1. Architecture and design patterns
2. Component relationships and dependencies
3. Potential technical debt or improvement areas
4. Performance and scalability considerations
5. Security posture and risk assessment

The analysis should be actionable and prioritized by impact.
"""

def build_file_operation_prompt(
    operation: str, 
    parameters: Dict[str, Any], 
    context: Dict[str, Any]
) -> str:
    """
    Build a prompt for generating a file operation command.
    
    Args:
        operation: The type of file operation (e.g., 'create_file', 'delete_directory').
        parameters: Parameters for the operation.
        context: Context information about the current environment.
        
    Returns:
        A prompt string for the Gemini API.
    """
    # Create file information
    file_path = parameters.get("path", "Unknown")
    
    # Get file info if available
    file_info = {}
    if file_path != "Unknown":
        try:
            from angela.context.manager import context_manager
            file_info = context_manager.get_file_info(Path(file_path))
        except Exception as e:
            logger.debug(f"Error getting file info: {str(e)}")
    
    file_info_str = f"""
File: {file_path}
Type: {file_info.get('type', 'Unknown')}
Language: {file_info.get('language', 'Unknown')}
"""
    
    # Create a description of the requested operation
    operation_str = f"""
Requested file operation: {operation}
Parameters:
"""
    for key, value in parameters.items():
        operation_str += f"- {key}: {value}\n"
    
    # Create enhanced project context
    project_context_str = "Project Context:\n"
    
    if context.get("enhanced_project"):
        project_info = context["enhanced_project"]
        project_context_str += f"- Project Type: {project_info.get('type', 'Unknown')}\n"
        
        # Add frameworks if available
        if project_info.get("frameworks"):
            frameworks = list(project_info["frameworks"].keys())
            project_context_str += f"- Frameworks: {', '.join(frameworks[:3])}"
            if len(frameworks) > 3:
                project_context_str += f" and {len(frameworks) - 3} more"
            project_context_str += "\n"
        
        # Add file's relationship to project
        if file_path != "Unknown" and context.get("project_root"):
            try:
                rel_path = Path(file_path).relative_to(Path(context["project_root"]))
                project_context_str += f"- Relative Path: {rel_path}\n"
            except ValueError:
                # File is not within project root
                project_context_str += f"- Note: File is outside project root\n"
    
    # Define the task
    task_str = f"""
Your task is to generate a shell command that will perform the requested file operation.
The command should be safe, efficient, and follow best practices for Linux/Unix shell environments.
Consider the file type, language, and project context when generating the command.
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
    prompt = f"{SYSTEM_INSTRUCTIONS}\n\n{operation_str}\n\n{file_info_str}\n\n{project_context_str}\n\n{task_str}\n\n{response_format}\n\nResponse:"
    
    logger.debug(f"Built file operation prompt with length: {len(prompt)}")
    return prompt
