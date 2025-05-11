# angela/generation/architecture.py
"""
Architectural analysis and improvements for Angela CLI.

This module provides capabilities for analyzing project architecture,
detecting anti-patterns, and suggesting improvements.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json
import re

from angela.ai.client import gemini_client, GeminiRequest
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class ArchitecturalPattern:
    """Base class for architectural patterns."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize the architectural pattern.
        
        Args:
            name: Pattern name
            description: Pattern description
        """
        self.name = name
        self.description = description
    
    async def detect(self, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if the pattern is present in the project.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            Dictionary with detection results
        """
        raise NotImplementedError("Subclasses must implement detect")
    
    def get_recommendations(self, detection_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recommendations based on detection results.
        
        Args:
            detection_result: Results from the detect method
            
        Returns:
            List of recommendation dictionaries
        """
        raise NotImplementedError("Subclasses must implement get_recommendations")

class AntiPattern:
    """Base class for architectural anti-patterns."""
    
    def __init__(self, name: str, description: str, severity: str):
        """
        Initialize the anti-pattern.
        
        Args:
            name: Anti-pattern name
            description: Anti-pattern description
            severity: Severity level (low, medium, high)
        """
        self.name = name
        self.description = description
        self.severity = severity
    
    async def detect(self, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if the anti-pattern is present in the project.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            Dictionary with detection results
        """
        raise NotImplementedError("Subclasses must implement detect")
    
    def get_recommendations(self, detection_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recommendations to fix the anti-pattern.
        
        Args:
            detection_result: Results from the detect method
            
        Returns:
            List of recommendation dictionaries
        """
        raise NotImplementedError("Subclasses must implement get_recommendations")

class MvcPattern(ArchitecturalPattern):
    """Model-View-Controller pattern detector."""
    
    def __init__(self):
        """Initialize the MVC pattern detector."""
        super().__init__(
            name="Model-View-Controller",
            description="Separates application logic into three components: Model (data), View (presentation), and Controller (logic)"
        )
    
    async def detect(self, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if MVC pattern is used in the project.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            Dictionary with detection results
        """
        logger.debug("Detecting MVC pattern")
        
        # Default result
        result = {
            "pattern": self.name,
            "present": False,
            "confidence": 0.0,
            "components": {
                "models": [],
                "views": [],
                "controllers": []
            }
        }
        
        # Check file structure for MVC pattern
        models = []
        views = []
        controllers = []
        
        for file_info in project_analysis.get("files", []):
            file_path = file_info.get("path", "").lower()
            file_content = file_info.get("content", "")
            
            # Check for models
            if "model" in file_path or "/models/" in file_path:
                models.append(file_path)
            elif file_content and re.search(r'class\s+\w*Model\b', file_content):
                models.append(file_path)
            
            # Check for views
            if "view" in file_path or "/views/" in file_path:
                views.append(file_path)
            elif file_path.endswith((".html", ".jsx", ".tsx", ".vue")) or "template" in file_path:
                views.append(file_path)
            elif file_content and re.search(r'class\s+\w*View\b', file_content):
                views.append(file_path)
            
            # Check for controllers
            if "controller" in file_path or "/controllers/" in file_path:
                controllers.append(file_path)
            elif file_content and re.search(r'class\s+\w*Controller\b', file_content):
                controllers.append(file_path)
        
        # Update result with components found
        result["components"]["models"] = models
        result["components"]["views"] = views
        result["components"]["controllers"] = controllers
        
        # Calculate confidence
        if models and views and controllers:
            result["present"] = True
            result["confidence"] = 0.9  # High confidence if all three components found
        elif (models and views) or (models and controllers) or (views and controllers):
            result["present"] = True
            result["confidence"] = 0.6  # Medium confidence if two components found
        elif models or views or controllers:
            result["present"] = False
            result["confidence"] = 0.3  # Low confidence if only one component found
        
        return result
    
    def get_recommendations(self, detection_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recommendations for improving MVC pattern usage.
        
        Args:
            detection_result: Results from the detect method
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        if detection_result["present"]:
            # MVC pattern is present, check if all components are balanced
            models = detection_result["components"]["models"]
            views = detection_result["components"]["views"]
            controllers = detection_result["components"]["controllers"]
            
            if len(models) < len(controllers) / 2:
                recommendations.append({
                    "title": "Insufficient Model Separation",
                    "description": "There are significantly fewer Model files than Controllers, which may indicate business logic leaking into Controllers.",
                    "action": "Consider extracting data models from Controllers into separate Model classes.",
                    "priority": "medium"
                })
            
            if not controllers and models and views:
                recommendations.append({
                    "title": "Missing Controller Layer",
                    "description": "Models and Views are present, but no clear Controller layer was detected.",
                    "action": "Implement Controllers to handle the interaction between Models and Views.",
                    "priority": "high"
                })
        else:
            # MVC pattern is not present
            if detection_result["confidence"] > 0.0:
                # Some components found, but not all
                recommendations.append({
                    "title": "Incomplete MVC Implementation",
                    "description": "Some MVC components are present, but the pattern is not fully implemented.",
                    "action": "Consider fully adopting the MVC pattern by adding the missing components.",
                    "priority": "medium"
                })
            else:
                # No components found
                recommendations.append({
                    "title": "Consider MVC Pattern",
                    "description": "The project doesn't appear to use the MVC pattern, which can help with code organization and maintainability.",
                    "action": "Consider refactoring to separate concerns into Model, View, and Controller components.",
                    "priority": "low"
                })
        
        return recommendations

class SingleResponsibilityAntiPattern(AntiPattern):
    """Detects violations of the Single Responsibility Principle."""
    
    def __init__(self):
        """Initialize the single responsibility anti-pattern detector."""
        super().__init__(
            name="Single Responsibility Violation",
            description="Classes or modules that have more than one reason to change",
            severity="medium"
        )
    
    async def detect(self, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect violations of the Single Responsibility Principle.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            Dictionary with detection results
        """
        logger.debug("Detecting Single Responsibility violations")
        
        # Default result
        result = {
            "anti_pattern": self.name,
            "detected": False,
            "instances": [],
            "severity": self.severity
        }
        
        # Check for large classes with many methods
        for file_info in project_analysis.get("files", []):
            if not file_info.get("content"):
                continue
            
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            # Skip non-source files
            if file_info.get("type") != "source_code":
                continue
            
            language = file_info.get("language", "").lower()
            
            if language in ["python", "java", "javascript", "typescript"]:
                # Check for classes with too many methods
                classes = self._extract_classes(content, language)
                
                for class_info in classes:
                    # Check number of methods
                    if len(class_info["methods"]) > 10:  # Arbitrary threshold
                        # Check for different categories of methods
                        categories = self._categorize_methods(class_info["methods"], language)
                        
                        if len(categories) >= 3:  # If methods fall into 3+ categories, likely has multiple responsibilities
                            result["instances"].append({
                                "file": file_path,
                                "class": class_info["name"],
                                "method_count": len(class_info["methods"]),
                                "categories": categories,
                                "confidence": min(0.5 + (len(categories) - 3) * 0.1, 0.9)  # Higher confidence with more categories
                            })
        
        if result["instances"]:
            result["detected"] = True
        
        return result
    
    def _extract_classes(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract classes and their methods from code.
        
        Args:
            content: Source code content
            language: Programming language
            
        Returns:
            List of dictionaries with class info
        """
        classes = []
        
        if language == "python":
            # Extract Python classes
            class_pattern = r'class\s+(\w+)(?:\(.*?\))?:'
            method_pattern = r'\s+def\s+(\w+)\s*\('
            
            class_matches = re.finditer(class_pattern, content)
            
            for class_match in class_matches:
                class_name = class_match.group(1)
                class_start = class_match.end()
                
                # Find the end of the class (indentation level)
                class_content = ""
                for line in content[class_start:].splitlines():
                    if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                        break
                    class_content += line + "\n"
                
                # Extract methods
                methods = []
                for method_match in re.finditer(method_pattern, class_content):
                    method_name = method_match.group(1)
                    if method_name != "__init__":  # Skip constructor
                        methods.append(method_name)
                
                classes.append({
                    "name": class_name,
                    "methods": methods
                })
        
        elif language in ["java", "javascript", "typescript"]:
            # Extract classes (simplified)
            class_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{'
            method_pattern = r'(?:public|private|protected)?\s+(?:static\s+)?(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*{(?:[^{}]|{[^{}]*})*}'
            
            class_matches = re.finditer(class_pattern, content)
            
            for class_match in class_matches:
                class_name = class_match.group(1)
                class_start = class_match.start()
                
                # Find the class block by counting braces
                brace_count = 0
                class_end = class_start
                in_class = False
                
                for i, c in enumerate(content[class_start:]):
                    if c == '{':
                        if not in_class:
                            in_class = True
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if in_class and brace_count == 0:
                            class_end = class_start + i + 1
                            break
                
                class_content = content[class_start:class_end]
                
                # Extract methods
                methods = []
                for method_match in re.finditer(method_pattern, class_content):
                    method_name = method_match.group(1)
                    if method_name != "constructor" and not method_name.startswith("get") and not method_name.startswith("set"):
                        methods.append(method_name)
                
                classes.append({
                    "name": class_name,
                    "methods": methods
                })
        
        return classes
    
    def _categorize_methods(self, methods: List[str], language: str) -> Dict[str, List[str]]:
        """
        Categorize methods into different responsibilities.
        
        Args:
            methods: List of method names
            language: Programming language
            
        Returns:
            Dictionary mapping categories to method names
        """
        categories = {}
        
        # Common categories and their keywords
        categories_keywords = {
            "data_access": ["save", "load", "read", "write", "fetch", "store", "retrieve", "query", "find", "get", "set", "select", "insert", "update", "delete", "persist", "repository", "dao"],
            "business_logic": ["calculate", "compute", "process", "validate", "check", "verify", "evaluate", "analyze", "generate", "create", "build", "make", "service"],
            "presentation": ["display", "show", "render", "view", "draw", "paint", "print", "format", "transform", "convert", "ui", "gui", "interface"],
            "networking": ["connect", "disconnect", "send", "receive", "post", "get", "put", "delete", "request", "response", "url", "uri", "http", "api", "rest", "soap", "websocket"],
            "file_io": ["file", "stream", "open", "close", "read", "write", "input", "output", "io", "path", "directory", "folder"],
            "concurrency": ["thread", "async", "await", "parallel", "concurrent", "lock", "mutex", "semaphore", "synchronize", "task", "job", "worker", "pool"],
            "utility": ["util", "helper", "common", "shared", "factory", "builder", "converter", "mapper", "utils"]
        }
        
        # Categorize methods based on name
        for method in methods:
            method_lower = method.lower()
            categorized = False
            
            for category, keywords in categories_keywords.items():
                for keyword in keywords:
                    if keyword in method_lower:
                        if category not in categories:
                            categories[category] = []
                        categories[category].append(method)
                        categorized = True
                        break
                
                if categorized:
                    break
            
            # If method doesn't match any category, put it in "other"
            if not categorized:
                if "other" not in categories:
                    categories["other"] = []
                categories["other"].append(method)
        
        return categories
    
    def get_recommendations(self, detection_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recommendations for fixing Single Responsibility Principle violations.
        
        Args:
            detection_result: Results from the detect method
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        if detection_result["detected"]:
            for instance in detection_result["instances"]:
                # Create a recommendation for each instance
                categories_str = ", ".join(instance["categories"].keys())
                
                recommendations.append({
                    "title": f"Refactor Class: {instance['class']}",
                    "description": f"This class has multiple responsibilities: {categories_str}",
                    "action": f"Consider splitting '{instance['class']}' into multiple classes, each with a single responsibility.",
                    "priority": "medium" if instance["confidence"] > 0.7 else "low"
                })
        
        return recommendations

class GodObjectAntiPattern(AntiPattern):
    """Detects God Objects - classes that know or do too much."""
    
    def __init__(self):
        """Initialize the God Object anti-pattern detector."""
        super().__init__(
            name="God Object",
            description="Classes that know or do too much, often with excessive size and responsibilities",
            severity="high"
        )
    
    async def detect(self, project_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect God Objects in the project.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            Dictionary with detection results
        """
        logger.debug("Detecting God Objects")
        
        # Default result
        result = {
            "anti_pattern": self.name,
            "detected": False,
            "instances": [],
            "severity": self.severity
        }
        
        # Define thresholds for various metrics
        thresholds = {
            "lines": 500,  # Lines of code
            "methods": 20,  # Number of methods
            "fields": 15,   # Number of fields/properties
            "imports": 15,  # Number of imports
            "dependencies": 10  # Number of dependencies on other classes
        }
        
        # Check each file for potential God Objects
        for file_info in project_analysis.get("files", []):
            if not file_info.get("content"):
                continue
            
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            
            # Skip non-source files
            if file_info.get("type") != "source_code":
                continue
            
            language = file_info.get("language", "").lower()
            
            if language in ["python", "java", "javascript", "typescript"]:
                # Extract classes
                classes = self._extract_classes_with_metrics(content, language)
                
                for class_info in classes:
                    # Check if any metric exceeds thresholds
                    violations = {}
                    for metric, value in class_info["metrics"].items():
                        if metric in thresholds and value > thresholds[metric]:
                            violations[metric] = value
                    
                    if violations:
                        # Calculate violation severity
                        violation_count = len(violations)
                        violation_ratio = sum(violations[m] / thresholds[m] for m in violations) / len(violations)
                        confidence = min(0.5 + (violation_count * 0.1) + (violation_ratio * 0.2), 0.95)
                        
                        result["instances"].append({
                            "file": file_path,
                            "class": class_info["name"],
                            "violations": violations,
                            "metrics": class_info["metrics"],
                            "confidence": confidence
                        })
        
        if result["instances"]:
            result["detected"] = True
        
        return result
    
    def _extract_classes_with_metrics(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract classes and calculate metrics.
        
        Args:
            content: Source code content
            language: Programming language
            
        Returns:
            List of dictionaries with class info and metrics
        """
        classes = []
        
        if language == "python":
            # Extract Python classes
            class_pattern = r'class\s+(\w+)(?:\(.*?\))?:'
            method_pattern = r'\s+def\s+(\w+)\s*\('
            field_pattern = r'\s+self\.(\w+)\s*='
            import_pattern = r'(?:import|from)\s+[\w.]+'
            
            # Count imports
            imports = len(re.findall(import_pattern, content))
            
            class_matches = re.finditer(class_pattern, content)
            
            for class_match in class_matches:
                class_name = class_match.group(1)
                class_start = class_match.end()
                
                # Find the end of the class (indentation level)
                class_content = ""
                class_lines = 0
                for line in content[class_start:].splitlines():
                    if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                        break
                    class_content += line + "\n"
                    class_lines += 1
                
                # Extract methods
                methods = re.findall(method_pattern, class_content)
                
                # Extract fields
                fields = re.findall(field_pattern, class_content)
                
                # Calculate other dependencies (simplified)
                dependencies = set()
                for line in class_content.splitlines():
                    # Look for other class instantiations
                    instance_matches = re.findall(r'=\s*(\w+)\(', line)
                    for instance in instance_matches:
                        if instance != class_name and instance[0].isupper():  # Potential class
                            dependencies.add(instance)
                
                classes.append({
                    "name": class_name,
                    "content": class_content,
                    "metrics": {
                        "lines": class_lines,
                        "methods": len(methods),
                        "fields": len(fields),
                        "imports": imports,
                        "dependencies": len(dependencies)
                    }
                })
        
        elif language in ["java", "javascript", "typescript"]:
            # Extract classes (simplified)
            class_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{'
            method_pattern = r'(?:public|private|protected)?\s+(?:static\s+)?(?:\w+\s+)?(\w+)\s*\(['
            field_pattern = r'(?:public|private|protected)?\s+(?:static\s+)?(?:final\s+)?[\w<>[\],\s]+\s+(\w+)\s*[;=]'
            import_pattern = r'import\s+[\w.]+'
            
            # Count imports
            imports = len(re.findall(import_pattern, content))
            
            class_matches = re.finditer(class_pattern, content)
            
            for class_match in class_matches:
                class_name = class_match.group(1)
                class_start = class_match.start()
                
                # Find the class block by counting braces
                brace_count = 0
                class_end = class_start
                in_class = False
                
                for i, c in enumerate(content[class_start:]):
                    if c == '{':
                        if not in_class:
                            in_class = True
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if in_class and brace_count == 0:
                            class_end = class_start + i + 1
                            break
                
                class_content = content[class_start:class_end]
                class_lines = class_content.count('\n')
                
                # Extract methods
                methods = re.findall(method_pattern, class_content)
                
                # Extract fields
                fields = re.findall(field_pattern, class_content)
                
                # Calculate other dependencies (simplified)
                dependencies = set()
                for line in class_content.splitlines():
                    # Look for other class instantiations
                    instance_matches = re.findall(r'new\s+(\w+)\(', line)
                    for instance in instance_matches:
                        if instance != class_name:
                            dependencies.add(instance)
                
                classes.append({
                    "name": class_name,
                    "content": class_content,
                    "metrics": {
                        "lines": class_lines,
                        "methods": len(methods),
                        "fields": len(fields),
                        "imports": imports,
                        "dependencies": len(dependencies)
                    }
                })
        
        return classes
    
    def get_recommendations(self, detection_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recommendations for fixing God Objects.
        
        Args:
            detection_result: Results from the detect method
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        if detection_result["detected"]:
            for instance in detection_result["instances"]:
                # Create specific recommendations based on violations
                violations_msg = []
                
                if "lines" in instance["violations"]:
                    violations_msg.append(f"excessive size ({instance['violations']['lines']} lines)")
                if "methods" in instance["violations"]:
                    violations_msg.append(f"too many methods ({instance['violations']['methods']})")
                if "fields" in instance["violations"]:
                    violations_msg.append(f"too many fields ({instance['violations']['fields']})")
                if "dependencies" in instance["violations"]:
                    violations_msg.append(f"too many dependencies ({instance['violations']['dependencies']})")
                
                violations_str = ", ".join(violations_msg)
                
                # Main recommendation
                recommendations.append({
                    "title": f"Refactor God Object: {instance['class']}",
                    "description": f"This class exhibits God Object symptoms: {violations_str}",
                    "action": f"Break '{instance['class']}' into smaller, more focused classes following the Single Responsibility Principle.",
                    "priority": "high" if instance["confidence"] > 0.8 else "medium"
                })
                
                # Add specific tactical recommendations
                if "methods" in instance["violations"] and instance["violations"]["methods"] > 25:
                    recommendations.append({
                        "title": f"Extract Classes from {instance['class']}",
                        "description": f"This class has an excessive number of methods ({instance['violations']['methods']}).",
                        "action": "Group related methods and extract them into new classes with clear responsibilities.",
                        "priority": "high"
                    })
                
                if "dependencies" in instance["violations"] and instance["violations"]["dependencies"] > 12:
                    recommendations.append({
                        "title": f"Reduce Dependencies in {instance['class']}",
                        "description": f"This class depends on too many other classes ({instance['violations']['dependencies']}).",
                        "action": "Use dependency injection or introduce service locators to reduce direct dependencies.",
                        "priority": "medium"
                    })
        
        return recommendations

class ArchitecturalAnalyzer:
    """
    Analyzer for project architecture, detecting patterns and anti-patterns.
    """
    
    def __init__(self):
        """Initialize the architectural analyzer."""
        self._logger = logger
        
        # Register patterns and anti-patterns
        self._patterns = [
            MvcPattern(),
            # Add more patterns here
        ]
        
        self._anti_patterns = [
            SingleResponsibilityAntiPattern(),
            GodObjectAntiPattern(),
            # Add more anti-patterns here
        ]
    
    async def analyze_architecture(
        self, 
        project_path: Union[str, Path],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze project architecture.
        
        Args:
            project_path: Path to the project
            context: Additional context information
            
        Returns:
            Dictionary with analysis results
        """
        self._logger.info(f"Analyzing architecture of project at {project_path}")
        
        # Analyze project structure
        project_analysis = await self._analyze_project_structure(project_path, context)
        
        # Detect patterns
        patterns_results = await self._detect_patterns(project_analysis)
        
        # Detect anti-patterns
        anti_patterns_results = await self._detect_anti_patterns(project_analysis)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(patterns_results, anti_patterns_results)
        
        return {
            "project_path": str(project_path),
            "patterns": patterns_results,
            "anti_patterns": anti_patterns_results,
            "recommendations": recommendations,
            "project_analysis": project_analysis
        }
    
    async def _analyze_project_structure(
        self, 
        project_path: Union[str, Path],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze project structure.
        
        Args:
            project_path: Path to the project
            context: Additional context information
            
        Returns:
            Dictionary with project analysis
        """
        self._logger.info(f"Analyzing project structure at {project_path}")
        
        # Convert to Path object
        project_path = Path(project_path)
        
        # Use context if available
        if context and "enhanced_project" in context:
            return {
                "project_type": context["enhanced_project"].get("type", "unknown"),
                "frameworks": context["enhanced_project"].get("frameworks", {}),
                "dependencies": context["enhanced_project"].get("dependencies", {}),
                "files": context.get("files", []),
                "path": str(project_path)
            }
        
        # Perform a simplified project analysis
        project_analysis = {
            "project_type": "unknown",
            "frameworks": {},
            "dependencies": {},
            "files": [],
            "path": str(project_path)
        }
        
        # Determine project type
        if (project_path / "requirements.txt").exists() or (project_path / "setup.py").exists() or (project_path / "pyproject.toml").exists():
            project_analysis["project_type"] = "python"
        elif (project_path / "package.json").exists():
            project_analysis["project_type"] = "node"
        elif (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
            project_analysis["project_type"] = "java"
        
        # Collect file information
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                # Skip common directories to ignore
                if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "venv", ".idea", ".vscode"]):
                    continue
                
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(project_path)
                
                # Get basic file info
                file_info = {
                    "path": str(rel_path),
                    "full_path": str(file_path),
                    "type": None,
                    "language": None,
                    "content": None
                }
                
                # Try to determine file type and language
                try:
                    from angela.context.file_detector import detect_file_type
                    type_info = detect_file_type(file_path)
                    file_info["type"] = type_info.get("type")
                    file_info["language"] = type_info.get("language")
                    
                    # Read content for source code files (limit to prevent memory issues)
                    if type_info.get("type") == "source_code" and file_path.stat().st_size < 100000:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            file_info["content"] = f.read()
                except Exception as e:
                    self._logger.debug(f"Error analyzing file {file_path}: {str(e)}")
                
                project_analysis["files"].append(file_info)
        
        return project_analysis
    
    async def _detect_patterns(self, project_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect architectural patterns in the project.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            List of pattern detection results
        """
        self._logger.info("Detecting architectural patterns")
        
        results = []
        
        # Run all pattern detectors
        for pattern in self._patterns:
            try:
                pattern_result = await pattern.detect(project_analysis)
                results.append(pattern_result)
                self._logger.debug(f"Pattern '{pattern.name}' detected: {pattern_result['present']}")
            except Exception as e:
                self._logger.error(f"Error detecting pattern '{pattern.name}': {str(e)}")
        
        return results
    
    async def _detect_anti_patterns(self, project_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect architectural anti-patterns in the project.
        
        Args:
            project_analysis: Analysis of the project
            
        Returns:
            List of anti-pattern detection results
        """
        self._logger.info("Detecting architectural anti-patterns")
        
        results = []
        
        # Run all anti-pattern detectors
        for anti_pattern in self._anti_patterns:
            try:
                anti_pattern_result = await anti_pattern.detect(project_analysis)
                results.append(anti_pattern_result)
                self._logger.debug(f"Anti-pattern '{anti_pattern.name}' detected: {anti_pattern_result['detected']}")
            except Exception as e:
                self._logger.error(f"Error detecting anti-pattern '{anti_pattern.name}': {str(e)}")
        
        return results
    
    async def _generate_recommendations(
        self, 
        patterns_results: List[Dict[str, Any]],
        anti_patterns_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on detected patterns and anti-patterns.
        
        Args:
            patterns_results: Pattern detection results
            anti_patterns_results: Anti-pattern detection results
            
        Returns:
            List of recommendations
        """
        self._logger.info("Generating architecture recommendations")
        
        recommendations = []
        
        # Generate recommendations from patterns
        for pattern_result in patterns_results:
            pattern_name = pattern_result["pattern"]
            pattern = next((p for p in self._patterns if p.name == pattern_name), None)
            
            if pattern:
                pattern_recommendations = pattern.get_recommendations(pattern_result)
                recommendations.extend(pattern_recommendations)
        
        # Generate recommendations from anti-patterns
        for anti_pattern_result in anti_patterns_results:
            anti_pattern_name = anti_pattern_result["anti_pattern"]
            anti_pattern = next((ap for ap in self._anti_patterns if ap.name == anti_pattern_name), None)
            
            if anti_pattern and anti_pattern_result["detected"]:
                anti_pattern_recommendations = anti_pattern.get_recommendations(anti_pattern_result)
                recommendations.extend(anti_pattern_recommendations)
        
        # Generate general recommendations using AI for more complex analysis
        if patterns_results or anti_patterns_results:
            ai_recommendations = await self._generate_ai_recommendations(patterns_results, anti_patterns_results)
            recommendations.extend(ai_recommendations)
        
        return recommendations
    
    async def _generate_ai_recommendations(
        self, 
        patterns_results: List[Dict[str, Any]],
        anti_patterns_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate additional recommendations using AI.
        
        Args:
            patterns_results: Pattern detection results
            anti_patterns_results: Anti-pattern detection results
            
        Returns:
            List of AI-generated recommendations
        """
        self._logger.debug("Generating AI recommendations")
        
        # Build prompt for AI
        prompt = """
You are an expert software architect tasked with providing architectural recommendations based on detected patterns and anti-patterns in a project.

Here are the detected architectural patterns:
"""
        
        # Add pattern information
        for pattern_result in patterns_results:
            prompt += f"\n- Pattern: {pattern_result['pattern']}"
            prompt += f"\n  Present: {pattern_result['present']}"
            prompt += f"\n  Confidence: {pattern_result['confidence']:.2f}"
            
            if "components" in pattern_result:
                prompt += "\n  Components:"
                for component_type, components in pattern_result["components"].items():
                    prompt += f"\n    - {component_type}: {len(components)} files"
        
        prompt += "\n\nHere are the detected architectural anti-patterns:"
        
        # Add anti-pattern information
        for anti_pattern_result in anti_patterns_results:
            prompt += f"\n- Anti-pattern: {anti_pattern_result['anti_pattern']}"
            prompt += f"\n  Detected: {anti_pattern_result['detected']}"
            prompt += f"\n  Severity: {anti_pattern_result['severity']}"
            
            if anti_pattern_result["detected"] and "instances" in anti_pattern_result:
                prompt += f"\n  Instances: {len(anti_pattern_result['instances'])}"
                
                # Add details for the first few instances
                for i, instance in enumerate(anti_pattern_result["instances"][:3]):
                    prompt += f"\n    {i+1}. Class: {instance.get('class', 'Unknown')}"
                    if "violations" in instance:
                        violations = ", ".join(f"{v}: {val}" for v, val in instance["violations"].items())
                        prompt += f"\n       Violations: {violations}"
        
        prompt += """

Based on the above information, provide 3-5 high-level architectural recommendations that would improve the project's design.
For each recommendation, include:
1. A title (concise description)
2. A detailed explanation
3. Concrete action steps
4. Priority (high, medium, low)

Format your response as a JSON array of recommendation objects, like this:
[
  {
    "title": "Clear recommendation title",
    "description": "Detailed explanation of the issue",
    "action": "Specific action steps to implement the recommendation",
    "priority": "high|medium|low"
  },
  ...
]
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3
        )
        
        try:
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response
            recommendations = []
            
            # Extract JSON
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'(\[.*\])', response.text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Assume the entire response is JSON
                    json_str = response.text
            
            try:
                recommendations = json.loads(json_str)
            except json.JSONDecodeError:
                self._logger.error("Failed to parse AI recommendations as JSON")
                recommendations = []
            
            # Add source information
            for rec in recommendations:
                rec["source"] = "ai"
            
            return recommendations
            
        except Exception as e:
            self._logger.error(f"Error generating AI recommendations: {str(e)}")
            return []

async def analyze_project_architecture(
    project_path: Union[str, Path],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze project architecture.
    
    Args:
        project_path: Path to the project
        context: Additional context information
        
    Returns:
        Dictionary with analysis results
    """
    analyzer = ArchitecturalAnalyzer()
    return await analyzer.analyze_architecture(project_path, context)

# Global architectural analyzer instance
architectural_analyzer = ArchitecturalAnalyzer()
