"""
Advanced confidence scoring system for Angela CLI.

This module implements a sophisticated, multi-dimensional confidence scoring system 
that evaluates the reliability of AI-generated command suggestions based on
numerous factors including command history, complexity analysis, semantic relevance,
entity matching, parameter validation, domain-specific heuristics, and
contextual appropriateness.

The scoring system incorporates:
- Historical command usage patterns and success rates
- Semantic similarity between request and suggested command
- Contextual relevance to current environment
- Path and entity validation
- Command structure and complexity analysis
- Parameter and flag validation
- Domain-specific knowledge for different command types
- Risk assessment and safety heuristics
- User preference matching

This enhanced confidence scoring helps the system make better decisions about
when to auto-execute commands versus when to seek user confirmation,
improving both safety and user experience.
"""

import re
import os
import sys
import shlex
import difflib
import statistics
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union, Callable
from dataclasses import dataclass
from enum import Enum
import json
import time
from datetime import datetime, timedelta
import shutil
import hashlib

from angela.api.context import get_history_manager, get_context_manager, get_semantic_context_manager
from angela.api.context import get_file_activity_tracker, get_file_resolver, get_session_manager
from angela.api.shell import get_terminal_formatter
from angela.utils.logging import get_logger
from angela.config import config_manager

logger = get_logger(__name__)

# Constants for confidence scoring
DEFAULT_CONFIDENCE = 0.7  # Base confidence score
MIN_CONFIDENCE = 0.3      # Minimum confidence score
MAX_CONFIDENCE = 0.98     # Maximum confidence score - never quite 100%

# Scoring weights for different factors (must sum to 1.0)
SCORING_WEIGHTS = {
    "historical": 0.20,    # Increased from 0.3 - command history and past success
    "complexity": 0.15,    # Command complexity relative to request
    "semantic": 0.15,      # New factor - semantic similarity between request and command
    "entity": 0.15,        # Decreased from 0.3 - entities in request vs command
    "syntax": 0.10,        # New factor - command syntax correctness
    "context": 0.10,       # New factor - contextual relevance to current environment
    "flags": 0.05,         # Decreased from 0.1 - flag analysis
    "risk": 0.05,          # New factor - risk assessment
    "user_prefs": 0.05,    # New factor - user preferences matching
}

# Command categories for domain-specific scoring
class CommandCategory(Enum):
    FILE_OPERATION = "file_operation"
    NETWORK = "network"
    PROCESS = "process"
    SYSTEM = "system"
    PACKAGE = "package"
    USER = "user"
    GIT = "git"
    DOCKER = "docker"
    UNKNOWN = "unknown"

# File operation subcategories
class FileOperationSubcategory(Enum):
    READ = "read"          # Reading operations (cat, less, head, tail, etc.)
    WRITE = "write"        # Writing operations (echo, write, etc.)
    MODIFY = "modify"      # Modifying operations (sed, awk, etc.)
    CREATE = "create"      # Creation operations (touch, mkdir, etc.)
    DELETE = "delete"      # Deletion operations (rm, rmdir, etc.)
    COPY = "copy"          # Copying operations (cp, rsync, etc.)
    MOVE = "move"          # Moving operations (mv, rename, etc.)
    PERMISSION = "perm"    # Permission operations (chmod, chown, etc.)
    LISTING = "list"       # Listing operations (ls, find, etc.)
    ARCHIVE = "archive"    # Archive operations (tar, zip, etc.)
    LINK = "link"          # Link operations (ln, etc.)
    SEARCH = "search"      # Search operations (grep, find, etc.)

# Entity types for context matching
class EntityType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    USER = "user"
    GROUP = "group"
    HOST = "host"
    PACKAGE = "package"
    PROCESS = "process"
    PORT = "port"
    URL = "url"
    PARAMETER = "parameter"
    FLAG = "flag"
    PATTERN = "pattern"
    UNKNOWN = "unknown"

@dataclass
class Entity:
    """Represents an entity extracted from a request or command."""
    text: str
    type: EntityType
    value: Any = None
    start_pos: int = -1
    end_pos: int = -1
    validated: bool = False
    confidence: float = 0.0
    
    def __hash__(self):
        return hash((self.text, self.type))
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.text == other.text and self.type == other.type

@dataclass
class CommandAnalysis:
    """Detailed analysis of a command for confidence scoring."""
    base_command: str
    args: List[str]
    flags: List[str]
    category: CommandCategory = CommandCategory.UNKNOWN
    subcategory: Optional[Any] = None
    entities: List[Entity] = None
    is_complex: bool = False
    has_redirects: bool = False
    has_pipes: bool = False
    token_count: int = 0
    char_count: int = 0
    risk_level: int = 0
    invalid_syntax: bool = False
    potential_issues: List[str] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.potential_issues is None:
            self.potential_issues = []
        # Calculate token and character counts if not explicitly set
        if self.token_count == 0:
            self.token_count = len([self.base_command] + self.args + self.flags)
        if self.char_count == 0:
            self.char_count = sum(len(arg) for arg in [self.base_command] + self.args + self.flags)

@dataclass
class SemanticAnalysis:
    """Semantic analysis of a request and command."""
    similarity_score: float
    topic_match_score: float
    intent_match_score: float
    key_terms_overlap: float
    context_relevant_score: float
    overall_score: float

@dataclass
class HistoricalAnalysis:
    """Historical analysis of command usage."""
    frequency: int
    success_rate: float
    last_used: Optional[datetime] = None
    similar_commands: List[Tuple[str, float]] = None
    pattern_match_score: float = 0.0
    environment_match_score: float = 0.0
    overall_score: float = 0.0
    
    def __post_init__(self):
        if self.similar_commands is None:
            self.similar_commands = []

@dataclass
class RiskAnalysis:
    """Risk analysis of a command."""
    risk_level: int
    risk_factors: List[str]
    safety_score: float
    requires_confirmation: bool
    is_reversible: bool
    impact_scope: str
    overall_score: float

