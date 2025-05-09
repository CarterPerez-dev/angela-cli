# angela/ai/semantic_analyzer.py
"""
Semantic code analysis for Angela CLI.

This module provides deep code understanding capabilities, extracting semantic
information from source code files to enable context-aware assistance.
"""
import os
import re
import ast
import json
import asyncio
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set, Union, NamedTuple
from collections import defaultdict

from angela.utils.logging import get_logger
from angela.context.file_detector import detect_file_type
from angela.ai.client import gemini_client, GeminiRequest

logger = get_logger(__name__)

class CodeEntity:
    """Base class for code entities like functions, classes, and variables."""
    
    def __init__(self, name: str, line_start: int, line_end: int, filename: str):
        self.name = name
        self.line_start = line_start
        self.line_end = line_end
        self.filename = filename
        self.references: List[Tuple[str, int]] = []  # (filename, line)
        self.dependencies: List[str] = []  # Names of other entities this depends on
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "filename": self.filename,
            "references": self.references,
            "dependencies": self.dependencies
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, file={Path(self.filename).name}:{self.line_start}-{self.line_end})"


class Function(CodeEntity):
    """Represents a function or method in code."""
    
    def __init__(self, name: str, line_start: int, line_end: int, filename: str, 
                 params: List[str], docstring: Optional[str] = None,
                 is_method: bool = False, decorators: List[str] = None,
                 return_type: Optional[str] = None, class_name: Optional[str] = None):
        super().__init__(name, line_start, line_end, filename)
        self.params = params
        self.docstring = docstring
        self.is_method = is_method
        self.decorators = decorators or []
        self.return_type = return_type
        self.class_name = class_name
        self.called_functions: List[str] = []
        self.complexity: Optional[int] = None  # Cyclomatic complexity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update({
            "params": self.params,
            "docstring": self.docstring,
            "is_method": self.is_method,
            "decorators": self.decorators,
            "return_type": self.return_type,
            "class_name": self.class_name,
            "called_functions": self.called_functions,
            "complexity": self.complexity
        })
        return result


class Class(CodeEntity):
    """Represents a class in code."""
    
    def __init__(self, name: str, line_start: int, line_end: int, filename: str,
                 docstring: Optional[str] = None, base_classes: List[str] = None,
                 decorators: List[str] = None):
        super().__init__(name, line_start, line_end, filename)
        self.docstring = docstring
        self.base_classes = base_classes or []
        self.decorators = decorators or []
        self.methods: Dict[str, Function] = {}
        self.attributes: Dict[str, Variable] = {}
        self.nested_classes: Dict[str, 'Class'] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update({
            "docstring": self.docstring,
            "base_classes": self.base_classes,
            "decorators": self.decorators,
            "methods": {name: method.to_dict() for name, method in self.methods.items()},
            "attributes": {name: attr.to_dict() for name, attr in self.attributes.items()},
            "nested_classes": {name: cls.to_dict() for name, cls in self.nested_classes.items()}
        })
        return result


class Variable(CodeEntity):
    """Represents a variable or attribute in code."""
    
    def __init__(self, name: str, line_start: int, line_end: int, filename: str,
                 var_type: Optional[str] = None, value: Optional[str] = None,
                 is_attribute: bool = False, class_name: Optional[str] = None,
                 is_constant: bool = False):
        super().__init__(name, line_start, line_end, filename)
        self.var_type = var_type
        self.value = value
        self.is_attribute = is_attribute
        self.class_name = class_name
        self.is_constant = is_constant
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update({
            "var_type": self.var_type,
            "value": self.value,
            "is_attribute": self.is_attribute,
            "class_name": self.class_name,
            "is_constant": self.is_constant
        })
        return result


class Import(CodeEntity):
    """Represents an import statement."""
    
    def __init__(self, name: str, line_start: int, line_end: int, filename: str,
                 import_path: str, is_from: bool = False, alias: Optional[str] = None):
        super().__init__(name, line_start, line_end, filename)
        self.import_path = import_path
        self.is_from = is_from
        self.alias = alias
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = super().to_dict()
        result.update({
            "import_path": self.import_path,
            "is_from": self.is_from,
            "alias": self.alias
        })
        return result


class Module:
    """Represents a code module (file) with its entities."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.imports: Dict[str, Import] = {}
        self.functions: Dict[str, Function] = {}
        self.classes: Dict[str, Class] = {}
        self.variables: Dict[str, Variable] = {}
        self.docstring: Optional[str] = None
        self.language: Optional[str] = None
        self.dependencies: List[str] = []
        self.last_modified: Optional[float] = None
        self.code_metrics: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "filename": self.filename,
            "imports": {name: imp.to_dict() for name, imp in self.imports.items()},
            "functions": {name: func.to_dict() for name, func in self.functions.items()},
            "classes": {name: cls.to_dict() for name, cls in self.classes.items()},
            "variables": {name: var.to_dict() for name, var in self.variables.items()},
            "docstring": self.docstring,
            "language": self.language,
            "dependencies": self.dependencies,
            "last_modified": self.last_modified,
            "code_metrics": self.code_metrics
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get a simplified summary of the module."""
        return {
            "filename": self.filename,
            "name": Path(self.filename).name,
            "language": self.language,
            "class_count": len(self.classes),
            "function_count": len(self.functions),
            "import_count": len(self.imports),
            "docstring": self.docstring[:100] + "..." if self.docstring and len(self.docstring) > 100 else self.docstring,
            "classes": list(self.classes.keys()),
            "key_functions": list(self.functions.keys())[:5] + (["..."] if len(self.functions) > 5 else []),
            "dependencies": self.dependencies
        }


