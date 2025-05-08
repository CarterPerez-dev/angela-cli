"""
Enhanced file activity tracking for Angela CLI.

This module extends the basic file activity tracking to include fine-grained
tracking of specific code entities (functions, classes, methods) being modified,
providing deeper contextual awareness.
"""
import os
import re
import time
import difflib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum

from angela.utils.logging import get_logger
from angela.context.file_activity import file_activity_tracker, ActivityType
from angela.ai.semantic_analyzer import semantic_analyzer, Module, Function, Class

logger = get_logger(__name__)

class EntityType(str, Enum):
    """Types of code entities that can be tracked."""
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    VARIABLE = "variable"
    IMPORT = "import"
    DOCSTRING = "docstring"
    PARAMETER = "parameter"
    UNKNOWN = "unknown"

@dataclass
class EntityActivity:
    """Represents an activity on a specific code entity."""
    entity_name: str
    entity_type: EntityType
    activity_type: ActivityType
    file_path: Path
    timestamp: float
    line_start: int
    line_end: int
    details: Dict[str, Any]
    before_content: Optional[str] = None
    after_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "activity_type": self.activity_type,
            "file_path": str(self.file_path),
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "line_start": self.line_start,
            "line_end": self.line_end,
            "details": self.details,
            "has_content_diff": self.before_content is not None and self.after_content is not None
        }

