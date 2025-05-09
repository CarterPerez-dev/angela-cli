# angela/execution/error_recovery.py

import os
import re
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from enum import Enum
from datetime import datetime

from angela.ai.client import gemini_client, GeminiRequest
from angela.ai.analyzer import error_analyzer
from angela.context import context_manager
from angela.utils.logging import get_logger
from angela.shell.formatter import terminal_formatter, OutputType

logger = get_logger(__name__)

class RecoveryStrategy(Enum):
    """Types of error recovery strategies."""
    RETRY = "retry"                 # Simple retry
    MODIFY_COMMAND = "modify"       # Modify the command and retry
    ALTERNATIVE_COMMAND = "alternative"  # Try an alternative command
    PREPARE_ENV = "prepare"         # Prepare the environment and retry
    REVERT_CHANGES = "revert"       # Revert changes and retry
    SKIP = "skip"                   # Skip the step and continue
    ABORT = "abort"                 # Abort the plan execution

class ErrorRecoveryManager:
    """
    Manager for error recovery during multi-step execution.
    
    This class provides:
    1. Analysis of execution errors
    2. Automatic recovery strategies
    3. Guided recovery with user input
    4. Learning from successful recoveries
    """
    
    def __init__(self):
        """Initialize the error recovery manager."""
        self._logger = logger
        self._recovery_history = {}  
        self._success_patterns = {}
        
            
    async def handle_error(
        self, 
        step: Any, 
        error_result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle an error during step execution with enhanced recovery learning.
        
        Args:
            step: The step that failed
            error_result: The execution result with error information
            context: Context information
            
        Returns:
            Updated execution result with recovery information
        """
        self._logger.info(f"Handling error for step {step.id if hasattr(step, 'id') else 'unknown'}")
        
        # Extract error information
        command = error_result.get("command") or getattr(step, "command", None)
        stderr = error_result.get("stderr", "")
        error_msg = error_result.get("error", "")
        
        if not command or (not stderr and not error_msg):
            # Not enough information to recover
            self._logger.warning("Insufficient information for error recovery")
            return error_result
        
        # Analyze the error
        analysis = await self._analyze_error(command, stderr or error_msg)
        
        # Get error pattern for historical matching
        error_pattern = self._extract_error_pattern(error_result)
        
        # Generate recovery strategies
        recovery_strategies = await self._generate_recovery_strategies(command, analysis, context)
        
        # Check if we have historical successes for this error pattern
        if error_pattern in self._success_patterns:
            self._logger.info(f"Found historical recovery strategies for error pattern: {error_pattern}")
            # Add strategies from successful historical recoveries
            for strategy_record in self._success_patterns[error_pattern]:
                historical_strategy = {
                    "type": strategy_record["type"],
                    "command": strategy_record["command"],
                    "description": f"Previously successful strategy (used {strategy_record['success_count']} times)",
                    "confidence": min(0.5 + (strategy_record["success_count"] * 0.1), 0.9),
                    "source": "history"
                }
                # Add to beginning of strategies list if not already present
                if not any(s["type"] == historical_strategy["type"] and s["command"] == historical_strategy["command"] 
                        for s in recovery_strategies):
                    recovery_strategies.insert(0, historical_strategy)
        
        # Prioritize strategies based on historical success
        prioritized_strategies = self._prioritize_strategies_by_history(recovery_strategies)
        
        # Record error analysis and strategies
        result = dict(error_result)
        result["error_analysis"] = analysis
        result["recovery_strategies"] = prioritized_strategies
        
        # Check if we can auto-recover
        if prioritized_strategies and self._can_auto_recover(prioritized_strategies[0]):
            # Attempt automatic recovery
            recovery_result = await self._execute_recovery_strategy(
                prioritized_strategies[0], step, error_result, context
            )
            
            # Update the result
            result["recovery_attempted"] = True
            result["recovery_strategy"] = prioritized_strategies[0]
            result["recovery_success"] = recovery_result.get("success", False)
            
            # Learn from this recovery attempt
            await self._learn_from_recovery_result(recovery_result, step, error_result, context)
            
            # If recovery succeeded, replace the result
            if recovery_result.get("success", False):
                self._logger.info(f"Automatic recovery succeeded for step {getattr(step, 'id', 'unknown')}")
                result.update(recovery_result)
        else:
            # Guided recovery with user input
            recovery_result = await self._guided_recovery(prioritized_strategies, step, error_result, context)
            
            # Update the result
            result["recovery_attempted"] = recovery_result is not None
            if recovery_result:
                result["recovery_strategy"] = recovery_result.get("strategy", {})
                result["recovery_success"] = recovery_result.get("success", False)
                
                # Learn from this recovery attempt
                await self._learn_from_recovery_result(recovery_result, step, error_result, context)
                
                # If recovery succeeded, replace the result
                if recovery_result.get("success", False):
                    self._logger.info(f"Guided recovery succeeded for step {getattr(step, 'id', 'unknown')}")
                    result.update(recovery_result)
        
        return result
    
    async def _learn_from_recovery_result(
        self, 
        recovery_result: Dict[str, Any], 
        step: Any, 
        error_result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> None:
        """
        Learn from recovery attempts to improve future strategies.
        
        Args:
            recovery_result: Result from the recovery attempt
            step: The step that failed
            error_result: Original error information
            context: Context information
        """
        if recovery_result.get("success", False):
            strategy = recovery_result.get("strategy", recovery_result.get("recovery_strategy", {}))
            strategy_type = strategy.get("type")
            error_pattern = self._extract_error_pattern(error_result)
            
            self._logger.debug(f"Learning from successful recovery of type {strategy_type} for pattern {error_pattern}")
            
            if strategy_type and error_pattern:
                # Update recovery history
                strategy_key = f"{strategy_type}:{strategy.get('command', '')}"
                if strategy_key not in self._recovery_history:
                    self._recovery_history[strategy_key] = {"success_count": 0}
                
                self._recovery_history[strategy_key]["success_count"] += 1
                self._recovery_history[strategy_key]["last_success"] = datetime.now().isoformat()
                
                # Record successful strategy for this error pattern
                if error_pattern not in self._success_patterns:
                    self._success_patterns[error_pattern] = []
                
                # Check if strategy already exists for this pattern
                existing_strategy = next(
                    (s for s in self._success_patterns[error_pattern] 
                     if s["type"] == strategy_type and s["command"] == strategy.get("command", "")),
                    None
                )
                
                if existing_strategy:
                    # Update existing strategy
                    existing_strategy["success_count"] += 1
                    existing_strategy["last_success"] = datetime.now().isoformat()
                else:
                    # Add new strategy record
                    strategy_record = {
                        "type": strategy_type,
                        "command": strategy.get("command", ""),
                        "success_count": 1,
                        "last_success": datetime.now().isoformat()
                    }
                    self._success_patterns[error_pattern].append(strategy_record)
                
                # Publish learning event if event_bus is available
                try:
                    if 'event_bus' in globals() or hasattr(self, 'event_bus'):
                        event_bus_obj = globals().get('event_bus', getattr(self, 'event_bus', None))
                        if event_bus_obj and hasattr(event_bus_obj, 'publish'):
                            await event_bus_obj.publish("recovery:learning", {
                                "error_pattern": error_pattern,
                                "successful_strategy": strategy_type,
                                "timestamp": datetime.now().isoformat()
                            })
                except Exception as e:
                    self._logger.error(f"Error publishing learning event: {str(e)}")
    
    def _extract_error_pattern(
        self, 
        error_result: Dict[str, Any]
    ) -> str:
        """
        Extract a pattern that identifies the type of error.
        
        Args:
            error_result: Error information
            
        Returns:
            String pattern identifying the error type
        """
        stderr = error_result.get("stderr", "")
        error_msg = error_result.get("error", "")
        
        # Use stderr or error message
        error_text = stderr or error_msg
        
        # Try to extract the most specific part of the error
        # This is a simplified approach - can be made more sophisticated
        
        # Check for common error patterns
        patterns = self._get_common_error_patterns()
        
        for pattern, pattern_name in patterns:
            if re.search(pattern, error_text, re.IGNORECASE):
                return pattern_name
        
        # If no specific pattern matches, return a more generic one
        # based on the first line of the error
        first_line = error_text.split('\n')[0][:50]
        if first_line:
            return f"generic:{first_line}"
        
        return "unknown_error"
    
    def _prioritize_strategies_by_history(
        self, 
        strategies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize recovery strategies based on historical success.
        
        Args:
            strategies: List of recovery strategies
            
        Returns:
            Prioritized list of strategies
        """
        # Create a copy of the strategies to avoid modifying the original
        prioritized = list(strategies)
        
        # Adjust confidence based on historical success
        for strategy in prioritized:
            strategy_key = f"{strategy.get('type')}:{strategy.get('command', '')}"
            
            # Check history for this strategy
            if strategy_key in self._recovery_history:
                history = self._recovery_history[strategy_key]
                success_count = history.get("success_count", 0)
                
                # Boost confidence based on success count
                # Original confidence is weighted at 60%, historical at 40%
                original_confidence = strategy.get("confidence", 0.5)
                history_confidence = min(0.3 + (success_count * 0.1), 0.9)
                
                # Combine confidences
                adjusted_confidence = (original_confidence * 0.6) + (history_confidence * 0.4)
                strategy["confidence"] = min(adjusted_confidence, 0.95)
                
                # Add metadata about historical success
                strategy["history"] = {
                    "success_count": success_count,
                    "last_success": history.get("last_success", "unknown")
                }
        
        # Sort by confidence (highest first)
        return sorted(prioritized, key=lambda s: s.get("confidence", 0), reverse=True)
    
    async def _analyze_error(self, command: str, error: str) -> Dict[str, Any]:
        """
        Analyze an error to determine its cause and possible fixes.
        
        Args:
            command: The command that failed
            error: The error message
            
        Returns:
            Error analysis result
        """
        # Use the error analyzer to analyze the error
        analysis = error_analyzer.analyze_error(command, error)
        
        # Generate fix suggestions
        suggestions = error_analyzer.generate_fix_suggestions(command, error)
        analysis["fix_suggestions"] = suggestions
        
        # Add error patterns
        error_patterns = analysis.get("error_patterns", [])
        if not error_patterns:
            # Try to match common error patterns
            for pattern in self._get_common_error_patterns():
                if re.search(pattern["pattern"], error, re.IGNORECASE):
                    error_patterns.append({
                        "pattern": pattern["pattern"],
                        "description": pattern["description"],
                        "fixes": pattern["fixes"]
                    })
        
        analysis["error_patterns"] = error_patterns
        
        return analysis
    
    async def _generate_recovery_strategies(
        self, 
        command: str, 
        analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate recovery strategies based on error analysis.
        
        Args:
            command: The command that failed
            analysis: Error analysis result
            context: Context information
            
        Returns:
            List of recovery strategies
        """
        strategies = []
        
        # Check if we have fix suggestions
        if analysis.get("fix_suggestions"):
            for suggestion in analysis["fix_suggestions"]:
                # Parse the suggestion to generate a recovery strategy
                strategy = self._parse_fix_suggestion(suggestion, command)
                if strategy:
                    strategies.append(strategy)
        
        # Check for error patterns
        if analysis.get("error_patterns"):
            for pattern in analysis["error_patterns"]:
                for fix in pattern.get("fixes", []):
                    strategy = self._create_strategy_from_pattern_fix(fix, command)
                    if strategy and not any(s["command"] == strategy["command"] for s in strategies):
                        strategies.append(strategy)
        
        # If no strategies yet, use AI to generate strategies
        if not strategies:
            ai_strategies = await self._generate_ai_recovery_strategies(command, analysis, context)
            strategies.extend(ai_strategies)
        
        # Always add retry and skip as fallback strategies
        if not any(s["type"] == RecoveryStrategy.RETRY.value for s in strategies):
            strategies.append({
                "type": RecoveryStrategy.RETRY.value,
                "command": command,
                "description": "Retry the command without changes",
                "confidence": 0.3
            })
        
        # Add skip strategy
        strategies.append({
            "type": RecoveryStrategy.SKIP.value,
            "command": None,
            "description": "Skip this step and continue with the plan",
            "confidence": 0.2
        })
        
        # Sort strategies by confidence
        strategies.sort(key=lambda s: s.get("confidence", 0), reverse=True)
        
        return strategies
    
    def _parse_fix_suggestion(self, suggestion: str, command: str) -> Optional[Dict[str, Any]]:
        """
        Parse a fix suggestion into a recovery strategy.
        
        Args:
            suggestion: The fix suggestion
            command: The original command
            
        Returns:
            Recovery strategy or None if parsing fails
        """
        # Check for suggested commands in the form of "Try: command"
        command_match = re.search(r'try:?\s*`?([^`]+)`?', suggestion, re.IGNORECASE)
        if command_match:
            suggested_command = command_match.group(1).strip()
            return {
                "type": RecoveryStrategy.MODIFY_COMMAND.value,
                "command": suggested_command,
                "description": suggestion,
                "confidence": 0.8
            }
        
        # Check for permission issues
        if "permission" in suggestion.lower():
            if "sudo" not in command.lower() and not command.strip().startswith("sudo "):
                # Add sudo to the command
                sudo_command = f"sudo {command}"
                return {
                    "type": RecoveryStrategy.MODIFY_COMMAND.value,
                    "command": sudo_command,
                    "description": "Add sudo to the command for elevated privileges",
                    "confidence": 0.7
                }
        
        # Check for missing file or directory suggestions
        if "file not found" in suggestion.lower() or "directory not found" in suggestion.lower():
            mkdir_match = re.search(r'mkdir\s+([^\s]+)', suggestion, re.IGNORECASE)
            if mkdir_match:
                dir_path = mkdir_match.group(1)
                return {
                    "type": RecoveryStrategy.PREPARE_ENV.value,
                    "command": f"mkdir -p {dir_path}",
                    "description": f"Create the directory {dir_path} and retry",
                    "confidence": 0.7,
                    "retry_original": True
                }
        
        # General suggestion without a specific command
        return {
            "type": RecoveryStrategy.ALTERNATIVE_COMMAND.value,
            "command": None,  # Will be filled in by AI
            "description": suggestion,
            "confidence": 0.5
        }
    
    def _create_strategy_from_pattern_fix(self, fix: str, command: str) -> Optional[Dict[str, Any]]:
        """
        Create a recovery strategy from a pattern fix.
        
        Args:
            fix: The fix description
            command: The original command
            
        Returns:
            Recovery strategy or None if parsing fails
        """
        # Check for command suggestions
        command_match = re.search(r'`([^`]+)`', fix)
        if command_match:
            suggested_command = command_match.group(1).strip()
            return {
                "type": RecoveryStrategy.ALTERNATIVE_COMMAND.value,
                "command": suggested_command,
                "description": fix,
                "confidence": 0.7
            }
        
        # Check for common actions
        if "install" in fix.lower():
            # Extract package name
            pkg_match = re.search(r'install\s+(\w+)', fix, re.IGNORECASE)
            if pkg_match:
                pkg_name = pkg_match.group(1)
                return {
                    "type": RecoveryStrategy.PREPARE_ENV.value,
                    "command": f"apt-get install -y {pkg_name}",
                    "description": f"Install missing package: {pkg_name}",
                    "confidence": 0.7,
                    "retry_original": True
                }
        
        return None
    
    async def _generate_ai_recovery_strategies(
        self, 
        command: str, 
        analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate recovery strategies using the AI.
        
        Args:
            command: The command that failed
            analysis: Error analysis result
            context: Context information
            
        Returns:
            List of AI-generated recovery strategies
        """
        # Build a prompt for strategy generation
        error_summary = analysis.get("error_summary", "Unknown error")
        possible_cause = analysis.get("possible_cause", "Unknown cause")
        
        prompt = f"""
Generate recovery strategies for a failed command execution.

Failed command: `{command}`
Error summary: {error_summary}
Possible cause: {possible_cause}

Generate 2-3 specific recovery strategies, each with:
1. A specific command to execute
2. A description of what the strategy does
3. A confidence level (0.0-1.0)

Format your response as JSON:
[
  {{
    "type": "modify",
    "command": "modified command",
    "description": "Description of the strategy",
    "confidence": 0.8
  }},
  {{
    "type": "prepare",
    "command": "preparation command",
    "description": "Prepare the environment",
    "confidence": 0.7,
    "retry_original": true
  }}
]

Valid strategy types:
- modify: Modify the original command
- alternative: Use an alternative command
- prepare: Prepare the environment and retry
- revert: Revert changes and retry
"""
        
        # Call the AI service
        api_request = GeminiRequest(prompt=prompt, max_tokens=1000)
        api_response = await gemini_client.generate_text(api_request)
        
        # Parse the response
        try:
            # Extract JSON from the response
            import re
            import json
            
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', api_response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = api_response.text
            
            # Parse the JSON
            strategies = json.loads(json_str)
            
            # Validate and normalize strategies
            valid_strategies = []
            for strategy in strategies:
                if isinstance(strategy, dict) and "type" in strategy and "command" in strategy:
                    # Ensure type is valid
                    try:
                        RecoveryStrategy(strategy["type"])
                        valid_strategies.append(strategy)
                    except ValueError:
                        # Invalid strategy type, skip it
                        pass
            
            return valid_strategies
            
        except Exception as e:
            self._logger.error(f"Error parsing AI recovery strategies: {str(e)}")
            return []
    
    def _can_auto_recover(self, strategy: Dict[str, Any]) -> bool:
        """
        Determine if a strategy can be applied automatically.
        
        Args:
            strategy: The recovery strategy
            
        Returns:
            True if auto-recovery is possible, False otherwise
        """
        # High confidence strategies can be auto-applied
        if strategy.get("confidence", 0) >= 0.8:
            return True
        
        # Certain strategy types can always be auto-applied
        auto_types = [
            RecoveryStrategy.RETRY.value
        ]
        
        if strategy.get("type") in auto_types:
            return True
        
        # Check if the strategy has been successful in the past
        strategy_key = f"{strategy.get('type')}:{strategy.get('command')}"
        if self._recovery_history.get(strategy_key, {}).get("success_count", 0) > 0:
            return True
        
        return False
    
    async def _execute_recovery_strategy(
        self, 
        strategy: Dict[str, Any], 
        step: Any, 
        error_result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a recovery strategy.
        
        Args:
            strategy: The recovery strategy to execute
            step: The step that failed
            error_result: The original error result
            context: Context information
            
        Returns:
            Updated execution result
        """
        self._logger.info(f"Executing recovery strategy: {strategy.get('type')}")
        
        # Import here to avoid circular imports
        from angela.execution.engine import execution_engine
        
        result = {
            "strategy": strategy,
            "original_error": error_result.get("error"),
            "original_stderr": error_result.get("stderr")
        }
        
        try:
            # Execute based on strategy type
            strategy_type = strategy.get("type")
            
            if strategy_type == RecoveryStrategy.RETRY.value:
                # Simple retry of the original command
                command = getattr(step, "command", None) or error_result.get("command")
                if command:
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command,
                        check_safety=False  # Skip safety checks for retry
                    )
                    
                    result.update({
                        "command": command,
                        "stdout": stdout,
                        "stderr": stderr,
                        "return_code": return_code,
                        "success": return_code == 0
                    })
                else:
                    result.update({
                        "error": "No command available for retry",
                        "success": False
                    })
            
            elif strategy_type in [RecoveryStrategy.MODIFY_COMMAND.value, 
                                RecoveryStrategy.ALTERNATIVE_COMMAND.value]:
                # Execute modified or alternative command
                command = strategy.get("command")
                if command:
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command,
                        check_safety=True  # Safety checks for new commands
                    )
                    
                    result.update({
                        "command": command,
                        "stdout": stdout,
                        "stderr": stderr,
                        "return_code": return_code,
                        "success": return_code == 0
                    })
                    
                    # If successful and requested, retry the original command
                    if return_code == 0 and strategy.get("retry_original"):
                        original_command = getattr(step, "command", None) or error_result.get("command")
                        if original_command:
                            self._logger.info(f"Retrying original command: {original_command}")
                            stdout, stderr, return_code = await execution_engine.execute_command(
                                original_command,
                                check_safety=False
                            )
                            
                            result.update({
                                "original_retry": {
                                    "command": original_command,
                                    "stdout": stdout,
                                    "stderr": stderr,
                                    "return_code": return_code,
                                    "success": return_code == 0
                                }
                            })
                            
                            # Update overall success based on original command retry
                            result["success"] = return_code == 0
                else:
                    result.update({
                        "error": "No command specified in strategy",
                        "success": False
                    })
            
            elif strategy_type == RecoveryStrategy.PREPARE_ENV.value:
                # Execute preparation command
                command = strategy.get("command")
                if command:
                    stdout, stderr, return_code = await execution_engine.execute_command(
                        command,
                        check_safety=True
                    )
                    
                    result.update({
                        "preparation": {
                            "command": command,
                            "stdout": stdout,
                            "stderr": stderr,
                            "return_code": return_code,
                            "success": return_code == 0
                        }
                    })
                    
                    # If preparation succeeded and requested, retry the original command
                    if return_code == 0 and strategy.get("retry_original"):
                        original_command = getattr(step, "command", None) or error_result.get("command")
                        if original_command:
                            self._logger.info(f"Retrying original command after preparation: {original_command}")
                            stdout, stderr, return_code = await execution_engine.execute_command(
                                original_command,
                                check_safety=False
                            )
                            
                            result.update({
                                "command": original_command,
                                "stdout": stdout,
                                "stderr": stderr,
                                "return_code": return_code,
                                "success": return_code == 0
                            })
                        else:
                            result.update({
                                "error": "No original command available for retry",
                                "success": False
                            })
                    else:
                        # No retry requested or preparation failed
                        result["success"] = return_code == 0
                else:
                    result.update({
                        "error": "No preparation command specified in strategy",
                        "success": False
                    })
            
            elif strategy_type == RecoveryStrategy.REVERT_CHANGES.value:
                # Revert changes (simplified implementation)
                result.update({
                    "message": "Revert changes not implemented",
                    "success": False
                })
            
            elif strategy_type == RecoveryStrategy.SKIP.value:
                # Skip the step
                result.update({
                    "message": "Step skipped",
                    "success": True,
                    "skipped": True
                })
            
            else:
                result.update({
                    "error": f"Unknown strategy type: {strategy_type}",
                    "success": False
                })
            
            # Update recovery history
            if result.get("success"):
                strategy_key = f"{strategy.get('type')}:{strategy.get('command')}"
                if strategy_key in self._recovery_history:
                    self._recovery_history[strategy_key]["success_count"] += 1
                    self._recovery_history[strategy_key]["last_success"] = datetime.now()
                else:
                    self._recovery_history[strategy_key] = {
                        "success_count": 1,
                        "failure_count": 0,
                        "last_success": datetime.now()
                    }
            
            return result
            
        except Exception as e:
            self._logger.exception(f"Error executing recovery strategy: {str(e)}")
            return {
                "strategy": strategy,
                "error": str(e),
                "success": False
            }
    
    async def _guided_recovery(
        self, 
        strategies: List[Dict[str, Any]], 
        step: Any, 
        error_result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Guide the user through recovery options.
        
        Args:
            strategies: Available recovery strategies
            step: The step that failed
            error_result: The original error result
            context: Context information
            
        Returns:
            Recovery result or None if aborted
        """
        if not strategies:
            return None
        
        # Display recovery options
        terminal_formatter.print_output(
            "Command execution failed. The following recovery options are available:",
            OutputType.WARNING,
            title="Recovery Options"
        )
        
        # Display the error
        terminal_formatter.print_output(
            error_result.get("stderr", "") or error_result.get("error", "Unknown error"),
            OutputType.ERROR,
            title="Error"
        )
        
        # Show strategies
        for i, strategy in enumerate(strategies):
            description = strategy.get("description", "No description")
            command = strategy.get("command", "No command")
            
            if strategy.get("type") == RecoveryStrategy.SKIP.value:
                terminal_formatter.print_output(
                    f"Option {i+1}: [Skip] {description}",
                    OutputType.INFO
                )
            else:
                terminal_formatter.print_output(
                    f"Option {i+1}: {description}\n  Command: {command}",
                    OutputType.INFO
                )
        
        # Add abort option
        terminal_formatter.print_output(
            f"Option {len(strategies)+1}: [Abort] Abort execution",
            OutputType.WARNING
        )
        
        # Get user selection
        from prompt_toolkit.shortcuts import input_dialog
        selection = input_dialog(
            title="Select Recovery Option",
            text="Enter option number:",
        ).run()
        
        if not selection or not selection.isdigit():
            return None
        
        option = int(selection)
        
        # Handle abort option
        if option == len(strategies) + 1:
            return {
                "message": "Execution aborted by user",
                "success": False,
                "aborted": True
            }
        
        # Handle strategy selection
        if 1 <= option <= len(strategies):
            selected_strategy = strategies[option - 1]
            
            # Execute the selected strategy
            return await self._execute_recovery_strategy(
                selected_strategy, step, error_result, context
            )
        
        return None
    
    def _get_common_error_patterns(self) -> List[Dict[str, Any]]:
        """
        Get common error patterns and fix suggestions.
        
        Returns:
            List of error pattern dictionaries
        """
        return [
            {
                "pattern": r'permission denied|cannot access|operation not permitted',
                "description": "Permission denied error",
                "fixes": [
                    "Try running the command with sudo: `sudo {command}`",
                    "Check file permissions with `ls -l {path}`",
                    "Change file permissions with `chmod +x {path}`"
                ]
            },
            {
                "pattern": r'command not found|not installed|no such file or directory',
                "description": "Command or file not found",
                "fixes": [
                    "Install the package containing the command",
                    "Check if the path is correct",
                    "Use `which {command}` to check if the command is in PATH"
                ]
            },
            {
                "pattern": r'syntax error|invalid option|unrecognized option',
                "description": "Command syntax error",
                "fixes": [
                    "Check the command syntax with `man {command}`",
                    "Remove problematic options or flags",
                    "Ensure quotes and brackets are properly matched"
                ]
            },
            {
                "pattern": r'cannot connect|connection refused|network is unreachable',
                "description": "Network connection error",
                "fixes": [
                    "Check if the host is reachable with `ping {host}`",
                    "Verify network connectivity",
                    "Ensure the service is running with `systemctl status {service}`"
                ]
            },
            {
                "pattern": r'disk quota exceeded|no space left on device|file system is full',
                "description": "Disk space issue",
                "fixes": [
                    "Free up disk space with `df -h` to check and `rm` to remove files",
                    "Clean up temporary files with `apt-get clean` or `yum clean all`",
                    "Compress large files with `gzip {file}`"
                ]
            },
            {
                "pattern": r'resource temporarily unavailable|resource busy|device or resource busy',
                "description": "Resource busy error",
                "fixes": [
                    "Wait and try again later",
                    "Check what processes are using the resource with `lsof {path}`",
                    "Terminate competing processes with `kill {pid}`"
                ]
            }
        ]
