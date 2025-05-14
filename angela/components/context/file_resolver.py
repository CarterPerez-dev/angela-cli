# angela/context/file_resolver.py

import os
import re
import time
import difflib
import fnmatch
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Set, NamedTuple, Iterator, Callable

from angela.api.context import get_context_manager, get_session_manager, get_file_activity_tracker
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class ResolutionStrategy(Enum):
    """Strategies used to resolve file references."""
    EXACT_PATH = "exact_path"
    SPECIAL_REFERENCE = "special_reference" 
    RECENT_FILE = "recent_file"
    FUZZY_MATCH = "fuzzy_match"
    PATTERN_MATCH = "pattern_match"
    PROJECT_STRUCTURE = "project_structure"
    FILE_TYPE = "file_type"
    SEMANTIC_CONTEXT = "semantic_context"
    
    def __str__(self):
        return self.value

@dataclass
class Match:
    """A potential match for a file reference."""
    path: Path
    score: float
    strategy: ResolutionStrategy
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class FileType(Enum):
    """Common file types for more intelligent matching."""
    PYTHON = ["py", "pyi", "pyx", "ipynb"]
    JAVASCRIPT = ["js", "jsx", "ts", "tsx", "mjs", "cjs"]
    HTML = ["html", "htm", "xhtml"]
    CSS = ["css", "scss", "sass", "less"]
    CONFIG = ["json", "yaml", "yml", "toml", "ini", "cfg", "conf"]
    MARKDOWN = ["md", "markdown", "mdx"]
    TEXT = ["txt", "text", "log"]
    SHELL = ["sh", "bash", "zsh", "fish"]
    COMPILED = ["pyc", "class", "o", "obj", "dll", "so", "dylib"]
    
    @classmethod
    def from_extension(cls, ext: str) -> Optional['FileType']:
        """Get a file type from an extension."""
        ext = ext.lstrip('.').lower()
        for file_type in cls:
            if ext in file_type.value:
                return file_type
        return None
    
    @classmethod
    def get_extensions(cls, file_type_name: str) -> List[str]:
        """Get extensions for a file type name."""
        try:
            return cls[file_type_name.upper()].value
        except KeyError:
            return []