class EnhancedFileActivityTracker:
    """
    Enhanced tracker for file activities that includes code entity tracking.
    
    This class extends the basic file activity tracking to include:
    1. Function/method modification tracking
    2. Class structure changes
    3. Import statement changes
    4. Semantic diffs between versions
    """
    
    def __init__(self):
        """Initialize the enhanced file activity tracker."""
        self._logger = logger
        self._entity_activities: List[EntityActivity] = []
        self._max_activities = 100
        self._file_snapshots: Dict[str, Dict[str, Any]] = {}
        
        # Keep track of the last analyzed version of each file
        self._last_analyzed_modules: Dict[str, Module] = {}
        
        # Regular expressions for quick entity detection
        self._function_pattern = re.compile(r'(?:async\s+)?(?:def|function)\s+(\w+)\s*\(')
        self._class_pattern = re.compile(r'class\s+(\w+)\s*(?:\(|:)')
        self._import_pattern = re.compile(r'(?:import|from)\s+(\w+)')
    
    async def track_entity_changes(
        self, 
        file_path: Union[str, Path], 
        new_content: str = None,
        activity_type: ActivityType = ActivityType.MODIFIED,
        details: Dict[str, Any] = None
    ) -> List[EntityActivity]:
        """
        Track changes to specific entities within a file.
        
        Args:
            file_path: Path to the file being modified
            new_content: New content of the file (if None, will read from disk)
            activity_type: Type of activity
            details: Additional details about the activity
            
        Returns:
            List of entity activities detected
        """
        path_obj = Path(file_path)
        
        # Skip if file doesn't exist (or is being created)
        if not path_obj.exists() and activity_type != ActivityType.CREATED:
            return []
        
        # Skip binary files
        if self._is_binary_file(path_obj):
            return []
        
        # Get new content
        if new_content is None:
            try:
                with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                    new_content = f.read()
            except Exception as e:
                self._logger.error(f"Error reading file {path_obj}: {str(e)}")
                return []
        
        # Get old content from snapshot or disk
        old_content = self._get_previous_content(path_obj)
        
        # If file is new or we don't have previous content
        if old_content is None:
            # This is a new file or we don't have previous content
            # Analyze it as a whole
            entity_activities = await self._analyze_new_file(path_obj, new_content, activity_type, details or {})
            
            # Update the snapshot
            self._update_file_snapshot(path_obj, new_content)
            
            return entity_activities
        
        # Skip if content hasn't changed
        if old_content == new_content:
            return []
        
        # Detect changed entities
        entity_activities = await self._detect_entity_changes(path_obj, old_content, new_content, details or {})
        
        # Update the snapshot
        self._update_file_snapshot(path_obj, new_content)
        
        return entity_activities
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False
    
    def _get_previous_content(self, file_path: Path) -> Optional[str]:
        """Get the previous content of a file from snapshot."""
        path_str = str(file_path)
        
        if path_str in self._file_snapshots:
            return self._file_snapshots[path_str].get('content')
        
        return None
    
    def _update_file_snapshot(self, file_path: Path, content: str) -> None:
        """Update the snapshot of a file."""
        path_str = str(file_path)
        
        self._file_snapshots[path_str] = {
            'content': content,
            'timestamp': time.time()
        }
    
    async def _analyze_new_file(
        self,
        file_path: Path,
        content: str,
        activity_type: ActivityType,
        details: Dict[str, Any]
    ) -> List[EntityActivity]:
        """
        Analyze a new file to detect all entities.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            activity_type: Type of activity
            details: Additional details
            
        Returns:
            List of entity activities
        """
        # Use semantic analyzer to extract entities
        try:
            module = await semantic_analyzer.analyze_file(file_path)
            
            if not module:
                return []
            
            # Store module for later comparisons
            self._last_analyzed_modules[str(file_path)] = module
            
            entity_activities = []
            
            # Track classes
            for class_name, class_obj in module.classes.items():
                entity_activities.append(EntityActivity(
                    entity_name=class_name,
                    entity_type=EntityType.CLASS,
                    activity_type=activity_type,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=class_obj.line_start,
                    line_end=class_obj.line_end,
                    details={
                        **details,
                        'methods_count': len(class_obj.methods),
                        'attributes_count': len(class_obj.attributes),
                        'base_classes': class_obj.base_classes
                    },
                    before_content=None,
                    after_content=self._extract_entity_content(content, class_obj.line_start, class_obj.line_end)
                ))
                
                # Track methods
                for method_name, method_obj in class_obj.methods.items():
                    entity_activities.append(EntityActivity(
                        entity_name=f"{class_name}.{method_name}",
                        entity_type=EntityType.METHOD,
                        activity_type=activity_type,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=method_obj.line_start,
                        line_end=method_obj.line_end,
                        details={
                            **details,
                            'params': method_obj.params,
                            'class_name': class_name,
                            'return_type': method_obj.return_type
                        },
                        before_content=None,
                        after_content=self._extract_entity_content(content, method_obj.line_start, method_obj.line_end)
                    ))
            
            # Track functions
            for func_name, func_obj in module.functions.items():
                entity_activities.append(EntityActivity(
                    entity_name=func_name,
                    entity_type=EntityType.FUNCTION,
                    activity_type=activity_type,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=func_obj.line_start,
                    line_end=func_obj.line_end,
                    details={
                        **details,
                        'params': func_obj.params,
                        'return_type': func_obj.return_type
                    },
                    before_content=None,
                    after_content=self._extract_entity_content(content, func_obj.line_start, func_obj.line_end)
                ))
            
            # Track imports
            for import_name, import_obj in module.imports.items():
                entity_activities.append(EntityActivity(
                    entity_name=import_name,
                    entity_type=EntityType.IMPORT,
                    activity_type=activity_type,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=import_obj.line_start,
                    line_end=import_obj.line_end,
                    details={
                        **details,
                        'import_path': import_obj.import_path,
                        'is_from': import_obj.is_from
                    },
                    before_content=None,
                    after_content=self._extract_entity_content(content, import_obj.line_start, import_obj.line_end)
                ))
            
            # Store entity activities
            self._store_entity_activities(entity_activities)
            
            return entity_activities
            
        except Exception as e:
            self._logger.error(f"Error analyzing new file {file_path}: {str(e)}")
            return []
    
    async def _detect_entity_changes(
        self,
        file_path: Path,
        old_content: str,
        new_content: str,
        details: Dict[str, Any]
    ) -> List[EntityActivity]:
        """
        Detect changes to specific entities between file versions.
        
        Args:
            file_path: Path to the file
            old_content: Previous content of the file
            new_content: New content of the file
            details: Additional details
            
        Returns:
            List of entity activities
        """
        entity_activities = []
        
        # Use semantic analyzer to extract entities from both versions
        try:
            # Create a temporary file for the old content
            old_temp_path = file_path.with_suffix(f"{file_path.suffix}.old")
            with open(old_temp_path, 'w', encoding='utf-8') as f:
                f.write(old_content)
            
            # Analyze old and new versions
            old_module = await semantic_analyzer.analyze_file(old_temp_path)
            
            # Remove temporary file
            os.unlink(old_temp_path)
            
            # If we already have the old module analyzed, use it
            path_str = str(file_path)
            if path_str in self._last_analyzed_modules:
                old_module = self._last_analyzed_modules[path_str]
            
            # Analyze new version
            new_module = await semantic_analyzer.analyze_file(file_path)
            
            if not old_module or not new_module:
                # Fall back to diff-based detection
                return await self._detect_changes_by_diff(file_path, old_content, new_content, details)
            
            # Store new module for later comparisons
            self._last_analyzed_modules[path_str] = new_module
            
            # Compare classes
            entity_activities.extend(self._compare_classes(
                file_path, old_module, new_module, old_content, new_content, details
            ))
            
            # Compare standalone functions
            entity_activities.extend(self._compare_functions(
                file_path, old_module, new_module, old_content, new_content, details
            ))
            
            # Compare imports
            entity_activities.extend(self._compare_imports(
                file_path, old_module, new_module, old_content, new_content, details
            ))
            
            # Compare docstring
            if old_module.docstring != new_module.docstring:
                entity_activities.append(EntityActivity(
                    entity_name="module_docstring",
                    entity_type=EntityType.DOCSTRING,
                    activity_type=ActivityType.MODIFIED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=1,
                    line_end=1 + (new_module.docstring or "").count('\n'),
                    details=details,
                    before_content=old_module.docstring,
                    after_content=new_module.docstring
                ))
            
            # Fall back to diff-based detection if no entities were detected
            if not entity_activities:
                entity_activities = await self._detect_changes_by_diff(file_path, old_content, new_content, details)
            
            # Store entity activities
            self._store_entity_activities(entity_activities)
            
            return entity_activities
            
        except Exception as e:
            self._logger.error(f"Error analyzing entity changes in {file_path}: {str(e)}")
            
            # Fall back to diff-based detection
            return await self._detect_changes_by_diff(file_path, old_content, new_content, details)
    
    def _compare_classes(
        self,
        file_path: Path,
        old_module: Module,
        new_module: Module,
        old_content: str,
        new_content: str,
        details: Dict[str, Any]
    ) -> List[EntityActivity]:
        """
        Compare classes between module versions.
        
        Args:
            file_path: Path to the file
            old_module: Previous module
            new_module: New module
            old_content: Previous content
            new_content: New content
            details: Additional details
            
        Returns:
            List of entity activities
        """
        entity_activities = []
        
        # Check for added classes
        for class_name, new_class in new_module.classes.items():
            if class_name not in old_module.classes:
                # Class was added
                entity_activities.append(EntityActivity(
                    entity_name=class_name,
                    entity_type=EntityType.CLASS,
                    activity_type=ActivityType.CREATED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_class.line_start,
                    line_end=new_class.line_end,
                    details={
                        **details,
                        'methods_count': len(new_class.methods),
                        'attributes_count': len(new_class.attributes),
                        'base_classes': new_class.base_classes
                    },
                    before_content=None,
                    after_content=self._extract_entity_content(new_content, new_class.line_start, new_class.line_end)
                ))
                continue
            
            # Class exists in both - check for changes
            old_class = old_module.classes[class_name]
            
            # Check if class definition changed
            class_changed = (
                old_class.base_classes != new_class.base_classes or
                old_class.docstring != new_class.docstring or
                old_class.decorators != new_class.decorators
            )
            
            if class_changed:
                entity_activities.append(EntityActivity(
                    entity_name=class_name,
                    entity_type=EntityType.CLASS,
                    activity_type=ActivityType.MODIFIED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_class.line_start,
                    line_end=new_class.line_end,
                    details={
                        **details,
                        'methods_count': len(new_class.methods),
                        'attributes_count': len(new_class.attributes),
                        'old_base_classes': old_class.base_classes,
                        'new_base_classes': new_class.base_classes
                    },
                    before_content=self._extract_entity_content(old_content, old_class.line_start, old_class.line_end),
                    after_content=self._extract_entity_content(new_content, new_class.line_start, new_class.line_end)
                ))
            
            # Check for added/modified methods
            for method_name, new_method in new_class.methods.items():
                if method_name not in old_class.methods:
                    # Method was added
                    entity_activities.append(EntityActivity(
                        entity_name=f"{class_name}.{method_name}",
                        entity_type=EntityType.METHOD,
                        activity_type=ActivityType.CREATED,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=new_method.line_start,
                        line_end=new_method.line_end,
                        details={
                            **details,
                            'params': new_method.params,
                            'class_name': class_name,
                            'return_type': new_method.return_type
                        },
                        before_content=None,
                        after_content=self._extract_entity_content(new_content, new_method.line_start, new_method.line_end)
                    ))
                    continue
                
                # Method exists in both - check for changes
                old_method = old_class.methods[method_name]
                method_changed = (
                    old_method.params != new_method.params or
                    old_method.return_type != new_method.return_type or
                    old_method.docstring != new_method.docstring or
                    self._extract_entity_content(old_content, old_method.line_start, old_method.line_end) !=
                    self._extract_entity_content(new_content, new_method.line_start, new_method.line_end)
                )
                
                if method_changed:
                    entity_activities.append(EntityActivity(
                        entity_name=f"{class_name}.{method_name}",
                        entity_type=EntityType.METHOD,
                        activity_type=ActivityType.MODIFIED,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=new_method.line_start,
                        line_end=new_method.line_end,
                        details={
                            **details,
                            'old_params': old_method.params,
                            'new_params': new_method.params,
                            'class_name': class_name,
                            'old_return_type': old_method.return_type,
                            'new_return_type': new_method.return_type
                        },
                        before_content=self._extract_entity_content(old_content, old_method.line_start, old_method.line_end),
                        after_content=self._extract_entity_content(new_content, new_method.line_start, new_method.line_end)
                    ))
            
            # Check for removed methods
            for method_name in old_class.methods:
                if method_name not in new_class.methods:
                    # Method was removed
                    old_method = old_class.methods[method_name]
                    entity_activities.append(EntityActivity(
                        entity_name=f"{class_name}.{method_name}",
                        entity_type=EntityType.METHOD,
                        activity_type=ActivityType.DELETED,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=old_method.line_start,
                        line_end=old_method.line_end,
                        details={
                            **details,
                            'params': old_method.params,
                            'class_name': class_name,
                            'return_type': old_method.return_type
                        },
                        before_content=self._extract_entity_content(old_content, old_method.line_start, old_method.line_end),
                        after_content=None
                    ))
        
        # Check for removed classes
        for class_name, old_class in old_module.classes.items():
            if class_name not in new_module.classes:
                # Class was removed
                entity_activities.append(EntityActivity(
                    entity_name=class_name,
                    entity_type=EntityType.CLASS,
                    activity_type=ActivityType.DELETED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=old_class.line_start,
                    line_end=old_class.line_end,
                    details={
                        **details,
                        'methods_count': len(old_class.methods),
                        'attributes_count': len(old_class.attributes),
                        'base_classes': old_class.base_classes
                    },
                    before_content=self._extract_entity_content(old_content, old_class.line_start, old_class.line_end),
                    after_content=None
                ))
        
        return entity_activities
    
    def _compare_functions(
        self,
        file_path: Path,
        old_module: Module,
        new_module: Module,
        old_content: str,
        new_content: str,
        details: Dict[str, Any]
    ) -> List[EntityActivity]:
        """
        Compare standalone functions between module versions.
        
        Args:
            file_path: Path to the file
            old_module: Previous module
            new_module: New module
            old_content: Previous content
            new_content: New content
            details: Additional details
            
        Returns:
            List of entity activities
        """
        entity_activities = []
        
        # Check for added functions
        for func_name, new_func in new_module.functions.items():
            if func_name not in old_module.functions:
                # Function was added
                entity_activities.append(EntityActivity(
                    entity_name=func_name,
                    entity_type=EntityType.FUNCTION,
                    activity_type=ActivityType.CREATED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_func.line_start,
                    line_end=new_func.line_end,
                    details={
                        **details,
                        'params': new_func.params,
                        'return_type': new_func.return_type
                    },
                    before_content=None,
                    after_content=self._extract_entity_content(new_content, new_func.line_start, new_func.line_end)
                ))
                continue
            
            # Function exists in both - check for changes
            old_func = old_module.functions[func_name]
            func_changed = (
                old_func.params != new_func.params or
                old_func.return_type != new_func.return_type or
                old_func.docstring != new_func.docstring or
                self._extract_entity_content(old_content, old_func.line_start, old_func.line_end) !=
                self._extract_entity_content(new_content, new_func.line_start, new_func.line_end)
            )
            
            if func_changed:
                entity_activities.append(EntityActivity(
                    entity_name=func_name,
                    entity_type=EntityType.FUNCTION,
                    activity_type=ActivityType.MODIFIED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_func.line_start,
                    line_end=new_func.line_end,
                    details={
                        **details,
                        'old_params': old_func.params,
                        'new_params': new_func.params,
                        'old_return_type': old_func.return_type,
                        'new_return_type': new_func.return_type
                    },
                    before_content=self._extract_entity_content(old_content, old_func.line_start, old_func.line_end),
                    after_content=self._extract_entity_content(new_content, new_func.line_start, new_func.line_end)
                ))
        
        # Check for removed functions
        for func_name, old_func in old_module.functions.items():
            if func_name not in new_module.functions:
                # Function was removed
                entity_activities.append(EntityActivity(
                    entity_name=func_name,
                    entity_type=EntityType.FUNCTION,
                    activity_type=ActivityType.DELETED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=old_func.line_start,
                    line_end=old_func.line_end,
                    details={
                        **details,
                        'params': old_func.params,
                        'return_type': old_func.return_type
                    },
                    before_content=self._extract_entity_content(old_content, old_func.line_start, old_func.line_end),
                    after_content=None
                ))
        
        return entity_activities
    
    def _compare_imports(
        self,
        file_path: Path,
        old_module: Module,
        new_module: Module,
        old_content: str,
        new_content: str,
        details: Dict[str, Any]
    ) -> List[EntityActivity]:
        """
        Compare imports between module versions.
        
        Args:
            file_path: Path to the file
            old_module: Previous module
            new_module: New module
            old_content: Previous content
            new_content: New content
            details: Additional details
            
        Returns:
            List of entity activities
        """
        entity_activities = []
        
        # Check for added imports
        for import_name, new_import in new_module.imports.items():
            if import_name not in old_module.imports:
                # Import was added
                entity_activities.append(EntityActivity(
                    entity_name=import_name,
                    entity_type=EntityType.IMPORT,
                    activity_type=ActivityType.CREATED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_import.line_start,
                    line_end=new_import.line_end,
                    details={
                        **details,
                        'import_path': new_import.import_path,
                        'is_from': new_import.is_from
                    },
                    before_content=None,
                    after_content=self._extract_entity_content(new_content, new_import.line_start, new_import.line_end)
                ))
                continue
            
            # Import exists in both - check for changes
            old_import = old_module.imports[import_name]
            import_changed = (
                old_import.import_path != new_import.import_path or
                old_import.is_from != new_import.is_from or
                old_import.alias != new_import.alias
            )
            
            if import_changed:
                entity_activities.append(EntityActivity(
                    entity_name=import_name,
                    entity_type=EntityType.IMPORT,
                    activity_type=ActivityType.MODIFIED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_import.line_start,
                    line_end=new_import.line_end,
                    details={
                        **details,
                        'old_import_path': old_import.import_path,
                        'new_import_path': new_import.import_path,
                        'old_is_from': old_import.is_from,
                        'new_is_from': new_import.is_from
                    },
                    before_content=self._extract_entity_content(old_content, old_import.line_start, old_import.line_end),
                    after_content=self._extract_entity_content(new_content, new_import.line_start, new_import.line_end)
                ))
        
        # Check for removed imports
        for import_name, old_import in old_module.imports.items():
            if import_name not in new_module.imports:
                # Import was removed
                entity_activities.append(EntityActivity(
                    entity_name=import_name,
                    entity_type=EntityType.IMPORT,
                    activity_type=ActivityType.DELETED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=old_import.line_start,
                    line_end=old_import.line_end,
                    details={
                        **details,
                        'import_path': old_import.import_path,
                        'is_from': old_import.is_from
                    },
                    before_content=self._extract_entity_content(old_content, old_import.line_start, old_import.line_end),
                    after_content=None
                ))
        
        return entity_activities
    
    async def _detect_changes_by_diff(
        self,
        file_path: Path,
        old_content: str,
        new_content: str,
        details: Dict[str, Any]
    ) -> List[EntityActivity]:
        """
        Use diff to detect changes when semantic analysis fails.
        
        Args:
            file_path: Path to the file
            old_content: Previous content
            new_content: New content
            details: Additional details
            
        Returns:
            List of entity activities
        """
        if not old_content or not new_content:
            return []
        
        entity_activities = []
        
        # Generate diff
        diff = list(difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            n=3  # Context lines
        ))
        
        if not diff:
            return []
        
        # Extract chunks of changes
        current_chunk = []
        chunks = []
        
        for line in diff:
            if line.startswith('@@'):
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [line]
            elif current_chunk:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Process each chunk to detect entity changes
        for chunk in chunks:
            if not chunk:
                continue
            
            # Parse chunk header to get line numbers
            header = chunk[0]
            match = re.search(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', header)
            if not match:
                continue
            
            old_start, old_count = int(match.group(1)), int(match.group(2))
            new_start, new_count = int(match.group(3)), int(match.group(4))
            
            # Get the chunk content
            chunk_content = chunk[1:]
            
            # Try to identify entities in this chunk
            entity_activity = self._identify_entity_in_diff_chunk(
                file_path, old_content, new_content, old_start, old_count, new_start, new_count, chunk_content, details
            )
            
            if entity_activity:
                entity_activities.append(entity_activity)
            else:
                # Fall back to a generic line range activity
                entity_activities.append(EntityActivity(
                    entity_name=f"line_range_{new_start}_{new_start + new_count}",
                    entity_type=EntityType.UNKNOWN,
                    activity_type=ActivityType.MODIFIED,
                    file_path=file_path,
                    timestamp=time.time(),
                    line_start=new_start,
                    line_end=new_start + new_count,
                    details=details,
                    before_content="\n".join(old_content.splitlines()[old_start-1:old_start+old_count-1]),
                    after_content="\n".join(new_content.splitlines()[new_start-1:new_start+new_count-1])
                ))
        
        # Store entity activities
        self._store_entity_activities(entity_activities)
        
        return entity_activities
    
    def _identify_entity_in_diff_chunk(
        self,
        file_path: Path,
        old_content: str,
        new_content: str,
        old_start: int,
        old_count: int,
        new_start: int,
        new_count: int,
        chunk_content: List[str],
        details: Dict[str, Any]
    ) -> Optional[EntityActivity]:
        """
        Try to identify what entity was modified in a diff chunk.
        
        Args:
            file_path: Path to the file
            old_content: Previous content
            new_content: New content
            old_start: Starting line in old content (1-based)
            old_count: Number of lines in old content
            new_start: Starting line in new content (1-based)
            new_count: Number of lines in new content
            chunk_content: Content of the diff chunk
            details: Additional details
            
        Returns:
            EntityActivity if identified, None otherwise
        """
        # Get the surrounding context from old and new content
        old_context_start = max(1, old_start - 10)
        old_context_end = min(len(old_content.splitlines()), old_start + old_count + 10)
        old_context = old_content.splitlines()[old_context_start-1:old_context_end]
        
        new_context_start = max(1, new_start - 10)
        new_context_end = min(len(new_content.splitlines()), new_start + new_count + 10)
        new_context = new_content.splitlines()[new_context_start-1:new_context_end]
        
        # Check for function definitions
        for i, line in enumerate(old_context):
            match = self._function_pattern.search(line)
            if match:
                func_start = old_context_start + i
                if old_start <= func_start <= old_start + old_count:
                    # Function was modified or deleted
                    func_name = match.group(1)
                    
                    # Look for the same function in new content
                    found_in_new = False
                    new_func_start = 0
                    
                    for j, new_line in enumerate(new_context):
                        new_match = self._function_pattern.search(new_line)
                        if new_match and new_match.group(1) == func_name:
                            found_in_new = True
                            new_func_start = new_context_start + j
                            break
                    
                    activity_type = ActivityType.MODIFIED if found_in_new else ActivityType.DELETED
                    
                    # Estimate function end
                    old_func_end = self._estimate_entity_end(old_content, func_start)
                    new_func_end = self._estimate_entity_end(new_content, new_func_start) if found_in_new else 0
                    
                    return EntityActivity(
                        entity_name=func_name,
                        entity_type=EntityType.FUNCTION,
                        activity_type=activity_type,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=new_func_start if found_in_new else func_start,
                        line_end=new_func_end if found_in_new else old_func_end,
                        details=details,
                        before_content=self._extract_entity_content(old_content, func_start, old_func_end),
                        after_content=self._extract_entity_content(new_content, new_func_start, new_func_end) if found_in_new else None
                    )
        
        # Check for new functions in the new content
        for i, line in enumerate(new_context):
            match = self._function_pattern.search(line)
            if match:
                func_start = new_context_start + i
                if new_start <= func_start <= new_start + new_count:
                    # New function was added
                    func_name = match.group(1)
                    
                    # Check if this function exists in old content
                    found_in_old = False
                    for old_line in old_context:
                        old_match = self._function_pattern.search(old_line)
                        if old_match and old_match.group(1) == func_name:
                            found_in_old = True
                            break
                    
                    if not found_in_old:
                        # Estimate function end
                        func_end = self._estimate_entity_end(new_content, func_start)
                        
                        return EntityActivity(
                            entity_name=func_name,
                            entity_type=EntityType.FUNCTION,
                            activity_type=ActivityType.CREATED,
                            file_path=file_path,
                            timestamp=time.time(),
                            line_start=func_start,
                            line_end=func_end,
                            details=details,
                            before_content=None,
                            after_content=self._extract_entity_content(new_content, func_start, func_end)
                        )
        
        # Check for class definitions
        for i, line in enumerate(old_context):
            match = self._class_pattern.search(line)
            if match:
                class_start = old_context_start + i
                if old_start <= class_start <= old_start + old_count:
                    # Class was modified or deleted
                    class_name = match.group(1)
                    
                    # Look for the same class in new content
                    found_in_new = False
                    new_class_start = 0
                    
                    for j, new_line in enumerate(new_context):
                        new_match = self._class_pattern.search(new_line)
                        if new_match and new_match.group(1) == class_name:
                            found_in_new = True
                            new_class_start = new_context_start + j
                            break
                    
                    activity_type = ActivityType.MODIFIED if found_in_new else ActivityType.DELETED
                    
                    # Estimate class end
                    old_class_end = self._estimate_entity_end(old_content, class_start)
                    new_class_end = self._estimate_entity_end(new_content, new_class_start) if found_in_new else 0
                    
                    return EntityActivity(
                        entity_name=class_name,
                        entity_type=EntityType.CLASS,
                        activity_type=activity_type,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=new_class_start if found_in_new else class_start,
                        line_end=new_class_end if found_in_new else old_class_end,
                        details=details,
                        before_content=self._extract_entity_content(old_content, class_start, old_class_end),
                        after_content=self._extract_entity_content(new_content, new_class_start, new_class_end) if found_in_new else None
                    )
        
        # Check for new classes in the new content
        for i, line in enumerate(new_context):
            match = self._class_pattern.search(line)
            if match:
                class_start = new_context_start + i
                if new_start <= class_start <= new_start + new_count:
                    # New class was added
                    class_name = match.group(1)
                    
                    # Check if this class exists in old content
                    found_in_old = False
                    for old_line in old_context:
                        old_match = self._class_pattern.search(old_line)
                        if old_match and old_match.group(1) == class_name:
                            found_in_old = True
                            break
                    
                    if not found_in_old:
                        # Estimate class end
                        class_end = self._estimate_entity_end(new_content, class_start)
                        
                        return EntityActivity(
                            entity_name=class_name,
                            entity_type=EntityType.CLASS,
                            activity_type=ActivityType.CREATED,
                            file_path=file_path,
                            timestamp=time.time(),
                            line_start=class_start,
                            line_end=class_end,
                            details=details,
                            before_content=None,
                            after_content=self._extract_entity_content(new_content, class_start, class_end)
                        )
        
        # Check for import statements
        for i, line in enumerate(old_context):
            match = self._import_pattern.search(line)
            if match:
                import_start = old_context_start + i
                if old_start <= import_start <= old_start + old_count:
                    # Import was modified or deleted
                    import_name = match.group(1)
                    
                    # Look for the same import in new content
                    found_in_new = False
                    new_import_start = 0
                    
                    for j, new_line in enumerate(new_context):
                        new_match = self._import_pattern.search(new_line)
                        if new_match and new_match.group(1) == import_name:
                            found_in_new = True
                            new_import_start = new_context_start + j
                            break
                    
                    activity_type = ActivityType.MODIFIED if found_in_new else ActivityType.DELETED
                    
                    return EntityActivity(
                        entity_name=import_name,
                        entity_type=EntityType.IMPORT,
                        activity_type=activity_type,
                        file_path=file_path,
                        timestamp=time.time(),
                        line_start=new_import_start if found_in_new else import_start,
                        line_end=new_import_start if found_in_new else import_start,
                        details=details,
                        before_content=line.strip(),
                        after_content=new_context[new_import_start - new_context_start].strip() if found_in_new else None
                    )
        
        # Check for new imports in the new content
        for i, line in enumerate(new_context):
            match = self._import_pattern.search(line)
            if match:
                import_start = new_context_start + i
                if new_start <= import_start <= new_start + new_count:
                    # New import was added
                    import_name = match.group(1)
                    
                    # Check if this import exists in old content
                    found_in_old = False
                    for old_line in old_context:
                        old_match = self._import_pattern.search(old_line)
                        if old_match and old_match.group(1) == import_name:
                            found_in_old = True
                            break
                    
                    if not found_in_old:
                        return EntityActivity(
                            entity_name=import_name,
                            entity_type=EntityType.IMPORT,
                            activity_type=ActivityType.CREATED,
                            file_path=file_path,
                            timestamp=time.time(),
                            line_start=import_start,
                            line_end=import_start,
                            details=details,
                            before_content=None,
                            after_content=line.strip()
                        )
        
        return None
    
    def _extract_entity_content(self, content: str, start_line: int, end_line: int) -> str:
        """
        Extract entity content from a file.
        
        Args:
            content: File content
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)
            
        Returns:
            Extracted content
        """
        if not content:
            return ""
        
        lines = content.splitlines()
        
        # Adjust line numbers to be within bounds
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        
        return "\n".join(lines[start_idx:end_idx])
    
    def _estimate_entity_end(self, content: str, start_line: int) -> int:
        """
        Estimate the ending line number of an entity.
        
        Args:
            content: File content
            start_line: Starting line number (1-based)
            
        Returns:
            Estimated ending line number (1-based)
        """
        lines = content.splitlines()
        
        # Adjust line number to be within bounds
        start_idx = max(0, start_line - 1)
        
        if start_idx >= len(lines):
            return start_line
        
        # Count indentation of the entity definition line
        first_line = lines[start_idx]
        indent_match = re.match(r'^(\s*)', first_line)
        base_indent = len(indent_match.group(1)) if indent_match else 0
        
        # Find the first line with the same or less indentation
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check indentation
            indent_match = re.match(r'^(\s*)', line)
            indent = len(indent_match.group(1)) if indent_match else 0
            
            if indent <= base_indent:
                return i + 1  # 1-based line number
        
        # If we reach the end of the file, return the last line number
        return len(lines)
    
    def _store_entity_activities(self, entity_activities: List[EntityActivity]) -> None:
        """
        Store entity activities and log them to the basic file activity tracker.
        
        Args:
            entity_activities: List of entity activities to store
        """
        # Add to the entity activities list
        self._entity_activities.extend(entity_activities)
        
        # Trim if needed
        if len(self._entity_activities) > self._max_activities:
            self._entity_activities = self._entity_activities[-self._max_activities:]
        
        # Log to the basic file activity tracker
        for activity in entity_activities:
            entity_str = f"{activity.entity_type.value}:{activity.entity_name}"
            
            # Track in the basic file activity tracker
            file_activity_tracker.track_activity(
                path=activity.file_path,
                activity_type=activity.activity_type,
                details={
                    "entity_name": activity.entity_name,
                    "entity_type": activity.entity_type.value,
                    "line_start": activity.line_start,
                    "line_end": activity.line_end,
                    **activity.details
                }
            )
            
            # Log the activity
            self._logger.debug(
                f"Tracked {activity.activity_type.value} of {entity_str} "
                f"in {activity.file_path.name}:{activity.line_start}-{activity.line_end}"
            )
    
    def get_recent_entity_activities(
        self,
        limit: int = 10,
        entity_types: Optional[List[EntityType]] = None,
        activity_types: Optional[List[ActivityType]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent entity activities.
        
        Args:
            limit: Maximum number of activities to return
            entity_types: Optional filter for entity types
            activity_types: Optional filter for activity types
            
        Returns:
            List of entity activities as dictionaries
        """
        # Apply filters
        filtered = self._entity_activities
        
        if entity_types:
            filtered = [a for a in filtered if a.entity_type in entity_types]
        
        if activity_types:
            filtered = [a for a in filtered if a.activity_type in activity_types]
        
        # Sort by timestamp (newest first)
        sorted_activities = sorted(filtered, key=lambda a: a.timestamp, reverse=True)
        
        # Convert to dictionaries
        return [a.to_dict() for a in sorted_activities[:limit]]
    
    def get_entity_activities_by_name(
        self,
        entity_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get activities for a specific entity.
        
        Args:
            entity_name: Name of the entity
            limit: Maximum number of activities to return
            
        Returns:
            List of entity activities as dictionaries
        """
        # Filter by entity name
        filtered = [a for a in self._entity_activities if a.entity_name == entity_name]
        
        # Sort by timestamp (newest first)
        sorted_activities = sorted(filtered, key=lambda a: a.timestamp, reverse=True)
        
        # Convert to dictionaries
        return [a.to_dict() for a in sorted_activities[:limit]]
    
    def get_most_active_entities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most actively modified entities.
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of entities with activity counts
        """
        # Count activities by entity
        entity_counts = {}
        
        for activity in self._entity_activities:
            key = f"{activity.entity_type.value}:{activity.entity_name}"
            
            if key not in entity_counts:
                entity_counts[key] = {
                    "entity_name": activity.entity_name,
                    "entity_type": activity.entity_type.value,
                    "count": 0,
                    "last_activity": None,
                    "activity_types": set()
                }
            
            entity_counts[key]["count"] += 1
            entity_counts[key]["activity_types"].add(activity.activity_type.value)
            
            # Update last activity if newer
            if entity_counts[key]["last_activity"] is None or activity.timestamp > entity_counts[key]["last_activity"]:
                entity_counts[key]["last_activity"] = activity.timestamp
                entity_counts[key]["file_path"] = str(activity.file_path)
                entity_counts[key]["line_start"] = activity.line_start
                entity_counts[key]["line_end"] = activity.line_end
        
        # Convert to list and sort by count
        result = []
        for key, entity_info in entity_counts.items():
            # Convert activity types set to list
            entity_info["activity_types"] = list(entity_info["activity_types"])
            
            # Add formatted timestamp
            if entity_info["last_activity"]:
                entity_info["last_activity_time"] = datetime.fromtimestamp(entity_info["last_activity"]).isoformat()
            
            result.append(entity_info)
        
        result.sort(key=lambda x: x["count"], reverse=True)
        
        return result[:limit]
    
    def clear_activities(self) -> None:
        """Clear all tracked activities."""
        self._entity_activities.clear()
        self._file_snapshots.clear()
        self._last_analyzed_modules.clear()
        self._logger.debug("Cleared all entity activities and snapshots")
    
    def get_entity_history(self, entity_name: str, entity_type: Optional[EntityType] = None) -> List[Dict[str, Any]]:
        """
        Get the complete history of changes for a specific entity.
        
        Args:
            entity_name: Name of the entity
            entity_type: Optional entity type filter
            
        Returns:
            List of activities for the entity, ordered by time
        """
        # Filter activities
        filtered = [a for a in self._entity_activities if a.entity_name == entity_name]
        
        if entity_type:
            filtered = [a for a in filtered if a.entity_type == entity_type]
        
        # Sort by timestamp (oldest first for history)
        sorted_activities = sorted(filtered, key=lambda a: a.timestamp)
        
        # Convert to dictionaries
        return [a.to_dict() for a in sorted_activities]

# Global enhanced file activity tracker instance
enhanced_file_activity_tracker = EnhancedFileActivityTracker()
