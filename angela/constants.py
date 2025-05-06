"""
Constants for the Angela CLI application.
"""
from pathlib import Path
import os

# Application information
APP_NAME = "angela-cli"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "AI-powered command-line assistant integrated into your terminal shell"

# Paths
BASE_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = Path(os.path.expanduser("~/.config/angela"))
CONFIG_FILE = CONFIG_DIR / "config.toml"
LOG_DIR = CONFIG_DIR / "logs"
HISTORY_FILE = CONFIG_DIR / "history.json"

# Shell integration
SHELL_INVOKE_COMMAND = "angela"
BASH_INTEGRATION_PATH = BASE_DIR / "shell" / "angela.bash"
ZSH_INTEGRATION_PATH = BASE_DIR / "shell" / "angela.zsh"

# Project markers for detection
PROJECT_MARKERS = [
    ".git",               # Git repository
    "package.json",       # Node.js project
    "requirements.txt",   # Python project
    "Cargo.toml",         # Rust project
    "pom.xml",            # Maven project
    "build.gradle",       # Gradle project
    "Dockerfile",         # Docker project
    "docker-compose.yml", # Docker Compose project
    "CMakeLists.txt",     # CMake project
    "Makefile",           # Make project
]

# Logging
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
LOG_ROTATION = "100 MB"
LOG_RETENTION = "10 days"

# API
GEMINI_MODEL = "gemini-2.5-pro-exp-03-25"
GEMINI_MAX_TOKENS = 4000
GEMINI_TEMPERATURE = 0.2
REQUEST_TIMEOUT = 45  # seconds

# Safety
RISK_LEVELS = {
    "SAFE": 0,            # Reading operations, info commands
    "LOW": 1,             # Directory creation, simple file operations
    "MEDIUM": 2,          # File content changes, non-critical configurations
    "HIGH": 3,            # System configuration, package installation
    "CRITICAL": 4,        # Destructive operations, security-sensitive changes
}

# Default confirmation requirements by risk level
DEFAULT_CONFIRMATION_REQUIREMENTS = {
    0: False,  # SAFE: No confirmation needed
    1: False,  # LOW: No confirmation needed
    2: True,   # MEDIUM: Confirmation needed
    3: True,   # HIGH: Confirmation needed
    4: True,   # CRITICAL: Confirmation needed with warning
}
