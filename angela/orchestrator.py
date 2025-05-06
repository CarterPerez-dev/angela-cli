# angela/orchestrator.py
import asyncio
from typing import Dict, Any

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
    
    async def process_request(self, request: str, execute: bool = False) -> Dict[str, Any]:
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
            if execute:
                self._logger.info(f"Executing suggested command: {suggestion.command}")
                stdout, stderr, return_code = await execution_engine.execute_command(suggestion.command)
                
                result["execution"] = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "return_code": return_code,
                    "success": return_code == 0
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

# Global orchestrator instance
orchestrator = Orchestrator()

# Synchronous wrapper for backwards compatibility
def process_request(request: str) -> Dict[str, Any]:
    """Synchronous wrapper for processing a request."""
    return asyncio.run(orchestrator.process_request(request))
