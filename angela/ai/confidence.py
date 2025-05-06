# angela/ai/confidence.py

import re
from typing import Dict, Any, List, Tuple, Optional

from angela.context.history import history_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class ConfidenceScorer:
    """
    System for scoring confidence in natural language understanding
    and command suggestions.
    """
    
    def __init__(self):
        """Initialize the confidence scorer."""
        self._logger = logger
    
    def score_command_confidence(
        self, 
        request: str, 
        command: str, 
        context: Dict[str, Any]
    ) -> float:
        """
        Score confidence in a command suggestion.
        
        Args:
            request: The original request
            command: The suggested command
            context: Context information
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence starts at 0.7 (moderate default)
        confidence = 0.7
        
        # 1. Check if similar commands have been used before
        historical_confidence = self._check_history(command)
        
        # 2. Check command complexity vs. request complexity
        complexity_confidence = self._check_complexity(request, command)
        
        # 3. Check for entity matches
        entity_confidence = self._check_entities(request, command, context)
        
        # 4. Check for flags/options that seem out of place
        flags_confidence = self._check_command_flags(command)
        
        # Combine all factors (with weights)
        confidence = (
            0.3 * historical_confidence + 
            0.3 * complexity_confidence + 
            0.3 * entity_confidence + 
            0.1 * flags_confidence
        )
        
        # Ensure we stay in valid range
        confidence = min(1.0, max(0.0, confidence))
        
        self._logger.debug(f"Command confidence: {confidence:.2f} (hist: {historical_confidence:.2f}, " 
                          f"comp: {complexity_confidence:.2f}, ent: {entity_confidence:.2f}, " 
                          f"flags: {flags_confidence:.2f})")
        
        return confidence
    
    def _check_history(self, command: str) -> float:
        """
        Check if similar commands have been used before.
        
        Args:
            command: The suggested command
            
        Returns:
            Confidence score component (0.0-1.0)
        """
        # Extract the base command (first word)
        base_command = command.split()[0] if command else ""
        
        # Get frequency of this base command
        frequency = history_manager.get_command_frequency(base_command)
        
        # Get success rate
        success_rate = history_manager.get_command_success_rate(base_command)
        
        # Calculate confidence based on frequency and success rate
        if frequency == 0:
            return 0.5  # Neutral for new commands
            
        # Scale based on frequency (up to 10 uses)
        frequency_factor = min(frequency / 10.0, 1.0)
        
        # Combine with success rate
        return 0.5 + (0.5 * frequency_factor * success_rate)
    
    def _check_complexity(self, request: str, command: str) -> float:
        """
        Check if command complexity matches request complexity.
        
        Args:
            request: The original request
            command: The suggested command
            
        Returns:
            Confidence score component (0.0-1.0)
        """
        # Simple heuristic: count tokens in request and command
        request_tokens = len(request.split())
        command_tokens = len(command.split())
        
        # Very simple requests should lead to simple commands
        if request_tokens <= 3 and command_tokens > 10:
            return 0.4  # Low confidence for complex command from simple request
            
        # Complex requests might lead to complex commands
        if request_tokens >= 10 and command_tokens <= 3:
            return 0.6  # Moderate confidence for simple command from complex request
            
        # Ideal ratio is roughly 1:1 to 1:2
        ratio = command_tokens / max(1, request_tokens)
        if 0.5 <= ratio <= 2.0:
            return 0.9  # High confidence when complexity matches
        elif 0.25 <= ratio <= 4.0:
            return 0.7  # Moderate confidence for reasonable mismatch
        else:
            return 0.5  # Low confidence for significant mismatch
    
    def _check_entities(
        self, 
        request: str, 
        command: str, 
        context: Dict[str, Any]
    ) -> float:
        """
        Check if entities in the request match those in the command.
        
        Args:
            request: The original request
            command: The suggested command
            context: Context information
            
        Returns:
            Confidence score component (0.0-1.0)
        """
        # Extract potential entities from request (simple approach)
        request_words = set(request.lower().split())
        
        # Check for important entities
        file_mentions = any(word in request_words for word in ["file", "files", "document", "text"])
        dir_mentions = any(word in request_words for word in ["directory", "folder", "dir"])
        
        # Check if command matches the entity types mentioned
        if file_mentions and not any(ext in command for ext in [".txt", ".md", ".py", ".js", ".html"]):
            return 0.5  # Request mentions files but command doesn't seem to deal with files
            
        if dir_mentions and not any(cmd in command for cmd in ["cd", "mkdir", "rmdir", "ls"]):
            return 0.6  # Request mentions directories but command doesn't seem to deal with directories
        
        # Check for specific paths or filenames
        # This is a simplified approach - real implementation would use regex
        path_pattern = r'[\w/\.-]+'
        request_paths = re.findall(path_pattern, request)
        command_paths = re.findall(path_pattern, command)
        
        if request_paths and not any(rp in command for rp in request_paths):
            return 0.7  # Paths mentioned in request don't appear in command
        
        # Default - reasonable confidence
        return 0.8
    
    def _check_command_flags(self, command: str) -> float:
        """
        Check for unusual flag combinations or invalid options.
        
        Args:
            command: The suggested command
            
        Returns:
            Confidence score component (0.0-1.0)
        """
        # This would ideally have a database of valid flags for common commands
        # For now, just do some basic checks
        
        # Check for potentially conflicting flags
        if "-r" in command and "--no-recursive" in command:
            return 0.3  # Conflicting flags
            
        if "-f" in command and "--interactive" in command:
            return 0.4  # Potentially conflicting (force vs. interactive)
        
        # Check for unusual combinations
        if "rm" in command and "-p" in command:
            return 0.5  # Unusual flag for rm
            
        if "cp" in command and "-l" in command:
            return 0.6  # Unusual flag for cp
        
        # Default - high confidence
        return 0.9

# Global confidence scorer instance
confidence_scorer = ConfidenceScorer()
