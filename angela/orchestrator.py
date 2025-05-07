"""
Main orchestration service for Angela CLI.

This module coordinates all the components of Angela CLI, from receiving
user requests to executing commands with safety checks.
"""
import asyncio
import re
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from enum import Enum

from angela.ai.client import gemini_client, GeminiRequest
from angela.ai.prompts import build_prompt
from angela.ai.parser import parse_ai_response, CommandSuggestion
from angela.ai.file_integration import extract_file_operation, execute_file_operation
from angela.ai.content_analyzer import content_analyzer
from angela.context import context_manager
from angela.context.session import session_manager
from angela.context.history import history_manager
from angela.execution.engine import execution_engine
from angela.execution.adaptive_engine import adaptive_engine
from angela.ai.analyzer import error_analyzer
from angela.ai.intent_analyzer import intent_analyzer
from angela.ai.confidence import confidence_scorer
from angela.intent.planner import task_planner
from angela.workflows.manager import workflow_manager
from angela.utils.logging import get_logger
from angela.shell.formatter import terminal_formatter, OutputType
from angela.execution.error_recovery import ErrorRecoveryManager
from angela.context.enhancer import context_enhancer
from angela.context.file_resolver import file_resolver
from angela.context.file_activity import file_activity_tracker, ActivityType
from angela.execution.hooks import execution_hooks
from angela.core.registry import registry

logger = get_logger(__name__)

class RequestType(Enum):
    """Types of requests that can be handled by the orchestrator."""
    COMMAND = "command"                # Single command suggestion
    MULTI_STEP = "multi_step"          # Multi-step operation
    FILE_CONTENT = "file_content"      # File content analysis/manipulation
    WORKFLOW_DEFINITION = "workflow"   # Define a new workflow
    WORKFLOW_EXECUTION = "run_workflow" # Execute a workflow
    CLARIFICATION = "clarification"    # Request for clarification
    UNKNOWN = "unknown"                # Unknown request type

