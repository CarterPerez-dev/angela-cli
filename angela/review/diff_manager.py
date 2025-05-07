# angela/review/diff_manager.py
"""
Diff management for Angela CLI.

This module provides functionality for managing and presenting diffs
between original and modified code.
"""
import os
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from angela.utils.logging import get_logger

logger = get_logger(__name__)

class DiffManager:
    """
    Manager for generating and displaying code diffs.
    """
    
    def __init__(self):
        """Initialize the diff manager."""
        self._logger = logger
    
    def generate_diff(
        self, 
        original: str, 
        modified: str, 
        context_lines: int = 3
    ) -> str:
        """
        Generate a unified diff between original and modified content.
        
        Args:
            original: Original content
            modified: Modified content
            context_lines: Number of context lines to include
            
        Returns:
            Unified diff string
        """
        self._logger.debug("Generating diff")
        
        # Split content into lines
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        # Generate unified diff
        diff = difflib.unified_diff(
            original_lines, 
            modified_lines,
            fromfile='original',
            tofile='modified',
            n=context_lines
        )
        
        return ''.join(diff)
    
    def generate_html_diff(
        self, 
        original: str, 
        modified: str, 
        context_lines: int = 3
    ) -> str:
        """
        Generate an HTML diff between original and modified content.
        
        Args:
            original: Original content
            modified: Modified content
            context_lines: Number of context lines to include
            
        Returns:
            HTML diff string
        """
        self._logger.debug("Generating HTML diff")
        
        # Split content into lines
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Generate HTML diff
        diff = difflib.HtmlDiff().make_file(
            original_lines, 
            modified_lines,
            fromdesc='Original',
            todesc='Modified',
            context=True,
            numlines=context_lines
        )
        
        return diff
    
    def generate_file_diff(
        self, 
        original_file: Union[str, Path], 
        modified_file: Union[str, Path],
        context_lines: int = 3
    ) -> str:
        """
        Generate a unified diff between original and modified files.
        
        Args:
            original_file: Path to original file
            modified_file: Path to modified file
            context_lines: Number of context lines to include
            
        Returns:
            Unified diff string
        """
        self._logger.debug(f"Generating diff between {original_file} and {modified_file}")
        
        # Read file contents
        try:
            with open(original_file, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
            
            with open(modified_file, 'r', encoding='utf-8', errors='replace') as f:
                modified_content = f.read()
            
            # Generate diff
            return self.generate_diff(
                original_content, 
                modified_content,
                context_lines
            )
        except Exception as e:
            self._logger.error(f"Error generating file diff: {str(e)}")
            return f"Error generating diff: {str(e)}"
    
    def generate_directory_diff(
        self, 
        original_dir: Union[str, Path], 
        modified_dir: Union[str, Path],
        context_lines: int = 3
    ) -> Dict[str, str]:
        """
        Generate diffs for all files in two directories.
        
        Args:
            original_dir: Path to original directory
            modified_dir: Path to modified directory
            context_lines: Number of context lines to include
            
        Returns:
            Dictionary mapping file paths to diffs
        """
        self._logger.debug(f"Generating diffs between {original_dir} and {modified_dir}")
        
        original_dir = Path(original_dir)
        modified_dir = Path(modified_dir)
        
        # Check if directories exist
        if not original_dir.exists() or not original_dir.is_dir():
            self._logger.error(f"Original directory does not exist: {original_dir}")
            return {}
        
        if not modified_dir.exists() or not modified_dir.is_dir():
            self._logger.error(f"Modified directory does not exist: {modified_dir}")
            return {}
        
        # Find all files in both directories
        original_files = set()
        modified_files = set()
        
        for root, _, files in os.walk(original_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(original_dir)
                original_files.add(str(rel_path))
        
        for root, _, files in os.walk(modified_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(modified_dir)
                modified_files.add(str(rel_path))
        
        # Generate diffs for all files
        diffs = {}
        
        # Files in both directories
        for rel_path in original_files.intersection(modified_files):
            original_file = original_dir / rel_path
            modified_file = modified_dir / rel_path
            
            try:
                diff = self.generate_file_diff(
                    original_file, 
                    modified_file,
                    context_lines
                )
                
                # Only include if there are differences
                if diff:
                    diffs[rel_path] = diff
            except Exception as e:
                self._logger.error(f"Error generating diff for {rel_path}: {str(e)}")
        
        # Files only in original directory (deleted)
        for rel_path in original_files - modified_files:
            original_file = original_dir / rel_path
            
            try:
                with open(original_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Generate diff showing deletion
                diff = self.generate_diff(content, '')
                diffs[rel_path] = diff
            except Exception as e:
                self._logger.error(f"Error generating diff for {rel_path}: {str(e)}")
        
        # Files only in modified directory (added)
        for rel_path in modified_files - original_files:
            modified_file = modified_dir / rel_path
            
            try:
                with open(modified_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Generate diff showing addition
                diff = self.generate_diff('', content)
                diffs[rel_path] = diff
            except Exception as e:
                self._logger.error(f"Error generating diff for {rel_path}: {str(e)}")
        
        return diffs
    
    def apply_diff(
        self, 
        original: str, 
        diff: str
    ) -> Tuple[str, bool]:
        """
        Apply a unified diff to original content.
        
        Args:
            original: Original content
            diff: Unified diff string
            
        Returns:
            Tuple of (modified_content, success)
        """
        self._logger.debug("Applying diff")
        
        try:
            # Parse the diff
            lines = diff.splitlines()
            
            # Skip header lines (starting with ---, +++, @@)
            i = 0
            while i < len(lines) and (lines[i].startswith('---') or lines[i].startswith('+++') or lines[i].startswith('@@')):
                i += 1
            
            # Apply changes
            result = []
            original_lines = original.splitlines()
            
            line_num = 0
            while line_num < len(original_lines):
                if i < len(lines):
                    if lines[i].startswith('-'):
                        # Line removed, skip in original
                        if not original_lines[line_num] == lines[i][1:]:
                            # Mismatch, can't apply diff
                            return original, False
                        
                        line_num += 1
                        i += 1
                    elif lines[i].startswith('+'):
                        # Line added
                        result.append(lines[i][1:])
                        i += 1
                    elif lines[i].startswith(' '):
                        # Context line
                        if not original_lines[line_num] == lines[i][1:]:
                            # Mismatch, can't apply diff
                            return original, False
                        
                        result.append(original_lines[line_num])
                        line_num += 1
                        i += 1
                    else:
                        # Unknown line in diff
                        return original, False
                else:
                    # No more diff lines, copy remaining original lines
                    result.extend(original_lines[line_num:])
                    break
            
            # Return the modified content
            return '\n'.join(result), True
        except Exception as e:
            self._logger.error(f"Error applying diff: {str(e)}")
            return original, False

# Global diff manager instance
diff_manager = DiffManager()
