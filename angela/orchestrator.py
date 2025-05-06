"""
Main orchestration service for Angela CLI.

This module coordinates all the components of Angela CLI, from receiving
user requests to executing commands with safety checks.
"""
import asyncio
from typing import Dict, Any, Optional, List, Tuple

from angela.ai.client import gemini_client, GeminiRequest
from angela.ai.prompts import build_prompt
from angela.ai.parser import parse_ai_response, CommandSuggestion
from angela.ai.file_integration import extract_file_operation, execute_file_operation
from angela.context import context_manager
from angela.execution.engine import execution_engine
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class Orchestrator:
    """Main orchestration service for Angela CLI."""
    
    def __init__(self):
        self._logger = logger
    
    async def process_request(
        self, 
        request: str, 
        execute: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process a request from the user."""
        # Refresh context to ensure we have the latest information
        context_manager.refresh_context()
        context = context_manager.get_context_dict()
        
        self._logger.info(f"Processing request: {request}")
        self._logger.debug(f"Context: {context}")
        
        try:
            # Get command suggestion from AI
            suggestion = await self._get_ai_suggestion(request, context)
            
            result = {
                "request": request,
                "suggestion": suggestion,
                "context": context,
            }
            
            # Execute the command if requested
            if execute or dry_run:
                self._logger.info(f"{'Dry run' if dry_run else 'Executing'} suggested command: {suggestion.command}")
                
                # Check if this is a file operation that we can handle directly
                file_operation = await extract_file_operation(suggestion.command)
                
                if file_operation:
                    # Handle file operation directly
                    operation_type, parameters = file_operation
                    self._logger.info(f"Extracted file operation: {operation_type}")
                    
                    operation_result = await execute_file_operation(
                        operation_type, parameters, dry_run=dry_run
                    )
                    
                    result["file_operation"] = operation_result
                    result["execution"] = {
                        "stdout": f"File operation executed: {operation_type}",
                        "stderr": operation_result.get("error", ""),
                        "return_code": 0 if operation_result.get("success", False) else 1,
                        "success": operation_result.get("success", False),
                        "dry_run": dry_run
                    }
                    
                    # If it's a read operation and successful, add content to stdout
                    if operation_type == "read_file" and operation_result.get("success", False):
                        result["execution"]["stdout"] = operation_result.get("content", "")
                else:
                    # Regular command execution
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        suggestion.command,
                        check_safety=True,
                        dry_run=dry_run
                    )
                    
                    result["execution"] = {
                        "stdout": stdout,
                        "stderr": stderr,
                        "return_code": return_code,
                        "success": return_code == 0,
                        "dry_run": dry_run
                    }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error processing request: {str(e)}")
            # Fallback to old behavior if AI service fails
            return {
                "request": request,
                "response": f"Echo: {request}",
                "error": str(e),
                "context": context,
            }
    
    async def _get_ai_suggestion(self, request: str, context: Dict[str, Any]) -> CommandSuggestion:
        """Get a command suggestion from the AI service."""
        # Build prompt with context
        prompt = build_prompt(request, context)
        
        # Create a request to the Gemini API
        api_request = GeminiRequest(prompt=prompt)
        
        # Call the Gemini API
        self._logger.info("Sending request to Gemini API")
        api_response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        suggestion = parse_ai_response(api_response.text)
        
        self._logger.info(f"Received suggestion: {suggestion.command}")
        return suggestion
    
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

# Global orchestrator instance
orchestrator = Orchestrator()

# Synchronous wrapper for backwards compatibility
def process_request(request: str) -> Dict[str, Any]:
    """Synchronous wrapper for processing a request."""
    return asyncio.run(orchestrator.process_request(request))
