# angela/shell/completion.py
"""
AI-powered contextual auto-completion for Angela CLI.
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
import os
from pathlib import Path
import re

from angela.utils.logging import get_logger
from angela.context import context_manager
from angela.context.file_activity import file_activity_tracker
from angela.context.session import session_manager
from angela.context.history import history_manager
from angela.ai.client import gemini_client, GeminiRequest

logger = get_logger(__name__)

class CompletionHandler:
    """
    Provides contextually relevant completions for the Angela CLI.
    
    This class generates completions based on command history, project context,
    recent file activity, and current input state.
    """
    
    def __init__(self):
        """Initialize the completion handler."""
        self._logger = logger
        
        # Cache common completions to avoid repeated calculation
        self._completion_cache = {}
        self._cache_ttl = 300  # Cache lifetime in seconds
        self._cache_last_update = {}
        
        # Static completions for common commands
        self._static_completions = {
            "init": [],
            "status": [],
            "shell": [],
            "files": ["ls", "mkdir", "rm", "cat", "write", "find", "info", "rollback"],
            "workflows": ["list", "create", "run", "delete", "show", "export", "import"],
            "generate": ["create-project", "add-feature", "refine-code", "refine-project", "generate-ci", "generate-tests"],
            "rollback": ["list", "operation", "transaction", "last"],
        }
        
        # Common file extensions for different contexts
        self._file_extensions = {
            "python": [".py", ".json", ".yml", ".yaml", ".txt", ".md"],
            "javascript": [".js", ".json", ".ts", ".jsx", ".tsx", ".html", ".css"],
            "web": [".html", ".css", ".js", ".svg", ".png", ".jpg"],
            "data": [".csv", ".json", ".xml", ".yaml", ".sql"],
            "docs": [".md", ".txt", ".pdf", ".docx"],
        }
    
    async def get_completions(self, args: List[str]) -> List[str]:
        """
        Get completions for the current command line.
        
        Args:
            args: The current command line arguments
            
        Returns:
            List of completions
        """
        self._logger.debug(f"Generating completions for args: {args}")
        
        if not args:
            # No args yet, return top-level commands
            return self._get_top_level_completions()
        
        # Handle subcommand completions
        main_command = args[0]
        
        # Check static completions first
        if main_command in self._static_completions and len(args) == 1:
            return self._static_completions[main_command]
        
        # Handle specific completion contexts
        if main_command == "files":
            return await self._get_files_completions(args[1:] if len(args) > 1 else [])
        elif main_command == "workflows":
            return await self._get_workflow_completions(args[1:] if len(args) > 1 else [])
        elif main_command == "generate":
            return await self._get_generate_completions(args[1:] if len(args) > 1 else [])
        elif main_command == "rollback":
            return await self._get_rollback_completions(args[1:] if len(args) > 1 else [])
        elif main_command in ["fix", "explain", "help-with"]:
            # Natural language commands get context-aware completions
            return await self._get_contextual_completions(main_command, args[1:] if len(args) > 1 else [])
        
        # Default to empty list for unknown commands
        return []
    
    def _get_top_level_completions(self) -> List[str]:
        """
        Get top-level command completions.
        
        Returns:
            List of top-level commands
        """
        # Standard commands
        commands = list(self._static_completions.keys())
        
        # Add natural language command prefixes
        commands.extend(["fix", "explain", "help-with"])
        
        # Sort and return
        return sorted(commands)
    
    async def _get_files_completions(self, args: List[str]) -> List[str]:
        """
        Get completions for file-related commands.
        
        Args:
            args: The command arguments after 'files'
            
        Returns:
            List of completions
        """
        if not args:
            # No subcommand yet, return available subcommands
            return self._static_completions["files"]
        
        subcommand = args[0]
        
        # For commands that take file paths, provide file path completions
        if subcommand in ["ls", "cat", "rm", "find", "info"] and len(args) <= 2:
            return await self._get_file_path_completions(args[1] if len(args) > 1 else "")
        
        return []
    
    async def _get_file_path_completions(self, partial_path: str) -> List[str]:
        """
        Get completions for file paths.
        
        Args:
            partial_path: The partial file path to complete
            
        Returns:
            List of matching file paths
        """
        # Convert to Path object for easier handling
        path = Path(partial_path) if partial_path else Path(".")
        
        # Check if it's a directory prefix
        if not partial_path.endswith("/") and path.is_dir():
            # Return the directory with a trailing slash
            return [f"{partial_path}/"]
        
        # Get the directory to search in
        directory = path.parent if partial_path and not partial_path.endswith("/") else path
        prefix = path.name if partial_path and not partial_path.endswith("/") else ""
        
        try:
            # List directory contents matching the prefix
            if not directory.exists():
                return []
                
            completions = []
            for item in directory.iterdir():
                if prefix and not item.name.startswith(prefix):
                    continue
                    
                # Handle directories
                if item.is_dir():
                    completions.append(f"{item.name}/")
                else:
                    completions.append(item.name)
            
            # Return with proper prefix
            prefix_dir = str(directory) if str(directory) != "." else ""
            if prefix_dir and not prefix_dir.endswith("/"):
                prefix_dir += "/"
                
            return [f"{prefix_dir}{c}" for c in completions]
            
        except Exception as e:
            self._logger.error(f"Error getting file path completions: {str(e)}")
            return []
    
    async def _get_workflow_completions(self, args: List[str]) -> List[str]:
        """
        Get completions for workflow-related commands.
        
        Args:
            args: The command arguments after 'workflows'
            
        Returns:
            List of completions
        """
        if not args:
            # No subcommand yet, return available subcommands
            return self._static_completions["workflows"]
        
        subcommand = args[0]
        
        # For commands that take workflow names, provide workflow name completions
        if subcommand in ["run", "delete", "show", "export"] and len(args) <= 2:
            # This would be replaced with actual workflow names from the workflow manager
            return ["workflow1", "workflow2", "backup", "deploy"]
        
        return []
    
    async def _get_generate_completions(self, args: List[str]) -> List[str]:
        """
        Get completions for code generation commands.
        
        Args:
            args: The command arguments after 'generate'
            
        Returns:
            List of completions
        """
        if not args:
            # No subcommand yet, return available subcommands
            return self._static_completions["generate"]
        
        subcommand = args[0]
        
        # Handle specific generate subcommands
        if subcommand == "generate-ci" and len(args) <= 2:
            return ["github_actions", "gitlab_ci", "jenkins", "travis", "circle_ci"]
        
        return []
    

    
    async def _get_rollback_completions(self, args: List[str]) -> List[str]:
        """
        Get completions for rollback commands.
        
        Args:
            args: The command arguments after 'rollback'
            
        Returns:
            List of completions
        """
        if not args:
            # No subcommand yet, return available subcommands
            return self._static_completions["rollback"]
        
        subcommand = args[0]
        
        # For commands that take operation or transaction IDs
        if subcommand in ["operation", "transaction"] and len(args) <= 2:
            # Get IDs from rollback manager
            try:
                # Import here to avoid circular imports
                from angela.execution.rollback import rollback_manager
                
                if subcommand == "operation":
                    # Get recent operations
                    operations = await rollback_manager.get_recent_operations(limit=10)
                    return [str(op["id"]) for op in operations if op.get("can_rollback", False)]
                else:  # transaction
                    # Get recent transactions
                    transactions = await rollback_manager.get_recent_transactions(limit=10)
                    return [str(tx["id"]) for tx in transactions if tx.get("can_rollback", False)]
            except Exception as e:
                self._logger.error(f"Error fetching rollback IDs: {str(e)}")
                return []
        
        # For the "list" command with options
        elif subcommand == "list" and len(args) <= 2:
            return ["--transactions", "--operations", "--limit"]
        
        # For the "last" command with options
        elif subcommand == "last" and len(args) <= 2:
            return ["--transaction", "--force"]
        
        return []
    
    def _get_fix_completions(self, context: Dict[str, Any]) -> List[str]:
        """
        Get completions for the 'fix' command.
        
        Args:
            context: The completion context
            
        Returns:
            List of completions
        """
        completions = []
        
        # Add completions based on last failed command
        last_failed = context.get("last_failed_command")
        if last_failed:
            base_command = last_failed.split()[0] if last_failed.strip() else ""
            completions.append(f"last {base_command} command")
            completions.append(f"last command")
        
        # Add project-specific fix suggestions
        project_type = context.get("project_type")
        if project_type == "python":
            completions.extend([
                "import errors",
                "python syntax",
                "pip dependencies",
                "missing module"
            ])
        elif project_type == "node":
            completions.extend([
                "npm dependencies",
                "webpack config",
                "typescript errors",
                "node version"
            ])
        
        # Add general fix suggestions
        completions.extend([
            "git conflicts",
            "git merge issues",
            "build errors",
            "path issues"
        ])
        
        return completions
    
    def _get_explain_completions(self, context: Dict[str, Any]) -> List[str]:
        """
        Get completions for the 'explain' command.
        
        Args:
            context: The completion context
            
        Returns:
            List of completions
        """
        completions = []
        
        # Add completions for recent files
        recent_files = context.get("recent_files", [])
        for file in recent_files[:3]:  # Limit to 3 recent files
            completions.append(f"file {file}")
        
        # Add completions for recent commands
        recent_commands = context.get("recent_commands", [])
        for cmd in recent_commands[:3]:  # Limit to 3 recent commands
            # Extract base command
            base_cmd = cmd.split()[0] if cmd.strip() else ""
            if base_cmd:
                completions.append(f"command {base_cmd}")
        
        # Add project-specific explain suggestions
        project_type = context.get("project_type")
        if project_type == "python":
            completions.extend([
                "virtual environments",
                "python packaging",
                "project structure"
            ])
        elif project_type == "node":
            completions.extend([
                "package.json",
                "nodejs modules",
                "npm scripts"
            ])
        
        return completions
    
    def _get_help_completions(self, context: Dict[str, Any]) -> List[str]:
        """
        Get completions for the 'help-with' command.
        
        Args:
            context: The completion context
            
        Returns:
            List of completions
        """
        completions = []
        
        # Add project-specific help suggestions
        project_type = context.get("project_type")
        if project_type == "python":
            completions.extend([
                "setting up pytest",
                "creating a Python package",
                "using virtual environments",
                "debugging Python code"
            ])
        elif project_type == "node":
            completions.extend([
                "creating a React component",
                "setting up webpack",
                "optimizing npm builds",
                "debugging JavaScript"
            ])
        
        # Add general help suggestions
        completions.extend([
            "git workflow",
            "project structure",
            "optimizing performance",
            "writing documentation"
        ])
        
        return completions
    
    async def _get_ai_completions(
        self,
        command: str,
        partial: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get AI-powered completions for natural language commands.
        
        Args:
            command: The main command (fix, explain, help-with)
            partial: The partial natural language input
            context: The completion context
            
        Returns:
            List of AI-suggested completions
        """
        try:
            # Build a prompt for the AI
            prompt = f"""
You are suggesting auto-completions for the Angela CLI's "{command}" command.
The user has typed: "{command} {partial}"
Context information:
Project type: {context.get('project_type', 'unknown')}
Recent files: {', '.join(context.get('recent_files', [])[:3])}
Recent commands: {', '.join(context.get('recent_commands', [])[:3])}
Last failed command: {context.get('last_failed_command', 'none')}
Suggest 3-5 natural language completions that would be helpful continuations of what the user is typing.
Each completion should be the FULL text that would follow "{command} ", not just the part after "{partial}".
Completions should be relevant to the current context and project type.
Respond with ONLY a JSON array of strings, like:
["completion 1", "completion 2", "completion 3"
"""
            
    

            api_request = GeminiRequest(
                prompt=prompt,
                max_tokens=200,
                temperature=0.1  # Low temperature for more deterministic completions
            )
            
            response = await gemini_client.generate_text(api_request)
            
            # Parse the response to extract completions
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                try:
                    completions = json.loads(json_match.group(0))
                    if isinstance(completions, list): # Ensure it's a list
                        return completions
                    else:
                        self._logger.warning(f"AI completion response was valid JSON but not a list: {json_match.group(0)}")
                        return []
                except json.JSONDecodeError as e:
                    self._logger.error(f"Error decoding AI completions JSON: {str(e)} - Response part: {json_match.group(0)}")
                    return []
            
            # If we couldn't parse JSON or find a match, return empty list
            self._logger.debug(f"No valid JSON array found in AI completion response: {response.text}")
            return []
            
        except Exception as e:
            self._logger.error(f"Error getting AI completions: {str(e)}")
            return []

    
    def _build_completion_context(self) -> Dict[str, Any]:
        """
        Build a context dictionary for completions.
        
        Returns:
            Context dictionary
        """
        context = {}
        
        # Add project information
        context["project_type"] = context_manager.project_type
        
        # Add recent files
        recent_activities = file_activity_tracker.get_recent_activities(max_count=5)
        context["recent_files"] = [str(activity.file_path) for activity in recent_activities 
                                  if activity.file_path is not None]
        
        # Add recent commands from session
        session_context = session_manager.get_context()
        context["recent_commands"] = session_context.get("recent_commands", [])
        
        # Add last failed command if available
        last_failed = session_manager.get_entity("last_failed_command")
        if last_failed:
            context["last_failed_command"] = last_failed.get("value", "")
        
        return context

# Global instance
completion_handler = CompletionHandler()
