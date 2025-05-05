# angela/orchestrator.py
"""
Main orchestration service for Angela CLI.
"""
from typing import List, Dict, Any, Optional

from angela.context import context_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """
    Main orchestration service for Angela CLI.
    
    Responsible for:
    - Receiving requests from the CLI
    - Updating context information
    - Processing requests (future: send to AI service)
    - Executing actions (future)
    - Returning results
    """
    
    def __init__(self):
        self._logger = logger
    
    def process_request(self, request: str) -> Dict[str, Any]:
        """
        Process a request from the user.
        
        For MVP Phase 1, this simply echoes the request back with some context info.
        Future versions will send the request to the AI service for processing.
        
        Args:
            request: The user's natural language request.
            
        Returns:
            A dictionary with the response information.
        """
        # Refresh context to ensure we have the latest information
        context_manager.refresh_context()
        context = context_manager.get_context_dict()
        
        self._logger.info(f"Processing request: {request}")
        self._logger.debug(f"Context: {context}")
        
        # For MVP Phase 1, just echo the request back
        return {
            "request": request,
            "response": f"Echo: {request}",
            "context": context,
        }


# Global orchestrator instance
orchestrator = Orchestrator()
