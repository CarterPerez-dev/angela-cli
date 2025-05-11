# angela/generation/refiner.py
"""
Interactive code refinement for Angela CLI.

This module provides capabilities for interactively refining generated code
based on natural language feedback.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import json
import re
import difflib

from angela.utils.logging import get_logger
from angela.ai.client import gemini_client, GeminiRequest
from angela.generation.engine import CodeFile, CodeProject
from angela.review.feedback import feedback_manager
from angela.review.diff_manager import diff_manager
from angela.generation.context_manager import generation_context_manager

logger = get_logger(__name__)

class InteractiveRefiner:
    """
    Interactive refiner for generated code projects.
    
    This class handles the refinement of generated code based on natural language
    feedback, allowing for iterative improvement of generated projects.
    """
    
    def __init__(self):
        """Initialize the interactive refiner."""
        self._logger = logger
    
    async def process_refinement_feedback(
        self, 
        feedback: str,
        project: CodeProject,
        focus_files: Optional[List[str]] = None
    ) -> Tuple[CodeProject, Dict[str, Any]]:
        """
        Process feedback to refine a generated project.
        
        Args:
            feedback: Natural language feedback
            project: The project to refine
            focus_files: Optional list of files to focus on
            
        Returns:
            Tuple of (refined project, refinement results)
        """
        self._logger.info(f"Processing refinement feedback: {feedback}")
        
        # Analyze feedback to determine affected files
        affected_files = await self._analyze_feedback_for_files(feedback, project, focus_files)
        self._logger.debug(f"Affected files: {[f.path for f in affected_files]}")
        
        # Process each affected file
        refinement_results = []
        
        for file in affected_files:
            # Process feedback for this file
            self._logger.debug(f"Processing feedback for file: {file.path}")
            
            file_result = await self._process_file_feedback(
                feedback=feedback,
                file=file,
                project=project
            )
            
            # Add to results
            refinement_results.append({
                "file_path": file.path,
                "has_changes": file_result["original_code"] != file_result["improved_code"],
                "diff": file_result["diff"],
                "explanation": file_result["explanation"]
            })
            
            # Update file content if changed
            if file_result["original_code"] != file_result["improved_code"]:
                for project_file in project.files:
                    if project_file.path == file.path:
                        project_file.content = file_result["improved_code"]
                        break
        
        # Return updated project and results
        return project, {
            "success": True,
            "feedback": feedback,
            "results": refinement_results,
            "files_processed": len(refinement_results)
        }
    
    async def _analyze_feedback_for_files(
        self, 
        feedback: str, 
        project: CodeProject,
        focus_files: Optional[List[str]] = None
    ) -> List[CodeFile]:
        """
        Analyze feedback to determine which files are affected.
        
        Args:
            feedback: Natural language feedback
            project: The project to refine
            focus_files: Optional list of files to focus on
            
        Returns:
            List of affected files
        """
        # If focus files are provided, use those
        if focus_files:
            return [file for file in project.files if any(
                self._match_file_pattern(file.path, pattern) for pattern in focus_files
            )]
        
        # Extract file mentions from feedback
        file_mentions = self._extract_file_mentions(feedback)
        
        if file_mentions:
            # Find mentioned files
            mentioned_files = []
            for mention in file_mentions:
                for file in project.files:
                    if self._match_file_mention(file.path, mention):
                        mentioned_files.append(file)
                        break
            
            if mentioned_files:
                return mentioned_files
        
        # If no files were found from feedback or focus_files, determine files based on feedback intent
        return await self._determine_files_by_intent(feedback, project)
    
    def _extract_file_mentions(self, feedback: str) -> List[str]:
        """
        Extract mentions of files from feedback.
        
        Args:
            feedback: Natural language feedback
            
        Returns:
            List of file mentions
        """
        # Common file mention patterns
        patterns = [
            r'(?:file|in|modify|change|update)\s+["\']?([.\w/-]+\.\w+)["\']?',  # file foo.py
            r'["\']([.\w/-]+\.\w+)["\']',  # "foo.py"
        ]
        
        mentions = []
        for pattern in patterns:
            matches = re.finditer(pattern, feedback, re.IGNORECASE)
            for match in matches:
                mentions.append(match.group(1))
        
        return mentions
    
    def _match_file_mention(self, file_path: str, mention: str) -> bool:
        """
        Check if a file path matches a mention.
        
        Args:
            file_path: Path to the file
            mention: File mention from feedback
            
        Returns:
            True if the file matches the mention
        """
        # Exact match
        if mention == file_path:
            return True
        
        # Basename match
        if Path(mention).name == Path(file_path).name:
            return True
        
        # Partial path match
        if mention in file_path:
            return True
        
        return False
    
    def _match_file_pattern(self, file_path: str, pattern: str) -> bool:
        """
        Check if a file path matches a pattern.
        
        Args:
            file_path: Path to the file
            pattern: Pattern to match against
            
        Returns:
            True if the file matches the pattern
        """
        # Exact match
        if pattern == file_path:
            return True
        
        # Wildcard match
        if '*' in pattern:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace('.', '\\.').replace('*', '.*')
            return re.match(regex_pattern, file_path) is not None
        
        # Partial path match
        if pattern in file_path:
            return True
        
        return False
    
    async def _determine_files_by_intent(
        self, 
        feedback: str, 
        project: CodeProject
    ) -> List[CodeFile]:
        """
        Determine which files to modify based on feedback intent.
        
        Args:
            feedback: Natural language feedback
            project: The project to refine
            
        Returns:
            List of files to modify
        """
        # Build prompt for AI to determine affected files
        prompt = f"""
