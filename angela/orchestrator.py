# angela/orchestrator.py
"""
Main orchestration service for Angela CLI.

This module coordinates all the components of Angela CLI, from receiving
user requests to executing commands with safety checks.
"""
import asyncio
import re
import shlex
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from enum import Enum
import uuid
from rich.console import Console
from datetime import datetime
from rich.panel import Panel

# Use API imports to avoid circular dependencies
from angela.api.ai import get_gemini_client, get_gemini_request_class, get_parse_ai_response_func
from angela.api.ai import get_build_prompt_func, get_error_analyzer, get_content_analyzer, get_intent_analyzer
from angela.api.ai import get_confidence_scorer
from angela.api.context import get_context_manager, get_session_manager, get_history_manager, get_file_resolver
from angela.api.context import get_file_activity_tracker, get_activity_type, get_context_enhancer
from angela.api.execution import get_execution_engine, get_adaptive_engine, get_rollback_manager, get_execution_hooks
from angela.api.intent import get_task_planner, get_plan_model_classes
from angela.api.workflows import get_workflow_manager
from angela.api.shell import get_terminal_formatter, get_output_type_enum, get_advanced_formatter
from angela.api.monitoring import get_background_monitor, get_network_monitor
from angela.api.safety import get_command_risk_classifier, get_adaptive_confirmation
from angela.api.toolchain import get_docker_integration

# Get the core models and classes
from angela.utils.logging import get_logger

# Import execution modules via api to avoid circular imports
from angela.api.execution import get_execution_engine, get_adaptive_engine
execution_engine = get_execution_engine()
adaptive_engine = get_adaptive_engine()

# Import other required components
GeminiRequest = get_gemini_request_class()
parse_ai_response = get_parse_ai_response_func()
build_prompt = get_build_prompt_func()
context_manager = get_context_manager()
session_manager = get_session_manager()
history_manager = get_history_manager()
error_analyzer = get_error_analyzer()
intent_analyzer = get_intent_analyzer() 
confidence_scorer = get_confidence_scorer()
task_planner = get_task_planner()
workflow_manager = get_workflow_manager()
file_resolver = get_file_resolver()
file_activity_tracker = get_file_activity_tracker()
ActivityType = get_activity_type()
terminal_formatter = get_terminal_formatter()
OutputType = get_output_type_enum()
rollback_manager = get_rollback_manager()
execution_hooks = get_execution_hooks()
background_monitor = get_background_monitor()
network_monitor = get_network_monitor()
content_analyzer = get_content_analyzer()
context_enhancer = get_context_enhancer()
gemini_client = get_gemini_client()

# Get classification and confirmation from API
classify_command_risk = get_command_risk_classifier().classify
analyze_command_impact = get_command_risk_classifier().analyze_impact
get_adaptive_confirmation = get_adaptive_confirmation()

# Get Docker integration
docker_integration = get_docker_integration()

# Get necessary plan model classes
AdvancedTaskPlan, TaskPlan = get_plan_model_classes()[3:5]

logger = get_logger(__name__)

console = Console()


class RequestType(Enum):
    """Types of requests that can be handled by the orchestrator."""
    COMMAND = "command"                # Single command suggestion
    MULTI_STEP = "multi_step"          # Multi-step operation
    FILE_CONTENT = "file_content"      # File content analysis/manipulation
    WORKFLOW_DEFINITION = "workflow"   # Define a new workflow
    WORKFLOW_EXECUTION = "run_workflow" # Execute a workflow
    CLARIFICATION = "clarification"    # Request for clarification
    CODE_GENERATION = "code_generation" # Generate a complete project
    FEATURE_ADDITION = "feature_addition" # Add feature to existing project
    TOOLCHAIN_OPERATION = "toolchain_operation" # DevOps operations (CI/CD, etc.)
    CODE_REFINEMENT = "code_refinement" # Refine/improve existing code
    CODE_ARCHITECTURE = "code_architecture" # Analyze or enhance architecture
    UNKNOWN = "unknown"                # Unknown request type
    UNIVERSAL_CLI = "universal_cli"  # Request to use the Universal CLI Translator
    COMPLEX_WORKFLOW = "complex_workflow"  # Complex workflow involving multiple tools
    CI_CD_PIPELINE = "ci_cd_pipeline"  # CI/CD pipeline setup and execution
    PROACTIVE_SUGGESTION = "proactive_suggestion"    
        
