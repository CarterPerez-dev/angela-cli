# angela/components/interfaces/safety.pyy
"""Interfaces for safety components."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class SafetyValidator(ABC):
    """Interface for safety validation."""
    
    @abstractmethod
    async def check_command_safety(self, command: str, dry_run: bool = False) -> bool:
        """
        Check if a command is safe to execute.
        
        Args:
            command: The shell command to check
            dry_run: Whether this is a dry run
            
        Returns:
            True if the command is safe and confirmed, False otherwise
        """
        pass

    @abstractmethod
    def validate_command_safety(self, command: str) -> Tuple[bool, str]:
        """
        Validate a command against safety rules.
        
        Args:
            command: The shell command to validate
            
        Returns:
            A tuple of (is_valid, error_message or None)
        """
        pass
