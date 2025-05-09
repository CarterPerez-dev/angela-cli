# angela/ai/enhanced_prompts.py
"""
Enhanced prompt engineering for Angela CLI with semantic awareness.

This module extends Angela's prompting capabilities with semantic code understanding,
detailed project state, and nuanced user history for significantly more informed responses.
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union

from angela.utils.logging import get_logger
from angela.context.file_detector import detect_file_type
from angela.ai.prompts import (
    build_prompt, SYSTEM_INSTRUCTIONS, EXAMPLES, FILE_OPERATION_EXAMPLES,
    ENHANCED_PROJECT_CONTEXT, ERROR_ANALYSIS_PROMPT, MULTI_STEP_OPERATION_PROMPT,
    CODE_GENERATION_PROMPT, RECENT_FILES_CONTEXT, RESOLVED_FILES_CONTEXT,
    FILE_OPERATION_PROMPT_TEMPLATE
)
from angela.context.project_state_analyzer import project_state_analyzer
from angela.ai.semantic_analyzer import semantic_analyzer

logger = get_logger(__name__)

# Enhanced system instructions that highlight semantic understanding
ENHANCED_SYSTEM_INSTRUCTIONS = """
You are Angela, an AI-powered command-line assistant with deep semantic code understanding. 
You are integrated into the user's terminal shell and possess detailed awareness of the code structure, 
project state, and development history.

Your capabilities include:
1. Understanding code at a semantic level - functions, classes, dependencies, and architectural patterns
2. Being aware of the project's state including Git status, pending migrations, and build health
3. Tracking specific code entities (functions, classes, methods) across files
4. Interpreting user intentions in the context of their recent activity
5. Providing intelligent suggestions based on comprehensive project understanding
6. Translating high-level goals into precise, context-appropriate actions

You prioritize:
1. Precision in commands and file operations based on semantic understanding
2. Context-awareness that leverages project structure, state, and dependencies
3. Intelligent code modifications with an understanding of potential impacts
4. Helpful explanations that leverage code entity relationships
5. Proactive suggestions informed by project state (test failures, code quality issues, etc.)
"""

# Semantic code context template
SEMANTIC_CODE_CONTEXT = """
## Semantic Code Understanding
{entity_type}: {entity_name}
Location: {filename}:{line_start}-{line_end}
Summary: {summary}

Related Entities:
{related_entities}

Dependencies:
{dependencies}
"""

# Project state context template
PROJECT_STATE_CONTEXT = """
## Project State
Git Status: {git_status}
Branch: {branch} {remote_state}
Changes: {has_changes} {change_details}

Build Status: {build_status}
Tests: {test_status}
Dependencies: {dependencies_status}

Issues:
{issues_summary}
"""

# Enhanced task planning prompt template
SEMANTIC_TASK_PLANNING_PROMPT = """
I'm going to help you plan a complex task with deep awareness of the project's semantic structure and state.

Project Code Context:
{semantic_code_context}

Project State:
{project_state_context}

Recent Activity:
{recent_activity}

For this request:
"{request}"

Let me break this down into well-structured, semantically-aware steps that account for:
1. Dependencies between code components
2. Potential impacts of changes
3. Current project state considerations
4. Error handling for each step
5. Verification steps after critical operations

Here's my detailed plan:
"""

# Enhanced code manipulation prompt template
SEMANTIC_CODE_MANIPULATION_PROMPT = """
I need to modify code with a detailed understanding of its semantic structure and implications.

## Entity to Modify
{entity_type}: {entity_name}
Purpose: {entity_summary}
Dependencies: {entity_dependencies}
Referenced by: {entity_references}

## Desired Modification
"{instruction}"

## Approach
I'll make this change while:
1. Preserving the function's contract with callers
2. Maintaining consistent error handling
3. Respecting existing patterns
4. Updating related documentation
5. Considering potential impacts on dependent code

## Modified Code
```{language}
{modified_code}
```
"""

# Template for summarizing recent coding activity
CODING_HISTORY_CONTEXT = """
## Recent Coding Activity
Recently Modified Entities:
{recent_entities}

Coding Patterns:
{coding_patterns}

