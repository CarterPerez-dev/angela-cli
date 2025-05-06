"""
Main orchestration service for Angela CLI.

This module coordinates all the components of Angela CLI, from receiving
user requests to executing commands with safety checks.
"""
import asyncio
from typing import Dict, Any, Optional, List

from angela.ai.client import gemini_client, GeminiRequest
from angela.ai.prompts import build_prompt
from angela.ai.parser import parse_ai_response, CommandSuggestion
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
                
                # Execute with safety checks enabled
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
        # Import here to avoid circular imports
        from angela.execution.filesystem import (
            create_directory, delete_directory, create_file,
            read_file, write_file, delete_file, copy_file, move_file,
            FileSystemError
        )
        
        self._logger.info(f"Processing file operation: {operation}")
        self._logger.debug(f"Parameters: {parameters}")
        
        try:
            result = {
                "operation": operation,
                "parameters": parameters,
                "success": False,
                "dry_run": dry_run,
            }
            
            # Execute the appropriate operation
            if operation == "create_directory":
                path = parameters.get("path")
                parents = parameters.get("parents", True)
                
                success = await create_directory(path, parents=parents, dry_run=dry_run)
                result["success"] = success
                
            elif operation == "delete_directory":
                path = parameters.get("path")
                recursive = parameters.get("recursive", False)
                force = parameters.get("force", False)
                
                success = await delete_directory(
                    path, recursive=recursive, force=force, dry_run=dry_run
                )
                result["success"] = success
                
            elif operation == "create_file":
                path = parameters.get("path")
                content = parameters.get("content")
                
                success = await create_file(path, content=content, dry_run=dry_run)
                result["success"] = success
                
            elif operation == "read_file":
                path = parameters.get("path")
                binary = parameters.get("binary", False)
                
                content = await read_file(path, binary=binary)
                result["content"] = content
                result["success"] = True
                
            elif operation == "write_file":
                path = parameters.get("path")
                content = parameters.get("content", "")
                append = parameters.get("append", False)
                
                success = await write_file(
                    path, content, append=append, dry_run=dry_run
                )
                result["success"] = success
                
            elif operation == "delete_file":
                path = parameters.get("path")
                force = parameters.get("force", False)
                
                success = await delete_file(path, force=force, dry_run=dry_run)
                result["success"] = success
                
            elif operation == "copy_file":
                source = parameters.get("source")
                destination = parameters.get("destination")
                overwrite = parameters.get("overwrite", False)
                
                success = await copy_file(
                    source, destination, overwrite=overwrite, dry_run=dry_run
                )
                result["success"] = success
                
            elif operation == "move_file":
                source = parameters.get("source")
                destination = parameters.get("destination")
                overwrite = parameters.get("overwrite", False)
                
                success = await move_file(
                    source, destination, overwrite=overwrite, dry_run=dry_run
                )
                result["success"] = success
                
            else:
                self._logger.warning(f"Unknown file operation: {operation}")
                result["error"] = f"Unknown file operation: {operation}"
            
            return result
            
        except FileSystemError as e:
            self._logger.exception(f"Error processing file operation: {str(e)}")
            return {
                "operation": operation,
                "parameters": parameters,
                "success": False,
                "error": str(e),
                "dry_run": dry_run,
            }
        except Exception as e:
            self._logger.exception(f"Unexpected error in file operation: {str(e)}")
            return {
                "operation": operation,
                "parameters": parameters,
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "dry_run": dry_run,
            }

# Global orchestrator instance
orchestrator = Orchestrator()

# Synchronous wrapper for backwards compatibility
def process_request(request: str) -> Dict[str, Any]:
    """Synchronous wrapper for processing a request."""
    return asyncio.run(orchestrator.process_request(request))
