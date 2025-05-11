# angela/config.py
"""
Configuration management for Angela CLI.
Uses TOML format for configuration files.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import sys
from angela.utils.logging import get_logger


# --- TOML Library Handling ---

# Reader (tomllib for >= 3.11, tomli for < 3.11)
if sys.version_info >= (3, 11):
    import tomllib
    _TOML_LOAD_AVAILABLE = True
    _TOML_READ_ERROR_TYPE = tomllib.TOMLDecodeError
else:
    try:
        import tomli as tomllib # Alias tomli as tomllib
        _TOML_LOAD_AVAILABLE = True
        _TOML_READ_ERROR_TYPE = tomllib.TOMLDecodeError
    except ImportError:
        tomllib = None
        _TOML_LOAD_AVAILABLE = False
        _TOML_READ_ERROR_TYPE = Exception # Fallback

# Writer (tomli-w)
try:
    import tomli_w
    _TOML_WRITE_AVAILABLE = True
except ImportError:
    tomli_w = None
    _TOML_WRITE_AVAILABLE = False

# --- Pydantic and Environment Handling ---
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from angela.constants import CONFIG_DIR, CONFIG_FILE
CONFIG_DIR = Path.home() / ".angela"

# --- Configuration Models ---

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


# --- Configuration Manager ---

class ConfigManager:
    """Manages the configuration for the Angela CLI application using TOML."""

    def __init__(self):
        """Initializes the ConfigManager with default settings."""
        self._config: AppConfig = AppConfig()
        self.CONFIG_DIR = CONFIG_DIR
        self._load_environment()
        self._ensure_config_dir()
        self._logger = get_logger(__name__)
        # Note: Loading from file happens via the global instance later

    def _load_environment(self) -> None:
        """Loads API keys from environment variables and .env file."""
        load_dotenv() # Load .env file if present
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            self._config.api.gemini_api_key = gemini_api_key
            # Add other environment variable loadings here if needed

    def _ensure_config_dir(self) -> None:
        """Ensures the application's configuration directory exists."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating configuration directory {CONFIG_DIR}: {e}")
            # Depending on severity, might want to raise or exit here

    # Update in angela/config.py
    
    def load_config(self) -> None:
        """Loads configuration from the TOML config file."""
        if not CONFIG_FILE.exists():
            # Only log at debug level, not print to console
            self._logger.debug(f"Configuration file not found at '{CONFIG_FILE}'. Saving default configuration.")
            self.save_config() # Save default TOML config
            return
        
        if not _TOML_LOAD_AVAILABLE:
            self._logger.error(f"Warning: Cannot load TOML config file '{CONFIG_FILE}'.")
            if sys.version_info < (3, 11):
                self._logger.error("       Reason: 'tomli' package is not installed for this Python version.")
                self._logger.error("       To fix, ensure 'tomli; python_version < \"3.11\"' is in your dependencies.")
            else:
                 self._logger.error("       Reason: Could not import the built-in 'tomllib' module.") # Should be unlikely
            self._logger.error("       Using default configuration and environment variables.")
            return
        
        try:
            # Changed: only log at debug level, not print to console
            self._logger.debug(f"Loading configuration from: {CONFIG_FILE}")
            with open(CONFIG_FILE, "rb") as f: # TOML requires binary read mode
                config_data = tomllib.load(f)
        
            # Update configuration with loaded data, using Pydantic validation
            if "api" in config_data and isinstance(config_data["api"], dict):
                self._config.api = ApiConfig(**config_data["api"])
        
            if "user" in config_data and isinstance(config_data["user"], dict):
                 # Pydantic will handle Path conversion from string during validation
                 self._config.user = UserConfig(**config_data["user"])
        
            if "debug" in config_data:
                # Explicitly check type for robustness
                if isinstance(config_data["debug"], bool):
                     self._config.debug = config_data["debug"]
                else:
                     self._logger.warning(f"Invalid type for 'debug' in {CONFIG_FILE}. Expected boolean, got {type(config_data['debug'])}. Ignoring.")
        
        except _TOML_READ_ERROR_TYPE as e:
             self._logger.error(f"Error decoding TOML configuration file ({CONFIG_FILE}): {e}")
             self._logger.error("       Please check the file syntax. Using default configuration and environment variables.")
             self._logger.error("       Resetting configuration to default.")
             self._config = AppConfig()
             self._load_environment()
        except FileNotFoundError as e:
            self._logger.error(f"Configuration file not found: {e}")
            self._logger.error("       Using default configuration and environment variables.")
            self._config = AppConfig()
            self._load_environment()
        except PermissionError as e:
            self._logger.error(f"Permission error accessing configuration file: {e}")
            self._logger.error("       Using default configuration and environment variables.")
            self._config = AppConfig()
            self._load_environment()
        except IOError as e:
            self._logger.error(f"I/O error accessing configuration file: {e}")
            self._logger.error("       Using default configuration and environment variables.")
            self._config = AppConfig()
            self._load_environment()


    def save_config(self) -> None:
        """Saves the current configuration to the config file (as TOML)."""
        if not _TOML_WRITE_AVAILABLE:
             print(f"Error: Cannot save TOML config. 'tomli-w' package not installed.")
             print(f"       To fix, add 'tomli-w' to your dependencies and reinstall.")
             print(f"       Skipping save to {CONFIG_FILE}.")
             return

        try:
            # Convert Pydantic model to dict.
            # Need to handle Path object manually for TOML serialization.
            config_dict = self._config.model_dump()
            if config_dict.get("user", {}).get("default_project_root"):
               # Convert Path to string if it exists
               config_dict["user"]["default_project_root"] = str(config_dict["user"]["default_project_root"])

            # Ensure parent directory exists (usually handled by _ensure_config_dir)
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Write to file using tomli_w in binary write mode
            with open(CONFIG_FILE, "wb") as f:
                tomli_w.dump(config_dict, f)
            print(f"Configuration saved successfully to {CONFIG_FILE}") # Confirmation message

        except Exception as e:
            print(f"Error saving TOML configuration to {CONFIG_FILE}: {e}")
            # Consider more specific error handling if needed


    @property
    def config(self) -> AppConfig:
        """Provides read-only access to the current application configuration."""
        return self._config


# --- Global Instance ---

# Create a single, globally accessible instance of the ConfigManager
config_manager = ConfigManager()

# Load the configuration from file immediately when this module is imported.
# This makes the loaded config available to other modules that import config_manager.
config_manager.load_config()