class FileResolver:
    """
    Advanced resolver for file references in natural language queries.
    
    Provides multiple intelligent strategies for resolving file references:
    1. Exact path matching
    2. Fuzzy name matching with enhanced scoring
    3. Pattern matching with multiple variants
    4. Context-aware resolution (recent files, project files)
    5. Special references (current file, last modified file)
    6. Project structure awareness
    7. File type awareness
    8. Semantic context analysis
    """
    
    def __init__(self):
        """Initialize the file resolver with enhanced capabilities."""
        self._logger = logger
        self._fuzzy_threshold = 0.6  # Base threshold for fuzzy matching
        self._max_candidates = 10  # Maximum number of candidates to consider
        self._context_weight = 1.5  # Weight multiplier for context matches
        self._recency_weight = 1.2  # Weight multiplier for recently used files
        self._cache = {}  # Cache for resolved references
        self._cache_ttl = 300  # Cache TTL in seconds
        self._cache_last_cleanup = time.time()
        
        # Specific to project types
        self._known_project_structures = {
            "python": {
                "src_dirs": ["src", "app", "lib"],
                "test_dirs": ["tests", "test"],
                "config_files": ["setup.py", "pyproject.toml", "requirements.txt"],
                "doc_dirs": ["docs", "doc"],
            },
            "node": {
                "src_dirs": ["src", "app", "lib"],
                "test_dirs": ["tests", "test", "__tests__"],
                "config_files": ["package.json", "tsconfig.json", ".eslintrc"],
                "doc_dirs": ["docs", "doc"],
            },
            "web": {
                "src_dirs": ["src", "app", "public", "static"],
                "style_dirs": ["css", "styles", "scss"],
                "script_dirs": ["js", "scripts"],
                "asset_dirs": ["assets", "images", "img"],
            }
        }
        
        # Common exclusion patterns
        self._exclusion_patterns = [
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/dist/**",
            "**/build/**",
            "**/.cache/**",
            "**/.pytest_cache/**",
        ]
    
    async def resolve_reference(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> Optional[Path]:
        """
        Resolve a file reference to an actual file path using multiple intelligent strategies.
        
        Args:
            reference: The file reference to resolve
            context: Context information
            search_scope: Optional scope for the search (project, directory, recent)
            
        Returns:
            Path object if found, None otherwise
        """
        self._logger.info(f"Resolving file reference: '{reference}'")
        
        # Clean up the reference
        reference = self._clean_reference(reference)
        
        # Skip empty references
        if not reference:
            return None
        
        # Check cache first
        cache_key = f"{reference}:{context.get('cwd')}:{search_scope}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self._logger.debug(f"Using cached resolution for '{reference}': {cached_result}")
            return cached_result
        
        # Cleanup cache if needed
        self._maybe_cleanup_cache()
        
        # Try resolving with each strategy and collect matches
        all_matches = await self._collect_all_matches(reference, context, search_scope)
        
        # Rank and process matches
        best_match = self._pick_best_match(reference, all_matches, context)
        if best_match:
            self._logger.debug(f"Best match for '{reference}': {best_match.path} (score: {best_match.score:.2f}, strategy: {best_match.strategy})")
            final_path = best_match.path
            
            # Record successful resolution
            await self._record_resolution(reference, final_path, str(best_match.strategy))
            
            # Cache the result
            self._add_to_cache(cache_key, final_path)
            
            return final_path
        
        # If all strategies fail, log and return None
        self._logger.warning(f"Could not resolve file reference: '{reference}'")
        return None
    
    async def resolve_file_references(
        self,
        cwd: str,
        project_root: Optional[str],
        references: List[str]
    ) -> Dict[str, str]:
        """
        Resolve multiple file references for API usage.
        
        Args:
            cwd: Current working directory
            project_root: Optional project root
            references: List of references to resolve
            
        Returns:
            Dictionary mapping references to resolved paths (as strings)
        """
        self._logger.info(f"Resolving multiple file references: {references}")
        
        # Prepare basic context
        context = {
            "cwd": cwd
        }
        if project_root:
            context["project_root"] = project_root
        
        # Get current file from context
        context_manager = get_context_manager()
        if context_manager.current_file:
            context["current_file"] = context_manager.current_file
        
        # Resolve each reference
        result = {}
        for ref in references:
            resolved = await self.resolve_reference(ref, context)
            if resolved:
                result[ref] = str(resolved)
        
        return result
    
    async def extract_references(
        self, 
        text: str,
        context: Dict[str, Any]
    ) -> List[Tuple[str, Optional[Path]]]:
        """
        Extract and resolve file references from text with enhanced pattern recognition.
        
        Args:
            text: The text to extract references from
            context: Context information
            
        Returns:
            List of (reference, resolved_path) tuples
        """
        self._logger.info(f"Extracting file references from text ({len(text)} chars)")
        
        # Define common words that should not be treated as file references
        common_words = self._get_common_words()
        
        # Define minimum token length for potential file references
        MIN_TOKEN_LENGTH = 3
        
        # Define more specific and detailed patterns for finding file references
        extraction_patterns = self._get_extraction_patterns()
        
        # Special patterns for creation targets that we won't try to resolve as existing files
        creation_patterns = self._get_creation_patterns()
        
        references = []
        creation_targets = []  # Track references that are meant for file creation
        
        # First identify creation targets that we should NOT try to resolve
        for pattern in creation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                reference = match.group(1)
                
                # Apply filtering rules
                if not self._is_valid_reference(reference, common_words, MIN_TOKEN_LENGTH):
                    continue
                    
                # Skip if we've already seen this reference
                if reference in creation_targets:
                    continue
                    
                # This is a creation target, not an existing file to resolve
                creation_targets.append(reference)
                self._logger.debug(f"Identified creation target: {reference}")
        
        # Now extract references that should be resolved as existing files
        for pattern in extraction_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                reference = match.group(1)
                
                # Apply filtering rules
                if not self._is_valid_reference(reference, common_words, MIN_TOKEN_LENGTH):
                    continue
                    
                # Skip if this reference is a creation target or already in our list
                if reference in creation_targets or any(ref == reference for ref, _ in references):
                    continue
                
                # Try to resolve the reference
                resolved = await self.resolve_reference(reference, context)
                references.append((reference, resolved))
                
                # If we found a resolution, look for related files
                if resolved:
                    related_refs = self._find_related_references(reference, text)
                    for related_ref in related_refs:
                        if related_ref not in creation_targets and not any(ref == related_ref for ref, _ in references):
                            related_resolved = await self.resolve_reference(related_ref, context)
                            if related_resolved:
                                references.append((related_ref, related_resolved))
        
        self._logger.debug(f"Extracted {len(references)} file references")
        self._logger.debug(f"Skipped {len(creation_targets)} creation targets")
        
        return references
    
    async def get_most_relevant_files(
        self, 
        context: Dict[str, Any],
        query: Optional[str] = None,
        limit: int = 5
    ) -> List[Path]:
        """
        Get the most relevant files for the current context.
        
        Args:
            context: Context information
            query: Optional query to filter files 
            limit: Maximum number of files to return
            
        Returns:
            List of relevant file paths
        """
        self._logger.info(f"Finding most relevant files for context {query if query else 'without query'}")
        
        # Start with recently active files
        relevant_files = set()
        try:
            file_activity_tracker = get_file_activity_tracker()
            active_files = file_activity_tracker.get_most_active_files(limit=limit*2)
            
            for file_info in active_files:
                if 'path' in file_info:
                    path = Path(file_info['path'])
                    if path.exists() and path.is_file():
                        relevant_files.add(path)
        except Exception as e:
            self._logger.warning(f"Error getting active files: {str(e)}")
        
        # Add files from session
        try:
            session_manager = get_session_manager()
            session = session_manager.get_context()
            entities = session.get("entities", {})
            
            for name, entity in entities.items():
                if entity.get("type") in ["file", "recent_file"]:
                    path = Path(entity.get("value", ""))
                    if path.exists() and path.is_file():
                        relevant_files.add(path)
        except Exception as e:
            self._logger.warning(f"Error getting session files: {str(e)}")
        
        # If we have a query, score and filter the files
        if query:
            scored_files = []
            for path in relevant_files:
                # Score based on name similarity
                name_similarity = difflib.SequenceMatcher(None, path.name.lower(), query.lower()).ratio()
                
                # Adjust score based on file type if present in query
                score = name_similarity
                for file_type in FileType:
                    if any(ext in query.lower() for ext in file_type.value):
                        path_ext = path.suffix.lstrip('.')
                        if path_ext in file_type.value:
                            score *= 1.5
                
                scored_files.append((path, score))
            
            # Sort by score and take the top results
            scored_files.sort(key=lambda x: x[1], reverse=True)
            return [path for path, _ in scored_files[:limit]]
        
        # Without a query, just limit the results
        return list(relevant_files)[:limit]
    
    def _is_valid_reference(self, reference: str, common_words: Set[str], min_length: int) -> bool:
        """
        Check if a reference is valid for extraction.
        
        Args:
            reference: The reference to check
            common_words: Set of common words to ignore
            min_length: Minimum token length
            
        Returns:
            True if the reference is valid, False otherwise
        """
        # Skip references that are too short
        if len(reference) < min_length:
            return False
            
        # Skip common words
        if reference.lower() in common_words:
            return False
            
        # Skip if it's just a number
        if reference.isdigit():
            return False
            
        # Ensure we don't have URLs or weird things
        if reference.startswith(('http:', 'https:', 'ftp:', 'mailto:')):
            return False
        
        return True
    
    def _clean_reference(self, reference: str) -> str:
        """
        Clean and normalize a reference.
        
        Args:
            reference: The reference to clean
            
        Returns:
            Cleaned reference
        """
        # Strip quotes and whitespace
        reference = reference.strip('\'"\\/* \t\n\r')
        
        # Handle path separators
        reference = reference.replace('\\', '/')
        
        return reference
    
    def _get_common_words(self) -> Set[str]:
        """
        Get a set of common words that should not be treated as file references.
        
        Returns:
            Set of common words
        """
        return set([
            "that", "this", "those", "these", "the", "it", "which", "what", 
            "inside", "called", "named", "from", "with", "using", "into", 
            "as", "for", "about", "like", "than", "then", "when", "where",
            "how", "why", "who", "whom", "whose", "my", "your", "our", "their",
            "create", "make", "build", "run", "execute", "script", "program", 
            "command", "code", "function", "class", "module", "file", "directory",
            "folder", "project", "value", "test", "example", "code", "content",
            "please", "help", "need", "want", "trying", "would", "could", "should"
        ])
    
    def _get_extraction_patterns(self) -> List[str]:
        """
        Get regex patterns for extracting file references.
        
        Returns:
            List of regex patterns
        """
        return [
            # Quoted paths with extensions - high confidence
            r'["\']([a-zA-Z0-9](?:[a-zA-Z0-9_\-\.]+)/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]{1,10})["\']',
            
            # Quoted files with extensions - high confidence
            r'["\']([a-zA-Z0-9][a-zA-Z0-9_\-\.]{1,50}\.[a-zA-Z0-9]{1,10})["\']',
            
            # Unquoted but clear file paths with extensions - medium confidence
            r'\b([a-zA-Z0-9](?:[a-zA-Z0-9_\-\.]+)/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]{1,10})\b',
            
            # Unquoted files with extensions and minimal length - medium confidence
            r'\b([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}\.[a-zA-Z0-9]{1,10})\b',
            
            # Very specific references with operation keywords - high confidence
            r'(?:edit|open|read|cat|view|show|display|modify|update|check|access)\s+(?:file|script|module|config)?\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # Specific file operations with clear file reference - high confidence
            r'(?:append\s+to|write\s+to|delete|remove)\s+(?:file|script)?\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # File references with clear context - medium confidence
            r'(?:in|from|to)\s+(?:file|directory|folder)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # References with operations that specifically mention "file" - medium-high confidence
            r'(?:the|this|that|my)\s+file\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # References to project files - medium confidence
            r'(?:project|repo|repository|codebase)\s+file\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # References to file type mentions - lower confidence but useful
            r'\b((?:python|java|js|javascript|html|css|config|yaml|json|markdown|shell|bash)\s+file\s+[a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,})',
            
            # File paths with directory structure mentioned - high confidence
            r'(?:under|in|within|from)\s+(?:the\s+)?([a-zA-Z0-9][a-zA-Z0-9_\-\.]+/[a-zA-Z0-9][a-zA-Z0-9_\-\.]+(?:/[a-zA-Z0-9][a-zA-Z0-9_\-\.]+)*)',
            
            # Common directory structure in technical projects - medium confidence
            r'(?:src|lib|app|test|tests|scripts|config|docs)/([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)',
            
            # File with description and location - medium-high confidence
            r'([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}\.[a-zA-Z0-9]{1,10})\s+(?:located|found|residing|present)\s+(?:in|under|within)',
            
            # Named imports/includes - high confidence for code references
            r'(?:import|include|require|from)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.\/]{2,})["\']?',
            
            # Extensions mentioned directly - medium confidence
            r'(?:a|the|this)\s+([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,})\.(?:py|js|html|css|md|json|yaml|yml|txt|xml|csv)'
        ]
    
    def _get_creation_patterns(self) -> List[str]:
        """
        Get regex patterns for identifying file creation references.
        
        Returns:
            List of regex patterns
        """
        return [
            # "save as X" pattern
            r'save\s+(?:it\s+)?(?:as|to)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # "create file X" pattern
            r'create\s+(?:a\s+)?(?:new\s+)?(?:file|script)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # "generate X" where X has a file extension
            r'generate\s+(?:a\s+)?(?:new\s+)?(?:file|script|code)?\s*["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}\.[a-zA-Z0-9]{1,10})["\']?',
            
            # "write X" where X refers to a new file
            r'write\s+(?:a\s+)?(?:new\s+)?(?:file|script)\s+(?:called|named)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # "output to X" patterns
            r'output\s+(?:to|into)\s+(?:a\s+)?(?:file\s+(?:called|named)\s+)?["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?',
            
            # "new X file" patterns
            r'(?:new|create)\s+([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,})\s+file',
            
            # "make X" patterns explicitly mentioning creation
            r'make\s+(?:a\s+)?(?:new\s+)(?:file|script)\s+["\']?([a-zA-Z0-9][a-zA-Z0-9_\-\.]{2,}(?:\.[a-zA-Z0-9]{1,10})?)["\']?'
        ]
    
    def _find_related_references(self, reference: str, text: str) -> List[str]:
        """
        Find references that might be related to an already identified reference.
        
        Args:
            reference: The original reference
            text: The text to analyze
            
        Returns:
            List of related references
        """
        # Get base name and extension
        path = Path(reference)
        base_name = path.stem
        extension = path.suffix
        
        related = []
        
        # Look for variants with same base name but different extensions
        if extension:
            for ext in ['.py', '.js', '.html', '.css', '.json', '.yaml', '.yml', '.md', '.txt']:
                if ext != extension:
                    variant = f"{base_name}{ext}"
                    if variant in text:
                        related.append(variant)
        
        # Look for related test files
        if not base_name.startswith('test_') and 'test' not in base_name:
            test_variants = [f"test_{base_name}{extension}", f"{base_name}_test{extension}"]
            for variant in test_variants:
                if variant in text:
                    related.append(variant)
        
        # Look for related implementation files
        if base_name.startswith('test_'):
            impl_name = base_name[5:]  # Remove 'test_'
            if impl_name:
                impl_variant = f"{impl_name}{extension}"
                if impl_variant in text:
                    related.append(impl_variant)
        
        return related
    
    async def _collect_all_matches(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Collect matches from all resolution strategies.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of potential matches
        """
        all_matches = []
        
        # Try each strategy
        strategies = [
            (self._resolve_exact_path, ResolutionStrategy.EXACT_PATH),
            (self._resolve_special_reference, ResolutionStrategy.SPECIAL_REFERENCE),
            (self._resolve_recent_file, ResolutionStrategy.RECENT_FILE),
            (self._resolve_fuzzy_match, ResolutionStrategy.FUZZY_MATCH),
            (self._resolve_pattern_match, ResolutionStrategy.PATTERN_MATCH),
            (self._resolve_by_project_structure, ResolutionStrategy.PROJECT_STRUCTURE),
            (self._resolve_by_file_type, ResolutionStrategy.FILE_TYPE),
            (self._resolve_by_semantic_context, ResolutionStrategy.SEMANTIC_CONTEXT),
        ]
        
        for resolver_func, strategy in strategies:
            try:
                # Call the resolver function
                matches = await resolver_func(reference, context, search_scope)
                
                # Add strategy information to matches
                for match in matches:
                    match.strategy = strategy
                    all_matches.append(match)
                
                self._logger.debug(f"Strategy {strategy}: found {len(matches)} matches")
                
                # If we have exact path matches, they take precedence
                if strategy == ResolutionStrategy.EXACT_PATH and matches:
                    return matches
            except Exception as e:
                self._logger.error(f"Error in {strategy} resolver: {str(e)}")
        
        return all_matches
    
    def _pick_best_match(
        self, 
        reference: str, 
        matches: List[Match],
        context: Dict[str, Any]
    ) -> Optional[Match]:
        """
        Pick the best match from multiple candidates.
        
        Args:
            reference: The original reference
            matches: List of potential matches
            context: Context information
            
        Returns:
            The best match, or None if no good matches
        """
        if not matches:
            return None
        
        # If we have only one match, return it
        if len(matches) == 1:
            return matches[0]
        
        # Prioritize exact path matches
        exact_matches = [m for m in matches if m.strategy == ResolutionStrategy.EXACT_PATH]
        if exact_matches:
            return max(exact_matches, key=lambda m: m.score)
        
        # Sort by score and return the best match
        return max(matches, key=lambda m: m.score)
    
    async def _resolve_exact_path(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference as an exact path.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # Try as absolute path
        path = Path(reference)
        if path.is_absolute() and path.exists():
            matches.append(Match(path=path, score=1.0, strategy=ResolutionStrategy.EXACT_PATH))
        
        # Try relative to current directory
        cwd_path = Path(context["cwd"]) / reference
        if cwd_path.exists():
            matches.append(Match(path=cwd_path, score=1.0, strategy=ResolutionStrategy.EXACT_PATH))
        
        # Try relative to project root if available
        if context.get("project_root"):
            proj_path = Path(context["project_root"]) / reference
            if proj_path.exists():
                matches.append(Match(path=proj_path, score=1.0, strategy=ResolutionStrategy.EXACT_PATH))
        
        return matches
    
    async def _resolve_special_reference(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve special references like "current file", "last modified", etc.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        lowercase_ref = reference.lower()
        
        # Current file
        if lowercase_ref in ["current file", "this file", "current", "."]:
            if context.get("current_file") and "path" in context["current_file"]:
                path = Path(context["current_file"]["path"])
                matches.append(Match(
                    path=path, 
                    score=1.0, 
                    strategy=ResolutionStrategy.SPECIAL_REFERENCE,
                    metadata={"special": "current_file"}
                ))
        
        # Last modified file
        if lowercase_ref in ["last file", "last modified", "previous file", "recent file"]:
            # Try to get from file activity tracker
            try:
                file_activity_tracker = get_file_activity_tracker()
                from angela.api.context import get_activity_type
                ActivityType = get_activity_type()
                
                modified_activities = file_activity_tracker.get_recent_activities(
                    limit=1, 
                    activity_types=[ActivityType.MODIFIED]
                )
                
                if modified_activities and 'path' in modified_activities[0]:
                    path = Path(modified_activities[0]['path'])
                    if path.exists():
                        matches.append(Match(
                            path=path, 
                            score=1.0, 
                            strategy=ResolutionStrategy.SPECIAL_REFERENCE,
                            metadata={"special": "last_modified"}
                        ))
            except Exception as e:
                self._logger.warning(f"Error getting last modified file: {str(e)}")
            
            # Fallback to session
            if not matches:
                session_manager = get_session_manager()
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
                    path = Path(last_file)
                    matches.append(Match(
                        path=path, 
                        score=0.9, 
                        strategy=ResolutionStrategy.SPECIAL_REFERENCE,
                        metadata={"special": "last_file_from_session"}
                    ))
        
        # Previous directory
        if lowercase_ref in ["previous directory", "parent directory", ".."]:
            path = Path(context["cwd"]).parent
            if path.exists():
                matches.append(Match(
                    path=path, 
                    score=1.0, 
                    strategy=ResolutionStrategy.SPECIAL_REFERENCE,
                    metadata={"special": "parent_directory"}
                ))
        
        # Home directory
        if lowercase_ref in ["home directory", "home", "~"]:
            path = Path.home()
            matches.append(Match(
                path=path, 
                score=1.0, 
                strategy=ResolutionStrategy.SPECIAL_REFERENCE,
                metadata={"special": "home_directory"}
            ))
        
        return matches
    
    async def _resolve_recent_file(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference against recently used files.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # Get file activity tracker
        try:
            file_activity_tracker = get_file_activity_tracker()
            active_files = file_activity_tracker.get_most_active_files(limit=10)
            
            for file_info in active_files:
                if 'path' in file_info:
                    path = Path(file_info['path'])
                    
                    # Check if it matches the reference
                    if path.name.lower() == reference.lower():
                        matches.append(Match(
                            path=path, 
                            score=1.0, 
                            strategy=ResolutionStrategy.RECENT_FILE,
                            metadata={"activity": "exact_name_match", "count": file_info.get("count", 1)}
                        ))
                    else:
                        # Try fuzzy matching
                        similarity = difflib.SequenceMatcher(None, path.name.lower(), reference.lower()).ratio()
                        if similarity >= self._fuzzy_threshold:
                            matches.append(Match(
                                path=path, 
                                score=similarity * 0.9, # Slightly lower than exact match
                                strategy=ResolutionStrategy.RECENT_FILE,
                                metadata={"activity": "fuzzy_match", "count": file_info.get("count", 1)}
                            ))
        except Exception as e:
            self._logger.warning(f"Error resolving from recent files: {str(e)}")
        
        # Get from session for additional recent files
        try:
            session_manager = get_session_manager()
            session = session_manager.get_context()
            entities = session.get("entities", {})
            
            # Filter for file entities
            file_entities = {
                name: entity for name, entity in entities.items()
                if entity.get("type") in ["file", "directory", "recent_file"]
            }
            
            for name, entity in file_entities.items():
                path_str = entity.get("value", "")
                if not path_str:
                    continue
                    
                path = Path(path_str)
                
                # Skip if already in matches
                if any(m.path == path for m in matches):
                    continue
                
                # Check for exact match
                if path.name.lower() == reference.lower():
                    matches.append(Match(
                        path=path, 
                        score=0.95,  # Slightly lower than from activity tracker
                        strategy=ResolutionStrategy.RECENT_FILE,
                        metadata={"session": "exact_name_match"}
                    ))
                else:
                    # Try fuzzy matching
                    similarity = difflib.SequenceMatcher(None, path.name.lower(), reference.lower()).ratio()
                    if similarity >= self._fuzzy_threshold:
                        matches.append(Match(
                            path=path, 
                            score=similarity * 0.85,  # Lower than activity tracker
                            strategy=ResolutionStrategy.RECENT_FILE,
                            metadata={"session": "fuzzy_match"}
                        ))
        except Exception as e:
            self._logger.warning(f"Error resolving from session: {str(e)}")
        
        return matches
    
    async def _resolve_fuzzy_match(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference using enhanced fuzzy matching.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # Get paths to check based on search scope
        paths_to_check = await self._get_paths_to_check(context, search_scope)
        
        # Skip if no paths to check
        if not paths_to_check:
            return matches
        
        # Check if we're looking for a specific extension
        reference_path = Path(reference)
        specific_extension = reference_path.suffix if reference_path.suffix else None
        
        # Calculate match scores with enhanced scoring
        for path in paths_to_check:
            # Skip directories unless explicitly looking for one
            if path.is_dir() and not reference.endswith('/'):
                continue
                
            # Skip files with wrong extension if we're looking for a specific one
            if specific_extension and path.is_file() and path.suffix != specific_extension:
                continue
            
            # Calculate base similarity score
            name_similarity = difflib.SequenceMatcher(None, path.name.lower(), reference.lower()).ratio()
            
            # Only consider if above threshold
            if name_similarity >= self._fuzzy_threshold * 0.8:  # Slightly lower threshold for initial consideration
                # Start with the name similarity
                score = name_similarity
                
                # Adjust score based on various factors
                score = self._adjust_fuzzy_score(score, path, reference, context)
                
                # Only add if final score is above threshold
                if score >= self._fuzzy_threshold:
                    matches.append(Match(
                        path=path,
                        score=score,
                        strategy=ResolutionStrategy.FUZZY_MATCH,
                        metadata={"name_similarity": name_similarity}
                    ))
        
        # Sort by score and limit candidates
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:self._max_candidates]
    
    def _adjust_fuzzy_score(
        self, 
        base_score: float, 
        path: Path, 
        reference: str, 
        context: Dict[str, Any]
    ) -> float:
        """
        Adjust fuzzy match score based on various factors.
        
        Args:
            base_score: The base similarity score
            path: The path being scored
            reference: The original reference
            context: Context information
            
        Returns:
            Adjusted score
        """
        score = base_score
        
        # Boost for correct extension if mentioned
        ref_ext = Path(reference).suffix
        if ref_ext and path.suffix == ref_ext:
            score *= 1.2
        
        # Boost for path in current directory
        if path.parent == Path(context["cwd"]):
            score *= 1.1
        
        # Boost for exact stem match (ignoring extension)
        if path.stem.lower() == Path(reference).stem.lower():
            score *= 1.25
        
        # Penalty for paths in excluded directories
        for pattern in self._exclusion_patterns:
            if fnmatch.fnmatch(str(path), pattern):
                score *= 0.5
                break
        
        # Boost for paths containing keywords from reference
        words = set(reference.lower().split('_'))
        path_words = set(path.stem.lower().split('_'))
        common_words = words.intersection(path_words)
        if common_words:
            score *= (1 + 0.1 * len(common_words))
        
        # Boost for recently modified files
        try:
            mtime = path.stat().st_mtime
            now = time.time()
            if now - mtime < 86400:  # Modified in the last day
                score *= 1.1
        except:
            pass
        
        return score
    
    async def _resolve_pattern_match(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference using improved pattern matching.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # Determine base paths based on search scope
        base_paths = await self._get_base_paths(context, search_scope)
        
        # Try each base path
        for base_path in base_paths:
            # Create different pattern variations
            patterns_to_try = self._generate_pattern_variations(reference)
            
            for pattern in patterns_to_try:
                try:
                    # Use glob to find matching files
                    found_matches = list(base_path.glob(pattern))
                    
                    # Score and add matches
                    for path in found_matches:
                        # Calculate score based on pattern specificity
                        score = self._calculate_pattern_match_score(pattern, path, reference)
                        
                        # Add to matches if score is high enough
                        if score >= self._fuzzy_threshold:
                            matches.append(Match(
                                path=path,
                                score=score,
                                strategy=ResolutionStrategy.PATTERN_MATCH,
                                metadata={"pattern": pattern}
                            ))
                except Exception as e:
                    # Invalid pattern, log and continue
                    self._logger.debug(f"Invalid pattern {pattern}: {str(e)}")
                    continue
        
        # Deduplicate, sort by score, and limit
        unique_matches = {}
        for match in matches:
            if match.path not in unique_matches or match.score > unique_matches[match.path].score:
                unique_matches[match.path] = match
        
        result = list(unique_matches.values())
        result.sort(key=lambda m: m.score, reverse=True)
        return result[:self._max_candidates]
    
    def _generate_pattern_variations(self, reference: str) -> List[str]:
        """
        Generate different pattern variations for a reference.
        
        Args:
            reference: The reference to create patterns for
            
        Returns:
            List of patterns to try
        """
        patterns = [
            reference,  # As-is
            f"*{reference}*",  # Wildcard prefix and suffix
            f"*{reference}",  # Wildcard prefix
            f"{reference}*",  # Wildcard suffix
            f"**/{reference}",  # Anywhere in project
            f"**/{reference}*",  # Starts with reference anywhere
            f"**/*{reference}*",  # Contains reference anywhere
        ]
        
        # Add with different cases if applicable
        if not reference.islower() and not reference.isupper():
            patterns.append(reference.lower())
            patterns.append(reference.upper())
        
        # Add patterns for file extension variations
        ref_path = Path(reference)
        if not ref_path.suffix:
            # Try common extensions
            for ext in ['.py', '.js', '.html', '.css', '.md', '.json', '.yaml', '.yml']:
                patterns.append(f"{reference}{ext}")
        else:
            # If has extension, try without it too
            patterns.append(ref_path.stem)
        
        # Replace underscores with dashes and vice versa
        if '_' in reference:
            patterns.append(reference.replace('_', '-'))
        if '-' in reference:
            patterns.append(reference.replace('-', '_'))
        
        return patterns
    
    def _calculate_pattern_match_score(self, pattern: str, path: Path, reference: str) -> float:
        """
        Calculate a score for a pattern match.
        
        Args:
            pattern: The pattern that matched
            path: The matching path
            reference: The original reference
            
        Returns:
            Match score
        """
        # Base score depends on pattern specificity
        if pattern == reference:
            base_score = 1.0  # Exact match
        elif pattern.startswith('*') and pattern.endswith('*'):
            base_score = 0.7  # Wildcard prefix and suffix
        elif pattern.startswith('*') or pattern.endswith('*'):
            base_score = 0.8  # Wildcard prefix or suffix
        elif '**/' in pattern:
            base_score = 0.75  # Recursive search
        else:
            base_score = 0.9  # Other pattern
        
        # Adjust score based on path characteristics
        score = base_score
        
        # Boost for exact filename match
        if path.name.lower() == reference.lower():
            score *= 1.2
        
        # Boost for exact stem match
        if path.stem.lower() == Path(reference).stem.lower():
            score *= 1.15
        
        # Boost for correct extension if specified
        ref_ext = Path(reference).suffix
        if ref_ext and path.suffix == ref_ext:
            score *= 1.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def _resolve_by_project_structure(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference using project structure knowledge.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # Only proceed if we have a project root
        if not context.get("project_root"):
            return matches
        
        project_root = Path(context["project_root"])
        project_type = context.get("project_type", "unknown")
        
        # Use project structure knowledge if available
        if project_type in self._known_project_structures:
            structure = self._known_project_structures[project_type]
            
            # Check specific locations based on file type and project structure
            ref_path = Path(reference)
            extension = ref_path.suffix.lstrip('.')
            
            # Determine file category
            is_source = extension in ['py', 'js', 'jsx', 'ts', 'tsx']
            is_test = 'test' in reference.lower() or reference.startswith('test_')
            is_config = extension in ['json', 'yaml', 'yml', 'toml', 'ini']
            is_doc = extension in ['md', 'rst', 'txt']
            
            # Check in appropriate directories
            locations_to_check = []
            
            if is_source and not is_test:
                # Check source directories
                for src_dir in structure.get('src_dirs', []):
                    locations_to_check.append(project_root / src_dir)
            
            if is_test:
                # Check test directories
                for test_dir in structure.get('test_dirs', []):
                    locations_to_check.append(project_root / test_dir)
            
            if is_config:
                # Config files are often in root or specific config dirs
                locations_to_check.append(project_root)
                locations_to_check.append(project_root / 'config')
            
            if is_doc:
                # Doc files are often in doc dirs or root
                for doc_dir in structure.get('doc_dirs', []):
                    locations_to_check.append(project_root / doc_dir)
                locations_to_check.append(project_root)
            
            # Add project root as fallback
            locations_to_check.append(project_root)
            
            # Search in each location
            for location in locations_to_check:
                if not location.exists() or not location.is_dir():
                    continue
                    
                # Try exact match
                exact_path = location / reference
                if exact_path.exists():
                    matches.append(Match(
                        path=exact_path,
                        score=0.95,  # High but not perfect
                        strategy=ResolutionStrategy.PROJECT_STRUCTURE,
                        metadata={"location": str(location.relative_to(project_root))}
                    ))
                    continue  # Skip fuzzy matching if exact match found
                
                # Try fuzzy matching in this location
                for path in location.glob('*'):
                    if path.is_file():
                        similarity = difflib.SequenceMatcher(None, path.name.lower(), reference.lower()).ratio()
                        if similarity >= self._fuzzy_threshold:
                            # Calculate score based on similarity and location appropriateness
                            score = similarity * 0.9  # Base score
                            
                            # Boost score if location is appropriate for the file type
                            location_appropriate = False
                            rel_path = location.relative_to(project_root)
                            rel_path_str = str(rel_path)
                            
                            if is_source and any(src_dir == rel_path_str for src_dir in structure.get('src_dirs', [])):
                                location_appropriate = True
                            elif is_test and any(test_dir == rel_path_str for test_dir in structure.get('test_dirs', [])):
                                location_appropriate = True
                            elif is_doc and any(doc_dir == rel_path_str for doc_dir in structure.get('doc_dirs', [])):
                                location_appropriate = True
                            
                            if location_appropriate:
                                score *= 1.1
                            
                            matches.append(Match(
                                path=path,
                                score=score,
                                strategy=ResolutionStrategy.PROJECT_STRUCTURE,
                                metadata={
                                    "location": str(location.relative_to(project_root)),
                                    "similarity": similarity
                                }
                            ))
        
        return matches
    
    async def _resolve_by_file_type(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference using file type inference.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # Extract potential file type information from the reference
        detected_file_type = None
        file_type_patterns = [
            (r'python\s+file', FileType.PYTHON),
            (r'\.py\b', FileType.PYTHON),
            (r'javascript\s+file', FileType.JAVASCRIPT),
            (r'js\s+file', FileType.JAVASCRIPT),
            (r'\.js\b', FileType.JAVASCRIPT),
            (r'html\s+file', FileType.HTML),
            (r'\.html\b', FileType.HTML),
            (r'css\s+file', FileType.CSS),
            (r'\.css\b', FileType.CSS),
            (r'config\s+file', FileType.CONFIG),
            (r'configuration', FileType.CONFIG),
            (r'\.(json|yaml|yml|toml|ini)\b', FileType.CONFIG),
            (r'markdown\s+file', FileType.MARKDOWN),
            (r'\.md\b', FileType.MARKDOWN),
            (r'text\s+file', FileType.TEXT),
            (r'\.txt\b', FileType.TEXT),
            (r'shell\s+script', FileType.SHELL),
            (r'bash\s+script', FileType.SHELL),
            (r'\.(sh|bash)\b', FileType.SHELL),
        ]
        
        # Detect file type from reference
        reference_lower = reference.lower()
        for pattern, file_type in file_type_patterns:
            if re.search(pattern, reference_lower):
                detected_file_type = file_type
                break
        
        # If no file type detected, try to infer from reference
        if not detected_file_type:
            ref_path = Path(reference)
            extension = ref_path.suffix.lstrip('.')
            detected_file_type = FileType.from_extension(extension)
        
        # Only proceed if we detected a file type
        if not detected_file_type:
            return matches
        
        # Get paths to search based on context
        paths_to_check = await self._get_paths_to_check(context, search_scope)
        
        # Filter and score by matching the detected file type
        for path in paths_to_check:
            if not path.is_file():
                continue
                
            path_ext = path.suffix.lstrip('.')
            path_file_type = FileType.from_extension(path_ext)
            
            # If this path matches the detected file type
            if path_file_type == detected_file_type:
                # Start with a decent base score
                base_score = 0.75
                
                # Adjust score based on name similarity
                name_similarity = difflib.SequenceMatcher(None, path.stem.lower(), Path(reference).stem.lower()).ratio()
                if name_similarity >= 0.5:  # Lower threshold since we're matching by type
                    # Final score is a weighted combination of base score and name similarity
                    score = (base_score + name_similarity) / 2
                    
                    # Boost for exact extension match
                    ref_ext = Path(reference).suffix
                    if ref_ext and path.suffix == ref_ext:
                        score *= 1.1
                    
                    matches.append(Match(
                        path=path,
                        score=score,
                        strategy=ResolutionStrategy.FILE_TYPE,
                        metadata={
                            "file_type": detected_file_type.name,
                            "similarity": name_similarity
                        }
                    ))
        
        return matches
    
    async def _resolve_by_semantic_context(
        self, 
        reference: str, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Match]:
        """
        Resolve a reference using semantic context analysis.
        
        Args:
            reference: The reference to resolve
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of matches
        """
        matches = []
        
        # This is the most advanced strategy, using multiple context clues
        
        # Try to infer module/package name from reference
        module_name = None
        if '.' in reference and not reference.startswith('.'):
            parts = reference.split('.')
            if len(parts) > 1:
                # Could be a module reference like "module.submodule"
                module_name = parts[0]
        
        # Gather hints from various context elements
        context_hints = []
        
        # Check recent commands for hints
        if 'recent_commands' in context:
            for cmd in context.get('recent_commands', []):
                if reference in cmd:
                    context_hints.append(('command', cmd))
        
        # Check current file for hints
        if context.get('current_file') and 'content' in context.get('current_file', {}):
            content = context['current_file']['content']
            if reference in content:
                context_hints.append(('current_file', context['current_file']['path']))
        
        # Use these contextual hints to guide the search
        if module_name or context_hints:
            # Get paths to check
            base_paths = await self._get_base_paths(context, search_scope)
            
            for base_path in base_paths:
                if not base_path.exists() or not base_path.is_dir():
                    continue
                
                # If we have a module name, look for it as a directory
                if module_name:
                    module_path = base_path / module_name
                    if module_path.exists() and module_path.is_dir():
                        # Look for files within the module
                        for file_path in module_path.glob('**/*'):
                            if file_path.is_file():
                                # Check if any part of the reference matches
                                if any(part.lower() in file_path.name.lower() for part in reference.split('.')):
                                    # Calculate a score based on the match quality
                                    parts_matched = sum(1 for part in reference.split('.') if part.lower() in file_path.name.lower())
                                    score = 0.7 + (0.1 * parts_matched)  # Base score plus bonus for parts matched
                                    
                                    matches.append(Match(
                                        path=file_path,
                                        score=score,
                                        strategy=ResolutionStrategy.SEMANTIC_CONTEXT,
                                        metadata={"module": module_name}
                                    ))
                
                # Use context hints to guide search
                for hint_type, hint_value in context_hints:
                    # Different search strategy based on hint type
                    if hint_type == 'command':
                        # Extract paths from command
                        for word in hint_value.split():
                            word_path = Path(word)
                            if word_path.exists():
                                # Check if the word's directory contains our reference
                                parent_dir = word_path.parent
                                for file_path in parent_dir.glob('*'):
                                    if file_path.is_file() and reference.lower() in file_path.name.lower():
                                        # Score based on how much of the reference matches
                                        name_similarity = difflib.SequenceMatcher(None, file_path.name.lower(), reference.lower()).ratio()
                                        if name_similarity >= 0.6:  # Lower threshold due to context
                                            score = 0.75 * name_similarity  # Context-based discount
                                            
                                            matches.append(Match(
                                                path=file_path,
                                                score=score,
                                                strategy=ResolutionStrategy.SEMANTIC_CONTEXT,
                                                metadata={"hint": "command"}
                                            ))
                    
                    elif hint_type == 'current_file':
                        # Look for related files near the current file
                        current_file_path = Path(hint_value)
                        if current_file_path.exists():
                            # Check in the same directory
                            for file_path in current_file_path.parent.glob('*'):
                                if file_path.is_file() and reference.lower() in file_path.name.lower():
                                    # Score based on how much of the reference matches
                                    name_similarity = difflib.SequenceMatcher(None, file_path.name.lower(), reference.lower()).ratio()
                                    if name_similarity >= 0.6:  # Lower threshold due to context
                                        score = 0.7 * name_similarity  # Context-based discount
                                        
                                        matches.append(Match(
                                            path=file_path,
                                            score=score,
                                            strategy=ResolutionStrategy.SEMANTIC_CONTEXT,
                                            metadata={"hint": "current_file"}
                                        ))
        
        return matches
    
    async def _get_base_paths(
        self, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Path]:
        """
        Get base paths to search based on context and search scope.
        
        Args:
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of base paths
        """
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
        
        return base_paths
    
    async def _get_paths_to_check(
        self, 
        context: Dict[str, Any],
        search_scope: Optional[str] = None
    ) -> List[Path]:
        """
        Get paths to check based on context and search scope.
        
        Args:
            context: Context information
            search_scope: Optional scope for the search
            
        Returns:
            List of paths to check
        """
        paths_to_check = []
        
        # Get paths based on search scope
        if search_scope == "project" and context.get("project_root"):
            # Get files in the project (more targeted approach)
            project_path = Path(context["project_root"])
            
            # Add direct children of project root
            paths_to_check.extend(project_path.glob("*"))
            
            # Get common directories in projects and add their contents
            common_dirs = ["src", "lib", "app", "test", "tests", "docs", "scripts", "config"]
            for dirname in common_dirs:
                dir_path = project_path / dirname
                if dir_path.exists() and dir_path.is_dir():
                    paths_to_check.extend(dir_path.glob("*"))
                    
                    # For src directories, also check one level deeper
                    if dirname in ["src", "lib", "app"]:
                        paths_to_check.extend(dir_path.glob("*/*"))
        elif search_scope == "directory":
            # Get all files in the current directory
            cwd_path = Path(context["cwd"])
            paths_to_check.extend(cwd_path.glob("*"))
        else:
            # Default: check current directory first
            cwd_path = Path(context["cwd"])
            paths_to_check.extend(cwd_path.glob("*"))
            
            # Then check project root if different
            if context.get("project_root"):
                project_path = Path(context["project_root"])
                if project_path != cwd_path:
                    # Add direct children of project root
                    paths_to_check.extend(project_path.glob("*"))
                    
                    # Add common directories like src, lib, test
                    common_dirs = ["src", "lib", "test", "tests", "docs", "app", "bin"]
                    for dirname in common_dirs:
                        dir_path = project_path / dirname
                        if dir_path.exists() and dir_path.is_dir():
                            paths_to_check.extend(dir_path.glob("*"))
        
        # Deduplicate
        return list(set(paths_to_check))
    
    async def _record_resolution(
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
        self._logger.debug(f"Recording resolution: '{reference}' -> {resolved_path} (method: {method})")
        
        # Store in session for future reference
        try:
            session_manager = get_session_manager()
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
            
            # Track file viewing activity
            try:
                file_activity_tracker = get_file_activity_tracker()
                from angela.api.context import get_activity_type
                ActivityType = get_activity_type()
                
                file_activity_tracker.track_file_viewing(
                    resolved_path,
                    details={"reference": reference, "resolution_method": method}
                )
            except Exception as e:
                self._logger.warning(f"Error tracking file activity: {str(e)}")
                
        except Exception as e:
            self._logger.error(f"Error recording resolution: {str(e)}")
    
    def _get_from_cache(self, key: str) -> Optional[Path]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
            # Expired
            del self._cache[key]
        return None
    
    def _add_to_cache(self, key: str, value: Path) -> None:
        """
        Add a value to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (time.time(), value)
    
    def _maybe_cleanup_cache(self) -> None:
        """Clean up expired entries from the cache."""
        now = time.time()
        if now - self._cache_last_cleanup > 60:  # Cleanup every 60 seconds
            self._cache_last_cleanup = now
            expired_keys = []
            for key, (timestamp, _) in self._cache.items():
                if now - timestamp > self._cache_ttl:
                    expired_keys.append(key)
            for key in expired_keys:
                del self._cache[key]
            
            self._logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")

# Global file resolver instance
file_resolver = FileResolver()
