# angela/ai/analyzer.py

import re
import os
import sys
import shlex
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

from angela.utils.logging import get_logger
from angela.api.context import get_history_manager

logger = get_logger(__name__)

class ErrorAnalyzer:
    """Analyzer for command errors with fix suggestions."""
    
    # Common error patterns and their explanations/fixes
    ERROR_PATTERNS = [
        # File not found
        (r'No such file or directory', 'The specified file or directory does not exist', [
            'Check if the path is correct',
            'Use ls to view available files',
            'Use find to search for the file'
        ]),
        # Permission denied
        (r'Permission denied', 'You don\'t have sufficient permissions', [
            'Check file permissions with ls -l',
            'Use sudo for operations requiring elevated privileges',
            'Change permissions with chmod'
        ]),
        # Command not found
        (r'command not found', 'The command is not installed or not in PATH', [
            'Check if the command is installed',
            'Install the package containing the command',
            'Check your PATH environment variable'
        ]),
        # Syntax errors
        (r'syntax error', 'There\'s a syntax error in the command', [
            'Check for missing quotes or brackets',
            'Check the command documentation for correct syntax',
            'Simplify the command and try again'
        ]),
        # Network errors
        (r'(Connection refused|Network is unreachable)', 'Network connection issue', [
            'Check if the host is reachable',
            'Verify network connectivity',
            'Check if the service is running on the target host'
        ])
    ]
    
    def __init__(self):
        """Initialize the error analyzer."""
        self._logger = logger
    
    def analyze_error(self, command: str, error: str) -> Dict[str, Any]:
        """
        Analyze a command error and provide fix suggestions.
        
        Args:
            command: The failed command
            error: The error output
            
        Returns:
            Dictionary with analysis and suggestions
        """
        self._logger.debug(f"Analyzing error for command: {command}")
        
        # Extract the important parts of the error
        error_short = self._extract_key_error(error)
        
        # Check for known error patterns
        pattern_match = self._match_error_pattern(error)
        
        # Check command history for similar errors and their fixes
        historical_fixes = get_history_manager().find_error_patterns(error_short)
        
        # Analyze command structure for potential issues
        command_issues = self._analyze_command_structure(command)
        
        # Check for missing files or directories
        file_issues = self._check_file_references(command, error)
        
        # Build the response
        result = {
            "error_summary": error_short,
            "possible_cause": pattern_match[1] if pattern_match else "Unknown error",
            "fix_suggestions": pattern_match[2] if pattern_match else [],
            "historical_fixes": [fix for _, fix in historical_fixes],
            "command_issues": command_issues,
            "file_issues": file_issues
        }
        
        return result
    
    def _extract_key_error(self, error: str) -> str:
        """
        Extract the key part of an error message.
        
        Args:
            error: The full error output
            
        Returns:
            A shorter, more focused error message
        """
        # Split by lines and remove empty ones
        lines = [line.strip() for line in error.splitlines() if line.strip()]
        
        if not lines:
            return "Unknown error"
        
        # Check for common error patterns in the first few lines
        for line in lines[:3]:
            # Look for lines with "error" or "ERROR"
            if "error" in line.lower():
                return line
            
            # Look for lines with common error indicators
            for pattern, _, _ in self.ERROR_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    return line
        
        # If no clear error pattern is found, return the first line
        return lines[0]
    
    def _match_error_pattern(self, error: str) -> Optional[Tuple[str, str, List[str]]]:
        """
        Match an error against known patterns.
        
        Args:
            error: The error output
            
        Returns:
            Tuple of (pattern, explanation, fixes) or None if no match
        """
        for pattern, explanation, fixes in self.ERROR_PATTERNS:
            if re.search(pattern, error, re.IGNORECASE):
                return (pattern, explanation, fixes)
        
        return None
    
    def _analyze_command_structure(self, command: str) -> List[str]:
        """
        Analyze command structure for potential issues.
        
        Args:
            command: The command string
            
        Returns:
            List of potential issues
        """
        issues = []
        
        # Check if the command is empty
        if not command.strip():
            issues.append("Command is empty")
            return issues
        
        try:
            # Try to parse the command with shlex
            tokens = shlex.split(command)
            
            # Check for basic command structure
            if not tokens:
                issues.append("Command parsing failed")
                return issues
            
            base_cmd = tokens[0]
            
            # Check for redirect without command
            if base_cmd in ['>', '>>', '<']:
                issues.append("Redirect symbol used as command")
            
            # Check for pipe without command
            if base_cmd == '|':
                issues.append("Pipe symbol used as command")
            
            # Check for unbalanced quotes (shlex would have raised an error)
            
            # Check for missing arguments in common commands
            if len(tokens) == 1:
                if base_cmd in ['cp', 'mv', 'ln']:
                    issues.append(f"{base_cmd} requires source and destination arguments")
                elif base_cmd in ['grep', 'sed', 'awk']:
                    issues.append(f"{base_cmd} requires a pattern and input")
            
            # Check for potentially incorrect flag formats
            for token in tokens[1:]:
                if token.startswith('-') and len(token) > 2 and not token.startswith('--'):
                    # Might be combining single-letter flags incorrectly
                    if any(not c.isalpha() for c in token[1:]):
                        issues.append(f"Potentially malformed flag: {token}")
            
        except ValueError as e:
            # This typically happens with unbalanced quotes
            issues.append(f"Command parsing error: {str(e)}")
        
        return issues
    
    def _check_file_references(self, command: str, error: str) -> List[Dict[str, Any]]:
        """
        Check for file references in the command that might be causing issues.
        
        Args:
            command: The command string
            error: The error output
            
        Returns:
            List of file issues
        """
        issues = []
        
        # Extract potential file paths from the command
        try:
            tokens = shlex.split(command)
            
            # Skip the command name
            potential_paths = []
            for token in tokens[1:]:
                # Skip options
                if token.startswith('-'):
                    continue
                
                # Skip operators
                if token in ['|', '>', '>>', '<', '&&', '||', ';']:
                    continue
                
                # Consider as potential path
                potential_paths.append(token)
            
            # Check if the paths exist
            for path_str in potential_paths:
                path = Path(path_str)
                
                # Only check if it looks like a path
                if '/' in path_str or '.' in path_str:
                    issue = {"path": path_str}
                    
                    if not path.exists():
                        issue["exists"] = False
                        issue["suggestion"] = f"File/directory does not exist: {path_str}"
                        
                        # Check for common typos
                        parent = path.parent
                        if parent.exists():
                            # Check for similar files in the same directory
                            similar_files = []
                            try:
                                for p in parent.iterdir():
                                    # Simple similarity: Levenshtein distance approximation
                                    if p.name.startswith(path.name[:2]) or p.name.endswith(path.name[-2:]):
                                        similar_files.append(p.name)
                            except (PermissionError, OSError):
                                pass
                            
                            if similar_files:
                                issue["similar_files"] = similar_files[:3]  # Limit to top 3
                        
                        issues.append(issue)
                    else:
                        # Check for permission issues
                        issue["exists"] = True
                        if "Permission denied" in error and not os.access(path, os.R_OK):
                            issue["permission"] = False
                            issue["suggestion"] = f"Permission denied for: {path_str}"
                            issues.append(issue)
        
        except Exception as e:
            logger.exception(f"Error checking file references: {str(e)}")
        
        return issues
    
    def generate_fix_suggestions(self, command: str, error: str) -> List[str]:
        """
        Generate fix suggestions for a failed command.
        
        Args:
            command: The failed command
            error: The error output
            
        Returns:
            List of suggested fixes
        """
        # Analyze the error
        analysis = self.analyze_error(command, error)
        
        # Combine all suggestions
        suggestions = []
        
        # Add suggestions from pattern matching
        suggestions.extend(analysis["fix_suggestions"])
        
        # Add suggestions from historical fixes
        if analysis["historical_fixes"]:
            for i, fix in enumerate(analysis["historical_fixes"], 1):
                suggestions.append(f"Previous fix: {fix}")
        
        # Add suggestions from command issues
        for issue in analysis["command_issues"]:
            if issue == "Command parsing failed":
                suggestions.append("Check for unbalanced quotes or special characters")
            elif "requires" in issue:
                suggestions.append(issue)  # Already a suggestion
            elif "flag" in issue:
                suggestions.append("Check command flags format")
        
        # Add suggestions from file issues
        for issue in analysis["file_issues"]:
            if "suggestion" in issue:
                suggestions.append(issue["suggestion"])
            
            if "similar_files" in issue:
                similar = ", ".join(issue["similar_files"])
                suggestions.append(f"Did you mean one of these: {similar}?")
        
        # Deduplicate suggestions
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            suggestion_key = suggestion.lower()
            if suggestion_key not in seen:
                seen.add(suggestion_key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions

# Global error analyzer instance
error_analyzer = ErrorAnalyzer()
