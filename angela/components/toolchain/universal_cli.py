# angela/components/toolchain/universal_cli.py

"""
Universal CLI Translator for Angela CLI.

This module provides the ability to translate natural language requests
into commands for arbitrary CLI tools by analyzing their help documentation
and applying knowledge about CLI conventions.
"""
import asyncio
import re
import shlex
import subprocess
import os
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from pathlib import Path

from pydantic import BaseModel, Field

# Updated imports to use API layer
from angela.api.ai import get_gemini_client, GeminiRequest
from angela.api.context import get_context_manager
from angela.utils.logging import get_logger
from angela.api.safety import get_command_validator
from angela.core.registry import registry

logger = get_logger(__name__)

class CommandParameter(BaseModel):
    """Model for a command parameter."""
    name: str
    description: Optional[str] = None
    required: bool = False
    type: str = "string"  # string, number, boolean, etc.
    short_flag: Optional[str] = None  # e.g. -f
    long_flag: Optional[str] = None  # e.g. --file
    default: Optional[Any] = None
    values: Optional[List[str]] = None  # possible values for enum-like parameters

class CommandOption(BaseModel):
    """Model for a command option."""
    name: str
    description: Optional[str] = None
    short_flag: Optional[str] = None  # e.g. -v
    long_flag: Optional[str] = None  # e.g. --verbose
    takes_value: bool = False

class CommandDefinition(BaseModel):
    """Model for a CLI command definition."""
    tool: str  # The CLI tool name (e.g., "git", "docker")
    command: str  # The command name (e.g., "commit", "run")
    description: Optional[str] = None
    usage: Optional[str] = None
    parameters: List[CommandParameter] = Field(default_factory=list)
    options: List[CommandOption] = Field(default_factory=list)
    subcommands: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)

