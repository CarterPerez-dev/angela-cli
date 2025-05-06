"""
Enhanced prompt engineering for Angela CLI.

This file contains enhanced prompt templates that incorporate rich project context,
dependency information, recent file activities, and resolved file references.
"""

# Enhanced project context prompt section
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

# Recent file activity prompt section
RECENT_FILES_CONTEXT = """
## Recent File Activity
Recently Accessed Files:
{recent_files}

Most Active Files:
{active_files}
"""

# Resolved file references prompt section
RESOLVED_FILES_CONTEXT = """
## Resolved File References
The following file references were resolved from your request:
{resolved_files}
"""

# Enhanced build_prompt function
def build_prompt(
    request: str, 
    context: Dict[str, Any],
    similar_command: Optional[str] = None,
    intent_result: Optional[Dict[str, Any]] = None
) -> str:
    """Build a prompt for the Gemini API with enhanced context information."""
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

# Enhanced prompt template for file operations
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

# Enhanced prompt for file operation
def build_file_operation_prompt(
    operation: str, 
    parameters: Dict[str, Any], 
    context: Dict[str, Any]
) -> str:
    """
    Build an enhanced prompt for generating a file operation command.
    
    Args:
        operation: The type of file operation.
        parameters: Parameters for the operation.
        context: Context information about the current environment.
        
    Returns:
        A prompt string for the Gemini API.
    """
    # Create file information
    file_path = parameters.get("path", "Unknown")
    file_info = context_manager.get_file_info(Path(file_path)) if file_path != "Unknown" else {}
    
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