class Orchestrator:
    """Main orchestration service for Angela CLI."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        self._logger = logger
        self._background_tasks = set()
        self._error_recovery_manager = ErrorRecoveryManager()
    
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
        # Initialize dependencies we'll need (getting from registry avoids circular imports)
        if self._error_recovery_manager is None:
            self._error_recovery_manager = registry.get("error_recovery_manager")
            
        # Get context enhancer from registry
        context_enhancer = registry.get("context_enhancer")
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
    
    async def _determine_request_type(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> RequestType:
        """
        Determine the type of request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            RequestType enum value
        """
        # Check for keywords and patterns indicating different request types
        
        # Workflow definition patterns
        workflow_def_patterns = [
            r'\b(?:define|create|make|add)\s+(?:a\s+)?(?:new\s+)?workflow\b',
            r'\bworkflow\s+(?:called|named)\b',
            r'\bsave\s+(?:this|these)\s+(?:as\s+(?:a\s+)?)?workflow\b',
        ]
        
        # Workflow execution patterns
        workflow_exec_patterns = [
            r'\brun\s+(?:the\s+)?workflow\b',
            r'\bexecute\s+(?:the\s+)?workflow\b',
            r'\bstart\s+(?:the\s+)?workflow\b',
        ]
        
        # File content patterns
        file_content_patterns = [
            r'\b(?:analyze|understand|summarize|examine)\s+(?:the\s+)?(?:content|code|text)\b',
            r'\b(?:modify|change|update|edit|refactor)\s+(?:the\s+)?(?:content|code|text|file)\b',
            r'\bfind\s+(?:in|inside|within)\s+(?:the\s+)?file\b',
        ]
        
        # Multi-step operation patterns
        multi_step_patterns = [
            r'\b(?:multiple steps|sequence|series|several|many)\b',
            r'\band then\b',
            r'\bafter that\b',
            r'\bone by one\b',
            r'\bstep by step\b',
            r'\bautomatically\b',
        ]
        
        # Check for workflow definition
        for pattern in workflow_def_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                return RequestType.WORKFLOW_DEFINITION
        
        # Check for workflow execution
        for pattern in workflow_exec_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                return RequestType.WORKFLOW_EXECUTION
        
        # Check for file content analysis/manipulation
        file_mentions = re.search(r'\b(?:file|code|script|document)\b', request, re.IGNORECASE)
        if file_mentions:
            for pattern in file_content_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.FILE_CONTENT
        
        # Check for multi-step operation
        complexity_indicators = sum(bool(re.search(pattern, request, re.IGNORECASE)) for pattern in multi_step_patterns)
        if complexity_indicators >= 1 or len(request.split()) > 15:
            # Complex requests or longer instructions often imply multi-step operations
            return RequestType.MULTI_STEP
        
        # Default to single command
        return RequestType.COMMAND
    
    async def _process_command_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a single command request.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the command
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        # Analyze intent with enhanced NLU
        intent_result = await intent_analyzer.analyze_intent(request)
        
        # Check if we've seen a similar request before
        similar_command = history_manager.search_similar_command(request)
        
        # Get command suggestion from AI
        suggestion = await self._get_ai_suggestion(
            request, 
            context, 
            similar_command, 
            intent_result
        )
        
        # Score confidence in the suggestion
        confidence = confidence_scorer.score_command_confidence(
            request=request,
            command=suggestion.command,
            context=context
        )
        
        # If confidence is low, offer clarification
        if confidence < 0.6 and not dry_run and not session_context.get("skip_clarification"):
            # Interactive clarification
            from prompt_toolkit.shortcuts import yes_no_dialog
            should_proceed = yes_no_dialog(
                title="Low Confidence Suggestion",
                text=f"I'm not very confident this is what you meant:\n\n{suggestion.command}\n\nWould you like to proceed with this command?",
            ).run()
            
            if not should_proceed:
                return {
                    "request": request,
                    "response": "Command cancelled due to low confidence.",
                    "context": context,
                }
        
        result = {
            "request": request,
            "suggestion": suggestion,
            "confidence": confidence,
            "intent": intent_result.intent_type if hasattr(intent_result, 'intent_type') else "unknown",
            "context": context,
            "type": "command"
        }
        
        # Execute the command if requested
        if execute or dry_run:
            self._logger.info(f"{'Dry run' if dry_run else 'Executing'} suggested command: {suggestion.command}")
            
            # Execute using the adaptive engine with rich feedback
            execution_result = await adaptive_engine.execute_command(
                command=suggestion.command,
                natural_request=request,
                explanation=suggestion.explanation,
                dry_run=dry_run
            )
            
            result["execution"] = execution_result
            
            # If execution failed, analyze errors and provide suggestions
            if not execution_result.get("success") and execution_result.get("stderr"):
                error_analysis = error_analyzer.analyze_error(
                    suggestion.command, 
                    execution_result["stderr"]
                )
                result["error_analysis"] = error_analysis
                
                # Generate fix suggestions
                fix_suggestions = error_analyzer.generate_fix_suggestions(
                    suggestion.command, 
                    execution_result["stderr"]
                )
                execution_result["fix_suggestions"] = fix_suggestions
                
                # Start background monitoring
                if not dry_run:
                    self._start_background_monitoring(suggestion.command, error_analysis)
        
        return result
    


    
    # Add this as a class member in the Orchestrator class
    def __init__(self):
        """Initialize the orchestrator."""
        self._logger = logger
        self._background_tasks = set()
        self._error_recovery_manager = ErrorRecoveryManager()
    

    
    # Updates for angela/orchestrator.py
    # Add these methods to the Orchestrator class
    
    async def _process_multi_step_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a multi-step operation request with transaction-based rollback support.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the commands
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing multi-step request: {request}")
        
        # Determine if we should use advanced planning
        complexity = await task_planner._determine_complexity(request)
        
        # Start a transaction for this multi-step operation
        transaction_id = None
        if not dry_run:
            transaction_id = await rollback_manager.start_transaction(f"Multi-step plan: {request[:50]}...")
        
        try:
            if complexity == "advanced":
                # Use the advanced planner for complex tasks
                plan = await task_planner.plan_task(request, context, complexity)
                
                # Record the plan in the transaction
                if transaction_id:
                    await rollback_manager.record_plan_execution(
                        plan_id=plan.id,
                        goal=plan.goal,
                        plan_data=plan.dict(),
                        transaction_id=transaction_id
                    )
                
                # Create result with the plan
                if isinstance(plan, AdvancedTaskPlan):
                    # Advanced plan with branching
                    result = {
                        "request": request,
                        "type": "advanced_multi_step",
                        "context": context,
                        "plan": {
                            "id": plan.id,
                            "goal": plan.goal,
                            "description": plan.description,
                            "steps": [
                                {
                                    "id": step_id,
                                    "type": step.type,
                                    "description": step.description,
                                    "command": step.command,
                                    "dependencies": step.dependencies,
                                    "risk": step.estimated_risk
                                }
                                for step_id, step in plan.steps.items()
                            ],
                            "entry_points": plan.entry_points,
                            "step_count": len(plan.steps)
                        }
                    }
                    
                    # Execute the plan if requested
                    if execute or dry_run:
                        # Display the plan with rich formatting
                        await terminal_formatter.display_advanced_plan(plan)
                        
                        # Get confirmation for plan execution
                        confirmed = await self._confirm_advanced_plan(plan, dry_run)
                        
                        if confirmed or dry_run:
                            # Execute the plan with transaction support
                            execution_results = await task_planner.execute_plan(
                                plan, 
                                dry_run=dry_run,
                                transaction_id=transaction_id
                            )
                            result["execution_results"] = execution_results
                            result["success"] = execution_results.get("success", False)
                            
                            # Update transaction status
                            if transaction_id:
                                status = "completed" if result["success"] else "failed"
                                await rollback_manager.end_transaction(transaction_id, status)
                        else:
                            result["cancelled"] = True
                            result["success"] = False
                            
                            # End the transaction as cancelled
                            if transaction_id:
                                await rollback_manager.end_transaction(transaction_id, "cancelled")
                else:
                    # Basic plan (fallback)
                    result = await self._process_basic_multi_step(plan, request, context, execute, dry_run, transaction_id)
            else:
                # Use the basic planner for simple tasks
                plan = await task_planner.plan_task(request, context)
                result = await self._process_basic_multi_step(plan, request, context, execute, dry_run, transaction_id)
            
            return result
        
        except Exception as e:
            # Handle any exceptions and end the transaction
            if transaction_id:
                await rollback_manager.end_transaction(transaction_id, "failed")
            
            self._logger.exception(f"Error processing multi-step request: {str(e)}")
            raise
        
    async def _process_basic_multi_step(
        self,
        plan: TaskPlan,
        request: str,
        context: Dict[str, Any],
        execute: bool,
        dry_run: bool,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a basic multi-step plan with transaction support.
        
        Args:
            plan: The task plan
            request: The user request
            context: Context information
            execute: Whether to execute the commands
            dry_run: Whether to simulate execution without making changes
            transaction_id: Transaction ID for tracking operations
            
        Returns:
            Dictionary with processing results
        """
        # Record the plan in the transaction if not already done
        if transaction_id and not dry_run:
            await rollback_manager.record_plan_execution(
                plan_id=getattr(plan, "id", str(uuid.uuid4())),
                goal=plan.goal,
                plan_data=plan.dict(),
                transaction_id=transaction_id
            )
        
        # Create result with the plan
        result = {
            "request": request,
            "type": "multi_step",
            "context": context,
            "plan": {
                "goal": plan.goal,
                "steps": [
                    {
                        "command": step.command,
                        "explanation": step.explanation,
                        "dependencies": step.dependencies,
                        "risk": step.estimated_risk
                    }
                    for step in plan.steps
                ],
                "step_count": len(plan.steps)
            }
        }
        
        # Execute the plan if requested
        if execute or dry_run:
            # Display the plan with rich formatting
            await self._display_plan(plan)
            
            # Get confirmation for plan execution
            confirmed = await self._confirm_plan_execution(plan, dry_run)
            
            if confirmed or dry_run:
                # Execute the plan with transaction support
                execution_results = await task_planner.execute_plan(
                    plan, 
                    dry_run=dry_run,
                    transaction_id=transaction_id
                )
                result["execution_results"] = execution_results
                result["success"] = all(r.get("success", False) for r in execution_results)
                
                # Update transaction status
                if transaction_id:
                    status = "completed" if result["success"] else "failed"
                    await rollback_manager.end_transaction(transaction_id, status)
                
                # Handle errors with recovery
                if not result["success"] and not dry_run:
                    recovered_results = await self._handle_execution_errors(plan, execution_results)
                    result["recovery_attempted"] = True
                    result["recovered_results"] = recovered_results
                    # Update success status if recovery was successful
                    if all(r.get("success", False) for r in recovered_results):
                        result["success"] = True
            else:
                result["cancelled"] = True
                result["success"] = False
                
                # End the transaction as cancelled
                if transaction_id:
                    await rollback_manager.end_transaction(transaction_id, "cancelled")
        
        return result
    
    async def _process_file_content_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a file content analysis/manipulation request with transaction support.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute file operations
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing file content request: {request}")
        
        # Start a transaction for this operation
        transaction_id = None
        if not dry_run and execute:
            transaction_id = await rollback_manager.start_transaction(f"File content operation: {request[:50]}...")
        
        try:
            # Extract file path from request using file_resolver
            file_path = await self._extract_file_path(request, context)
            
            if not file_path:
                # End the transaction as failed
                if transaction_id:
                    await rollback_manager.end_transaction(transaction_id, "failed")
                    
                return {
                    "request": request,
                    "type": "file_content",
                    "context": context,
                    "error": "Could not determine file path from request",
                    "response": "I couldn't determine which file you're referring to. Please specify the file path."
                }
            
            # Determine if this is analysis or manipulation
            operation_type = await self._determine_file_operation_type(request)
            
            result = {
                "request": request,
                "type": "file_content",
                "context": context,
                "file_path": str(file_path),
                "operation_type": operation_type
            }
            
            if operation_type == "analyze":
                # Analyze file content (no rollback needed)
                analysis_result = await content_analyzer.analyze_content(file_path, request)
                result["analysis"] = analysis_result
                
                # End transaction as completed
                if transaction_id:
                    await rollback_manager.end_transaction(transaction_id, "completed")
                
            elif operation_type == "summarize":
                # Summarize file content (no rollback needed)
                summary_result = await content_analyzer.summarize_content(file_path)
                result["summary"] = summary_result
                
                # End transaction as completed
                if transaction_id:
                    await rollback_manager.end_transaction(transaction_id, "completed")
                
            elif operation_type == "search":
                # Search file content (no rollback needed)
                search_result = await content_analyzer.search_content(file_path, request)
                result["search_results"] = search_result
                
                # End transaction as completed
                if transaction_id:
                    await rollback_manager.end_transaction(transaction_id, "completed")
                
            elif operation_type == "manipulate":
                # Manipulate file content
                manipulation_result = await content_analyzer.manipulate_content(file_path, request)
                result["manipulation"] = manipulation_result
                
                # Apply changes if requested
                if execute and not dry_run and manipulation_result["has_changes"]:
                    # Get confirmation before applying changes
                    confirmed = await self._confirm_file_changes(
                        file_path, 
                        manipulation_result["diff"]
                    )
                    
                    if confirmed:
                        # Read original content for rollback
                        original_content = manipulation_result["original_content"]
                        modified_content = manipulation_result["modified_content"]
                        
                        # Record the content manipulation for rollback
                        if transaction_id:
                            await rollback_manager.record_content_manipulation(
                                file_path=file_path,
                                original_content=original_content,
                                modified_content=modified_content,
                                instruction=request,
                                transaction_id=transaction_id
                            )
                        
                        # Write the changes to the file
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(modified_content)
                            result["changes_applied"] = True
                            result["success"] = True
                            
                            # End transaction as completed
                            if transaction_id:
                                await rollback_manager.end_transaction(transaction_id, "completed")
                        except Exception as e:
                            self._logger.error(f"Error applying changes to {file_path}: {str(e)}")
                            result["error"] = f"Error applying changes: {str(e)}"
                            result["changes_applied"] = False
                            result["success"] = False
                            
                            # End transaction as failed
                            if transaction_id:
                                await rollback_manager.end_transaction(transaction_id, "failed")
                    else:
                        result["changes_applied"] = False
                        result["cancelled"] = True
                        
                        # End transaction as cancelled
                        if transaction_id:
                            await rollback_manager.end_transaction(transaction_id, "cancelled")
                elif dry_run and manipulation_result["has_changes"]:
                    result["changes_applied"] = False
                    result["success"] = True
                    result["dry_run"] = True
                    
                    # End transaction as completed for dry run
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "completed")
                else:
                    # No changes to apply or not executing
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "completed")
            
            return result
            
        except Exception as e:
            # Handle any exceptions and end the transaction
            if transaction_id:
                await rollback_manager.end_transaction(transaction_id, "failed")
            
            self._logger.exception(f"Error processing file content request: {str(e)}")
            raise
    

    
    async def _handle_execution_errors(
        self,
        plan: TaskPlan,
        execution_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Handle errors in multi-step execution with recovery.
        
        Args:
            plan: The task plan
            execution_results: Original execution results
            
        Returns:
            Updated execution results after recovery attempts
        """
        recovered_results = list(execution_results)  # Copy the original results
        
        # Find failed steps
        for i, result in enumerate(execution_results):
            if not result.get("success", False):
                # Get the corresponding step
                if i < len(plan.steps):
                    step = plan.steps[i]
                    
                    # Attempt recovery
                    recovery_result = await self._error_recovery_manager.handle_error(
                        step, result, {"plan": plan}
                    )
                    
                    # Update the result
                    if recovery_result.get("recovery_success", False):
                        recovered_results[i] = recovery_result
        
        return recovered_results
    
    async def _confirm_advanced_plan(self, plan: AdvancedTaskPlan, dry_run: bool) -> bool:
        """
        Get confirmation to execute an advanced plan.
        
        Args:
            plan: The advanced task plan
            dry_run: Whether this is a dry run
            
        Returns:
            True if confirmed, False otherwise
        """
        if dry_run:
            # No confirmation needed for dry run
            return True
        
        # Check if any steps are high risk
        has_high_risk = any(step.estimated_risk >= 3 for step in plan.steps.values())
        
        # Import here to avoid circular imports
        from rich.console import Console
        from prompt_toolkit.shortcuts import yes_no_dialog
        
        console = Console()
        
        if has_high_risk:
            # Use a more prominent warning for high-risk plans
            console.print(Panel(
                "⚠️  [bold red]This plan includes HIGH RISK operations[/bold red] ⚠️\n"
                "Some of these steps could make significant changes to your system.",
                border_style="red",
                expand=False
            ))
        
        # Show complexity warning for advanced plans
        console.print(Panel(
            "[bold yellow]This is an advanced plan with complex execution flow.[/bold yellow]\n"
            "It may include conditional branching and dependency-based execution.",
            border_style="yellow",
            expand=False
        ))
        
        # Get confirmation
        confirmed = yes_no_dialog(
            title="Confirm Advanced Plan Execution",
            text=f"Do you want to execute this {len(plan.steps)}-step advanced plan?",
        ).run()
        
        return confirmed
    

    
    async def _process_workflow_definition(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a workflow definition request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing workflow definition request: {request}")
        
        # Extract workflow information using AI
        workflow_info = await self._extract_workflow_info(request, context)
        
        if not workflow_info or "name" not in workflow_info:
            return {
                "request": request,
                "type": "workflow_definition",
                "context": context,
                "error": "Could not extract workflow information",
                "response": "I couldn't understand the workflow definition. Please provide a name and description."
            }
        
        # Define workflow
        workflow = await workflow_manager.define_workflow_from_natural_language(
            name=workflow_info["name"],
            description=workflow_info.get("description", ""),
            natural_language=workflow_info.get("steps", request),
            context=context
        )
        
        # Return result
        return {
            "request": request,
            "type": "workflow_definition",
            "context": context,
            "workflow": {
                "name": workflow.name,
                "description": workflow.description,
                "steps": [
                    {
                        "command": step.command,
                        "explanation": step.explanation,
                        "optional": step.optional,
                        "requires_confirmation": step.requires_confirmation
                    }
                    for step in workflow.steps
                ],
                "variables": workflow.variables,
                "step_count": len(workflow.steps)
            },
            "success": True,
            "response": f"Successfully defined workflow '{workflow.name}' with {len(workflow.steps)} steps."
        }
    
    async def _process_workflow_execution(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a workflow execution request.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the workflow
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing workflow execution request: {request}")
        
        # Extract workflow name and variables using AI
        workflow_execution_info = await self._extract_workflow_execution_info(request, context)
        
        if not workflow_execution_info or "name" not in workflow_execution_info:
            return {
                "request": request,
                "type": "workflow_execution",
                "context": context,
                "error": "Could not determine workflow name",
                "response": "I couldn't determine which workflow to run. Please specify the workflow name."
            }
        
        workflow_name = workflow_execution_info["name"]
        variables = workflow_execution_info.get("variables", {})
        
        # Check if workflow exists
        workflow = workflow_manager.get_workflow(workflow_name)
        if not workflow:
            available_workflows = workflow_manager.list_workflows()
            if available_workflows:
                workflow_list = ", ".join([w.name for w in available_workflows])
                return {
                    "request": request,
                    "type": "workflow_execution",
                    "context": context,
                    "error": f"Workflow '{workflow_name}' not found",
                    "response": f"Workflow '{workflow_name}' not found. Available workflows: {workflow_list}"
                }
            else:
                return {
                    "request": request,
                    "type": "workflow_execution",
                    "context": context,
                    "error": "No workflows defined",
                    "response": "No workflows have been defined yet. Use 'define workflow' to create one."
                }
        
        result = {
            "request": request,
            "type": "workflow_execution",
            "context": context,
            "workflow": {
                "name": workflow.name,
                "description": workflow.description,
                "steps": [
                    {
                        "command": step.command,
                        "explanation": step.explanation,
                        "optional": step.optional,
                        "requires_confirmation": step.requires_confirmation
                    }
                    for step in workflow.steps
                ],
                "variables": variables,
                "step_count": len(workflow.steps)
            }
        }
        
        # Execute the workflow if requested
        if execute or dry_run:
            # Display workflow with rich formatting
            await self._display_workflow(workflow, variables)
            
            # Get confirmation
            confirmed = await self._confirm_workflow_execution(workflow, variables, dry_run)
            
            if confirmed or dry_run:
                # Execute workflow
                execution_result = await workflow_manager.execute_workflow(
                    workflow_name=workflow_name,
                    variables=variables,
                    context=context,
                    dry_run=dry_run
                )
                
                result["execution_result"] = execution_result
                result["success"] = execution_result.get("success", False)
            else:
                result["cancelled"] = True
                result["success"] = False
        
        return result
    
    async def _process_clarification_request(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a request for clarification.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with processing results
        """
        # Get session context for previous commands
        session = session_manager.get_context()
        recent_commands = session.get("recent_commands", [])
        
        # Build prompt for clarification
        prompt = f"""
You are Angela, an AI terminal assistant. The user is asking for clarification regarding a previous interaction.

Recent commands:
{recent_commands}

User request: {request}

Provide a helpful clarification or explanation about the recent commands or operations. Be concise but thorough.
If the user is asking about how to do something, explain the appropriate command or procedure.
"""
        
        # Call AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=2000)
        response = await gemini_client.generate_text(api_request)
        
        return {
            "request": request,
            "type": "clarification",
            "context": context,
            "response": response.text
        }
    
    async def _process_unknown_request(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an unknown request type.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with processing results
        """
        # Try to get a general response from the AI
        prompt = f"""
You are Angela, an AI terminal assistant. The user has made a request that doesn't clearly match a command, multi-step operation, file manipulation, or workflow.

User request: {request}

Provide a helpful response. If appropriate, suggest what kinds of commands or operations might help with what they're trying to do.
Keep your response concise and focused.
"""
        
        # Call AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=2000)
        response = await gemini_client.generate_text(api_request)
        
        return {
            "request": request,
            "type": "unknown",
            "context": context,
            "response": response.text
        }
    
    async def _get_ai_suggestion(
        self, 
        request: str, 
        context: Dict[str, Any],
        similar_command: Optional[str] = None,
        intent_result: Optional[Any] = None
    ) -> CommandSuggestion:
        """Get a command suggestion from the AI service."""
        # Build prompt with context, including session context if available
        prompt = build_prompt(request, context, similar_command, intent_result)
        
        # Create a request to the Gemini API
        api_request = GeminiRequest(prompt=prompt)
        
        # Call the Gemini API
        self._logger.info("Sending request to Gemini API")
        api_response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        suggestion = parse_ai_response(api_response.text)
        
        self._logger.info(f"Received suggestion: {suggestion.command}")
        return suggestion
    
    async def _extract_file_path(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Extract a file path from a request using file_resolver.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Path object if found, None otherwise
        """
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
        # [Existing AI extraction code]
        return None
    
    async def _determine_file_operation_type(self, request: str) -> str:
        """
        Determine the type of file operation requested.
        
        Args:
            request: The user request
            
        Returns:
            String indicating the operation type: "analyze", "summarize", "search", or "manipulate"
        """
        # Check for keywords indicating different operation types
        
        # Manipulation keywords
        manipulation_keywords = [
            "change", "modify", "update", "edit", "replace", "rename", "refactor",
            "convert", "transform", "add", "remove", "delete", "fix"
        ]
        
        # Analysis keywords
        analysis_keywords = [
            "analyze", "explain", "understand", "evaluate", "assess", "examine",
            "review", "check", "audit"
        ]
        
        # Summarization keywords
        summarization_keywords = [
            "summarize", "summary", "overview", "brief", "digress", "gist"
        ]
        
        # Search keywords
        search_keywords = [
            "find", "search", "locate", "grep", "look for", "identify", "pinpoint"
        ]
        
        # Normalize request text
        normalized = request.lower()
        
        # Check for each type of operation
        for keyword in manipulation_keywords:
            if keyword in normalized:
                return "manipulate"
        
        for keyword in summarization_keywords:
            if keyword in normalized:
                return "summarize"
        
        for keyword in search_keywords:
            if keyword in normalized:
                return "search"
        
        # Default to analysis
        return "analyze"
    
    async def _extract_workflow_info(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract workflow information from a request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with workflow name, description, and steps
        """
        prompt = f"""
Extract information about a workflow definition from this user request:
"{request}"

Return a JSON object with:
1. name: The workflow name
2. description: A brief description of what the workflow does
3. steps: The sequence of steps or commands to include in the workflow

Format:
{{
  "name": "workflow_name",
  "description": "What this workflow does",
  "steps": "Detailed description of steps"
}}

Include only the JSON object with no additional text.
"""
        
        api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract JSON from the response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            workflow_info = json.loads(json_str)
            return workflow_info
            
        except Exception as e:
            self._logger.error(f"Error extracting workflow info: {str(e)}")
            return {}
    
    async def _extract_workflow_execution_info(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract workflow execution information from a request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with workflow name and variables
        """
        # Get list of available workflows
        available_workflows = workflow_manager.list_workflows()
        workflow_names = [w.name for w in available_workflows]
        
        prompt = f"""
Extract information about a workflow execution from this user request:
"{request}"

Available workflows: {", ".join(workflow_names) if workflow_names else "None"}

Return a JSON object with:
1. name: The workflow name to execute
2. variables: Any variable values to use (as key-value pairs)

Format:
{{
  "name": "workflow_name",
  "variables": {{
    "var1": "value1",
    "var2": "value2"
  }}
}}

Include only the JSON object with no additional text.
"""
        
        api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract JSON from the response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            execution_info = json.loads(json_str)
            return execution_info
            
        except Exception as e:
            self._logger.error(f"Error extracting workflow execution info: {str(e)}")
            return {}
    
    async def _display_plan(self, plan: Any) -> None:
        """
        Display a task plan with rich formatting.
        
        Args:
            plan: The task plan to display
        """
        # Use the terminal formatter to display the plan
        from angela.shell.formatter import terminal_formatter
        await terminal_formatter.display_task_plan(plan)
    
    async def _confirm_plan_execution(self, plan: Any, dry_run: bool) -> bool:
        """
        Get confirmation to execute a plan.
        
        Args:
            plan: The task plan to execute
            dry_run: Whether this is a dry run
            
        Returns:
            True if confirmed, False otherwise
        """
        if dry_run:
            # No confirmation needed for dry run
            return True
        
        # Check if any steps are high risk
        has_high_risk = any(step.estimated_risk >= 3 for step in plan.steps)
        
        # Import here to avoid circular imports
        from rich.console import Console
        from prompt_toolkit.shortcuts import yes_no_dialog
        
        console = Console()
        
        if has_high_risk:
            # Use a more prominent warning for high-risk plans
            console.print(Panel(
                "⚠️  [bold red]This plan includes HIGH RISK operations[/bold red] ⚠️\n"
                "Some of these steps could make significant changes to your system.",
                border_style="red",
                expand=False
            ))
        
        # Get confirmation
        confirmed = yes_no_dialog(
            title="Confirm Plan Execution",
            text=f"Do you want to execute this {len(plan.steps)}-step plan?",
        ).run()
        
        return confirmed
    
    async def _display_workflow(self, workflow: Any, variables: Dict[str, Any]) -> None:
        """
        Display a workflow with rich formatting.
        
        Args:
            workflow: The workflow to display
            variables: Variables for the workflow
        """
        # Import here to avoid circular imports
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.syntax import Syntax
        
        console = Console()
        
        # Create a table for the workflow steps
        table = Table(title=f"Workflow: {workflow.name}")
        table.add_column("#", style="cyan")
        table.add_column("Command", style="green")
        table.add_column("Explanation", style="white")
        table.add_column("Options", style="yellow")
        
        # Add steps to the table
        for i, step in enumerate(workflow.steps):
            # Apply variable substitution
            command = step.command
            for var_name, var_value in variables.items():
                # Remove leading $ if present
                clean_name = var_name[1:] if var_name.startswith('$') else var_name
                
                # Substitute ${VAR} syntax
                command = command.replace(f"${{{clean_name}}}", str(var_value))
                
                # Substitute $VAR syntax
                command = command.replace(f"${clean_name}", str(var_value))
            
            options = []
            if step.optional:
                options.append("Optional")
            if step.requires_confirmation:
                options.append("Requires Confirmation")
            
            table.add_row(
                str(i + 1),
                Syntax(command, "bash", theme="monokai", word_wrap=True).markup,
                step.explanation,
                ", ".join(options) if options else ""
            )
        
        # Display the table
        console.print("\n")
        console.print(Panel(
            workflow.description,
            title=f"Workflow: {workflow.name}",
            border_style="blue"
        ))
        console.print(table)
        
        # Display variables if any
        if variables:
            var_table = Table(title="Variables")
            var_table.add_column("Name", style="cyan")
            var_table.add_column("Value", style="green")
            
            for var_name, var_value in variables.items():
                var_table.add_row(var_name, str(var_value))
            
            console.print(var_table)
    
    async def _confirm_workflow_execution(
        self, 
        workflow: Any, 
        variables: Dict[str, Any], 
        dry_run: bool
    ) -> bool:
        """
        Get confirmation to execute a workflow.
        
        Args:
            workflow: The workflow to execute
            variables: Variables for the workflow
            dry_run: Whether this is a dry run
            
        Returns:
            True if confirmed, False otherwise
        """
        if dry_run:
            # No confirmation needed for dry run
            return True
        
        # Check if any steps require confirmation
        requires_confirmation = any(step.requires_confirmation for step in workflow.steps)
        
        # Import here to avoid circular imports
        from rich.console import Console
        from prompt_toolkit.shortcuts import yes_no_dialog
        
        console = Console()
        
        if requires_confirmation:
            # Use a more prominent warning for confirmation-required workflows
            console.print(Panel(
                "⚠️  [bold yellow]This workflow includes steps that require confirmation[/bold yellow] ⚠️\n"
                "Some of these steps could make significant changes.",
                border_style="yellow",
                expand=False
            ))
        
        # Get confirmation
        confirmed = yes_no_dialog(
            title="Confirm Workflow Execution",
            text=f"Do you want to execute workflow '{workflow.name}' with {len(workflow.steps)} steps?",
        ).run()
        
        return confirmed
    
    async def _confirm_file_changes(self, file_path: Path, diff: str) -> bool:
        """
        Get confirmation for file changes.
        
        Args:
            file_path: Path to the file being changed
            diff: Unified diff of the changes
            
        Returns:
            True if confirmed, False otherwise
        """
        # Import here to avoid circular imports
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        from prompt_toolkit.shortcuts import yes_no_dialog
        
        console = Console()
        
        # Display the diff
        console.print("\n")
        console.print(Panel(
            f"Proposed changes to {file_path}:",
            title="File Changes",
            border_style="yellow"
        ))
        console.print(Syntax(diff, "diff", theme="monokai"))
        
        # Get confirmation
        confirmed = yes_no_dialog(
            title="Confirm File Changes",
            text=f"Do you want to apply these changes to {file_path}?",
        ).run()
        
        return confirmed
    
    def _start_background_monitoring(self, command: str, error_analysis: Dict[str, Any]) -> None:
        """
        Start background monitoring for a failed command.
        
        Args:
            command: The failed command
            error_analysis: Analysis of the error
        """
        # Create and start a background task
        task = asyncio.create_task(
            self._monitor_for_suggestions(command, error_analysis)
        )
        
        # Add the task to our set of background tasks
        self._background_tasks.add(task)
        # Remove the task when it's done
        task.add_done_callback(self._background_tasks.discard)
    
    async def _monitor_for_suggestions(self, command: str, error_analysis: Dict[str, Any]) -> None:
        """
        Monitor and provide suggestions for a failed command.
        
        Args:
            command: The failed command
            error_analysis: Analysis of the error
        """
        # Wait a short time before offering suggestions
        await asyncio.sleep(2)
        
        # Import here to avoid circular imports
        from rich.console import Console
        
        console = Console()
        
        # Generate potential fix suggestions
        suggestions = []
        
        # Add suggestions from error analysis
        if "fix_suggestions" in error_analysis:
            suggestions.extend(error_analysis["fix_suggestions"])
        
        # Add historical fixes if available
        if "historical_fixes" in error_analysis:
            suggestions.extend(error_analysis["historical_fixes"])
        
        # If we have suggestions, offer them
        if suggestions:
            console.print("\n")
            console.print("[bold blue]Suggestion:[/bold blue] Try one of these commands to fix the issue:")
            
            for i, suggestion in enumerate(suggestions[:3], 1):  # Limit to top 3
                console.print(f"  {i}. {suggestion}")
            
            console.print("\nUse 'angela try fix 1' to execute the first suggestion, etc.")
    
    async def process_file_operation(
        self, 
        operation: str, 
        parameters: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Process a file operation request.
        
        Args:
            operation: The type of file operation (e.g., 'create_file', 'read_file').
            parameters: Parameters for the operation.
            dry_run: Whether to simulate the operation without making changes.
            
        Returns:
            A dictionary with the operation results.
        """
        # Execute the file operation
        return await execute_file_operation(operation, parameters, dry_run=dry_run)


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
        
        return resul



# Global orchestrator instance
orchestrator = Orchestrator()

# Synchronous wrapper for backwards compatibility
def process_request(request: str) -> Dict[str, Any]:
    """Synchronous wrapper for processing a request."""
    return asyncio.run(orchestrator.process_request(request))
