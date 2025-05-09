# angela/context/semantic_context_manager.py
"""
Semantic context management for Angela CLI.

This module integrates and manages all semantic understanding components,
providing a unified interface for accessing rich contextual information
about code, project state, and user intentions.
"""
import os
import asyncio
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union
from datetime import datetime

from angela.utils.logging import get_logger
from angela.context.manager import context_manager
from angela.context.file_activity import file_activity_tracker
from angela.context.project_state_analyzer import project_state_analyzer
from angela.ai.semantic_analyzer import semantic_analyzer
from angela.core.registry import registry

logger = get_logger(__name__)

class SemanticContextManager:
    """
    Central manager for all semantic context information.
    
    This class integrates:
    1. Code semantic analysis (functions, classes, relationships)
    2. Project state information (git status, migrations, dependencies)
    3. File activity tracking (down to function/class level)
    4. User intention mapping based on history and current context
    
    It provides a unified interface for AI components to access rich
    contextual information for more informed responses.
    """
    
    def __init__(self):
        """Initialize the semantic context manager."""
        self._logger = logger
        self._analysis_cache = {}  # Cache of semantic analysis results
        self._last_analysis_time = {}  # Timestamp of last analysis
        self._active_analyses = set()  # Currently running analyses
        self._analysis_valid_time = 300  # Seconds before a cached analysis is invalid
        
        # Project module cache - maps project root to module info
        self._project_modules = {}
        
        # Map of file paths to functions and classes
        self._entity_map = {}  # Maps "function_name" -> file_path
        self._recent_entity_usages = []  # List of recently used entities
        
        # Register this service
        registry.register("semantic_context_manager", self)
    
    async def refresh_context(self, force: bool = False) -> None:
        """
        Refresh the semantic context for the current project.
        
        Args:
            force: Whether to force a refresh even if the cache is valid
        """
        # Get the current project root
        project_root = context_manager.project_root
        if not project_root:
            self._logger.debug("No project root detected, skipping semantic context refresh")
            return
        
        # Check if we need to refresh
        if not force and project_root in self._last_analysis_time:
            last_time = self._last_analysis_time[project_root]
            age = datetime.now().timestamp() - last_time
            if age < self._analysis_valid_time:
                self._logger.debug(f"Using cached semantic analysis for {project_root} (age: {age:.1f}s)")
                return
        
        # Don't start multiple analyses for the same project
        if project_root in self._active_analyses:
            self._logger.debug(f"Analysis already in progress for {project_root}")
            return
            
        self._active_analyses.add(project_root)
        
        try:
            self._logger.info(f"Refreshing semantic context for {project_root}")
            
            # Get project state asynchronously
            project_state_task = asyncio.create_task(
                project_state_analyzer.get_project_state(project_root)
            )
            
            # Start semantic analysis of key files asynchronously
            semantic_analysis_task = asyncio.create_task(
                self._analyze_key_files(project_root)
            )
            
            # Wait for both tasks to complete
            project_state, semantic_analysis = await asyncio.gather(
                project_state_task, 
                semantic_analysis_task
            )
            
            # Store the results
            self._analysis_cache[project_root] = {
                "project_state": project_state,
                "semantic_analysis": semantic_analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            self._last_analysis_time[project_root] = datetime.now().timestamp()
            self._logger.info(f"Semantic context refresh completed for {project_root}")
            
        except Exception as e:
            self._logger.exception(f"Error refreshing semantic context: {str(e)}")
        finally:
            self._active_analyses.remove(project_root)
    
    async def _analyze_key_files(self, project_root: Path) -> Dict[str, Any]:
        """
        Analyze the key files in the project.
        
        Args:
            project_root: The project root path
            
        Returns:
            Dictionary with semantic analysis information
        """
        # Get key files to analyze
        key_files = await self._identify_key_files(project_root)
        
        # Perform semantic analysis
        modules = {}
        for file_path in key_files:
            try:
                module = await semantic_analyzer.analyze_file(file_path)
                if module:
                    modules[str(file_path)] = module
            except Exception as e:
                self._logger.error(f"Error analyzing file {file_path}: {str(e)}")
        
        # Update the entity map
        self._update_entity_map(modules)
        
        # Store the modules for this project
        self._project_modules[str(project_root)] = modules
        
        # Calculate project-wide metrics
        metrics = semantic_analyzer.calculate_project_metrics(modules)
        
        # Return summary
        return {
            "analyzed_files_count": len(modules),
            "entities": {
                "functions": sum(len(module.functions) for module in modules.values()),
                "classes": sum(len(module.classes) for module in modules.values()),
                "variables": sum(len(module.variables) for module in modules.values())
            },
            "metrics": metrics,
            "key_files": [str(f) for f in key_files[:10]]  # Include only the first 10 for brevity
        }
    
    def _update_entity_map(self, modules: Dict[str, Any]) -> None:
        """
        Update the entity map with the analyzed modules.
        
        Args:
            modules: Dictionary of modules
        """
        for file_path, module in modules.items():
            # Add functions
            for func_name, func in module.functions.items():
                self._entity_map[func_name] = file_path
            
            # Add classes
            for class_name, cls in module.classes.items():
                self._entity_map[class_name] = file_path
                
                # Add methods with class prefix
                for method_name in cls.methods:
                    qualified_name = f"{class_name}.{method_name}"
                    self._entity_map[qualified_name] = file_path
    
    async def _identify_key_files(self, project_root: Path) -> List[Path]:
        """
        Identify the key files in the project for analysis.
        
        Prioritizes:
        1. Recently accessed files
        2. Files with the most activity
        3. Entry point files (main.py, index.js, etc.)
        4. Config and initialization files
        
        Args:
            project_root: The project root path
            
        Returns:
            List of file paths
        """
        key_files = set()
        
        # Get recently accessed files
        recent_activities = file_activity_tracker.get_recent_activities(limit=20)
        for activity in recent_activities:
            file_path = Path(activity["path"])
            if file_path.exists() and file_path.is_file():
                key_files.add(file_path)
        
        # Get most active files
        active_files = file_activity_tracker.get_most_active_files(limit=20)
        for file_info in active_files:
            file_path = Path(file_info["path"])
            if file_path.exists() and file_path.is_file():
                key_files.add(file_path)
        
        # Find entry point files
        entry_point_patterns = [
            "main.py", "__main__.py", "app.py", "index.js", "server.js",
            "index.ts", "App.tsx", "App.jsx", "Main.java", "Program.cs"
        ]
        
        for pattern in entry_point_patterns:
            for file_path in project_root.glob(f"**/{pattern}"):
                if file_path.exists() and file_path.is_file():
                    key_files.add(file_path)
        
        # Find config and initialization files
        config_patterns = [
            "config.py", "settings.py", "constants.py", "__init__.py",
            "package.json", "tsconfig.json", ".eslintrc.js", "webpack.config.js",
            "Dockerfile", "docker-compose.yml", "requirements.txt", "pyproject.toml"
        ]
        
        for pattern in config_patterns:
            for file_path in project_root.glob(f"**/{pattern}"):
                if file_path.exists() and file_path.is_file():
                    key_files.add(file_path)
        
        # Limit to 100 files to avoid excessive analysis
        return list(key_files)[:100]
    
    async def get_enriched_context(self) -> Dict[str, Any]:
        """
        Get an enriched context dictionary with semantic information.
        
        Returns:
            Dictionary with enriched context information
        """
        project_root = context_manager.project_root
        if not project_root:
            return {"semantic_context_available": False}
        
        # Ensure we have up-to-date analysis
        await self.refresh_context()
        
        if str(project_root) not in self._analysis_cache:
            return {"semantic_context_available": False}
        
        # Get the analysis results
        analysis = self._analysis_cache[str(project_root)]
        
        # Get the current file
        current_file = context_manager.current_file
        current_file_entities = None
        
        if current_file and str(current_file) in self._project_modules.get(str(project_root), {}):
            module = self._project_modules[str(project_root)][str(current_file)]
            
            # Extract information about entities in the current file
            current_file_entities = {
                "functions": list(module.functions.keys()),
                "classes": list(module.classes.keys()),
                "imports": list(module.imports.keys()),
                "docstring": module.docstring
            }
        
        # Build the enriched context
        return {
            "semantic_context_available": True,
            "project_semantic_info": {
                "analyzed_files": analysis["semantic_analysis"]["analyzed_files_count"],
                "entity_counts": analysis["semantic_analysis"]["entities"],
                "key_metrics": {
                    "total_lines": analysis["semantic_analysis"]["metrics"].get("total_lines", 0),
                    "function_count": analysis["semantic_analysis"]["metrics"].get("function_count", 0),
                    "class_count": analysis["semantic_analysis"]["metrics"].get("class_count", 0),
                    "average_function_complexity": analysis["semantic_analysis"]["metrics"].get("average_function_complexity", 0)
                }
            },
            "project_state": {
                "git": {
                    "current_branch": analysis["project_state"]["git_state"].get("current_branch"),
                    "has_changes": analysis["project_state"]["git_state"].get("has_changes", False),
                    "modified_files_count": len(analysis["project_state"]["git_state"].get("modified_files", [])),
                    "untracked_files_count": len(analysis["project_state"]["git_state"].get("untracked_files", []))
                },
                "tests": {
                    "framework": analysis["project_state"]["test_status"].get("framework"),
                    "test_files_count": analysis["project_state"]["test_status"].get("test_files_count", 0),
                    "coverage": analysis["project_state"]["test_status"].get("coverage", {}).get("percentage")
                },
                "dependencies": {
                    "count": analysis["project_state"]["dependencies"].get("dependencies_count", 0),
                    "outdated_count": len(analysis["project_state"]["dependencies"].get("outdated_packages", [])),
                    "package_manager": analysis["project_state"]["dependencies"].get("package_manager")
                },
                "code_quality": {
                    "linter": analysis["project_state"]["code_quality"].get("linter"),
                    "issues_count": analysis["project_state"]["code_quality"].get("issues_count", 0)
                },
                "todos_count": len(analysis["project_state"]["todo_items"])
            },
            "current_file_semantic": current_file_entities
        }
    
    async def track_entity_access(self, entity_name: str, file_path: Optional[Path] = None) -> None:
        """
        Track access to a code entity (function, class, etc.).
        
        Args:
            entity_name: Name of the entity being accessed
            file_path: Optional path to the file containing the entity
        """
        if not entity_name:
            return
        
        # If file_path is not provided, try to find it from the entity map
        if not file_path and entity_name in self._entity_map:
            file_path = Path(self._entity_map[entity_name])
        
        if not file_path:
            return
        
        # Add to recent entity usages
        timestamp = datetime.now().timestamp()
        self._recent_entity_usages.append({
            "entity_name": entity_name,
            "file_path": str(file_path),
            "timestamp": timestamp
        })
        
        # Keep only the most recent 100 usages
        if len(self._recent_entity_usages) > 100:
            self._recent_entity_usages = self._recent_entity_usages[-100:]
        
        # Also track file access at the file level
        file_activity_tracker.track_file_viewing(file_path, None, {
            "entity_name": entity_name,
            "entity_type": "code_entity",
            "timestamp": timestamp
        })
    
    async def get_entity_info(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a code entity.
        
        Args:
            entity_name: Name of the entity to look up
            
        Returns:
            Dictionary with entity information or None if not found
        """
        project_root = context_manager.project_root
        if not project_root:
            return None
        
        # Ensure the context is refreshed
        await self.refresh_context()
        
        # Check if the entity exists in our map
        if entity_name not in self._entity_map:
            return None
        
        file_path = self._entity_map[entity_name]
        
        # Track this entity access
        await self.track_entity_access(entity_name, Path(file_path))
        
        # Get the module
        if str(project_root) not in self._project_modules or file_path not in self._project_modules[str(project_root)]:
            return None
        
        module = self._project_modules[str(project_root)][file_path]
        
        # Check if it's a function, class, or class method
        if "." in entity_name:
            # Class method
            class_name, method_name = entity_name.split(".", 1)
            
            if class_name in module.classes and method_name in module.classes[class_name].methods:
                method = module.classes[class_name].methods[method_name]
                return {
                    "type": "method",
                    "name": method_name,
                    "class_name": class_name,
                    "file_path": file_path,
                    "line_start": method.line_start,
                    "line_end": method.line_end,
                    "params": method.params,
                    "docstring": method.docstring,
                    "return_type": method.return_type,
                    "complexity": method.complexity
                }
        
        elif entity_name in module.functions:
            # Function
            function = module.functions[entity_name]
            return {
                "type": "function",
                "name": entity_name,
                "file_path": file_path,
                "line_start": function.line_start,
                "line_end": function.line_end,
                "params": function.params,
                "docstring": function.docstring,
                "return_type": function.return_type,
                "complexity": function.complexity,
                "called_functions": function.called_functions
            }
        
        elif entity_name in module.classes:
            # Class
            cls = module.classes[entity_name]
            return {
                "type": "class",
                "name": entity_name,
                "file_path": file_path,
                "line_start": cls.line_start,
                "line_end": cls.line_end,
                "docstring": cls.docstring,
                "base_classes": cls.base_classes,
                "methods": list(cls.methods.keys()),
                "attributes": list(cls.attributes.keys())
            }
        
        return None
    
    async def find_related_code(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find code entities related to a natural language query.
        
        Args:
            query: Natural language query describing code functionality
            limit: Maximum number of results to return
            
        Returns:
            List of entity information dictionaries
        """
        project_root = context_manager.project_root
        if not project_root:
            return []
        
        # Ensure the context is refreshed
        await self.refresh_context()
        
        if str(project_root) not in self._project_modules:
            return []
        
        # Simple keyword matching for now
        # In a real implementation, you might use embedding-based similarity
        keywords = query.lower().split()
        matches = []
        
        # Search through all modules
        for file_path, module in self._project_modules[str(project_root)].items():
            # Search functions
            for func_name, func in module.functions.items():
                score = self._calculate_match_score(func, keywords)
                if score > 0:
                    matches.append({
                        "entity_name": func_name,
                        "type": "function",
                        "file_path": file_path,
                        "score": score,
                        "preview": func.docstring[:100] + "..." if func.docstring and len(func.docstring) > 100 else func.docstring,
                        "line": func.line_start
                    })
            
            # Search classes
            for class_name, cls in module.classes.items():
                score = self._calculate_match_score(cls, keywords)
                if score > 0:
                    matches.append({
                        "entity_name": class_name,
                        "type": "class",
                        "file_path": file_path,
                        "score": score,
                        "preview": cls.docstring[:100] + "..." if cls.docstring and len(cls.docstring) > 100 else cls.docstring,
                        "line": cls.line_start
                    })
                
                # Search class methods
                for method_name, method in cls.methods.items():
                    score = self._calculate_match_score(method, keywords)
                    if score > 0:
                        matches.append({
                            "entity_name": f"{class_name}.{method_name}",
                            "type": "method",
                            "file_path": file_path,
                            "score": score,
                            "preview": method.docstring[:100] + "..." if method.docstring and len(method.docstring) > 100 else method.docstring,
                            "line": method.line_start
                        })
        
        # Sort by score
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return matches[:limit]
    
    def _calculate_match_score(self, entity: Any, keywords: List[str]) -> float:
        """
        Calculate a match score between an entity and keywords.
        
        Args:
            entity: Code entity (function, class, etc.)
            keywords: List of keywords to match
            
        Returns:
            Score value where higher is better
        """
        score = 0.0
        
        # Check entity name
        name_words = entity.name.lower().split('_')
        for word in name_words:
            for keyword in keywords:
                if keyword in word:
                    score += 1.0 if keyword == word else 0.5
        
        # Check docstring
        if entity.docstring:
            for keyword in keywords:
                if keyword in entity.docstring.lower():
                    score += 0.3
        
        return score
    
    async def get_recent_entity_usages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recently used code entities.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of entity usage information
        """
        # Sort by timestamp (newest first)
        sorted_usages = sorted(
            self._recent_entity_usages, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )
        
        # Take only the most recent usage of each entity
        unique_entities = {}
        for usage in sorted_usages:
            entity_name = usage["entity_name"]
            if entity_name not in unique_entities:
                unique_entities[entity_name] = usage
                
                # Add entity information
                try:
                    entity_info = await self.get_entity_info(entity_name)
                    if entity_info:
                        unique_entities[entity_name]["info"] = entity_info
                except Exception:
                    pass
        
        # Convert to list and limit
        return list(unique_entities.values())[:limit]
    
    async def get_code_summary(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get a summary of the code in a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with code summary information
        """
        path_obj = Path(file_path)
        project_root = context_manager.project_root
        
        if not project_root:
            return {"error": "No project root detected"}
        
        # Ensure the context is refreshed
        await self.refresh_context()
        
        if str(project_root) not in self._project_modules:
            return {"error": "Project not analyzed"}
        
        # Get the module
        file_str = str(path_obj)
        if file_str not in self._project_modules[str(project_root)]:
            # Try to analyze the file now
            try:
                module = await semantic_analyzer.analyze_file(path_obj)
                if module:
                    self._project_modules[str(project_root)][file_str] = module
                else:
                    return {"error": "Failed to analyze file"}
            except Exception as e:
                return {"error": f"Error analyzing file: {str(e)}"}
        
        module = self._project_modules[str(project_root)][file_str]
        
        # Create a summary
        return {
            "file_path": file_str,
            "language": module.language,
            "docstring": module.docstring,
            "functions": [
                {
                    "name": name,
                    "params": func.params,
                    "docstring": func.docstring[:100] + "..." if func.docstring and len(func.docstring) > 100 else func.docstring,
                    "complexity": func.complexity
                }
                for name, func in module.functions.items()
            ],
            "classes": [
                {
                    "name": name,
                    "docstring": cls.docstring[:100] + "..." if cls.docstring and len(cls.docstring) > 100 else cls.docstring,
                    "methods_count": len(cls.methods),
                    "attributes_count": len(cls.attributes),
                    "base_classes": cls.base_classes
                }
                for name, cls in module.classes.items()
            ],
            "imports": len(module.imports),
            "metrics": module.code_metrics
        }
    
    async def get_project_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current project.
        
        Returns:
            Dictionary with project summary information
        """
        project_root = context_manager.project_root
        if not project_root:
            return {"error": "No project root detected"}
        
        # Ensure the context is refreshed
        await self.refresh_context()
        
        if str(project_root) not in self._analysis_cache:
            return {"error": "Project not analyzed"}
        
        # Get the analysis results
        analysis = self._analysis_cache[str(project_root)]
        
        # Build a detailed project summary
        return {
            "project_root": str(project_root),
            "project_type": analysis["project_state"].get("project_type", "unknown"),
            "git_info": {
                "current_branch": analysis["project_state"]["git_state"].get("current_branch"),
                "is_git_repo": analysis["project_state"]["git_state"].get("is_git_repo", False),
                "has_changes": analysis["project_state"]["git_state"].get("has_changes", False),
                "modified_files": analysis["project_state"]["git_state"].get("modified_files", []),
                "untracked_files": analysis["project_state"]["git_state"].get("untracked_files", []),
                "recent_commits": analysis["project_state"]["git_state"].get("recent_commits", [])
            },
            "test_info": {
                "framework": analysis["project_state"]["test_status"].get("framework"),
                "test_files_count": analysis["project_state"]["test_status"].get("test_files_count", 0),
                "coverage": analysis["project_state"]["test_status"].get("coverage", {}).get("percentage")
            },
            "build_info": {
                "system": analysis["project_state"]["build_status"].get("system"),
                "last_build": analysis["project_state"]["build_status"].get("last_build"),
                "artifacts_count": len(analysis["project_state"]["build_status"].get("artifacts", []))
            },
            "dependency_info": {
                "package_manager": analysis["project_state"]["dependencies"].get("package_manager"),
                "dependencies_count": analysis["project_state"]["dependencies"].get("dependencies_count", 0),
                "dev_dependencies_count": analysis["project_state"]["dependencies"].get("dev_dependencies_count", 0),
                "outdated_packages": analysis["project_state"]["dependencies"].get("outdated_packages", [])
            },
            "code_quality": {
                "linter": analysis["project_state"]["code_quality"].get("linter"),
                "formatter": analysis["project_state"]["code_quality"].get("formatter"),
                "issues_count": analysis["project_state"]["code_quality"].get("issues_count", 0)
            },
            "todo_items": analysis["project_state"]["todo_items"][:5],  # Include only the first 5 for brevity
            "semantic_stats": {
                "analyzed_files": analysis["semantic_analysis"]["analyzed_files_count"],
                "functions": analysis["semantic_analysis"]["entities"]["functions"],
                "classes": analysis["semantic_analysis"]["entities"]["classes"],
                "total_lines": analysis["semantic_analysis"]["metrics"].get("total_lines", 0),
                "avg_func_complexity": analysis["semantic_analysis"]["metrics"].get("average_function_complexity", 0)
            }
        }

# Global semantic context manager instance
semantic_context_manager = SemanticContextManager()