Frequent Operations:
{common_operations}
"""

async def build_enhanced_prompt(
    request: str, 
    context: Dict[str, Any],
    similar_command: Optional[str] = None,
    intent_result: Optional[Dict[str, Any]] = None,
    entity_name: Optional[str] = None
) -> str:
    """
    Build an enhanced prompt for the Gemini API with semantic code understanding
    and project state awareness.
    
    Args:
        request: The user request
        context: Context information about the current environment
        similar_command: Optional similar command from history
        intent_result: Optional intent analysis result
        entity_name: Optional specific code entity to focus on
        
    Returns:
        A prompt string for the AI service with enhanced semantic context
    """
    logger.debug("Building enhanced prompt with semantic awareness")
    
    # Start with basic context information
    enhanced_context = f"Current working directory: {context.get('cwd', 'unknown')}\n"
    
    # Add project root if available
    project_root = context.get('project_root')
    if project_root:
        enhanced_context += f"Project root: {project_root}\n"
        
        # Add project type if available
        project_type = context.get('project_type', 'unknown')
        enhanced_context += f"Project type: {project_type}\n"
        
        # Get enhanced project state if available
        try:
            project_state = await project_state_analyzer.get_project_state(project_root)
            
            # Add Git status
            git_state = project_state.get('git_state', {})
            if git_state.get('is_git_repo', False):
                # Format Git status information
                branch = git_state.get('current_branch', 'unknown')
                has_changes = git_state.get('has_changes', False)
                
                # Format remote state information
                remote_state = git_state.get('remote_state', {})
                remote_info = ""
                if remote_state:
                    ahead = remote_state.get('ahead', 0)
                    behind = remote_state.get('behind', 0)
                    
                    if ahead > 0 and behind > 0:
                        remote_info = f"(ahead {ahead}, behind {behind})"
                    elif ahead > 0:
                        remote_info = f"(ahead {ahead})"
                    elif behind > 0:
                        remote_info = f"(behind {behind})"
                
                # Format change details
                change_details = ""
                if has_changes:
                    modified_count = len(git_state.get('modified_files', []))
                    untracked_count = len(git_state.get('untracked_files', []))
                    staged_count = len(git_state.get('staged_files', []))
                    
                    details = []
                    if modified_count > 0:
                        details.append(f"{modified_count} modified")
                    if untracked_count > 0:
                        details.append(f"{untracked_count} untracked")
                    if staged_count > 0:
                        details.append(f"{staged_count} staged")
                    
                    change_details = f"({', '.join(details)})"
                
                # Add Git information to context
                enhanced_context += PROJECT_STATE_CONTEXT.format(
                    git_status="Active repository" if git_state.get('is_git_repo', False) else "Not a Git repository",
                    branch=branch,
                    remote_state=remote_info,
                    has_changes="With uncommitted changes" if has_changes else "Clean working directory",
                    change_details=change_details,
                    build_status=f"System: {project_state.get('build_status', {}).get('system', 'unknown')}",
                    test_status=f"Framework: {project_state.get('test_status', {}).get('framework', 'unknown')}",
                    dependencies_status=f"Manager: {project_state.get('dependencies', {}).get('package_manager', 'unknown')}",
                    issues_summary=_format_issues_summary(project_state)
                )
            
            # Add build status
            build_status = project_state.get('build_status', {})
            if build_status.get('build_system_detected', False):
                enhanced_context += f"Build system: {build_status.get('system', 'unknown')}\n"
                
                if build_status.get('last_build'):
                    enhanced_context += f"Last build: {build_status.get('last_build')}\n"
            
            # Add test status
            test_status = project_state.get('test_status', {})
            if test_status.get('test_framework_detected', False):
                enhanced_context += f"Test framework: {test_status.get('framework', 'unknown')}\n"
                enhanced_context += f"Test files: {test_status.get('test_files_count', 0)}\n"
                
                if test_status.get('coverage'):
                    enhanced_context += f"Test coverage: {test_status.get('coverage', {}).get('percentage')}%\n"
            
            # Add dependency information
            dependencies = project_state.get('dependencies', {})
            if dependencies.get('has_dependencies', False):
                enhanced_context += f"Package manager: {dependencies.get('package_manager', 'unknown')}\n"
                enhanced_context += f"Dependencies: {dependencies.get('dependencies_count', 0)} main, {dependencies.get('dev_dependencies_count', 0)} dev\n"
                
                if dependencies.get('outdated_packages'):
                    outdated_count = len(dependencies.get('outdated_packages', []))
                    enhanced_context += f"Outdated packages: {outdated_count}\n"
        
        except Exception as e:
            logger.error(f"Error getting project state: {str(e)}")
    
    # Add semantic code information if a specific entity is provided
    if entity_name and project_root:
        try:
            entity_info = await semantic_analyzer.analyze_entity_usage(entity_name, project_root)
            
            if entity_info.get('found', False):
                entity_type = entity_info.get('type', 'unknown')
                filename = entity_info.get('filename', 'unknown')
                line_start = entity_info.get('line_start', 0)
                line_end = entity_info.get('line_end', 0)
                
                # Generate a summary of the entity
                summary = await semantic_analyzer.summarize_code_entity(entity_name, project_root)
                
                # Format related entities
                related = entity_info.get('related_entities', [])
                related_entities = ""
                if related:
                    related_entities = "\n".join([
                        f"- {r.get('name')} ({r.get('relationship')})"
                        for r in related[:5]  # Limit to 5 for brevity
                    ])
                else:
                    related_entities = "None detected"
                
                # Format dependencies
                dependencies = entity_info.get('details', {}).get('dependencies', [])
                dependencies_str = ", ".join(dependencies) if dependencies else "None detected"
                
                # Add semantic information to context
                enhanced_context += SEMANTIC_CODE_CONTEXT.format(
                    entity_type=entity_type.capitalize(),
                    entity_name=entity_name,
                    filename=Path(filename).name,
                    line_start=line_start,
                    line_end=line_end,
                    summary=summary,
                    related_entities=related_entities,
                    dependencies=dependencies_str
                )
        
        except Exception as e:
            logger.error(f"Error getting semantic code information: {str(e)}")
    
    # Add information about the current file if available
    current_file = context.get('current_file')
    if current_file:
        file_path = current_file.get('path')
        enhanced_context += f"Current file: {file_path}\n"
        
        # Try to get semantic information about the current file
        if project_root and file_path:
            try:
                file_path_obj = Path(file_path)
                module = await semantic_analyzer.analyze_file(file_path_obj)
                
                if module:
                    # Add basic module information
                    enhanced_context += f"File type: {module.language} module\n"
                    enhanced_context += f"Functions: {len(module.functions)}\n"
                    enhanced_context += f"Classes: {len(module.classes)}\n"
                    
                    # Add key entities in the file
                    if module.functions or module.classes:
                        enhanced_context += "Key entities:\n"
                        
                        # List top classes
                        for class_name in list(module.classes.keys())[:3]:
                            cls = module.classes[class_name]
                            method_count = len(cls.methods)
                            enhanced_context += f"- Class {class_name} ({method_count} methods)\n"
                        
                        # List top functions
                        for func_name in list(module.functions.keys())[:3]:
                            func = module.functions[func_name]
                            enhanced_context += f"- Function {func_name}({', '.join(func.params)})\n"
            except Exception as e:
                logger.error(f"Error analyzing current file: {str(e)}")
    
    # Add recent file activity information
    recent_files = context.get('recent_files', {})
    if recent_files:
        accessed_files = recent_files.get('accessed', [])
        active_files = recent_files.get('active_files', [])
        
        if accessed_files or active_files:
            enhanced_context += "Recent file activity:\n"
            
            if accessed_files:
                enhanced_context += f"- Accessed: {', '.join([Path(f).name for f in accessed_files[:3]])}\n"
            
            if active_files:
                enhanced_context += f"- Most active: {', '.join([f.get('name', 'unknown') for f in active_files[:3]])}\n"
    
    # Add intent analysis if available
    if intent_result:
        enhanced_context += "\nIntent analysis:\n"
        enhanced_context += f"- Intent type: {intent_result.get('intent_type', 'unknown')}\n"
        enhanced_context += f"- Confidence: {intent_result.get('confidence', 0.0):.2f}\n"
        
        # Add extracted entities
        if intent_result.get("entities"):
            enhanced_context += "- Extracted entities:\n"
            for key, value in intent_result.get("entities", {}).items():
                enhanced_context += f"  - {key}: {value}\n"
    
    # Add similar command suggestion if available
    if similar_command:
        enhanced_context += f"\nYou previously suggested this similar command: {similar_command}\n"
    
    # Add examples for few-shot learning
    examples = "\nExamples:\n"
    
    # Add standard examples
    for example in EXAMPLES:
        examples += f"\nUser request: {example['request']}\n"
        examples += f"Context: {example['context']}\n"
        examples += f"Response: {example['response']}\n"
    
    # Define the expected response format
    response_format = """
