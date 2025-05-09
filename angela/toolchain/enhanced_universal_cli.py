# angela/toolchain/enhanced_universal_cli.py

"""
Enhanced Universal CLI Integration for Angela CLI.

This module provides an extended interface to the Universal CLI Translator
with improved context awareness and tool chaining capabilities.
"""
import asyncio
import os
import re
import json
import shlex
from typing import Dict, Any, List, Optional, Set, Union, Tuple
from pathlib import Path

from angela.utils.logging import get_logger
from angela.core.registry import registry
from angela.context import context_manager
from angela.ai.client import gemini_client, GeminiRequest
from angela.shell.formatter import terminal_formatter

logger = get_logger(__name__)

class EnhancedUniversalCLI:
    """
    Enhanced interface to the Universal CLI Translator with improved context
    awareness and tool chaining capabilities.
    """
    
    def __init__(self):
        """Initialize the enhanced Universal CLI interface."""
        self._logger = logger
        self._translator = None
        self._tool_cache = {}  # Cache of tool information
        self._command_history = {}  # History of commands by tool
    
    def initialize(self):
        """Initialize the translator."""
        self._translator = registry.get("universal_cli_translator")
        if not self._translator:
            try:
                from angela.toolchain.universal_cli import universal_cli_translator
                self._translator = universal_cli_translator
                registry.register("universal_cli_translator", universal_cli_translator)
            except ImportError:
                self._logger.error("Failed to import Universal CLI Translator")
                return False
        
        return self._translator is not None
    
    async def translate_with_context(
        self, 
        request: str, 
        tool: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Translate a natural language request to a command with enhanced context awareness.
        
        Args:
            request: Natural language request
            tool: Optional specific tool to use
            context: Optional context information
            
        Returns:
            Dictionary with the translation result
        """
        self._logger.info(f"Translating request with context: {request}")
        
        if not self._translator:
            if not self.initialize():
                return {
                    "success": False,
                    "error": "Universal CLI Translator not available"
                }
        
        # Get context if not provided
        if context is None:
            context = context_manager.get_context_dict()
        
        # Extract tool from request if not specified
        if not tool:
            tool_match = re.search(r'\b(use|run|with|using)\s+(?:the\s+)?([a-zA-Z0-9_\-]+)', request, re.IGNORECASE)
            if tool_match:
                tool = tool_match.group(2).lower()
        
        # If tool is still not determined, analyze the request to guess
        if not tool:
            tool = await self._guess_tool_from_request(request)
        
        # Enhance the request with context awareness
        enhanced_request = request
        
        # Add context for specific tools
        if tool == "git":
            enhanced_request = await self._enhance_git_request(request, context)
        elif tool in ["docker", "docker-compose"]:
            enhanced_request = await self._enhance_docker_request(request, context)
        elif tool in ["aws", "gcloud", "az"]:
            enhanced_request = await self._enhance_cloud_request(request, context, tool)
        elif tool in ["npm", "yarn", "pip", "gem"]:
            enhanced_request = await self._enhance_package_request(request, context, tool)
        
        # Create an enhanced context for the translator
        enhanced_context = {
            **context,
            "tool": tool,
            "command_history": self._command_history.get(tool, [])
        }
        
        # Log the enhancement
        if enhanced_request != request:
            self._logger.debug(f"Enhanced request: {enhanced_request}")
        
        # Translate the request
        result = await self._translator.translate_request(enhanced_request, enhanced_context)
        
        # If successful, update command history
        if result.get("success", False) and "command" in result:
            if tool not in self._command_history:
                self._command_history[tool] = []
            
            # Add to history, limited to 10 commands
            self._command_history[tool].append(result["command"])
            if len(self._command_history[tool]) > 10:
                self._command_history[tool] = self._command_history[tool][-10:]
        
        return result
    
    async def _guess_tool_from_request(self, request: str) -> Optional[str]:
        """
        Guess which tool a request is likely for based on content analysis.
        
        Args:
            request: Natural language request
            
        Returns:
            Tool name or None if not determined
        """
        # Use AI to analyze the request
        prompt = f"""
Analyze this request to determine which command-line tool it's most likely related to:
"{request}"

Consider common CLI tools like:
- git (version control)
- docker or docker-compose (containers)
- npm, yarn, pip (package managers)
- aws, gcloud, az (cloud CLIs)
- kubectl (Kubernetes)
- terraform (Infrastructure as Code)
- ansible (configuration management)
- curl, wget (HTTP tools)

Return just the tool name in lowercase, nothing else.
"""

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=10)
            response = await gemini_client.generate_text(api_request)
            
            # Extract the tool name (should be a single word)
            tool = response.text.strip().lower()
            
            # Basic validation - tool should be a single word with allowed characters
            if re.match(r'^[a-z0-9_\-]+$', tool):
                self._logger.debug(f"Guessed tool from request: {tool}")
                return tool
            
            return None
            
        except Exception as e:
            self._logger.error(f"Error guessing tool from request: {str(e)}")
            return None
    
    async def _enhance_git_request(self, request: str, context: Dict[str, Any]) -> str:
        """
        Enhance a Git-related request with context information.
        
        Args:
            request: Original request
            context: Context information
            
        Returns:
            Enhanced request
        """
        # Get Git status if we have a project root
        project_root = context.get("project_root")
        if not project_root:
            return request
        
        # Check if "project_state" has Git information already
        if "project_state" in context and "git_state" in context["project_state"]:
            git_state = context["project_state"]["git_state"]
        else:
            # Get Git status
            try:
                from angela.execution.engine import execution_engine
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command="git status --porcelain",
                    check_safety=True,
                    working_dir=project_root
                )
                
                if return_code == 0:
                    # Parse porcelain status
                    changes = []
                    for line in stdout.splitlines():
                        if line.strip():
                            changes.append(line.strip())
                    
                    git_state = {
                        "is_git_repo": True,
                        "has_changes": len(changes) > 0,
                        "changes": changes
                    }
                    
                    # Get branch name
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command="git rev-parse --abbrev-ref HEAD",
                        check_safety=True,
                        working_dir=project_root
                    )
                    
                    if return_code == 0:
                        git_state["current_branch"] = stdout.strip()
                else:
                    git_state = {"is_git_repo": False}
            except Exception as e:
                self._logger.debug(f"Error getting Git status: {str(e)}")
                git_state = {"is_git_repo": False}
        
        # Enhance the request with Git information
        if git_state.get("is_git_repo", False):
            enhanced_request = f"{request}\n\nContext: "
            
            if "current_branch" in git_state:
                enhanced_request += f"On branch {git_state['current_branch']}. "
            
            if git_state.get("has_changes", False):
                changes_count = len(git_state.get("changes", []))
                enhanced_request += f"Working tree has {changes_count} changes. "
            else:
                enhanced_request += f"Working tree clean. "
            
            return enhanced_request
        
        return request
    
    async def _enhance_docker_request(self, request: str, context: Dict[str, Any]) -> str:
        """
        Enhance a Docker-related request with context information.
        
        Args:
            request: Original request
            context: Context information
            
        Returns:
            Enhanced request
        """
        # Check for Docker Compose file in current directory
        cwd = context.get("cwd", os.getcwd())
        
        compose_files = [
            os.path.join(cwd, "docker-compose.yml"),
            os.path.join(cwd, "docker-compose.yaml"),
            os.path.join(cwd, "compose.yml"),
            os.path.join(cwd, "compose.yaml")
        ]
        
        has_compose = any(os.path.exists(f) for f in compose_files)
        
        # Check for Dockerfile in current directory
        has_dockerfile = os.path.exists(os.path.join(cwd, "Dockerfile"))
        
        # Get running containers
        try:
            from angela.execution.engine import execution_engine
            stdout, stderr, return_code = await execution_engine.execute_command(
                command="docker ps --format '{{.Names}}'",
                check_safety=True
            )
            
            if return_code == 0:
                containers = [c for c in stdout.strip().split('\n') if c]
            else:
                containers = []
        except Exception as e:
            self._logger.debug(f"Error getting Docker containers: {str(e)}")
            containers = []
        
        # Enhance the request with Docker information
        enhanced_request = f"{request}\n\nContext: "
        
        if has_compose:
            enhanced_request += f"Docker Compose file present in the current directory. "
        
        if has_dockerfile:
            enhanced_request += f"Dockerfile present in the current directory. "
        
        if containers:
            enhanced_request += f"Running containers: {', '.join(containers)}. "
        elif return_code == 0:  # Docker command worked but no containers
            enhanced_request += f"No running containers. "
        
        return enhanced_request
    
    async def _enhance_cloud_request(self, request: str, context: Dict[str, Any], tool: str) -> str:
        """
        Enhance a cloud CLI-related request with context information.
        
        Args:
            request: Original request
            context: Context information
            tool: The cloud CLI tool (aws, gcloud, az)
            
        Returns:
            Enhanced request
        """
        # Get cloud configuration
        config_info = ""
        
        try:
            # Get current profile/account/project
            if tool == "aws":
                from angela.execution.engine import execution_engine
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command="aws configure get region",
                    check_safety=True
                )
                
                if return_code == 0:
                    region = stdout.strip()
                    config_info += f"AWS Region: {region}. "
                
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command="aws configure get profile",
                    check_safety=True
                )
                
                if return_code == 0 and stdout.strip():
                    profile = stdout.strip()
                    config_info += f"AWS Profile: {profile}. "
            
            elif tool == "gcloud":
                from angela.execution.engine import execution_engine
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command="gcloud config get-value project",
                    check_safety=True
                )
                
                if return_code == 0 and stdout.strip():
                    project = stdout.strip()
                    config_info += f"GCP Project: {project}. "
                
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command="gcloud config get-value account",
                    check_safety=True
                )
                
                if return_code == 0 and stdout.strip():
                    account = stdout.strip()
                    config_info += f"GCP Account: {account}. "
            
            elif tool == "az":
                from angela.execution.engine import execution_engine
                stdout, stderr, return_code = await execution_engine.execute_command(
                    command="az account show --query name -o tsv",
                    check_safety=True
                )
                
                if return_code == 0 and stdout.strip():
                    account = stdout.strip()
                    config_info += f"Azure Subscription: {account}. "
        except Exception as e:
            self._logger.debug(f"Error getting cloud configuration: {str(e)}")
        
        # Only enhance if we have configuration information
        if config_info:
            return f"{request}\n\nContext: {config_info}"
        
        return request
    
    async def _enhance_package_request(self, request: str, context: Dict[str, Any], tool: str) -> str:
        """
        Enhance a package manager-related request with context information.
        
        Args:
            request: Original request
            context: Context information
            tool: The package manager (npm, yarn, pip, gem)
            
        Returns:
            Enhanced request
        """
        # Get project information
        project_root = context.get("project_root")
        if not project_root:
            return request
        
        # Check for package manager files
        package_files = {
            "npm": os.path.join(project_root, "package.json"),
            "yarn": os.path.join(project_root, "package.json"),
            "pip": [
                os.path.join(project_root, "requirements.txt"),
                os.path.join(project_root, "pyproject.toml"),
                os.path.join(project_root, "setup.py")
            ],
            "gem": os.path.join(project_root, "Gemfile")
        }
        
        # Check for the relevant package file
        if tool in ["npm", "yarn", "gem"]:
            file_path = package_files[tool]
            has_file = os.path.exists(file_path)
            
            if has_file:
                # Get basic package info
                try:
                    if tool in ["npm", "yarn"]:
                        with open(file_path, 'r') as f:
                            package_data = json.load(f)
                        
                        package_info = f"Project: {package_data.get('name', 'Unknown')}. "
                        package_info += f"Version: {package_data.get('version', 'Unknown')}. "
                        
                        deps_count = len(package_data.get("dependencies", {}))
                        dev_deps_count = len(package_data.get("devDependencies", {}))
                        
                        package_info += f"Dependencies: {deps_count}. "
                        package_info += f"Dev Dependencies: {dev_deps_count}. "
                        
                        return f"{request}\n\nContext: {package_info}"
                    
                    elif tool == "gem":
                        # Basic Gemfile info
                        with open(file_path, 'r') as f:
                            gemfile = f.read()
                        
                        # Count gem lines
                        gem_count = len(re.findall(r'^\s*gem\s+', gemfile, re.MULTILINE))
                        
                        package_info = f"Gemfile present with approximately {gem_count} gems. "
                        
                        return f"{request}\n\nContext: {package_info}"
                except Exception as e:
                    self._logger.debug(f"Error reading package file: {str(e)}")
        
        elif tool == "pip":
            # Check multiple possible Python package files
            files = package_files[tool]
            if not isinstance(files, list):
                files = [files]
            
            found_files = [f for f in files if os.path.exists(f)]
            
            if found_files:
                package_info = f"Python package files found: {', '.join([os.path.basename(f) for f in found_files])}. "
                
                # Try to count dependencies in requirements.txt if it exists
                req_txt = os.path.join(project_root, "requirements.txt")
                if os.path.exists(req_txt):
                    try:
                        with open(req_txt, 'r') as f:
                            req_content = f.read()
                        
                        # Count non-empty, non-comment lines
                        req_count = len([line for line in req_content.splitlines() 
                                        if line.strip() and not line.strip().startswith('#')])
                        
                        package_info += f"Requirements: approximately {req_count} packages. "
                    except Exception as e:
                        self._logger.debug(f"Error reading requirements.txt: {str(e)}")
                
                return f"{request}\n\nContext: {package_info}"
        
        return request
    
    async def get_supported_tools(self) -> List[str]:
        """
        Get a list of supported tools on the system.
        
        Returns:
            List of available CLI tools
        """
        if not self._translator:
            if not self.initialize():
                return []
        
        # Start with common tools to check
        common_tools = [
            "git", "docker", "docker-compose", "npm", "yarn", "pip", "gem",
            "aws", "gcloud", "az", "kubectl", "terraform", "ansible",
            "vagrant", "ssh", "scp", "rsync", "curl", "wget"
        ]
        
        available_tools = set()
        
        for tool in common_tools:
            try:
                suggestions = await self._translator.get_tool_suggestions(tool)
                if tool in suggestions:
                    available_tools.add(tool)
            except Exception as e:
                self._logger.debug(f"Error checking tool {tool}: {str(e)}")
        
        # Get additional tools from the universal CLI translator
        try:
            all_suggestions = await self._translator.get_tool_suggestions("")
            available_tools.update(all_suggestions)
        except Exception as e:
            self._logger.debug(f"Error getting additional tools: {str(e)}")
        
        return sorted(available_tools)
    
    async def get_tool_command_suggestions(self, tool: str, context: Dict[str, Any]) -> List[str]:
        """
        Get commonly used commands for a specific tool based on context.
        
        Args:
            tool: The tool name
            context: Context information
            
        Returns:
            List of suggested commands
        """
        self._logger.debug(f"Getting command suggestions for {tool}")
        
        # Use AI to generate contextual command suggestions
        project_type = context.get("project_type", "unknown")
        project_root = context.get("project_root", "unknown")
        
        prompt = f"""
Suggest 5 commonly used commands for the CLI tool "{tool}" that would be most relevant for a {project_type} project.

Current context:
- Project type: {project_type}
- Project directory: {project_root}

For each command, provide:
1. The exact command syntax (no explanations in the command itself)
2. A one-line description of what the command does

Format as JSON:
{{
  "commands": [
    {{ "command": "command syntax", "description": "what it does" }},
    ...
  ]
}}
"""

        try:
            # Call AI service
            api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
            response = await gemini_client.generate_text(api_request)
            
            # Extract JSON
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse JSON
            suggestions_data = json.loads(json_str)
            
            # Extract command suggestions
            commands = []
            for item in suggestions_data.get("commands", []):
                if "command" in item:
                    commands.append(item["command"])
            
            return commands
            
        except Exception as e:
            self._logger.error(f"Error getting command suggestions: {str(e)}")
            
            # Fallback: return common commands for some well-known tools
            common_commands = {
                "git": ["git status", "git add .", "git commit -m 'message'", "git push", "git pull"],
                "docker": ["docker ps", "docker images", "docker build -t name .", "docker run -p 8080:80 name", "docker logs container_name"],
                "npm": ["npm install", "npm start", "npm test", "npm run build", "npm update"],
                "pip": ["pip install -r requirements.txt", "pip list", "pip freeze > requirements.txt", "pip install package", "pip uninstall package"],
                "kubectl": ["kubectl get pods", "kubectl get services", "kubectl apply -f file.yaml", "kubectl describe pod name", "kubectl logs pod_name"]
            }
            
            return common_commands.get(tool, [])

# Create a global instance
enhanced_universal_cli = EnhancedUniversalCLI()

# Register it in the service registry
registry.register("enhanced_universal_cli", enhanced_universal_cli)

# Initialize on module import
enhanced_universal_cli.initialize()
