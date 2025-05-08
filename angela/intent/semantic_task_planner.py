"""
Semantic task planning and intent decomposition for Angela CLI.

This module extends the enhanced task planner with semantic code understanding
and improved intent decomposition for handling complex, ambiguous, multi-stage goals.
"""
import re
import json
import uuid
import asyncio
from typing import Dict, Any, List, Tuple, Optional, Set, Union
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from angela.ai.client import gemini_client, GeminiRequest
from angela.ai.semantic_analyzer import semantic_analyzer
from angela.context import context_manager
from angela.context.project_state_analyzer import project_state_analyzer
from angela.intent.enhanced_task_planner import EnhancedTaskPlanner, AdvancedTaskPlan, PlanStepType
from angela.utils.logging import get_logger
from angela.core.registry import registry
from angela.shell.inline_feedback import inline_feedback

logger = get_logger(__name__)

class IntentClarification(BaseModel):
    """Model for intent clarification information."""
    
    original_request: str = Field(..., description="The original user request")
    ambiguity_type: str = Field(..., description="Type of ambiguity detected")
    ambiguity_details: str = Field(..., description="Details about the ambiguity")
    clarification_question: str = Field(..., description="Question to ask the user")
    options: List[str] = Field(default_factory=list, description="Possible options to present to the user")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context for resolving the ambiguity")


