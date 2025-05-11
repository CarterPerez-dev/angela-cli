# angela/context/session.py

import json
import time
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

from angela.api.context import get_preferences_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class EntityReference:
    """A reference to an entity in the session context."""
    name: str  # Name or identifier of the entity
    type: str  # Type of entity (file, directory, command, result, etc.)
    value: str  # Actual value or path 
    created: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "created": self.created.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityReference':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            type=data["type"],
            value=data["value"],
            created=datetime.fromisoformat(data["created"])
        )


class SessionMemory:
    """Memory for a single conversation session."""
    
    def __init__(self):
        """Initialize session memory."""
        self.entities: Dict[str, EntityReference] = {}
        self.recent_commands: List[str] = []
        self.recent_results: List[str] = []
        self.created = datetime.now()
        self.last_accessed = datetime.now()
    
    def add_entity(self, name: str, entity_type: str, value: str) -> None:
        """
        Add an entity to the session memory.
        
        Args:
            name: The name or identifier of the entity
            entity_type: The type of entity
            value: The value or path of the entity
        """
        self.entities[name] = EntityReference(name, entity_type, value)
        self.last_accessed = datetime.now()
    
    def get_entity(self, name: str) -> Optional[EntityReference]:
        """
        Get an entity from the session memory.
        
        Args:
            name: The name or identifier of the entity
            
        Returns:
            The entity reference, or None if not found
        """
        self.last_accessed = datetime.now()
        return self.entities.get(name)
    
    def add_command(self, command: str) -> None:
        """
        Add a command to the recent commands list.
        
        Args:
            command: The command string
        """
        self.recent_commands.append(command)
        self.last_accessed = datetime.now()
        
        # Keep only the last 10 commands
        if len(self.recent_commands) > 10:
            self.recent_commands.pop(0)
    
    def add_result(self, result: str) -> None:
        """
        Add a result to the recent results list.
        
        Args:
            result: The result string
        """
        self.recent_results.append(result)
        self.last_accessed = datetime.now()
        
        # Keep only the last 5 results
        if len(self.recent_results) > 5:
            self.recent_results.pop(0)
    
    def get_context_dict(self) -> Dict[str, Any]:
        """
        Get the session memory as a dictionary.
        
        Returns:
            A dictionary representation of the session memory
        """
        return {
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "recent_commands": self.recent_commands,
            "recent_results": self.recent_results,
            "created": self.created.isoformat(),
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMemory':
        """
        Create a session memory from a dictionary.
        
        Args:
            data: The dictionary representation
            
        Returns:
            A new SessionMemory instance
        """
        session = cls()
        session.entities = {
            k: EntityReference.from_dict(v) 
            for k, v in data.get("entities", {}).items()
        }
        session.recent_commands = data.get("recent_commands", [])
        session.recent_results = data.get("recent_results", [])
        session.created = datetime.fromisoformat(data["created"])
        session.last_accessed = datetime.fromisoformat(data["last_accessed"])
        return session


class SessionManager:
    """Manager for conversation session memories."""
    
    def __init__(self):
        """Initialize the session manager."""
        self._current_session = SessionMemory()
        self._logger = logger
    
    def refresh_session(self) -> None:
        """Refresh the current session or create a new one if expired."""
        # Check if session is enabled in preferences
        preferences_manager = get_preferences_manager()
        if not preferences_manager.preferences.context.remember_session_context:
            self._current_session = SessionMemory()
            return
        
        # Check if the session has expired (2 hours of inactivity)
        now = datetime.now()
        session_timeout = timedelta(hours=2)
        
        if now - self._current_session.last_accessed > session_timeout:
            self._logger.debug("Session expired, creating new session")
            self._current_session = SessionMemory()
    
    def add_entity(self, name: str, entity_type: str, value: str) -> None:
        """
        Add an entity to the current session.
        
        Args:
            name: The name or identifier of the entity
            entity_type: The type of entity
            value: The value or path of the entity
        """
        self.refresh_session()
        self._current_session.add_entity(name, entity_type, value)
    
    def get_entity(self, name: str) -> Optional[EntityReference]:
        """
        Get an entity from the current session.
        
        Args:
            name: The name or identifier of the entity
            
        Returns:
            The entity reference, or None if not found
        """
        self.refresh_session()
        return self._current_session.get_entity(name)
    
    def add_command(self, command: str) -> None:
        """
        Add a command to the current session.
        
        Args:
            command: The command string
        """
        self.refresh_session()
        self._current_session.add_command(command)
    
    def add_result(self, result: str) -> None:
        """
        Add a result to the current session.
        
        Args:
            result: The result string
        """
        self.refresh_session()
        self._current_session.add_result(result)
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the current session context as a dictionary.
        
        Returns:
            A dictionary representation of the current session context
        """
        self.refresh_session()
        return self._current_session.get_context_dict()
    
    def clear_session(self) -> None:
        """Clear the current session."""
        self._current_session = SessionMemory()

# Global session manager instance
session_manager = SessionManager()
