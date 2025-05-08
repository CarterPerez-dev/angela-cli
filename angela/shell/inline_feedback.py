"""
Inline feedback and interaction system for Angela CLI.
"""
import sys
import os
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
import time
import threading

from angela.utils.logging import get_logger
from angela.context.session import session_manager

logger = get_logger(__name__)

class InlineFeedback:
    """
    Provides inline feedback and interaction capabilities.
    
    This class allows Angela to display feedback, ask questions, and
    interact with the user directly within the terminal session.
    """
    
    def __init__(self):
        """Initialize the inline feedback system."""
        self._logger = logger
        self._active_prompts = {}
        self._last_message_time = 0
        self._message_cooldown = 5  # Seconds between automatic messages
        self._prompt_id_counter = 0
        self._active_threads = {}
    
    async def show_message(
        self, 
        message: str, 
        message_type: str = "info",
        timeout: float = 0
    ) -> None:
        """
        Display a message inline in the terminal.
        
        Args:
            message: The message to display
            message_type: Type of message (info, warning, error, success)
            timeout: Auto-clear message after this many seconds (0 = no auto-clear)
        """
        # Respect cooldown for automatic messages
        current_time = time.time()
        if current_time - self._last_message_time < self._message_cooldown:
            self._logger.debug(f"Skipping message due to cooldown: {message}")
            return
        
        self._last_message_time = current_time
        
        # Determine color based on message type
        color_code = {
            "info": "\033[34m",     # Blue
            "warning": "\033[33m",  # Yellow
            "error": "\033[31m",    # Red
            "success": "\033[32m",  # Green
        }.get(message_type, "\033[34m")  # Default to blue
        
        reset_code = "\033[0m"
        
        # Format the message
        formatted_message = f"\n{color_code}[Angela] {message}{reset_code}"
        
        # Print the message
        print(formatted_message, file=sys.stderr)
        
        # Set up auto-clear if timeout is specified
        if timeout > 0:
            # Schedule message clear after timeout
            asyncio.create_task(self._clear_message_after_timeout(formatted_message, timeout))
    
    async def ask_question(
        self, 
        question: str,
        options: List[str],
        default_option: Optional[str] = None,
        timeout: int = 30,
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        Ask a question inline and wait for response.
        
        Args:
            question: The question to ask
            options: List of possible answers
            default_option: Default option to use if user doesn't respond
            timeout: Timeout in seconds before using default
            callback: Optional callback to call with the selected option
            
        Returns:
            The selected option
        """
        prompt_id = self._get_next_prompt_id()
        
        # Format options display
        options_display = "/".join(options)
        if default_option and default_option in options:
            # Highlight default option
            options_display = options_display.replace(
                default_option, 
                f"[{default_option}]"
            )
        
        # Format the question
        formatted_question = f"\n\033[35m[Angela] {question} ({options_display})\033[0m "
        
        # Store active prompt
        self._active_prompts[prompt_id] = {
            "question": question,
            "options": options,
            "default": default_option,
            "result": asyncio.Future(),
            "formatted_question": formatted_question
        }
        
        # Start a thread to handle user input
        thread = threading.Thread(
            target=self._input_thread,
            args=(prompt_id, formatted_question, options, default_option, timeout)
        )
        thread.daemon = True
        thread.start()
        
        self._active_threads[prompt_id] = thread
        
        try:
            # Wait for the result
            result = await self._active_prompts[prompt_id]["result"]
            
            # Call the callback if provided
            if callback and result:
                await callback(result)
            
            return result
        finally:
            # Clean up
            if prompt_id in self._active_prompts:
                del self._active_prompts[prompt_id]
            if prompt_id in self._active_threads:
                del self._active_threads[prompt_id]
    
    async def suggest_command(
        self, 
        command: str,
        explanation: str,
        confidence: float = 0.8,
        execute_callback: Optional[Callable[[], Awaitable[None]]] = None
    ) -> bool:
        """
        Suggest a command and offer to execute it.
        
        Args:
            command: The command to suggest
            explanation: Explanation for the suggestion
            confidence: Confidence level (0.0-1.0)
            execute_callback: Callback to execute if accepted
            
        Returns:
            True if the suggestion was accepted, False otherwise
        """
        # Format confidence indicator
        confidence_stars = int(confidence * 5)
        confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
        
        # Format the message
        message = (
            f"I suggest this command: \033[1m{command}\033[0m\n"
            f"Confidence: {confidence_display} ({confidence:.2f})\n"
            f"{explanation}\n"
            f"Execute? (y/n/e - where 'e' will edit before executing)"
        )
        
        # Ask the question
        response = await self.ask_question(
            message,
            ["y", "n", "e"],
            default_option="n",
            timeout=30
        )
        
        if response == "y":
            # User accepted the suggestion
            if execute_callback:
                await execute_callback()
            return True
        elif response == "e":
            # User wants to edit before executing
            edited_command = await self._get_edited_command(command)
            if edited_command and execute_callback:
                # Store the edited command for execution
                session_manager.add_entity("edited_command", "command", edited_command)
                await execute_callback()
                return True
        
        # User declined or edited but didn't execute
        return False
    
    async def _get_edited_command(self, original_command: str) -> Optional[str]:
        """
        Allow the user to edit a command.
        
        Args:
            original_command: The original command
            
        Returns:
            The edited command or None if cancelled
        """
        # This implementation is simplified - in a real implementation,
        # you might want to use a library like prompt_toolkit for a more
        # sophisticated editor
        
        print(f"\n\033[36m[Angela] Edit the command (Ctrl+C to cancel):\033[0m", file=sys.stderr)
        print(f"\033[36m> \033[1m{original_command}\033[0m", file=sys.stderr)
        
        try:
            # Start a thread to get user input
            input_future = asyncio.Future()
            
            def get_input():
                try:
                    user_input = input("\033[36m> \033[0m")
                    asyncio.run(self._set_future_result(input_future, user_input))
                except (KeyboardInterrupt, EOFError):
                    asyncio.run(self._set_future_result(input_future, None))
            
            thread = threading.Thread(target=get_input)
            thread.daemon = True
            thread.start()
            
            # Wait for input with a timeout
            return await asyncio.wait_for(input_future, timeout=60)
            
        except asyncio.TimeoutError:
            print("\n\033[33m[Angela] Edit timed out\033[0m", file=sys.stderr)
            return None
    
    async def _set_future_result(self, future, result):
        """Set the result of a future, handling event loop issues."""
        if not future.done():
            future.set_result(result)
    
    def _input_thread(
        self, 
        prompt_id: int,
        formatted_question: str,
        options: List[str],
        default_option: Optional[str],
        timeout: int
    ) -> None:
        """
        Thread function to handle user input for a prompt.
        
        Args:
            prompt_id: ID of the prompt
            formatted_question: Formatted question to display
            options: Valid response options
            default_option: Default option
            timeout: Timeout in seconds
        """
        print(formatted_question, end="", file=sys.stderr)
        sys.stderr.flush()
        
        result = default_option
        
        try:
            # Use select to implement timeout on Unix systems
            if os.name == "posix":
                import select
                
                # Check if input is available
                i, o, e = select.select([sys.stdin], [], [], timeout)
                
                if i:
                    # Input is available
                    user_input = sys.stdin.readline().strip().lower()
                    
                    if user_input in options:
                        result = user_input
                    elif user_input == "" and default_option:
                        result = default_option
            else:
                # Fallback for non-Unix systems
                user_input = input().strip().lower()
                
                if user_input in options:
                    result = user_input
                elif user_input == "" and default_option:
                    result = default_option
                
        except (KeyboardInterrupt, EOFError):
            # User cancelled, use default
            pass
        except Exception as e:
            self._logger.error(f"Error in input thread: {str(e)}")
        
        # Set the result in the future
        if prompt_id in self._active_prompts:
            future = self._active_prompts[prompt_id]["result"]
            if not future.done():
                asyncio.run(self._set_future_result(future, result))
    
    async def _clear_message_after_timeout(self, message: str, timeout: float) -> None:
        """
        Clear a message after a timeout.
        
        Args:
            message: The message to clear
            timeout: Timeout in seconds
        """
        await asyncio.sleep(timeout)
        
        # In a real implementation, you would need to handle terminal 
        # control sequences to actually clear the message
        # This is a simplified version that just logs the intent
        self._logger.debug(f"Would clear message after timeout: {message}")
    
    def _get_next_prompt_id(self) -> int:
        """
        Get the next prompt ID.
        
        Returns:
            A unique prompt ID
        """
        self._prompt_id_counter += 1
        return self._prompt_id_counter

# Global instance
inline_feedback = InlineFeedback()