class SemanticAnalyzer:
    """
    Semantic code analyzer that extracts deeper meaning from source files.
    
    This class provides:
    1. Extraction of code structure (functions, classes, variables)
    2. Analysis of dependencies and references
    3. Code metrics and complexity information
    4. Integration with the LLM for deeper insights
    """
    
    def __init__(self):
        self._logger = logger
        self._modules: Dict[str, Module] = {}
        self._language_analyzers: Dict[str, callable] = {
            "python": self._analyze_python_file,
            "javascript": self._analyze_javascript_file,
            "typescript": self._analyze_typescript_file,
            "java": self._analyze_with_llm,
            "c#": self._analyze_with_llm,
            "c++": self._analyze_with_llm,
            "ruby": self._analyze_with_llm,
            "go": self._analyze_with_llm,
            "rust": self._analyze_with_llm
        }
        self._cache_valid_time = 300  # Seconds before a cached analysis is considered stale
    
    async def analyze_file(self, file_path: Union[str, Path]) -> Optional[Module]:
        """
        Analyze a source code file to extract semantic information.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Module object with semantic information or None if analysis failed
        """
        path_obj = Path(file_path)
        
        # Check if we have a recent cached analysis
        if str(path_obj) in self._modules:
            module = self._modules[str(path_obj)]
            if module.last_modified and path_obj.stat().st_mtime <= module.last_modified:
                self._logger.debug(f"Using cached analysis for {path_obj}")
                return module
        
        # Check if file exists
        if not path_obj.exists():
            self._logger.warning(f"File not found for semantic analysis: {path_obj}")
            return None
        
        # Detect file type
        file_info = detect_file_type(path_obj)
        language = file_info.get("language", "").lower()
        
        # Skip if this isn't a supported code file
        if not language or language.lower() not in self._language_analyzers:
            self._logger.debug(f"Unsupported language for semantic analysis: {language} in {path_obj}")
            return None
        
        # Create a new module
        module = Module(str(path_obj))
        module.language = language
        module.last_modified = path_obj.stat().st_mtime
        
        try:
            # Call the appropriate analyzer based on language
            analyzer = self._language_analyzers.get(language.lower(), self._analyze_with_llm)
            
            if asyncio.iscoroutinefunction(analyzer):
                result = await analyzer(path_obj, module)
            else:
                result = analyzer(path_obj, module)
            
            if result:
                self._modules[str(path_obj)] = module
                self._logger.info(f"Completed semantic analysis of {path_obj}")
                return module
        except Exception as e:
            self._logger.exception(f"Error analyzing {path_obj}: {str(e)}")
        
        return None
    
    async def analyze_project_files(self, project_root: Union[str, Path], max_files: int = 100) -> Dict[str, Module]:
        """
        Analyze multiple source files within a project.
        
        Args:
            project_root: Root directory of the project
            max_files: Maximum number of files to analyze
            
        Returns:
            Dictionary of file paths to Module objects
        """
        root_path = Path(project_root)
        
        # Find source code files
        source_files = []
        
        for language, _ in self._language_analyzers.items():
            extensions = self._get_extensions_for_language(language)
            for ext in extensions:
                source_files.extend(list(root_path.glob(f"**/*{ext}")))
        
        # Exclude files that shouldn't be analyzed
        exclude_patterns = [
            "**/node_modules/**", "**/venv/**", "**/.venv/**",
            "**/.git/**", "**/build/**", "**/dist/**",
            "**/__pycache__/**", "**/.pytest_cache/**"
        ]
        
        for pattern in exclude_patterns:
            source_files = [f for f in source_files if not self._matches_glob_pattern(str(f), pattern)]
        
        # Limit to max files
        source_files = source_files[:max_files]
        
        # Analyze each file
        analysis_results = {}
        
        for file_path in source_files:
            module = await self.analyze_file(file_path)
            if module:
                analysis_results[str(file_path)] = module
        
        # Analyze references between modules
        self._analyze_cross_module_references(analysis_results)
        
        return analysis_results
    
    def _get_extensions_for_language(self, language: str) -> List[str]:
        """Get file extensions for a given language."""
        extensions_map = {
            "python": [".py", ".pyi", ".pyx"],
            "javascript": [".js", ".jsx", ".mjs"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "c#": [".cs"],
            "c++": [".cpp", ".cc", ".h", ".hpp"],
            "ruby": [".rb"],
            "go": [".go"],
            "rust": [".rs"]
        }
        
        return extensions_map.get(language.lower(), [])
    
    def _matches_glob_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    def _analyze_python_file(self, file_path: Path, module: Module) -> bool:
        """
        Analyze a Python file using the ast module.
        
        Args:
            file_path: Path to the Python file
            module: Module object to populate
            
        Returns:
            True if analysis was successful, False otherwise
        """
        # Read the file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._logger.error(f"Error reading Python file {file_path}: {str(e)}")
            return False
        
        # Parse the AST
        try:
            tree = ast.parse(content, filename=str(file_path))
            
            # Get module docstring
            module.docstring = ast.get_docstring(tree)
            
            # Visit all nodes in the AST to extract information
            for node in ast.walk(tree):
                # Extract imports
                if isinstance(node, ast.Import):
                    for name in node.names:
                        import_name = name.asname or name.name
                        module.imports[import_name] = Import(
                            name=import_name,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            filename=str(file_path),
                            import_path=name.name,
                            is_from=False,
                            alias=name.asname
                        )
                        module.dependencies.append(name.name)
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ""
                    for name in node.names:
                        import_name = name.asname or name.name
                        full_path = f"{module_name}.{name.name}" if module_name else name.name
                        module.imports[import_name] = Import(
                            name=import_name,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            filename=str(file_path),
                            import_path=full_path,
                            is_from=True,
                            alias=name.asname
                        )
                        module.dependencies.append(full_path)
                
                # Extract functions
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # Check if we're inside a class
                    parent_class = None
                    for ancestor in ast.iter_fields(tree):
                        if isinstance(ancestor[1], list):
                            for item in ancestor[1]:
                                if isinstance(item, ast.ClassDef) and node in item.body:
                                    parent_class = item.name
                                    break
                    
                    # Get function parameters
                    params = []
                    for arg in node.args.args:
                        params.append(arg.arg)
                    
                    # Get decorators
                    decorators = []
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorators.append(decorator.id)
                        elif isinstance(decorator, ast.Attribute):
                            decorators.append(f"{decorator.value.id}.{decorator.attr}")
                        elif isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name):
                                decorators.append(decorator.func.id)
                            elif isinstance(decorator.func, ast.Attribute):
                                decorators.append(f"{decorator.func.value.id}.{decorator.func.attr}")
                    
                    # Get return type annotation if available
                    return_type = None
                    if node.returns:
                        return_type = self._get_type_annotation(node.returns)
                    
                    # Create function entity
                    function = Function(
                        name=node.name,
                        line_start=node.lineno,
                        line_end=self._get_last_line(node),
                        filename=str(file_path),
                        params=params,
                        docstring=ast.get_docstring(node),
                        is_method=parent_class is not None,
                        decorators=decorators,
                        return_type=return_type,
                        class_name=parent_class
                    )
                    
                    # Extract called functions
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name):
                                function.called_functions.append(child.func.id)
                            elif isinstance(child.func, ast.Attribute):
                                if isinstance(child.func.value, ast.Name):
                                    function.called_functions.append(f"{child.func.value.id}.{child.func.attr}")
                    
                    # Calculate cyclomatic complexity
                    function.complexity = self._calculate_complexity(node)
                    
                    # Store the function in the appropriate place
                    if parent_class and parent_class in module.classes:
                        module.classes[parent_class].methods[node.name] = function
                    else:
                        module.functions[node.name] = function
                
                # Extract classes
                elif isinstance(node, ast.ClassDef):
                    # Get base classes
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_classes.append(f"{base.value.id}.{base.attr}")
                    
                    # Get decorators
                    decorators = []
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorators.append(decorator.id)
                    
                    # Create class entity
                    class_entity = Class(
                        name=node.name,
                        line_start=node.lineno,
                        line_end=self._get_last_line(node),
                        filename=str(file_path),
                        docstring=ast.get_docstring(node),
                        base_classes=base_classes,
                        decorators=decorators
                    )
                    
                    # Look for class attributes
                    for child in node.body:
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    # Get value as string
                                    value = None
                                    if isinstance(child.value, ast.Constant):
                                        value = str(child.value.value)
                                    
                                    # Create attribute entity
                                    attribute = Variable(
                                        name=target.id,
                                        line_start=child.lineno,
                                        line_end=child.lineno,
                                        filename=str(file_path),
                                        var_type=None,  # No type annotation in assign
                                        value=value,
                                        is_attribute=True,
                                        class_name=node.name
                                    )
                                    
                                    class_entity.attributes[target.id] = attribute
                        
                        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                            # Get type annotation
                            var_type = self._get_type_annotation(child.annotation)
                            
                            # Get value as string
                            value = None
                            if child.value and isinstance(child.value, ast.Constant):
                                value = str(child.value.value)
                            
                            # Create attribute entity
                            attribute = Variable(
                                name=child.target.id,
                                line_start=child.lineno,
                                line_end=child.lineno,
                                filename=str(file_path),
                                var_type=var_type,
                                value=value,
                                is_attribute=True,
                                class_name=node.name
                            )
                            
                            class_entity.attributes[child.target.id] = attribute
                    
                    module.classes[node.name] = class_entity
                
                # Extract global variables
                elif isinstance(node, ast.Assign) and all(isinstance(target, ast.Name) for target in node.targets):
                    for target in node.targets:
                        # Skip private variables
                        if target.id.startswith('_'):
                            continue
                        
                        # Get value as string
                        value = None
                        if isinstance(node.value, ast.Constant):
                            value = str(node.value.value)
                        
                        # Check if this is a constant
                        is_constant = target.id.isupper()
                        
                        # Create variable entity
                        variable = Variable(
                            name=target.id,
                            line_start=node.lineno,
                            line_end=node.lineno,
                            filename=str(file_path),
                            var_type=None,  # No type annotation in assign
                            value=value,
                            is_constant=is_constant
                        )
                        
                        module.variables[target.id] = variable
                
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    # Skip private variables
                    if node.target.id.startswith('_'):
                        continue
                    
                    # Get type annotation
                    var_type = self._get_type_annotation(node.annotation)
                    
                    # Get value as string
                    value = None
                    if node.value and isinstance(node.value, ast.Constant):
                        value = str(node.value.value)
                    
                    # Check if this is a constant
                    is_constant = node.target.id.isupper()
                    
                    # Create variable entity
                    variable = Variable(
                        name=node.target.id,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        filename=str(file_path),
                        var_type=var_type,
                        value=value,
                        is_constant=is_constant
                    )
                    
                    module.variables[node.target.id] = variable
            
            # Calculate code metrics
            module.code_metrics = {
                "total_lines": len(content.splitlines()),
                "code_lines": len([line for line in content.splitlines() if line.strip() and not line.strip().startswith('#')]),
                "comment_lines": len([line for line in content.splitlines() if line.strip().startswith('#')]),
                "blank_lines": len([line for line in content.splitlines() if not line.strip()]),
                "function_count": len(module.functions),
                "class_count": len(module.classes),
                "import_count": len(module.imports),
                "complexity": sum(func.complexity or 0 for func in module.functions.values()),
                "average_function_size": sum(func.line_end - func.line_start for func in module.functions.values()) / len(module.functions) if module.functions else 0
            }
            
            return True
        
        except SyntaxError as e:
            self._logger.warning(f"Syntax error in Python file {file_path}: {str(e)}")
            return False
            
        except Exception as e:
            self._logger.error(f"Error parsing Python file {file_path}: {str(e)}")
            return False
    
    def _get_type_annotation(self, annotation) -> Optional[str]:
        """Extract type annotation string from AST node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            if isinstance(annotation.value, ast.Name):
                return f"{annotation.value.id}.{annotation.attr}"
            return annotation.attr
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if isinstance(annotation.slice, ast.Name):
                    return f"{annotation.value.id}[{annotation.slice.id}]"
                elif isinstance(annotation.slice, ast.Constant):
                    return f"{annotation.value.id}[{annotation.slice.value}]"
                return f"{annotation.value.id}[...]"
            return "..."
        return None
    
    def _get_last_line(self, node) -> int:
        """Get the last line number of an AST node."""
        # If the node has an end_lineno attribute (Python 3.8+), use it
        if hasattr(node, 'end_lineno'):
            return node.end_lineno
        
        # Otherwise, find the maximum lineno in the node and its children
        max_lineno = node.lineno
        for child in ast.iter_child_nodes(node):
            max_lineno = max(max_lineno, self._get_last_line(child))
        return max_lineno
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Start with 1 (default path)
        
        # Count branches
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.IfExp)):
                complexity += 1
            elif isinstance(child, ast.BoolOp) and isinstance(child.op, ast.And):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.BoolOp) and isinstance(child.op, ast.Or):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers)  # Count except blocks
        
        return complexity
    
    async def _analyze_javascript_file(self, file_path: Path, module: Module) -> bool:
        """
        Analyze a JavaScript file using a simple regex-based approach or LLM.
        
        Args:
            file_path: Path to the JavaScript file
            module: Module object to populate
            
        Returns:
            True if analysis was successful, False otherwise
        """
        # For non-Python files, we'll use a simple regex-based approach for now
        # In a real implementation, you might want to use language-specific parsers
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract imports/requires
            import_patterns = [
                r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]',  # import { x, y } from 'module'
                r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',  # import x from 'module'
                r'import\s+[\'"]([^\'"]+)[\'"]',  # import 'module'
                r'const\s+{([^}]+)}\s+=\s+require\([\'"]([^\'"]+)[\'"]\)',  # const { x, y } = require('module')
                r'const\s+(\w+)\s+=\s+require\([\'"]([^\'"]+)[\'"]\)'  # const x = require('module')
            ]
            
            line_num = 1
            for line in content.splitlines():
                for pattern in import_patterns:
                    for match in re.finditer(pattern, line):
                        if len(match.groups()) == 2:
                            names, module_path = match.groups()
                            if ',' in names:
                                # Multiple imports
                                for name in names.split(','):
                                    name = name.strip()
                                    if name:
                                        module.imports[name] = Import(
                                            name=name,
                                            line_start=line_num,
                                            line_end=line_num,
                                            filename=str(file_path),
                                            import_path=f"{module_path}.{name}",
                                            is_from=True
                                        )
                                        module.dependencies.append(module_path)
                            else:
                                # Single import
                                name = names.strip()
                                module.imports[name] = Import(
                                    name=name,
                                    line_start=line_num,
                                    line_end=line_num,
                                    filename=str(file_path),
                                    import_path=module_path,
                                    is_from=True
                                )
                                module.dependencies.append(module_path)
                        else:
                            # Simple import
                            module_path = match.group(1)
                            module.dependencies.append(module_path)
                line_num += 1
            
            # Extract functions
            function_patterns = [
                r'function\s+(\w+)\s*\(([^)]*)\)',  # function name(params)
                r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{',  # const name = (params) => {
                r'let\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{',  # let name = (params) => {
                r'var\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*{',  # var name = (params) => {
                r'async\s+function\s+(\w+)\s*\(([^)]*)\)'  # async function name(params)
            ]
            
            for pattern in function_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    name = match.group(1)
                    params = []
                    if len(match.groups()) > 1:
                        params = [p.strip() for p in match.group(2).split(',') if p.strip()]
                    
                    start_line = content[:match.start()].count('\n') + 1
                    end_line = start_line + content[match.start():].split('{', 1)[1].count('\n')
                    
                    function = Function(
                        name=name,
                        line_start=start_line,
                        line_end=end_line if end_line > start_line else start_line + 5,  # Estimate if we couldn't find the end
                        filename=str(file_path),
                        params=params
                    )
                    
                    module.functions[name] = function
            
            # Extract classes
            class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
            for match in re.finditer(class_pattern, content, re.MULTILINE):
                name = match.group(1)
                base_classes = []
                if match.group(2):
                    base_classes.append(match.group(2))
                
                start_line = content[:match.start()].count('\n') + 1
                
                # Try to find the end of the class
                class_content = content[match.start():]
                open_braces = 0
                for i, char in enumerate(class_content):
                    if char == '{':
                        open_braces += 1
                    elif char == '}':
                        open_braces -= 1
                        if open_braces == 0:
                            end_line = start_line + class_content[:i+1].count('\n')
                            break
                else:
                    end_line = start_line + 20  # Estimate if we couldn't find the end
                
                class_entity = Class(
                    name=name,
                    line_start=start_line,
                    line_end=end_line,
                    filename=str(file_path),
                    base_classes=base_classes
                )
                
                module.classes[name] = class_entity
            
            # Calculate code metrics
            module.code_metrics = {
                "total_lines": len(content.splitlines()),
                "code_lines": len([line for line in content.splitlines() if line.strip() and not line.strip().startswith('//')]),
                "comment_lines": len([line for line in content.splitlines() if line.strip().startswith('//')]),
                "blank_lines": len([line for line in content.splitlines() if not line.strip()]),
                "function_count": len(module.functions),
                "class_count": len(module.classes),
                "import_count": len(module.imports)
            }
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error analyzing JavaScript file {file_path}: {str(e)}")
            return False
    
    async def _analyze_typescript_file(self, file_path: Path, module: Module) -> bool:
        """
        Analyze a TypeScript file.
        
        Args:
            file_path: Path to the TypeScript file
            module: Module object to populate
            
        Returns:
            True if analysis was successful, False otherwise
        """
        # Start with JavaScript analysis
        js_result = await self._analyze_javascript_file(file_path, module)
        
        if not js_result:
            return False
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract interfaces
            interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
            for match in re.finditer(interface_pattern, content, re.MULTILINE):
                name = match.group(1)
                base_classes = []
                if match.group(2):
                    base_classes.append(match.group(2))
                
                start_line = content[:match.start()].count('\n') + 1
                
                # Try to find the end of the interface
                interface_content = content[match.start():]
                open_braces = 0
                for i, char in enumerate(interface_content):
                    if char == '{':
                        open_braces += 1
                    elif char == '}':
                        open_braces -= 1
                        if open_braces == 0:
                            end_line = start_line + interface_content[:i+1].count('\n')
                            break
                else:
                    end_line = start_line + 10  # Estimate if we couldn't find the end
                
                # Treat interfaces as classes for simplicity
                class_entity = Class(
                    name=name,
                    line_start=start_line,
                    line_end=end_line,
                    filename=str(file_path),
                    base_classes=base_classes
                )
                
                module.classes[name] = class_entity
            
            # Extract types
            type_pattern = r'type\s+(\w+)\s*=\s*\{[^}]*\}'
            for match in re.finditer(type_pattern, content, re.MULTILINE):
                name = match.group(1)
                
                start_line = content[:match.start()].count('\n') + 1
                end_line = start_line + content[match.start():match.end()].count('\n')
                
                # For simplicity, we'll store types as variables
                variable = Variable(
                    name=name,
                    line_start=start_line,
                    line_end=end_line,
                    filename=str(file_path),
                    var_type="type",
                    is_constant=True
                )
                
                module.variables[name] = variable
            
            # Update functions and class methods with type information
            for name, function in module.functions.items():
                # Try to find the function with type annotations
                function_pattern = fr'function\s+{re.escape(name)}\s*\([^)]*\)\s*:\s*(\w+)'
                match = re.search(function_pattern, content)
                if match:
                    function.return_type = match.group(1)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error analyzing TypeScript file {file_path}: {str(e)}")
            return False
    
    async def _analyze_with_llm(self, file_path: Path, module: Module) -> bool:
        """
        Use the LLM to analyze files when language-specific parsers aren't available.
        
        Args:
            file_path: Path to the file
            module: Module object to populate
            
        Returns:
            True if analysis was successful, False otherwise
        """
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Limit content size for LLM
            if len(content) > 20000:
                self._logger.warning(f"File {file_path} is too large for LLM analysis, truncating")
                content = content[:20000] + "\n... [truncated]"
            
            # Detect language
            file_info = detect_file_type(file_path)
            language = file_info.get("language", "unknown")
            
            # Build prompt for the LLM
            prompt = f"""
