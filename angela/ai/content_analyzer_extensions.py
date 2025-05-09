# angela/ai/content_analyzer_extensions.py

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import re
import json

from angela.ai.content_analyzer import ContentAnalyzer, content_analyzer
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class EnhancedContentAnalyzer(ContentAnalyzer):
    """Extended content analyzer with support for additional file types and languages."""
    
    # Language-specific analysis handlers 
    LANGUAGE_HANDLERS = {
        # Existing handlers
        "Python": "_analyze_python",
        "JavaScript": "_analyze_javascript",
        "HTML": "_analyze_html",
        "CSS": "_analyze_css",
        
        # New handlers
        "TypeScript": "_analyze_typescript",
        "Java": "_analyze_java",
        "Rust": "_analyze_rust",
        "Go": "_analyze_go",
        "Ruby": "_analyze_ruby",
        "PHP": "_analyze_php",
        "C": "_analyze_c",
        "CPP": "_analyze_cpp",
        "CSharp": "_analyze_csharp",
        "Swift": "_analyze_swift",
        "Kotlin": "_analyze_kotlin",
        
        # Data formats
        "JSON": "_analyze_json",
        "YAML": "_analyze_yaml",
        "XML": "_analyze_xml",
        "CSV": "_analyze_csv",
        
        # Config files
        "Dockerfile": "_analyze_dockerfile",
        "Makefile": "_analyze_makefile",
    }
    
    async def analyze_content(self, file_path, request=None):
        """Override the base analyze_content method to use specialized analyzers."""
        result = await super().analyze_content(file_path, request)
        
        # If we got an error, return it
        if "error" in result:
            return result
        
        # Check if we have a specialized analyzer for this file type
        file_type = result.get("type", "unknown")
        language = result.get("language", "unknown").lower()
        
        specialized_analyzer = self._specialized_analyzers.get(language)
        if specialized_analyzer:
            try:
                enhanced_result = await specialized_analyzer(file_path, request)
                if enhanced_result:
                    # Merge the enhanced result with the base result
                    result.update(enhanced_result)
            except Exception as e:
                self._logger.error(f"Error in specialized analyzer for {language}: {str(e)}")
        
        return result
    
    async def _analyze_python(self, file_path, request=None):
        """Specialized analyzer for Python files."""
        # Example implementation - you would expand this
        import ast
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Extract classes and functions
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.FunctionDef):
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.iter_path(tree, node)):
                        functions.append({
                            "name": node.name,
                            "line": node.lineno,
                            "args": [a.arg for a in node.args.args]
                        })
            
            return {
                "classes": classes,
                "functions": functions,
                "imports": self._extract_python_imports(content)
            }
        except Exception as e:
            self._logger.error(f"Error analyzing Python file: {str(e)}")
            return None
    
    def _extract_python_imports(self, content):
        """Extract import statements from Python code."""
        import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
        imports = []
        
        for line in content.splitlines():
            line = line.strip()
            match = re.match(import_pattern, line)
            if match:
                from_module, imported = match.groups()
                imports.append({
                    "from_module": from_module,
                    "imported": [name.strip() for name in imported.split(',')]
                })
        
        return imports
    
    async def _analyze_typescript(self, file_path, request=None):
        """Specialized analyzer for TypeScript files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract interfaces and types
            types = self._extract_typescript_types(content)
            
            # For more complex analysis, we can use the AI
            prompt = f"""
                Analyze this TypeScript file and extract key information:
                
                ```typescript
                {content[:20000]}  # Limit for large files
                ```
                
                Identify and describe:
                1. Interfaces and their properties
                2. Type definitions
                3. Classes and their methods
                4. Key functions and their purposes
                5. Design patterns used
                6. Dependencies and imports
                
                Format your response as a structured analysis.
                """
                
            # Call AI for analysis
            response = await self._get_ai_analysis(prompt)
            
            return {
                "types": types,
                "ai_analysis": response
            }
        except Exception as e:
            self._logger.error(f"Error analyzing TypeScript file: {str(e)}")
            return None
    
    def _extract_typescript_types(self, content: str) -> List[Dict[str, Any]]:
        """Extract interface and type definitions from TypeScript code."""
        interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{([^}]*)\}'
        type_pattern = r'type\s+(\w+)\s*=\s*(.+?);'
        
        interfaces = []
        for match in re.finditer(interface_pattern, content, re.DOTALL):
            name, extends, body = match.groups()
            properties = {}
            
            # Parse properties
            prop_pattern = r'(\w+)(?:\?)?:\s*([^;]+);'
            for prop_match in re.finditer(prop_pattern, body):
                prop_name, prop_type = prop_match.groups()
                properties[prop_name] = prop_type.strip()
            
            interfaces.append({
                "name": name,
                "extends": extends,
                "properties": properties
            })
        
        types = []
        for match in re.finditer(type_pattern, content, re.DOTALL):
            name, definition = match.groups()
            types.append({
                "name": name,
                "definition": definition.strip()
            })
        
        return interfaces + types
    
    async def _analyze_javascript(self, file_path, request=None):
        """Specialized analyzer for JavaScript files."""
        # Similar implementation to TypeScript but without type information
        pass
    
    async def _analyze_json(self, file_path, request=None):
        """Specialized analyzer for JSON files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the JSON
            data = json.loads(content)
            
            # Infer schema
            schema = self._infer_json_schema(data)
            
            return {
                "schema": schema,
                "keys": list(data.keys()) if isinstance(data, dict) else [],
                "array_length": len(data) if isinstance(data, list) else None,
                "data_preview": str(data)[:1000] + "..." if len(str(data)) > 1000 else str(data)
            }
        except Exception as e:
            self._logger.error(f"Error analyzing JSON file: {str(e)}")
            return None
    
    def _infer_json_schema(self, data):
        """Infer a simple schema from JSON data."""
        if isinstance(data, dict):
            schema = {}
            for key, value in data.items():
                schema[key] = self._get_type(value)
            return {"type": "object", "properties": schema}
        elif isinstance(data, list):
            if not data:
                return {"type": "array", "items": {"type": "unknown"}}
            
            # Get the type of the first item
            first_item_type = self._get_type(data[0])
            
            # Check if all items have the same type
            same_type = all(self._get_type(item) == first_item_type for item in data)
            
            if same_type:
                return {"type": "array", "items": first_item_type}
            else:
                return {"type": "array", "items": {"type": "mixed"}}
        else:
            return self._get_type(data)
    
    def _get_type(self, value):
        """Get the type of a JSON value."""
        if value is None:
            return {"type": "null"}
        elif isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        elif isinstance(value, str):
            return {"type": "string"}
        elif isinstance(value, dict):
            schema = {}
            for key, val in value.items():
                schema[key] = self._get_type(val)
            return {"type": "object", "properties": schema}
        elif isinstance(value, list):
            if not value:
                return {"type": "array", "items": {"type": "unknown"}}
            return {"type": "array", "items": self._get_type(value[0])}
        else:
            return {"type": "unknown"}
    
    async def _analyze_yaml(self, file_path, request=None):
        """Specialized analyzer for YAML files."""
        # Implementation similar to JSON
        pass
    
    async def _analyze_markdown(self, file_path, request=None):
        """Specialized analyzer for Markdown files."""
        # Extract headings, links, etc.
        pass
    
    async def _analyze_html(self, file_path, request=None):
        """Specialized analyzer for HTML files."""
        # Extract elements, links, scripts, etc.
        pass
    
    async def _analyze_css(self, file_path, request=None):
        """Specialized analyzer for CSS files."""
        # Extract selectors, properties, etc.
        pass
    
    async def _analyze_sql(self, file_path, request=None):
        """Specialized analyzer for SQL files."""
        # Extract tables, queries, etc.
        pass
    
    async def _get_ai_analysis(self, prompt):
        """Get analysis from the AI service."""
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000
        )
        
        response = await gemini_client.generate_text(api_request)
        return response.text