class UniversalCLITranslator:
    """
    Translates natural language requests into commands for arbitrary CLI tools.
    
    This class analyzes help documentation from CLI tools to understand their
    command structure and parameters, then matches natural language requests
    to appropriate commands and generates valid command strings.
    """
    
    def __init__(self):
        """Initialize the translator."""
        self._logger = logger
        self._command_cache: Dict[str, CommandDefinition] = {}
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._recently_used_tools: List[str] = []
    
    async def translate_request(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate a natural language request into a command for a CLI tool.
        
        Args:
            request: The natural language request
            context: Context information
            
        Returns:
            Dictionary with the translation result
        """
        self._logger.info(f"Translating request: {request}")
        
        # Analyze the request to determine the likely tool and command
        analysis = await self._analyze_request(request, context)
        
        if not analysis or not analysis.get("tool"):
            return {
                "success": False,
                "error": "Could not determine which CLI tool to use",
                "request": request
            }
        
        tool = analysis["tool"]
        command = analysis.get("command", "")
        
        # Add to recently used tools
        self._update_recently_used_tools(tool)
        
        # Get the command definition for the tool
        command_def = await self._get_command_definition(tool, command)
        
        if not command_def:
            return {
                "success": False,
                "error": f"Could not get command definition for {tool} {command}",
                "request": request,
                "tool": tool,
                "command": command
            }
        
        # Generate a command string using the definition and the request
        cmd_result = await self._generate_command_string(request, command_def, analysis)
        
        if not cmd_result.get("success"):
            return {
                "success": False,
                "error": cmd_result.get("error", "Failed to generate command string"),
                "request": request,
                "tool": tool,
                "command": command
            }
        
        # Validate the generated command for safety
        command_str = cmd_result["command"]
        # Get command validator from API
        command_validator = get_command_validator()
        is_safe, error_message = command_validator(command_str)
        
        if not is_safe:
            return {
                "success": False,
                "error": f"Generated command fails safety validation: {error_message}",
                "request": request,
                "tool": tool,
                "command": command,
                "generated_command": command_str
            }
        
        # Return the successful result
        return {
            "success": True,
            "command": command_str,
            "tool": tool,
            "subcommand": command,
            "explanation": cmd_result.get("explanation", ""),
            "request": request
        }
    
    def _update_recently_used_tools(self, tool: str) -> None:
        """
        Update the list of recently used tools.
        
        Args:
            tool: The tool name to add/move to front
        """
        # Remove the tool if already in the list
        if tool in self._recently_used_tools:
            self._recently_used_tools.remove(tool)
        
        # Add to the front of the list
        self._recently_used_tools.insert(0, tool)
        
        # Keep list at a reasonable size
        self._recently_used_tools = self._recently_used_tools[:10]
    
    async def _analyze_request(
        self, 
        request: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a request to determine the likely CLI tool and command.
        
        Args:
            request: The natural language request
            context: Context information
            
        Returns:
            Dictionary with analysis results
        """
        # Check if we've already analyzed this request
        cache_key = request.strip().lower()
        if cache_key in self._analysis_cache:
            self._logger.debug(f"Using cached analysis for request: {request}")
            return self._analysis_cache[cache_key]
        
        # Prepare the context information for the prompt
        recently_used = ", ".join(self._recently_used_tools) if self._recently_used_tools else "None"
        
        # Use AI to analyze the request
        prompt = f"""
You are an expert command-line tools analyst. Your task is to analyze a natural language request and determine:
1. Which CLI tool the user likely wants to use
2. Which command or subcommand for that tool
3. What parameters and options might be needed

User's request: "{request}"

Context information:
- Current directory: {context.get('cwd', 'Unknown')}
- Recently used tools: {recently_used}

Return a JSON object with:
- tool: The name of the CLI tool (e.g., "git", "docker", "aws")
- command: The specific command or subcommand (e.g., "commit", "run", "s3 cp")
- parameters: List of likely parameters needed, each with a name and value
- options: List of likely options needed, each with a name (e.g., "verbose")

Only include the most likely tool. If you're unsure, make your best guess.
"""
        
        self._logger.debug("Sending analysis request to AI service")
        
        # Get gemini client from API
        gemini_client = get_gemini_client()
        
        # Call AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract JSON from the response
            import json
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse the JSON
            analysis = json.loads(json_str)
            
            # Cache the result
            self._analysis_cache[cache_key] = analysis
            
            self._logger.debug(f"Analysis found tool: {analysis.get('tool')}, command: {analysis.get('command')}")
            
            return analysis
            
        except Exception as e:
            self._logger.error(f"Error parsing analysis response: {str(e)}")
            return {"error": str(e)}
    
    async def _get_command_definition(
        self, 
        tool: str, 
        command: Optional[str] = None
    ) -> Optional[CommandDefinition]:
        """
        Get or create a command definition for a CLI tool.
        
        Args:
            tool: The CLI tool name (e.g., "git", "docker")
            command: Optional specific command to get
            
        Returns:
            CommandDefinition object or None if not found
        """
        # Check if we already have this command cached
        cache_key = f"{tool}:{command}" if command else tool
        if cache_key in self._command_cache:
            self._logger.debug(f"Using cached command definition for {cache_key}")
            return self._command_cache[cache_key]
        
        # Check if the tool is available
        if not await self._is_tool_available(tool):
            self._logger.warning(f"Tool {tool} not available in the system")
            return None
        
        # Generate the help command based on the tool and command
        help_cmd = await self._generate_help_command(tool, command)
        
        # Run the help command to get documentation
        help_text = await self._get_help_text(help_cmd)
        if not help_text:
            self._logger.warning(f"Could not get help text for {tool} {command}")
            return None
        
        # Parse the help text to create a command definition
        command_def = await self._parse_help_text(tool, command, help_text)
        
        if command_def:
            # Cache the result
            self._command_cache[cache_key] = command_def
            self._logger.debug(f"Cached command definition for {cache_key}")
        
        return command_def
    
    async def _is_tool_available(self, tool: str) -> bool:
        """
        Check if a CLI tool is available in the system.
        
        Args:
            tool: The CLI tool name
            
        Returns:
            True if the tool is available, False otherwise
        """
        try:
            self._logger.debug(f"Checking if tool is available: {tool}")
            
            # Try to run the command with --version or --help
            process = await asyncio.create_subprocess_exec(
                tool, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                self._logger.debug(f"Tool {tool} is available (--version check)")
                return True
            
            # Try with --help if --version failed
            process = await asyncio.create_subprocess_exec(
                tool, "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            availability = process.returncode == 0
            self._logger.debug(f"Tool {tool} {'is' if availability else 'is not'} available (--help check)")
            return availability
            
        except Exception as e:
            self._logger.error(f"Error checking tool availability for {tool}: {str(e)}")
            return False
    
    async def _generate_help_command(
        self, 
        tool: str, 
        command: Optional[str] = None
    ) -> str:
        """
        Generate a help command for a CLI tool.
        
        Args:
            tool: The CLI tool name
            command: Optional specific command
            
        Returns:
            Help command string
        """
        if command:
            # Try with both --help and help syntax
            return f"{tool} {command} --help"
        else:
            return f"{tool} --help"
    
    async def _get_help_text(self, help_cmd: str) -> Optional[str]:
        """
        Get help text by running a help command.
        
        Args:
            help_cmd: The help command to run
            
        Returns:
            Help text string or None if failed
        """
        try:
            self._logger.debug(f"Running help command: {help_cmd}")
            
            # Split the command into args
            args = shlex.split(help_cmd)
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Combine stdout and stderr as some tools print help to stderr
            help_text = stdout.decode('utf-8', errors='replace')
            if not help_text and stderr:
                help_text = stderr.decode('utf-8', errors='replace')
            
            if help_text:
                self._logger.debug(f"Got help text of length {len(help_text)}")
            else:
                self._logger.warning(f"No help text received for command: {help_cmd}")
            
            return help_text if help_text else None
            
        except Exception as e:
            self._logger.error(f"Error running help command '{help_cmd}': {str(e)}")
            return None
    
    async def _parse_help_text(
        self, 
        tool: str, 
        command: Optional[str], 
        help_text: str
    ) -> Optional[CommandDefinition]:
        """
        Parse help text to create a command definition.
        
        Args:
            tool: The CLI tool name
            command: Optional specific command
            help_text: Help text to parse
            
        Returns:
            CommandDefinition object or None if parsing failed
        """
        # This is a complex task that varies by tool, so we'll use AI to help
        self._logger.debug(f"Parsing help text for {tool} {command or ''}")
        
        # Truncate help text if too long for prompt
        max_help_text_len = 4000
        truncated_help = help_text
        if len(help_text) > max_help_text_len:
            truncated_help = help_text[:max_help_text_len] + "... [truncated]"
            self._logger.debug(f"Truncated help text from {len(help_text)} to {max_help_text_len} characters")
        
        prompt = f"""
You are an expert in command-line interfaces. Parse this help text for {tool} {command or ''} and extract:
1. Command description
2. Usage syntax
3. Parameters (required inputs)
4. Options (flags)
5. Examples

Help text:
```
{truncated_help}
```

Return a structured JSON object with:
- tool: "{tool}"
- command: "{command or ''}"
- description: Command description
- usage: Usage syntax
- parameters: List of parameters with name, description, required status, type
- options: List of options with name, description, short_flag, long_flag
- examples: List of example commands

Focus on accuracy. Skip any sections you can't confidently parse.
"""

        gemini_client = get_gemini_client()        
        # Call AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=2000)
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract JSON from the response
            import json
            
            # Try to find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Assume the entire response is JSON
                json_str = response.text
            
            # Parse the JSON
            cmd_data = json.loads(json_str)
            
            self._logger.debug(f"Successfully parsed help text into command definition")
            
            # Create CommandParameter objects
            parameters = []
            for param_data in cmd_data.get("parameters", []):
                param = CommandParameter(
                    name=param_data["name"],
                    description=param_data.get("description"),
                    required=param_data.get("required", False),
                    type=param_data.get("type", "string")
                )
                parameters.append(param)
            
            # Create CommandOption objects
            options = []
            for opt_data in cmd_data.get("options", []):
                opt = CommandOption(
                    name=opt_data["name"],
                    description=opt_data.get("description"),
                    short_flag=opt_data.get("short_flag"),
                    long_flag=opt_data.get("long_flag"),
                    takes_value=opt_data.get("takes_value", False)
                )
                options.append(opt)
            
            # Create the CommandDefinition
            cmd_def = CommandDefinition(
                tool=tool,
                command=command or "",
                description=cmd_data.get("description"),
                usage=cmd_data.get("usage"),
                parameters=parameters,
                options=options,
                examples=cmd_data.get("examples", [])
            )
            
            return cmd_def
            
        except Exception as e:
            self._logger.error(f"Error parsing help text for {tool} {command}: {str(e)}")
            return None
    
    async def _generate_command_string(
        self, 
        request: str, 
        command_def: CommandDefinition, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a command string based on the request and command definition.
        
        Args:
            request: The natural language request
            command_def: The command definition
            analysis: The request analysis results
            
        Returns:
            Dictionary with the command string and explanation
        """
        self._logger.debug(f"Generating command string for request: {request}")
        
        # Use AI to generate the command string
        prompt = f"""
You are an expert CLI command generator. Your task is to generate a valid command based on user request and command definition.

User request: "{request}"

Command definition:
- Tool: {command_def.tool}
- Command: {command_def.command}
- Description: {command_def.description or 'N/A'}
- Usage: {command_def.usage or 'N/A'}

Parameters:
{self._format_parameters(command_def.parameters)}

Options:
{self._format_options(command_def.options)}

Examples:
{self._format_examples(command_def.examples)}

Generate a complete, valid command that fulfills the user's request.
Along with the command, provide a brief explanation of what it does and why you chose specific parameters/options.

Return your response as:
COMMAND: <the exact command string>
EXPLANATION: <explanation of the command>

Be precise and accurate. Include necessary quotes for paths or arguments that need them.
"""
        
        # Get gemini client from API
        gemini_client = get_gemini_client()
        
        # Call AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
        response = await gemini_client.generate_text(api_request)
        
        try:
            # Extract the command and explanation from the response
            command_match = re.search(r'COMMAND:\s*(.+?)(?:\n|$)', response.text)
            explanation_match = re.search(r'EXPLANATION:\s*(.+(?:\n.+)*)', response.text)
            
            if not command_match:
                self._logger.error("Could not extract command from AI response")
                return {
                    "success": False,
                    "error": "Could not extract command from AI response"
                }
            
            command = command_match.group(1).strip()
            explanation = explanation_match.group(1).strip() if explanation_match else ""
            
            self._logger.debug(f"Generated command: {command}")
            
            return {
                "success": True,
                "command": command,
                "explanation": explanation
            }
            
        except Exception as e:
            self._logger.error(f"Error extracting command from response: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_parameters(self, parameters: List[CommandParameter]) -> str:
        """Format parameters for the prompt."""
        if not parameters:
            return "None"
        
        result = []
        for param in parameters:
            required = "Required" if param.required else "Optional"
            result.append(f"- {param.name}: {param.description or 'No description'} ({required}, Type: {param.type})")
        
        return "\n".join(result)
    
    def _format_options(self, options: List[CommandOption]) -> str:
        """Format options for the prompt."""
        if not options:
            return "None"
        
        result = []
        for opt in options:
            flags = []
            if opt.short_flag:
                flags.append(opt.short_flag)
            if opt.long_flag:
                flags.append(opt.long_flag)
            
            flags_str = ", ".join(flags) if flags else "No flag"
            result.append(f"- {opt.name}: {opt.description or 'No description'} (Flags: {flags_str})")
        
        return "\n".join(result)
    
    def _format_examples(self, examples: List[str]) -> str:
        """Format examples for the prompt."""
        if not examples:
            return "None"
        
        result = []
        for i, example in enumerate(examples, 1):
            result.append(f"{i}. {example}")
        
        return "\n".join(result)
    
    async def get_tool_suggestions(self, partial_tool: str = "") -> List[str]:
        """
        Get suggestions for available tools.
        
        Args:
            partial_tool: Optional partial tool name to filter by
            
        Returns:
            List of tool suggestions
        """
        # Check common locations for executables
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        
        tools = set()
        for path_dir in path_dirs:
            if not os.path.exists(path_dir):
                continue
                
            for entry in os.listdir(path_dir):
                entry_path = os.path.join(path_dir, entry)
                if os.path.isfile(entry_path) and os.access(entry_path, os.X_OK):
                    if not partial_tool or entry.startswith(partial_tool):
                        tools.add(entry)
        
        # Prioritize recently used tools
        result = []
        for tool in self._recently_used_tools:
            if tool in tools and (not partial_tool or tool.startswith(partial_tool)):
                result.append(tool)
                tools.remove(tool)
        
        # Add remaining tools
        result.extend(sorted(tools))
        
        return result


# Global instance
universal_cli_translator = UniversalCLITranslator()