Analyze this {language} source code and extract the key semantic information:

```{language}
{content}
```

Please return a JSON response with the following structure:
{{
  "imports": [
    {{ "name": "import_name", "path": "import_path", "line": line_number }}
  ],
  "functions": [
    {{ "name": "function_name", "start_line": start_line, "end_line": end_line, "params": ["param1", "param2"], "return_type": "return_type", "complexity": estimated_complexity }}
  ],
  "classes": [
    {{ 
      "name": "class_name", 
      "start_line": start_line, 
      "end_line": end_line, 
      "base_classes": ["base1", "base2"],
      "methods": [
        {{ "name": "method_name", "start_line": start_line, "end_line": end_line, "params": ["param1", "param2"] }}
      ],
      "attributes": [
        {{ "name": "attr_name", "type": "attr_type", "line": line_number }}
      ]
    }}
  ],
  "variables": [
    {{ "name": "var_name", "type": "var_type", "line": line_number, "is_constant": true_or_false }}
  ],
  "docstring": "module_level_docstring_if_any",
  "code_metrics": {{
    "total_lines": total_line_count,
    "function_count": number_of_functions,
    "class_count": number_of_classes,
    "complexity": estimated_overall_complexity
  }}
}}

Ensure your JSON is valid. Don't include any comments or explanations outside the JSON.
"""
            # Call AI service
            api_request = GeminiRequest(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.1  # Low temperature for more deterministic output
            )
            
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            try:
                # Try to extract JSON from the response
                response_text = response.text
                
                # Look for JSON block
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                
                # Try to parse the JSON
                data = json.loads(response_text)
                
                # Populate the module with the extracted information
                
                # Module docstring
                if "docstring" in data:
                    module.docstring = data["docstring"]
                
                # Imports
                for imp in data.get("imports", []):
                    name = imp.get("name", "")
                    if name:
                        module.imports[name] = Import(
                            name=name,
                            line_start=imp.get("line", 1),
                            line_end=imp.get("line", 1),
                            filename=str(file_path),
                            import_path=imp.get("path", "")
                        )
                        if imp.get("path"):
                            module.dependencies.append(imp.get("path"))
                
                # Functions
                for func in data.get("functions", []):
                    name = func.get("name", "")
                    if name:
                        module.functions[name] = Function(
                            name=name,
                            line_start=func.get("start_line", 1),
                            line_end=func.get("end_line", 1),
                            filename=str(file_path),
                            params=func.get("params", []),
                            return_type=func.get("return_type"),
                            complexity=func.get("complexity")
                        )
                
                # Classes
                for cls in data.get("classes", []):
                    name = cls.get("name", "")
                    if name:
                        class_entity = Class(
                            name=name,
                            line_start=cls.get("start_line", 1),
                            line_end=cls.get("end_line", 1),
                            filename=str(file_path),
                            base_classes=cls.get("base_classes", [])
                        )
                        
                        # Add methods
                        for method in cls.get("methods", []):
                            method_name = method.get("name", "")
                            if method_name:
                                class_entity.methods[method_name] = Function(
                                    name=method_name,
                                    line_start=method.get("start_line", 1),
                                    line_end=method.get("end_line", 1),
                                    filename=str(file_path),
                                    params=method.get("params", []),
                                    is_method=True,
                                    class_name=name
                                )
                        
                        # Add attributes
                        for attr in cls.get("attributes", []):
                            attr_name = attr.get("name", "")
                            if attr_name:
                                class_entity.attributes[attr_name] = Variable(
                                    name=attr_name,
                                    line_start=attr.get("line", 1),
                                    line_end=attr.get("line", 1),
                                    filename=str(file_path),
                                    var_type=attr.get("type"),
                                    is_attribute=True,
                                    class_name=name
                                )
                        
                        module.classes[name] = class_entity
                
                # Variables
                for var in data.get("variables", []):
                    name = var.get("name", "")
                    if name:
                        module.variables[name] = Variable(
                            name=name,
                            line_start=var.get("line", 1),
                            line_end=var.get("line", 1),
                            filename=str(file_path),
                            var_type=var.get("type"),
                            is_constant=var.get("is_constant", False)
                        )
                
                # Code metrics
                if "code_metrics" in data:
                    module.code_metrics = data["code_metrics"]
                
                return True
                
            except json.JSONDecodeError as e:
                self._logger.error(f"Error parsing LLM response as JSON: {str(e)}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error in LLM analysis for {file_path}: {str(e)}")
            return False
    
    def _analyze_cross_module_references(self, modules: Dict[str, Module]) -> None:
        """
        Analyze references between modules to build a dependency graph.
        
        Args:
            modules: Dictionary of modules to analyze
        """
        # Build a map of entity names to their modules
        entity_map = {}
        
        for module_path, module in modules.items():
            # Add functions
            for func_name in module.functions:
                entity_map[func_name] = module_path
            
            # Add classes
            for class_name in module.classes:
                entity_map[class_name] = module_path
        
        # Look for references
        for module_path, module in modules.items():
            # Check function calls
            for func_name, func in module.functions.items():
                for called_func in func.called_functions:
                    # Ignore method calls (with dots)
                    if '.' in called_func:
                        continue
                    
                    if called_func in entity_map and entity_map[called_func] != module_path:
                        # Found a reference to a function in another module
                        target_module = modules[entity_map[called_func]]
                        if called_func in target_module.functions:
                            target_func = target_module.functions[called_func]
                            target_func.references.append((module_path, func.line_start))
                            func.dependencies.append(called_func)
            
            # Check class inheritance
            for class_name, cls in module.classes.items():
                for base_class in cls.base_classes:
                    # Ignore qualified base classes
                    if '.' in base_class:
                        continue
                    
                    if base_class in entity_map and entity_map[base_class] != module_path:
                        # Found a reference to a class in another module
                        target_module = modules[entity_map[base_class]]
                        if base_class in target_module.classes:
                            target_class = target_module.classes[base_class]
                            target_class.references.append((module_path, cls.line_start))
                            cls.dependencies.append(base_class)
                            
    
    def find_related_entities(self, entity_name: str, project_files: Dict[str, Module]) -> List[Dict[str, Any]]:
        """
        Find entities related to a given entity in the project.
        
        Args:
            entity_name: Name of the entity to find relations for
            project_files: Dictionary of modules in the project
            
        Returns:
            List of related entities with relationship information
        """
        related_entities = []
        
        # Look for entities that reference or are referenced by the target entity
        for module_path, module in project_files.items():
            # Check functions
            for func_name, func in module.functions.items():
                # Check if this is our target entity
                if func_name == entity_name:
                    # Find functions that call this one
                    for other_module_path, other_module in project_files.items():
                        for other_func_name, other_func in other_module.functions.items():
                            if entity_name in other_func.called_functions:
                                related_entities.append({
                                    "name": other_func_name,
                                    "type": "function",
                                    "relationship": "calls",
                                    "filename": other_module_path,
                                    "line": other_func.line_start
                                })
                
                # Check if this function calls our target entity
                if entity_name in func.called_functions:
                    related_entities.append({
                        "name": func_name,
                        "type": "function",
                        "relationship": "called_by",
                        "filename": module_path,
                        "line": func.line_start
                    })
            
            # Check classes
            for class_name, cls in module.classes.items():
                # Check if this is our target entity
                if class_name == entity_name:
                    # Find classes that inherit from this one
                    for other_module_path, other_module in project_files.items():
                        for other_class_name, other_class in other_module.classes.items():
                            if entity_name in other_class.base_classes:
                                related_entities.append({
                                    "name": other_class_name,
                                    "type": "class",
                                    "relationship": "inherits_from",
                                    "filename": other_module_path,
                                    "line": other_class.line_start
                                })
                
                # Check if this class inherits from our target entity
                if entity_name in cls.base_classes:
                    related_entities.append({
                        "name": class_name,
                        "type": "class",
                        "relationship": "extended_by",
                        "filename": module_path,
                        "line": cls.line_start
                    })
                
                # Check class methods
                for method_name, method in cls.methods.items():
                    if entity_name in method.called_functions:
                        related_entities.append({
                            "name": f"{class_name}.{method_name}",
                            "type": "method",
                            "relationship": "called_by",
                            "filename": module_path,
                            "line": method.line_start
                        })
        
        return related_entities
    
    async def analyze_entity_usage(self, entity_name: str, project_root: Union[str, Path], depth: int = 1) -> Dict[str, Any]:
        """
        Analyze how a specific entity is used throughout the project.
        
        Args:
            entity_name: Name of the entity to analyze
            project_root: Root directory of the project
            depth: Relationship depth to explore
            
        Returns:
            Dictionary with entity usage information
        """
        root_path = Path(project_root)
        
        # Analyze project files first
        project_files = await self.analyze_project_files(root_path)
        
        # Find the entity in the project
        entity_info = None
        entity_module = None
        entity_type = None
        
        for module_path, module in project_files.items():
            # Check functions
            if entity_name in module.functions:
                entity_info = module.functions[entity_name].to_dict()
                entity_module = module
                entity_type = "function"
                break
            
            # Check classes
            if entity_name in module.classes:
                entity_info = module.classes[entity_name].to_dict()
                entity_module = module
                entity_type = "class"
                break
            
            # Check variables
            if entity_name in module.variables:
                entity_info = module.variables[entity_name].to_dict()
                entity_module = module
                entity_type = "variable"
                break
            
            # Check for class methods
            for class_name, cls in module.classes.items():
                if entity_name in cls.methods:
                    entity_info = cls.methods[entity_name].to_dict()
                    entity_info["class_name"] = class_name
                    entity_module = module
                    entity_type = "method"
                    break
                
                # Check for full qualified method name (class.method)
                if "." in entity_name:
                    class_part, method_part = entity_name.split(".", 1)
                    if class_name == class_part and method_part in cls.methods:
                        entity_info = cls.methods[method_part].to_dict()
                        entity_info["class_name"] = class_name
                        entity_module = module
                        entity_type = "method"
                        break
        
        if not entity_info:
            return {
                "entity_name": entity_name,
                "found": False,
                "message": f"Entity '{entity_name}' not found in the project"
            }
        
        # Find related entities
        related = self.find_related_entities(entity_name, project_files)
        
        # For methods, also check the class name if it's a qualified name
        if "." in entity_name and not related:
            class_part = entity_name.split(".", 1)[0]
            class_related = self.find_related_entities(class_part, project_files)
            related.extend(class_related)
        
        # Get recursive related entities if depth > 1
        if depth > 1:
            next_level = []
            for related_entity in related:
                name = related_entity["name"]
                if "." in name:  # Skip qualified names for simplicity
                    continue
                    
                sub_related = self.find_related_entities(name, project_files)
                for sub in sub_related:
                    if sub not in next_level and sub not in related:
                        sub["relationship_depth"] = 2
                        next_level.append(sub)
            
            related.extend(next_level)
        
        # Build result
        result = {
            "entity_name": entity_name,
            "found": True,
            "type": entity_type,
            "filename": entity_info["filename"],
            "line_start": entity_info["line_start"],
            "line_end": entity_info["line_end"],
            "related_entities": related,
            "details": entity_info
        }
        
        if entity_type == "function" or entity_type == "method":
            # Add information about function parameters
            result["parameters"] = entity_info.get("params", [])
            result["return_type"] = entity_info.get("return_type")
            result["complexity"] = entity_info.get("complexity")
            
            # If it's a method, add class information
            if entity_type == "method":
                result["class_name"] = entity_info.get("class_name")
                
                # Get class info
                if entity_module and entity_info.get("class_name") in entity_module.classes:
                    class_info = entity_module.classes[entity_info["class_name"]].to_dict()
                    result["class_details"] = {
                        "base_classes": class_info.get("base_classes", []),
                        "method_count": len(class_info.get("methods", {})),
                        "attribute_count": len(class_info.get("attributes", {}))
                    }
        
        elif entity_type == "class":
            # Add class-specific information
            result["base_classes"] = entity_info.get("base_classes", [])
            result["method_count"] = len(entity_info.get("methods", {}))
            result["attribute_count"] = len(entity_info.get("attributes", {}))
            result["methods"] = list(entity_info.get("methods", {}).keys())
            result["attributes"] = list(entity_info.get("attributes", {}).keys())
        
        elif entity_type == "variable":
            # Add variable-specific information
            result["var_type"] = entity_info.get("var_type")
            result["value"] = entity_info.get("value")
            result["is_constant"] = entity_info.get("is_constant", False)
        
        return result
    
    async def summarize_code_entity(self, entity_name: str, project_root: Union[str, Path]) -> str:
        """
        Generate a natural language summary of a code entity.
        
        Args:
            entity_name: Name of the entity to summarize
            project_root: Root directory of the project
            
        Returns:
            String with a natural language summary
        """
        # First, get the entity usage information
        usage_info = await self.analyze_entity_usage(entity_name, project_root)
        
        if not usage_info.get("found", False):
            return f"Could not find entity '{entity_name}' in the project."
        
        # Create a detailed prompt for the LLM
        entity_type = usage_info.get("type", "unknown")
        filename = usage_info.get("filename", "unknown")
        
        # Read the actual file content around the entity definition
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            lines = file_content.splitlines()
            start_line = max(0, usage_info.get("line_start", 1) - 1)  # Lines are 1-indexed
            end_line = min(len(lines), usage_info.get("line_end", start_line + 10))
            
            entity_code = "\n".join(lines[start_line:end_line])
            
            # Get the language
            file_info = detect_file_type(Path(filename))
            language = file_info.get("language", "").lower()
            
            # Build the prompt
            prompt = f"""
