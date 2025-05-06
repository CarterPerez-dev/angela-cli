# angela/context/preferences.py

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from angela.config import config_manager
from angela.constants import RISK_LEVELS
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class TrustPreferences(BaseModel):
    """Model for user trust preferences."""
    default_trust_level: int = Field(4, description="Default trust level (0-4)")
    auto_execute_safe: bool = Field(True, description="Auto-execute SAFE operations")
    auto_execute_low: bool = Field(True, description="Auto-execute LOW risk operations")
    auto_execute_medium: bool = Field(False, description="Auto-execute MEDIUM risk operations")
    auto_execute_high: bool = Field(False, description="Auto-execute HIGH risk operations")
    auto_execute_critical: bool = Field(False, description="Auto-execute CRITICAL risk operations")
    trusted_commands: List[str] = Field(default_factory=list, description="Commands that are always trusted")
    untrusted_commands: List[str] = Field(default_factory=list, description="Commands that require confirmation")

class UIPreferences(BaseModel):
    """Model for UI preferences."""
    show_command_preview: bool = Field(True, description="Show command preview before execution")
    show_impact_analysis: bool = Field(True, description="Show impact analysis for commands")
    use_rich_output: bool = Field(True, description="Use rich formatted output")
    verbose_feedback: bool = Field(True, description="Show detailed execution feedback")
    use_spinners: bool = Field(True, description="Show spinners for long-running operations")

class ContextPreferences(BaseModel):
    """Model for context preferences."""
    remember_session_context: bool = Field(True, description="Maintain context between commands")
    max_history_items: int = Field(50, description="Maximum number of history items to remember")
    auto_learn_patterns: bool = Field(True, description="Automatically learn command patterns")

class UserPreferences(BaseModel):
    """User preferences model."""
    trust: TrustPreferences = Field(default_factory=TrustPreferences, description="Trust settings")
    ui: UIPreferences = Field(default_factory=UIPreferences, description="UI settings")
    context: ContextPreferences = Field(default_factory=ContextPreferences, description="Context settings")

class PreferencesManager:
    """Manager for user preferences."""
    
    def __init__(self):
        """Initialize the preferences manager."""
        self._prefs = UserPreferences()
        self._prefs_file = config_manager.CONFIG_DIR / "preferences.json"
        self._load_preferences()
    
    def _load_preferences(self) -> None:
        """Load preferences from file."""
        try:
            if self._prefs_file.exists():
                with open(self._prefs_file, "r") as f:
                    data = json.load(f)
                    self._prefs = UserPreferences.parse_obj(data)
                logger.debug(f"Loaded preferences from {self._prefs_file}")
            else:
                logger.debug("No preferences file found, using defaults")
                self._save_preferences()  # Create the file with defaults
        except Exception as e:
            logger.error(f"Error loading preferences: {e}")
    
    def _save_preferences(self) -> None:
        """Save preferences to file."""
        try:
            with open(self._prefs_file, "w") as f:
                json.dump(self._prefs.dict(), f, indent=2)
            logger.debug(f"Saved preferences to {self._prefs_file}")
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
    
    def update_preferences(self, **kwargs) -> None:
        """Update preferences with provided values."""
        if not kwargs:
            return
            
        # Handle nested preferences
        for section in ["trust", "ui", "context"]:
            section_data = kwargs.pop(section, None)
            if section_data and isinstance(section_data, dict):
                for k, v in section_data.items():
                    setattr(getattr(self._prefs, section), k, v)
        
        # Handle top-level preferences
        for k, v in kwargs.items():
            setattr(self._prefs, k, v)
        
        self._save_preferences()
    
    def should_auto_execute(self, risk_level: int, command: str) -> bool:
        """
        Determine if a command should be auto-executed based on risk level
        and user preferences.
        
        Args:
            risk_level: The risk level of the command
            command: The command string
            
        Returns:
            True if should auto-execute, False if confirmation needed
        """
        # Check if the command is explicitly trusted or untrusted
        if command in self._prefs.trust.trusted_commands:
            return True
        if command in self._prefs.trust.untrusted_commands:
            return False
        
        # Check based on risk level
        if risk_level == RISK_LEVELS["SAFE"]:
            return self._prefs.trust.auto_execute_safe
        elif risk_level == RISK_LEVELS["LOW"]:
            return self._prefs.trust.auto_execute_low
        elif risk_level == RISK_LEVELS["MEDIUM"]:
            return self._prefs.trust.auto_execute_medium
        elif risk_level == RISK_LEVELS["HIGH"]:
            return self._prefs.trust.auto_execute_high
        elif risk_level == RISK_LEVELS["CRITICAL"]:
            return self._prefs.trust.auto_execute_critical
        
        # Default to require confirmation
        return False
    
    def add_trusted_command(self, command: str) -> None:
        """Add a command to the trusted commands list."""
        if command not in self._prefs.trust.trusted_commands:
            self._prefs.trust.trusted_commands.append(command)
            # Remove from untrusted if present
            if command in self._prefs.trust.untrusted_commands:
                self._prefs.trust.untrusted_commands.remove(command)
            self._save_preferences()
    
    def add_untrusted_command(self, command: str) -> None:
        """Add a command to the untrusted commands list."""
        if command not in self._prefs.trust.untrusted_commands:
            self._prefs.trust.untrusted_commands.append(command)
            # Remove from trusted if present
            if command in self._prefs.trust.trusted_commands:
                self._prefs.trust.trusted_commands.remove(command)
            self._save_preferences()
    
    @property
    def preferences(self) -> UserPreferences:
        """Get the current preferences."""
        return self._prefs

# Create a global instance of the preferences manager
preferences_manager = PreferencesManager()
