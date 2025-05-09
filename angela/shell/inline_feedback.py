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
        self._active_messages = {}  # Track messages that might need to be cleared
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def _ensure_loop(self) -> bool:
        """Ensures self.loop is set to the current running asyncio event loop."""
        if self.loop is None:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self._logger.error("InlineFeedback: Could not get running asyncio event loop. Threaded operations might fail.")
                return False
        return True

    def _set_future_result_threadsafe(self, future: asyncio.Future, result: Any) -> None:
        """Synchronous method to set future result, intended for call_soon_threadsafe."""
        if self.loop and not future.done(): # Check loop just in case, though call_soon_threadsafe needs it
            self.loop.call_soon_threadsafe(future.set_result, result)
        elif not future.done(): # Fallback if loop somehow not set, though this path is less ideal
            future.set_result(result)


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
        current_time = time.time()
        if current_time - self._last_message_time < self._message_cooldown:
            self._logger.debug(f"Skipping message due to cooldown: {message}")
            return
        
        self._last_message_time = current_time
        
        color_code = {
            "info": "\033[34m",
            "warning": "\033[33m",
            "error": "\033[31m",
            "success": "\033[32m",
        }.get(message_type, "\033[34m")
        
        reset_code = "\033[0m"
        formatted_message = f"\n{color_code}[Angela] {message}{reset_code}"
        message_id = str(time.time())
        self._active_messages[message_id] = formatted_message
        
        print(formatted_message, file=sys.stderr)
        
        if timeout > 0:
            asyncio.create_task(self._clear_message_after_timeout(message_id, timeout))
    
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
        """
        if not await self._ensure_loop() or not self.loop:
            self._logger.error("Cannot ask question: Event loop not available.")
            return default_option or "" # Fallback

        prompt_id = self._get_next_prompt_id()
        options_display = "/".join(options)
        if default_option and default_option in options:
            options_display = options_display.replace(default_option, f"[{default_option}]")
        
        formatted_question = f"\n\033[35m[Angela] {question} ({options_display})\033[0m "
        
        result_future = self.loop.create_future()
        self._active_prompts[prompt_id] = {
            "question": question,
            "options": options,
            "default": default_option,
            "result": result_future,
            "formatted_question": formatted_question
        }
        
        thread = threading.Thread(
            target=self._input_thread,
            args=(prompt_id, formatted_question, options, default_option, timeout, result_future)
        )
        thread.daemon = True
        thread.start()
        self._active_threads[prompt_id] = thread
        
        try:
            result = await asyncio.wait_for(result_future, timeout=timeout + 5) # Add buffer for thread ops
            if callback and result is not None: # Ensure result is not None before callback
                await callback(result)
            return result if result is not None else default_option or ""
        except asyncio.TimeoutError:
            self._logger.warning(f"Question timed out: {question}")
            if not result_future.done():
                 self._set_future_result_threadsafe(result_future, default_option) # Ensure future is resolved
            return default_option or ""
        finally:
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
        """
        confidence_stars = int(confidence * 5)
        confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
        message = (
            f"I suggest this command: \033[1m{command}\033[0m\n"
            f"Confidence: {confidence_display} ({confidence:.2f})\n"
            f"{explanation}\n"
            f"Execute? (y/n/e - where 'e' will edit before executing)"
        )
        
        response = await self.ask_question(message, ["y", "n", "e"], default_option="n", timeout=30)
        
        if response == "y":
            if execute_callback:
                await execute_callback()
            return True
        elif response == "e":
            edited_command = await self._get_edited_command(command)
            if edited_command and execute_callback:
                session_manager.add_entity("edited_command", "command", edited_command)
                await execute_callback()
                return True
        return False
    
    async def _get_edited_command(self, original_command: str) -> Optional[str]:
        """
        Allow the user to edit a command.
        """
        if not await self._ensure_loop() or not self.loop:
            self._logger.error("Cannot edit command: Event loop not available.")
            return None # Fallback

        input_future = self.loop.create_future()

        try:
            from prompt_toolkit import prompt
            from prompt_toolkit.history import InMemoryHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            from prompt_toolkit.formatted_text import HTML
            from prompt_toolkit.key_binding import KeyBindings
            
            def get_prompt_toolkit_input():
                try:
                    kb = KeyBindings()
                    @kb.add('escape')
                    def _(event): event.app.exit(result=None)
                    
                    history = InMemoryHistory()
                    history.append_string(original_command)
                    
                    result = prompt(
                        HTML("<ansiblue>Edit the command: </ansiblue>"),
                        default=original_command, history=history,
                        auto_suggest=AutoSuggestFromHistory(), key_bindings=kb,
                        enable_history_search=True, enable_system_prompt=True,
                        enable_suspend=True, mouse_support=True
                    )
                    self._set_future_result_threadsafe(input_future, result)
                except (KeyboardInterrupt, EOFError):
                    self._set_future_result_threadsafe(input_future, None)
                except Exception as e_thread:
                    self._logger.error(f"Error in prompt_toolkit thread: {e_thread}")
                    self._set_future_result_threadsafe(input_future, None)

            thread = threading.Thread(target=get_prompt_toolkit_input)
            thread.daemon = True
            thread.start()
            
        except ImportError:
            self._logger.warning("prompt_toolkit not available, using basic input for command edit.")
            print(f"\n\033[36m[Angela] Edit the command (Ctrl+C to cancel):\033[0m", file=sys.stderr)
            print(f"\033[36m> \033[1m{original_command}\033[0m", file=sys.stderr)
            
            def get_basic_input():
                try:
                    user_input = input("\033[36m> \033[0m")
                    self._set_future_result_threadsafe(input_future, user_input)
                except (KeyboardInterrupt, EOFError):
                    self._set_future_result_threadsafe(input_future, None)
                except Exception as e_thread:
                    self._logger.error(f"Error in basic input thread: {e_thread}")
                    self._set_future_result_threadsafe(input_future, None)
            
            thread = threading.Thread(target=get_basic_input)
            thread.daemon = True
            thread.start()

        try:
            return await asyncio.wait_for(input_future, timeout=60)
        except asyncio.TimeoutError:
            print("\n\033[33m[Angela] Edit timed out\033[0m", file=sys.stderr)
            if not input_future.done():
                self._set_future_result_threadsafe(input_future, None) # Ensure future is resolved
            return None
        except Exception as e:
            self._logger.error(f"Error in command editor: {str(e)}")
            if not input_future.done():
                self._set_future_result_threadsafe(input_future, None)
            return None

    def _input_thread(
        self, 
        prompt_id: int,
        formatted_question: str,
        options: List[str],
        default_option: Optional[str],
        timeout: int,
        future: asyncio.Future # Pass the future directly
    ) -> None:
        """
        Thread function to handle user input for a prompt.
        """
        print(formatted_question, end="", file=sys.stderr)
        sys.stderr.flush()
        
        result = default_option
        
        try:
            if os.name == "posix":
                import select
                i, _, _ = select.select([sys.stdin], [], [], timeout)
                if i:
                    user_input = sys.stdin.readline().strip().lower()
                    if user_input in options: result = user_input
                    elif user_input == "" and default_option: result = default_option
            else: # Fallback for non-Unix (e.g. Windows)
                # Basic input() doesn't support timeout directly in a simple way here
                # This part remains a challenge for non-POSIX without more complex threading
                user_input = input().strip().lower()
                if user_input in options: result = user_input
                elif user_input == "" and default_option: result = default_option
        except (KeyboardInterrupt, EOFError):
            # User cancelled, result remains default_option or None if no default
            pass
        except Exception as e:
            self._logger.error(f"Error in input thread: {str(e)}")
        
        self._set_future_result_threadsafe(future, result)
    
    async def _clear_message_after_timeout(self, message_id: str, timeout: float) -> None:
        """
        Clear a message after a timeout.
        """
        await asyncio.sleep(timeout)
        if message_id not in self._active_messages: return
        message = self._active_messages[message_id]
        try:
            lines = message.count('\n') + 1
            up_sequence = f"\033[{lines}A"
            clear_sequence = "\033[K"
            clear_command = up_sequence
            for _ in range(lines):
                clear_command += clear_sequence + "\033[1B"
            clear_command += f"\033[{lines}A"
            sys.stderr.write(clear_command)
            sys.stderr.flush()
            del self._active_messages[message_id]
            self._logger.debug(f"Cleared message after timeout: {message_id}")
        except Exception as e:
            self._logger.error(f"Error clearing message: {str(e)}")
    
    def _get_next_prompt_id(self) -> int:
        """Get the next prompt ID."""
        self._prompt_id_counter += 1
        return self._prompt_id_counter

# Global instance
inline_feedback = InlineFeedback()