You are reviewing code and need to provide a clear, concise summary of a specific code entity.

Entity Name: {entity_name}
Entity Type: {entity_type}
File: {Path(filename).name}
Language: {language}

Here is the code for this entity:
```{language}
{entity_code}
```

Additional Information:
"""
            
            if entity_type == "function" or entity_type == "method":
                params = usage_info.get("parameters", [])
                return_type = usage_info.get("return_type", "unknown")
                complexity = usage_info.get("complexity", "unknown")
                
                prompt += f"""
- Parameters: {', '.join(params)}
- Return Type: {return_type}
- Complexity: {complexity}
"""
                
                if entity_type == "method":
                    class_name = usage_info.get("class_name", "unknown")
                    prompt += f"- Part of Class: {class_name}\n"
                    
                    class_details = usage_info.get("class_details", {})
                    if class_details:
                        base_classes = class_details.get("base_classes", [])
                        if base_classes:
                            prompt += f"- Class Inherits From: {', '.join(base_classes)}\n"
            
            elif entity_type == "class":
                base_classes = usage_info.get("base_classes", [])
                methods = usage_info.get("methods", [])
                attributes = usage_info.get("attributes", [])
                
                prompt += f"""
- Base Classes: {', '.join(base_classes) if base_classes else 'None'}
- Methods: {', '.join(methods[:5]) + ('...' if len(methods) > 5 else '') if methods else 'None'}
- Attributes: {', '.join(attributes[:5]) + ('...' if len(attributes) > 5 else '') if attributes else 'None'}
"""
            
            elif entity_type == "variable":
                var_type = usage_info.get("var_type", "unknown")
                value = usage_info.get("value", "unknown")
                is_constant = usage_info.get("is_constant", False)
                
                prompt += f"""