Given this feedback for a software project:
"{feedback}"

Determine which types of files would need to be modified to implement this feedback.
Consider the feedback's intent and what components of a software system it affects.

Here are the available files in the project:
{', '.join(file.path for file in project.files)}

Return a JSON array of file paths that should be modified, like this:
["path/to/file1.ext", "path/to/file2.ext"]

Only include files that are directly relevant to the feedback.
"""
        
        # Call AI service
        api_request = GeminiRequest(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.2
        )
        
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract JSON from response
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
                    
            # Parse JSON
            file_paths = json.loads(json_str)
            
            # Match these paths to actual files
            affected_files = []
            for path in file_paths:
                for file in project.files:
                    if self._match_file_pattern(file.path, path):
                        affected_files.append(file)
                        break
            
            return affected_files
            
        except Exception as e:
            self._logger.error(f"Error determining files by intent: {str(e)}")
            
            # Fallback: return a few important files based on naming conventions
            important_files = []
            
            # Look for main files
            for file in project.files:
                if 'main' in file.path.lower() or 'app' in file.path.lower() or 'index' in file.path.lower():
                    important_files.append(file)
            
            # If we found some files, return those
            if important_files:
                return important_files[:3]  # Limit to 3 files
            
            # Otherwise, just return a few files
            return project.files[:3]  # Limit to 3 files
    
    async def _process_file_feedback(
        self, 
        feedback: str,
        file: CodeFile,
        project: CodeProject
    ) -> Dict[str, Any]:
        """
        Process feedback for a specific file.
        
        Args:
            feedback: Natural language feedback
            file: The file to refine
            project: The parent project
            
        Returns:
            Dictionary with refinement results
        """
        # Get context for this file
        file_context = self._build_file_context(file, project)
        
        # Use the feedback manager to process the feedback
        result = await feedback_manager.process_feedback(
            feedback=feedback,
            original_code=file.content,
            file_path=file.path,
            context=file_context
        )
        
        return result
    
    def _build_file_context(self, file: CodeFile, project: CodeProject) -> Dict[str, Any]:
        """
        Build context for a file for feedback processing.
        
        Args:
            file: The file to build context for
            project: The parent project
            
        Returns:
            Dictionary with file context
        """
        # Start with basic context
        context = {
            "file_path": file.path,
            "file_purpose": file.purpose,
            "language": file.language,
            "project_name": project.name,
            "project_type": project.project_type,
            "project_description": project.description
        }
        
        # Add dependency information if available
        if file.dependencies:
            context["dependencies"] = file.dependencies
        
        # Add global context from generation context manager
        context.update(generation_context_manager.get_all_global_context())
        
        # Add project architecture if available
        architecture = generation_context_manager.get_global_context("architecture")
        if architecture:
            context["architecture"] = architecture
        
        return context
    
    async def summarize_refinements(
        self, 
        refinement_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a human-readable summary of refinements.
        
        Args:
            refinement_results: Results from process_refinement_feedback
            
        Returns:
            Dictionary with summarized results
        """
        results = refinement_results.get("results", [])
        modified_count = sum(1 for r in results if r.get("has_changes", False))
        
        # Create summary
        summary = {
            "feedback": refinement_results.get("feedback", ""),
            "files_processed": len(results),
            "files_modified": modified_count,
            "file_summaries": []
        }
        
        # Summarize each file
        for result in results:
            if result.get("has_changes", False):
                # Count lines changed
                diff_lines = result.get("diff", "").splitlines()
                additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
                deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
                
                # Add to summary
                summary["file_summaries"].append({
                    "file_path": result.get("file_path", ""),
                    "lines_added": additions,
                    "lines_deleted": deletions,
                    "explanation": result.get("explanation", "")
                })
        
        return summary

# Global instance
interactive_refiner = InteractiveRefiner()
