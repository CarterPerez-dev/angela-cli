# angela/integrations/semantic_integration.py
"""
Semantic integration module for Angela CLI.

This module ties together the various semantic analysis components and
integrates them into Angela's workflow, making semantic code understanding
available to all parts of the application.
"""
import asyncio
from typing import Dict, Any, List, Optional, Union, Set
from pathlib import Path

from angela.utils.logging import get_logger
from angela.context import context_manager
from angela.context.file_activity import file_activity_tracker
from angela.context.project_state_analyzer import project_state_analyzer
from angela.ai.semantic_analyzer import semantic_analyzer
from angela.context.enhancer import context_enhancer
from angela.context.session import session_manager

logger = get_logger(__name__)

class SemanticIntegration:
    """
    Integration hub for semantic understanding features.
    
    This class coordinates the different semantic analysis components
    and makes their functionality available to the rest of the application.
    It serves as the main entry point for requesting semantic information.
    """
    
    def __init__(self):
        """Initialize the semantic integration."""
        self._logger = logger
        self._semantic_context_cache = {}  # Cache for semantic context
        self._analysis_in_progress = set()  # Set of files/projects currently being analyzed
        self._analysis_tasks = {}  # Background analysis tasks by file/project path
    
    async def get_semantic_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance the context with semantic information.
        
        Args:
            context: The base context dictionary
            
        Returns:
            Enhanced context with semantic information
        """
        # Create a new context with semantic information
        semantic_context = dict(context)
        
        # Get project root if available
        project_root = context.get("project_root")
        if not project_root:
            return semantic_context
        
        # Check if we have a file in focus
        current_file = context.get("current_file", {}).get("path")
        
        try:
            # Add project state information
            semantic_context["project_state"] = await self._get_project_state(project_root)
            
            # Add semantic code information if a file is in focus
            if current_file:
                semantic_context["semantic_code"] = await self._get_semantic_code(current_file)
            
            # Add information about recently accessed files
            recent_files = context.get("recent_files", {}).get("accessed", [])
            if recent_files:
                semantic_context["semantic_recent"] = await self._get_semantic_recent(recent_files[:5])
            
            # Add semantic context for active project entities
            semantic_context["semantic_entities"] = await self._get_semantic_entities(project_root)
            
            # Add function/class relationships
            if current_file and semantic_context.get("semantic_code", {}).get("entity_name"):
                entity_name = semantic_context["semantic_code"]["entity_name"]
                semantic_context["semantic_relationships"] = await self._get_semantic_relationships(project_root, entity_name)
            
            return semantic_context
            
        except Exception as e:
            self._logger.error(f"Error getting semantic context: {str(e)}")
            return semantic_context
    
    async def _get_project_state(self, project_root: str) -> Dict[str, Any]:
        """
        Get project state information.
        
        Args:
            project_root: Path to the project root
            
        Returns:
            Project state information
        """
        # Start a background analysis task if not already in progress
        if project_root not in self._analysis_in_progress:
            self._schedule_background_analysis(project_root)
        
        # Get state information (cached or real-time)
        try:
            state_info = await project_state_analyzer.get_project_state(project_root)
            
            # Extract the most important information for the context
            summary = {
                "git": {
                    "branch": state_info.get("git_state", {}).get("current_branch"),
                    "has_changes": state_info.get("git_state", {}).get("has_changes", False),
                    "changed_files_count": len(state_info.get("git_state", {}).get("modified_files", [])) +
                                          len(state_info.get("git_state", {}).get("untracked_files", [])),
                },
                "tests": {
                    "framework": state_info.get("test_status", {}).get("framework"),
                    "count": state_info.get("test_status", {}).get("test_files_count", 0),
                    "coverage": state_info.get("test_status", {}).get("coverage", {}).get("percentage")
                },
                "dependencies": {
                    "package_manager": state_info.get("dependencies", {}).get("package_manager"),
                    "count": state_info.get("dependencies", {}).get("dependencies_count", 0),
                    "outdated_count": len(state_info.get("dependencies", {}).get("outdated_packages", []))
                },
                "build": {
                    "system": state_info.get("build_status", {}).get("system"),
                    "last_build": state_info.get("build_status", {}).get("last_build")
                },
                "code_quality": {
                    "linter": state_info.get("code_quality", {}).get("linter"),
                    "issues_count": state_info.get("code_quality", {}).get("issues_count", 0)
                },
                "todo_count": len(state_info.get("todo_items", []))
            }
            
            return summary
            
        except Exception as e:
            self._logger.error(f"Error getting project state: {str(e)}")
            return {}
    
    async def _get_semantic_code(self, file_path: str) -> Dict[str, Any]:
        """
        Get semantic information about a code file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Semantic code information
        """
        try:
            # Start a background analysis task if not already in progress
            if file_path not in self._analysis_in_progress:
                self._schedule_background_analysis(file_path, is_file=True)
            
            # Get the module information from semantic analyzer
            module = await semantic_analyzer.analyze_file(file_path)
            
            if not module:
                return {}
            
            # Extract important information for the context
            result = {
                "language": module.language,
                "docstring": module.docstring,
                "functions": list(module.functions.keys()),
                "classes": list(module.classes.keys()),
                "imports": list(module.imports.keys()),
                "code_metrics": module.code_metrics
            }
            
            # If current cursor position is known, try to determine the entity at cursor
            cursor_line = context_manager.get_context_dict().get("cursor_line")
            if cursor_line:
                entity = self._find_entity_at_line(module, cursor_line)
                if entity:
                    result["entity_name"] = entity.name
                    result["entity_type"] = entity.__class__.__name__.lower()
                    result["entity_line_start"] = entity.line_start
                    result["entity_line_end"] = entity.line_end
                    
                    # Add entity-specific information
                    if result["entity_type"] == "function":
                        result["function_params"] = entity.params
                        result["function_docstring"] = entity.docstring
                        result["function_return_type"] = entity.return_type
                        result["function_complexity"] = entity.complexity
                    elif result["entity_type"] == "class":
                        result["class_bases"] = entity.base_classes
                        result["class_methods"] = list(entity.methods.keys())
                        result["class_attributes"] = list(entity.attributes.keys())
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error getting semantic code information: {str(e)}")
            return {}
    
    def _find_entity_at_line(self, module, line_number: int):
        """Find the entity at a specific line number."""
        # Check functions
        for func in module.functions.values():
            if func.line_start <= line_number <= func.line_end:
                return func
        
        # Check classes
        for cls in module.classes.values():
            if cls.line_start <= line_number <= cls.line_end:
                # Check if we're in a method of this class
                for method in cls.methods.values():
                    if method.line_start <= line_number <= method.line_end:
                        return method
                return cls
        
        # Check variables
        for var in module.variables.values():
            if var.line_start <= line_number <= var.line_end:
                return var
        
        return None
    
    async def _get_semantic_recent(self, recent_files: List[str]) -> Dict[str, Any]:
        """
        Get semantic information about recently accessed files.
        
        Args:
            recent_files: List of recently accessed file paths
            
        Returns:
            Semantic information about recent files
        """
        result = {}
        
        for file_path in recent_files:
            try:
                # Schedule background analysis if needed
                if file_path not in self._analysis_in_progress:
                    self._schedule_background_analysis(file_path, is_file=True)
                
                # Get module information
                module = await semantic_analyzer.analyze_file(file_path)
                
                if module:
                    # Get file summary
                    result[file_path] = module.get_summary()
            except Exception as e:
                self._logger.error(f"Error analyzing recent file {file_path}: {str(e)}")
        
        return result
    
    async def _get_semantic_entities(self, project_root: str) -> Dict[str, Any]:
        """
        Get semantic information about important entities in the project.
        
        Args:
            project_root: Path to the project root
            
        Returns:
            Semantic information about important project entities
        """
        # Extract entities from session
        entities = session_manager.get_context().get("entities", {})
        
        result = {
            "current_focus": [],
            "important_functions": [],
            "important_classes": []
        }
        
        # Find entities that the user has interacted with
        entity_names = set()
        for entity_name, entity_info in entities.items():
            if entity_info.get("type") == "function" or entity_info.get("type") == "class" or entity_info.get("type") == "method":
                entity_names.add(entity_info.get("value"))
        
        # Get recently viewed files
        recent_activities = file_activity_tracker.get_recent_activities(activity_types=["viewed"])
        recent_files = [activity.get("path") for activity in recent_activities]
        
        # Analyze recently viewed files to find important entities
        for file_path in recent_files[:5]:  # Limit to 5 most recent files
            try:
                module = await semantic_analyzer.analyze_file(file_path)
                
                if not module:
                    continue
                
                # Add functions and classes to the result
                for func_name, func in module.functions.items():
                    if func_name in entity_names:
                        result["current_focus"].append({
                            "name": func_name,
                            "type": "function",
                            "file": file_path,
                            "line": func.line_start
                        })
                    elif func.complexity and func.complexity > 5:  # Complex functions
                        result["important_functions"].append({
                            "name": func_name,
                            "file": file_path,
                            "complexity": func.complexity,
                            "line": func.line_start
                        })
                
                for class_name, cls in module.classes.items():
                    if class_name in entity_names:
                        result["current_focus"].append({
                            "name": class_name,
                            "type": "class",
                            "file": file_path,
                            "line": cls.line_start,
                            "method_count": len(cls.methods)
                        })
                    elif len(cls.methods) > 5:  # Classes with many methods
                        result["important_classes"].append({
                            "name": class_name,
                            "file": file_path,
                            "method_count": len(cls.methods),
                            "line": cls.line_start
                        })
            except Exception as e:
                self._logger.error(f"Error analyzing entities in {file_path}: {str(e)}")
        
        # Sort important entities by complexity/size
        result["important_functions"] = sorted(
            result["important_functions"], 
            key=lambda f: f.get("complexity", 0), 
            reverse=True
        )[:5]  # Limit to top 5
        
        result["important_classes"] = sorted(
            result["important_classes"], 
            key=lambda c: c.get("method_count", 0), 
            reverse=True
        )[:5]  # Limit to top 5
        
        return result
    
    async def _get_semantic_relationships(self, project_root: str, entity_name: str) -> Dict[str, Any]:
        """
        Get semantic relationship information for a specific entity.
        
        Args:
            project_root: Path to the project root
            entity_name: Name of the entity
            
        Returns:
            Semantic relationship information
        """
        try:
            # Get entity usage information
            usage_info = await semantic_analyzer.analyze_entity_usage(entity_name, project_root)
            
            if not usage_info.get("found", False):
                return {}
            
            # Extract relationship information
            result = {
                "type": usage_info.get("type"),
                "callers": [],
                "callees": [],
                "related_entities": []
            }
            
            # Process related entities
            related = usage_info.get("related_entities", [])
            
            for entity in related:
                rel_type = entity.get("relationship")
                
                if rel_type == "calls":
                    result["callers"].append({
                        "name": entity.get("name"),
                        "file": entity.get("filename"),
                        "line": entity.get("line")
                    })
                elif rel_type == "called_by":
                    result["callees"].append({
                        "name": entity.get("name"),
                        "file": entity.get("filename"),
                        "line": entity.get("line")
                    })
                else:
                    result["related_entities"].append({
                        "name": entity.get("name"),
                        "type": entity.get("type"),
                        "relationship": rel_type,
                        "file": entity.get("filename"),
                        "line": entity.get("line")
                    })
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error getting relationships for {entity_name}: {str(e)}")
            return {}
    
    def _schedule_background_analysis(self, path: str, is_file: bool = False):
        """
        Schedule a background analysis task.
        
        Args:
            path: Path to the file or project
            is_file: Whether the path is a file or project
        """
        if path in self._analysis_in_progress:
            return
        
        self._analysis_in_progress.add(path)
        
        async def _run_analysis():
            try:
                if is_file:
                    await semantic_analyzer.analyze_file(path)
                else:
                    await project_state_analyzer.get_project_state(path)
            except Exception as e:
                self._logger.error(f"Error in background analysis for {path}: {str(e)}")
            finally:
                self._analysis_in_progress.remove(path)
        
        # Create and store the task
        task = asyncio.create_task(_run_analysis())
        self._analysis_tasks[path] = task
        
        # Remove the task when it's done
        def _clean_up(task):
            if path in self._analysis_tasks:
                del self._analysis_tasks[path]
        
        task.add_done_callback(_clean_up)
    
    async def get_entity_summary(self, entity_name: str, project_root: Optional[str] = None) -> str:
        """
        Get a natural language summary of a code entity.
        
        Args:
            entity_name: Name of the entity to summarize
            project_root: Path to the project root (optional)
            
        Returns:
            Natural language summary
        """
        if not project_root:
            project_root = context_manager.project_root
            
        if not project_root:
            return f"Cannot generate summary: No project root specified and none detected."
        
        return await semantic_analyzer.summarize_code_entity(entity_name, project_root)
    
    async def get_code_suggestions(self, file_path: str, line_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get code improvement suggestions for a file.
        
        Args:
            file_path: Path to the file
            line_number: Optional line number to focus on
            
        Returns:
            List of improvement suggestions
        """
        try:
            # First, analyze the file
            module = await semantic_analyzer.analyze_file(file_path)
            
            if not module:
                return []
            
            # Find entity at line number if specified
            entity = None
            if line_number:
                entity = self._find_entity_at_line(module, line_number)
            
            # Get the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create suggestions based on analysis
            suggestions = []
            
            # Entity-specific suggestions
            if entity:
                if hasattr(entity, 'complexity') and entity.complexity > 10:
                    suggestions.append({
                        "type": "complexity",
                        "severity": "medium",
                        "message": f"Function '{entity.name}' has high complexity ({entity.complexity}). Consider refactoring.",
                        "line": entity.line_start,
                        "entity": entity.name
                    })
                
                if hasattr(entity, 'docstring') and not entity.docstring:
                    suggestions.append({
                        "type": "documentation",
                        "severity": "low",
                        "message": f"Add docstring to {entity.__class__.__name__.lower()} '{entity.name}'.",
                        "line": entity.line_start,
                        "entity": entity.name
                    })
                
                if hasattr(entity, 'params') and len(entity.params) > 5:
                    suggestions.append({
                        "type": "parameters",
                        "severity": "low",
                        "message": f"Function '{entity.name}' has many parameters ({len(entity.params)}). Consider grouping them.",
                        "line": entity.line_start,
                        "entity": entity.name
                    })
            
            # General file suggestions
            if len(module.functions) > 10:
                suggestions.append({
                    "type": "structure",
                    "severity": "low",
                    "message": f"File has {len(module.functions)} functions. Consider splitting into multiple modules.",
                    "line": 1,
                    "file": file_path
                })
            
            if module.code_metrics.get("blank_ratio", 0) < 0.1:
                suggestions.append({
                    "type": "readability",
                    "severity": "low",
                    "message": "Low blank line ratio. Add more whitespace to improve readability.",
                    "line": 1,
                    "file": file_path
                })
            
            if module.code_metrics.get("comment_ratio", 0) < 0.1:
                suggestions.append({
                    "type": "documentation",
                    "severity": "low",
                    "message": "Low comment ratio. Add more comments to improve maintainability.",
                    "line": 1,
                    "file": file_path
                })
            
            # Check for long lines
            lines = content.split('\n')
            long_lines = []
            for i, line in enumerate(lines, 1):
                if len(line) > 100:
                    long_lines.append(i)
            
            if long_lines:
                suggestions.append({
                    "type": "style",
                    "severity": "low",
                    "message": f"File contains {len(long_lines)} lines longer than 100 characters.",
                    "lines": long_lines[:5],  # List up to 5 problematic lines
                    "file": file_path
                })
            
            return suggestions
            
        except Exception as e:
            self._logger.error(f"Error getting code suggestions: {str(e)}")
            return []
    
    async def find_similar_code(self, code_snippet: str, project_root: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find similar code in the project.
        
        Args:
            code_snippet: Code snippet to search for
            project_root: Path to the project root (optional)
            
        Returns:
            List of similar code snippets
        """
        if not project_root:
            project_root = context_manager.project_root
            
        if not project_root:
            return []
        
        # TODO: Implement semantic code similarity search
        # This would require more advanced techniques beyond the scope of this example
        # Could use embeddings, AST comparison, or other similarity metrics
        
        # For now, return a placeholder
        return [
            {
                "file": "placeholder.py",
                "similarity": 0.8,
                "code": "print('This is a placeholder')",
                "line": 1
            }
        ]

# Global instance of semantic integration
semantic_integration = SemanticIntegration()

# Add to context enhancer
async def enhance_context_with_semantics(context: Dict[str, Any]) -> Dict[str, Any]:
    """Context enhancer function for semantic information."""
    return await semantic_integration.get_semantic_context(context)

# Register with context_enhancer
context_enhancer.register_enhancer(enhance_context_with_semantics)
