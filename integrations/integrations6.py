"""
Phase 6 Integration for Enhanced Project Context.

This file provides the necessary integration points for all Phase 6 components.
It should be used to update the existing code in the Angela CLI project.
"""

# Import statements to add to the beginning of orchestrator.py
IMPORT_STATEMENTS = """
from angela.context.enhancer import context_enhancer
from angela.context.file_resolver import file_resolver
from angela.context.file_activity import file_activity_tracker, ActivityType
from angela.execution.hooks import execution_hooks
"""

# Updated process_request method for Orchestrator class
PROCESS_REQUEST_METHOD = """
async def process_request(
    self, 
    request: str, 
    execute: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    '''
    Process a request from the user with enhanced context.
    
    Args:
        request: The user request
        execute: Whether to execute commands
        dry_run: Whether to simulate execution without making changes
        
    Returns:
        Dictionary with processing results
    '''
    # Refresh context to ensure we have the latest information
    context_manager.refresh_context()
    context = context_manager.get_context_dict()
    
    # Add session context for continuity across requests
    session_context = session_manager.get_context()
    context["session"] = session_context
    
    # Enhance context with project information, dependencies, and recent activity
    context = await context_enhancer.enrich_context(context)
    
    self._logger.info(f"Processing request: {request}")
    self._logger.debug(f"Enhanced context with {len(context)} keys")
    
    # Extract and resolve file references
    file_references = await file_resolver.extract_references(request, context)
    if file_references:
        # Add resolved file references to context
        context["resolved_files"] = [
            {"reference": ref, "path": str(path) if path else None}
            for ref, path in file_references
        ]
        self._logger.debug(f"Resolved {len(file_references)} file references")
    
    try:
        # Analyze the request to determine its type
        request_type = await self._determine_request_type(request, context)
        self._logger.info(f"Determined request type: {request_type.value}")
        
        # Process the request based on its type
        if request_type == RequestType.COMMAND:
            # Handle single command request
            return await self._process_command_request(request, context, execute, dry_run)
            
        elif request_type == RequestType.MULTI_STEP:
            # Handle multi-step operation
            return await self._process_multi_step_request(request, context, execute, dry_run)
            
        elif request_type == RequestType.FILE_CONTENT:
            # Handle file content analysis/manipulation
            return await self._process_file_content_request(request, context, execute, dry_run)
            
        elif request_type == RequestType.WORKFLOW_DEFINITION:
            # Handle workflow definition
            return await self._process_workflow_definition(request, context)
            
        elif request_type == RequestType.WORKFLOW_EXECUTION:
            # Handle workflow execution
            return await self._process_workflow_execution(request, context, execute, dry_run)
            
        elif request_type == RequestType.CLARIFICATION:
            # Handle request for clarification
            return await self._process_clarification_request(request, context)
            
        else:
            # Handle unknown request type
            return await self._process_unknown_request(request, context)
        
    except Exception as e:
        self._logger.exception(f"Error processing request: {str(e)}")
        # Fallback behavior
        return {
            "request": request,
            "response": f"An error occurred while processing your request: {str(e)}",
            "error": str(e),
            "context": context,
        }
"""

# Updated _extract_file_path method for Orchestrator class
EXTRACT_FILE_PATH_METHOD = """
async def _extract_file_path(
    self, 
    request: str, 
    context: Dict[str, Any]
) -> Optional[Path]:
    '''
    Extract a file path from a request using file_resolver.
    
    Args:
        request: The user request
        context: Context information
        
    Returns:
        Path object if found, None otherwise
    '''
    self._logger.debug(f"Extracting file path from: {request}")
    
    # Try to extract file references
    file_references = await file_resolver.extract_references(request, context)
    
    # If we found any resolved references, return the first one
    for reference, path in file_references:
        if path:
            # Track as viewed file
            file_activity_tracker.track_file_viewing(path, None, {
                "request": request,
                "reference": reference
            })
            return path
    
    # If we found references but couldn't resolve them, use AI extraction as fallback
    if file_references:
        for reference, _ in file_references:
            # Try to resolve with a broader scope
            path = await file_resolver.resolve_reference(
                reference, 
                context,
                search_scope="project"
            )
            if path:
                # Track as viewed file
                file_activity_tracker.track_file_viewing(path, None, {
                    "request": request,
                    "reference": reference
                })
                return path
    
    # If all else fails, fall back to the original AI method
    prompt = f'''
Extract the most likely file path from this user request:
"{request}"

Current working directory: {context["cwd"]}
Project root (if any): {context.get("project_root", "None")}

Return the most likely file path as just a single word, with no additional explanation or context.
'''
    
    api_request = GeminiRequest(prompt=prompt, max_tokens=100)
    response = await gemini_client.generate_text(api_request)
    
    file_name = response.text.strip()
    
    # Remove quotes if present
    if file_name.startswith('"') and file_name.endswith('"'):
        file_name = file_name[1:-1]
    if file_name.startswith("'") and file_name.endswith("'"):
        file_name = file_name[1:-1]
    
    # Check if this is a valid path
    path = Path(file_name)
    if not path.is_absolute():
        # Check in current directory
        cwd_path = Path(context["cwd"]) / path
        if cwd_path.exists():
            return cwd_path
        
        # Check in project root if available
        if context.get("project_root"):
            proj_path = Path(context["project_root"]) / path
            if proj_path.exists():
                return proj_path
    else:
        # Absolute path
        if path.exists():
            return path
    
    # No valid path found
    return None
"""

