# angela/safety/classifier.py
"""
Command and operation risk classification system for Angela CLI.

This module is responsible for determining the risk level of commands 
and operations to ensure appropriate confirmation and safety measures.
"""
import re
import shlex
from typing import List, Dict, Tuple, Set, Optional

from angela.constants import RISK_LEVELS
from angela.utils.logging import get_logger

logger = get_logger(__name__)

# Define risk patterns for shell commands
RISK_PATTERNS = {
    # Critical risk - destructive operations
    RISK_LEVELS["CRITICAL"]: [
        # rm with recursive or force flags
        (r"^rm\s+.*((-r|-rf|--recursive|-f|--force)\b|--)", "File deletion with dangerous flags"),
        # Disk formatting
        (r"^(mkfs|fdisk|dd)\b", "Disk formatting/partitioning"), 
        # Systemwide configuration changes
        (r"^(sudo|pkexec|su)\s+", "Privileged operation"),
        # Direct writes to device files
        (r">\s*/dev/", "Direct write to device file"),
    ],
    
    # High risk - significant changes
    RISK_LEVELS["HIGH"]: [
        # Regular file deletion
        (r"^rm\s+", "File deletion"),
        # Moving files
        (r"^mv\s+", "File movement"),
        # Installing packages
        (r"^(apt(-get)?|yum|pacman|dnf|brew)\s+(install|remove|purge)\b", "Package management"),
        # Changing permissions
        (r"^chmod\s+", "Changing file permissions"),
        # Changing ownership
        (r"^chown\s+", "Changing file ownership"),
    ],
    
    # Medium risk - file modifications
    RISK_LEVELS["MEDIUM"]: [
        # Writing to files
        (r"(>|>>)\s*[\w\./-]+", "Writing to files"),
        # Editing files
        (r"^(nano|vim|vi|emacs|sed)\s+", "File editing"),
        # Creating symbolic links
        (r"^ln\s+(-s|--symbolic)\s+", "Creating symbolic links"),
        # Transferring files remotely
        (r"^(scp|rsync)\s+", "File transfer"),
    ],
    
    # Low risk - creating files/dirs without overwriting
    RISK_LEVELS["LOW"]: [
        # Making directories
        (r"^mkdir\s+", "Creating directory"),
        # Touching files
        (r"^touch\s+", "Creating/updating file timestamp"),
        # Copying files
        (r"^cp\s+", "Copying files"),
    ],
    
    # Safe - read-only operations
    RISK_LEVELS["SAFE"]: [
        # Listing files
        (r"^ls\s+", "Listing files"),
        # Reading files
        (r"^(cat|less|more|head|tail)\s+", "Reading file content"),
        # Finding files
        (r"^find\s+", "Finding files"),
        # Viewing disk usage
        (r"^du\s+", "Checking disk usage"),
        # Getting working directory
        (r"^pwd\s*$", "Printing working directory"),
        # Checking file status
        (r"^(stat|file)\s+", "Checking file information"),
    ],
}

# Special case patterns that override normal classification
OVERRIDE_PATTERNS = {
    # Force certain grep operations to be safe
    "SAFE": [
        r"^grep\s+(-r|--recursive)?\s+[\w\s]+\s+[\w\s\./-]+$",  # Basic grep with fixed strings
        r"^find\s+[\w\s\./-]+\s+-name\s+[\w\s\*\./-]+$",  # Basic find by name
    ],
    # Operations that should always be considered critical regardless of base command
    "CRITICAL": [
        r"[\s;|`]+rm\s+(-r|-f|--recursive|--force)\s+[~/]",  # rm commands affecting home or root
        r"[\s;|`]+dd\s+",  # dd embedded in a command chain
        r">/dev/null\s+2>&1",  # Redirecting errors (often hiding destructive operations)
    ],
}

def classify_command_risk(command: str) -> Tuple[int, str]:
    """
    Classify the risk level of a shell command.
    
    Args:
        command: The shell command to classify.
        
    Returns:
        A tuple of (risk_level, reason), where risk_level is an integer
        from the RISK_LEVELS constants and reason is a string explaining
        the classification.
    """
    if not command.strip():
        return RISK_LEVELS["SAFE"], "Empty command"
    
    # First check override patterns that would force a specific risk level
    for level_name, patterns in OVERRIDE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, command):
                level = RISK_LEVELS[level_name]
                return level, f"Matched override pattern for {level_name} risk"
    
    # Check standard risk patterns from highest to lowest risk
    for level, patterns in sorted(RISK_PATTERNS.items(), key=lambda x: x[0], reverse=True):
        for pattern, reason in patterns:
            if re.search(pattern, command.strip()):
                return level, reason
    
    # Default to medium risk if no pattern matches
    # It's safer to require confirmation for unknown commands
    return RISK_LEVELS["MEDIUM"], "Unrecognized command type"


def analyze_command_impact(command: str) -> Dict[str, any]:
    """
    Analyze the potential impact of a command.
    
    Args:
        command: The shell command to analyze.
        
    Returns:
        A dictionary containing impact analysis information, such as
        affected files, operations, etc.
    """
    impact = {
        "affected_files": set(),
        "affected_dirs": set(),
        "operations": [],
        "destructive": False,
        "creates_files": False,
        "modifies_files": False,
    }
    
    try:
        # Simple lexical analysis of the command
        tokens = shlex.split(command)
        if not tokens:
            return impact
        
        base_cmd = tokens[0]
        args = tokens[1:]
        
        # Extract potentially affected files and directories
        for arg in args:
            # Skip arguments that start with a dash (options)
            if arg.startswith('-'):
                continue
            
            # Skip redirection operators
            if arg in ['>', '>>', '<', '|']:
                continue
                
            # Assume it might be a file or directory path
            if '/' in arg or '.' in arg or not arg.startswith('-'):
                if base_cmd in ['rm', 'mv', 'rmdir']:
                    impact["destructive"] = True
                
                if base_cmd in ['mkdir']:
                    impact["affected_dirs"].add(arg)
                    impact["creates_files"] = True
                else:
                    impact["affected_files"].add(arg)
                
                if base_cmd in ['cp', 'mv', 'touch', 'mkdir', 'ln']:
                    impact["creates_files"] = True
                
                if base_cmd in ['vim', 'nano', 'sed', 'cp', 'mv']:
                    impact["modifies_files"] = True
        
        # Record the type of operation
        if base_cmd in ['ls', 'find', 'grep', 'cat', 'less', 'more', 'tail', 'head']:
            impact["operations"].append("read")
        elif base_cmd in ['rm', 'rmdir']:
            impact["operations"].append("delete")
        elif base_cmd in ['mv']:
            impact["operations"].append("move")
        elif base_cmd in ['cp']:
            impact["operations"].append("copy")
        elif base_cmd in ['touch', 'mkdir']:
            impact["operations"].append("create")
        elif base_cmd in ['chmod', 'chown']:
            impact["operations"].append("change_attributes")
        else:
            impact["operations"].append("unknown")
    
    except Exception as e:
        logger.exception(f"Error analyzing command impact for '{command}': {str(e)}")
    
    # Convert sets to lists for easier serialization
    impact["affected_files"] = list(impact["affected_files"])
    impact["affected_dirs"] = list(impact["affected_dirs"])
    
    return impact