Expected response format (valid JSON):
{
    "intent": "the_classified_intent",
    "command": "the_suggested_command",
    "explanation": "explanation of what the command does, including semantic considerations",
    "confidence": 0.85, /* Optional confidence score from 0.0 to 1.0 */
    "semantic_insights": "insights about code/project impacts (optional)",
    "additional_info": "any additional information (optional)"
}
"""
    
    # Build the complete prompt
    prompt = f"{ENHANCED_SYSTEM_INSTRUCTIONS}\n\n{enhanced_context}\n\n{examples}\n\n{response_format}\n\nUser request: {request}\n\nResponse:"
    
    logger.debug(f"Built enhanced prompt with length: {len(prompt)}")
    return prompt

def _format_issues_summary(project_state: Dict[str, Any]) -> str:
    """Format a summary of project issues for the prompt."""
    todo_items = project_state.get('todo_items', [])
    code_quality = project_state.get('code_quality', {})
    issues_count = code_quality.get('issues_count', 0)
    high_priority_issues = code_quality.get('high_priority_issues', [])
    
    summary = []
    
    if todo_items:
        todo_count = len(todo_items)
        fixme_count = sum(1 for item in todo_items if item.get('type') == 'FIXME')
        summary.append(f"{todo_count} TODOs ({fixme_count} FIXMEs)")
    
    if issues_count > 0:
        summary.append(f"{issues_count} linting issues")
    
    if high_priority_issues:
        summary.append(f"{len(high_priority_issues)} high-priority issues")
    
    if not summary:
        return "No significant issues detected"
    
    return ", ".join(summary)

async def build_semantic_code_manipulation_prompt(
    entity_name: str,
    instruction: str,
    project_root: Union[str, Path],
    modified_code: Optional[str] = None
) -> str:
    """
    Build a prompt for modifying code with semantic understanding.
    
    Args:
        entity_name: Name of the entity to modify
        instruction: The modification instruction
        project_root: Path to the project root
        modified_code: Optional modified code to include
        
    Returns:
        A prompt string for code manipulation
    """
    logger.debug(f"Building semantic code manipulation prompt for {entity_name}")
    
    try:
        # Get semantic information about the entity
        entity_info = await semantic_analyzer.analyze_entity_usage(entity_name, project_root)
        
        if not entity_info.get('found', False):
            return f"Could not find entity '{entity_name}' in the project."
        
        # Get entity information
        entity_type = entity_info.get('type', 'unknown')
        filename = entity_info.get('filename', 'unknown')
        line_start = entity_info.get('line_start', 0)
        line_end = entity_info.get('line_end', 0)
        
        # Get a summary of the entity
        entity_summary = await semantic_analyzer.summarize_code_entity(entity_name, project_root)
        
        # Get the entity's code if not provided
        if not modified_code:
            original_code = await semantic_analyzer.get_entity_code(entity_name, project_root)
            modified_code = original_code
        
        # Get file type
        file_info = detect_file_type(Path(filename))
        language = file_info.get('language', '').lower()
        
        # Format references
        related = entity_info.get('related_entities', [])
        references = []
        
        for r in related:
            if r.get('relationship') == 'called_by':
                references.append(f"{r.get('name')} calls this {entity_type}")
            elif r.get('relationship') == 'extended_by':
                references.append(f"{r.get('name')} extends this {entity_type}")
        
        references_str = "\n".join([f"- {ref}" for ref in references]) if references else "None detected"
        
        # Format dependencies
        dependencies = []
        
        if entity_type == 'function' or entity_type == 'method':
            for called in entity_info.get('details', {}).get('called_functions', []):
                dependencies.append(f"Calls {called}")
        
        elif entity_type == 'class':
            for base in entity_info.get('base_classes', []):
                dependencies.append(f"Extends {base}")
        
        dependencies_str = "\n".join([f"- {dep}" for dep in dependencies]) if dependencies else "None detected"
        
        # Build the prompt
        prompt = SEMANTIC_CODE_MANIPULATION_PROMPT.format(
            entity_type=entity_type.capitalize(),
            entity_name=entity_name,
            entity_summary=entity_summary,
            entity_dependencies=dependencies_str,
            entity_references=references_str,
            instruction=instruction,
            language=language,
            modified_code=modified_code
        )
        
        return prompt
    
    except Exception as e:
        logger.error(f"Error building semantic code manipulation prompt: {str(e)}")
        return f"Error building semantic code manipulation prompt: {str(e)}"

async def build_semantic_task_planning_prompt(
    request: str,
    context: Dict[str, Any],
    entity_names: Optional[List[str]] = None
) -> str:
    """
    Build a prompt for task planning with semantic understanding.
    
    Args:
        request: The user request
        context: Context information
        entity_names: Optional list of entity names to focus on
        
    Returns:
        A prompt string for task planning
    """
    logger.debug("Building semantic task planning prompt")
    
    project_root = context.get('project_root')
    if not project_root:
        return build_prompt(request, context)  # Fall back to regular prompt
    
    # Build semantic code context
    semantic_code_context = ""
    
    if entity_names:
        for entity_name in entity_names:
            try:
                entity_info = await semantic_analyzer.analyze_entity_usage(entity_name, project_root)
                
                if entity_info.get('found', False):
                    entity_type = entity_info.get('type', 'unknown')
                    filename = entity_info.get('filename', 'unknown')
                    
                    # Get a summary of the entity
                    summary = await semantic_analyzer.summarize_code_entity(entity_name, project_root)
                    
                    semantic_code_context += f"{entity_type.capitalize()}: {entity_name} in {Path(filename).name}\n"
                    semantic_code_context += f"Summary: {summary}\n\n"
            except Exception as e:
                logger.error(f"Error getting semantic info for {entity_name}: {str(e)}")
    
    # Get project state context
    project_state_context = ""
    
    try:
        # Get project state
        project_state = await project_state_analyzer.get_project_state(project_root)
        
        # Format Git information
        git_state = project_state.get('git_state', {})
        if git_state.get('is_git_repo', False):
            branch = git_state.get('current_branch', 'unknown')
            has_changes = git_state.get('has_changes', False)
            
            project_state_context += f"Git: Branch {branch}, "
            project_state_context += "Uncommitted changes" if has_changes else "Clean working directory"
            project_state_context += "\n"
        
        # Add build status
        build_status = project_state.get('build_status', {})
        if build_status.get('build_system_detected', False):
            project_state_context += f"Build: {build_status.get('system', 'unknown')}"
            
            if build_status.get('last_build'):
                project_state_context += f", Last build at {build_status.get('last_build')}"
            
            project_state_context += "\n"
        
        # Add test status
        test_status = project_state.get('test_status', {})
        if test_status.get('test_framework_detected', False):
            project_state_context += f"Tests: {test_status.get('framework', 'unknown')}, "
            project_state_context += f"{test_status.get('test_files_count', 0)} test files"
            
            if test_status.get('coverage'):
                project_state_context += f", {test_status.get('coverage', {}).get('percentage')}% coverage"
            
            project_state_context += "\n"
        
        # Add code quality issues
        code_quality = project_state.get('code_quality', {})
        if code_quality.get('linting_setup_detected', False):
            project_state_context += f"Linting: {code_quality.get('linter', 'unknown')}, "
            project_state_context += f"{code_quality.get('issues_count', 0)} issues"
            project_state_context += "\n"
        
        # Add TODO items
        todo_items = project_state.get('todo_items', [])
        if todo_items:
            project_state_context += f"TODOs: {len(todo_items)} items "
            
            # Count by type
            todo_counts = {}
            for item in todo_items:
                item_type = item.get('type', 'unknown')
                if item_type not in todo_counts:
                    todo_counts[item_type] = 0
                todo_counts[item_type] += 1
            
            type_counts = [f"{count} {type_}" for type_, count in todo_counts.items()]
            project_state_context += f"({', '.join(type_counts)})"
            project_state_context += "\n"
    
    except Exception as e:
        logger.error(f"Error getting project state: {str(e)}")
    
    # Get recent activity information
    recent_activity = ""
    
    # Add recent file activity
    recent_files = context.get('recent_files', {})
    if recent_files:
        accessed = recent_files.get('accessed', [])
        if accessed:
            recent_activity += "Recently accessed files:\n"
            for file_path in accessed[:5]:
                recent_activity += f"- {Path(file_path).name}\n"
    
    # Add recent commands
    session = context.get('session', {})
    recent_commands = session.get('recent_commands', [])
    if recent_commands:
        recent_activity += "\nRecent commands:\n"
        for cmd in recent_commands[:5]:
            recent_activity += f"- {cmd}\n"
    
    # Build the prompt
    prompt = SEMANTIC_TASK_PLANNING_PROMPT.format(
        semantic_code_context=semantic_code_context or "No specific code entities focused on.",
        project_state_context=project_state_context or "No detailed project state available.",
        recent_activity=recent_activity or "No recent activity recorded.",
        request=request
    )
    
    return prompt
