"""
File content analysis and manipulation for Angela CLI.

This module provides AI-powered capabilities for understanding and
manipulating file contents based on natural language requests.
"""
import os
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union

from angela.review.diff_manager import diff_manager
from angela.ai.client import gemini_client, GeminiRequest
from angela.context import context_manager
from angela.context.file_detector import detect_file_type
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class ContentAnalyzer:
    """
    Analyzer for file content with AI-powered understanding and manipulation.
    
    This class provides:
    1. Content understanding - extract meaning from code or text
    2. Content summarization - generate concise summaries
    3. Content manipulation - make targeted changes based on natural language requests
    4. Content search - find relevant sections or patterns
    """
    
    def __init__(self):
        """Initialize the content analyzer."""
        self._logger = logger
    
    async def analyze_content(
        self, 
        file_path: Union[str, Path], 
        request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze file content to extract meaningful information.
        
        Args:
            file_path: Path to the file to analyze
            request: Optional specific analysis request
            
        Returns:
            Dictionary with analysis results
        """
        path_obj = Path(file_path)
        
        # Check if file exists
        if not path_obj.exists():
            return {"error": f"File not found: {path_obj}"}
        
        # Get file info to determine type and appropriate analysis
        file_info = detect_file_type(path_obj)
        
        # Read file content
        try:
            with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            self._logger.error(f"Error reading file: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}
        
        # Generate analysis prompt based on file type and request
        prompt = self._build_analysis_prompt(content, file_info, request)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Structure the analysis results
        result = {
            "path": str(path_obj),
            "type": file_info.get("type", "unknown"),
            "language": file_info.get("language"),
            "analysis": response.text,
            "request": request
        }
        
        return result
    
    async def summarize_content(
        self, 
        file_path: Union[str, Path], 
        max_length: int = 500
    ) -> Dict[str, Any]:
        """
        Generate a concise summary of file content.
        
        Args:
            file_path: Path to the file to summarize
            max_length: Maximum length of the summary in characters
            
        Returns:
            Dictionary with summary results
        """
        path_obj = Path(file_path)
        
        # Check if file exists
        if not path_obj.exists():
            return {"error": f"File not found: {path_obj}"}
        
        # Get file info
        file_info = detect_file_type(path_obj)
        
        # Read file content
        try:
            with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            self._logger.error(f"Error reading file: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}
        
        # Generate summarization prompt
        prompt = f"""
Provide a concise summary of the following {file_info.get('language', 'text')} file. 
Focus on the main purpose, structure, and key components.
Keep the summary under {max_length} characters.

```
{content[:20000]}  # Limit to first 20K chars for very large files
```

Summary:
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=1000
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Return the summary
        return {
            "path": str(path_obj),
            "type": file_info.get("type", "unknown"),
            "language": file_info.get("language"),
            "summary": response.text,
            "content_length": len(content)
        }
    
    async def manipulate_content(
        self, 
        file_path: Union[str, Path], 
        instruction: str
    ) -> Dict[str, Any]:
        """
        Manipulate file content based on a natural language instruction.
        
        Args:
            file_path: Path to the file to manipulate
            instruction: Natural language instruction for the manipulation
            
        Returns:
            Dictionary with manipulation results including old and new content
        """
        path_obj = Path(file_path)
        
        # Check if file exists
        if not path_obj.exists():
            return {"error": f"File not found: {path_obj}"}
        
        # Get file info
        file_info = detect_file_type(path_obj)
        
        # Check if this is a text file that can be manipulated
        if file_info.get("binary", False):
            return {"error": f"Cannot manipulate binary file: {path_obj}"}
        
        # Read current content
        try:
            with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
        except Exception as e:
            self._logger.error(f"Error reading file: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}
        
        # Generate manipulation prompt
        prompt = self._build_manipulation_prompt(original_content, file_info, instruction)
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=20000  # Large token limit for returning the full modified content
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Extract the modified content from the response
        modified_content = self._extract_modified_content(response.text, original_content)
        
        # Generate diff
        diff = diff_manager.generate_diff(original_content, modified_content)
        
        # Return the results
        return {
            "path": str(path_obj),
            "type": file_info.get("type", "unknown"),
            "language": file_info.get("language"),
            "instruction": instruction,
            "original_content": original_content,
            "modified_content": modified_content,
            "diff": diff,
            "has_changes": original_content != modified_content
        }
    
    async def search_content(
        self,
        file_path: Union[str, Path],
        query: str,
        context_lines: int = 2
    ) -> Dict[str, Any]:
        """
        Search for relevant sections in a file based on a query.
        
        Args:
            file_path: Path to the file to search
            query: Natural language search query
            context_lines: Number of context lines to include around matches
            
        Returns:
            Dictionary with search results
        """
        path_obj = Path(file_path)
        
        # Check if file exists
        if not path_obj.exists():
            return {"error": f"File not found: {path_obj}"}
        
        # Get file info
        file_info = detect_file_type(path_obj)
        
        # Check if this is a text file that can be searched
        if file_info.get("binary", False):
            return {"error": f"Cannot search binary file: {path_obj}"}
        
        # Read content
        try:
            with open(path_obj, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            self._logger.error(f"Error reading file: {str(e)}")
            return {"error": f"Error reading file: {str(e)}"}
        
        # Generate search prompt
        prompt = f"""
Search the following {file_info.get('language', 'text')} file for sections that match this query: "{query}"

For each matching section, provide:
1. Line numbers (approximate)
2. The relevant code/text section
3. A brief explanation of why it matches the query

```
{content[:50000]}  # Limit to first 50K chars for very large files
```

Search results:
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=4000
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Parse the search results to extract matches
        matches = self._parse_search_results(response.text, content, context_lines)
        
        # Return the results
        return {
            "path": str(path_obj),
            "type": file_info.get("type", "unknown"),
            "language": file_info.get("language"),
            "query": query,
            "matches": matches,
            "match_count": len(matches)
        }
    
    def _build_analysis_prompt(
        self, 
        content: str, 
        file_info: Dict[str, Any], 
        request: Optional[str]
    ) -> str:
        """
        Build a prompt for content analysis.
        
        Args:
            content: The file content
            file_info: Information about the file
            request: Specific analysis request
            
        Returns:
            A prompt string for the AI service
        """
        file_type = file_info.get("type", "unknown")
        language = file_info.get("language", "unknown")
        
        # Adjust analysis based on file type and language
        analysis_focus = ""
        if language == "Python":
            analysis_focus = """
- Identify main functions and classes
- Describe the overall code structure
- Note any imports and dependencies
- Identify potential bugs or code issues
- Suggest improvements or best practices
"""
        elif language == "JavaScript" or language == "TypeScript":
            analysis_focus = """
- Identify key functions and modules
- Note any imports, frameworks, or libraries used
- Analyze the code structure and patterns
- Identify potential bugs or code issues
- Suggest improvements or best practices
"""
        elif language == "HTML" or language == "CSS":
            analysis_focus = """
- Describe the document structure
- Identify key components or sections
- Note any external resources or dependencies
- Analyze accessibility and best practices
- Suggest improvements
"""
        elif file_type == "document" or language == "Markdown":
            analysis_focus = """
- Summarize the main topics and sections
- Identify key points and arguments
- Note the document structure and organization
- Analyze clarity and coherence
- Suggest improvements
"""
        elif "config" in file_type.lower() or file_type in ["JSON", "YAML", "TOML"]:
            analysis_focus = """
- Identify key configuration settings
- Explain the purpose of important parameters
- Note any environment-specific settings
- Identify potential issues or missing values
- Suggest improvements or best practices
"""
        
        # Create prompt based on request and file type
        if request:
            prompt = f"""
Analyze the following {language} file with this specific request: "{request}"

```
{content[:50000]}  # Limit to first 50K chars for very large files
```

Analysis:
"""
        else:
            prompt = f"""
Analyze the following {language} file.

{analysis_focus}

```
{content[:50000]}  # Limit to first 50K chars for very large files
```

Analysis:
"""
        
        return prompt
    
    def _build_manipulation_prompt(
        self, 
        content: str, 
        file_info: Dict[str, Any], 
        instruction: str
    ) -> str:
        """
        Build a prompt for content manipulation.
        
        Args:
            content: The original file content
            file_info: Information about the file
            instruction: Manipulation instruction
            
        Returns:
            A prompt string for the AI service
        """
        language = file_info.get("language", "unknown")
        
        prompt = f"""
You are given a {language} file and a request to modify it.

File content:
```
{content}
```

Request: {instruction}

Your task is to modify the file according to the request, maintaining the integrity, style, and purpose of the original file.
Return the ENTIRE modified content, not just the changed parts.
Only make changes that directly address the request.

Modified file content:
```
"""
        
        return prompt
    
    def _extract_modified_content(self, response: str, original_content: str) -> str:
        """
        Extract the modified content from the AI response.
        
        Args:
            response: The AI service response
            original_content: The original file content
            
        Returns:
            The modified content
        """
        # Try to extract content between ```
        match = re.search(r'```(?:.*?)\n(.*?)```', response, re.DOTALL)
        if match:
            return match.group(1)
        
        # If no code block, look for specific patterns indicating the start of content
        patterns = [
            r'Modified file content:\n(.*)',
            r'MODIFIED CONTENT:\n(.*)',
            r'Here\'s the modified content:\n(.*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no clear content found, return the full response
        # (or the original content if response clearly isn't just content)
        if len(response.splitlines()) < 5 or len(response) > len(original_content) * 1.5:
            self._logger.warning("Could not clearly identify modified content, using original")
            return original_content
        
        return response.strip()
    
    
    def _parse_search_results(
        self, 
        response: str, 
        content: str, 
        context_lines: int
    ) -> List[Dict[str, Any]]:
        """
        Parse search results from the AI response.
        
        Args:
            response: The AI service response
            content: The original file content
            context_lines: Number of context lines to include
            
        Returns:
            A list of match dictionaries
        """
        # Split content into lines for context
        content_lines = content.splitlines()
        
        # Look for patterns like "Lines 10-15" or "Line 20"
        line_patterns = [
            r'Lines? (\d+)(?:-(\d+))?',  # Standard "Line X" or "Lines X-Y"
            r'L(\d+)(?:-L(\d+))?',       # Shortened "LX" or "LX-LY"
            r'(\d+)(?:-(\d+))?\s*:',     # Line numbers with colon "X:" or "X-Y:"
        ]
        
        # Matches to return
        matches = []
        
        # Process multi-line response sections separately
        sections = re.split(r'\n\s*\n', response)
        
        for section in sections:
            # Skip empty sections
            if not section.strip():
                continue
                
            # Look for line number patterns
            line_start = None
            line_end = None
            
            for pattern in line_patterns:
                line_match = re.search(pattern, section)
                if line_match:
                    line_start = int(line_match.group(1))
                    if line_match.group(2):
                        line_end = int(line_match.group(2))
                    else:
                        line_end = line_start
                    break
            
            # If no line numbers found, continue to next section
            if line_start is None:
                continue
            
            # Extract code block if present
            code_block = None
            code_match = re.search(r'```(?:.*?)\n(.*?)```', section, re.DOTALL)
            if code_match:
                code_block = code_match.group(1)
            
            # Extract explanation
            explanation = section
            if code_block:
                explanation = re.sub(r'```(?:.*?)\n.*?```', '', explanation, flags=re.DOTALL)
            explanation = re.sub(r'Lines? \d+(?:-\d+)?:?', '', explanation, flags=re.DOTALL)
            explanation = explanation.strip()
            
            # Get context lines
            context_start = max(0, line_start - 1 - context_lines)
            context_end = min(len(content_lines) - 1, line_end - 1 + context_lines)
            
            # Get the actual content with context
            match_content = '\n'.join(content_lines[context_start:context_end + 1])
            
            # Create match entry
            match = {
                "line_start": line_start,
                "line_end": line_end,
                "context_start": context_start + 1,  # 1-indexed for display
                "context_end": context_end + 1,      # 1-indexed for display
                "content": match_content,
                "explanation": explanation
            }
            
            matches.append(match)
        
        return matches

# Global content analyzer instance
content_analyzer = ContentAnalyzer()
