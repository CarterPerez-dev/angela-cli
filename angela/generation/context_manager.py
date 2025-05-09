# angela/generation/context_manager.py
"""
Multi-file context management for code generation.

This module provides tools for managing context across multiple files during code generation,
ensuring coherence and proper dependency management.
"""
import asyncio
from typing import Dict, Any, List, Optional, Set, Union, Tuple
from pathlib import Path
import json
import re
from collections import defaultdict

from angela.utils.logging import get_logger
from angela.generation.engine import CodeFile
from angela.ai.client import gemini_client, GeminiRequest
from angela.context.file_detector import detect_file_type

logger = get_logger(__name__)

class GenerationContextManager:
    """
    Manages context across multiple files during code generation.
    
    This class tracks relationships, shared entities, and dependencies across
    files to ensure generated code remains coherent and consistent.
    """
    
    def __init__(self):
        """Initialize the generation context manager."""
        self._logger = logger
        self._shared_entities = {}  # Maps entity names to their types and definitions
        self._file_dependencies = defaultdict(set)  # Maps file paths to their dependencies
        self._import_statements = defaultdict(set)  # Maps file paths to their imports
        self._global_context = {}  # Shared context for the entire project
        self._modules = defaultdict(dict)  # Maps module names to their exported entities
        self._api_endpoints = []  # List of API endpoints for backend projects
        self._database_models = []  # List of database models
        self._ui_components = []  # List of UI components for frontend projects
        self._entity_references = defaultdict(list)  # Maps entity names to where they're referenced
        
    def reset(self):
        """Reset all context data."""
        self._shared_entities.clear()
        self._file_dependencies.clear()
        self._import_statements.clear()
        self._global_context.clear()
        self._modules.clear()
        self._api_endpoints.clear()
        self._database_models.clear()
        self._ui_components.clear()
        self._entity_references.clear()
        
    def register_entity(self, name: str, entity_type: str, definition: Any, file_path: str):
        """
        Register a shared entity that might be used across files.
        
        Args:
            name: Name of the entity
            entity_type: Type of entity (e.g., 'class', 'function', 'interface')
            definition: Definition or details of the entity
            file_path: Path to the file where the entity is defined
        """
        self._logger.debug(f"Registering entity: {name} ({entity_type}) in {file_path}")
        
        self._shared_entities[name] = {
            'type': entity_type,
            'definition': definition,
            'file_path': file_path
        }
        
        # Add to specific collections based on type
        if entity_type == 'api_endpoint':
            self._api_endpoints.append({
                'name': name,
                'path': definition.get('path', ''),
                'method': definition.get('method', ''),
                'handler': definition.get('handler', '')
            })
        elif entity_type == 'database_model':
            self._database_models.append({
                'name': name,
                'fields': definition.get('fields', {}),
                'relationships': definition.get('relationships', [])
            })
        elif entity_type == 'ui_component':
            self._ui_components.append({
                'name': name,
                'props': definition.get('props', {}),
                'description': definition.get('description', '')
            })
            
        # Add to module exports if applicable
        module_path = Path(file_path).parent.name
        if module_path:
            self._modules[module_path][name] = {
                'type': entity_type,
                'file_path': file_path
            }
            
    def register_dependency(self, file_path: str, dependency_path: str):
        """
        Register a dependency between files.
        
        Args:
            file_path: Path to the dependent file
            dependency_path: Path to the file being depended on
        """
        self._file_dependencies[file_path].add(dependency_path)
        
    def register_import(self, file_path: str, import_statement: str):
        """
        Register an import statement in a file.
        
        Args:
            file_path: Path to the file
            import_statement: The import statement
        """
        self._import_statements[file_path].add(import_statement)
        
    def register_entity_reference(self, entity_name: str, file_path: str, position: Optional[str] = None):
        """
        Register a reference to an entity in a file.
        
        Args:
            entity_name: Name of the entity
            file_path: Path to the file where the entity is referenced
            position: Optional position information
        """
        self._entity_references[entity_name].append({
            'file_path': file_path,
            'position': position
        })
        
    def get_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered entity.
        
        Args:
            name: Name of the entity
            
        Returns:
            Dictionary with entity information or None if not found
        """
        return self._shared_entities.get(name)
        
    def get_dependencies(self, file_path: str) -> Set[str]:
        """
        Get dependencies for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Set of dependency file paths
        """
        return self._file_dependencies.get(file_path, set())
        
    def get_imports(self, file_path: str) -> Set[str]:
        """
        Get import statements for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Set of import statements
        """
        return self._import_statements.get(file_path, set())
        
    def set_global_context(self, key: str, value: Any):
        """
        Set a global context value.
        
        Args:
            key: Context key
            value: Context value
        """
        self._global_context[key] = value
        
    def get_global_context(self, key: str, default: Any = None) -> Any:
        """
        Get a global context value.
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self._global_context.get(key, default)
        
    def get_all_global_context(self) -> Dict[str, Any]:
        """
        Get all global context.
        
        Returns:
            Dictionary with all global context
        """
        return self._global_context.copy()
        
    def get_modules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all modules and their exports.
        
        Returns:
            Dictionary mapping module names to exports
        """
        return self._modules.copy()
        
    def get_api_endpoints(self) -> List[Dict[str, Any]]:
        """
        Get all API endpoints.
        
        Returns:
            List of API endpoint dictionaries
        """
        return self._api_endpoints.copy()
        
    def get_database_models(self) -> List[Dict[str, Any]]:
        """
        Get all database models.
        
        Returns:
            List of database model dictionaries
        """
        return self._database_models.copy()
        
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """
        Get all UI components.
        
        Returns:
            List of UI component dictionaries
        """
        return self._ui_components.copy()
        
    def get_references(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get references to an entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            List of references
        """
        return self._entity_references.get(entity_name, [])
        
    async def extract_entities_from_file(self, file: CodeFile) -> List[Dict[str, Any]]:
        """
        Extract entities from a file.
        
        Args:
            file: CodeFile to extract entities from
            
        Returns:
            List of extracted entities
        """
        self._logger.debug(f"Extracting entities from {file.path}")
        
        # Determine file type
        file_type = detect_file_type(Path(file.path))
        language = file_type.get("language", "unknown")
        
        # Extract entities based on language
        entities = []
        
        if language == "python":
            entities = self._extract_python_entities(file.content, file.path)
        elif language in ["javascript", "typescript"]:
            entities = self._extract_js_entities(file.content, file.path, language == "typescript")
        elif language in ["java"]:
            entities = self._extract_java_entities(file.content, file.path)
        
        # Register extracted entities
        for entity in entities:
            self.register_entity(
                entity["name"],
                entity["type"],
                entity["definition"],
                file.path
            )
            
        return entities
        
    def _extract_python_entities(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract entities from Python code.
        
        Args:
            content: File content
            file_path: Path to the file
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\(.*?\))?:'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            
            # Check if it might be a database model
            if "model" in file_path.lower() or "models" in file_path.lower() or "db" in file_path.lower():
                if "Base" in content or "Model" in content or "Column" in content:
                    # Extract fields
                    fields = {}
                    field_pattern = r'(\w+)\s*=\s*(?:Column|db\.Column)\(([^)]*)\)'
                    for field_match in re.finditer(field_pattern, content):
                        field_name = field_match.group(1)
                        field_type = field_match.group(2)
                        fields[field_name] = field_type
                    
                    entities.append({
                        "name": class_name,
                        "type": "database_model",
                        "definition": {
                            "fields": fields,
                            "relationships": []  # Would need more complex parsing for relationships
                        }
                    })
                else:
                    entities.append({
                        "name": class_name,
                        "type": "class",
                        "definition": {
                            "methods": []  # Could extract methods if needed
                        }
                    })
            else:
                entities.append({
                    "name": class_name,
                    "type": "class",
                    "definition": {
                        "methods": []  # Could extract methods if needed
                    }
                })
        
        # Extract functions
        function_pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            # Skip if it's likely a method (indented)
            # This is a simple check and might miss some cases
            line_start = content[:match.start()].rfind('\n') + 1
            if match.start() - line_start > 0:
                continue
                
            # Check if it might be an API endpoint
            if (
                "route" in file_path.lower() or 
                "api" in file_path.lower() or 
                "app." in content or 
                "@app." in content or
                "blueprint." in content or
                "@blueprint." in content
            ):
                # Look for route decorators
                route_pattern = r'@(?:app|blueprint|router)\.(?:route|get|post|put|delete|patch)\s*\([\'"]([^\'"]*)[\'"]'
                route_match = re.search(route_pattern, content[:match.start()].split('\n')[-5:])
                if route_match:
                    path = route_match.group(1)
                    method = "GET"  # Default
                    if "post" in content[:match.start()].lower():
                        method = "POST"
                    elif "put" in content[:match.start()].lower():
                        method = "PUT"
                    elif "delete" in content[:match.start()].lower():
                        method = "DELETE"
                    elif "patch" in content[:match.start()].lower():
                        method = "PATCH"
                        
                    entities.append({
                        "name": func_name,
                        "type": "api_endpoint",
                        "definition": {
                            "path": path,
                            "method": method,
                            "handler": func_name
                        }
                    })
                else:
                    entities.append({
                        "name": func_name,
                        "type": "function",
                        "definition": {}
                    })
            else:
                entities.append({
                    "name": func_name,
                    "type": "function",
                    "definition": {}
                })
        
        return entities
        
    def _extract_js_entities(self, content: str, file_path: str, is_typescript: bool) -> List[Dict[str, Any]]:
        """
        Extract entities from JavaScript/TypeScript code.
        
        Args:
            content: File content
            file_path: Path to the file
            is_typescript: Whether the file is TypeScript
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            entities.append({
                "name": class_name,
                "type": "class",
                "definition": {}
            })
        
        # Extract functions/methods
        function_pattern = r'(?:function|const|let|var)\s+(\w+)\s*=?\s*(?:async\s*)?\(?[^)]*\)?\s*=>\s*{|\s*=?\s*function\s*\('
        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            entities.append({
                "name": func_name,
                "type": "function",
                "definition": {}
            })
        
        # Extract React components (functional)
        if "react" in content.lower() or "jsx" in file_path.lower() or "tsx" in file_path.lower():
            react_component_pattern = r'(?:function|const|let|var)\s+(\w+)(?:\s*:\s*React\.FC(?:<[^>]*>)?)?\s*=?\s*(?:\([^)]*\))?\s*=>\s*{'
            for match in re.finditer(react_component_pattern, content):
                component_name = match.group(1)
                
                # Extract props
                props = {}
                props_pattern = r'type Props = {([^}]*)}'
                props_match = re.search(props_pattern, content)
                if props_match:
                    props_content = props_match.group(1)
                    prop_lines = props_content.split('\n')
                    for line in prop_lines:
                        prop_match = re.search(r'(\w+)(?:\?)?:\s*([^;]*)', line)
                        if prop_match:
                            props[prop_match.group(1)] = prop_match.group(2).strip()
                
                entities.append({
                    "name": component_name,
                    "type": "ui_component",
                    "definition": {
                        "props": props,
                        "description": f"React component defined in {file_path}"
                    }
                })
        
        # Extract TypeScript interfaces
        if is_typescript:
            interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+\w+)?\s*{'
            for match in re.finditer(interface_pattern, content):
                interface_name = match.group(1)
                entities.append({
                    "name": interface_name,
                    "type": "interface",
                    "definition": {}
                })
                
            # Extract TypeScript types
            type_pattern = r'type\s+(\w+)\s*=\s*'
            for match in re.finditer(type_pattern, content):
                type_name = match.group(1)
                entities.append({
                    "name": type_name,
                    "type": "type",
                    "definition": {}
                })
        
        # Extract API routes (Express/Next.js/etc.)
        if "route" in file_path.lower() or "api" in file_path.lower():
            api_patterns = [
                r'(?:router|app)\.(?:get|post|put|delete|patch)\s*\([\'"]([^\'"]*)[\'"]',  # Express
                r'export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|DELETE|PATCH)\s*\(',  # Next.js API routes
                r'handler\s*\([^)]*\)\s*{'  # Generic API handler
            ]
            
            for pattern in api_patterns:
                for match in re.finditer(pattern, content):
                    name = Path(file_path).stem
                    path = match.group(1) if 'router' in pattern else f"/api/{name}"
                    method = "GET"
                    
                    if "post" in content.lower():
                        method = "POST"
                    elif "put" in content.lower():
                        method = "PUT"
                    elif "delete" in content.lower():
                        method = "DELETE"
                    elif "patch" in content.lower():
                        method = "PATCH"
                    
                    entities.append({
                        "name": name,
                        "type": "api_endpoint",
                        "definition": {
                            "path": path,
                            "method": method,
                            "handler": name
                        }
                    })
        
        return entities
        
    def _extract_java_entities(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract entities from Java code.
        
        Args:
            content: File content
            file_path: Path to the file
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Extract classes
        class_pattern = r'(?:public|private|protected)?\s*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            
            # Check if it might be a database entity/model
            if (
                "@Entity" in content or 
                "@Table" in content or
                "javax.persistence" in content or
                "jakarta.persistence" in content
            ):
                fields = {}
                field_pattern = r'(?:@Column[^)]*\))?\s*(?:private|public|protected)\s+(\w+(?:<[^>]*>)?)\s+(\w+)\s*;'
                for field_match in re.finditer(field_pattern, content):
                    field_type = field_match.group(1)
                    field_name = field_match.group(2)
                    fields[field_name] = field_type
                
                entities.append({
                    "name": class_name,
                    "type": "database_model",
                    "definition": {
                        "fields": fields,
                        "relationships": []
                    }
                })
            else:
                entities.append({
                    "name": class_name,
                    "type": "class",
                    "definition": {}
                })
        
        # Extract methods
        method_pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+(?:<[^>]*>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*{'
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            entities.append({
                "name": method_name,
                "type": "method",
                "definition": {}
            })
        
        # Extract REST endpoints
        if (
            "@RestController" in content or 
            "@Controller" in content or
            "@RequestMapping" in content or
            "@GetMapping" in content or
            "@PostMapping" in content
        ):
            # Get class-level path
            class_path = ""
            request_mapping_pattern = r'@RequestMapping\s*\((?:[^")]*)?"([^"]*)"'
            class_mapping_match = re.search(request_mapping_pattern, content)
            if class_mapping_match:
                class_path = class_mapping_match.group(1)
            
            # Find endpoint methods
            endpoint_patterns = [
                r'@GetMapping\s*\((?:[^")]*)?"([^"]*)"',
                r'@PostMapping\s*\((?:[^")]*)?"([^"]*)"',
                r'@PutMapping\s*\((?:[^")]*)?"([^"]*)"',
                r'@DeleteMapping\s*\((?:[^")]*)?"([^"]*)"',
                r'@PatchMapping\s*\((?:[^")]*)?"([^"]*)"'
            ]
            
            endpoint_methods = {
                "GetMapping": "GET",
                "PostMapping": "POST",
                "PutMapping": "PUT",
                "DeleteMapping": "DELETE",
                "PatchMapping": "PATCH"
            }
            
            for pattern in endpoint_patterns:
                for match in re.finditer(pattern, content):
                    endpoint_path = match.group(1)
                    full_path = class_path + endpoint_path
                    
                    # Find the method for this endpoint
                    pattern_type = pattern.split('@')[1].split('Mapping')[0]
                    method_type = endpoint_methods.get(pattern_type + "Mapping", "GET")
                    
                    # Find the method name (assuming it follows the annotation)
                    method_lines = content[match.end():].split('\n', 10)
                    for line in method_lines:
                        method_match = re.search(method_pattern, line)
                        if method_match:
                            method_name = method_match.group(1)
                            entities.append({
                                "name": method_name,
                                "type": "api_endpoint",
                                "definition": {
                                    "path": full_path,
                                    "method": method_type,
                                    "handler": method_name
                                }
                            })
                            break
        
        return entities
        
    async def analyze_code_relationships(self, files: List[CodeFile]) -> Dict[str, Any]:
        """
        Analyze relationships between code files.
        
        Args:
            files: List of code files
            
        Returns:
            Dictionary with analysis results
        """
        self._logger.info(f"Analyzing code relationships among {len(files)} files")
        
        # Reset the context
        self.reset()
        
        # Extract entities from all files
        for file in files:
            await self.extract_entities_from_file(file)
            
        # Build dependency graph
        for file in files:
            # Extract imports and register dependencies
            self._extract_and_register_imports(file)
            
            # Check for references to other entities
            for entity_name in self._shared_entities:
                if entity_name in file.content:
                    self.register_entity_reference(entity_name, file.path)
        
        # Analyze architecture patterns
        architecture_patterns = await self._analyze_architecture_patterns(files)
        
        # Return the analysis
        return {
            "entity_count": len(self._shared_entities),
            "dependency_count": sum(len(deps) for deps in self._file_dependencies.values()),
            "api_endpoints": len(self._api_endpoints),
            "database_models": len(self._database_models),
            "ui_components": len(self._ui_components),
            "architecture_patterns": architecture_patterns
        }
    
    def _extract_and_register_imports(self, file: CodeFile):
        """
        Extract imports from a file and register dependencies.
        
        Args:
            file: CodeFile to extract imports from
        """
        # Detect file type
        file_type = detect_file_type(Path(file.path))
        language = file_type.get("language", "unknown")
        
        if language == "python":
            # Extract Python imports
            import_patterns = [
                r'from\s+([\w.]+)\s+import\s+(?:[\w,\s]+)',
                r'import\s+([\w.]+)'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, file.content):
                    module = match.group(1)
                    
                    # Skip standard library imports
                    if module in ["os", "sys", "json", "datetime", "typing", "re", "pathlib"]:
                        continue
                    
                    # Register import statement
                    self.register_import(file.path, match.group(0))
                    
                    # Check if this is a local module
                    for other_file in self._file_dependencies:
                        module_path = module.replace('.', '/')
                        if module_path in other_file or module.split('.')[-1] in other_file:
                            self.register_dependency(file.path, other_file)
        
        elif language in ["javascript", "typescript"]:
            # Extract JS/TS imports
            import_patterns = [
                r'import\s+(?:{[^}]*}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]*)[\'"]',
                r'require\([\'"]([^\'"]*)[\'"]'
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, file.content):
                    module = match.group(1)
                    
                    # Skip node modules
                    if not module.startswith('.') and not module.startswith('/'):
                        continue
                    
                    # Register import statement
                    self.register_import(file.path, match.group(0))
                    
                    # Resolve relative path
                    if module.startswith('.'):
                        # Remove file extension if present
                        if module.endswith('.js') or module.endswith('.ts') or module.endswith('.jsx') or module.endswith('.tsx'):
                            module = module[:-3]
                        
                        # Get parent directory of current file
                        parent = Path(file.path).parent
                        
                        # Resolve relative path
                        if module.startswith('./'):
                            module_path = parent / module[2:]
                        elif module.startswith('../'):
                            module_path = parent.parent / module[3:]
                        else:
                            module_path = parent / module
                        
                        # Check if this path matches any file
                        for other_file in self._file_dependencies:
                            if (
                                str(module_path) in other_file or 
                                module.split('/')[-1] in other_file
                            ):
                                self.register_dependency(file.path, other_file)
        
        elif language == "java":
            # Extract Java imports
            import_pattern = r'import\s+([\w.]+);'
            
            for match in re.finditer(import_pattern, file.content):
                full_class = match.group(1)
                
                # Skip standard library imports
                if full_class.startswith("java.") or full_class.startswith("javax."):
                    continue
                
                # Register import statement
                self.register_import(file.path, match.group(0))
                
                # Check if this is a local class
                class_name = full_class.split('.')[-1]
                package_path = '.'.join(full_class.split('.')[:-1])
                
                # Convert package to directory structure
                package_dir = package_path.replace('.', '/')
                
                # Check if this matches any file
                for other_file in self._file_dependencies:
                    if (
                        package_dir in other_file and class_name in other_file or
                        class_name in other_file
                    ):
                        self.register_dependency(file.path, other_file)
    
    async def _analyze_architecture_patterns(self, files: List[CodeFile]) -> List[str]:
        """
        Analyze architecture patterns in the files.
        
        Args:
            files: List of code files
            
        Returns:
            List of detected architecture pattern names
        """
        patterns = []
        
        # Check for MVC pattern
        if self._check_mvc_pattern(files):
            patterns.append("MVC (Model-View-Controller)")
        
        # Check for Clean Architecture
        if self._check_clean_architecture(files):
            patterns.append("Clean Architecture")
        
        # Check for Microservices
        if self._check_microservices(files):
            patterns.append("Microservices")
        
        # Check for Repository Pattern
        if self._check_repository_pattern(files):
            patterns.append("Repository Pattern")
        
        # Check for Service Layer
        if self._check_service_layer(files):
            patterns.append("Service Layer")
        
        # Check for CQRS
        if self._check_cqrs(files):
            patterns.append("CQRS (Command Query Responsibility Segregation)")
        
        return patterns
    
    def _check_mvc_pattern(self, files: List[CodeFile]) -> bool:
        """Check if the MVC pattern is present."""
        # Count files in different categories
        models_count = sum(1 for f in files if "model" in f.path.lower() or "models" in f.path.lower())
        views_count = sum(1 for f in files if "view" in f.path.lower() or "views" in f.path.lower())
        controllers_count = sum(1 for f in files if "controller" in f.path.lower() or "controllers" in f.path.lower())
        
        # Check if all three components exist
        return models_count > 0 and views_count > 0 and controllers_count > 0
    
    def _check_clean_architecture(self, files: List[CodeFile]) -> bool:
        """Check if Clean Architecture is present."""
        # Look for key components of Clean Architecture
        has_entities = any("entity" in f.path.lower() or "entities" in f.path.lower() for f in files)
        has_use_cases = any("usecase" in f.path.lower() or "usecases" in f.path.lower() for f in files)
        has_interfaces = any("interface" in f.path.lower() or "interfaces" in f.path.lower() for f in files)
        has_infrastructure = any("infra" in f.path.lower() or "infrastructure" in f.path.lower() for f in files)
        
        return has_entities and has_use_cases and (has_interfaces or has_infrastructure)
    
    def _check_microservices(self, files: List[CodeFile]) -> bool:
        """Check if Microservices architecture is present."""
        # Look for multiple service directories
        service_dirs = set()
        for file in files:
            path_parts = Path(file.path).parts
            if "service" in path_parts or "services" in path_parts:
                service_index = -1
                for i, part in enumerate(path_parts):
                    if "service" in part.lower():
                        service_index = i
                        break
                
                if service_index >= 0 and service_index + 1 < len(path_parts):
                    service_dirs.add(path_parts[service_index + 1])
        
        # If we have multiple service directories, it's likely microservices
        return len(service_dirs) >= 2
    
    def _check_repository_pattern(self, files: List[CodeFile]) -> bool:
        """Check if Repository Pattern is present."""
        # Look for repository classes
        has_repositories = any("repository" in f.path.lower() or "repositories" in f.path.lower() for f in files)
        has_entities = len(self._database_models) > 0
        
        return has_repositories and has_entities
    
    def _check_service_layer(self, files: List[CodeFile]) -> bool:
        """Check if Service Layer pattern is present."""
        # Look for service classes
        has_services = any("service" in f.path.lower() or "services" in f.path.lower() for f in files)
        
        # Check if service classes actually exist in content
        if has_services:
            service_files = [f for f in files if "service" in f.path.lower() or "services" in f.path.lower()]
            for file in service_files:
                if "class" in file.content.lower() and "service" in file.content.lower():
                    return True
        
        return False
    
    def _check_cqrs(self, files: List[CodeFile]) -> bool:
        """Check if CQRS pattern is present."""
        # Look for command and query separation
        has_commands = any("command" in f.path.lower() or "commands" in f.path.lower() for f in files)
        has_queries = any("query" in f.path.lower() or "queries" in f.path.lower() for f in files)
        
        return has_commands and has_queries
    
    async def enhance_prompt_with_context(
        self, 
        prompt: str, 
        file_path: str, 
        related_files: Optional[List[str]] = None,
        max_tokens: int = 4000
    ) -> str:
        """
        Enhance a prompt with relevant context for better code generation.
        
        Args:
            prompt: Original prompt
            file_path: Path of the file being generated
            related_files: Optional list of related file paths
            max_tokens: Maximum context tokens to include
            
        Returns:
            Enhanced prompt with context
        """
        self._logger.debug(f"Enhancing prompt for {file_path}")
        
        # Start with the original prompt
        enhanced_prompt = prompt
        
        # Add global context
        enhanced_prompt += "\n\nGlobal context for this project:\n"
        for key, value in self._global_context.items():
            if isinstance(value, (str, int, float, bool)):
                enhanced_prompt += f"- {key}: {value}\n"
        
        # Add information about APIs if relevant
        if "api" in file_path.lower() or "controller" in file_path.lower() or "routes" in file_path.lower():
            if self._api_endpoints:
                enhanced_prompt += "\nAPI Endpoints already defined in the project:\n"
                for endpoint in self._api_endpoints:
                    enhanced_prompt += f"- {endpoint['method']} {endpoint['path']} (handler: {endpoint['name']})\n"
        
        # Add information about database models if relevant
        if "model" in file_path.lower() or "entity" in file_path.lower() or "repository" in file_path.lower():
            if self._database_models:
                enhanced_prompt += "\nDatabase Models already defined in the project:\n"
                for model in self._database_models:
                    enhanced_prompt += f"- {model['name']} with fields: {', '.join(model['fields'].keys())}\n"
        
        # Add information about UI components if relevant
        if "component" in file_path.lower() or "view" in file_path.lower() or any(ext in file_path.lower() for ext in [".jsx", ".tsx", ".vue"]):
            if self._ui_components:
                enhanced_prompt += "\nUI Components already defined in the project:\n"
                for component in self._ui_components:
                    enhanced_prompt += f"- {component['name']} with props: {', '.join(component['props'].keys())}\n"
        
        # Add dependencies if this file has any
        dependencies = self.get_dependencies(file_path)
        if dependencies:
            enhanced_prompt += "\nThis file depends on:\n"
            for dep in dependencies:
                enhanced_prompt += f"- {dep}\n"
        
        # Add entities that are referenced by this file
        referenced_entities = [name for name, refs in self._entity_references.items() if any(ref["file_path"] == file_path for ref in refs)]
        if referenced_entities:
            enhanced_prompt += "\nThis file references these entities:\n"
            for entity_name in referenced_entities:
                entity = self.get_entity(entity_name)
                if entity:
                    enhanced_prompt += f"- {entity_name} ({entity['type']})\n"
        
        # Add content from related files if provided
        if related_files:
            # Sort related files by relationship importance
            sorted_related = self._sort_related_files_by_importance(file_path, related_files)
            
            # Add content with a token limit
            added_tokens = len(enhanced_prompt.split())
            max_tokens_for_related = max_tokens - added_tokens
            
            added_files = []
            for related_file in sorted_related:
                # Find the file content
                file_content = None
                for f in [file for file in self._file_dependencies if file == related_file]:
                    file_content = f
                    break
                
                if not file_content:
                    continue
                
                # Estimate tokens in this content
                tokens_in_file = len(file_content.split())
                
                # If we would exceed the limit, skip this file
                if tokens_in_file + added_tokens > max_tokens_for_related:
                    continue
                
                # Add the file content
                enhanced_prompt += f"\n\nContent of related file {related_file}:\n```\n{file_content}\n```\n"
                added_tokens += tokens_in_file
                added_files.append(related_file)
                
                # If we're approaching the limit, stop adding files
                if added_tokens > max_tokens_for_related * 0.9:
                    break
        
        return enhanced_prompt
    
    def _sort_related_files_by_importance(self, file_path: str, related_files: List[str]) -> List[str]:
        """
        Sort related files by their importance to the current file.
        
        Args:
            file_path: Current file path
            related_files: List of related file paths
            
        Returns:
            Sorted list of related file paths
        """
        # Calculate importance scores
        file_scores = {}
        for related in related_files:
            score = 0
            
            # Direct dependency gets high score
            if related in self.get_dependencies(file_path):
                score += 10
                
            # File that depends on this file gets high score
            if file_path in self.get_dependencies(related):
                score += 8
                
            # Files in the same directory are important
            if Path(related).parent == Path(file_path).parent:
                score += 5
                
            # Files with shared entity references
            file_entities = set()
            for entity, refs in self._entity_references.items():
                if any(ref["file_path"] == file_path for ref in refs):
                    file_entities.add(entity)
            
            related_entities = set()
            for entity, refs in self._entity_references.items():
                if any(ref["file_path"] == related for ref in refs):
                    related_entities.add(entity)
            
            shared_entities = file_entities.intersection(related_entities)
            score += len(shared_entities) * 2
            
            file_scores[related] = score
        
        # Sort by score, descending
        return sorted(related_files, key=lambda f: file_scores.get(f, 0), reverse=True)

# Global instance
generation_context_manager = GenerationContextManager()
