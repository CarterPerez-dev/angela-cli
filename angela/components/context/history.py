# angela/context/history.py

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from angela.config import config_manager
from angela.utils.logging import get_logger
from angela.context.preferences import preferences_manager

logger = get_logger(__name__)

class CommandRecord:
    """Record of a command execution."""
    
    def __init__(
        self,
        command: str,
        natural_request: str,
        success: bool,
        timestamp: Optional[datetime] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
        risk_level: int = 0
    ):
        self.command = command
        self.natural_request = natural_request
        self.success = success
        self.timestamp = timestamp or datetime.now()
        self.output = output
        self.error = error
        self.risk_level = risk_level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a dictionary for storage."""
        return {
            "command": self.command,
            "natural_request": self.natural_request,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "output": self.output,
            "error": self.error,
            "risk_level": self.risk_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandRecord':
        """Create a record from a dictionary."""
        return cls(
            command=data["command"],
            natural_request=data["natural_request"],
            success=data["success"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            output=data.get("output"),
            error=data.get("error"),
            risk_level=data.get("risk_level", 0)
        )


class CommandPattern:
    """Pattern of commands executed by the user."""
    
    def __init__(self, base_command: str, count: int = 1, success_rate: float = 1.0):
        self.base_command = base_command
        self.count = count
        self.success_rate = success_rate
        self.last_used = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the pattern to a dictionary for storage."""
        return {
            "base_command": self.base_command,
            "count": self.count,
            "success_rate": self.success_rate,
            "last_used": self.last_used.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandPattern':
        """Create a pattern from a dictionary."""
        pattern = cls(
            base_command=data["base_command"],
            count=data["count"],
            success_rate=data["success_rate"]
        )
        pattern.last_used = datetime.fromisoformat(data["last_used"])
        return pattern


class HistoryManager:
    """Manager for command history and pattern analysis."""
    
    def __init__(self):
        """Initialize the history manager."""
        self._history_file = config_manager.CONFIG_DIR / "command_history.json"
        self._patterns_file = config_manager.CONFIG_DIR / "command_patterns.json"
        self._history: List[CommandRecord] = []
        self._patterns: Dict[str, CommandPattern] = {}
        self._load_history()
        self._load_patterns()
    
    def _load_history(self) -> None:
        """Load history from file."""
        try:
            if self._history_file.exists():
                with open(self._history_file, "r") as f:
                    data = json.load(f)
                    self._history = [CommandRecord.from_dict(item) for item in data]
                logger.debug(f"Loaded {len(self._history)} history items")
                
                # Trim history if needed
                max_items = preferences_manager.preferences.context.max_history_items
                if len(self._history) > max_items:
                    self._history = self._history[-max_items:]
                    self._save_history()  # Save the trimmed history
            else:
                logger.debug("No history file found")
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            self._history = []
    
    def _load_patterns(self) -> None:
        """Load command patterns from file."""
        try:
            if self._patterns_file.exists():
                with open(self._patterns_file, "r") as f:
                    data = json.load(f)
                    self._patterns = {k: CommandPattern.from_dict(v) for k, v in data.items()}
                logger.debug(f"Loaded {len(self._patterns)} command patterns")
            else:
                logger.debug("No patterns file found")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            self._patterns = {}
    
    def _save_history(self) -> None:
        """Save history to file."""
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, "w") as f:
                json.dump([item.to_dict() for item in self._history], f, indent=2)
            logger.debug(f"Saved history with {len(self._history)} items")
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def _save_patterns(self) -> None:
        """Save command patterns to file."""
        try:
            self._patterns_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._patterns_file, "w") as f:
                json.dump({k: v.to_dict() for k, v in self._patterns.items()}, f, indent=2)
            logger.debug(f"Saved {len(self._patterns)} command patterns")
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")
    
    def add_command(
        self, 
        command: str, 
        natural_request: str, 
        success: bool,
        output: Optional[str] = None,
        error: Optional[str] = None,
        risk_level: int = 0
    ) -> None:
        """
        Add a command to the history.
        
        Args:
            command: The shell command executed
            natural_request: The natural language request
            success: Whether the command executed successfully
            output: Command output (if any)
            error: Command error (if any)
            risk_level: Risk level of the command
        """
        # Create and add the record
        record = CommandRecord(
            command=command,
            natural_request=natural_request,
            success=success,
            output=output,
            error=error,
            risk_level=risk_level
        )
        self._history.append(record)
        
        # Save the updated history
        self._save_history()
        
        # Update patterns if enabled
        if preferences_manager.preferences.context.auto_learn_patterns:
            self._update_patterns(record)
    
    def _extract_base_command(self, command: str) -> str:
        """
        Extract the base command without arguments.
        
        Args:
            command: The full command string
            
        Returns:
            The base command
        """
        # Extract the first word (command name)
        base = command.strip().split()[0]
        
        # For some commands, include the first argument if it's an operation
        if base in ["git", "docker", "npm", "pip", "apt", "apt-get"]:
            parts = command.strip().split()
            if len(parts) > 1 and not parts[1].startswith("-"):
                base = f"{base} {parts[1]}"
        
        return base
    
    def _update_patterns(self, record: CommandRecord) -> None:
        """
        Update command patterns based on a new record.
        
        Args:
            record: The command record
        """
        base_command = self._extract_base_command(record.command)
        
        if base_command in self._patterns:
            # Update existing pattern
            pattern = self._patterns[base_command]
            pattern.count += 1
            pattern.last_used = record.timestamp
            
            # Update success rate
            success_weight = 1.0 / pattern.count  # Weight of the new record
            pattern.success_rate = (
                (pattern.success_rate * (1 - success_weight)) + 
                (1.0 if record.success else 0.0) * success_weight
            )
        else:
            # Create new pattern
            self._patterns[base_command] = CommandPattern(
                base_command=base_command,
                count=1,
                success_rate=1.0 if record.success else 0.0
            )
        
        # Save updated patterns
        self._save_patterns()
    
    def get_recent_commands(self, limit: int = 10) -> List[CommandRecord]:
        """
        Get the most recent commands.
        
        Args:
            limit: Maximum number of commands to return
            
        Returns:
            List of recent CommandRecord objects
        """
        return self._history[-limit:]
    
    def get_command_frequency(self, command: str) -> int:
        """
        Get the frequency of a command.
        
        Args:
            command: The command to check
            
        Returns:
            The number of times the command has been executed
        """
        base_command = self._extract_base_command(command)
        pattern = self._patterns.get(base_command)
        return pattern.count if pattern else 0
    
    def get_command_success_rate(self, command: str) -> float:
        """
        Get the success rate of a command.
        
        Args:
            command: The command to check
            
        Returns:
            The success rate (0.0-1.0) or 0.0 if command not found
        """
        base_command = self._extract_base_command(command)
        pattern = self._patterns.get(base_command)
        return pattern.success_rate if pattern else 0.0
    
    def search_similar_command(self, request: str) -> Optional[str]:
        """
        Search for a similar command in history based on natural language request.
        
        Args:
            request: The natural language request
            
        Returns:
            A similar command if found, None otherwise
        """
        # Simple similarity: lowercase and remove punctuation
        request = re.sub(r'[^\w\s]', '', request.lower())
        
        for record in reversed(self._history):  # Start from most recent
            historical_request = re.sub(r'[^\w\s]', '', record.natural_request.lower())
            
            # Check for significant overlap in words
            request_words = set(request.split())
            historical_words = set(historical_request.split())
            
            # Calculate Jaccard similarity
            if request_words and historical_words:
                intersection = request_words.intersection(historical_words)
                union = request_words.union(historical_words)
                similarity = len(intersection) / len(union)
                
                # If similarity is high enough, return this command
                if similarity > 0.6:
                    return record.command
        
        return None
    
    def find_error_patterns(self, error: str) -> List[Tuple[str, str]]:
        """
        Find patterns in error messages and corresponding fixes.
        
        Args:
            error: The error message
            
        Returns:
            List of (failed_command, successful_fix) tuples
        """
        error_patterns = []
        
        # Find failed commands with this error
        for i, record in enumerate(self._history):
            if not record.success and record.error and error in record.error:
                # Look ahead for successful fixes
                for j in range(i+1, min(i+5, len(self._history))):
                    if self._history[j].success:
                        error_patterns.append((record.command, self._history[j].command))
                        break
        
        return error_patterns
    
    def get_common_command_contexts(self) -> Dict[str, List[str]]:
        """
        Get common command sequences or contexts.
        
        Returns:
            Dict mapping commands to commonly following commands
        """
        context_map = defaultdict(Counter)
        
        # Analyze command sequences
        for i in range(1, len(self._history)):
            prev_cmd = self._extract_base_command(self._history[i-1].command)
            curr_cmd = self._extract_base_command(self._history[i].command)
            context_map[prev_cmd][curr_cmd] += 1
        
        # Convert to more usable format
        result = {}
        for cmd, followers in context_map.items():
            # Get the most common followers
            result[cmd] = [cmd for cmd, count in followers.most_common(3)]
        
        return result

# Global history manager instance
history_manager = HistoryManager()
