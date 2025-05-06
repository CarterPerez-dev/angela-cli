# angela/ai/content_analyzer_extensions.py

from typing import Dict, Any, Union, Optional
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
    
    async def analyze_content(
        self, 
        file_path: Union[str, Path], 
        request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhanced analyze_content that routes to language-specific handlers.
        """
        path_obj = Path(file_path)
        
        # Check if file exists
        if not path_obj.exists():
            return {"error": f"File not found: {path_obj}"}
        
        # Get file info for language-specific handling
        file_info = self._get_file_info(path_obj)
        language = file_info.get("language")
        
        # Read file content
        try:
            with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}
        
        # Use language-specific handler if available
        handler_name = self.LANGUAGE_HANDLERS.get(language)
        if handler_name and hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            return await handler(path_obj, content, file_info, request)
        
        # Fall back to generic analysis
        return await super().analyze_content(file_path, request)
    
    # Language-specific analysis methods
    
    async def _analyze_typescript(
        self, 
        path: Path, 
        content: str, 
        file_info: Dict[str, Any], 
        request: Optional[str]
    ) -> Dict[str, Any]:
        """TypeScript-specific analysis."""
        logger.debug(f"Analyzing TypeScript file: {path}")
        
        # TypeScript-specific analysis prompt
        prompt = f"""
Analyze the following TypeScript code with a focus on:
- Types and interfaces defined
- Function signatures and return types
- React component structure (if present)
- Type safety issues
- Potential type improvements

```typescript
{content[:50000]}
Analysis:
"""
# Call AI for analysis
response = await self._get_ai_analysis(prompt)
    # Extract important types and interfaces
    types_and_interfaces = self._extract_typescript_types(content)
    
    # Structure the analysis results
    result = {
        "path": str(path),
        "type": file_info.get("type", "unknown"),
        "language": "TypeScript",
        "analysis": response,
        "types_and_interfaces": types_and_interfaces,
        "request": request
    }
    
    return result

def _extract_typescript_types(self, content: str) -> List[Dict[str, Any]]:
    """Extract TypeScript types and interfaces from content."""
    types_and_interfaces = []
    
    # Simple regex to find interface and type definitions
    interface_pattern = r'interface\s+(\w+)(?:<[\w\s,]+>)?\s*{([^}]*)}'
    type_pattern = r'type\s+(\w+)(?:<[\w\s,]+>)?\s*=\s*([^;]*);'
    
    # Find interfaces
    for match in re.finditer(interface_pattern, content):
        name = match.group(1)
        body = match.group(2).strip()
        types_and_interfaces.append({
            "kind": "interface",
            "name": name,
            "definition": body
        })
    
    # Find types
    for match in re.finditer(type_pattern, content):
        name = match.group(1)
        definition = match.group(2).strip()
        types_and_interfaces.append({
            "kind": "type",
            "name": name,
            "definition": definition
        })
    
    return types_and_interfaces

# Add more language-specific methods as needed... IMPORTANT

async def _analyze_json(
    self, 
    path: Path, 
    content: str, 
    file_info: Dict[str, Any], 
    request: Optional[str]
) -> Dict[str, Any]:
    """JSON-specific analysis."""
    logger.debug(f"Analyzing JSON file: {path}")
    
    # Validate JSON and extract schema information
    try:
        json_data = json.loads(content)
        # Infer schema structure
        schema = self._infer_json_schema(json_data)
        
        # Generate human-readable analysis
        prompt = f"""
Analyze the following JSON data structure:
{content[:5000]}
Focus on:

The overall structure and purpose
Key fields and their meaning
Potential issues or inconsistencies
Schema validation suggestions

Analysis:
"""
response = await self._get_ai_analysis(prompt)
        return {
            "path": str(path),
            "type": "JSON",
            "language": "JSON",
            "valid": True,
            "schema": schema,
            "analysis": response,
            "request": request
        }
        
    except json.JSONDecodeError as e:
        # Invalid JSON
        return {
            "path": str(path),
            "type": "JSON",
            "language": "JSON",
            "valid": False,
            "error": f"Invalid JSON: {str(e)}",
            "error_position": {"line": e.lineno, "column": e.colno},
            "request": request
        }

def _infer_json_schema(self, data: Any, depth: int = 0) -> Dict[str, Any]:
    """Infer a basic JSON schema from data."""
    if depth > 5:  # Prevent infinite recursion
        return {"type": "unknown"}
        
    if data is None:
        return {"type": "null"}
    elif isinstance(data, bool):
        return {"type": "boolean"}
    elif isinstance(data, int):
        return {"type": "integer"}
    elif isinstance(data, float):
        return {"type": "number"}
    elif isinstance(data, str):
        return {"type": "string"}
    elif isinstance(data, list):
        if not data:
            return {"type": "array", "items": {}}
        # Sample the first few items to infer element type
        sample_items = data[:min(5, len(data))]
        item_schemas = [self._infer_json_schema(item, depth + 1) for item in sample_items]
        return {"type": "array", "items": item_schemas[0]}  # Simplification: use first item's schema
    elif isinstance(data, dict):
        properties = {}
        for key, value in data.items():
            properties[key] = self._infer_json_schema(value, depth + 1)
        return {"type": "object", "properties": properties}
    else:
        return {"type": "unknown"}

# Helper methods for AI analysis

async def _get_ai_analysis(self, prompt: str) -> str:
    """Get AI analysis using the Gemini API."""
    from angela.ai.client import gemini_client, GeminiRequest
    
    # Call AI service
    api_request = GeminiRequest(
        prompt=prompt,
        max_tokens=4000
    )
    
    response = await gemini_client.generate_text(api_request)
    return response.text