- Type: {var_type}
- Value: {value}
- Is Constant: {is_constant}
"""
            
            # Add relationship information
            related = usage_info.get("related_entities", [])
            if related:
                callers = [r["name"] for r in related if r.get("relationship") == "calls"]
                called = [r["name"] for r in related if r.get("relationship") == "called_by"]
                inherits = [r["name"] for r in related if r.get("relationship") == "inherits_from"]
                extends = [r["name"] for r in related if r.get("relationship") == "extended_by"]
                
                prompt += "\nRelationships:\n"
                
                if callers:
                    prompt += f"- Called by: {', '.join(callers[:5]) + ('...' if len(callers) > 5 else '')}\n"
                
                if called:
                    prompt += f"- Calls: {', '.join(called[:5]) + ('...' if len(called) > 5 else '')}\n"
                
                if inherits:
                    prompt += f"- Inherits from: {', '.join(inherits)}\n"
                
                if extends:
                    prompt += f"- Extended by: {', '.join(extends[:5]) + ('...' if len(extends) > 5 else '')}\n"
            
            prompt += """
Based on the code and information provided, give a concise, useful summary of what this entity does,
its role in the codebase, and any notable design patterns or implementation details. Keep the summary
focused and to-the-point - ideally 3-5 sentences.
"""
            
            # Call AI service
            api_request = GeminiRequest(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            response = await gemini_client.generate_text(api_request)
            
            return response.text.strip()
            
        except Exception as e:
            self._logger.error(f"Error generating summary for {entity_name}: {str(e)}")
            return f"Error generating summary for {entity_name}: {str(e)}"
    
    async def get_entity_code(self, entity_name: str, project_root: Union[str, Path]) -> Optional[str]:
        """
        Get the source code for a specific entity.
        
        Args:
            entity_name: Name of the entity to get code for
            project_root: Root directory of the project
            
        Returns:
            String with the entity's source code or None if not found
        """
        # First, get the entity usage information
        usage_info = await self.analyze_entity_usage(entity_name, project_root)
        
        if not usage_info.get("found", False):
            return None
        
        # Get the file path and line range
        filename = usage_info.get("filename")
        start_line = usage_info.get("line_start", 1)
        end_line = usage_info.get("line_end", start_line)
        
        # Read the file content
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get the specified line range (adjust for 0-based indexing)
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)
            
            return "".join(lines[start_idx:end_idx])
            
        except Exception as e:
            self._logger.error(f"Error getting code for {entity_name}: {str(e)}")
            return None
    
    def get_module_dependencies(self, modules: Dict[str, Module]) -> Dict[str, List[str]]:
        """
        Get a map of module dependencies.
        
        Args:
            modules: Dictionary of modules to analyze
            
        Returns:
            Dictionary with module paths as keys and lists of dependencies as values
        """
        dependencies = {}
        
        for module_path, module in modules.items():
            dependencies[module_path] = module.dependencies
        
        return dependencies
    
    def calculate_project_metrics(self, modules: Dict[str, Module]) -> Dict[str, Any]:
        """
        Calculate metrics for the entire project.
        
        Args:
            modules: Dictionary of modules to analyze
            
        Returns:
            Dictionary with project metrics
        """
        total_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        function_count = 0
        class_count = 0
        complexity = 0
        
        for module in modules.values():
            metrics = module.code_metrics
            total_lines += metrics.get("total_lines", 0)
            code_lines += metrics.get("code_lines", 0)
            comment_lines += metrics.get("comment_lines", 0)
            blank_lines += metrics.get("blank_lines", 0)
            function_count += metrics.get("function_count", 0) + sum(len(cls.methods) for cls in module.classes.values())
            class_count += metrics.get("class_count", 0)
            complexity += metrics.get("complexity", 0)
        
        # Calculate percentages
        comment_ratio = comment_lines / code_lines if code_lines > 0 else 0
        blank_ratio = blank_lines / total_lines if total_lines > 0 else 0
        average_function_complexity = complexity / function_count if function_count > 0 else 0
        
        return {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "function_count": function_count,
            "class_count": class_count,
            "complexity": complexity,
            "comment_ratio": comment_ratio,
            "blank_ratio": blank_ratio,
            "average_function_complexity": average_function_complexity,
            "module_count": len(modules),
            "file_count": len(modules)
        }

# Global semantic analyzer instance
semantic_analyzer = SemanticAnalyzer()