class SemanticTaskPlanner:
    """
    Enhanced task planner with semantic code understanding and improved intent decomposition.
    
    This class extends the existing EnhancedTaskPlanner with:
    1. Integration with semantic code analysis
    2. Improved handling of ambiguous requests
    3. Multi-stage goal decomposition with sub-goals
    4. Interactive clarification for uncertain intents
    """
    
    def __init__(self):
        """Initialize the semantic task planner."""
        self._logger = logger
        self._enhanced_planner = EnhancedTaskPlanner()
        self._clarification_handlers = {
            "file_reference": self._clarify_file_reference,
            "entity_reference": self._clarify_entity_reference,
            "action_type": self._clarify_action_type,
            "operation_scope": self._clarify_operation_scope,
            "step_ordering": self._clarify_step_ordering,
            "parameter_value": self._clarify_parameter_value
        }
    
    async def plan_task(
        self, 
        request: str, 
        context: Dict[str, Any],
        enable_clarification: bool = True,
        semantic_context: bool = True
    ) -> Dict[str, Any]:
        """
        Plan a task with semantic understanding and potential user clarification.
        
        Args:
            request: User request
            context: Task context
            enable_clarification: Whether to enable interactive clarification
            semantic_context: Whether to include semantic code understanding
            
        Returns:
            Dictionary with planning results including a task plan
        """
        self._logger.info(f"Planning semantic task: {request}")
        
        # Enhance context with semantic information if requested
        if semantic_context:
            context = await self._enhance_context_with_semantics(context)
        
        # First, analyze the request for potential ambiguities
        intent_analysis = await self._analyze_intent(request, context)
        
        # Check if clarification is needed and enabled
        if intent_analysis.get("needs_clarification", False) and enable_clarification:
            clarification = await self._create_clarification(request, intent_analysis, context)
            
            if clarification:
                # Get user clarification
                clarified_request = await self._get_user_clarification(clarification)
                
                if clarified_request:
                    # Update the request and intent analysis
                    self._logger.info(f"Using clarified request: {clarified_request}")
                    request = clarified_request
                    intent_analysis = await self._analyze_intent(request, context)
        
        # Decompose the goal into sub-goals if complex
        goal_decomposition = await self._decompose_goal(request, intent_analysis, context)
        
        # Create an execution plan
        plan_result = await self._create_execution_plan(request, goal_decomposition, context)
        
        # Return the planning results
        return {
            "original_request": request,
            "intent_analysis": intent_analysis,
            "goal_decomposition": goal_decomposition,
            "execution_plan": plan_result.get("plan"),
            "plan_type": plan_result.get("plan_type", "simple"),
            "plan_id": plan_result.get("plan_id"),
            "estimated_steps": plan_result.get("estimated_steps", 0),
            "max_risk_level": plan_result.get("max_risk_level", 0),
            "clarification_needed": intent_analysis.get("needs_clarification", False),
            "clarification_performed": intent_analysis.get("needs_clarification", False) and enable_clarification
        }
    
    async def execute_plan(
        self, 
        plan_result: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a task plan generated by the semantic planner.
        
        Args:
            plan_result: Planning results from plan_task
            context: Task context
            dry_run: Whether to perform a dry run without making changes
            transaction_id: Optional transaction ID for rollback
            
        Returns:
            Dictionary with execution results
        """
        self._logger.info(f"Executing semantic task plan: {plan_result.get('original_request')}")
        
        # Get the execution plan
        execution_plan = plan_result.get("execution_plan")
        
        if not execution_plan:
            return {
                "success": False,
                "error": "No execution plan available",
                "plan_result": plan_result
            }
        
        # Execute the plan using the enhanced task planner
        execution_result = await self._enhanced_planner.execute_plan(
            plan=execution_plan,
            dry_run=dry_run,
            transaction_id=transaction_id
        )
        
        # Return the execution results
        return {
            "success": execution_result.get("success", False),
            "execution_result": execution_result,
            "plan_result": plan_result,
            "dry_run": dry_run
        }
    
    async def _analyze_intent(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user intent with semantic understanding.
        
        Args:
            request: User request
            context: Task context
            
        Returns:
            Dictionary with intent analysis
        """
        self._logger.debug(f"Analyzing intent for request: {request}")
        
        # Create a prompt for the AI to analyze the intent
        project_context = self._extract_project_context(context)
        
        prompt = f"""
You are an expert assistant analyzing a user's request to an AI terminal assistant that can perform tasks using shell commands and code.

USER REQUEST: "{request}"

CONTEXT:
{project_context}

Provide a detailed analysis of the user's intent, including:
1. The primary goal they're trying to achieve
2. Required sub-tasks or steps
3. Entities involved (files, directories, commands, APIs)
4. Any potential ambiguities that need clarification 
5. Level of complexity (simple/moderate/complex)

Return your analysis as a JSON object with this structure:
```json
{{
  "primary_goal": "Clear description of the main objective",
  "intent_type": "One of: file_operation, code_generation, system_command, project_setup, information_request, refactoring",
  "entities": [
    {{ "type": "file|directory|command|api|code_entity", "name": "entity_name", "confidence": 0.0-1.0 }}
  ],
  "sub_tasks": [
    "Description of sub-task 1",
    "Description of sub-task 2"
  ],
  "needs_clarification": true|false,
  "ambiguities": [
    {{
      "type": "file_reference|entity_reference|action_type|operation_scope|step_ordering|parameter_value",
      "description": "Description of the ambiguity",
      "possible_interpretations": ["interpretation1", "interpretation2"]
    }}
  ],
  "complexity": "simple|moderate|complex",
  "estimated_steps": 1-20,
  "potential_risk": 0-4,
  "confidence": 0.0-1.0
}}
```

Use the highest standards for identifying ambiguities that would benefit from clarification. If anything is unclear, set "needs_clarification" to true and document the ambiguity.
"""
        
        # Call AI to analyze the intent
        api_request = GeminiRequest(
            prompt=prompt,
            temperature=0.1,  # Lower temperature for more deterministic analysis
            max_tokens=3000
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        try:
            # Try to extract JSON from the response
            response_text = response.text
            
            # Look for JSON block
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            
            # Try to parse the JSON
            intent_analysis = json.loads(response_text)
            
            # Add some metadata to the analysis
            intent_analysis["original_request"] = request
            intent_analysis["analysis_time"] = datetime.now().isoformat()
            
            return intent_analysis
            
        except (json.JSONDecodeError, IndexError) as e:
            self._logger.error(f"Error parsing intent analysis response: {str(e)}")
            
            # Return a basic fallback analysis
            return {
                "primary_goal": request,
                "intent_type": "unknown",
                "entities": [],
                "sub_tasks": [request],
                "needs_clarification": False,
                "ambiguities": [],
                "complexity": "simple",
                "estimated_steps": 1,
                "potential_risk": 0,
                "confidence": 0.5,
                "original_request": request,
                "analysis_time": datetime.now().isoformat(),
                "analysis_error": str(e)
            }
    
    def _extract_project_context(self, context: Dict[str, Any]) -> str:
        """
        Extract relevant project context for intent analysis.
        
        Args:
            context: Task context
            
        Returns:
            String with formatted project context
        """
        lines = []
        
        # Add current working directory
        if "cwd" in context:
            lines.append(f"Current Directory: {context['cwd']}")
        
        # Add project type if available
        if "project_type" in context:
            lines.append(f"Project Type: {context['project_type']}")
        
        # Add project root if available
        if "project_root" in context:
            lines.append(f"Project Root: {context['project_root']}")
        
        # Add enhanced project information if available
        if "enhanced_project" in context:
            enhanced_project = context["enhanced_project"]
            
            if "type" in enhanced_project:
                lines.append(f"Project Type: {enhanced_project['type']}")
            
            if "frameworks" in enhanced_project:
                frameworks = enhanced_project["frameworks"]
                if frameworks:
                    lines.append(f"Frameworks: {', '.join(frameworks.keys())}")
            
            if "dependencies" in enhanced_project and "top_dependencies" in enhanced_project["dependencies"]:
                deps = enhanced_project["dependencies"]["top_dependencies"]
                if deps:
                    lines.append(f"Top Dependencies: {', '.join(deps[:5])}")
        
        # Add recent file context if available
        if "recent_files" in context and "accessed" in context["recent_files"]:
            recent_files = context["recent_files"]["accessed"]
            if recent_files:
                lines.append(f"Recently Accessed Files: {', '.join([Path(f).name for f in recent_files[:3]])}")
        
        # Add resolved file references if available
        if "resolved_files" in context:
            resolved_files = context["resolved_files"]
            if resolved_files:
                lines.append("Resolved File References:")
                for ref_info in resolved_files:
                    lines.append(f"- '{ref_info['reference']}' → {ref_info['path']}")
        
        # Add semantic code information if available
        if "semantic_code" in context:
            semantic_code = context["semantic_code"]
            
            if "modules" in semantic_code:
                module_count = len(semantic_code["modules"])
                lines.append(f"Analyzed Code Modules: {module_count}")
            
            if "key_entities" in semantic_code:
                key_entities = semantic_code["key_entities"]
                if key_entities:
                    lines.append("Key Code Entities:")
                    for entity in key_entities[:5]:
                        lines.append(f"- {entity['type']} '{entity['name']}' in {Path(entity['filename']).name}")
        
        # Add project state information if available
        if "project_state" in context:
            project_state = context["project_state"]
            
            if "git_state" in project_state and project_state["git_state"].get("is_git_repo", False):
                git_state = project_state["git_state"]
                branch = git_state.get("current_branch", "unknown")
                has_changes = git_state.get("has_changes", False)
                
                git_info = f"Git: on branch '{branch}'"
                if has_changes:
                    git_info += " with uncommitted changes"
                
                lines.append(git_info)
            
            if "todo_items" in project_state and project_state["todo_items"]:
                todo_count = len(project_state["todo_items"])
                lines.append(f"Project TODOs: {todo_count} items")
        
        return "\n".join(lines)
    
    async def _create_clarification(
        self, 
        request: str, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Optional[IntentClarification]:
        """
        Create a clarification request for ambiguous intent.
        
        Args:
            request: Original user request
            intent_analysis: Intent analysis results
            context: Task context
            
        Returns:
            IntentClarification object or None if no clarification needed
        """
        if not intent_analysis.get("needs_clarification", False):
            return None
        
        ambiguities = intent_analysis.get("ambiguities", [])
        if not ambiguities:
            return None
        
        # Select the most important ambiguity to clarify
        # (for simplicity, just take the first one)
        ambiguity = ambiguities[0]
        
        ambiguity_type = ambiguity.get("type", "unknown")
        description = ambiguity.get("description", "")
        interpretations = ambiguity.get("possible_interpretations", [])
        
        # Select a clarification handler based on ambiguity type
        if ambiguity_type in self._clarification_handlers:
            return await self._clarification_handlers[ambiguity_type](
                request, ambiguity, interpretations, context
            )
        
        # Default clarification
        return IntentClarification(
            original_request=request,
            ambiguity_type=ambiguity_type,
            ambiguity_details=description,
            clarification_question=f"I'm not sure about this part of your request: {description}. Could you clarify?",
            options=interpretations,
            context={"ambiguity": ambiguity}
        )
    
    async def _get_user_clarification(self, clarification: IntentClarification) -> Optional[str]:
        """
        Get clarification from the user.
        
        Args:
            clarification: Clarification object
            
        Returns:
            Clarified request or None if clarification was not provided
        """
        self._logger.info(f"Getting user clarification for: {clarification.ambiguity_type}")
        
        try:
            # Check if inline_feedback is available
            if inline_feedback:
                question = clarification.clarification_question
                options = clarification.options
                
                if options:
                    # Present options for selection
                    response = await inline_feedback.ask_question(
                        question, 
                        choices=options,
                        allow_free_text=True
                    )
                else:
                    # Free-form response
                    response = await inline_feedback.ask_question(question)
                
                if response:
                    # Check if we need to create a new request or use the response as is
                    if clarification.ambiguity_type in ["file_reference", "entity_reference", "parameter_value"]:
                        # Just use the clarified response to update the original request
                        return self._update_request_with_clarification(
                            clarification.original_request, 
                            response, 
                            clarification
                        )
                    else:
                        # For other types, assume the response is a complete revised request
                        return response
                
            else:
                self._logger.warning("inline_feedback not available for clarification")
            
            return None
                
        except Exception as e:
            self._logger.error(f"Error getting user clarification: {str(e)}")
            return None
    
    def _update_request_with_clarification(
        self, 
        original_request: str, 
        clarification: str, 
        intent_clarification: IntentClarification
    ) -> str:
        """
        Update the original request with the clarified information.
        
        Args:
            original_request: Original user request
            clarification: User's clarification response
            intent_clarification: Original clarification object
            
        Returns:
            Updated request
        """
        ambiguity_type = intent_clarification.ambiguity_type
        
        if ambiguity_type == "file_reference":
            # Replace the ambiguous file reference with the clarified one
            context = intent_clarification.context
            if "file_reference" in context:
                ambiguous_ref = context["file_reference"]
                # Simple replacement (in practice, you might want a more sophisticated approach)
                return original_request.replace(ambiguous_ref, clarification)
            
        elif ambiguity_type == "entity_reference":
            # Replace the ambiguous entity reference with the clarified one
            context = intent_clarification.context
            if "entity_reference" in context:
                ambiguous_ref = context["entity_reference"]
                return original_request.replace(ambiguous_ref, clarification)
        
        elif ambiguity_type == "parameter_value":
            # Add or update the parameter value
            context = intent_clarification.context
            if "parameter_name" in context:
                param_name = context["parameter_name"]
                # Check if parameter already exists in the request
                if param_name in original_request:
                    # Try to update the existing parameter
                    param_pattern = f"{param_name}\\s*[=:]?\\s*\\S+"
                    updated = re.sub(
                        param_pattern, 
                        f"{param_name}={clarification}", 
                        original_request
                    )
                    if updated != original_request:
                        return updated
                
                # If not found or update failed, append the parameter
                return f"{original_request} {param_name}={clarification}"
        
        # For other types, or if the specific handling failed,
        # just append the clarification to the original request
        return f"{original_request} ({clarification})"
    
    async def _clarify_file_reference(
        self, 
        request: str, 
        ambiguity: Dict[str, Any], 
        interpretations: List[str], 
        context: Dict[str, Any]
    ) -> IntentClarification:
        """
        Create a clarification for ambiguous file references.
        
        Args:
            request: Original user request
            ambiguity: Ambiguity information
            interpretations: Possible interpretations
            context: Task context
            
        Returns:
            IntentClarification object
        """
        description = ambiguity.get("description", "")
        
        # Extract the ambiguous file reference
        file_reference = None
        
        # Try to find the ambiguous reference in the request
        match = re.search(r'(?:file|directory|folder|path|docs?)\s+["\']?([^"\']+)["\']?', description)
        if match:
            file_reference = match.group(1)
        
        # If not found, use a generic approach
        if not file_reference:
            # Use file_resolver to get possible matches
            from angela.context.file_resolver import file_resolver
            
            project_root = context.get("project_root")
            if project_root:
                # Get files in the project
                possible_files = await file_resolver.find_files(project_root)
                
                # Filter to the most relevant files based on the request
                relevant_files = []
                
                for file_path in possible_files:
                    # Check if any part of the file path appears in the request
                    file_parts = Path(file_path).parts
                    for part in file_parts:
                        if part in request:
                            relevant_files.append(str(file_path))
                            break
                
                # Limit to 5 options
                interpretations = [Path(f).name for f in relevant_files[:5]]
        
        # Create the clarification
        question = "Which file are you referring to?"
        if file_reference:
            question = f"I'm not sure which file '{file_reference}' refers to. Which one did you mean?"
        
        return IntentClarification(
            original_request=request,
            ambiguity_type="file_reference",
            ambiguity_details=description,
            clarification_question=question,
            options=interpretations,
            context={"file_reference": file_reference}
        )
    
    async def _clarify_entity_reference(
        self, 
        request: str, 
        ambiguity: Dict[str, Any], 
        interpretations: List[str], 
        context: Dict[str, Any]
    ) -> IntentClarification:
        """
        Create a clarification for ambiguous code entity references.
        
        Args:
            request: Original user request
            ambiguity: Ambiguity information
            interpretations: Possible interpretations
            context: Task context
            
        Returns:
            IntentClarification object
        """
        description = ambiguity.get("description", "")
        
        # Extract the ambiguous entity reference
        entity_reference = None
        
        # Try to find the ambiguous reference in the request
        match = re.search(r'(?:function|class|method|variable|object|module|component)\s+["\']?([^"\']+)["\']?', description)
        if match:
            entity_reference = match.group(1)
        
        # If semantic code information is available, try to find similar entities
        if "semantic_code" in context and entity_reference:
            semantic_code = context["semantic_code"]
            
            if "modules" in semantic_code:
                # Get all entities from the modules
                all_entities = []
                
                for module_info in semantic_code["modules"]:
                    # Add functions
                    for func_name in module_info.get("functions", {}):
                        all_entities.append({
                            "name": func_name,
                            "type": "function",
                            "file": module_info.get("filename")
                        })
                    
                    # Add classes
                    for class_name in module_info.get("classes", {}):
                        all_entities.append({
                            "name": class_name,
                            "type": "class",
                            "file": module_info.get("filename")
                        })
                        
                        # Add methods from the class
                        class_info = module_info.get("classes", {}).get(class_name, {})
                        for method_name in class_info.get("methods", {}):
                            all_entities.append({
                                "name": f"{class_name}.{method_name}",
                                "type": "method",
                                "file": module_info.get("filename")
                            })
                
                # Filter to entities with similar names
                import difflib
                
                similar_entities = []
                for entity in all_entities:
                    similarity = difflib.SequenceMatcher(None, entity_reference, entity["name"]).ratio()
                    if similarity > 0.6:
                        similar_entities.append(entity)
                
                # Sort by similarity
                similar_entities.sort(
                    key=lambda e: difflib.SequenceMatcher(None, entity_reference, e["name"]).ratio(),
                    reverse=True
                )
                
                # Update interpretations with the similar entities
                interpretations = [
                    f"{e['name']} ({e['type']} in {Path(e['file']).name})"
                    for e in similar_entities[:5]
                ]
        
        # Create the clarification
        question = "Which code entity are you referring to?"
        if entity_reference:
            question = f"I'm not sure which code entity '{entity_reference}' refers to. Which one did you mean?"
        
        return IntentClarification(
            original_request=request,
            ambiguity_type="entity_reference",
            ambiguity_details=description,
            clarification_question=question,
            options=interpretations,
            context={"entity_reference": entity_reference}
        )
    
    async def _clarify_action_type(
        self, 
        request: str, 
        ambiguity: Dict[str, Any], 
        interpretations: List[str], 
        context: Dict[str, Any]
    ) -> IntentClarification:
        """
        Create a clarification for ambiguous action types.
        
        Args:
            request: Original user request
            ambiguity: Ambiguity information
            interpretations: Possible interpretations
            context: Task context
            
        Returns:
            IntentClarification object
        """
        description = ambiguity.get("description", "")
        
        # If interpretations are provided, use them
        if not interpretations:
            # Default interpretations for action type
            interpretations = [
                "Show/display the content",
                "Edit/modify the content",
                "Create a new file/content",
                "Delete the file/content",
                "Analyze/examine the content"
            ]
        
        # Create the clarification
        question = f"I'm not sure what action you want to perform: {description}. What would you like to do?"
        
        return IntentClarification(
            original_request=request,
            ambiguity_type="action_type",
            ambiguity_details=description,
            clarification_question=question,
            options=interpretations,
            context={}
        )
    
    async def _clarify_operation_scope(
        self, 
        request: str, 
        ambiguity: Dict[str, Any], 
        interpretations: List[str], 
        context: Dict[str, Any]
    ) -> IntentClarification:
        """
        Create a clarification for ambiguous operation scopes.
        
        Args:
            request: Original user request
            ambiguity: Ambiguity information
            interpretations: Possible interpretations
            context: Task context
            
        Returns:
            IntentClarification object
        """
        description = ambiguity.get("description", "")
        
        # If interpretations are provided, use them
        if not interpretations:
            # Default interpretations for operation scope
            interpretations = [
                "Only the current file",
                "The entire directory",
                "All files matching a pattern",
                "The specific files mentioned",
                "The entire project"
            ]
        
        # Create the clarification
        question = f"I'm not sure about the scope of this operation: {description}. What scope do you want to apply?"
        
        return IntentClarification(
            original_request=request,
            ambiguity_type="operation_scope",
            ambiguity_details=description,
            clarification_question=question,
            options=interpretations,
            context={}
        )
    
    async def _clarify_step_ordering(
        self, 
        request: str, 
        ambiguity: Dict[str, Any], 
        interpretations: List[str], 
        context: Dict[str, Any]
    ) -> IntentClarification:
        """
        Create a clarification for ambiguous step ordering.
        
        Args:
            request: Original user request
            ambiguity: Ambiguity information
            interpretations: Possible interpretations
            context: Task context
            
        Returns:
            IntentClarification object
        """
        description = ambiguity.get("description", "")
        
        # Extract the conflicting steps if possible
        step1 = None
        step2 = None
        
        match = re.search(r'([^\s,]+)\s+(?:before|after)\s+([^\s,]+)', description)
        if match:
            step1 = match.group(1)
            step2 = match.group(2)
        
        # Create interpretations if not provided
        if not interpretations and step1 and step2:
            interpretations = [
                f"Do {step1} first, then {step2}",
                f"Do {step2} first, then {step1}",
                f"Do {step1} and {step2} in parallel",
                f"Only do {step1}, skip {step2}",
                f"Only do {step2}, skip {step1}"
            ]
        elif not interpretations:
            # Generic interpretations
            interpretations = [
                "Follow the steps in the order listed",
                "Reverse the order of steps",
                "Only do the first step",
                "Only do the last step",
                "Skip steps that seem risky"
            ]
        
        # Create the clarification
        question = f"I'm not sure about the order of steps: {description}. How should I proceed?"
        
        return IntentClarification(
            original_request=request,
            ambiguity_type="step_ordering",
            ambiguity_details=description,
            clarification_question=question,
            options=interpretations,
            context={"step1": step1, "step2": step2}
        )
    
    async def _clarify_parameter_value(
        self, 
        request: str, 
        ambiguity: Dict[str, Any], 
        interpretations: List[str], 
        context: Dict[str, Any]
    ) -> IntentClarification:
        """
        Create a clarification for ambiguous parameter values.
        
        Args:
            request: Original user request
            ambiguity: Ambiguity information
            interpretations: Possible interpretations
            context: Task context
            
        Returns:
            IntentClarification object
        """
        description = ambiguity.get("description", "")
        
        # Extract the parameter name if available
        param_name = None
        
        match = re.search(r'parameter\s+["\']?([^"\']+)["\']?', description)
        if match:
            param_name = match.group(1)
        
        # If not found through "parameter", try "value"
        if not param_name:
            match = re.search(r'value\s+(?:for|of)\s+["\']?([^"\']+)["\']?', description)
            if match:
                param_name = match.group(1)
        
        # Create the clarification
        question = f"I need a value for the parameter: {param_name or description}. What should it be?"
        
        return IntentClarification(
            original_request=request,
            ambiguity_type="parameter_value",
            ambiguity_details=description,
            clarification_question=question,
            options=interpretations,
            context={"parameter_name": param_name}
        )
    
    async def _decompose_goal(
        self, 
        request: str, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decompose a complex goal into sub-goals.
        
        Args:
            request: User request
            intent_analysis: Intent analysis results
            context: Task context
            
        Returns:
            Dictionary with goal decomposition
        """
        # If the intent is already simple, no need to decompose
        if intent_analysis.get("complexity", "simple") == "simple":
            return {
                "main_goal": intent_analysis.get("primary_goal", request),
                "complexity": "simple",
                "sub_goals": [intent_analysis.get("primary_goal", request)],
                "sequential": True
            }
        
        # Start with the sub-tasks from the intent analysis
        sub_tasks = intent_analysis.get("sub_tasks", [])
        
        # For complex intentions, do a more detailed decomposition
        if intent_analysis.get("complexity", "simple") == "complex" or len(sub_tasks) < 2:
            # Create a prompt for the AI to decompose the goal
            prompt = f"""
You need to decompose a complex user request into clear, logical sub-goals that can be executed sequentially or in parallel.

USER REQUEST: "{request}"

ANALYZED INTENT:
- Primary Goal: {intent_analysis.get("primary_goal", request)}
- Intent Type: {intent_analysis.get("intent_type", "unknown")}
- Complexity: {intent_analysis.get("complexity", "complex")}

Break this request down into 2-7 clear, logical sub-goals that together will accomplish the main goal.
For each sub-goal, indicate:
1. A clear description of what needs to be done
2. Whether it depends on other sub-goals
3. The estimated complexity (simple, moderate, complex)

Return your decomposition as a JSON object with this structure:
```json
{{
  "main_goal": "Clear description of the main objective",
  "complexity": "complex|moderate",
  "sub_goals": [
    {{
      "id": "sg1",
      "description": "Sub-goal description",
      "dependencies": ["sg0"],
      "complexity": "simple|moderate|complex",
      "estimated_steps": 1-5
    }}
  ],
  "sequential": true|false,
  "explanation": "Brief explanation of the decomposition approach"
}}
```

If the goals must be executed in a specific order, set "sequential" to true and ensure the sub_goals are in the correct execution order.
If some goals can be executed in parallel, set "sequential" to false and use dependencies to indicate required ordering.
"""
            
            # Call AI to decompose the goal
            api_request = GeminiRequest(
                prompt=prompt,
                temperature=0.2,
                max_tokens=3000
            )
            
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            try:
                # Try to extract JSON from the response
                response_text = response.text
                
                # Look for JSON block
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                
                # Try to parse the JSON
                decomposition = json.loads(response_text)
                
                # Add some metadata to the decomposition
                decomposition["original_request"] = request
                decomposition["intent_type"] = intent_analysis.get("intent_type", "unknown")
                
                return decomposition
                
            except (json.JSONDecodeError, IndexError) as e:
                self._logger.error(f"Error parsing goal decomposition response: {str(e)}")
        
        # If we get here, use a simple decomposition based on the intent analysis
        return {
            "main_goal": intent_analysis.get("primary_goal", request),
            "complexity": intent_analysis.get("complexity", "moderate"),
            "sub_goals": [
                {
                    "id": f"sg{i}",
                    "description": sub_task,
                    "dependencies": [] if i == 0 else [f"sg{i-1}"],
                    "complexity": "simple",
                    "estimated_steps": 1
                }
                for i, sub_task in enumerate(sub_tasks)
            ],
            "sequential": True,
            "explanation": "Simple sequential decomposition based on intent analysis",
            "original_request": request,
            "intent_type": intent_analysis.get("intent_type", "unknown")
        }
    
    async def _create_execution_plan(
        self, 
        request: str, 
        goal_decomposition: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an execution plan for the decomposed goal.
        
        Args:
            request: User request
            goal_decomposition: Goal decomposition
            context: Task context
            
        Returns:
            Dictionary with plan creation results
        """
        # For simple goals, use basic planning
        if goal_decomposition.get("complexity", "simple") == "simple":
            # Call the enhanced planner directly
            plan = await self._enhanced_planner.plan_task(
                request=request,
                context=context,
                complexity="auto"
            )
            
            return {
                "plan": plan,
                "plan_type": "simple",
                "plan_id": getattr(plan, "id", str(uuid.uuid4())),
                "estimated_steps": len(getattr(plan, "steps", [])),
                "max_risk_level": max(
                    [getattr(step, "estimated_risk", 0) for step in getattr(plan, "steps", {}).values()],
                    default=0
                ) if hasattr(plan, "steps") else 0
            }
        
        # For complex goals, create a more sophisticated plan
        # This is where we'd build a more complex execution plan
        # based on the goal decomposition
        
        # Extract the sub-goals
        sub_goals = goal_decomposition.get("sub_goals", [])
        sequential = goal_decomposition.get("sequential", True)
        
        if sequential:
            # For sequential execution, create a single plan with all steps
            combined_request = f"{request}\n\nExecute these steps in order:\n"
            for i, sub_goal in enumerate(sub_goals):
                combined_request += f"{i+1}. {sub_goal.get('description', '')}\n"
            
            plan = await self._enhanced_planner.plan_task(
                request=combined_request,
                context=context,
                complexity="advanced"
            )
            
            return {
                "plan": plan,
                "plan_type": "advanced_sequential",
                "plan_id": getattr(plan, "id", str(uuid.uuid4())),
                "estimated_steps": len(getattr(plan, "steps", [])),
                "max_risk_level": max(
                    [getattr(step, "estimated_risk", 0) for step in getattr(plan, "steps", {}).values()],
                    default=0
                ) if hasattr(plan, "steps") else 0
            }
            
        else:
            # For non-sequential execution, create a plan with dependencies
            # This requires a more sophisticated planning approach
            # that accounts for the dependencies between sub-goals
            
            # Generate a dependency-aware prompt
            dependency_prompt = f"{request}\n\nExecute these steps with the following dependencies:\n"
            for sub_goal in sub_goals:
                sg_id = sub_goal.get("id", "")
                description = sub_goal.get("description", "")
                dependencies = sub_goal.get("dependencies", [])
                
                if dependencies:
                    dependency_prompt += f"- {description} (depends on: {', '.join(dependencies)})\n"
                else:
                    dependency_prompt += f"- {description} (no dependencies)\n"
            
            plan = await self._enhanced_planner.plan_task(
                request=dependency_prompt,
                context=context,
                complexity="advanced"
            )
            
            return {
                "plan": plan,
                "plan_type": "advanced_dependency",
                "plan_id": getattr(plan, "id", str(uuid.uuid4())),
                "estimated_steps": len(getattr(plan, "steps", [])),
                "max_risk_level": max(
                    [getattr(step, "estimated_risk", 0) for step in getattr(plan, "steps", {}).values()],
                    default=0
                ) if hasattr(plan, "steps") else 0
            }
    
    async def _enhance_context_with_semantics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance context with semantic code information.
        
        Args:
            context: Task context
            
        Returns:
            Enhanced context
        """
        enhanced_context = dict(context)
        
        # Check if project root is available
        project_root = context.get("project_root")
        if not project_root:
            return enhanced_context
        
        try:
            # Add semantic code information
            semantic_info = {
                "modules": [],
                "key_entities": []
            }
            
            # Get recently accessed files from context
            recent_files = []
            if "recent_files" in context and "accessed" in context["recent_files"]:
                recent_files = context["recent_files"]["accessed"]
            
            # Prioritize recently accessed files for semantic analysis
            for file_path in recent_files[:3]:  # Limit to 3 for performance
                module = await semantic_analyzer.analyze_file(file_path)
                if module:
                    semantic_info["modules"].append(module.get_summary())
                    
                    # Add key entities from this module
                    for func_name, func in module.functions.items():
                        semantic_info["key_entities"].append({
                            "name": func_name,
                            "type": "function",
                            "filename": func.filename,
                            "line_start": func.line_start,
                            "line_end": func.line_end
                        })
                    
                    for class_name, cls in module.classes.items():
                        semantic_info["key_entities"].append({
                            "name": class_name,
                            "type": "class",
                            "filename": cls.filename,
                            "line_start": cls.line_start,
                            "line_end": cls.line_end
                        })
            
            # Add project state information
            project_state = await project_state_analyzer.get_project_state(project_root)
            
            # Add the semantic information and project state to the context
            enhanced_context["semantic_code"] = semantic_info
            enhanced_context["project_state"] = project_state
            
            return enhanced_context
            
        except Exception as e:
            self._logger.error(f"Error enhancing context with semantics: {str(e)}")
            return enhanced_context

# Global semantic task planner instance
semantic_task_planner = SemanticTaskPlanner()
