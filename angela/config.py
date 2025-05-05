"""
Configuration management for Angela CLI.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

import tomli
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from angela.constants import CONFIG_DIR, CONFIG_FILE


class ApiConfig(BaseModel):
    """API configuration settings."""
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API Key")


class UserConfig(BaseModel):
    """User-specific configuration settings."""
    default_project_root: Optional[Path] = Field(None, description="Default project root directory")
    confirm_all_actions: bool = Field(False, description="Whether to confirm all actions regardless of risk level")


class AppConfig(BaseModel):
    """Application configuration settings."""
    api: ApiConfig = Field(default_factory=ApiConfig, description="API configuration")
    user: UserConfig = Field(default_factory=UserConfig, description="User configuration")
    debug: bool = Field(False, description="Enable debug mode")


class ConfigManager:
    """Manages the configuration for the Angela CLI application."""
    
    def __init__(self):
        self._config: AppConfig = AppConfig()
        self._load_environment()
        self._ensure_config_dir()
    
    def _load_environment(self) -> None:
        """Load configuration from environment variables."""
        # Load from .env file if it exists
        load_dotenv()
        
        # Set API keys from environment
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            self._config.api.gemini_api_key = gemini_api_key
    
    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> None:
        """Load configuration from the config file."""
        if not CONFIG_FILE.exists():
            self.save_config()  # Create default config
            return
            
        try:
            with open(CONFIG_FILE, "rb") as f:
                config_data = tomli.load(f)
                
            # Update configuration with loaded data
            if "api" in config_data:
                self._config.api = ApiConfig(**config_data["api"])
            
            if "user" in config_data:
                self._config.user = UserConfig(**config_data["user"])
                
            if "debug" in config_data:
                self._config.debug = config_data["debug"]
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    def save_config(self) -> None:
        """Save the current configuration to the config file."""
        try:
            # Convert to dictionary
            config_dict = self._config.model_dump()
            
            # Convert Path objects to strings for serialization
            if config_dict["user"]["default_project_root"]:
                config_dict["user"]["default_project_root"] = str(config_dict["user"]["default_project_root"])
            
            # Write to file
            with open(CONFIG_FILE, "w") as f:
                json.dump(config_dict, f, indent=2)
                
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config


# Global configuration instance
config_manager = ConfigManager()