class Orchestrator:
    """Main orchestration service for Angela CLI."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        self._logger = logger
        self._background_tasks = set()
        self._background_monitor = background_monitor
        self._network_monitor = network_monitor
        
        # Register the monitoring insight callback
        self._background_monitor.register_insight_callback(self._handle_monitoring_insight)
        
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
        error_recovery_manager = self._get_error_recovery_manager()
            
        # Refresh context to ensure we have the latest information
        context_manager.refresh_context()
        context = context_manager.get_context_dict()
        
        # Add session context for continuity across requests
        session_context = session_manager.get_context()
        context["session"] = session_context
        
        # Enhance context with project information, dependencies, and recent activity
        try:
            # Get context enhancer from registry
            context_enhancer = registry.get("context_enhancer")
            
            if context_enhancer:
                # If available in registry, use it
                context = await context_enhancer.enrich_context(context)
            else:
                # If not in registry, try direct import as fallback
                self._logger.warning("context_enhancer not found in registry, attempting direct import")
                try:
                    from angela.context.enhancer import context_enhancer
                    if context_enhancer:
                        # Register for future use
                        registry.register("context_enhancer", context_enhancer)
                        context = await context_enhancer.enrich_context(context)
                    else:
                        self._logger.warning("context_enhancer is None after direct import, attempting to create instance")
                        try:
                            from angela.context.enhancer import ContextEnhancer
                            temp_enhancer = ContextEnhancer()
                            registry.register("context_enhancer", temp_enhancer)
                            context = await temp_enhancer.enrich_context(context)
                            self._logger.info("Successfully created and used temporary context_enhancer")
                        except Exception as create_error:
                            self._logger.error(f"Failed to create context_enhancer instance: {create_error}")
                            self._logger.warning("Continuing with basic context")
                except ImportError as e:
                    self._logger.error(f"Failed to import context_enhancer directly: {e}")
                    self._logger.warning("Continuing with basic context")
        except Exception as e:
            self._logger.error(f"Error during context enhancement: {str(e)}")
            self._logger.warning("Continuing with unenriched context")
        
        self._logger.info(f"Processing request: {request}")
        self._logger.debug(f"Context contains {len(context)} keys")
        
        # Perform quick intent analysis to determine if we should extract file references
        request_intent = self._analyze_quick_intent(request)
        
        # Only extract file references for certain intents
        if request_intent in ["read", "modify", "analyze", "unknown"]:
            # Extract and resolve file references
            file_references = await file_resolver.extract_references(request, context)
            if file_references:
                # Add resolved file references to context
                context["resolved_files"] = [
                    {"reference": ref, "path": str(path) if path else None}
                    for ref, path in file_references
                ]
                self._logger.debug(f"Resolved {len(file_references)} file references")
        else:
            self._logger.debug(f"Skipping file resolution for {request_intent} intent")
        
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
                
            elif request_type == RequestType.CODE_GENERATION:
                return await self._process_code_generation_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.FEATURE_ADDITION:
                return await self._process_feature_addition_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.TOOLCHAIN_OPERATION:
                return await self._process_toolchain_operation(request, context, execute, dry_run)
                
            elif request_type == RequestType.CODE_REFINEMENT:
                return await self._process_code_refinement_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.CODE_ARCHITECTURE:
                return await self._process_code_architecture_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.UNIVERSAL_CLI:
                return await self._process_universal_cli_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.COMPLEX_WORKFLOW:
                return await self._process_complex_workflow_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.CI_CD_PIPELINE:
                return await self._process_ci_cd_pipeline_request(request, context, execute, dry_run)
                
            elif request_type == RequestType.PROACTIVE_SUGGESTION:
                return await self._process_proactive_suggestion(request, context)
                
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
     
            # Docker operation patterns
            docker_patterns = [
                r'\bdocker\b',
                r'\bcontainer\b',
                r'\bdockerfile\b',
                r'\bdocker-compose\b',
                r'\bdocker\s+compose\b',
                r'\bimage\b.+\b(?:build|run|pull|push)\b',
                r'\b(?:build|run|pull|push)\b.+\bimage\b',
                r'\b(?:start|stop|restart|remove)\b.+\bcontainer\b',
                r'\bcontainer\b.+\b(?:start|stop|restart|remove)\b',
                r'\bgenerate\b.+\b(?:dockerfile|docker-compose)\b',
                r'\bsetup\s+docker\b',
                r'\bdocker\s+(?:ps|logs|images|rmi|exec)\b',
            ]
    
            code_generation_patterns = [
                r'\bcreate\s+(?:a\s+)?(?:new\s+)?(?:project|app|website|application)\b',
                r'\bgenerate\s+(?:a\s+)?(?:new\s+)?(?:project|app|website|application)\b',
                r'\bmake\s+(?:a\s+)?(?:new\s+)?(?:project|app|website|application)\b',
                r'\bbuild\s+(?:a\s+)?(?:whole|complete|full|entire)\b',
            ]
            
            # Feature addition patterns
            feature_addition_patterns = [
                r'\badd\s+(?:a\s+)?(?:new\s+)?feature\b',
                r'\bimplement\s+(?:a\s+)?(?:new\s+)?feature\b',
                r'\bcreate\s+(?:a\s+)?(?:new\s+)?feature\b',
                r'\bextend\s+(?:the\s+)?(?:project|app|code|application)\b',
            ]
            
            # Toolchain operation patterns
            toolchain_patterns = [
                r'\bsetup\s+(?:ci|cd|ci/cd|cicd|continuous integration|deployment)\b',
                r'\bconfigure\s+(?:ci|cd|ci/cd|cicd|continuous integration|deployment|git)\b',
                r'\bgenerate\s+(?:ci|cd|jenkins|gitlab|github)\b',
                r'\binstall\s+dependencies\b',
                r'\binitialize\s+(?:git|repo|repository)\b',
            ]
            
            # Code refinement patterns
            refinement_patterns = [
                r'\brefine\s+(?:the\s+)?code\b',
                r'\bimprove\s+(?:the\s+)?code\b',
                r'\boptimize\s+(?:the\s+)?code\b',
                r'\brefactor\s+(?:the\s+)?code\b',
                r'\bupdate\s+(?:the\s+)?code\b',
                r'\benhance\s+(?:the\s+)?code\b',
            ]
            
            # Architecture patterns
            architecture_patterns = [
                r'\banalyze\s+(?:the\s+)?(?:architecture|structure)\b',
                r'\bimprove\s+(?:the\s+)?(?:architecture|structure)\b',
                r'\bredesign\s+(?:the\s+)?(?:architecture|structure)\b',
                r'\bproject\s+structure\b',
            ]
    
            # CI/CD patterns
            ci_cd_patterns = [
                r'\bset\s*up\s+(?:a\s+)?(?:ci|cd|ci/cd|cicd|continuous integration|deployment)(?:\s+pipeline)?\b',
                r'\bcreate\s+(?:a\s+)?(?:ci|cd|ci/cd|cicd|continuous integration)(?:\s+pipeline)?\b',
                r'\bci/cd\s+(?:pipeline|setup|configuration)\b',
                r'\bpipeline\s+(?:setup|configuration|for)\b',
                r'\bgithub\s+actions\b',
                r'\bgitlab\s+ci\b',
                r'\bjenkins(?:file)?\b',
                r'\btravis\s+ci\b',
                r'\bcircle\s+ci\b',
                r'\b(?:automate|automation)\s+(?:build|test|deploy)\b',
            ]
            
            # First check for CI/CD patterns since they're more specific
            for pattern in ci_cd_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CI_CD_PIPELINE
            
            # Then check for Universal CLI patterns
            universal_cli_patterns = [
                r'\buse\s+(?:the\s+)?(.+?)\s+(?:cli|command|tool)\b',
                r'\brun\s+(?:a\s+)?(.+?)\s+command\b',
                r'\b(?:execute|with)\s+(?:the\s+)?(.+?)\s+tool\b',
            ]
            
            for pattern in universal_cli_patterns:
                match = re.search(pattern, request, re.IGNORECASE)
                if match:
                    tool = match.group(1).strip().lower()
                    if tool not in ["angela", "workflow"]:  # Exclude Angela's own commands
                        return RequestType.UNIVERSAL_CLI
            
            # Check for complex workflow patterns
            complex_workflow_patterns = [
                r'\bcomplex\s+workflow\b',
                r'\bcomplete\s+(?:ci/cd|cicd|pipeline)\b',
                r'\bautomated\s+(?:build|test|deploy)\b',
                r'\bend-to-end\s+workflow\b',
                r'\bchain\s+of\s+commands\b',
                r'\bmulti-step\s+operation\s+across\b',
                r'\bpipeline\s+using\b',
                r'\bseries\s+of\s+tools\b',
            ]
            
            for pattern in complex_workflow_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.COMPLEX_WORKFLOW
            
            # Check for common CLI tools explicitly mentioned
            common_tools = ["git", "docker", "aws", "kubectl", "terraform", "npm", "pip", "yarn"]
            tool_words = request.lower().split()
            for tool in common_tools:
                if tool in tool_words:
                    # Make sure it's a standalone word, not part of another word
                    # Check the positions where the tool appears
                    positions = [i for i, word in enumerate(tool_words) if word == tool]
                    for pos in positions:
                        # Check if it's a command (usually preceded by use, run, with, etc.)
                        if pos > 0 and tool_words[pos-1] in ["use", "run", "with", "using", "execute"]:
                            return RequestType.UNIVERSAL_CLI
                    
                    # If tool is the first word in the request, it's likely a direct usage
                    if tool_words[0] == tool:
                        return RequestType.UNIVERSAL_CLI
            
            # Also check for complexity indicators combined with multiple tool mentions
            tool_mentions = sum(1 for tool in ["git", "docker", "aws", "kubernetes", "npm", "pip"] 
                               if tool in request.lower())
            has_complex_indicators = any(indicator in request.lower() for indicator in 
                                       ["pipeline", "sequence", "then", "after", "followed"])
        
            if tool_mentions >= 2 and has_complex_indicators:
                return RequestType.COMPLEX_WORKFLOW
    
            # Check for code generation first (highest priority)
            for pattern in code_generation_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CODE_GENERATION
            
            # Check for feature addition
            for pattern in feature_addition_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.FEATURE_ADDITION
            
            # Check for toolchain operations
            for pattern in toolchain_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.TOOLCHAIN_OPERATION
            
            # Check for code refinement
            for pattern in refinement_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CODE_REFINEMENT
            
            # Check for architecture analysis
            for pattern in architecture_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CODE_ARCHITECTURE
     
            # Check for workflow definition
            for pattern in workflow_def_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.WORKFLOW_DEFINITION
            
            # Check for workflow execution
            for pattern in workflow_exec_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.WORKFLOW_EXECUTION
    
            # Check for Docker operations first
            for pattern in docker_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.TOOLCHAIN_OPERATION
    
            # Check for code generation (high priority)
            for pattern in code_generation_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CODE_GENERATION
            
            # Check for feature addition
            for pattern in feature_addition_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.FEATURE_ADDITION
            
            # Check for toolchain operations
            for pattern in toolchain_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.TOOLCHAIN_OPERATION
            
            # Check for code refinement
            for pattern in refinement_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CODE_REFINEMENT
            
            # Check for architecture analysis
            for pattern in architecture_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.CODE_ARCHITECTURE
    
            for pattern in complex_workflow_patterns:
                if re.search(pattern, request, re.IGNORECASE):
                    return RequestType.COMPLEX_WORKFLOW
                    
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


    def _analyze_quick_intent(self, request: str) -> str:
        """
        Perform a quick analysis of request intent to determine if file resolution is needed.
        
        Args:
            request: The user request
            
        Returns:
            String indicating the high-level intent: "create", "read", "modify", "analyze", "unknown"
        """
        request_lower = request.lower()
        
        # Check for file creation keywords
        creation_keywords = [
            "create", "generate", "make", "new file", "save as", 
            "write a new", "write new", "save it as", "output to"
        ]
        for keyword in creation_keywords:
            if keyword in request_lower:
                return "create"
        
        # Check for file reading keywords
        read_keywords = [
            "read", "open", "show", "display", "view", "cat", 
            "print", "output", "list", "contents of"
        ]
        for keyword in read_keywords:
            if keyword in request_lower:
                return "read"
        
        # Check for file modification keywords
        modify_keywords = [
            "edit", "modify", "update", "change", "replace", "delete",
            "remove", "rename", "move", "copy"
        ]
        for keyword in modify_keywords:
            if keyword in request_lower:
                return "modify"
        
        # Check for analysis keywords
        analyze_keywords = [
            "analyze", "examine", "check", "inspect", "review",
            "summarize", "understand", "evaluate"
        ]
        for keyword in analyze_keywords:
            if keyword in request_lower:
                return "analyze"
        
        # Default case
        return "unknown"

    async def _process_code_generation_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a code generation request.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the generation
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing code generation request: {request}")
        
        # Import here to avoid circular imports
        from angela.generation.engine import code_generation_engine
        
        # Project details extraction
        project_details = await self._extract_project_details(request)
        
        # Get output directory (default to current dir)
        output_dir = project_details.get("output_dir", context.get("cwd", "."))
        
        # Get project type if specified
        project_type = project_details.get("project_type")
        
        # Create result structure
        result = {
            "request": request,
            "type": "code_generation",
            "context": context,
            "project_details": project_details
        }
        
        # Skip execution if not requested
        if not execute and not dry_run:
            return result
        
        try:
            # Generate the project using the generation engine
            with console.status(f"[bold green]Generating project based on: {request}[/bold green]"):
                project_plan = await code_generation_engine.generate_project(
                    description=request,  # Use full request as description
                    output_dir=output_dir,
                    project_type=project_type,
                    context=context
                )
            
            # Add project plan to result
            result["project_plan"] = {
                "name": project_plan.name,
                "description": project_plan.description,
                "project_type": project_plan.project_type,
                "file_count": len(project_plan.files),
                "structure_explanation": project_plan.structure_explanation
            }
            
            # Create files if not in dry run mode
            if not dry_run:
                with console.status("[bold green]Creating project files...[/bold green]"):
                    creation_result = await code_generation_engine.create_project_files(project_plan)
                    result["creation_result"] = creation_result
                    result["success"] = creation_result.get("success", False)
            else:
                result["dry_run"] = True
                result["success"] = True
                
            # Add Git initialization if appropriate
            if not dry_run and project_details.get("git_init", True):
                from angela.toolchain.git import git_integration
                
                with console.status("[bold green]Initializing Git repository...[/bold green]"):
                    git_result = await git_integration.init_repository(
                        path=output_dir,
                        initial_branch="main",
                        gitignore_template=project_plan.project_type
                    )
                    result["git_result"] = git_result
            
            return result
        except Exception as e:
            self._logger.exception(f"Error in code generation: {str(e)}")
            result["error"] = str(e)
            result["success"] = False
            return result

    async def _process_feature_addition_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a feature addition request.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the feature addition
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing feature addition request: {request}")
        
        # Import here to avoid circular imports
        from angela.generation.engine import code_generation_engine
        
        # Extract feature details
        feature_details = await self._extract_feature_details(request, context)
        
        # Get project directory (default to current dir)
        project_dir = feature_details.get("project_dir", context.get("cwd", "."))
        
        # Create result structure
        result = {
            "request": request,
            "type": "feature_addition",
            "context": context,
            "feature_details": feature_details
        }
        
        # Skip execution if not requested
        if not execute and not dry_run:
            return result
        
        # Add the feature to the project
        with console.status(f"[bold green]Adding feature to project: {request}[/bold green]"):
            addition_result = await code_generation_engine.add_feature_to_project(
                description=feature_details.get("description", request),
                project_dir=project_dir,
                context=context
            )
        
        result["addition_result"] = addition_result
        
        # Create branch if specified and not in dry run mode
        if not dry_run and feature_details.get("branch"):
            from angela.toolchain.git import git_integration
            
            branch_name = feature_details.get("branch")
            with console.status(f"[bold green]Creating branch: {branch_name}[/bold green]"):
                branch_result = await git_integration.create_branch(
                    path=project_dir,
                    branch_name=branch_name,
                    checkout=True
                )
                result["branch_result"] = branch_result
        
        return result



    async def _process_toolchain_operation(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a toolchain operation request.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the operation
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing toolchain operation request: {request}")
        
        # Extract operation details
        operation_details = await self._extract_toolchain_operation(request, context)
        
        # Get operation type
        operation_type = operation_details.get("operation_type", "unknown")
        
        # Create result structure
        result = {
            "request": request,
            "type": "toolchain_operation",
            "context": context,
            "operation_details": operation_details,
            "operation_type": operation_type
        }
        
        # Skip execution if not requested
        if not execute and not dry_run:
            return result
        
        # Process based on operation type
        if operation_type == "docker":
            result.update(await self._process_docker_operation(request, operation_details, context, dry_run))
        elif operation_type == "ci_cd":
            result.update(await self._process_ci_cd_operation(operation_details, context, dry_run))
        elif operation_type == "package_management":
            result.update(await self._process_package_operation(operation_details, context, dry_run))
        elif operation_type == "git":
            result.update(await self._process_git_operation(operation_details, context, dry_run))
        elif operation_type == "testing":
            result.update(await self._process_testing_operation(operation_details, context, dry_run))
        else:
            result["error"] = f"Unknown toolchain operation type: {operation_type}"
        
        return result
        
    async def _process_docker_operation(
        self,
        request: str,
        operation_details: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a Docker operation request.
        
        Args:
            request: The user request
            operation_details: Details about the operation
            context: Context information
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing Docker operation: {request}")
        
        # Get docker_integration from registry
        docker_integration = registry.get("docker_integration")
        if not docker_integration:
            return {
                "success": False,
                "error": "Docker integration not available in the system."
            }
            
        # Check Docker availability
        docker_available = await docker_integration.is_docker_available()
        if not docker_available:
            return {
                "success": False,
                "error": "Docker is not available on this system. Please install Docker to use this feature."
            }
            
        # Determine specific Docker operation
        docker_action = operation_details.get("docker_action", "")
        
        # Handle different Docker operations
        if "setup" in request.lower() or "generate" in request.lower() or "dockerfile" in request.lower() or "docker-compose" in request.lower():
            # Generate Docker configuration files
            project_dir = operation_details.get("project_dir", context.get("cwd", "."))
            
            result = await docker_integration.setup_docker_project(
                project_directory=project_dir,
                generate_dockerfile="dockerfile" in request.lower() or "setup" in request.lower(),
                generate_compose="compose" in request.lower() or "setup" in request.lower(),
                generate_dockerignore="dockerignore" in request.lower() or "setup" in request.lower(),
                overwrite=False,  # Default to safe operation
                include_databases="database" in request.lower() or "db" in request.lower(),
                build_image="build" in request.lower() and dry_run is False
            )
            
            # Format the result
            formatted_result = {
                "success": result.get("success", False),
                "message": "Docker setup completed",
                "files_generated": result.get("files_generated", []),
                "docker_details": result
            }
            
            return formatted_result
            
        elif "build" in request.lower() or "image" in request.lower():
            # Build Docker image
            project_dir = operation_details.get("project_dir", context.get("cwd", "."))
            image_tag = operation_details.get("image_tag", "app:latest")
            
            result = await docker_integration.build_image(
                context_path=project_dir,
                tag=image_tag,
                no_cache="no cache" in request.lower()
            )
            
            return {
                "success": result.get("success", False),
                "message": f"Docker image build {'completed' if result.get('success', False) else 'failed'}",
                "image_details": result
            }
            
        elif "run" in request.lower() or "start" in request.lower() or "launch" in request.lower():
            # Run Docker container
            image = operation_details.get("image", "")
            if not image:
                # Try to extract image from request
                image_match = re.search(r'(?:run|start|launch)\s+(?:container\s+)?(?:from\s+)?(\S+)(?:\s+image)?', request, re.IGNORECASE)
                if image_match:
                    image = image_match.group(1)
                else:
                    image = "app:latest"  # Default
            
            # Extract ports if mentioned
            ports = []
            ports_match = re.search(r'port[s]?\s+(\d+(?::\d+)?(?:,\s*\d+(?::\d+)?)*)', request, re.IGNORECASE)
            if ports_match:
                ports_str = ports_match.group(1)
                ports = [p.strip() for p in ports_str.split(',')]
            
            # Run container
            result = await docker_integration.run_container(
                image=image,
                ports=ports,
                detach=True,
                remove="remove" in request.lower() or "rm" in request.lower()
            )
            
            return {
                "success": result.get("success", False),
                "message": f"Docker container {'started' if result.get('success', False) else 'failed to start'}",
                "container_details": result
            }
            
        elif "compose" in request.lower() or "up" in request.lower():
            # Docker Compose operation
            project_dir = operation_details.get("project_dir", context.get("cwd", "."))
            
            # Check Docker Compose availability
            compose_available = await docker_integration.is_docker_compose_available()
            if not compose_available:
                return {
                    "success": False,
                    "error": "Docker Compose is not available on this system. Please install Docker Compose to use this feature."
                }
            
            # Determine if it's compose up or down
            if "down" in request.lower() or "stop" in request.lower():
                result = await docker_integration.compose_down(
                    project_directory=project_dir,
                    remove_volumes="volumes" in request.lower(),
                    remove_images="images" in request.lower() or "rmi" in request.lower()
                )
            else:
                # Default to compose up
                result = await docker_integration.compose_up(
                    project_directory=project_dir,
                    detach=True,
                    build="build" in request.lower()
                )
            
            return {
                "success": result.get("success", False),
                "message": f"Docker Compose operation {'completed' if result.get('success', False) else 'failed'}",
                "compose_details": result
            }
            
        else:
            # Generate and execute appropriate Docker command
            suggestion = await self._get_ai_suggestion(request, context)
            
            if not suggestion.command or not suggestion.command.startswith("docker"):
                return {
                    "success": False,
                    "error": "Unable to generate appropriate Docker command for this request.",
                    "suggestion": suggestion
                }
                
            # Execute the command using the engine
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "command": suggestion.command,
                    "explanation": suggestion.explanation
                }
                
            stdout, stderr, exit_code = await execution_engine.execute_command(
                suggestion.command,
                check_safety=True
            )
            
            return {
                "success": exit_code == 0,
                "command": suggestion.command,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": exit_code,
                "explanation": suggestion.explanation
            }
    
    async def _extract_toolchain_operation(
        self, 
        request: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract toolchain operation details from a request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with operation details
        """
        # First check if this is a Docker request
        for pattern in [r'\bdocker\b', r'\bcontainer\b', r'\bdockerfile\b', r'\bdocker-compose\b']:
            if re.search(pattern, request, re.IGNORECASE):
                docker_details = await self._extract_docker_operation_details(request, context)
                if docker_details:
                    return docker_details
        
        # Use AI to extract operation details for other toolchain operations
        prompt = f"""
    Extract toolchain operation details from this request:
    "{request}"
    
    Return a JSON object with:
    1. operation_type: One of "ci_cd", "package_management", "git", "testing", "docker"
    2. platform: For CI/CD, the platform (e.g., "github_actions", "gitlab_ci")
    3. project_dir: The project directory (default to ".")
    4. dependencies: For package management, list of dependencies
    5. test_framework: For testing, the test framework
    6. docker_action: For Docker, the specific action (e.g., "build", "run", "compose")
    7. image: For Docker run, the image name
    
    Format:
    {{
      "operation_type": "type",
      "platform": "platform",
      "project_dir": "directory",
      "dependencies": ["dep1", "dep2"],
      "test_framework": "framework"
    }}
    
    Only include keys relevant to the operation type.
    """

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
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
            details = json.loads(json_str)
            
            # Default project directory to context's project_root if available
            if "project_dir" not in details and context.get("project_root"):
                details["project_dir"] = context.get("project_root")
            
            return details
            
        except Exception as e:
            self._logger.error(f"Error extracting toolchain operation details: {str(e)}")
            # Return minimal details on failure
            return {
                "operation_type": "unknown",
                "project_dir": context.get("project_root", ".")
            }
            
    async def _extract_docker_operation_details(
        self,
        request: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract Docker operation details from a request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with Docker operation details
        """
        details = {
            "operation_type": "docker",
            "project_dir": context.get("project_root", context.get("cwd", "."))
        }
        
        # Extract Docker action based on keywords
        if re.search(r'\b(build|create)\b.+\b(image|dockerfile)\b', request, re.IGNORECASE) or re.search(r'\bimage.+\b(build|create)\b', request, re.IGNORECASE):
            details["docker_action"] = "build"
            
            # Try to extract image tag if present
            tag_match = re.search(r'tag\s+(\S+)', request, re.IGNORECASE)
            if tag_match:
                details["image_tag"] = tag_match.group(1)
            else:
                details["image_tag"] = "app:latest"
                
        elif re.search(r'\b(run|start|launch)\b.+\b(container|image)\b', request, re.IGNORECASE) or re.search(r'\b(container|image).+\b(run|start|launch)\b', request, re.IGNORECASE):
            details["docker_action"] = "run"
            
            # Try to extract image if present
            image_match = re.search(r'(image|container)\s+(\S+)', request, re.IGNORECASE)
            if image_match:
                details["image"] = image_match.group(2)
            else:
                # Look for any word that might be an image name
                words = request.split()
                for i, word in enumerate(words):
                    if word.lower() in ["image", "from"] and i < len(words) - 1:
                        details["image"] = words[i+1].strip(",:;")
                        break
            
            # Extract ports if present
            port_match = re.search(r'port\s+(\d+)', request, re.IGNORECASE)
            if port_match:
                port = port_match.group(1)
                details["ports"] = [f"{port}:{port}"]
                
        elif re.search(r'\b(setup|generate|create)\b.+\b(docker|dockerfile|compose)\b', request, re.IGNORECASE):
            details["docker_action"] = "setup"
            
            # Determine which files to generate
            details["generate_dockerfile"] = "dockerfile" in request.lower()
            details["generate_compose"] = "compose" in request.lower()
            details["generate_dockerignore"] = "ignore" in request.lower()
            
            # If not specified, generate all
            if not any([details["generate_dockerfile"], details["generate_compose"], details["generate_dockerignore"]]):
                details["generate_dockerfile"] = True
                details["generate_compose"] = True
                details["generate_dockerignore"] = True
                
        elif re.search(r'\b(compose|docker-compose)\b.+\b(up|start|run)\b', request, re.IGNORECASE):
            details["docker_action"] = "compose_up"
            
            # Extract services if mentioned
            services_match = re.search(r'service[s]?\s+(\w+(?:,\s*\w+)*)', request, re.IGNORECASE)
            if services_match:
                services_str = services_match.group(1)
                details["services"] = [s.strip() for s in services_str.split(',')]
                
        elif re.search(r'\b(compose|docker-compose)\b.+\b(down|stop)\b', request, re.IGNORECASE):
            details["docker_action"] = "compose_down"
            
            # Check for additional options
            details["remove_volumes"] = "volume" in request.lower()
            details["remove_images"] = "image" in request.lower() or "rmi" in request.lower()
            
        elif re.search(r'\b(stop|kill)\b.+\b(container)\b', request, re.IGNORECASE):
            details["docker_action"] = "stop"
            
            # Try to extract container ID or name
            container_match = re.search(r'(container|id|name)\s+(\S+)', request, re.IGNORECASE)
            if container_match:
                details["container"] = container_match.group(2)
                
        elif re.search(r'\b(rm|remove)\b.+\b(container)\b', request, re.IGNORECASE):
            details["docker_action"] = "rm"
            
            # Try to extract container ID or name
            container_match = re.search(r'(container|id|name)\s+(\S+)', request, re.IGNORECASE)
            if container_match:
                details["container"] = container_match.group(2)
                
            # Check for force flag
            details["force"] = "force" in request.lower()
            
        elif re.search(r'\b(ps|list)\b.+\b(container)', request, re.IGNORECASE):
            details["docker_action"] = "ps"
            
            # Check for all flag
            details["all"] = "all" in request.lower()
            
        elif re.search(r'\b(logs|log)\b', request, re.IGNORECASE):
            details["docker_action"] = "logs"
            
            # Try to extract container ID or name
            container_match = re.search(r'(container|id|name)\s+(\S+)', request, re.IGNORECASE)
            if container_match:
                details["container"] = container_match.group(2)
                
            # Check for follow flag
            details["follow"] = "follow" in request.lower() or "tail" in request.lower()
            
        elif re.search(r'\b(exec|execute|run)\b.+\b(command|in)\b', request, re.IGNORECASE):
            details["docker_action"] = "exec"
            
            # Try to extract container ID or name
            container_match = re.search(r'(container|id|name)\s+(\S+)', request, re.IGNORECASE)
            if container_match:
                details["container"] = container_match.group(2)
                
            # Try to extract command
            command_match = re.search(r'command\s+(.+?)$', request, re.IGNORECASE)
            if command_match:
                details["command"] = command_match.group(1)
                
        else:
            # Default to general docker action
            details["docker_action"] = "general"
            
        return details



    
    async def _process_ci_cd_operation(
        self, 
        operation_details: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a CI/CD operation request.
        
        Args:
            operation_details: Details about the operation
            context: Context information
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        # Import here to avoid circular imports
        from angela.toolchain.ci_cd import ci_cd_integration
        
        self._logger.info(f"Processing CI/CD operation: {operation_details.get('platform', 'unknown')}")
        
        # Get details
        platform = operation_details.get("platform", "github_actions")
        project_dir = operation_details.get("project_dir", context.get("cwd", "."))
        
        # Execute CI/CD operation
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Would configure CI/CD for {platform} in {project_dir}"
            }
        
        try:
            result = await ci_cd_integration.generate_ci_configuration(
                path=project_dir,
                platform=platform
            )
            
            return {
                "success": result.get("success", False),
                "message": result.get("message", "CI/CD configuration completed"),
                "ci_cd_details": result
            }
        except Exception as e:
            self._logger.exception(f"Error processing CI/CD operation: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing CI/CD operation: {str(e)}"
            }
    
    async def _process_package_operation(
        self,
        operation_details: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a package management operation request.
        
        Args:
            operation_details: Details about the operation
            context: Context information
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        # Import here to avoid circular imports
        from angela.toolchain.package_managers import package_manager_integration
        
        self._logger.info(f"Processing package operation")
        
        # Get details
        project_dir = operation_details.get("project_dir", context.get("cwd", "."))
        dependencies = operation_details.get("dependencies", [])
        dev_dependencies = operation_details.get("dev_dependencies", [])
        
        if not dependencies and not dev_dependencies:
            return {
                "success": False,
                "error": "No dependencies specified for package operation"
            }
        
        # Execute package operation
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Would install {len(dependencies)} dependencies and {len(dev_dependencies)} dev dependencies in {project_dir}"
            }
        
        try:
            result = await package_manager_integration.install_dependencies(
                path=project_dir,
                dependencies=dependencies,
                dev_dependencies=dev_dependencies
            )
            
            return {
                "success": result.get("success", False),
                "message": result.get("message", "Dependencies installed successfully"),
                "package_details": result
            }
        except Exception as e:
            self._logger.exception(f"Error processing package operation: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing package operation: {str(e)}"
            }
    
    async def _process_git_operation(
        self,
        operation_details: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a Git operation request.
        
        Args:
            operation_details: Details about the operation
            context: Context information
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        # Import here to avoid circular imports
        from angela.toolchain.git import git_integration
        
        self._logger.info(f"Processing Git operation: {operation_details.get('git_action', 'unknown')}")
        
        # Get details
        git_action = operation_details.get("git_action", "")
        project_dir = operation_details.get("project_dir", context.get("cwd", "."))
        
        # Handle different Git operations based on git_action
        if git_action == "init":
            return await self._process_git_init(operation_details, project_dir, dry_run)
        elif git_action == "commit":
            return await self._process_git_commit(operation_details, project_dir, dry_run)
        elif git_action == "branch":
            return await self._process_git_branch(operation_details, project_dir, dry_run)
        elif git_action == "status":
            return await self._process_git_status(operation_details, project_dir, dry_run)
        else:
            # Generate and execute appropriate Git command using AI
            suggestion = await self._get_ai_suggestion(
                operation_details.get("request", f"git {git_action}"),
                context
            )
            
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "command": suggestion.command,
                    "explanation": suggestion.explanation
                }
            
            # Execute the command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                suggestion.command,
                check_safety=True,
                working_dir=project_dir
            )
            
            return {
                "success": exit_code == 0,
                "command": suggestion.command,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": exit_code,
                "explanation": suggestion.explanation
            }
    
    async def _process_git_init(self, operation_details, project_dir, dry_run):
        """Process git init operation."""
        from angela.toolchain.git import git_integration
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Would initialize Git repository in {project_dir}"
            }
        
        # Get initialization parameters
        branch = operation_details.get("branch", "main")
        gitignore = operation_details.get("gitignore", True)
        
        # Initialize repository
        result = await git_integration.init_repository(
            path=project_dir,
            initial_branch=branch,
            gitignore_template=operation_details.get("gitignore_template")
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Git repository initialized"),
            "git_details": result
        }
    
    async def _process_git_commit(self, operation_details, project_dir, dry_run):
        """Process git commit operation."""
        from angela.toolchain.git import git_integration
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Would commit changes in {project_dir}"
            }
        
        # Get commit parameters
        message = operation_details.get("message", "Update via Angela CLI")
        add_all = operation_details.get("add_all", True)
        
        # Stage files if requested
        if add_all:
            await git_integration.stage_files(path=project_dir, files=["."])
        
        # Commit changes
        result = await git_integration.commit_changes(
            path=project_dir,
            message=message
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Changes committed successfully"),
            "git_details": result
        }
    
    async def _process_git_branch(self, operation_details, project_dir, dry_run):
        """Process git branch operation."""
        from angela.toolchain.git import git_integration
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Would create/switch branch in {project_dir}"
            }
        
        # Get branch parameters
        branch_name = operation_details.get("branch_name", "")
        if not branch_name:
            return {
                "success": False,
                "error": "Branch name not specified"
            }
        
        checkout = operation_details.get("checkout", True)
        
        # Create branch
        result = await git_integration.create_branch(
            path=project_dir,
            branch_name=branch_name,
            checkout=checkout
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", f"Branch {branch_name} created"),
            "git_details": result
        }
    
    async def _process_git_status(self, operation_details, project_dir, dry_run):
        """Process git status operation."""
        from angela.toolchain.git import git_integration
        
        # Get repository status
        result = await git_integration.get_repository_status(path=project_dir)
        
        return {
            "success": result.get("success", False),
            "message": "Git status retrieved",
            "status": result.get("status", {}),
            "git_details": result
        }
    
    async def _process_testing_operation(
        self,
        operation_details: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a testing operation request.
        
        Args:
            operation_details: Details about the operation
            context: Context information
            dry_run: Whether to simulate without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing testing operation")
        
        # Get details
        project_dir = operation_details.get("project_dir", context.get("cwd", "."))
        test_framework = operation_details.get("test_framework", "")
        test_path = operation_details.get("test_path", "")
        
        # Execute testing operation
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Would run tests using {test_framework} in {project_dir}"
            }
        
        try:
            # Determine test command based on framework
            command = ""
            if test_framework == "pytest":
                command = f"pytest {test_path}" if test_path else "pytest"
            elif test_framework == "jest":
                command = f"npx jest {test_path}" if test_path else "npx jest"
            elif test_framework == "go":
                command = f"go test {test_path}" if test_path else "go test ./..."
            elif test_framework == "maven":
                command = "mvn test"
            elif test_framework == "gradle":
                command = "./gradlew test"
            else:
                # Default to using AI to generate appropriate test command
                suggestion = await self._get_ai_suggestion(
                    f"run tests for {test_framework} in {project_dir}",
                    context
                )
                command = suggestion.command
            
            # Execute test command
            stdout, stderr, exit_code = await execution_engine.execute_command(
                command,
                check_safety=True,
                working_dir=project_dir
            )
            
            return {
                "success": exit_code == 0,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": exit_code,
                "message": "Tests completed successfully" if exit_code == 0 else "Tests failed"
            }
        except Exception as e:
            self._logger.exception(f"Error processing testing operation: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing testing operation: {str(e)}"
            }
            
    async def _extract_feature_details(
        self, 
        request: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract feature details from a feature addition request.
        
        Args:
            request: The user request
            context: Context information
            
        Returns:
            Dictionary with feature details
        """
        # Use AI to extract feature details
        prompt = f"""
    Extract feature details from this feature addition request:
    "{request}"
    
    Return a JSON object with:
    1. description: A clear description of the feature to add
    2. project_dir: The project directory (default to ".")
    3. branch: A branch name if specified
    
    Format:
    {{
      "description": "feature description",
      "project_dir": "directory",
      "branch": "branch-name"
    }}
    
    Only include keys where you have clear information from the request.
    """
        
        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
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
            details = json.loads(json_str)
            
            # Default project directory to context's project_root if available
            if "project_dir" not in details and context.get("project_root"):
                details["project_dir"] = context.get("project_root")
            
            return details
            
        except Exception as e:
            self._logger.error(f"Error extracting feature details: {str(e)}")
            # Return minimal details on failure
            return {
                "project_dir": context.get("project_root", "."),
                "description": request
            }


    
    async def _extract_project_details(
        self, 
        request: str
    ) -> Dict[str, Any]:
        """
        Extract project details from a code generation request.
        
        Args:
            request: The user request
            
        Returns:
            Dictionary with project details
        """
        # Use AI to extract project details
        prompt = f"""
    Extract project details from this code generation request:
    "{request}"
    
    Return a JSON object with:
    1. project_type: The type of project (e.g., "python", "node", "java", etc.)
    2. framework: Any specific framework mentioned (e.g., "django", "react", "spring")
    3. output_dir: Where the project should be created (default to ".")
    4. git_init: Whether to initialize a Git repo (default to true)
    5. description: A clear description of what the project should do/be
    
    Format:
    {{
      "project_type": "type",
      "framework": "framework",
      "output_dir": "directory",
      "git_init": true/false,
      "description": "description"
    }}
    
    Only include keys where you have clear information from the request.
    If something is ambiguous, omit the key rather than guessing.
    """
        
        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
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
            details = json.loads(json_str)
            return details
            
        except Exception as e:
            self._logger.error(f"Error extracting project details: {str(e)}")
            # Return minimal details on failure
            return {
                "output_dir": ".",
                "git_init": True,
                "description": request
            }


    
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
        intent_result = intent_analyzer.analyze_intent(request)
        
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
        if confidence < 0.6 and not dry_run and not context.get("session", {}).get("skip_clarification"):
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
    

    async def _process_multi_step_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """Process a multi-step operation request with transaction-based rollback support."""
        self._logger.info(f"Processing multi-step request: {request}")
        
        # Get error recovery manager if needed
        error_recovery_manager = self._get_error_recovery_manager()
        
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
                    "response": "I couldn't determine which file you're referring to. Please specify the file path.",
                    "success": False
                }
            
            # Determine if this is analysis or manipulation
            operation_type = await self._determine_file_operation_type(request)
            
            result = {
                "request": request,
                "type": "file_content",
                "context": context,
                "file_path": str(file_path),
                "operation_type": operation_type,
                "success": False  # Default to False, will be updated if operation succeeds
            }
            
            if operation_type == "analyze":
                # Analyze file content (no rollback needed)
                try:
                    analysis_result = await content_analyzer.analyze_content(file_path, request)
                    result["analysis"] = analysis_result
                    result["success"] = True
                    
                    # End transaction as completed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "completed")
                except Exception as e:
                    self._logger.error(f"Error analyzing file content: {str(e)}")
                    result["error"] = f"Error analyzing file content: {str(e)}"
                    
                    # End transaction as failed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "failed")
                
            elif operation_type == "summarize":
                # Summarize file content (no rollback needed)
                try:
                    summary_result = await content_analyzer.summarize_content(file_path)
                    result["summary"] = summary_result
                    result["success"] = True
                    
                    # End transaction as completed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "completed")
                except Exception as e:
                    self._logger.error(f"Error summarizing file content: {str(e)}")
                    result["error"] = f"Error summarizing file content: {str(e)}"
                    
                    # End transaction as failed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "failed")
                
            elif operation_type == "search":
                # Search file content (no rollback needed)
                try:
                    search_result = await content_analyzer.search_content(file_path, request)
                    result["search_results"] = search_result
                    result["success"] = True
                    
                    # End transaction as completed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "completed")
                except Exception as e:
                    self._logger.error(f"Error searching file content: {str(e)}")
                    result["error"] = f"Error searching file content: {str(e)}"
                    
                    # End transaction as failed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "failed")
                
            elif operation_type == "manipulate":
                # Manipulate file content
                try:
                    manipulation_result = await content_analyzer.manipulate_content(file_path, request)
                    result["manipulation"] = manipulation_result
                    
                    # Apply changes if requested
                    if execute and not dry_run and manipulation_result.get("has_changes", False):
                        # Get confirmation before applying changes
                        confirmed = await self._confirm_file_changes(
                            file_path, 
                            manipulation_result.get("diff", "No changes")
                        )
                        
                        if confirmed:
                            # Read original content for rollback
                            original_content = manipulation_result.get("original_content", "")
                            modified_content = manipulation_result.get("modified_content", "")
                            
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
                    elif dry_run and manipulation_result.get("has_changes", False):
                        result["changes_applied"] = False
                        result["success"] = True
                        result["dry_run"] = True
                        
                        # End transaction as completed for dry run
                        if transaction_id:
                            await rollback_manager.end_transaction(transaction_id, "completed")
                    else:
                        # No changes to apply or not executing
                        result["success"] = True
                        if transaction_id:
                            await rollback_manager.end_transaction(transaction_id, "completed")
                except Exception as e:
                    self._logger.error(f"Error manipulating file content: {str(e)}")
                    result["error"] = f"Error manipulating file content: {str(e)}"
                    
                    # End transaction as failed
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "failed")
                
            else:
                # Unknown operation type
                result["error"] = f"Unknown file operation type: {operation_type}"
                
                # End transaction as failed
                if transaction_id:
                    await rollback_manager.end_transaction(transaction_id, "failed")
            
            return result
            
        except Exception as e:
            # Handle any exceptions and end the transaction
            if transaction_id:
                await rollback_manager.end_transaction(transaction_id, "failed")
            
            self._logger.exception(f"Error processing file content request: {str(e)}")
            
            return {
                "request": request,
                "type": "file_content",
                "context": context,
                "error": f"Error processing file content request: {str(e)}",
                "success": False
            }
    

    
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
        # Get error recovery manager
        error_recovery_manager = self._get_error_recovery_manager()
        
        recovered_results = list(execution_results)  # Copy the original results
        
        # Find failed steps
        for i, result in enumerate(execution_results):
            if not result.get("success", False):
                # Get the corresponding step - safely handle potential index errors
                step = None
                if hasattr(plan, 'steps') and isinstance(plan.steps, list) and i < len(plan.steps):
                    step = plan.steps[i]
                elif hasattr(plan, 'steps') and isinstance(plan.steps, dict):
                    # Try to find the step by id if it's a dictionary
                    step_id = result.get('step_id')
                    if step_id and step_id in plan.steps:
                        step = plan.steps[step_id]
                
                # Only attempt recovery if we have a valid step
                if step:
                    # Attempt recovery
                    recovery_result = await error_recovery_manager.handle_error(
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
        """
        Get a command suggestion from the AI service.
        
        Args:
            request: The user request
            context: Context information about the current environment
            similar_command: Optional similar command from history
            intent_result: Optional intent analysis result
            
        Returns:
            A CommandSuggestion object with the suggested command
        """
        # Build prompt with context, including session context if available
        prompt = build_prompt(request, context, similar_command, intent_result)
        
        # Create a request to the Gemini API
        api_request = GeminiRequest(prompt=prompt)
        
        # Call the Gemini API
        self._logger.info("Sending request to Gemini API")
        try:
            api_response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            suggestion = parse_ai_response(api_response.text)
            
            self._logger.info(f"Received suggestion: {suggestion.command}")
            return suggestion
        except Exception as e:
            self._logger.exception(f"Error getting AI suggestion: {str(e)}")
            # Provide a fallback suggestion
            return CommandSuggestion(
                intent="error",
                command=f"echo 'Error generating suggestion: {str(e)}'",
                explanation="This is a fallback command due to an error in the AI service."
            )
    
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
        
        try:
            # Try to extract file references
            file_references = await file_resolver.extract_references(request, context)
            
            # If we found any resolved references, return the first one
            for reference, path in file_references:
                if path:
                    # Track as viewed file
                    try:
                        file_activity_tracker.track_file_viewing(path, None, {
                            "request": request,
                            "reference": reference
                        })
                    except Exception as e:
                        self._logger.warning(f"Error tracking file viewing: {str(e)}")
                        
                    return path
            
            # If we found references but couldn't resolve them, use AI extraction as fallback
            if file_references:
                for reference, _ in file_references:
                    # Try to resolve with a broader scope
                    try:
                        path = await file_resolver.resolve_reference(
                            reference, 
                            context,
                            search_scope="project"
                        )
                        if path:
                            # Track as viewed file
                            try:
                                file_activity_tracker.track_file_viewing(path, None, {
                                    "request": request,
                                    "reference": reference
                                })
                            except Exception as e:
                                self._logger.warning(f"Error tracking file viewing: {str(e)}")
                                
                            return path
                    except Exception as e:
                        self._logger.warning(f"Error resolving reference '{reference}': {str(e)}")
            
            # If all else fails, try to extract from the request text directly
            file_patterns = [
                r'file[s]?\s+(?:called|named)\s+"([^"]+)"',
                r'file[s]?\s+(?:called|named)\s+\'([^\']+)\'',
                r'file[s]?\s+([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)',
                r'(?:in|from|to)\s+(?:the\s+)?file[s]?\s+"([^"]+)"',
                r'(?:in|from|to)\s+(?:the\s+)?file[s]?\s+\'([^\']+)\'',
                r'(?:in|from|to)\s+(?:the\s+)?file[s]?\s+([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)'
            ]
            
            for pattern in file_patterns:
                match = re.search(pattern, request, re.IGNORECASE)
                if match:
                    file_name = match.group(1)
                    # Check if this file exists in the current directory
                    file_path = Path(context.get('cwd', '.')) / file_name
                    if file_path.exists():
                        return file_path
                    
                    # Check if it exists in the project root
                    if 'project_root' in context:
                        project_path = Path(context['project_root']) / file_name
                        if project_path.exists():
                            return project_path
            
            return None
            
        except Exception as e:
            self._logger.error(f"Error extracting file path: {str(e)}")
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
        Start background monitoring for a failed command with proper cleanup.
        
        Args:
            command: The failed command
            error_analysis: Analysis of the error
        """
        # Create and start a background task with timeout
        async def monitored_task():
            try:
                # Set a reasonable timeout for monitoring (e.g., 5 minutes)
                timeout = 300  # seconds
                await asyncio.wait_for(
                    self._monitor_for_suggestions(command, error_analysis),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                self._logger.info(f"Background monitoring timed out after {timeout} seconds")
            except Exception as e:
                self._logger.error(f"Error in background monitoring: {str(e)}")
        
        # Create the task and add it to our set of background tasks
        task = asyncio.create_task(monitored_task())
        
        # Add the task to our set of background tasks
        self._background_tasks.add(task)
        
        # Define a callback to remove the task when it's done and handle any exceptions
        def task_done_callback(task):
            self._background_tasks.discard(task)
            # Check for exceptions that weren't handled inside the task
            if not task.cancelled():
                exception = task.exception()
                if exception:
                    self._logger.error(f"Unhandled exception in background task: {str(exception)}")
        
        # Add the callback
        task.add_done_callback(task_done_callback)
    
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



    async def _process_universal_cli_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a request using the Universal CLI Translator.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the command
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing universal CLI request: {request}")
        
        # Import here to avoid circular imports
        from angela.toolchain.universal_cli import universal_cli_translator
        
        # Translate the request into a command
        translation = await universal_cli_translator.translate_request(request, context)
        
        if not translation.get("success"):
            return {
                "request": request,
                "type": "universal_cli",
                "context": context,
                "error": translation.get("error", "Failed to translate request"),
                "response": f"I couldn't translate your request into a command: {translation.get('error', 'Unknown error')}"
            }
        
        # Create result structure
        result = {
            "request": request,
            "type": "universal_cli",
            "context": context,
            "command": translation["command"],
            "tool": translation["tool"],
            "subcommand": translation.get("subcommand", ""),
            "explanation": translation.get("explanation", "")
        }
        
        # Execute the command if requested
        if execute or dry_run:
            execution_result = await self.execute_command(
                command=translation["command"],
                natural_request=request,
                explanation=translation.get("explanation", ""),
                dry_run=dry_run
            )
            
            result["execution"] = execution_result
        
        return result
    
    async def _process_complex_workflow(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a complex workflow request involving multiple tools.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the workflow
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing complex workflow: {request}")
        
        # Use the enhanced task planner for complex workflows
        from angela.intent.enhanced_task_planner import enhanced_task_planner
        from angela.shell.formatter import terminal_formatter
        from angela.execution.rollback import rollback_manager
        
        # Generate a complex plan
        plan = await enhanced_task_planner.plan_advanced_task(request, context, max_steps=30)
        
        # Create result structure
        result = {
            "request": request,
            "type": "complex_workflow",
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
                transaction_id = None
                if not dry_run:
                    transaction_id = await rollback_manager.start_transaction(f"Complex workflow: {request[:50]}...")
                
                # Set up variables for cross-step communication if needed
                initial_variables = {
                    "request": request,
                    "workflow_type": "complex",
                    "started_at": datetime.now().isoformat(),
                }
                
                # Add context variables that might be useful
                if context.get("project_root"):
                    initial_variables["project_root"] = str(context["project_root"])
                if context.get("project_type"):
                    initial_variables["project_type"] = context["project_type"]
                
                execution_results = await enhanced_task_planner.execute_advanced_plan(
                    plan, 
                    dry_run=dry_run,
                    transaction_id=transaction_id,
                    initial_variables=initial_variables
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
        
        return result
    
    async def _confirm_advanced_plan(self, plan, dry_run: bool) -> bool:
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
        from rich.panel import Panel
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
            "[bold yellow]This is an advanced workflow with complex execution flow.[/bold yellow]\n"
            "It includes multiple tools and dependencies between steps.",
            border_style="yellow",
            expand=False
        ))
        
        # Get confirmation
        confirmed = yes_no_dialog(
            title="Confirm Advanced Workflow Execution",
            text=f"Do you want to execute this {len(plan.steps)}-step workflow?",
        ).run()
        
        return confirmed






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


    async def _handle_monitoring_insight(self, insight_type: str, insight_data: Dict[str, Any]):
        """Handle insights from monitoring systems."""
        self._logger.info(f"Received monitoring insight: {insight_type}")
        
        # Store insight in context for future decision making
        session_manager.add_entity(
            f"monitoring_{insight_type}",
            "monitoring_insight", 
            insight_data
        )
        
        # Potentially trigger actions based on insights
        if insight_type == "critical_resource_warning" and insight_data.get("severity") == "high":
            # Take immediate action
            await self._handle_critical_resource_warning(insight_data)

    async def _process_complex_workflow_request(
        self, 
        request: str, 
        context: Dict[str, Any], 
        execute: bool, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Process a complex workflow request involving multiple tools.
        
        This method handles advanced workflows that span multiple tools and services,
        such as complete CI/CD pipelines, end-to-end deployment processes, etc.
        
        Args:
            request: The user request
            context: Context information
            execute: Whether to execute the workflow
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with processing results
        """
        self._logger.info(f"Processing complex workflow request: {request}")
        
        # Import here to avoid circular imports
        from angela.intent.complex_workflow_planner import complex_workflow_planner
        
        # Start a transaction for this complex workflow
        transaction_id = None
        if not dry_run and execute:
            transaction_id = await rollback_manager.start_transaction(f"Complex workflow: {request[:50]}...")
        
        try:
            # Generate a workflow plan
            workflow_plan = await complex_workflow_planner.plan_complex_workflow(
                request=request,
                context=context,
                max_steps=50  # Allow more steps for complex workflows
            )
            
            # Create result structure
            result = {
                "request": request,
                "type": "complex_workflow",
                "context": context,
                "workflow_plan": {
                    "id": workflow_plan.id,
                    "name": workflow_plan.name,
                    "description": workflow_plan.description,
                    "steps_count": len(workflow_plan.steps),
                    "tools": self._extract_unique_tools(workflow_plan),
                    "estimated_duration": self._estimate_workflow_duration(workflow_plan)
                }
            }
            
            # Execute the workflow if requested
            if execute or dry_run:
                # Display the workflow plan
                await terminal_formatter.display_complex_workflow_plan(workflow_plan)
                
                # Get confirmation from user unless forced
                confirmed = True
                if not context.get("session", {}).get("force_execution", False):
                    confirmed = await self._confirm_complex_workflow_execution(workflow_plan, dry_run)
                
                if confirmed or dry_run:
                    # Execute the workflow with transaction support
                    execution_results = await complex_workflow_planner.execute_complex_workflow(
                        workflow_plan, 
                        dry_run=dry_run,
                        transaction_id=transaction_id
                    )
                    
                    result["execution_results"] = execution_results
                    result["success"] = execution_results.get("success", False)
                    
                    # End transaction based on result
                    if transaction_id:
                        status = "completed" if result["success"] else "failed"
                        await rollback_manager.end_transaction(transaction_id, status)
                else:
                    # User cancelled execution
                    result["cancelled"] = True
                    result["success"] = False
                    
                    # End transaction as cancelled
                    if transaction_id:
                        await rollback_manager.end_transaction(transaction_id, "cancelled")
            
            return result
            
        except Exception as e:
            # Handle any exceptions and end the transaction
            self._logger.exception(f"Error processing complex workflow: {str(e)}")
            
            if transaction_id:
                await rollback_manager.end_transaction(transaction_id, "failed")
            
            return {
                "request": request,
                "type": "complex_workflow",
                "context": context,
                "error": str(e),
                "success": False
            }
    
    def _extract_unique_tools(self, workflow_plan: Any) -> List[str]:
        """
        Extract the unique tools used in a workflow plan.
        
        Args:
            workflow_plan: The workflow plan
            
        Returns:
            List of unique tools
        """
        import shlex  # Make sure shlex is imported
        
        tools = set()
        
        # Safely check if steps exists and is iterable
        if not hasattr(workflow_plan, 'steps') or not workflow_plan.steps:
            return []
        
        # Handle both dictionary and list step structures
        steps = []
        if isinstance(workflow_plan.steps, dict):
            steps = workflow_plan.steps.items()
        elif isinstance(workflow_plan.steps, list):
            steps = [(i, step) for i, step in enumerate(workflow_plan.steps)]
        else:
            # Unknown structure, return empty list
            return []
        
        for step_id, step in steps:
            if hasattr(step, "tool") and step.tool:
                tools.add(step.tool)
            elif hasattr(step, "type") and step.type == "TOOL" and hasattr(step, "tool") and step.tool:
                tools.add(step.tool)
            elif hasattr(step, "command") and step.command:
                # Try to extract tool from command
                try:
                    cmd_parts = shlex.split(step.command)
                    if cmd_parts:
                        tools.add(cmd_parts[0])
                except Exception:
                    # If shlex.split fails, just use the first word as a fallback
                    first_word = step.command.split()[0] if step.command.split() else ""
                    if first_word:
                        tools.add(first_word)
        
        return sorted(list(tools))
    
    def _estimate_workflow_duration(self, workflow_plan: Any) -> int:
        """
        Estimate the duration of a workflow in seconds.
        
        Args:
            workflow_plan: The workflow plan
            
        Returns:
            Estimated duration in seconds
        """
        # Base duration per step type
        step_durations = {
            "COMMAND": 10,  # Simple commands take ~10 seconds
            "TOOL": 30,     # Tool commands might take longer
            "API": 15,      # API calls typically take 15 seconds
            "FILE": 5,      # File operations are usually fast
            "WAIT": 30,     # Wait steps default to 30 seconds
            "DECISION": 2,  # Decisions are quick
            "VALIDATION": 5,  # Validations are usually fast
            "PARALLEL": 40,  # Parallel steps might take longer
            "CUSTOM_CODE": 20,  # Custom code execution
            "NOTIFICATION": 2   # Notifications are instantaneous
        }
        
        total_duration = 0
        
        for step_id, step in workflow_plan.steps.items():
            step_type = getattr(step, "type", "COMMAND")
            
            # Get base duration for this step type
            duration = step_durations.get(step_type, 10)
            
            # Adjust for specific commands or operations
            if hasattr(step, "command") and step.command:
                cmd = step.command.lower()
                
                # Long-running processes
                if any(pattern in cmd for pattern in ["build", "compile", "install", "test", "deploy"]):
                    duration = max(duration, 60)  # At least a minute
                
                # Very long running processes
                if any(pattern in cmd for pattern in ["docker build", "mvn install", "npm build", "deployment"]):
                    duration = max(duration, 300)  # At least 5 minutes
            
            # For wait steps, use the actual timeout if specified
            if step_type == "WAIT" and hasattr(step, "timeout") and step.timeout:
                duration = max(duration, step.timeout)
            
            total_duration += duration
        
        # Adjust for parallel execution
        # This is a simplification - we're not building a full dependency graph
        parallel_reduction = 0
        parallel_steps = sum(1 for step in workflow_plan.steps.values() 
                            if getattr(step, "type", "") == "PARALLEL")
        
        if parallel_steps > 0:
            # Rough estimate - each parallel step reduces total time by ~20%
            parallel_reduction = total_duration * (0.2 * min(parallel_steps, 3))
        
        # Apply the reduction, but ensure we don't go below 10 seconds
        return max(10, int(total_duration - parallel_reduction))
    
    async def _confirm_complex_workflow_execution(self, workflow_plan: Any, dry_run: bool) -> bool:
        """
        Get confirmation for executing a complex workflow.
        
        Args:
            workflow_plan: The workflow plan
            dry_run: Whether this is a dry run
            
        Returns:
            True if confirmed, False otherwise
        """
        if dry_run:
            return True  # No confirmation needed for dry run
        
        # Analyze the workflow risk level
        high_risk_steps = []
        for step_id, step in workflow_plan.steps.items():
            risk_level = getattr(step, "risk_level", 0)
            if risk_level >= 3:  # High risk
                high_risk_steps.append((step_id, getattr(step, "name", f"Step {step_id}")))
        
        # Import here to avoid circular imports
        from rich.console import Console
        from rich.panel import Panel
        from prompt_toolkit.shortcuts import yes_no_dialog
        
        console = Console()
        
        # Display a warning for high-risk steps
        if high_risk_steps:
            warning_text = "This workflow includes HIGH RISK operations:\n\n"
            for step_id, step_name in high_risk_steps:
                warning_text += f"• {step_name} ({step_id})\n"
            warning_text += "\nSome of these steps could make significant changes to your system."
            
            console.print(Panel(
                warning_text,
                title="⚠️ Warning: High Risk Operations ⚠️",
                border_style="red",
                expand=False
            ))
        
        # Display workflow scope and impact
        tools = self._extract_unique_tools(workflow_plan)
        estimated_duration = self._estimate_workflow_duration(workflow_plan)
        
        scope_text = f"This workflow will use {len(tools)} different tools: {', '.join(tools)}\n"
        scope_text += f"Estimated duration: {int(estimated_duration/60)} minutes {estimated_duration%60} seconds\n"
        scope_text += f"Step count: {len(workflow_plan.steps)}"
        
        console.print(Panel(
            scope_text,
            title="Workflow Scope",
            border_style="blue",
            expand=False
        ))
        
        # Get confirmation
        confirmed = yes_no_dialog(
            title="Confirm Complex Workflow Execution",
            text=f"Do you want to execute this complex workflow with {len(workflow_plan.steps)} steps?",
        ).run()
        
        return confirmed

    async def _execute_with_feedback(self, command: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a command with real-time feedback.
        
        Args:
            command: The command to execute
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"{'Dry run of' if dry_run else 'Executing'} command: {command}")
        
        if dry_run:
            return {
                "command": command,
                "success": True,
                "stdout": f"[DRY RUN] Would execute: {command}",
                "stderr": "",
                "return_code": 0,
                "dry_run": True
            }
        
        # Use the execution engine to run the command
        stdout, stderr, exit_code = await execution_engine.execute_command(
            command=command,
            check_safety=True
        )
        
        return {
            "command": command,
            "success": exit_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": exit_code,
            "dry_run": False
        }


    async def _handle_critical_resource_warning(self, warning_data: Dict[str, Any]) -> None:
        """
        Handle a critical resource warning from the monitoring system.
        
        Args:
            warning_data: Warning data from the monitoring system
        """
        self._logger.warning(f"Handling critical resource warning: {warning_data}")
        
        # Log the warning
        resource_type = warning_data.get("resource_type", "unknown")
        resource_name = warning_data.get("resource_name", "unknown")
        severity = warning_data.get("severity", "unknown")
        
        # Take action based on resource type
        if resource_type == "memory" and severity == "high":
            # Suggest garbage collection or process restart
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold red]Warning:[/bold red] High memory usage detected for {resource_name}")
            console.print("Consider freeing up memory or restarting resource-intensive processes.")
        
        elif resource_type == "disk" and severity == "high":
            # Suggest disk cleanup
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold red]Warning:[/bold red] Low disk space detected for {resource_name}")
            console.print("Consider removing temporary files or unused artifacts.")
        
        elif resource_type == "cpu" and severity == "high":
            # Suggest process throttling
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold red]Warning:[/bold red] High CPU usage detected for {resource_name}")
            console.print("Consider throttling or pausing resource-intensive processes.")
        
        return None  

    # Functions to add to your orchestrator:
    
    async def detect_pipeline_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect opportunities for CI/CD pipelines in the current context.
        
        Args:
            context: Context information
            
        Returns:
            Dictionary with pipeline opportunities
        """
        self._logger.info("Detecting CI/CD pipeline opportunities")
        
        ci_cd_integration = registry.get("ci_cd_integration")
        if not ci_cd_integration:
            return {
                "success": False,
                "error": "CI/CD Integration component not available"
            }
        
        project_root = context.get("project_root")
        if not project_root:
            return {
                "success": False,
                "error": "No project root detected in context"
            }
        
        return await ci_cd_integration.detect_project_type(project_root)
    
    async def suggest_complex_workflow(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest a complex workflow based on a natural language request.
        
        Args:
            request: Natural language request
            context: Context information
            
        Returns:
            Dictionary with suggested workflow information
        """
        self._logger.info(f"Suggesting complex workflow for: {request}")
        
        workflow_engine = registry.get("cross_tool_workflow_engine")
        if not workflow_engine:
            return {
                "success": False,
                "error": "Cross Tool Workflow Engine component not available"
            }
        
        # Create a workflow using the engine
        try:
            workflow = await workflow_engine.create_workflow(
                request=request,
                context=context
            )
            
            # Convert to dictionary for return
            workflow_dict = workflow.dict() if hasattr(workflow, "dict") else workflow
            
            return {
                "success": True,
                "workflow": workflow_dict
            }
        except Exception as e:
            self._logger.error(f"Error generating workflow: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to generate workflow: {str(e)}"
            }
    
    async def execute_cross_tool_workflow(
        self,
        request: str,
        context: Dict[str, Any],
        suggested_tools: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a workflow involving multiple tools.
        
        Args:
            request: Natural language request
            context: Context information
            suggested_tools: Optional list of suggested tools to use
            dry_run: Whether to simulate execution without making changes
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing cross-tool workflow: {request}")
        
        workflow_engine = registry.get("cross_tool_workflow_engine")
        if not workflow_engine:
            return {
                "success": False,
                "error": "Cross Tool Workflow Engine component not available"
            }
        
        # Create and execute workflow
        try:
            # Create a workflow
            workflow = await workflow_engine.create_workflow(
                request=request,
                context=context,
                tools=suggested_tools
            )
            
            # Execute the workflow
            return await workflow_engine.execute_workflow(
                workflow=workflow,
                dry_run=dry_run
            )
        except Exception as e:
            self._logger.error(f"Error executing cross-tool workflow: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to execute cross-tool workflow: {str(e)}"
            }
            

# Global orchestrator instance
orchestrator = Orchestrator()

# Synchronous wrapper for backwards compatibility
def process_request(request: str) -> Dict[str, Any]:
    """Synchronous wrapper for processing a request."""
    return asyncio.run(orchestrator.process_request(request))
