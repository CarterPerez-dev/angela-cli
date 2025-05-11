# angela/context/enhancer.py
"""
Enhanced project context management for Angela CLI.

This module provides advanced context enrichment by integrating project inference,
dependency detection, and file activity tracking to provide a richer context
for AI interactions.
"""
import asyncio
from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
from pathlib import Path

# Non-circular imports can remain at the top level
from angela.config import config_manager
from angela.utils.logging import get_logger
from angela.api.context import get_project_inference, get_file_activity_tracker, get_file_resolver

logger = get_logger(__name__)

class ContextEnhancer:
    """
    Enhanced context manager that enriches context with project information,
    dependency detection, and recent activity tracking.
    """
    
    def __init__(self):
        """Initialize the context enhancer."""
        self._logger = logger
        self._project_info_cache = {}  # Cache project info by path
        self._file_activity_cache = {}  # Cache recent file activity
        self._enhancers: List[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = []
    
    async def enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich the context with additional information.
        
        Args:
            context: The base context to enrich
            
        Returns:
            The enriched context
        """
        self._logger.debug("Enriching context with additional information")
        
        # Start with a copy of the original context
        enriched = dict(context)
        
        try:
            # Add enhanced project information if in a project
            if context.get("project_root"):
                await self._add_project_info(enriched, context["project_root"])
            
            # Add recent file activity
            await self._add_recent_file_activity(enriched)
            
            # Add file reference context
            await self._add_file_reference_context(enriched)
            
            # Add enhanced file activity information 
            file_activity_tracker = get_file_activity_tracker()
            
            try:
                # Get ActivityType enum
                from angela.api.context import get_activity_type
                ActivityType = get_activity_type()
                
                # Get recent file activities by types
                viewed_activities = file_activity_tracker.get_recent_activities(
                    limit=5, 
                    activity_types=[ActivityType.VIEWED]
                )
                modified_activities = file_activity_tracker.get_recent_activities(
                    limit=5, 
                    activity_types=[ActivityType.MODIFIED]
                )
                created_activities = file_activity_tracker.get_recent_activities(
                    limit=5, 
                    activity_types=[ActivityType.CREATED]
                )
                
                # Extract paths from activities
                viewed_files = [activity.get('path', '') for activity in viewed_activities if 'path' in activity]
                modified_files = [activity.get('path', '') for activity in modified_activities if 'path' in activity]
                created_files = [activity.get('path', '') for activity in created_activities if 'path' in activity]
                
                # Update or create recent_files
                if "recent_files" not in enriched:
                    enriched["recent_files"] = {}
                    
                enriched["recent_files"].update({
                    "accessed": viewed_files,
                    "modified": modified_files,
                    "created": created_files,
                })
                
                # Get most active files
                most_active = file_activity_tracker.get_most_active_files(limit=5)
                enriched["active_files"] = most_active
            except Exception as e:
                self._logger.warning(f"Error getting file activity: {str(e)}")
            
            # Add file resolver information if available
            if "requested_file" in context:
                file_resolver = get_file_resolver()
                
                try:
                    resolved_files = await file_resolver.resolve_file_references(
                        context.get("cwd", ""),
                        context.get("project_root", ""),
                        [context["requested_file"]]
                    )
                    
                    if resolved_files:
                        enriched["resolved_files"] = resolved_files
                except Exception as e:
                    self._logger.warning(f"Error resolving file references: {str(e)}")
            
            # Run all registered enhancers
            for enhancer in self._enhancers:
                try:
                    result = await enhancer(enriched)
                    if result:
                        enriched.update(result)
                except Exception as e:
                    self._logger.error(f"Error in enhancer {getattr(enhancer, '__name__', 'anonymous')}: {str(e)}")
            
            self._logger.debug(f"Context enriched with {len(enriched) - len(context)} additional keys")
        except Exception as e:
            self._logger.error(f"Error enriching context: {str(e)}")
            # Return what we have so far
        
        return enriched
    
    async def _add_project_info(self, context: Dict[str, Any], project_root: str) -> None:
        """
        Add enhanced project information to the context.
        
        Args:
            context: The context to enrich
            project_root: The path to the project root
        """
        # Get project_inference from API
        project_inference = get_project_inference()
        
        self._logger.debug(f"Adding project info for {project_root}")
        
        try:
            # Check cache first
            if project_root in self._project_info_cache:
                project_info = self._project_info_cache[project_root]
                self._logger.debug(f"Using cached project info for {project_root}")
            else:
                # Get project info from project_inference
                project_info = await project_inference.infer_project_info(Path(project_root))
                # Cache the result
                self._project_info_cache[project_root] = project_info
                self._logger.debug(f"Inferred project info for {project_root}")
            
            # Add project info to context
            context["enhanced_project"] = {
                "type": project_info.get("project_type", "unknown"),
                "frameworks": project_info.get("detected_frameworks", {}),
                "dependencies": self._format_dependencies(project_info.get("dependencies", [])),
                "important_files": self._format_important_files(project_info.get("detected_files", [])),
                "structure": self._summarize_structure(project_info.get("structure", {}))
            }
            
            self._logger.debug(f"Added enhanced project info to context: {context['enhanced_project']['type']}")
        except Exception as e:
            self._logger.error(f"Error adding project info: {str(e)}")
    
    def _format_dependencies(self, dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format dependencies for inclusion in context.
        
        Args:
            dependencies: List of dependency information
            
        Returns:
            Formatted dependency information
        """
        # Group dependencies by type
        dependency_types = {}
        
        for dep in dependencies:
            dep_type = dep.get("type", "unknown")
            if dep_type not in dependency_types:
                dependency_types[dep_type] = []
            
            dependency_types[dep_type].append({
                "name": dep.get("name", "unknown"),
                "version": dep.get("version_spec", "")
            })
        
        # Return summary with counts
        return {
            "types": list(dependency_types.keys()),
            "counts": {t: len(deps) for t, deps in dependency_types.items()},
            "total": len(dependencies),
            "top_dependencies": [d.get("name", "unknown") for d in dependencies[:10]]
        }
    
    def _format_important_files(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format important files for inclusion in context.
        
        Args:
            files: List of important file information
            
        Returns:
            Formatted important file information
        """
        # Group files by type
        file_types = {}
        paths = []
        
        for file in files:
            file_type = file.get("type", "unknown")
            if file_type not in file_types:
                file_types[file_type] = []
            
            file_types[file_type].append(file.get("path", "unknown"))
            paths.append(file.get("path", "unknown"))
        
        # Return summary
        return {
            "types": list(file_types.keys()),
            "counts": {t: len(files) for t, files in file_types.items()},
            "total": len(files),
            "paths": paths
        }
    
    def _summarize_structure(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize project structure for inclusion in context.
        
        Args:
            structure: Project structure information
            
        Returns:
            Summarized structure information
        """
        # Extract key information from structure
        if not structure:
            return {}
        
        # Handle case where main_directories is a list of strings instead of dictionaries
        main_directories = structure.get("main_directories", [])
        
        # Convert to proper format if needed
        main_dirs_list = []
        for directory in main_directories:
            if isinstance(directory, dict):
                main_dirs_list.append(directory.get("name", ""))
            elif isinstance(directory, str):
                main_dirs_list.append(directory)
        
        # Return summary
        return {
            "file_counts": structure.get("file_counts", {}),
            "total_files": structure.get("total_files", 0),
            "main_directories": main_dirs_list
        }
    
    async def _add_recent_file_activity(self, context: Dict[str, Any]) -> None:
        """
        Add recent file activity to the context.
        
        Args:
            context: The context to enrich
        """
        # Get session_manager from API
        from angela.api.context import get_session_manager
        session_manager = get_session_manager()
        
        self._logger.debug("Adding recent file activity to context")
        
        try:
            # Get recent file activities from session
            session = session_manager.get_context()
            entities = session.get("entities", {})
            
            # Filter for file-related entities
            file_entities = {
                name: entity for name, entity in entities.items()
                if entity.get("type") in ["file", "directory", "recent_file"]
            }
            
            # Extract accessed files from entities
            accessed_files = []
            for name, entity in file_entities.items():
                if "value" in entity and entity["value"]:
                    accessed_files.append(entity["value"])
            
            # Always ensure we have at least an empty list
            recent_activities = []
            
            # Format and add to context
            context["recent_files"] = {
                "accessed": accessed_files,
                "activities": recent_activities,
                "count": len(file_entities)
            }
            
            self._logger.debug(f"Added {len(file_entities)} recent files to context")
        except Exception as e:
            self._logger.error(f"Error adding recent file activity: {str(e)}")
            # IMPORTANT: Add an empty recent_files object to context even on failure
            context["recent_files"] = {
                "accessed": [],
                "activities": [],
                "count": 0
            }
    
    async def _add_file_reference_context(self, context: Dict[str, Any]) -> None:
        """
        Add file reference context information.
        
        Args:
            context: The context to enrich
        """
        self._logger.debug("Adding file reference context")
        
        try:
            # Get current working directory
            cwd = context.get("cwd", "")
            if not cwd:
                return
            
            # List files in the current directory
            cwd_path = Path(cwd)
            files = list(cwd_path.glob("*"))
            
            # Format file information
            file_info = {
                "files": [f.name for f in files if f.is_file()],
                "directories": [f.name for f in files if f.is_dir()],
                "total": len(files)
            }
            
            # Add to context
            context["file_reference"] = file_info
            
            self._logger.debug(f"Added file reference context with {len(files)} files")
        except Exception as e:
            self._logger.error(f"Error adding file reference context: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear the context enhancer cache."""
        self._logger.debug("Clearing context enhancer cache")
        self._project_info_cache.clear()
        self._file_activity_cache.clear()

    def register_enhancer(self, enhancer_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]) -> None:
        """
        Register a context enhancer function.
        
        Args:
            enhancer_func: Async function that takes a context dict and returns an enhanced context dict
        """
        self._logger.debug(f"Registering context enhancer: {enhancer_func.__name__ if hasattr(enhancer_func, '__name__') else 'anonymous'}")
        self._enhancers.append(enhancer_func)


# Global context enhancer instance
try:
    # Initialize the ContextEnhancer instance
    context_enhancer = ContextEnhancer()
    logger.debug(f"context_enhancer initialized: {context_enhancer}")
except Exception as e:
    logger.error(f"Failed to initialize context_enhancer: {e}")
    # Create a new instance with better error handling
    try:
        logger.debug("Attempting to create a new instance of ContextEnhancer")
        context_enhancer = ContextEnhancer()
        logger.debug(f"Successfully created a new instance: {context_enhancer}")
    except Exception as inner_e:
        logger.critical(f"Critical failure initializing context_enhancer: {inner_e}")
        # Create minimally functional instance to avoid further errors
        context_enhancer = ContextEnhancer()
