# angela/context/file_resolver.py
"""
File reference resolution for Angela CLI.

This module provides functionality to resolve file references from natural
language queries, using a combination of techniques such as exact matching,
fuzzy matching, pattern matching, and context-aware resolution.
"""
import os
import re
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Set

from angela.context import context_manager
from angela.context.session import session_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class FileResolver:
    """
    Resolver for file references in natural language queries.
    
    Provides multiple strategies for resolving file references:
    1. Exact path matching
    2. Fuzzy name matching
    3. Pattern matching
    4. Context-aware resolution (recent files, project files)
    5. Special references (current file, last modified file)
    """
    
    def __init__(self):
        """Initialize the file resolver."""
        self._logger = logger
        self._threshold = 0.6  # Threshold for fuzzy matching
    
    async def resolve_reference(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> Optional[Path]:
        """
        Resolve a file reference to an actual file path.
        
        Args:
            reference: The file reference to resolve
            context: Context information
            search_scope: Optional scope for the search (project, directory, recent)
            
        Returns:
            Path object if found, None otherwise
        """
        self._logger.info(f"Resolving file reference: '{reference}'")
        
        # Strip quotes if present
        reference = reference.strip('\'"')
        
        # If reference is empty or None, return None
        if not reference:
            return None
        
        # Try resolving with each strategy in order
        resolved = await self._resolve_exact_path(reference, context)
        if resolved:
            self._logger.debug(f"Resolved via exact path: {resolved}")
            self._record_resolution(reference, resolved, "exact_path")
            return resolved
        
        resolved = await self._resolve_special_reference(reference, context)
        if resolved:
            self._logger.debug(f"Resolved via special reference: {resolved}")
            self._record_resolution(reference, resolved, "special_reference")
            return resolved
        
        resolved = await self._resolve_recent_file(reference, context)
        if resolved:
            self._logger.debug(f"Resolved via recent file: {resolved}")
            self._record_resolution(reference, resolved, "recent_file")
            return resolved
        
        resolved = await self._resolve_fuzzy_match(reference, context, search_scope)
        if resolved:
            self._logger.debug(f"Resolved via fuzzy match: {resolved}")
            self._record_resolution(reference, resolved, "fuzzy_match")
            return resolved
        
        resolved = await self._resolve_pattern_match(reference, context, search_scope)
        if resolved:
            self._logger.debug(f"Resolved via pattern match: {resolved}")
            self._record_resolution(reference, resolved, "pattern_match")
            return resolved
        
        # If all strategies fail, log and return None
        self._logger.warning(f"Could not resolve file reference: '{reference}'")
        return None
    
    async def extract_references(
        self, 
        text: str,
        context: Dict[str, Any]
    ) -> List[Tuple[str, Optional[Path]]]:
        """
        Extract and resolve file references from text.
        
        Args:
            text: The text to extract references from
            context: Context information
            
        Returns:
            List of (reference, resolved_path) tuples
        """
        self._logger.info(f"Extracting file references from: '{text}'")
        
        # Define common words that should not be treated as file references
        common_words = set([
            "that", "this", "those", "these", "the", "it", "which", "what", 
            "inside", "called", "named", "from", "with", "using", "into", 
            "as", "for", "about", "like", "than", "then", "when", "where",
            "how", "why", "who", "whom", "whose", "my", "your", "our", "their"
        ])
        
        # Define minimum token length for potential file references
        MIN_TOKEN_LENGTH = 3
        
        # Define more specific and detailed patterns for finding file references
        patterns = [
            # Quoted paths with extensions - high confidence
            r'["\']([a-zA-Z0-9](?:[a-zA-Z0-9_\-\.]+)/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]{1,10})["\']',
            
            # Quoted files with extensions - high confidence
            r'["\']([a-zA-Z0-9][a-zA-Z0-9_\-\.]{1,50}\.[a-zA-Z0-9]{1,10})["\']',
            
            # Unquoted but clear file paths with extensions - medium confidence
            r'\b([a-zA-Z0-9](?:[a-zA-Z0-9_\-\.]+)/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]{1,10})\b',
            
            # Unquoted files with extensions and minimal length - medium confidence
            r'\b([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}\.[a-zA-Z0-9]{1,10})\b',
            
            # Very specific references with operation keywords - high confidence
            r'(?:edit|open|read|cat|view|show|display|modify|update|check)\s+(?:file|script|module|config)?\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # Specific file operations with clear file reference - high confidence
            r'(?:append\s+to|write\s+to|delete|remove)\s+(?:file|script)?\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # File references with clear context - medium confidence
            r'(?:in|from|to)\s+(?:file|directory|folder)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # References with operations that specifically mention "file" - medium-high confidence
            r'(?:the|this|that|my)\s+file\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
        ]
        
        # Special patterns for creation targets that we won't try to resolve as existing files
        creation_patterns = [
            # "save as X" pattern
            r'save\s+(?:it\s+)?(?:as|to)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # "create file X" pattern
            r'create\s+(?:a\s+)?(?:new\s+)?(?:file|script)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # "generate X" where X has a file extension
            r'generate\s+(?:a\s+)?(?:new\s+)?(?:file|script|code)?\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}\.[a-zA-Z0-9]{1,10})["\']?',
        ]
        
        references = []
        creation_targets = []  # Track references that are meant for file creation
        
        # First identify creation targets that we should NOT try to resolve
        for pattern in creation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                reference = match.group(1)
                
                # Skip references that are too short or common words
                if len(reference) < MIN_TOKEN_LENGTH or reference.lower() in common_words:
                    continue
                    
                # Skip if it's just a number
                if reference.isdigit():
                    continue
                    
                # Skip if we've already seen this reference
                if reference in creation_targets:
                    continue
                    
                # This is a creation target, not an existing file to resolve
                creation_targets.append(reference)
                self._logger.debug(f"Identified creation target: {reference}")
        
        # Now extract references that should be resolved as existing files
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                reference = match.group(1)
                
                # Skip references that are too short or common words
                if len(reference) < MIN_TOKEN_LENGTH or reference.lower() in common_words:
                    continue
                    
                # Skip if it's just a number
                if reference.isdigit():
                    continue
                    
                # Skip if this reference is a creation target or already in our list
                if reference in creation_targets or any(ref == reference for ref, _ in references):
                    continue
                
                # Try to resolve the reference
                resolved = await self.resolve_reference(reference, context)
                references.append((reference, resolved))
        
        self._logger.debug(f"Extracted {len(references)} file references and skipped {len(creation_targets)} creation targets")
        return references
    
    async def _resolve_exact_path(
        self, 
        reference: str, 
        context: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Resolve a reference as an exact path.
        
        Args:
            reference: The reference to resolve
            context: Context information
            
        Returns:
            Path object if found, None otherwise
        """
        # Try as absolute path
        path = Path(reference)
        if path.is_absolute() and path.exists():
            return path
        
        # Try relative to current directory
        cwd_path = Path(context["cwd"]) / reference
        if cwd_path.exists():
            return cwd_path
        
        # Try relative to project root if available
        if context.get("project_root"):
            proj_path = Path(context["project_root"]) / reference
            if proj_path.exists():
                return proj_path
        
        return None
    
    async def _resolve_special_reference(
        self, 
        reference: str, 
        context: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Resolve special references like "current file", "last modified", etc.
        
        Args:
            reference: The reference to resolve
            context: Context information
            
        Returns:
            Path object if found, None otherwise
        """
        # Handle various special references
        lowercase_ref = reference.lower()
        
        # Current file
        if lowercase_ref in ["current file", "this file", "current"]:
            if context.get("current_file") and "path" in context["current_file"]:
                return Path(context["current_file"]["path"])
        
        # Last modified file (via session)
        if lowercase_ref in ["last file", "last modified", "previous file"]:
            session = session_manager.get_context()
            entities = session.get("entities", {})
            
            # Look for the most recent file entity
            last_file = None
            last_time = None
            
            for name, entity in entities.items():
                if entity.get("type") in ["file", "recent_file"]:
                    entity_time = entity.get("created")
                    if entity_time and (not last_time or entity_time > last_time):
                        last_time = entity_time
                        last_file = entity.get("value")
            
            if last_file:
                return Path(last_file)
        
        return None
    
    async def _resolve_recent_file(
        self, 
        reference: str, 
        context: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Resolve a reference against recently used files.
        
        Args:
            reference: The reference to resolve
            context: Context information
            
        Returns:
            Path object if found, None otherwise
        """
        # Get recent files from session
        session = session_manager.get_context()
        entities = session.get("entities", {})
        
        # Filter for file entities
        file_entities = {
            name: entity for name, entity in entities.items()
            if entity.get("type") in ["file", "directory", "recent_file"]
        }
        
        # Look for exact matches first
        for name, entity in file_entities.items():
            path = Path(entity.get("value", ""))
            if path.name.lower() == reference.lower():
                return path
        
        # Then try fuzzy matches
        for name, entity in file_entities.items():
            path = Path(entity.get("value", ""))
            similarity = difflib.SequenceMatcher(None, path.name.lower(), reference.lower()).ratio()
            if similarity >= self._threshold:
                return path
        
        return None
    
    async def _resolve_fuzzy_match(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> Optional[Path]:
        """
        Resolve a reference using fuzzy matching.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            Path object if found, None otherwise
        """
        paths_to_check = []
        
        # Get paths based on search scope
        if search_scope == "project" and context.get("project_root"):
            # Get all files in the project
            project_path = Path(context["project_root"])
            paths_to_check.extend(project_path.glob("**/*"))
        elif search_scope == "directory":
            # Get all files in the current directory
            cwd_path = Path(context["cwd"])
            paths_to_check.extend(cwd_path.glob("*"))
        else:
            # Default: check both current directory and project root
            cwd_path = Path(context["cwd"])
            paths_to_check.extend(cwd_path.glob("*"))
            
            if context.get("project_root"):
                project_path = Path(context["project_root"])
                
                # Only search project root if different from current directory
                if project_path != cwd_path:
                    # Get direct children of project root
                    paths_to_check.extend(project_path.glob("*"))
                    
                    # Add common directories like src, lib, test
                    common_dirs = ["src", "lib", "test", "tests", "docs", "app", "bin"]
                    for dirname in common_dirs:
                        dir_path = project_path / dirname
                        if dir_path.exists() and dir_path.is_dir():
                            paths_to_check.extend(dir_path.glob("*"))
        
        # Deduplicate paths
        paths_to_check = list(set(paths_to_check))
        
        # Sort paths by the similarity of their name to the reference
        matches = []
        for path in paths_to_check:
            similarity = difflib.SequenceMatcher(None, path.name.lower(), reference.lower()).ratio()
            if similarity >= self._threshold:
                matches.append((path, similarity))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best match if any
        if matches:
            return matches[0][0]
        
        return None
    
    async def _resolve_pattern_match(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> Optional[Path]:
        """
        Resolve a reference using pattern matching.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            Path object if found, None otherwise
        """
        # Try to interpret the reference as a glob pattern
        base_paths = []
        
        # Determine base paths based on search scope
        if search_scope == "project" and context.get("project_root"):
            base_paths.append(Path(context["project_root"]))
        elif search_scope == "directory":
            base_paths.append(Path(context["cwd"]))
        else:
            # Default: check both current directory and project root
            base_paths.append(Path(context["cwd"]))
            if context.get("project_root"):
                project_path = Path(context["project_root"])
                if project_path != Path(context["cwd"]):
                    base_paths.append(project_path)
        
        # Try each base path
        for base_path in base_paths:
            # Try with wildcard prefix/suffix if needed
            patterns_to_try = [
                reference,  # As-is
                f"*{reference}*",  # Wildcard prefix and suffix
                f"*{reference}",  # Wildcard prefix
                f"{reference}*"  # Wildcard suffix
            ]
            
            for pattern in patterns_to_try:
                try:
                    # Use glob to find matching files
                    matches = list(base_path.glob(pattern))
                    if matches:
                        return matches[0]  # Return the first match
                except Exception:
                    # Invalid pattern, try the next one
                    continue
        
        return None
    
    def _record_resolution(
        self, 
        reference: str, 
        resolved_path: Path, 
        method: str
    ) -> None:
        """
        Record a successful resolution for learning.
        
        Args:
            reference: The original reference
            resolved_path: The resolved path
            method: The method used for resolution
        """
        # Store in session for future reference
        try:
            session_manager.add_entity(
                name=f"file_ref:{reference}",
                entity_type="file_reference",
                value=str(resolved_path)
            )
            
            # Also store as a recent file
            session_manager.add_entity(
                name=f"recent_file:{resolved_path.name}",
                entity_type="recent_file",
                value=str(resolved_path)
            )
        except Exception as e:
            self._logger.error(f"Error recording resolution: {str(e)}")

# Global file resolver instance
file_resolver = FileResolver()