# Updates to execution methods to add hooks
EXECUTE_COMMAND_METHOD = """
async def execute_command(
    self, 
    command: str,
    natural_request: str,
    explanation: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    '''
    Execute a command with adaptive behavior based on user context.
    
    Args:
        command: The command to execute
        natural_request: The original natural language request
        explanation: AI explanation of what the command does
        dry_run: Whether to simulate the command without execution
        
    Returns:
        Dictionary with execution results
    '''
    self._logger.info(f"Preparing to execute command: {command}")
    
    # Get current context for hooks
    context = context_manager.get_context_dict()
    
    # Call pre-execution hook
    await execution_hooks.pre_execute_command(command, context)
    
    # Analyze command risk and impact
    risk_level, risk_reason = classify_command_risk(command)
    impact = analyze_command_impact(command)
    
    # Add to session context
    session_manager.add_command(command)
    
    # Generate command preview if needed
    from angela.safety.preview import generate_preview
    preview = await generate_preview(command) if preferences_manager.preferences.ui.show_command_preview else None
    
    # Get adaptive confirmation based on risk level and user history
    confirmed = await get_adaptive_confirmation(
        command=command,
        risk_level=risk_level,
        risk_reason=risk_reason,
        impact=impact,
        preview=preview,
        explanation=explanation,
        natural_request=natural_request,
        dry_run=dry_run
    )
    
    if not confirmed and not dry_run:
        self._logger.info(f"Command execution cancelled by user: {command}")
        return {
            "command": command,
            "success": False,
            "cancelled": True,
            "stdout": "",
            "stderr": "Command execution cancelled by user",
            "return_code": 1,
            "dry_run": dry_run
        }
    
    # Execute the command
    result = await self._execute_with_feedback(command, dry_run)
    
    # Call post-execution hook
    await execution_hooks.post_execute_command(command, result, context)
    
    # Add to history
    history_manager.add_command(
        command=command,
        natural_request=natural_request,
        success=result["success"],
        output=result.get("stdout", ""),
        error=result.get("stderr", ""),
        risk_level=risk_level
    )
    
    # If execution failed, analyze error and suggest fixes
    if not result["success"] and result.get("stderr"):
        result["error_analysis"] = error_analyzer.analyze_error(command, result["stderr"])
        result["fix_suggestions"] = error_analyzer.generate_fix_suggestions(command, result["stderr"])
    
    # Offer to learn from successful executions
    if result["success"] and risk_level > 0:
        from angela.safety.adaptive_confirmation import offer_command_learning
        await offer_command_learning(command)
    
    return result
"""

# Integration steps for Phase 6
INTEGRATION_STEPS = """
To integrate Phase 6 components:

1. Add the new Python files to the project:
   - angela/context/enhancer.py
   - angela/context/file_resolver.py
   - angela/context/file_activity.py
   - angela/execution/hooks.py

2. Update orchestrator.py:
   - Add the import statements at the top
   - Replace process_request method with the updated version
   - Replace _extract_file_path method with the updated version
   - Update execute_command method in adaptive_engine.py with the updated version

3. Update ai/prompts.py:
   - Add the new prompt templates
   - Replace build_prompt function with the updated version
   - Replace build_file_operation_prompt function with the updated version

4. Update execution/engine.py and execution/adaptive_engine.py:
   - Add hooks integration to execution methods

5. Test all components:
   - Test project inference
   - Test file resolution
   - Test file activity tracking
   - Test enhanced prompts

6. Update documentation to reflect the new capabilities
"""

# Installation and usage instructions
INSTALLATION_INSTRUCTIONS = """
# Phase 6: Enhanced Project Context

## Installation

1. Copy the new Python files to their respective directories:
   ```
   cp angela/context/enhancer.py /path/to/angela/context/
   cp angela/context/file_resolver.py /path/to/angela/context/
   cp angela/context/file_activity.py /path/to/angela/context/
   cp angela/execution/hooks.py /path/to/angela/execution/
   ```

2. Update the existing files with the provided code snippets.

3. Install additional dependencies if needed:
   ```
   pip install difflib
   ```

## Usage

The enhanced project context capabilities are automatically used by the system.
When you make a request, Angela will:

1. Detect project type and dependencies
2. Resolve file references in your natural language query
3. Track file activities
4. Use all this information to provide more contextually relevant responses

Example usage:
```
angela "Find all functions in the main file that handle user input"
```

In this example, Angela will:
- Infer what "main file" means in your project
- Find relevant functions
- Track this file viewing in its history
- Use project context to understand what "user input" means in your specific project type
```
