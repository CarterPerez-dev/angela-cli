import sys
import os
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
import time
import threading

from angela.utils.logging import get_logger
from angela.api.context import get_session_manager

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
    
    async def suggest_command(
        self, 
        command: str,
        explanation: str,
        confidence: float = 0.8,
        execute_callback: Optional[Callable[[], Awaitable[None]]] = None
    ) -> bool:
        """
        Suggest a command and offer to execute it with enhanced visuals.
        
        Args:
            command: The command to suggest
            explanation: Explanation of what the command does
            confidence: Confidence score for the suggestion
            execute_callback: Callback to execute the command
            
        Returns:
            True if command was executed, False otherwise
        """
        from angela.api.context import get_session_manager
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        
        console = Console()
        
        # Calculate visual confidence representation
        confidence_stars = int(confidence * 5)
        confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
        confidence_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.6 else "red"
        
        # Display command with rich formatting
        console.print(Panel(
            Syntax(command, "bash", theme="monokai", word_wrap=True),
            title="Suggested Command",
            border_style="blue",
            expand=False
        ))
        
        # Display confidence score
        console.print(Panel(
            f"[bold]Confidence Score:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}] {confidence_display}\n"
            "[dim](Confidence indicates how sure Angela is that this command matches your request)[/dim]",
            title="AI Confidence",
            border_style=confidence_color,
            expand=False
        ))
        
        # Display explanation
        console.print(Panel(
            explanation,
            title="Explanation",
            border_style="blue",
            expand=False
        ))
        
        # Create execution options
        console.print("[bold cyan]┌───────────────────────────────────────┐[/bold cyan]")
        console.print("[bold cyan]│[/bold cyan] Execute? ([green]y[/green]/[red]n[/red]/[yellow]e[/yellow] - where 'e' will edit) [bold cyan]│[/bold cyan]")
        console.print("[bold cyan]└───────────────────────────────────────┘[/bold cyan]")
        console.print("[bold cyan]▶[/bold cyan] ", end="")
        
        # Get user's response
        response = input().strip().lower()
        
        if response == "y" or response == "yes" or response == "":
            if execute_callback:
                await execute_callback()
            return True
        elif response == "e" or response == "edit":
            edited_command = await self._get_edited_command(command)
            if edited_command and execute_callback:
                get_session_manager().add_entity("edited_command", "command", edited_command)
                await execute_callback()
                return True
        return False
    
    async def _get_edited_command(self, original_command: str) -> Optional[str]:
        """
        Allow the user to edit a command with enhanced visual presentation.
        
        Args:
            original_command: The command to edit
            
        Returns:
            The edited command or None if cancelled
        """
        if not await self._ensure_loop() or not self.loop:
            self._logger.error("Cannot edit command: Event loop not available.")
            return None
    
        input_future = self.loop.create_future()
        
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        
        console = Console()
    
        try:
            # Try to use prompt_toolkit for a better editing experience
            from prompt_toolkit import prompt
            from prompt_toolkit.history import InMemoryHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            from prompt_toolkit.formatted_text import HTML
            from prompt_toolkit.key_binding import KeyBindings
            
            # Show editing instructions
            console.print(Panel(
                "Edit the command below.\n"
                "Press [bold]Enter[/bold] to confirm or [bold]Esc[/bold] to cancel.",
                title="Command Editor",
                border_style="cyan",
                expand=False
            ))
            
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
            # Fallback to basic input if prompt_toolkit is not available
            self._logger.warning("prompt_toolkit not available, using basic input for command edit.")
            
            # Display the original command
            console.print(Panel(
                Syntax(original_command, "bash", theme="monokai", word_wrap=True),
                title="Original Command",
                border_style="blue",
                expand=False
            ))
            
            console.print("[bold cyan]┌────────────────────────────────┐[/bold cyan]")
            console.print("[bold cyan]│[/bold cyan] [bold]Edit command:[/bold] [dim](Ctrl+C to cancel)[/dim] [bold cyan]│[/bold cyan]")
            console.print("[bold cyan]└────────────────────────────────┘[/bold cyan]")
            console.print("[bold cyan]▶[/bold cyan] ", end="")
            
            def get_basic_input():
                try:
                    user_input = input()
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
            edited_command = await asyncio.wait_for(input_future, timeout=60)
            
            # Display the edited command for confirmation
            if edited_command is not None and edited_command != original_command:
                console.print(Panel(
                    Syntax(edited_command, "bash", theme="monokai", word_wrap=True),
                    title="Edited Command",
                    border_style="green",
                    expand=False
                ))
                
            return edited_command
        except asyncio.TimeoutError:
            console.print("\n[yellow]Edit timed out[/yellow]")
            if not input_future.done():
                self._set_future_result_threadsafe(input_future, None)
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
        future: asyncio.Future
    ) -> None:
        """
        Thread function to handle user input for a prompt.
        
        Args:
            prompt_id: ID of the prompt
            formatted_question: Formatted question text
            options: Valid options
            default_option: Default option
            timeout: Timeout in seconds
            future: Future to set with the result
        """
        try:
            if os.name == "posix":
                import select
                i, _, _ = select.select([sys.stdin], [], [], timeout)
                if i:
                    user_input = sys.stdin.readline().strip().lower()
                    if user_input in options: 
                        result = user_input
                    elif user_input == "" and default_option: 
                        result = default_option
                    else:
                        result = default_option
                else:
                    # Timeout occurred
                    result = default_option
            else: 
                # Fallback for non-Unix (e.g. Windows)
                user_input = input().strip().lower()
                if user_input in options: 
                    result = user_input
                elif user_input == "" and default_option: 
                    result = default_option
                else:
                    result = default_option
        except (KeyboardInterrupt, EOFError):
            # User cancelled, result remains default_option or None if no default
            result = default_option
        except Exception as e:
            self._logger.error(f"Error in input thread: {str(e)}")
            result = default_option
        
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
