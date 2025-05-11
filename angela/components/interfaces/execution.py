# angela/interfaces/execution.py
"""Interfaces for execution components."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

class CommandExecutor(ABC):
    """Interface for command execution."""
    
    @abstractmethod
    async def execute_command(
        self,
        command: str,
        check_safety: bool = True,
        dry_run: bool = False
    ) -> Tuple[str, str, int]:
        """
        Execute a shell command and return its output.
        
        Args:
            command: The shell command to execute
            check_safety: Whether to perform safety checks
            dry_run: Whether to simulate execution
            
        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        pass

class AdaptiveExecutor(ABC):
    """Interface for adaptive command execution."""
    
    @abstractmethod
    async def execute_command(
        self,
        command: str,
        natural_request: str,
        explanation: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a command with adaptive behavior.
        
        Args:
            command: The command to execute
            natural_request: The original natural language request
            explanation: AI explanation of what the command does
            dry_run: Whether to simulate the command without execution
            
        Returns:
            Dictionary with execution results
        """
        pass