@dataclass
class ConfidenceFactors:
    """Detailed breakdown of all confidence factors."""
    historical: HistoricalAnalysis
    semantic: SemanticAnalysis
    command: CommandAnalysis
    risk: RiskAnalysis
    entity_match_score: float
    complexity_match_score: float
    flag_validation_score: float
    context_relevance_score: float
    user_preference_score: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class ContextualState:
    """Represents the current contextual state for relevance scoring."""
    cwd: Path
    project_root: Optional[Path]
    project_type: Optional[str]
    recent_files: List[Tuple[Path, datetime]]
    recent_dirs: List[Tuple[Path, datetime]]
    recent_commands: List[Tuple[str, datetime]]
    active_processes: List[str]
    environment_vars: Dict[str, str]
    
    @classmethod
    def from_context_manager(cls, context_manager, session_manager=None):
        """Create ContextualState from context_manager and session_manager."""
        cwd = Path(context_manager.cwd)
        project_root = context_manager.project_root
        project_type = context_manager.project_type
        
        # Get recent files and directories
        recent_files = []
        recent_dirs = []
        
        if session_manager:
            # Extract file and directory entities from session
            for entity_id, entity_data in session_manager.get_session_memory().entities.items():
                if entity_data.get('type') == 'file' and entity_data.get('last_use'):
                    path = Path(entity_id)
                    last_use = datetime.fromisoformat(entity_data['last_use'])
                    recent_files.append((path, last_use))
                elif entity_data.get('type') == 'directory' and entity_data.get('last_use'):
                    path = Path(entity_id)
                    last_use = datetime.fromisoformat(entity_data['last_use'])
                    recent_dirs.append((path, last_use))
        
        # Get recent commands
        recent_commands = []
        history_manager = get_history_manager()
        for cmd_record in history_manager.get_recent_commands(10):
            timestamp = datetime.fromisoformat(cmd_record.get('timestamp', datetime.now().isoformat()))
            recent_commands.append((cmd_record.get('command', ''), timestamp))
        
        # Get active processes (simplified)
        active_processes = []
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    active_processes.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except ImportError:
            # psutil not available, skip process info
            pass
        
        # Get relevant environment variables
        env_vars = {}
        for key in ['PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'LANG', 'PWD']:
            if key in os.environ:
                env_vars[key] = os.environ[key]
        
        return cls(
            cwd=cwd,
            project_root=project_root,
            project_type=project_type,
            recent_files=recent_files,
            recent_dirs=recent_dirs,
            recent_commands=recent_commands,
            active_processes=active_processes,
            environment_vars=env_vars
        )

class ConfidenceScorer:
    """
    Advanced system for scoring confidence in natural language understanding
    and command suggestions.
    
    This class implements a sophisticated multi-dimensional approach to evaluate
    how well a suggested command matches the user's intent, incorporating:
    
    1. Historical command analysis and success patterns
    2. Semantic similarity between request and command
    3. Linguistic complexity matching
    4. Entity detection and validation
    5. Syntax correctness and command structure analysis
    6. Context awareness and environment relevance
    7. Command flag validation
    8. Risk assessment and safety evaluation
    9. User preference matching
    
    These confidence scores are used by Angela CLI to determine when to
    auto-execute commands versus when to seek confirmation, making the
    system both safer and more efficient.
    """
    
    def __init__(self):
        """Initialize the confidence scorer with advanced capabilities."""
        self._logger = logger
        
        # Cache for recent scoring data
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_size_limit = 100
        
        # Initialize command categorization mappings
        self._initialize_command_categories()
        
        # Initialize entity type detection patterns
        self._initialize_entity_patterns()
        
        # Initialize command flag compatibility data
        self._initialize_flag_compatibility()
        
        # Precompile regex patterns for performance
        self._precompile_regex_patterns()
        
        # Track execution statistics
        self._stats = {
            "total_evaluations": 0,
            "cache_hits": 0,
            "high_confidence_count": 0,
            "low_confidence_count": 0,
            "avg_computation_time": 0.0,
            "total_computation_time": 0.0,
        }
        
        self._logger.debug("Advanced ConfidenceScorer initialized")


    def _extract_base_command(self, command: str) -> str:
        """
        Extract the base command without arguments.
        """
        # Extract the first word (command name)
        parts = command.strip().split()
        if not parts:
            return ""
        base = parts[0]
        
        # For some commands, include the first argument if it's an operation
        # (you can expand this list as needed)
        if base in ["git", "docker", "npm", "pip", "apt", "apt-get", "yarn", "cargo", "go", "kubectl", "aws", "az", "gcloud"]:
            if len(parts) > 1 and not parts[1].startswith("-"):
                base = f"{base} {parts[1]}"
        
        return base




    
    def _initialize_command_categories(self):
        """Initialize mappings of commands to their categories and subcategories."""
        # Core file operations
        self._file_commands = {
            # Read operations
            'cat': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.READ),
            'less': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.READ),
            'more': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.READ),
            'head': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.READ),
            'tail': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.READ),
            'view': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.READ),
            
            # Write operations
            'echo': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.WRITE),
            'tee': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.WRITE),
            
            # Modify operations
            'sed': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MODIFY),
            'awk': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MODIFY),
            'tr': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MODIFY),
            'sort': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MODIFY),
            'uniq': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MODIFY),
            'cut': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MODIFY),
            
            # Create operations
            'touch': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.CREATE),
            'mkdir': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.CREATE),
            'mktemp': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.CREATE),
            
            # Delete operations
            'rm': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.DELETE),
            'rmdir': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.DELETE),
            'shred': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.DELETE),
            
            # Copy operations
            'cp': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.COPY),
            'rsync': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.COPY),
            'dd': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.COPY),
            
            # Move operations
            'mv': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MOVE),
            'rename': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.MOVE),
            
            # Permission operations
            'chmod': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.PERMISSION),
            'chown': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.PERMISSION),
            'chgrp': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.PERMISSION),
            'umask': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.PERMISSION),
            
            # Listing operations
            'ls': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'find': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'locate': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'tree': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'du': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'df': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'file': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            'stat': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LISTING),
            
            # Archive operations
            'tar': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            'gzip': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            'gunzip': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            'zip': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            'unzip': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            'bzip2': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            'bunzip2': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.ARCHIVE),
            
            # Link operations
            'ln': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.LINK),
            
            # Search operations
            'grep': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.SEARCH),
            'egrep': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.SEARCH),
            'fgrep': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.SEARCH),
            'rg': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.SEARCH),
            'ag': (CommandCategory.FILE_OPERATION, FileOperationSubcategory.SEARCH),
        }
        
        # Network commands
        self._network_commands = {
            'ping': CommandCategory.NETWORK,
            'curl': CommandCategory.NETWORK,
            'wget': CommandCategory.NETWORK,
            'ssh': CommandCategory.NETWORK,
            'scp': CommandCategory.NETWORK,
            'sftp': CommandCategory.NETWORK,
            'rsync': CommandCategory.NETWORK,
            'nc': CommandCategory.NETWORK,
            'telnet': CommandCategory.NETWORK,
            'dig': CommandCategory.NETWORK,
            'nslookup': CommandCategory.NETWORK,
            'host': CommandCategory.NETWORK,
            'traceroute': CommandCategory.NETWORK,
            'whois': CommandCategory.NETWORK,
            'ifconfig': CommandCategory.NETWORK,
            'ip': CommandCategory.NETWORK,
            'netstat': CommandCategory.NETWORK,
            'ss': CommandCategory.NETWORK,
            'iptables': CommandCategory.NETWORK,
            'ufw': CommandCategory.NETWORK,
        }
        
        # Process commands
        self._process_commands = {
            'ps': CommandCategory.PROCESS,
            'pgrep': CommandCategory.PROCESS,
            'pkill': CommandCategory.PROCESS,
            'kill': CommandCategory.PROCESS,
            'killall': CommandCategory.PROCESS,
            'top': CommandCategory.PROCESS,
            'htop': CommandCategory.PROCESS,
            'nice': CommandCategory.PROCESS,
            'renice': CommandCategory.PROCESS,
            'nohup': CommandCategory.PROCESS,
            'time': CommandCategory.PROCESS,
            'timeout': CommandCategory.PROCESS,
            'watch': CommandCategory.PROCESS,
            'cron': CommandCategory.PROCESS,
            'crontab': CommandCategory.PROCESS,
            'at': CommandCategory.PROCESS,
            'batch': CommandCategory.PROCESS,
            'bg': CommandCategory.PROCESS,
            'fg': CommandCategory.PROCESS,
            'jobs': CommandCategory.PROCESS,
        }
        
        # System commands
        self._system_commands = {
            'sudo': CommandCategory.SYSTEM,
            'su': CommandCategory.SYSTEM,
            'shutdown': CommandCategory.SYSTEM,
            'reboot': CommandCategory.SYSTEM,
            'halt': CommandCategory.SYSTEM,
            'poweroff': CommandCategory.SYSTEM,
            'systemctl': CommandCategory.SYSTEM,
            'service': CommandCategory.SYSTEM,
            'journalctl': CommandCategory.SYSTEM,
            'dmesg': CommandCategory.SYSTEM,
            'uname': CommandCategory.SYSTEM,
            'hostname': CommandCategory.SYSTEM,
            'uptime': CommandCategory.SYSTEM,
            'free': CommandCategory.SYSTEM,
            'vmstat': CommandCategory.SYSTEM,
            'mount': CommandCategory.SYSTEM,
            'umount': CommandCategory.SYSTEM,
            'fdisk': CommandCategory.SYSTEM,
            'parted': CommandCategory.SYSTEM,
            'lsblk': CommandCategory.SYSTEM,
            'swapon': CommandCategory.SYSTEM,
            'swapoff': CommandCategory.SYSTEM,
            'lsof': CommandCategory.SYSTEM,
            'ulimit': CommandCategory.SYSTEM,
        }
        
        # Package management commands
        self._package_commands = {
            'apt': CommandCategory.PACKAGE,
            'apt-get': CommandCategory.PACKAGE,
            'aptitude': CommandCategory.PACKAGE,
            'dpkg': CommandCategory.PACKAGE,
            'yum': CommandCategory.PACKAGE,
            'rpm': CommandCategory.PACKAGE,
            'dnf': CommandCategory.PACKAGE,
            'pacman': CommandCategory.PACKAGE,
            'zypper': CommandCategory.PACKAGE,
            'brew': CommandCategory.PACKAGE,
            'pip': CommandCategory.PACKAGE,
            'pip3': CommandCategory.PACKAGE,
            'npm': CommandCategory.PACKAGE,
            'yarn': CommandCategory.PACKAGE,
            'gem': CommandCategory.PACKAGE,
            'cargo': CommandCategory.PACKAGE,
            'go': CommandCategory.PACKAGE,
        }
        
        # User management commands
        self._user_commands = {
            'useradd': CommandCategory.USER,
            'userdel': CommandCategory.USER,
            'usermod': CommandCategory.USER,
            'groupadd': CommandCategory.USER,
            'groupdel': CommandCategory.USER,
            'groupmod': CommandCategory.USER,
            'passwd': CommandCategory.USER,
            'chage': CommandCategory.USER,
            'who': CommandCategory.USER,
            'w': CommandCategory.USER,
            'last': CommandCategory.USER,
            'id': CommandCategory.USER,
            'groups': CommandCategory.USER,
            'whoami': CommandCategory.USER,
        }
        
        # Git commands
        self._git_commands = {
            'git': CommandCategory.GIT,
            'git-clone': CommandCategory.GIT,
            'git-pull': CommandCategory.GIT,
            'git-push': CommandCategory.GIT,
            'git-commit': CommandCategory.GIT,
            'git-add': CommandCategory.GIT,
            'git-status': CommandCategory.GIT,
            'git-diff': CommandCategory.GIT,
            'git-log': CommandCategory.GIT,
            'git-branch': CommandCategory.GIT,
            'git-checkout': CommandCategory.GIT,
            'git-merge': CommandCategory.GIT,
            'git-rebase': CommandCategory.GIT,
            'git-reset': CommandCategory.GIT,
            'git-stash': CommandCategory.GIT,
            'git-tag': CommandCategory.GIT,
            'git-fetch': CommandCategory.GIT,
            'git-remote': CommandCategory.GIT,
            'git-config': CommandCategory.GIT,
            'git-init': CommandCategory.GIT,
        }
        
        # Docker commands
        self._docker_commands = {
            'docker': CommandCategory.DOCKER,
            'docker-compose': CommandCategory.DOCKER,
            'docker-machine': CommandCategory.DOCKER,
            'podman': CommandCategory.DOCKER,
            'container': CommandCategory.DOCKER,
            'image': CommandCategory.DOCKER,
        }
        
        # Combine all command categories into one mapping
        self._command_categories = {}
        for cmd, category_info in self._file_commands.items():
            self._command_categories[cmd] = category_info
        
        for category_dict, category in [
            (self._network_commands, CommandCategory.NETWORK),
            (self._process_commands, CommandCategory.PROCESS),
            (self._system_commands, CommandCategory.SYSTEM),
            (self._package_commands, CommandCategory.PACKAGE),
            (self._user_commands, CommandCategory.USER),
            (self._git_commands, CommandCategory.GIT),
            (self._docker_commands, CommandCategory.DOCKER),
        ]:
            for cmd in category_dict:
                if cmd not in self._command_categories:
                    self._command_categories[cmd] = (category, None)
    
    def _initialize_entity_patterns(self):
        """Initialize regex patterns for entity detection."""
        # File path patterns
        self._file_path_patterns = [
            # Absolute paths
            (r'/(?:[^/\0]+/)*[^/\0]+', EntityType.FILE),
            # Relative paths with directories
            (r'(?:[^/\0]+/)+[^/\0]+', EntityType.FILE),
            # Home directory paths
            (r'~(?:/[^/\0]+)+', EntityType.FILE),
            # Single filename with extension
            (r'[^/\0\s]+\.[a-zA-Z0-9]{1,10}', EntityType.FILE),
        ]
        
        # Directory path patterns
        self._directory_path_patterns = [
            # Absolute directory paths
            (r'/(?:[^/\0]+/)*[^/\0]*/?', EntityType.DIRECTORY),
            # Relative directory paths
            (r'(?:[^/\0]+/)+[^/\0]*/?', EntityType.DIRECTORY),
            # Home directory paths
            (r'~(?:/[^/\0]+)*/?', EntityType.DIRECTORY),
            # Current, parent, or named directory
            (r'\./|\.\./', EntityType.DIRECTORY),
        ]
        
        # User and group patterns
        self._user_group_patterns = [
            # Username pattern
            (r'(?<!\S)([a-z_][a-z0-9_-]{0,31})(?!\S)', EntityType.USER),
            # User ID pattern
            (r'(?:uid=|user\s+id:?\s*)(\d+)', EntityType.USER),
            # Group pattern
            (r'(?:group:?\s+)([a-z_][a-z0-9_-]{0,31})', EntityType.GROUP),
            # Group ID pattern
            (r'(?:gid=|group\s+id:?\s*)(\d+)', EntityType.GROUP),
        ]
        
        # Network patterns
        self._network_patterns = [
            # IPv4 address
            (r'(?<!\d)(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?!\d)', EntityType.HOST),
            # IPv6 address (simplified)
            (r'(?<![:\da-fA-F])(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}(?![:\da-fA-F])', EntityType.HOST),
            # Hostname
            (r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}', EntityType.HOST),
            # Port number
            (r'(?:port\s+|:)(\d{1,5})', EntityType.PORT),
            # URL
            (r'(?:https?|ftp|file)://[^\s/$.?#].[^\s]*', EntityType.URL),
        ]
        
        # Process patterns
        self._process_patterns = [
            # Process ID
            (r'(?:pid[=:]?\s*)(\d+)', EntityType.PROCESS),
            # Process name
            (r'(?:process\s+)([a-zA-Z0-9_.-]+)', EntityType.PROCESS),
        ]
        
        # Command flag patterns
        self._flag_patterns = [
            # Short flags
            (r'(?<!\S)-[a-zA-Z0-9]+', EntityType.FLAG),
            # Long flags
            (r'(?<!\S)--[a-zA-Z0-9][-a-zA-Z0-9]+(?:=[^\s]+)?', EntityType.FLAG),
        ]
        
        # Parameter patterns
        self._parameter_patterns = [
            # Key-value parameter
            (r'(?<!\S)([a-zA-Z0-9_.-]+)=([^\s]+)', EntityType.PARAMETER),
        ]
        
        # Pattern patterns
        self._pattern_patterns = [
            # Glob patterns
            (r'(?<!\S)(?:\*|\?|\[.+?\]|\{.+?\})[^\s]*', EntityType.PATTERN),
            # Regex patterns
            (r'(?<!\S)/[^/]+/[gim]*', EntityType.PATTERN),
        ]
        
        # Combine all entity patterns
        self._entity_patterns = []
        for pattern_list in [
            self._file_path_patterns,
            self._directory_path_patterns,
            self._user_group_patterns,
            self._network_patterns,
            self._process_patterns,
            self._flag_patterns,
            self._parameter_patterns,
            self._pattern_patterns,
        ]:
            self._entity_patterns.extend(pattern_list)
    
    def _initialize_flag_compatibility(self):
        """Initialize flag compatibility data for common commands."""
        # Define common flag combinations and incompatibilities
        # Format: command -> {flag: {compatible_with: [...], incompatible_with: [...]}}
        self._flag_compatibility = {
            # ls command flags
            'ls': {
                '-a': {
                    'compatible_with': ['-l', '-h', '-t', '-r', '-S', '-R'],
                    'incompatible_with': ['--almost-all'],
                },
                '--all': {
                    'compatible_with': ['-l', '-h', '-t', '-r', '-S', '-R'],
                    'incompatible_with': ['--almost-all'],
                },
                '-A': {
                    'compatible_with': ['-l', '-h', '-t', '-r', '-S', '-R'],
                    'incompatible_with': ['-a', '--all'],
                },
                '--almost-all': {
                    'compatible_with': ['-l', '-h', '-t', '-r', '-S', '-R'],
                    'incompatible_with': ['-a', '--all'],
                },
                '-l': {
                    'compatible_with': ['-a', '-A', '-h', '-t', '-r', '-S', '-R'],
                    'incompatible_with': ['-1'],
                },
                '-1': {
                    'compatible_with': ['-a', '-A', '-t', '-r', '-S', '-R'],
                    'incompatible_with': ['-l', '-C', '-x'],
                },
            },
            
            # grep command flags
            'grep': {
                '-i': {
                    'compatible_with': ['-v', '-n', '-r', '-l', '-c', '-w', '-x', '-F', '-E'],
                    'incompatible_with': [],
                },
                '--ignore-case': {
                    'compatible_with': ['-v', '-n', '-r', '-l', '-c', '-w', '-x', '-F', '-E'],
                    'incompatible_with': [],
                },
                '-v': {
                    'compatible_with': ['-i', '-n', '-r', '-l', '-c', '-w', '-x', '-F', '-E'],
                    'incompatible_with': [],
                },
                '-E': {
                    'compatible_with': ['-i', '-v', '-n', '-r', '-l', '-c', '-w', '-x'],
                    'incompatible_with': ['-F'],
                },
                '-F': {
                    'compatible_with': ['-i', '-v', '-n', '-r', '-l', '-c', '-w', '-x'],
                    'incompatible_with': ['-E'],
                },
            },
            
            # find command flags
            'find': {
                '-name': {
                    'compatible_with': ['-type', '-size', '-perm', '-exec', '-delete', '-print'],
                    'incompatible_with': [],
                },
                '-iname': {
                    'compatible_with': ['-type', '-size', '-perm', '-exec', '-delete', '-print'],
                    'incompatible_with': ['-name'],
                },
                '-type': {
                    'compatible_with': ['-name', '-iname', '-size', '-perm', '-exec', '-delete', '-print'],
                    'incompatible_with': [],
                },
                '-delete': {
                    'compatible_with': ['-name', '-iname', '-type', '-size', '-perm'],
                    'incompatible_with': ['-exec'],
                },
            },
            
            # rm command flags
            'rm': {
                '-f': {
                    'compatible_with': ['-r', '-R', '-v', '-d'],
                    'incompatible_with': ['-i'],
                },
                '--force': {
                    'compatible_with': ['-r', '-R', '-v', '-d'],
                    'incompatible_with': ['-i', '--interactive'],
                },
                '-i': {
                    'compatible_with': ['-r', '-R', '-v', '-d'],
                    'incompatible_with': ['-f', '--force'],
                },
                '--interactive': {
                    'compatible_with': ['-r', '-R', '-v', '-d'],
                    'incompatible_with': ['-f', '--force'],
                },
                '-r': {
                    'compatible_with': ['-f', '-i', '-v'],
                    'incompatible_with': [],
                },
                '-R': {
                    'compatible_with': ['-f', '-i', '-v'],
                    'incompatible_with': [],
                },
            },
            
            # cp command flags
            'cp': {
                '-r': {
                    'compatible_with': ['-f', '-i', '-v', '-p', '-a'],
                    'incompatible_with': [],
                },
                '-R': {
                    'compatible_with': ['-f', '-i', '-v', '-p'],
                    'incompatible_with': [],
                },
                '-a': {
                    'compatible_with': ['-f', '-i', '-v'],
                    'incompatible_with': ['-p', '-d', '--preserve'],
                },
                '-p': {
                    'compatible_with': ['-f', '-i', '-v', '-r', '-R'],
                    'incompatible_with': ['-a', '--archive'],
                },
                '-i': {
                    'compatible_with': ['-r', '-R', '-v', '-p', '-a'],
                    'incompatible_with': ['-f', '--force'],
                },
                '-f': {
                    'compatible_with': ['-r', '-R', '-v', '-p', '-a'],
                    'incompatible_with': ['-i', '--interactive'],
                },
            },
            
            # mkdir command flags
            'mkdir': {
                '-p': {
                    'compatible_with': ['-v', '-m'],
                    'incompatible_with': [],
                },
                '--parents': {
                    'compatible_with': ['-v', '-m', '--mode'],
                    'incompatible_with': [],
                },
                '-m': {
                    'compatible_with': ['-p', '-v'],
                    'incompatible_with': [],
                },
                '--mode': {
                    'compatible_with': ['-p', '-v', '--parents', '--verbose'],
                    'incompatible_with': [],
                },
            },
        }
    
    def _precompile_regex_patterns(self):
        """Precompile regex patterns for better performance."""
        # Compiled entity patterns
        self._compiled_entity_patterns = [(re.compile(pattern), entity_type) 
                                          for pattern, entity_type in self._entity_patterns]
        
        # Common command parsing patterns
        self._command_pattern = re.compile(r'^([^\s|<>]+)')
        self._redirect_pattern = re.compile(r'(?:[^\\]|^)(>|>>|<|<<|2>|2>>|&>|&>>)')
        self._pipe_pattern = re.compile(r'(?:[^\\]|^)\|')
        
        # Flag patterns
        self._short_flag_pattern = re.compile(r'-([a-zA-Z0-9]+)')
        self._long_flag_pattern = re.compile(r'--([a-zA-Z0-9][-a-zA-Z0-9]*(?:=[^\s]+)?)')
        
        # Path patterns
        self._absolute_path_pattern = re.compile(r'/[^\s]*')
        self._relative_path_pattern = re.compile(r'\.{1,2}/[^\s]*|[^-/\s][^/\s]*/[^\s]*')
        self._home_path_pattern = re.compile(r'~(/[^\s]*)?')
    
    def score_command_confidence(
        self, 
        request: str, 
        command: str, 
        context: Dict[str, Any]
    ) -> float:
        """
        Score confidence in a command suggestion with comprehensive analysis.
        
        Performs multi-dimensional analysis of how well the suggested command
        matches the user's request, considering historical patterns, semantic
        similarity, syntax correctness, contextual relevance, and more.
        
        Args:
            request: The original natural language request
            command: The suggested shell command
            context: Context information including environment, history, etc.
            
        Returns:
            Confidence score (0.0-1.0) representing how well the command matches
            the user's request, with higher scores indicating higher confidence
        """

        
        start_time = time.time()
        
        # Update statistics
        self._stats["total_evaluations"] += 1
        
        # Check cache first
        cache_key = self._generate_cache_key(request, command)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self._stats["cache_hits"] += 1
            return cached_result
        
        self._logger.debug(f"Scoring confidence for command: {command!r} from request: {request!r}")
        
        # Step 1: Parse and analyze the command structure
        command_analysis = self._analyze_command(command)
        # --- END OF MOVE ---
        
        # Step 2: Extract entities from both request and command
        request_entities = self._extract_entities(request)
        
        # Step 3: Analyze command history relevance
        historical_analysis = self._check_history(command, command_analysis) # Now command_analysis is defined
        
        # Step 4: Check command complexity vs. request complexity
        complexity_score = self._check_complexity(request, command, command_analysis) # Now defined
        
        # Step 5: Analyze semantic similarity between request and command
        semantic_analysis = self._check_semantic_similarity(request, command, command_analysis, context) 
        
        # Step 6: Check for entity matches
        entity_match_score = self._check_entities(request, command, request_entities, command_analysis, context) # Now defined
        
        # Step 7: Validate command flags and options
        flag_validation_score = self._check_command_flags(command, command_analysis) # Now defined
        
        # Step 8: Check contextual relevance
        context_relevance_score = self._check_contextual_relevance(request, command, command_analysis, context) # Now defined
        
        # Step 9: Analyze risk and safety aspects
        risk_analysis = self._analyze_risk(command, command_analysis, context) # Now defined
        
        # Step 10: Check user preferences
        user_preference_score = self._check_user_preferences(command, command_analysis, context) # Now defined
        
        # Step 11: Calculate final weighted score
        confidence = (
            SCORING_WEIGHTS["historical"] * historical_analysis.overall_score +
            SCORING_WEIGHTS["complexity"] * complexity_score +
            SCORING_WEIGHTS["semantic"] * semantic_analysis.overall_score +
            SCORING_WEIGHTS["entity"] * entity_match_score +
            SCORING_WEIGHTS["syntax"] * (0.0 if command_analysis.invalid_syntax else 1.0) +
            SCORING_WEIGHTS["context"] * context_relevance_score +
            SCORING_WEIGHTS["flags"] * flag_validation_score +
            SCORING_WEIGHTS["risk"] * risk_analysis.overall_score +
            SCORING_WEIGHTS["user_prefs"] * user_preference_score
        )
        
        # Ensure score is in valid range
        confidence = min(MAX_CONFIDENCE, max(MIN_CONFIDENCE, confidence))
        
        # Create detailed confidence factors object (useful for logging and explanation)
        factors = ConfidenceFactors(
            historical=historical_analysis,
            semantic=semantic_analysis,
            command=command_analysis,
            risk=risk_analysis,
            entity_match_score=entity_match_score,
            complexity_match_score=complexity_score,
            flag_validation_score=flag_validation_score,
            context_relevance_score=context_relevance_score,
            user_preference_score=user_preference_score
        )
        
        # Update statistics
        computation_time = time.time() - start_time
        self._stats["total_computation_time"] += computation_time
        self._stats["avg_computation_time"] = (
            self._stats["total_computation_time"] / self._stats["total_evaluations"]
        )
        
        if confidence >= 0.8:
            self._stats["high_confidence_count"] += 1
        elif confidence <= 0.5:
            self._stats["low_confidence_count"] += 1
        
        # Cache the result with detailed factors
        self._add_to_cache(cache_key, confidence, factors)
        
        self._logger.debug(f"Command confidence score: {confidence:.4f}")
        
        if config_manager.config.debug:
            self._log_detailed_confidence_analysis(confidence, factors, computation_time)
        
        return confidence
    
    def get_detailed_confidence_factors(
        self, 
        request: str, 
        command: str, 
        context: Dict[str, Any]
    ) -> Optional[ConfidenceFactors]:
        """
        Get detailed confidence factors for a previously scored command.
        
        Args:
            request: The original request
            command: The suggested command
            context: Context information
            
        Returns:
            Detailed confidence factors or None if not cached
        """
        cache_key = self._generate_cache_key(request, command)
        cache_entry = self._cache.get(cache_key)
        
        if cache_entry:
            return cache_entry.get("factors")
        
        # Not in cache, would need to score again
        return None
    
    def explain_confidence_score(
        self, 
        request: str, 
        command: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a human-readable explanation of a confidence score.
        
        Args:
            request: The original request
            command: The suggested command
            context: Context information
            
        Returns:
            Dictionary with explanation and score details
        """
        # Check if we already have factors from a previous scoring
        factors = self.get_detailed_confidence_factors(request, command, context)
        
        # If not cached, score command to get factors
        if factors is None:
            score = self.score_command_confidence(request, command, context)
            factors = self.get_detailed_confidence_factors(request, command, context)
        else:
            # Calculate score from factors for consistency
            score = (
                SCORING_WEIGHTS["historical"] * factors.historical.overall_score +
                SCORING_WEIGHTS["complexity"] * factors.complexity_match_score +
                SCORING_WEIGHTS["semantic"] * factors.semantic.overall_score +
                SCORING_WEIGHTS["entity"] * factors.entity_match_score +
                SCORING_WEIGHTS["syntax"] * (0.0 if factors.command.invalid_syntax else 1.0) +
                SCORING_WEIGHTS["context"] * factors.context_relevance_score +
                SCORING_WEIGHTS["flags"] * factors.flag_validation_score +
                SCORING_WEIGHTS["risk"] * factors.risk.overall_score +
                SCORING_WEIGHTS["user_prefs"] * factors.user_preference_score
            )
            
            # Ensure score is in valid range
            score = min(MAX_CONFIDENCE, max(MIN_CONFIDENCE, score))
        
        # Generate explanation
        explanation = {
            "score": score,
            "confidence_level": self._get_confidence_level(score),
            "explanation": self._generate_confidence_explanation(score, factors),
            "factors": {
                "historical": {
                    "score": factors.historical.overall_score,
                    "frequency": factors.historical.frequency,
                    "success_rate": factors.historical.success_rate,
                    "similar_commands": factors.historical.similar_commands
                },
                "semantic": {
                    "score": factors.semantic.overall_score,
                    "similarity": factors.semantic.similarity_score,
                    "topic_match": factors.semantic.topic_match_score,
                    "intent_match": factors.semantic.intent_match_score
                },
                "command": {
                    "base_command": factors.command.base_command,
                    "category": str(factors.command.category),
                    "subcategory": str(factors.command.subcategory) if factors.command.subcategory else None,
                    "is_complex": factors.command.is_complex,
                    "syntax_valid": not factors.command.invalid_syntax,
                    "potential_issues": factors.command.potential_issues
                },
                "entity_match": factors.entity_match_score,
                "complexity_match": factors.complexity_match_score,
                "flag_validation": factors.flag_validation_score,
                "context_relevance": factors.context_relevance_score,
                "risk": {
                    "score": factors.risk.overall_score,
                    "level": factors.risk.risk_level,
                    "factors": factors.risk.risk_factors,
                    "requires_confirmation": factors.risk.requires_confirmation
                },
                "user_preferences": factors.user_preference_score
            },
            "factor_weights": SCORING_WEIGHTS
        }
        
        return explanation
    
    def _generate_confidence_explanation(self, score: float, factors: ConfidenceFactors) -> str:
        """Generate a human-readable explanation of the confidence score."""
        confidence_level = self._get_confidence_level(score)
        
        # Base explanation based on confidence level
        if confidence_level == "very high":
            explanation = "I have very high confidence in this command because "
        elif confidence_level == "high":
            explanation = "I have high confidence in this command because "
        elif confidence_level == "moderate":
            explanation = "I have moderate confidence in this command because "
        elif confidence_level == "low":
            explanation = "I have low confidence in this command because "
        else:  # very low
            explanation = "I have very low confidence in this command because "
        
        # Add factors based on their contribution to the score
        reasons = []
        
        # Historical factors
        if factors.historical.overall_score > 0.8:
            if factors.historical.frequency > 10:
                reasons.append("it has been used frequently in the past with high success")
            elif factors.historical.success_rate > 0.9:
                reasons.append("similar commands have been used successfully in the past")
        elif factors.historical.overall_score < 0.4:
            reasons.append("it hasn't been used before or has failed in the past")
        
        # Semantic similarity
        if factors.semantic.overall_score > 0.8:
            reasons.append("it closely matches the intent of your request")
        elif factors.semantic.overall_score < 0.4:
            reasons.append("it may not fully match the intent of your request")
        
        # Entity matching
        if factors.entity_match_score > 0.8:
            reasons.append("it correctly includes the files or entities you mentioned")
        elif factors.entity_match_score < 0.4:
            reasons.append("it might not correctly target the files or entities you mentioned")
        
        # Syntax and flags
        if factors.command.invalid_syntax:
            reasons.append("there might be syntax issues with the command")
        elif factors.flag_validation_score < 0.5:
            reasons.append("some command flags or options might be incompatible")
        
        # Risk assessment
        if factors.risk.risk_level >= 3:
            reasons.append("it involves potentially high-risk operations")
        
        # Context relevance
        if factors.context_relevance_score > 0.8:
            reasons.append("it's highly relevant to your current context")
        elif factors.context_relevance_score < 0.4:
            reasons.append("it might not be the most relevant for your current context")
        
        # Combine reasons
        if reasons:
            explanation += ", ".join(reasons[:-1])
            if len(reasons) > 1:
                explanation += ", and " + reasons[-1]
            else:
                explanation += reasons[0]
        else:
            # Fallback for when no specific reasons stand out
            explanation += "it meets multiple confidence criteria at a " + confidence_level + " level"
        
        return explanation + "."
    
    def _get_confidence_level(self, score: float) -> str:
        """Convert a numeric confidence score to a descriptive level."""
        if score >= 0.9:
            return "very high"
        elif score >= 0.75:
            return "high"
        elif score >= 0.6:
            return "moderate"
        elif score >= 0.45:
            return "low"
        else:
            return "very low"
    
    def _analyze_command(self, command: str) -> CommandAnalysis:
        """
        Perform detailed analysis of a command's structure and properties.
        
        Args:
            command: The shell command to analyze
            
        Returns:
            CommandAnalysis object with detailed information
        """
        # Parse the command for analysis
        try:
            # Use shlex to handle quoting correctly
            tokens = shlex.split(command)
            base_command = tokens[0] if tokens else ""
            args = []
            flags = []
            
            # Separate args and flags
            for token in tokens[1:]:
                if token.startswith('-'):
                    flags.append(token)
                else:
                    args.append(token)
            
            # Check for pipes and redirects in the original command
            has_redirects = bool(self._redirect_pattern.search(command))
            has_pipes = bool(self._pipe_pattern.search(command))
            
            # Determine command category and subcategory
            category = CommandCategory.UNKNOWN
            subcategory = None
            
            if base_command in self._command_categories:
                category_info = self._command_categories[base_command]
                if isinstance(category_info, tuple):
                    category, subcategory = category_info
                else:
                    category = category_info
            
            # Extract entities
            entities = self._extract_entities_from_command(command, tokens)
            
            # Check for complex syntax
            is_complex = (
                has_redirects or 
                has_pipes or 
                len(flags) > 2 or 
                any('*' in arg or '?' in arg for arg in args) or
                len(args) > 3
            )
            
            # Check for potential syntax issues
            invalid_syntax = False
            potential_issues = []
            
            # Missing quotes check
            if command != ' '.join(tokens):
                for i, char in enumerate(command):
                    if char in ['"', "'"] and i > 0 and command[i-1] != '\\':
                        # Look for an unescaped matching quote
                        found_match = False
                        for j in range(i+1, len(command)):
                            if command[j] == char and command[j-1] != '\\':
                                found_match = True
                                break
                        if not found_match:
                            invalid_syntax = True
                            potential_issues.append("Unmatched quote detected")
                            break
            
            # Check for common command-specific syntax issues
            if base_command == 'find' and '-name' in flags:
                if len(args) < 2:
                    potential_issues.append("Missing pattern or path for find -name")
            
            if base_command == 'grep' and len(args) < 2:
                potential_issues.append("Missing pattern or file for grep")
            
            if base_command in ['cp', 'mv'] and len(args) < 2:
                potential_issues.append(f"Missing source or destination for {base_command}")
            
            # Estimate risk level for the command
            risk_level = self._estimate_risk_level(base_command, flags, args, has_pipes, has_redirects)
            
            return CommandAnalysis(
                base_command=base_command,
                args=args,
                flags=flags,
                category=category,
                subcategory=subcategory,
                entities=entities,
                is_complex=is_complex,
                has_redirects=has_redirects,
                has_pipes=has_pipes,
                token_count=len(tokens),
                char_count=len(command),
                risk_level=risk_level,
                invalid_syntax=invalid_syntax,
                potential_issues=potential_issues
            )
            
        except ValueError as e:
            # Syntax error in the command (e.g., unbalanced quotes)
            self._logger.warning(f"Command parsing error: {str(e)}")
            return CommandAnalysis(
                base_command=command.split()[0] if command.split() else "",
                args=[],
                flags=[],
                is_complex=True,
                has_redirects='>' in command or '>>' in command or '<' in command,
                has_pipes='|' in command,
                token_count=0,
                char_count=len(command),
                risk_level=0,
                invalid_syntax=True,
                potential_issues=[f"Command parsing error: {str(e)}"]
            )
    
    def _estimate_risk_level(
        self, 
        base_command: str, 
        flags: List[str], 
        args: List[str], 
        has_pipes: bool, 
        has_redirects: bool
    ) -> int:
        """
        Estimate the risk level of a command (0-4).
        
        Args:
            base_command: The command name
            flags: Command flags
            args: Command arguments
            has_pipes: Whether the command uses pipes
            has_redirects: Whether the command uses redirects
            
        Returns:
            Risk level (0-4)
        """
        # Start with a base risk level
        risk_level = 0
        
        # High-risk commands
        high_risk_commands = {
            'rm', 'rmdir', 'dd', 'mkfs', 'fdisk', 'parted',
            'chmod', 'chown', 'shutdown', 'reboot', 'halt',
            'systemctl', 'iptables', 'mkswap', 'swapon', 'swapoff'
        }
        
        # Medium-risk commands
        medium_risk_commands = {
            'mv', 'cp', 'sed', 'awk', 'find', 'kill', 'mount',
            'umount', 'apt', 'apt-get', 'yum', 'dnf', 'pacman',
            'pip', 'npm', 'git', 'docker', 'rsync'
        }
        
        # Low-risk commands (examples, not exhaustive)
        low_risk_commands = {
            'mkdir', 'touch', 'echo', 'cat', 'ls', 'pwd',
            'cd', 'grep', 'less', 'more', 'tail', 'head',
            'ps', 'top', 'df', 'du', 'date', 'whoami'
        }
        
        # Adjust risk level based on command category
        if base_command in high_risk_commands:
            risk_level += 3
        elif base_command in medium_risk_commands:
            risk_level += 2
        elif base_command in low_risk_commands:
            risk_level += 0
        else:
            risk_level += 1  # Unknown command gets a default of 1
        
        # Adjust for risky flags
        risky_flags = {
            'rm': ['-r', '-f', '-rf', '-fr', '--force', '--recursive'],
            'chmod': ['-R', '--recursive'],
            'chown': ['-R', '--recursive'],
            'find': ['-delete', '-exec'],
            'git': ['push', 'reset', '--hard', '--force'],
            'docker': ['system', 'prune', '--all', '--volumes', 'rm'],
        }
        
        if base_command in risky_flags:
            for flag in flags:
                if flag in risky_flags[base_command]:
                    risk_level += 1
                    break
        
        # Adjust for certain argument patterns
        if base_command == 'rm' and (args == ['*'] or args == ['-rf', '*'] or args == ['/', '-rf']):
            risk_level += 2
        
        # Check for redirects that might overwrite files
        if has_redirects and '>' in command and not '>>' in command:
            risk_level += 1
        
        # Check for complex pipe chains
        if has_pipes and command.count('|') > 2:
            risk_level += 1
        
        # Check for sudo
        if base_command == 'sudo':
            risk_level += 2
        
        # Cap risk level at 4
        return min(4, risk_level)
    
    def _extract_entities_from_command(self, command: str, tokens: List[str]) -> List[Entity]:
        """Extract entities from a command."""
        entities = []
        
        # Extract from raw command for entities that might have quotes
        for pattern, entity_type in self._compiled_entity_patterns:
            for match in pattern.finditer(command):
                text = match.group(0)
                # Skip if it's just a flag
                if entity_type == EntityType.FLAG and not text.startswith('-'):
                    continue
                    
                # Check if this entity is already captured
                if not any(e.text == text and e.type == entity_type for e in entities):
                    entities.append(Entity(
                        text=text,
                        type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        # Also extract from tokenized command for better handling of quoted entities
        for token in tokens:
            # Skip the base command
            if token == tokens[0]:
                continue
                
            # Determine entity type based on token
            entity_type = EntityType.UNKNOWN
            
            # Check if it's a flag
            if token.startswith('-'):
                entity_type = EntityType.FLAG
            # Check if it looks like a file path
            elif '/' in token or token.startswith('.') or token.startswith('~'):
                if token.endswith('/'):
                    entity_type = EntityType.DIRECTORY
                else:
                    # Heuristic: If it has an extension, it's likely a file
                    if '.' in token.split('/')[-1]:
                        entity_type = EntityType.FILE
                    else:
                        entity_type = EntityType.DIRECTORY
            
            # Add the entity if not a duplicate
            if entity_type != EntityType.UNKNOWN and not any(e.text == token for e in entities):
                entities.append(Entity(
                    text=token,
                    type=entity_type
                ))
        
        return entities
    
    def _extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text with advanced pattern matching.
        
        Args:
            text: The text to extract entities from
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Apply all compiled patterns
        for pattern, entity_type in self._compiled_entity_patterns:
            for match in pattern.finditer(text):
                text_match = match.group(0)
                
                # Check if this entity is already captured
                if not any(e.text == text_match and e.type == entity_type for e in entities):
                    entities.append(Entity(
                        text=text_match,
                        type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        # Further validate and classify entities
        self._validate_entities(entities)
        
        return entities
    
    def _validate_entities(self, entities: List[Entity]) -> None:
        """
        Validate extracted entities and refine their classifications.
        
        Args:
            entities: List of extracted entities to validate and refine
        """
        # Get current directory for path validation
        cwd = Path.cwd()
        
        for entity in entities:
            # Validate file paths
            if entity.type in [EntityType.FILE, EntityType.DIRECTORY]:
                # Handle relative paths
                path_str = entity.text
                if path_str.startswith('~'):
                    # Expand tilde
                    expanded = os.path.expanduser(path_str)
                    path = Path(expanded)
                else:
                    # Treat as relative to current directory
                    if not path_str.startswith('/'):
                        path = cwd / path_str
                    else:
                        path = Path(path_str)
                
                # Check if the path exists and refine the entity type
                if path.exists():
                    entity.validated = True
                    if path.is_dir():
                        entity.type = EntityType.DIRECTORY
                    else:
                        entity.type = EntityType.FILE
                    entity.value = path
                    entity.confidence = 1.0
                else:
                    # Path doesn't exist, but we can still refine by checking if
                    # it's intended to be a file or directory based on its format
                    entity.validated = False
                    if path_str.endswith('/'):
                        entity.type = EntityType.DIRECTORY
                    elif '.' in path_str.split('/')[-1]:
                        entity.type = EntityType.FILE
                    entity.value = path
                    entity.confidence = 0.7  # Moderate confidence
            
            # Validate flags
            elif entity.type == EntityType.FLAG:
                # Simple validation - just check format
                if entity.text.startswith('--'):
                    # Long flag
                    if '=' in entity.text:
                        entity.validated = True
                        entity.confidence = 0.9
                    else:
                        entity.validated = True
                        entity.confidence = 1.0
                else:
                    # Short flag
                    entity.validated = True
                    entity.confidence = 1.0
    
    def _check_history(self, command: str, command_analysis: CommandAnalysis) -> HistoricalAnalysis:
        """
        Check command history for relevance and success patterns.
        """
        history_manager = get_history_manager()
        
        # This call was already correct from the previous step
        frequency = history_manager.get_command_frequency(command_analysis.base_command)
        success_rate = history_manager.get_command_success_rate(command_analysis.base_command)
        
        # Get similar commands from history
        similar_commands = []
        for cmd_record_obj in history_manager.get_recent_commands(20):
            cmd = cmd_record_obj.command
            if cmd and cmd != command:
                similarity = self._calculate_command_similarity(command, cmd)
                if similarity > 0.5:
                    success = cmd_record_obj.success
                    similar_commands.append((cmd, similarity, success))
        
        similar_commands.sort(key=lambda x: x[1], reverse=True)
        similar_commands = [(cmd, sim) for cmd, sim, success in similar_commands[:5]]

        last_used = None
        for cmd_record_obj in history_manager.get_recent_commands(10):
            if cmd_record_obj.command == command:
                last_used = cmd_record_obj.timestamp
                break
        
        # Calculate pattern match score based on command usage patterns
        command_contexts = history_manager.get_common_command_contexts()
        pattern_match_score = 0.0
        
        recent_base_commands = []
        for cmd_record_obj in history_manager.get_recent_commands(3):
            # This line now correctly calls the method within the ConfidenceScorer class
            recent_base_commands.append(self._extract_base_command(cmd_record_obj.command))

        # This line now correctly calls the method within the ConfidenceScorer class
        current_base_cmd = self._extract_base_command(command)

        for prev_cmd_base in recent_base_commands:
            if prev_cmd_base in command_contexts:
                if current_base_cmd in command_contexts[prev_cmd_base]:
                    pattern_match_score = min(1.0, pattern_match_score + 0.2)
                    break 
        
        if pattern_match_score < 0.1 and current_base_cmd in command_contexts:
            for next_cmd_candidate in command_contexts[current_base_cmd]:
                if next_cmd_candidate in recent_base_commands:
                    pattern_match_score = min(1.0, pattern_match_score + 0.1)
                    break
                
        environment_match_score = 0.7
        
        if frequency == 0:
            historical_score = 0.5
        else:
            frequency_factor = min(frequency / 10.0, 1.0)
            historical_score = 0.3 + (0.7 * ((frequency_factor * 0.6) + (success_rate * 0.4)))
            historical_score = (historical_score * 0.8) + (pattern_match_score * 0.2)
            historical_score = (historical_score * 0.9) + (environment_match_score * 0.1)
        
        return HistoricalAnalysis(
            frequency=frequency,
            success_rate=success_rate,
            last_used=last_used,
            similar_commands=similar_commands,
            pattern_match_score=pattern_match_score,
            environment_match_score=environment_match_score,
            overall_score=historical_score
        )
    
    def _calculate_command_similarity(self, cmd1: str, cmd2: str) -> float:
        """
        Calculate similarity between two commands.
        
        Args:
            cmd1: First command
            cmd2: Second command
            
        Returns:
            Similarity score (0-1)
        """
        # Simple case - exact match
        if cmd1 == cmd2:
            return 1.0
        
        # Extract base command
        base1 = cmd1.split()[0] if cmd1.split() else ""
        base2 = cmd2.split()[0] if cmd2.split() else ""
        
        # Different base commands are less similar
        if base1 != base2:
            return 0.3
        
        # Parse the commands
        try:
            tokens1 = shlex.split(cmd1)
            tokens2 = shlex.split(cmd2)
        except ValueError:
            # Parsing error, fall back to simpler comparison
            tokens1 = cmd1.split()
            tokens2 = cmd2.split()
        
        # Compare token sets for flags and args
        flags1 = set(t for t in tokens1 if t.startswith('-'))
        flags2 = set(t for t in tokens2 if t.startswith('-'))
        
        args1 = set(t for t in tokens1 if not t.startswith('-'))
        args2 = set(t for t in tokens2 if not t.startswith('-'))
        
        # Calculate Jaccard similarity for flags and args
        flags_jaccard = len(flags1.intersection(flags2)) / max(1, len(flags1.union(flags2)))
        args_jaccard = len(args1.intersection(args2)) / max(1, len(args1.union(args2)))
        
        # Sequence similarity using difflib
        seq_ratio = difflib.SequenceMatcher(None, cmd1, cmd2).ratio()
        
        # Combine similarity measures (weighted)
        return 0.1 + (0.3 * flags_jaccard + 0.4 * args_jaccard + 0.2 * seq_ratio)
    
    def _check_complexity(
        self, 
        request: str, 
        command: str, 
        command_analysis: CommandAnalysis
    ) -> float:
        """
        Check if command complexity matches request complexity.
        
        Args:
            request: The original request
            command: The suggested command
            command_analysis: Detailed command analysis
            
        Returns:
            Complexity match score (0-1)
        """
        # Calculate request complexity
        request_tokens = len(request.split())
        request_chars = len(request)
        
        # Get command complexity from analysis
        command_tokens = command_analysis.token_count
        command_chars = command_analysis.char_count
        
        # Calculate complexity ratios
        token_ratio = command_tokens / max(1, request_tokens)
        char_ratio = command_chars / max(1, request_chars)
        
        # Adjust expectations based on request structure
        is_simple_request = request_tokens <= 5 or any(
            simple_term in request.lower() for simple_term in 
            ['list', 'show', 'display', 'view', 'print', 'what is', 'where is']
        )
        
        is_complex_request = request_tokens >= 15 or any(
            complex_term in request.lower() for complex_term in
            ['recursively', 'advanced', 'complex', 'all files', 'multiple', 'find all', 'search for']
        )
        
        # Calculate score based on expected complexity match
        if is_simple_request:
            # Simple requests should generally yield simple commands
            if command_analysis.is_complex or token_ratio > 3.0:
                # Complex command for simple request is suspicious
                return 0.5
            else:
                # Simple command for simple request is good
                return 0.9
        elif is_complex_request:
            # Complex requests may result in complex commands
            if command_analysis.is_complex or token_ratio > 0.5:
                # Complex command for complex request is expected
                return 0.85
            else:
                # Simple command for complex request is questionable
                # (but might be legitimately efficient)
                return 0.7
        else:
            # For moderate requests, expect moderate command complexity
            if 0.3 <= token_ratio <= 2.0:
                # Reasonable match
                return 0.8
            elif 0.2 <= token_ratio <= 3.0:
                # Slightly mismatched but acceptable
                return 0.7
            else:
                # Significantly mismatched
                return 0.5
    
    def _check_semantic_similarity(
        self, 
        request: str, 
        command: str, 
        command_analysis: CommandAnalysis,
        context: Dict[str, Any]
    ) -> SemanticAnalysis:
        """
        Analyze semantic similarity between request and command.
        
        Args:
            request: The original request
            command: The suggested command
            context: Context information
            
        Returns:
            SemanticAnalysis with similarity scores
        """
        # Lower-case the texts for better matching
        request_lower = request.lower()
        command_lower = command.lower()
        
        # Extract key terms from request
        request_terms = set(request_lower.split())
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'if', 'what', 'how', 
                        'is', 'are', 'do', 'does', 'did', 'can', 'could', 'would', 
                        'should', 'will', 'shall', 'may', 'might', 'must', 'to', 
                        'for', 'in', 'on', 'at', 'by', 'with', 'please'}
        request_terms = {term for term in request_terms if term not in common_words}
        
        # Get command terms and flags
        cmd_terms = set(command_lower.split())
        cmd_flags = {term for term in cmd_terms if term.startswith('-')}
        
        # Define common command intents and their keywords
        intent_keywords = {
            "list": {'list', 'show', 'display', 'view', 'files', 'directories', 'contents'},
            "search": {'find', 'search', 'locate', 'grep', 'where', 'which'},
            "create": {'create', 'make', 'new', 'touch', 'mkdir', 'add'},
            "delete": {'delete', 'remove', 'rm', 'erase', 'drop', 'clear'},
            "edit": {'edit', 'modify', 'change', 'update', 'replace', 'sed', 'awk'},
            "copy": {'copy', 'duplicate', 'backup', 'replicate', 'clone'},
            "move": {'move', 'rename', 'relocate', 'shift', 'transfer'},
            "execute": {'run', 'execute', 'start', 'launch', 'perform'},
            "permission": {'permission', 'chmod', 'chown', 'access', 'rights'},
            "compress": {'compress', 'zip', 'archive', 'tar', 'gzip', 'pack'},
            "extract": {'extract', 'unzip', 'unpack', 'decompress', 'expand'},
            "network": {'download', 'upload', 'connect', 'ping', 'network', 'server'},
            "process": {'process', 'kill', 'stop', 'pause', 'resume', 'background'},
            "system": {'system', 'reboot', 'shutdown', 'hibernate', 'sleep'}
        }
        
        # Command mapping to intents
        cmd_to_intent = {
            "ls": "list", "find": "search", "grep": "search", 
            "mkdir": "create", "touch": "create", 
            "rm": "delete", "rmdir": "delete",
            "sed": "edit", "awk": "edit", 
            "cp": "copy", "rsync": "copy",
            "mv": "move", "rename": "move",
            "chmod": "permission", "chown": "permission",
            "zip": "compress", "tar": "compress", "gzip": "compress",
            "unzip": "extract", "gunzip": "extract",
            "wget": "network", "curl": "network", "ping": "network",
            "ps": "process", "kill": "process", "top": "process",
            "shutdown": "system", "reboot": "system"
        }
        
        # Map flag shortcuts
        flag_intent_mapping = {
            "-l": "list detail", "-a": "show all", "-r": "recursive", 
            "-R": "recursive", "-f": "force", "-i": "interactive",
            "-v": "verbose", "-p": "preserve", "-h": "human readable"
        }
        
        # Calculate similarity metrics
        
        # 1. Direct term overlap (Jaccard similarity)
        common_terms = request_terms.intersection(cmd_terms)
        jaccard_similarity = len(common_terms) / max(1, len(request_terms.union(cmd_terms)))
        
        # 2. Detect request intent
        request_intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for kw in keywords if kw in request_lower) / len(keywords)
            request_intent_scores[intent] = score
        
        # Get top request intent
        request_intent = max(request_intent_scores.items(), key=lambda x: x[1])[0]
        request_intent_score = request_intent_scores[request_intent]
        
        # 3. Detect command intent
        command_base = command_lower.split()[0] if command_lower.split() else ""
        command_intent = cmd_to_intent.get(command_base, "unknown")
        
        # 4. Calculate intent match score
        intent_match_score = 1.0 if request_intent == command_intent else 0.3
        if request_intent_score < 0.2:  # If request intent is unclear
            intent_match_score = 0.5  # Neutral score
        
        # 5. Calculate topic match (entities, actions mentioned)
        # Extract nouns and verbs from request and command
        request_entities = self._extract_entities(request)
        request_entity_texts = {entity.text.lower() for entity in request_entities}
        
        command_entities = command_analysis.entities
        command_entity_texts = {entity.text.lower() for entity in command_entities}
        
        # Calculate entity overlap
        common_entities = request_entity_texts.intersection(command_entity_texts)
        entity_similarity = len(common_entities) / max(1, len(request_entity_texts))
        
        # 6. Flag semantics - check if flags match request semantics
        flag_relevance = 0.7  # Default - moderate relevance
        if cmd_flags:
            relevant_flags = 0
            for flag in cmd_flags:
                flag_intent = flag_intent_mapping.get(flag, "")
                if flag_intent and flag_intent.lower() in request_lower:
                    relevant_flags += 1
            
            if relevant_flags > 0:
                flag_relevance = min(1.0, 0.6 + (relevant_flags / len(cmd_flags)) * 0.4)
        
        # 7. Context relevance - check if command makes sense in current context
        context_match_score = self._check_context_semantic_match(request, command, context)
        
        # Combine all scores
        direct_similarity = jaccard_similarity * 0.3
        term_overlap = len(common_terms) / max(1, len(request_terms)) * 0.2
        entity_match = entity_similarity * 0.2
        intent_match = intent_match_score * 0.2
        flag_match = flag_relevance * 0.1
        
        overall_score = direct_similarity + term_overlap + entity_match + intent_match + flag_match
        
        # Ensure score is in valid range
        overall_score = min(1.0, max(0.2, overall_score))
        
        return SemanticAnalysis(
            similarity_score=jaccard_similarity,
            topic_match_score=entity_similarity,
            intent_match_score=intent_match_score,
            key_terms_overlap=term_overlap,
            context_relevant_score=context_match_score,
            overall_score=overall_score
        )
    
    def _check_context_semantic_match(
        self, 
        request: str, 
        command: str, 
        context: Dict[str, Any]
    ) -> float:
        """
        Check if command makes semantic sense in the current context.
        
        Args:
            request: The original request
            command: The suggested command
            context: Context information
            
        Returns:
            Context semantic match score (0-1)
        """
        # Get context manager for environment information
        context_manager = get_context_manager()
        semantic_context = get_semantic_context_manager()
        
        # Start with a neutral score
        context_score = 0.7
        
        # Check for project relevance
        if context_manager.project_root:
            project_type = context_manager.project_type
            project_relevant = False
            
            # Project-specific command checks
            if project_type == "python":
                project_relevant = any(term in command for term in 
                                       ['python', 'pip', 'venv', '.py', 'pytest', 'requirements.txt'])
            elif project_type == "node":
                project_relevant = any(term in command for term in 
                                       ['node', 'npm', 'yarn', 'package.json', '.js', 'jest'])
            elif project_type == "git":
                project_relevant = 'git' in command
            
            if project_relevant:
                context_score += 0.1
        
        # Check for file type relevance
        if context.get("current_file"):
            file_path = context["current_file"]
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Check for file extension specific commands
            if file_ext == '.py' and ('python' in command or '.py' in command):
                context_score += 0.1
            elif file_ext == '.js' and ('node' in command or '.js' in command):
                context_score += 0.1
            elif file_ext == '.html' and ('html' in command or 'http' in command):
                context_score += 0.1
            elif file_ext in ['.jpg', '.png', '.gif'] and ('image' in command or 'convert' in command):
                context_score += 0.1
        
        # Look for recent commands and check for continuity
        recent_commands = context.get("recent_commands", [])
        if recent_commands:
            last_command = recent_commands[0]
            
            # Check for command sequences that make sense
            if last_command.startswith('git clone') and command.startswith('cd '):
                context_score += 0.15
            elif last_command.startswith('cd ') and command.startswith('ls'):
                context_score += 0.1
            elif last_command.startswith('mkdir ') and (
                command.startswith('cd ') or command.startswith('touch ')):
                context_score += 0.1
        
        # Ensure score is in valid range
        return min(1.0, max(0.3, context_score))
    
    def _check_entities(
        self, 
        request: str, 
        command: str, 
        request_entities: List[Entity],
        command_analysis: CommandAnalysis,
        context: Dict[str, Any]
    ) -> float:
        """
        Check for entity matches between request and command.
        
        Analyzes entities extracted from both the request and command
        to determine if the command correctly refers to the entities
        mentioned in the request.
        
        Args:
            request: The original request
            command: The suggested command
            request_entities: Entities extracted from the request
            command_analysis: Detailed command analysis
            context: Context information
            
        Returns:
            Entity match score (0-1)
        """
        command_entities = command_analysis.entities
        
        # Get file activity tracker
        file_activity_tracker = get_file_activity_tracker()
        
        # If no entities in request, return a default score
        if not request_entities:
            # No specific entities mentioned, this is expected in general requests
            return 0.7
        
        # Filter for significant entities (files, directories, etc.)
        significant_request_entities = [
            entity for entity in request_entities 
            if entity.type in (EntityType.FILE, EntityType.DIRECTORY, EntityType.USER, 
                              EntityType.GROUP, EntityType.HOST, EntityType.PATTERN)
        ]
        
        # If no significant entities, check for command-specific entities
        if not significant_request_entities:
            # For search-related operations, look for search terms
            if command_analysis.base_command in ['grep', 'find', 'locate']:
                pattern_request_entities = [
                    entity for entity in request_entities 
                    if entity.type == EntityType.PATTERN
                ]
                if pattern_request_entities and any(
                    pattern.text in command for pattern in pattern_request_entities
                ):
                    return 0.85
            return 0.7  # No specific significant entities to match
        
        # Calculate entity overlap
        # First, normalize entity texts
        request_entity_texts = {self._normalize_entity_text(e.text): e.type for e in significant_request_entities}
        command_entity_texts = {self._normalize_entity_text(e.text): e.type for e in command_entities}
        
        # Look for direct matches
        direct_matches = 0
        for req_text, req_type in request_entity_texts.items():
            for cmd_text, cmd_type in command_entity_texts.items():
                # Exact match
                if req_text == cmd_text:
                    direct_matches += 1
                    break
                # Path-aware match for files and directories
                elif req_type in (EntityType.FILE, EntityType.DIRECTORY) and cmd_type in (EntityType.FILE, EntityType.DIRECTORY):
                    # Check if one path contains the other
                    if req_text in cmd_text or cmd_text in req_text:
                        direct_matches += 0.8
                        break
        
        # Calculate fuzzy matches for filenames
        fuzzy_matches = 0
        for req_text, req_type in request_entity_texts.items():
            if req_type in (EntityType.FILE, EntityType.DIRECTORY):
                req_filename = os.path.basename(req_text)
                for cmd_text, cmd_type in command_entity_texts.items():
                    if cmd_type in (EntityType.FILE, EntityType.DIRECTORY):
                        cmd_filename = os.path.basename(cmd_text)
                        # Use sequence matcher for fuzzy comparison
                        similarity = difflib.SequenceMatcher(None, req_filename, cmd_filename).ratio()
                        if similarity > 0.8:  # High similarity threshold
                            fuzzy_matches += similarity
                            break
        
        # Check for entity resolution through context
        resolved_matches = 0
        if context:
            for req_text, req_type in request_entity_texts.items():
                # Look for files or directories mentioned in context
                if req_type in (EntityType.FILE, EntityType.DIRECTORY):
                    # Get the most recent files from the activity tracker
                    recent_files = file_activity_tracker.get_recent_files(10)
                    for file_info in recent_files:
                        file_path = file_info.get('path', '')
                        file_name = os.path.basename(file_path)
                        
                        # Check if this recent file matches or contains the request entity
                        if (req_text in file_path or file_name == req_text or 
                            difflib.SequenceMatcher(None, file_name, req_text).ratio() > 0.8):
                            # Now check if this resolved file appears in the command
                            for cmd_text, cmd_type in command_entity_texts.items():
                                if file_path in cmd_text or file_name in cmd_text:
                                    resolved_matches += 1
                                    break
        
        # Calculate entity match score
        total_request_entities = len(significant_request_entities)
        match_score = (direct_matches + (fuzzy_matches * 0.8) + (resolved_matches * 0.7)) / max(1, total_request_entities)
        
        # Adjust for command-specific entity expectations
        if command_analysis.base_command in ['ls', 'cd', 'pwd']:
            # These commands might operate on current directory implicitly
            if not any(e.type == EntityType.DIRECTORY for e in command_entities) and match_score < 0.5:
                match_score = max(0.7, match_score)  # Boost score for common navigation commands
        
        # Ensure score is in valid range
        match_score = min(1.0, max(0.3, match_score))
        
        return match_score
    
    def _normalize_entity_text(self, text: str) -> str:
        """Normalize entity text for comparison."""
        # Remove quotes
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        
        # Expand tilde
        if text.startswith('~'):
            text = os.path.expanduser(text)
        
        # Normalize path separators
        text = text.replace('\\', '/')
        
        return text.lower()
    
    def _check_command_flags(
        self, 
        command: str, 
        command_analysis: CommandAnalysis
    ) -> float:
        """
        Validate command flags and options for correctness and compatibility.
        
        Args:
            command: The suggested command
            command_analysis: Detailed command analysis
            
        Returns:
            Flag validation score (0-1)
        """
        # If no flags in the command, return a high score (nothing to validate)
        if not command_analysis.flags:
            return 1.0
        
        # Default score - moderate confidence
        validation_score = 0.7
        
        # Get base command and flags
        base_command = command_analysis.base_command
        flags = command_analysis.flags
        
        # Check if we have compatibility data for this command
        if base_command in self._flag_compatibility:
            flag_data = self._flag_compatibility[base_command]
            
            # Check for incompatible flag combinations
            incompatible_found = False
            for flag in flags:
                if flag in flag_data:
                    incompatible_flags = flag_data[flag].get('incompatible_with', [])
                    for incompatible in incompatible_flags:
                        if incompatible in flags:
                            incompatible_found = True
                            validation_score -= 0.2  # Reduce score for each incompatibility
                            if validation_score < 0.3:
                                # Don't reduce score below 0.3
                                validation_score = 0.3
                            break
            
            # Check for expected flag combinations
            expected_combinations = 0
            missing_combinations = 0
            
            for flag in flags:
                if flag in flag_data:
                    compatible_flags = flag_data[flag].get('compatible_with', [])
                    for compatible in compatible_flags:
                        if compatible in flags:
                            expected_combinations += 1
                        # Only count as missing if it's commonly used together
                        # This could be enhanced with frequency data
            
            # Boost score for expected combinations
            if expected_combinations > 0:
                validation_score = min(1.0, validation_score + (expected_combinations * 0.05))
        
        # Check for potentially malformed flags
        malformed_flags = 0
        for flag in flags:
            # Check for long flag format
            if flag.startswith('--'):
                if not re.match(r'--[a-zA-Z][-a-zA-Z0-9]*(=[^\s]+)?$', flag):
                    malformed_flags += 1
            # Check for short flag format with combined options
            elif flag.startswith('-') and len(flag) > 2:
                # For commands that don't typically use combined flags
                if base_command in ['find', 'git', 'docker'] and not re.match(r'-[a-zA-Z0-9]+$', flag): # Check against 'flag' variable
                    malformed_flags += 1
                elif base_command not in ['head', 'tail', 'chmod', 'dd'] and re.search(r'\d', flag[1:]): # Check for digits in flag chars
                    malformed_flags += 1
                var_name = arg[1:]
                if var_name not in env_vars:
                    env_score = max(0.4, env_score - 0.1)
        
        # Check for command name resolution via PATH
        if command_analysis.base_command not in ['cd', 'pwd', 'echo', 'export', 'source']:
            # Check if command is in PATH
            cmd_in_path = False
            if 'PATH' in env_vars:
                path_dirs = env_vars['PATH'].split(':')
                for path_dir in path_dirs:
                    cmd_path = os.path.join(path_dir, command_analysis.base_command)
                    if os.path.exists(cmd_path) and os.access(cmd_path, os.X_OK):
                        cmd_in_path = True
                        break
            
            if not cmd_in_path:
                # Could be a built-in shell command or alias, don't penalize too much
                env_score = max(0.5, env_score - 0.1)
        
        return min(1.0, max(0.3, env_score))
    
    def _analyze_risk(
        self, 
        command: str, 
        command_analysis: CommandAnalysis,
        context: Dict[str, Any]
    ) -> RiskAnalysis:
        """
        Analyze the risk level and safety aspects of a command.
        
        Args:
            command: The suggested command
            command_analysis: Detailed command analysis
            context: Context information
            
        Returns:
            RiskAnalysis with risk scores and details
        """
        # Get base risk level from command analysis
        risk_level = command_analysis.risk_level
        risk_factors = []
        
        # Default to requiring confirmation for level 2+ risks
        requires_confirmation = risk_level >= 2
        
        # Destructive operations always have risks
        if command_analysis.base_command in ['rm', 'rmdir', 'shred']:
            risk_factors.append("Command can permanently delete data")
            
            # Check for especially risky rm patterns
            if command_analysis.base_command == 'rm':
                if '-rf' in command_analysis.flags or ('-r' in command_analysis.flags and '-f' in command_analysis.flags):
                    risk_factors.append("Recursive forced deletion")
                    requires_confirmation = True
                
                if '*' in command or '?' in command:
                    risk_factors.append("Wildcard deletion pattern")
                    requires_confirmation = True
                    
                if '/' in command and not command.endswith('/'):
                    # Deleting something with a path component
                    risk_factors.append("Deleting file/directory with path component")
        
        # System modification commands
        if command_analysis.base_command in ['chown', 'chmod', 'chgrp']:
            risk_factors.append("Command modifies file permissions/ownership")
            
            # Check for recursive permission changes
            if '-R' in command_analysis.flags or '--recursive' in command_analysis.flags:
                risk_factors.append("Recursive permission/ownership change")
                requires_confirmation = True
                
            # Check for critical directories
            for arg in command_analysis.args:
                if arg in ['/', '/etc', '/bin', '/usr', '/lib']:
                    risk_factors.append("Critical system directory modification")
                    requires_confirmation = True
        
        # File overwrite risks
        if '>' in command and not '>>' in command:
            risk_factors.append("Output redirection may overwrite files")
            
            # Try to extract the file being written to
            redirect_match = re.search(r'>\s*(\S+)', command)
            if redirect_match:
                file_path = redirect_match.group(1)
                if os.path.exists(file_path):
                    risk_factors.append(f"Will overwrite existing file: {file_path}")
                    requires_confirmation = True
        
        # Special risky commands
        risky_operation_patterns = {
            r'sudo|su': "Administrative privilege escalation",
            r'mkfs|fdisk|parted': "Disk partitioning/formatting operation",
            r'dd': "Low-level disk operation",
            r'iptables|ufw': "Firewall modification",
            r'shutdown|reboot|halt|poweroff': "System power operation",
            r'mount|umount': "Filesystem mounting operation",
            r'kill|pkill|killall': "Process termination",
            r'passwd|useradd|userdel|groupadd|groupdel': "User/group management",
            r'wget|curl.*\s*\|\s*sh': "Executing code from network",
            r'eval|source': "Executing dynamic content",
        }
        
        for pattern, description in risky_operation_patterns.items():
            if re.search(pattern, command):
                risk_factors.append(description)
                requires_confirmation = True
        
        # Modifying commands with backups
        is_reversible = '--backup' in command or command_analysis.base_command in ['cp', 'rsync'] and '-b' in command_analysis.flags
        
        # Assess impact scope
        impact_scope = "local"  # Default
        if 'sudo' in command:
            impact_scope = "system"
        elif command_analysis.base_command in ['docker', 'podman', 'kubectl', 'ssh']:
            impact_scope = "remote"
        elif command_analysis.base_command in ['curl', 'wget', 'git']:
            impact_scope = "network"
        
        # Calculate safety score (inverse of risk)
        safety_score = 1.0 - (risk_level / 4.0)
        
        # Adjust safety score based on risk factors
        safety_score -= len(risk_factors) * 0.05
        
        # If reversible, slightly improve safety
        if is_reversible:
            safety_score = min(1.0, safety_score + 0.1)
        
        # Ensure safety score is in valid range
        safety_score = min(1.0, max(0.1, safety_score))
        
        # Overall score is weighted safety_score
        overall_score = safety_score
        
        # User safety preference adjustment
        user_data = context.get("user_data", {})
        if user_data.get("safety_preference") == "conservative":
            # More safety-conscious user, lower score for risky commands
            overall_score = max(0.3, overall_score - 0.1)
            requires_confirmation = requires_confirmation or risk_level >= 1
        elif user_data.get("safety_preference") == "permissive":
            # Less safety-conscious user, higher score for risky commands
            overall_score = min(0.9, overall_score + 0.1)
            requires_confirmation = requires_confirmation and risk_level >= 3
        
        return RiskAnalysis(
            risk_level=risk_level,
            risk_factors=risk_factors,
            safety_score=safety_score,
            requires_confirmation=requires_confirmation,
            is_reversible=is_reversible,
            impact_scope=impact_scope,
            overall_score=overall_score
        )
    
    def _check_user_preferences(
        self, 
        command: str, 
        command_analysis: CommandAnalysis,
        context: Dict[str, Any]
    ) -> float:
        """
        Check if command matches user preferences and patterns.
        
        Args:
            command: The suggested command
            command_analysis: Detailed command analysis
            context: Context information
            
        Returns:
            User preference match score (0-1)
        """
        # Start with a neutral score
        preference_score = 0.7
        
        # Get session manager for user preferences
        session_manager = get_session_manager()
        
        # Get preferences from context
        preferences = context.get("preferences", {})
        
        # Check for favorite/commonly used commands
        history_manager = get_history_manager()
        favorite_commands = history_manager.get_favorite_commands(10)
        
        base_command = command_analysis.base_command
        if base_command in favorite_commands:
            # User frequently uses this command
            preference_score = min(1.0, preference_score + 0.15)
        
        # Check for preferred flags
        if base_command in favorite_commands:
            # Get most common flags used with this command
            common_flags = history_manager.get_common_flags_for_command(base_command)
            
            # Check if current flags match common usage
            if common_flags:
                for flag in command_analysis.flags:
                    if flag in common_flags:
                        preference_score = min(1.0, preference_score + 0.05)
        
        # Check for trusted commands
        trusted_commands = preferences.get("trusted_commands", [])
        if base_command in trusted_commands:
            preference_score = min(1.0, preference_score + 0.1)
            
        # Check for untrusted commands
        untrusted_commands = preferences.get("untrusted_commands", [])
        if base_command in untrusted_commands:
            preference_score = max(0.3, preference_score - 0.2)
        
        # Check for verbose preference
        verbose_preference = preferences.get("verbose_output", False)
        has_verbose = '-v' in command_analysis.flags or '--verbose' in command_analysis.flags
        
        if verbose_preference and has_verbose:
            preference_score = min(1.0, preference_score + 0.05)
        elif verbose_preference and not has_verbose and command_analysis.base_command in ['ls', 'cp', 'mv', 'rm']:
            preference_score = max(0.4, preference_score - 0.05)
        
        # Check for interactive preference
        interactive_preference = preferences.get("interactive_mode", False)
        has_interactive = '-i' in command_analysis.flags or '--interactive' in command_analysis.flags
        
        if interactive_preference and has_interactive:
            preference_score = min(1.0, preference_score + 0.05)
        elif interactive_preference and not has_interactive and command_analysis.base_command in ['cp', 'mv', 'rm']:
            preference_score = max(0.4, preference_score - 0.05)
        
        # Check for force preference
        force_preference = preferences.get("force_operations", False)
        has_force = '-f' in command_analysis.flags or '--force' in command_analysis.flags
        
        if force_preference and has_force:
            preference_score = min(1.0, preference_score + 0.05)
        elif force_preference and not has_force and command_analysis.base_command in ['cp', 'mv', 'rm']:
            preference_score = max(0.4, preference_score - 0.05)
        
        # Check active session entities
        session_entities = session_manager.get_recent_entities(entity_type="file", limit=5)
        for entity_id, entity_data in session_entities.items():
            # Check if file is referenced in command
            if entity_id in command:
                preference_score = min(1.0, preference_score + 0.1)
                break
        
        return preference_score
    
    def _generate_cache_key(self, request: str, command: str) -> str:
        """Generate a cache key for a request-command pair."""
        # Create a stable hash that combines request and command
        combined = f"{request}:{command}"
        # Use a stable hashing algorithm (SHA-256)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[float]:
        """
        Get a cached confidence score if available and not expired.
        
        Args:
            cache_key: The cache key for the request-command pair
            
        Returns:
            Cached confidence score or None if not in cache or expired
        """
        cache_entry = self._cache.get(cache_key)
        if not cache_entry:
            return None
        
        # Check if entry is expired
        timestamp = cache_entry.get("timestamp", 0)
        if time.time() - timestamp > self._cache_ttl:
            # Expired entry, remove from cache
            del self._cache[cache_key]
            return None
        
        return cache_entry.get("score")
    
    def _add_to_cache(
        self, 
        cache_key: str, 
        score: float, 
        factors: ConfidenceFactors
    ) -> None:
        """
        Add a confidence score to the cache.
        
        Args:
            cache_key: The cache key for the request-command pair
            score: The confidence score to cache
            factors: Detailed confidence factors
        """
        # Create cache entry
        cache_entry = {
            "score": score,
            "timestamp": time.time(),
            "factors": factors
        }
        
        # Add to cache
        self._cache[cache_key] = cache_entry
        
        # Check if cache size limit is exceeded
        if len(self._cache) > self._cache_size_limit:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            
            # Remove oldest 10% of entries
            num_to_remove = max(1, int(self._cache_size_limit * 0.1))
            for key in sorted_keys[:num_to_remove]:
                del self._cache[key]
    
    def _log_detailed_confidence_analysis(
        self, 
        confidence: float, 
        factors: ConfidenceFactors,
        computation_time: float
    ) -> None:
        """
        Log detailed confidence analysis for debugging.
        
        Args:
            confidence: The final confidence score
            factors: Detailed confidence factors
            computation_time: Time taken to compute the score
        """
        self._logger.debug(f"=== Detailed Confidence Analysis ===")
        self._logger.debug(f"Final Score: {confidence:.4f} (computed in {computation_time:.3f}s)")
        
        # Log historical factors
        self._logger.debug(f"Historical Analysis:")
        self._logger.debug(f"  - Score: {factors.historical.overall_score:.4f}")
        self._logger.debug(f"  - Frequency: {factors.historical.frequency}")
        self._logger.debug(f"  - Success Rate: {factors.historical.success_rate:.4f}")
        
        # Log semantic analysis
        self._logger.debug(f"Semantic Analysis:")
        self._logger.debug(f"  - Score: {factors.semantic.overall_score:.4f}")
        self._logger.debug(f"  - Similarity: {factors.semantic.similarity_score:.4f}")
        self._logger.debug(f"  - Topic Match: {factors.semantic.topic_match_score:.4f}")
        self._logger.debug(f"  - Intent Match: {factors.semantic.intent_match_score:.4f}")
        
        # Log command analysis
        self._logger.debug(f"Command Analysis:")
        self._logger.debug(f"  - Base Command: {factors.command.base_command}")
        self._logger.debug(f"  - Category: {factors.command.category}")
        self._logger.debug(f"  - Subcategory: {factors.command.subcategory}")
        self._logger.debug(f"  - Is Complex: {factors.command.is_complex}")
        self._logger.debug(f"  - Has Redirects: {factors.command.has_redirects}")
        self._logger.debug(f"  - Has Pipes: {factors.command.has_pipes}")
        self._logger.debug(f"  - Risk Level: {factors.command.risk_level}")
        if factors.command.invalid_syntax:
            self._logger.debug(f"  - Invalid Syntax: True")
            self._logger.debug(f"  - Issues: {factors.command.potential_issues}")
        
        # Log entity match score
        self._logger.debug(f"Entity Match Score: {factors.entity_match_score:.4f}")
        
        # Log complexity match score
        self._logger.debug(f"Complexity Match Score: {factors.complexity_match_score:.4f}")
        
        # Log flag validation score
        self._logger.debug(f"Flag Validation Score: {factors.flag_validation_score:.4f}")
        
        # Log context relevance score
        self._logger.debug(f"Context Relevance Score: {factors.context_relevance_score:.4f}")
        
        # Log risk analysis
        self._logger.debug(f"Risk Analysis:")
        self._logger.debug(f"  - Score: {factors.risk.overall_score:.4f}")
        self._logger.debug(f"  - Risk Level: {factors.risk.risk_level}")
        self._logger.debug(f"  - Requires Confirmation: {factors.risk.requires_confirmation}")
        if factors.risk.risk_factors:
            self._logger.debug(f"  - Risk Factors: {factors.risk.risk_factors}")
        
        # Log user preference score
        self._logger.debug(f"User Preference Score: {factors.user_preference_score:.4f}")
        
        self._logger.debug(f"=====================================")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the confidence scorer's performance.
        
        Returns:
            Dictionary with performance statistics
        """
        return {
            "total_evaluations": self._stats["total_evaluations"],
            "cache_hits": self._stats["cache_hits"],
            "cache_hit_ratio": self._stats["cache_hits"] / max(1, self._stats["total_evaluations"]),
            "high_confidence_count": self._stats["high_confidence_count"],
            "low_confidence_count": self._stats["low_confidence_count"],
            "avg_computation_time": self._stats["avg_computation_time"],
            "cache_size": len(self._cache),
            "cache_size_limit": self._cache_size_limit,
        }
    
    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self._stats = {
            "total_evaluations": 0,
            "cache_hits": 0,
            "high_confidence_count": 0,
            "low_confidence_count": 0,
            "avg_computation_time": 0.0,
            "total_computation_time": 0.0,
        }
    
    def clear_cache(self) -> None:
        """Clear the confidence score cache."""
        self._cache.clear()

# Global confidence scorer instance
confidence_scorer = ConfidenceScorer()
