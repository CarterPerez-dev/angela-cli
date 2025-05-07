# angela/review/feedback.py
"""
Feedback processing for Angela CLI.

This module provides functionality for processing user feedback
on generated code and refining code based on feedback.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import json

from angela.ai.client import gemini_client, GeminiRequest
from angela.review.diff_manager import diff_manager
from angela.utils.logging import get_logger

logger = get_logger(__name__)

class FeedbackManager:
    """
    Manager for processing user feedback and refining code.
    """
    
    def __init__(self):
        """Initialize the feedback manager."""
        self._logger = logger
    
    async def process_feedback(
        self, 
        feedback: str,
        original_code: str,
        file_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process feedback on code and generate improved version.
        
        Args:
            feedback: User feedback
            original_code: Original code to improve
            file_path: Optional path to the file
            context: Optional additional context
            
        Returns:
            Dictionary with the improved code and other information
        """
        self._logger.info("Processing feedback for code improvement")
        
        # Extract file extension for language detection
        language = None
        if file_path:
            _, ext = os.path.splitext(file_path)
            language = self._get_language_from_extension(ext)
        
        # Build prompt for code improvement
        prompt = self._build_improvement_prompt(
            feedback, 
            original_code, 
            language,
            file_path,
            context
        )
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=16000,  # Large token limit for code
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        # Extract improved code and explanation
        improved_code, explanation = self._extract_improved_code(response.text, original_code)
        
        # Generate diff
        diff = diff_manager.generate_diff(original_code, improved_code)
        
        return {
            "original_code": original_code,
            "improved_code": improved_code,
            "explanation": explanation,
            "diff": diff,
            "file_path": file_path,
            "language": language,
            "feedback": feedback
        }
    
    async def refine_project(
        self, 
        project_dir: Union[str, Path],
        feedback: str,
        focus_files: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refine an entire project based on feedback.
        
        Args:
            project_dir: Path to the project directory
            feedback: User feedback
            focus_files: Optional list of files to focus on
            context: Optional additional context
            
        Returns:
            Dictionary with the refinement results
        """
        self._logger.info(f"Refining project in {project_dir} based on feedback")
        
        project_dir = Path(project_dir)
        
        # Check if directory exists
        if not project_dir.exists() or not project_dir.is_dir():
            return {
                "success": False,
                "error": f"Project directory does not exist: {project_dir}",
                "feedback": feedback
            }
        
        # Get list of files to refine
        files_to_refine = []
        
        if focus_files:
            # Refine specific files
            for file_pattern in focus_files:
                # Handle glob patterns
                if '*' in file_pattern or '?' in file_pattern:
                    matches = list(project_dir.glob(file_pattern))
                    for match in matches:
                        if match.is_file():
                            files_to_refine.append(match)
                else:
                    # Direct file path
                    file_path = project_dir / file_pattern
                    if file_path.is_file():
                        files_to_refine.append(file_path)
        else:
            # Auto-detect files to refine based on feedback
            files = self._find_relevant_files(project_dir, feedback)
            files_to_refine.extend(files)
        
        # Process each file
        results = []
        
        for file_path in files_to_refine:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    original_code = f.read()
                
                # Process feedback for this file
                file_result = await self.process_feedback(
                    feedback,
                    original_code,
                    str(file_path.relative_to(project_dir)),
                    context
                )
                
                results.append({
                    "file_path": str(file_path.relative_to(project_dir)),
                    "has_changes": original_code != file_result["improved_code"],
                    "diff": file_result["diff"],
                    "explanation": file_result["explanation"]
                })
            except Exception as e:
                self._logger.error(f"Error processing {file_path}: {str(e)}")
                results.append({
                    "file_path": str(file_path.relative_to(project_dir)),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "project_dir": str(project_dir),
            "feedback": feedback,
            "results": results,
            "files_processed": len(results)
        }
    
    async def apply_refinements(
        self, 
        refinements: Dict[str, Any],
        backup: bool = True
    ) -> Dict[str, Any]:
        """
        Apply refinements to files.
        
        Args:
            refinements: Refinement results from refine_project
            backup: Whether to create backup files
            
        Returns:
            Dictionary with the application results
        """
        self._logger.info("Applying refinements to files")
        
        # Extract project directory and results
        project_dir = Path(refinements["project_dir"])
        results = refinements["results"]
        
        # Apply changes to each file
        applied_results = []
        
        for result in results:
            file_path = project_dir / result["file_path"]
            
            # Skip files with errors
            if "error" in result:
                applied_results.append({
                    "file_path": result["file_path"],
                    "applied": False,
                    "error": result["error"]
                })
                continue
            
            # Skip files without changes
            if not result.get("has_changes", False):
                applied_results.append({
                    "file_path": result["file_path"],
                    "applied": False,
                    "message": "No changes to apply"
                })
                continue
            
            try:
                # Read original content
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    original_content = f.read()
                    
                    
                if backup:
                    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                
                # Apply diff
                new_content, success = diff_manager.apply_diff(original_content, result["diff"])
                
                if not success:
                    # If diff application fails, regenerate the improved code
                    new_content = self._regenerate_improved_code(original_content, result["diff"])
                
                # Write the improved content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                applied_results.append({
                    "file_path": result["file_path"],
                    "applied": True,
                    "backup": str(backup_path) if backup else None,
                    "explanation": result.get("explanation", "")
                })
            except Exception as e:
                self._logger.error(f"Error applying changes to {file_path}: {str(e)}")
                applied_results.append({
                    "file_path": result["file_path"],
                    "applied": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "project_dir": str(project_dir),
            "results": applied_results,
            "files_processed": len(applied_results),
            "files_changed": sum(1 for r in applied_results if r.get("applied", False))
        }
    
    def _get_language_from_extension(self, extension: str) -> Optional[str]:
        """
        Get programming language from file extension.
        
        Args:
            extension: File extension (with dot)
            
        Returns:
            Language name or None if unknown
        """
        # Map of extensions to languages
        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript (React)',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript (React)',
            '.html': 'HTML',
            '.css': 'CSS',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.h': 'C/C++ Header',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.md': 'Markdown',
            '.json': 'JSON',
            '.xml': 'XML',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.toml': 'TOML',
            '.sh': 'Shell',
            '.bash': 'Bash',
            '.sql': 'SQL'
        }
        
        return extension_map.get(extension.lower())
    
    def _build_improvement_prompt(
        self, 
        feedback: str,
        original_code: str,
        language: Optional[str],
        file_path: Optional[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a prompt for code improvement.
        
        Args:
            feedback: User feedback
            original_code: Original code to improve
            language: Programming language
            file_path: Path to the file
            context: Additional context
            
        Returns:
            Prompt for the AI service
        """
        # Add language context
        language_str = f"Language: {language}" if language else "Language: Unknown"
        
        # Add file path context
        file_context = f"File: {file_path}" if file_path else ""
        
        # Add additional context if provided
        context_str = ""
        if context:
            context_str = "Additional context:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
        
        # Build the prompt
        prompt = f"""
You are an expert software developer helping to improve code based on user feedback.

{language_str}
{file_context}
{context_str}

User feedback:
{feedback}

Your task is to refine the code according to the feedback while preserving the original functionality.
Provide both the improved code and an explanation of the changes you made.

Original code:
{original_code}

Provide your response in this format:
1. First, the full improved code block
2. Then, a detailed explanation of the changes you made

Improved code:
// Your improved code here

Explanation:
// Your explanation here
"""
        
        return prompt
    
    def _extract_improved_code(
        self, 
        response: str, 
        original_code: str
    ) -> Tuple[str, str]:
        """
        Extract improved code and explanation from AI response.
        
        Args:
            response: AI response
            original_code: Original code (fallback)
            
        Returns:
            Tuple of (improved_code, explanation)
        """
        # Try to extract code block
        code_match = re.search(r'```(?:\w*\n)?(.*?)```', response, re.DOTALL)
        
        if code_match:
            code = code_match.group(1).strip()
        else:
            # Fallback: look for "Improved code:" section
            code_section_match = re.search(r'Improved code:\s*(.*?)(?:\n\n|$)', response, re.DOTALL)
            if code_section_match:
                code = code_section_match.group(1).strip()
            else:
                # No clear code section, use original
                code = original_code
        
        # Try to extract explanation
        explanation_match = re.search(r'Explanation:\s*(.*?)(?:\n\n|$)', response, re.DOTALL)
        
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        else:
            # Fallback: anything after the code block
            if code_match:
                parts = response.split('```', 2)
                if len(parts) > 2:
                    explanation = parts[2].strip()
                else:
                    explanation = "No explanation provided."
            else:
                explanation = "No explanation provided."
        
        return code, explanation
    
    def _find_relevant_files(
        self, 
        project_dir: Path, 
        feedback: str
    ) -> List[Path]:
        """
        Find files relevant to the user feedback.
        
        Args:
            project_dir: Project directory
            feedback: User feedback
            
        Returns:
            List of relevant file paths
        """
        relevant_files = []
        
        # Extract potential file references from feedback
        file_mentions = set()
        
        # Look for explicit file references
        file_patterns = [
            r'file[s]?\s+(?:"|\')?([^"\'\s]+)(?:"|\')?',
            r'in\s+(?:"|\')?([^"\'\s]+)(?:"|\')?',
            r'(?:"|\')?([^"\'\s]+\.(?:py|js|java|html|css|cpp|h|go|rb))(?:"|\')?'
        ]
        
        for pattern in file_patterns:
            for match in re.finditer(pattern, feedback, re.IGNORECASE):
                file_mentions.add(match.group(1))
        
        # Check if mentioned files exist
        for mention in file_mentions:
            # Check for exact path
            file_path = project_dir / mention
            if file_path.exists() and file_path.is_file():
                relevant_files.append(file_path)
                continue
            
            # Check for glob pattern
            if '*' in mention or '?' in mention:
                matches = list(project_dir.glob(mention))
                for match in matches:
                    if match.is_file():
                        relevant_files.append(match)
                continue
            
            # Check for just the filename (could be in any directory)
            for root, _, files in os.walk(project_dir):
                if mention in files:
                    relevant_files.append(Path(root) / mention)
        
        # If no specific files mentioned, return all source code files
        if not relevant_files:
            for root, _, files in os.walk(project_dir):
                for file in files:
                    # Skip common non-source files and directories
                    if any(excluded in root for excluded in ['.git', 'node_modules', '__pycache__', '.venv']):
                        continue
                    
                    # Check if it's a source file
                    _, ext = os.path.splitext(file)
                    if ext.lower() in ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.go', '.rb', '.php', '.swift']:
                        relevant_files.append(Path(root) / file)
        
        return relevant_files
    
    def _regenerate_improved_code(
        self, 
        original_content: str, 
        diff: str
    ) -> str:
        """
        Regenerate improved code from original and diff when apply_diff fails.
        
        This is a fallback method when the diff can't be applied cleanly.
        It uses simple heuristics to apply changes.
        
        Args:
            original_content: Original content
            diff: Unified diff string
            
        Returns:
            Regenerated improved content
        """
        # Simple heuristic: if diff shows additions, add them at the end
        # if diff shows deletions, try to find and remove them
        
        lines = diff.splitlines()
        adds = []
        removes = []
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                adds.append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                removes.append(line[1:])
        
        # Start with original content
        result = original_content
        
        # Try to remove lines
        for remove in removes:
            result = result.replace(remove + '\n', '')
            result = result.replace(remove, '')
        
        # Add new lines at the end
        if adds:
            if not result.endswith('\n'):
                result += '\n'
            result += '\n'.join(adds)
        
        return result

# Global feedback manager instance
feedback_manager = FeedbackManager()                    
