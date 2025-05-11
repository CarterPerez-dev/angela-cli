# angela/shell/formatter.py
"""
Rich terminal formatting for Angela CLI.

This module provides enhanced terminal output formatting with
support for async operations and interactive elements.
"""
import asyncio
import sys
import time
from typing import Optional, List, Dict, Any, Callable, Awaitable, Tuple, Set
from enum import Enum
from pathlib import Path
import textwrap

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree
from rich.spinner import Spinner
from rich import box

from angela.api.intent import get_advanced_task_plan_class, get_plan_step_type_enum
from angela.utils.logging import get_logger
from angela.constants import RISK_LEVELS

# Get risk level names mapping for display
RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}

# Risk level color mapping
RISK_COLORS = {
    RISK_LEVELS["SAFE"]: "green",
    RISK_LEVELS["LOW"]: "blue", 
    RISK_LEVELS["MEDIUM"]: "yellow",
    RISK_LEVELS["HIGH"]: "bright_red",  
    RISK_LEVELS["CRITICAL"]: "red",
}

AdvancedTaskPlan = get_advanced_task_plan_class()
PlanStepType = get_plan_step_type_enum()

_console = Console(record=True, width=100)

logger = get_logger(__name__)

class OutputType(Enum):
    """Types of command output."""
    STDOUT = "stdout"
    STDERR = "stderr"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

class TerminalFormatter:
    """
    Rich terminal formatter with support for asynchronous output
    and interactive elements.
    """

    # Replace fun loading quotes with philosophical wisdom
    PHILOSOPHY_QUOTES = [
        # Aristotle quotes
        "We are what we repeatedly do. Excellence, then, is not an act, but a habit. - Aristotle",
        "The whole is greater than the sum of its parts. - Aristotle",
        "Knowing yourself is the beginning of all wisdom. - Aristotle",
        "It is the mark of an educated mind to be able to entertain a thought without accepting it. - Aristotle",
        "Happiness depends upon ourselves. - Aristotle",
        
        # Socrates quotes
        "The unexamined life is not worth living. - Socrates",
        "I know that I am intelligent, because I know that I know nothing. - Socrates",
        "The secret of change is to focus all of your energy not on fighting the old, but on building the new. - Socrates",
        "Be kind, for everyone you meet is fighting a hard battle. - Socrates",
        "Wonder is the beginning of wisdom. - Socrates",
        
        # Plato quotes
        "At the touch of love everyone becomes a poet. - Plato",
        "We can easily forgive a child who is afraid of the dark; the real tragedy of life is when men are afraid of the light. - Plato",
        "Be kind, for everyone you meet is fighting a harder battle. - Plato",
        "The measure of a man is what he does with power. - Plato",
        "Wise men speak because they have something to say; fools because they have to say something. - Plato",
        
        # Sun Tzu quotes
        "Appear weak when you are strong, and strong when you are weak. - Sun Tzu",
        "The supreme art of war is to subdue the enemy without fighting. - Sun Tzu",
        "Let your plans be dark and impenetrable as night, and when you move, fall like a thunderbolt. - Sun Tzu",
        "If you know the enemy and know yourself, you need not fear the result of a hundred battles. - Sun Tzu",
        "Victorious warriors win first and then go to war, while defeated warriors go to war first and then seek to win. - Sun Tzu",
        
        # Hypatia quotes
        "Reserve your right to think, for even to think wrongly is better than not to think at all. - Hypatia",
        "Life is an unfoldment, and the further we travel the more truth we can comprehend. - Hypatia",
        "To teach superstitions as truth is a most terrible thing. - Hypatia",
        "All formal dogmatic religions are fallacious and must never be accepted by self-respecting persons as final. - Hypatia",
        
        # Sextus Empiricus quotes
        "For every argument, there is a counter-argument of equal weight. - Sextus Empiricus",
        "The wise man suspends judgment; he recognizes that nothing is certain. - Sextus Empiricus",
        "Appearances are our only guide in life. - Sextus Empiricus",
        "The goal of the skeptic is tranquility of mind. - Sextus Empiricus",
        
        # Pythagoras quotes
        "The highest form of pure thought is in mathematics. - Pythagoras",
        "Number is the ruler of forms and ideas, and the cause of gods and demons. - Pythagoras",
        "Concern should drive us into action and not into a depression. - Pythagoras",
        "Above all things, reverence yourself. - Pythagoras",
        
        # Xenophanes quotes
        "If cattle and horses had hands, they would draw the forms of gods like cattle and horses. - Xenophanes",
        "There is one god, greatest among gods and men, similar to mortals neither in shape nor in thought. - Xenophanes",
        "The gods did not reveal all things to men at the start; but as time goes on, by searching, they discover more. - Xenophanes",
        "Men create the gods in their own image. - Xenophanes",
        
        # Additional philosophical quotes
        "The only true wisdom is in knowing you know nothing. - Socrates",
        "Man is the measure of all things. - Protagoras",
        "I think, therefore I am. - René Descartes",
        "He who has a why to live can bear almost any how. - Friedrich Nietzsche",
        "One cannot step twice in the same river. - Heraclitus",
        "The function of prayer is not to influence God, but rather to change the nature of the one who prays. - Søren Kierkegaard",
        "What is rational is actual and what is actual is rational. - G.W.F. Hegel"
    ]
    
    def __init__(self):
        """Initialize the terminal formatter."""
        self._console = Console()
        self._logger = logger
        self._active_displays = set()

    def _get_quantum_vortex_spinner(self, elapsed: float) -> Text:
        """Create a mesmerizing quantum vortex spinner animation."""
        import math
        spinner_text = Text()
        
        # Outer vortex ring with color cycling
        outer_symbols = ["◜", "◠", "◝", "◞", "◡", "◟"]
        outer_idx = int(elapsed * 6) % len(outer_symbols)
        outer_char = outer_symbols[outer_idx]
        
        # Color cycle through spectrum
        hue = int(elapsed * 36) % 360
        # Create RGB colors that cycle
        r = int(abs(math.sin(hue/60)) * 255)
        g = int(abs(math.sin((hue+120)/60)) * 255)
        b = int(abs(math.sin((hue+240)/60)) * 255)
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        
        # Inner particle with opposite rotation
        inner_symbols = ["•", "◦", "●", "○", "◎", "◉"]
        inner_idx = int(elapsed * 8) % len(inner_symbols)
        inner_idx_reverse = (len(inner_symbols) - 1 - inner_idx)  # Reverse direction
        inner_char = inner_symbols[inner_idx_reverse]
        
        # Pulsing effect for center particle
        pulse_size = 1 + 0.5 * math.sin(elapsed * 3)
        if pulse_size > 1.25:
            center_style = "bold bright_white"
        else:
            center_style = "dim white"
        
        # Assemble the spinner components
        spinner_text.append(f"[{color_hex}]{outer_char}[/{color_hex}]")
        spinner_text.append(f"[{center_style}]{inner_char}[/{center_style}]")
        
        # Quantum particle trails
        particle_pos = int(elapsed * 5) % 3
        trail = " " * particle_pos + "∴" + " " * (2 - particle_pos)
        spinner_text.append(f"[bright_cyan]{trail}[/bright_cyan]")
        
        return spinner_text
    
    def _get_elemental_cascade_spinner(self, elapsed: float) -> Text:
        """Create a spinner that cycles through elemental themes."""
        import math
        spinner_text = Text()
        
        # Determine current element based on time
        element_cycle = int(elapsed * 2) % 4  # Changes every 0.5 seconds
        
        # Element-specific animations
        if element_cycle == 0:  # Fire
            fire_symbols = ["🔥", "🔥", "🔥", "🔥", "💥", "✨", "🔥", "🔥"]
            fire_idx = int(elapsed * 12) % len(fire_symbols)
            
            # Flame intensity changes
            flame_chars = ["═", "╪", "╫", "╬", "╬", "╫", "╪"]
            flame_idx = int(elapsed * 14) % len(flame_chars)
            
            spinner_text.append(f"{fire_symbols[fire_idx]}")
            spinner_text.append(f"[bright_red]{flame_chars[flame_idx]}[/bright_red]")
            spinner_text.append("[yellow]~[/yellow]")
            
        elif element_cycle == 1:  # Water
            water_symbols = ["≈", "≋", "≈", "∽", "∿", "≈"]
            water_idx = int(elapsed * 12) % len(water_symbols)
            
            # Wave effect
            wave_level = int(2 + 2 * math.sin(elapsed * 6))
            waves = "~" * wave_level
            
            spinner_text.append(f"[bright_blue]{water_symbols[water_idx]}[/bright_blue]")
            spinner_text.append(f"[cyan]{waves}[/cyan]")
            spinner_text.append("[blue]○[/blue]")
            
        elif element_cycle == 2:  # Earth
            earth_symbols = ["◦", "•", "●", "◎", "◉", "⦿", "◉", "◎", "●", "•"]
            earth_idx = int(elapsed * 10) % len(earth_symbols)
            
            # Growth effect
            growth = [".", "․", "‥", "…", "⁘", "⁙"]
            growth_idx = int(elapsed * 6) % len(growth)
            
            spinner_text.append(f"[green]{earth_symbols[earth_idx]}[/green]")
            spinner_text.append(f"[dark_green]{growth[growth_idx]}[/dark_green]")
            spinner_text.append("[bright_green]⏣[/bright_green]")
            
        else:  # Air
            air_symbols = ["≋", "≈", "≋", "≈", "≋", "≈"]
            air_idx = int(elapsed * 8) % len(air_symbols)
            
            # Wind effect
            wind_dir = int(elapsed * 4) % 2
            if wind_dir == 0:
                wind = "»»»"
            else:
                wind = "«««"
                
            spinner_text.append(f"[white]{air_symbols[air_idx]}[/white]")
            spinner_text.append(f"[bright_white]{wind}[/bright_white]")
            spinner_text.append("[bright_cyan]◌[/bright_cyan]")
        
        return spinner_text
    
    def _get_interstellar_warp_spinner(self, elapsed: float) -> Text:
        """Create a mind-blowing warp drive animation effect."""
        import math
        spinner_text = Text()
        
        # Warp ship core with pulsing energy
        energy_level = int(3 + 3 * math.sin(elapsed * 8))
        core_symbols = ["▮", "▰", "█", "▰", "▮", "▯", "▮", "▰", "█"]
        core_idx = int(elapsed * 12) % len(core_symbols)
        core_char = core_symbols[core_idx]
        
        # Warp field effect with varying lengths based on warp speed
        warp_factor = 1 + int(elapsed * 10) % 9  # Warp factors 1-9
        warp_speed = min(4, int(1 + warp_factor/2))  # Max length of 4
        
        # Center of animation
        spinner_text.append("[bright_blue]=[/bright_blue]")
        spinner_text.append(f"[bright_yellow]{core_char * energy_level}[/bright_yellow]")
        spinner_text.append("[bright_blue]=[/bright_blue]")
        
        # Starfield effect - stars zooming past at different speeds
        star_positions = []
        for i in range(5):  # Generate 5 stars
            # Each star moves at different speeds
            pos = (elapsed * (5 + i)) % 15
            intensity = min(1.0, 15 - pos) / 1.0  # Fade based on position
            
            if intensity > 0.7:
                style = "bright_white"
            elif intensity > 0.4:
                style = "white"
            else:
                style = "dim white"
                
            # Convert position to integer for display
            pos_int = int(pos)
            
            # Star character depends on position (moving away = smaller)
            if pos_int < 3:
                star = "*"
            elif pos_int < 7:
                star = "·"
            else:
                star = "."
                
            # Add to positions list
            star_positions.append((pos_int, star, style))
        
        # Sort stars by position for layering
        star_positions.sort()
        
        # Create starfield
        starfield = [""] * 15  # Initialize empty spaces
        for pos, star, style in star_positions:
            if 0 <= pos < 15:  # Ensure within bounds
                starfield[pos] = f"[{style}]{star}[/{style}]"
        
        # Add leading stars
        for i in range(warp_speed):
            starfield_segment = "".join(starfield[i*3:(i+1)*3])
            if starfield_segment.strip():  # Only add if there's visible content
                spinner_text.append(starfield_segment)
        
        # Add warp drive energy fluctuation
        fluctuation = int(elapsed * 20) % 3
        if fluctuation == 0:
            spinner_text.append("[bright_cyan]⚡[/bright_cyan]")
        elif fluctuation == 1:
            spinner_text.append("[bright_magenta]⚡[/bright_magenta]")
        else:
            spinner_text.append("[bright_yellow]⚡[/bright_yellow]")
        
        return spinner_text
    
    def _get_random_spinner(self, elapsed: float) -> Text:
        """Get a random spinner based on object ID determinism."""
        # Use a hash of the current time's integer part to select a spinner
        # This ensures the same spinner is used throughout a single load operation
        import random
        import hashlib
        
        # We'll use the hash of the elapsed time's integer part to select a spinner,
        # but only hash it once at the beginning of a loading session
        if not hasattr(self, '_current_spinner_choice'):
            # Initialize a random spinner for this loading session
            self._current_spinner_choice = random.randint(1, 3)
            self._logger.debug(f"Selected spinner animation: {self._current_spinner_choice}")
        
        # Use the selected spinner
        if self._current_spinner_choice == 1:
            return self._get_quantum_vortex_spinner(elapsed)
        elif self._current_spinner_choice == 2:
            return self._get_elemental_cascade_spinner(elapsed)
        else:
            return self._get_interstellar_warp_spinner(elapsed)









    
    def print_command(self, command: str, title: Optional[str] = None) -> None:
        """
        Display a command with syntax highlighting.
        
        Args:
            command: The command to display
            title: Optional title for the panel
        """
        title = title or "Command"
        syntax = Syntax(command, "bash", theme="monokai", word_wrap=True)
        self._console.print(Panel(syntax, title=title, expand=False))
    
    def print_output(
        self, 
        output: str, 
        output_type: OutputType = OutputType.STDOUT,
        title: Optional[str] = None
    ) -> None:
        """
        Display command output with appropriate formatting.
        
        Args:
            output: The output text
            output_type: Type of output
            title: Optional title for the panel
        """
        if not output:
            return
            
        # Set styling based on output type
        if output_type == OutputType.STDERR or output_type == OutputType.ERROR:
            style = "bold red"
            title = title or "Error"
            border_style = "red"
        elif output_type == OutputType.WARNING:
            style = "yellow"
            title = title or "Warning"
            border_style = "yellow"
        elif output_type == OutputType.SUCCESS:
            style = "green"
            title = title or "Success"
            border_style = "green"
        elif output_type == OutputType.INFO:
            style = "blue"
            title = title or "Info"
            border_style = "blue"
        else:  # Default for STDOUT
            style = "white"
            title = title or "Output"
            border_style = "white"
        
        # Create panel with output
        panel = Panel(output, title=title, border_style=border_style, expand=False)
        self._console.print(panel)
    
    def print_error_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display error analysis with fix suggestions.
        
        Args:
            analysis: The error analysis dictionary
        """
        # Create a table for the error analysis
        table = Table(title="Error Analysis", expand=False)
        table.add_column("Aspect", style="bold cyan")
        table.add_column("Details", style="white")
        
        # Add error summary
        table.add_row("Error", Text(analysis.get("error_summary", "Unknown error"), style="bold red"))
        
        # Add possible cause
        table.add_row("Possible Cause", analysis.get("possible_cause", "Unknown"))
        
        # Add command issues
        if analysis.get("command_issues"):
            issues = "\n".join(f"• {issue}" for issue in analysis["command_issues"])
            table.add_row("Command Issues", issues)
        
        # Add file issues
        if analysis.get("file_issues"):
            file_issues = []
            for issue in analysis["file_issues"]:
                path = issue.get("path", "unknown")
                if "suggestion" in issue:
                    file_issues.append(f"• {path}: {issue['suggestion']}")
                if "similar_files" in issue:
                    similar = ", ".join(issue["similar_files"])
                    file_issues.append(f"  Did you mean: {similar}?")
            
            if file_issues:
                table.add_row("File Issues", "\n".join(file_issues))
        
        # Display the table
        self._console.print(table)
        
        # Display fix suggestions if available
        if analysis.get("fix_suggestions"):
            suggestions = analysis["fix_suggestions"]
            if suggestions:
                self._console.print(Panel(
                    "\n".join(f"• {suggestion}" for suggestion in suggestions),
                    title="Fix Suggestions",
                    border_style="green",
                    expand=False
                ))
    

    async def stream_output(
        self,
        command: str,
        show_spinner: bool = True,
        show_output: bool = True,
        callback: Optional[Callable[[str, OutputType], Awaitable[None]]] = None
    ) -> Tuple[str, str, int]:
        """
        Stream command output asynchronously with rich formatting.
        
        Args:
            command: The command to execute
            show_spinner: Whether to show a spinner
            show_output: Whether to display output
            callback: Optional callback for when output is received
            
        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        # Import here to avoid circular imports
        from angela.execution.engine import execution_engine
        import random
        import time
        
        stdout_chunks = []
        stderr_chunks = []
        return_code = None
        start_time = time.time()
        
        # Choose a random philosophy quote
        quote = random.choice(self.PHILOSOPHY_QUOTES)
        
        # Set up progress display if requested
        if show_spinner:
            progress = Progress(
                SpinnerColumn(),
                TextColumn(f"[bold blue]{quote} [/bold blue]"),
                TimeElapsedColumn(),
                console=self._console
            )
        else:
            progress = None
        
        try:
            # Start progress if requested
            if progress:
                progress.start()
                task = progress.add_task("Executing", total=None)
            
            # Create the process
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Set up tasks to read output
            async def read_stream(stream, output_type: OutputType):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                        
                    try:
                        line_str = line.decode('utf-8', errors='replace')
                        
                        # Store the output
                        if output_type == OutputType.STDOUT:
                            stdout_chunks.append(line_str)
                        else:
                            stderr_chunks.append(line_str)
                        
                        # Display if requested
                        if show_output:
                            if output_type == OutputType.STDOUT:
                                self._console.print(line_str, end="")
                            else:
                                self._console.print(f"[bold red]{line_str}[/bold red]", end="")
                        
                        # Call callback if provided
                        if callback:
                            await callback(line_str, output_type)
                            
                    except Exception as e:
                        self._logger.error(f"Error processing output: {str(e)}")
            
            # Create tasks for stdout and stderr
            stdout_task = asyncio.create_task(read_stream(proc.stdout, OutputType.STDOUT))
            stderr_task = asyncio.create_task(read_stream(proc.stderr, OutputType.STDERR))
            
            # Wait for the process to complete
            return_code = await proc.wait()
            
            # Wait for the streams to complete
            await stdout_task
            await stderr_task
            
            # Update progress
            if progress:
                end_time = time.time()
                execution_time = end_time - start_time
                progress.update(task, description=f"[bold green]Completed in {execution_time:.2f}s[/bold green]", completed=True)
                # Give a short pause to show completion time
                await asyncio.sleep(0.5)
        
        finally:
            # Clean up progress
            if progress:
                progress.stop()
        
        # Return the collected output
        return "".join(stdout_chunks), "".join(stderr_chunks), return_code
 



   
    async def display_pre_confirmation_info(
        self,
        command: str,
        risk_level: int,
        risk_reason: str,
        impact: Dict[str, Any],
        explanation: Optional[str] = None,
        preview: Optional[str] = None,
        confidence_score: Optional[float] = None,
        execution_time: Optional[float] = None
    ) -> None:
        """
        Display a comprehensive pre-confirmation information block.
        
        Args:
            command: The command to be executed
            risk_level: Risk level (0-4)
            risk_reason: Reason for the risk assessment
            impact: Impact analysis dictionary
            explanation: Optional explanation of the command
            preview: Optional preview of command execution
            confidence_score: Optional AI confidence score (0-1)
            execution_time: Optional execution time if this is post-execution
        """
        from rich import box
        
        # Get console width to ensure proper text wrapping
        console_width = self._console.width
        max_text_width = min(console_width - 10, 80)  # Leave some margin
        
        # Risk level styling
        risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
        risk_color = RISK_COLORS.get(risk_level, "yellow")
        
        # 1. Command panel with risk level in title
        self._console.print(Panel(
            Syntax(command, "bash", theme="monokai", word_wrap=True),
            title=f"Execute [{risk_name} Risk]",
            border_style=risk_color,
            box=box.ROUNDED,
            expand=False
        ))
        
        # Add spacing
        self._console.print("")
        
        # 2. Explanation panel if provided
        if explanation:
            # Ensure explanation doesn't get cut off
            wrapped_explanation = textwrap.fill(explanation, width=max_text_width)
            
            self._console.print(Panel(
                wrapped_explanation,
                title="Explanation",
                border_style="blue",
                box=box.ROUNDED,
                expand=False
            ))
            
            # Add spacing
            self._console.print("")
        
        # 3. Confidence score if available
        if confidence_score is not None:
            confidence_color = "green" if confidence_score > 0.8 else "yellow" if confidence_score > 0.6 else "red"
            confidence_stars = int(confidence_score * 5)
            confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
            
            self._console.print(Panel(
                f"[bold]Confidence Score:[/bold] [{confidence_color}]{confidence_score:.2f}[/{confidence_color}] {confidence_display}\n"
                "[dim](Confidence indicates how sure Angela is that this command matches your request)[/dim]",
                title="AI Confidence",
                border_style=confidence_color,
                box=box.ROUNDED,
                expand=False
            ))
            
            # Add spacing
            self._console.print("")
        
        # 4. Risk assessment panel
        risk_info = f"[bold {risk_color}]Risk Level:[/bold {risk_color}] {risk_name}\n"
        risk_info += f"[bold {risk_color}]Reason:[/bold {risk_color}] {risk_reason}"
        
        self._console.print(Panel(
            risk_info,
            title="Risk Assessment",
            border_style=risk_color,
            box=box.ROUNDED,
            expand=False
        ))
        
        # Add spacing
        self._console.print("")
        
        # 5. Preview panel if available
        if preview:
            # Ensure preview is properly formatted
            self._console.print(Panel(
                preview,
                title="Command Preview",
                border_style="blue",
                box=box.ROUNDED,
                expand=False
            ))
            
            # Add spacing
            self._console.print("")
        
        # 6. Warning for critical operations
        if risk_level >= 4:  # CRITICAL
            self._console.print(Panel(
                "⚠️  [bold red]This is a CRITICAL risk operation[/bold red] ⚠️\n"
                "It may cause significant changes to your system or data loss.",
                border_style="red",
                box=box.ROUNDED,
                expand=False
            ))
            
            # Add spacing
            self._console.print("")

    async def display_inline_confirmation(
        self,
        prompt_text: str = "Proceed with execution?"
    ) -> bool:
        """
        Display an inline confirmation prompt and get user input.
        
        Args:
            prompt_text: The confirmation prompt text
            
        Returns:
            True if confirmed, False otherwise
        """
        # Create a fancy confirmation prompt
        from rich import box
        from rich.panel import Panel
        from rich.text import Text
        
        prompt_panel = Text(prompt_text)
        prompt_panel.append(" (", style="cyan")
        prompt_panel.append("y", style="green")
        prompt_panel.append("/", style="cyan")
        prompt_panel.append("n", style="red")
        prompt_panel.append(")", style="cyan")
        
        self._console.print(Panel(
            prompt_panel,
            box=box.ROUNDED,
            border_style="cyan",
            expand=False
        ))
        
        # Get the user's response
        self._console.print(">>> ", end="", style="red")
        response = input().strip().lower()
        
        # Consider empty response or y/yes as "yes"
        if not response or response in ("y", "yes"):
            return True
        
        # Everything else is "no"
        return False

    async def display_execution_timer(
        self,
        command: str,
        with_philosophy: bool = True
    ) -> Tuple[str, str, int, float]:
        """
        Display a command execution timer with philosophy quotes.
        
        Args:
            command: The command being executed
            with_philosophy: Whether to display philosophy quotes
            
        Returns:
            Tuple of (stdout, stderr, return_code, execution_time)
        """
        import random
        import time
        import math  # For advanced effects
        import asyncio
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Group
        from rich import box
        
        # Ensure no active live displays
        self._ensure_no_active_live()
        
        # Reset spinner choice for new execution session
        if hasattr(self, '_current_spinner_choice'):
            delattr(self, '_current_spinner_choice')
        
        start_time = time.time()
        
        # Choose a random philosophy quote
        quote = random.choice(self.PHILOSOPHY_QUOTES) if with_philosophy else ""
        
        # Create a layout for execution display
        def get_layout():
            elapsed = time.time() - start_time
            
            # Get a random but consistent spinner for this execution session
            spinner = self._get_random_spinner(elapsed)
            
            # Add execution message
            spinner_with_text = Text()
            spinner_with_text.append_text(spinner)
            spinner_with_text.append(f" [bold]{elapsed:.2f}s[/bold]")
            spinner_with_text.append(" - Executing command...")
            
            if with_philosophy:
                # For the philosophy quote
                quote_text = Text(quote, style="italic cyan")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            panel = Panel(
                content,
                title="Command Execution",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            
            return panel
        
        # Use asyncio.create_subprocess_shell to execute the command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Collect output
        stdout_chunks = []
        stderr_chunks = []
        
        # Set up tasks to read output
        async def read_stream(stream, is_stdout: bool):
            while True:
                line = await stream.readline()
                if not line:
                    break
                    
                try:
                    line_str = line.decode('utf-8', errors='replace')
                    
                    # Store the output
                    if is_stdout:
                        stdout_chunks.append(line_str)
                    else:
                        stderr_chunks.append(line_str)
                        
                except Exception as e:
                    self._logger.error(f"Error processing output: {str(e)}")
        
        # Create tasks for stdout and stderr
        stdout_task = asyncio.create_task(read_stream(process.stdout, True))
        stderr_task = asyncio.create_task(read_stream(process.stderr, False))
        
        # Display the live progress
        try:
            with Live(get_layout(), refresh_per_second=20, console=self._console) as live:
                # Wait for the command to complete while updating the display
                return_code = await process.wait()
                
                # Wait for the streams to complete
                await stdout_task
                await stderr_task
                
                # Update once more when done
                execution_time = time.time() - start_time
                live.update(
                    Panel(
                        Text(f"Completed in {execution_time:.2f}s", style="bold green"),
                        title="Process Complete",
                        border_style="green",
                        box=box.ROUNDED,
                        expand=False
                    )
                )
                
                # Brief pause to show completion
                await asyncio.sleep(0.5)
        except Exception as e:
            self._logger.error(f"Error in execution timer: {str(e)}")
            # Ensure we still wait for the process
            if process.returncode is None:
                return_code = await process.wait()
            else:
                return_code = process.returncode
            
            # Wait for the streams to complete
            await stdout_task
            await stderr_task
            
            execution_time = time.time() - start_time
        
        # Return the results
        return (
            "".join(stdout_chunks),
            "".join(stderr_chunks),
            return_code,
            execution_time
        )
        
    async def display_loading_timer(
        self,
        message: str,
        with_philosophy: bool = True
    ) -> None:
        """
        Display a loading timer with optional philosophy quotes.
        
        Args:
            message: The loading message to display
            with_philosophy: Whether to display philosophy quotes
        """
        import random
        import time
        import math  
        import asyncio
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Group
        from rich import box
        
        # Ensure no active live displays
        self._ensure_no_active_live()
        
        # Reset spinner choice for new loading session
        if hasattr(self, '_current_spinner_choice'):
            delattr(self, '_current_spinner_choice')
        
        start_time = time.time()
        
        # Choose a random philosophy quote
        quote = random.choice(self.PHILOSOPHY_QUOTES) if with_philosophy else ""
        
        # Create a layout function that properly handles the spinner
        def get_layout():
            elapsed = time.time() - start_time
            
            # Get a random but consistent spinner for this loading session
            spinner = self._get_random_spinner(elapsed)
            
            # Add timer and message to the spinner
            spinner_with_text = Text()
            spinner_with_text.append_text(spinner)
            spinner_with_text.append(f" [bold]{elapsed:.2f}s[/bold]")
            spinner_with_text.append(f" - {message}")
            
            if with_philosophy:
                # For the philosophy quote
                quote_text = Text(quote, style="italic cyan")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            panel = Panel(
                content,
                title="Angela is thinking...",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            
            return panel
        
        # Use try-except with asyncio.sleep to make it cancellable
        try:
            with Live(get_layout(), refresh_per_second=20, console=self._console) as live:
                try:
                    while True:
                        await asyncio.sleep(0.03)  # Smaller sleep for smoother animation
                        live.update(get_layout())
                except asyncio.CancelledError:
                    # Handle cancellation gracefully
                    self._logger.debug("Loading display cancelled")
                    raise  # Re-raise to ensure proper cleanup
        except asyncio.CancelledError:
            # Expected when cancelled from outside
            pass
        except Exception as e:
            self._logger.error(f"Error displaying loading timer: {str(e)}")

    
    def _ensure_no_active_live(self):
        """Ensure no active Live displays by checking and resetting console state."""
        # Access the internal console state to check if it has an active Live
        if hasattr(self._console, "_live") and self._console._live:
            self._logger.warning("Detected active Live display. Attempting cleanup.")
            # Try to gracefully close any existing live display
            try:
                try:
                    # First try to stop it properly
                    self._console._live.stop()
                except Exception:
                    # If that fails, just set it to None
                    pass
                self._console._live = None
                # Reset other potentially problematic console state
                if hasattr(self._console, "_buffer"):
                    self._console._buffer = []
            except Exception as e:
                self._logger.error(f"Error cleaning up console state: {str(e)}")
            
    def create_table(
        self, 
        title: str, 
        columns: List[Tuple[str, Optional[str]]]
    ) -> Table:
        """
        Create a rich table.
        
        Args:
            title: The table title
            columns: List of (column_name, style) tuples
            
        Returns:
            A Rich Table object
        """
        table = Table(title=title, expand=False)
        
        for name, style in columns:
            table.add_column(name, style=style)
            
        return table
    
    async def display_task_plan(self, plan: Any) -> None:
        """
        Display a task plan with rich interactive visualization.
        
        Args:
            plan: The task plan to display
        """
        # Create a table for the plan steps
        table = Table(title=f"Plan for: {plan.goal}", box=box.ROUNDED)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Command", style="green")
        table.add_column("Explanation", style="white")
        table.add_column("Risk", style="yellow", no_wrap=True)
        table.add_column("Dependencies", style="magenta", no_wrap=True)
        
        # Risk level names
        risk_names = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_styles = ["green", "blue", "yellow", "red", "bold red"]
        
        # Add steps to the table
        for i, step in enumerate(plan.steps):
            risk_idx = step.estimated_risk if 0 <= step.estimated_risk < len(risk_names) else 0
            risk_name = risk_names[risk_idx]
            risk_style = risk_styles[risk_idx]
            
            # Format dependencies
            deps = ", ".join([str(d+1) for d in step.dependencies]) if step.dependencies else "None"
            
            # Create syntax object
            syntax = Syntax(step.command, "bash", theme="monokai", word_wrap=True)
            
            # Render to string instead of using .markup
            _console.record = True
            _console.print(syntax)
            syntax_str = _console.export_text(styles=True)
            _console.record = False
            
            table.add_row(
                str(i + 1),
                syntax_str,
                step.explanation,
                f"[{risk_style}]{risk_name}[/{risk_style}]",
                deps
            )
        
        # Display the table
        self._console.print("\n")
        self._console.print(Panel(
            "I've created a plan to accomplish your goal. Here are the steps I'll take:",
            title="Task Plan",
            border_style="blue",
            expand=False
        ))
        self._console.print(table)
        
        # Create a dependency visualization if there are non-trivial dependencies
        has_dependencies = any(step.dependencies for step in plan.steps)
        if has_dependencies:
            await self._display_dependency_graph(plan)
            


    def print_suggestion(self, suggestion: Dict[str, Any], with_confidence: bool = True) -> None:
        """
        Print a command suggestion with rich formatting.
        
        Args:
            suggestion: The command suggestion
            with_confidence: Whether to show confidence score
        """
        self._console.print("\n")
        
        # Extract suggestion components
        command = suggestion.get("command", "")
        explanation = suggestion.get("explanation", "")
        confidence = suggestion.get("confidence", 0.0)
        
        # Display the command
        self.print_command(command)
        
        # Show confidence if requested
        if with_confidence:
            confidence_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.6 else "red"
            confidence_stars = int(confidence * 5)
            confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
            self._console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}] {confidence_display}")
        
        # Show explanation
        self._console.print("\n[bold]Explanation:[/bold]")
        self._console.print(explanation)
        
    def print_proactive_suggestion(self, suggestion: str, source: str = "AI") -> None:
        """
        Print a proactive suggestion.
        
        Args:
            suggestion: The suggestion text
            source: The source of the suggestion
        """
        self._console.print("\n")
        self._console.print(Panel(
            suggestion,
            title=f"Suggestion from {source}",
            border_style="green",
            expand=False
        ))
    
    async def _display_dependency_graph(self, plan: Any) -> None:
        """
        Display a visual representation of the dependency graph.
        
        Args:
            plan: The task plan with dependencies
        """
        # Create a dependency tree
        tree = Tree("Execution Flow", guide_style="bold blue")
        
        # Track processed steps
        processed = set()
        
        # Add steps with no dependencies first (roots)
        roots = []
        for i, step in enumerate(plan.steps):
            if not step.dependencies:
                roots.append(i)
                node = tree.add(f"Step {i+1}: {step.command[:30]}..." if len(step.command) > 30 else step.command)
                processed.add(i)
                
                # Add children recursively
                self._add_dependency_children(node, i, plan, processed)
        
        # Check if any steps were not processed (in case of circular dependencies)
        if len(processed) < len(plan.steps):
            for i, step in enumerate(plan.steps):
                if i not in processed:
                    node = tree.add(f"Step {i+1}: {step.command[:30]}..." if len(step.command) > 30 else step.command)
                    processed.add(i)
                    
                    # Add children recursively
                    self._add_dependency_children(node, i, plan, processed)
        
        # Display the tree
        self._console.print("\n[bold blue]Dependency Graph:[/bold blue]")
        self._console.print(tree)
    
    def _add_dependency_children(
        self, 
        parent_node: Any, 
        step_idx: int, 
        plan: Any, 
        processed: Set[int]
    ) -> None:
        """
        Recursively add children to a dependency node.
        
        Args:
            parent_node: The parent tree node
            step_idx: The index of the current step
            plan: The task plan
            processed: Set of already processed steps
        """
        # Find steps that depend on this one
        for i, step in enumerate(plan.steps):
            if step_idx in step.dependencies and i not in processed:
                node = parent_node.add(f"Step {i+1}: {step.command[:30]}..." 
                                       if len(step.command) > 30 else step.command)
                processed.add(i)
                
                # Recurse
                self._add_dependency_children(node, i, plan, processed)
    
    async def display_multi_step_execution(
        self, 
        plan: Any, 
        results: List[Dict[str, Any]]
    ) -> None:
        """
        Display the results of a multi-step execution.
        
        Args:
            plan: The task plan that was executed
            results: The execution results for each step
        """
        # Create a table for the execution results
        table = Table(title="Execution Results", box=box.ROUNDED)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Command", style="green")
        table.add_column("Status", style="white", no_wrap=True)
        table.add_column("Output", style="white")
        
        # Add results to the table
        for i, result in enumerate(results):
            # Get the command
            command = result.get("command", plan.steps[i].command if i < len(plan.steps) else "Unknown")
            
            # Get status
            status = "[green]Success[/green]" if result.get("success", False) else "[red]Failed[/red]"
            
            # Get output (combine stdout and stderr)
            stdout = result.get("stdout", "").strip()
            stderr = result.get("stderr", "").strip()
            
            # Truncate output if too long
            output = stdout
            if stderr:
                if output:
                    output += "\n"
                output += f"[red]{stderr}[/red]"
            
            if len(output) > 100:
                output = output[:97] + "..."
            
            table.add_row(
                str(i + 1),
                Syntax(command, "bash", theme="monokai", word_wrap=True).markup,
                status,
                output
            )
        
        # Display the table
        self._console.print("\n")
        self._console.print(Panel(
            "Execution results for your multi-step task:",
            title="Multi-Step Execution",
            border_style="blue"
        ))
        self._console.print(table)
        
        # Display summary
        success_count = sum(1 for r in results if r.get("success", False))
        total_count = len(results)
        
        if success_count == total_count:
            self._console.print(f"[bold green]All {total_count} steps completed successfully![/bold green]")
        else:
            self._console.print(f"[bold yellow]{success_count} of {total_count} steps completed successfully[/bold yellow]")
            
            # Show which steps failed
            failed_steps = [i+1 for i, r in enumerate(results) if not r.get("success", False)]
            if failed_steps:
                self._console.print(f"[bold red]Failed steps: {', '.join(map(str, failed_steps))}[/bold red]")
    
    async def display_workflow(self, workflow: Any, variables: Dict[str, Any] = None) -> None:
        """
        Display a workflow with rich formatting.
        
        Args:
            workflow: The workflow to display
            variables: Optional variables for the workflow
        """
        # Create a table for the workflow steps
        table = Table(title=f"Workflow: {workflow.name}", box=box.ROUNDED)
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Command", style="green")
        table.add_column("Explanation", style="white")
        table.add_column("Options", style="yellow")
        
        # Add steps to the table
        for i, step in enumerate(workflow.steps):
            # Apply variable substitution if variables provided
            command = step.command
            if variables:
                for var_name, var_value in variables.items():
                    # Remove leading $ if present
                    clean_name = var_name[1:] if var_name.startswith('$') else var_name
                    
                    # Substitute ${VAR} syntax
                    command = command.replace(f"${{{clean_name}}}", str(var_value))
                    
                    # Substitute $VAR syntax
                    command = command.replace(f"${clean_name}", str(var_value))
            
            options = []
            if step.optional:
                options.append("Optional")
            if step.requires_confirmation:
                options.append("Requires Confirmation")
            
            table.add_row(
                str(i + 1),
                Syntax(command, "bash", theme="monokai", word_wrap=True).markup,
                step.explanation,
                ", ".join(options) if options else ""
            )
        
        # Display the table
        self._console.print("\n")
        self._console.print(Panel(
            workflow.description,
            title=f"Workflow: {workflow.name}",
            border_style="blue"
        ))
        self._console.print(table)
        
        # Display variables if provided
        if variables:
            var_table = Table(title="Variables", box=box.SIMPLE)
            var_table.add_column("Name", style="cyan")
            var_table.add_column("Value", style="green")
            
            for var_name, var_value in variables.items():
                var_table.add_row(var_name, str(var_value))
            
            self._console.print(var_table)
    
    async def display_file_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display file content analysis results.
        
        Args:
            analysis: The analysis results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Analysis of {analysis.get('path', 'file')}",
            title="File Analysis",
            border_style="blue"
        ))
        
        # Display language and type info
        file_type = analysis.get("type", "unknown")
        language = analysis.get("language")
        
        if language:
            self._console.print(f"[bold]File type:[/bold] {file_type} ({language})")
        else:
            self._console.print(f"[bold]File type:[/bold] {file_type}")
        
        # Display the analysis text
        self._console.print("\n[bold]Analysis:[/bold]")
        self._console.print(analysis.get("analysis", "No analysis available"))
    
    async def display_file_manipulation(self, manipulation: Dict[str, Any]) -> None:
        """
        Display file manipulation results with diff.
        
        Args:
            manipulation: The manipulation results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Changes to {manipulation.get('path', 'file')}",
            title="File Manipulation",
            border_style="blue"
        ))
        
        # Display the instruction
        self._console.print(f"[bold]Instruction:[/bold] {manipulation.get('instruction', 'Unknown')}")
        
        # Display the diff
        self._console.print("\n[bold]Changes:[/bold]")
        syntax = Syntax(manipulation.get("diff", "No changes"), "diff", theme="monokai")
        self._console.print(syntax)
        
        # Show whether changes were applied
        if manipulation.get("changes_applied", False):
            self._console.print("[bold green]Changes have been applied to the file.[/bold green]")
        elif manipulation.get("dry_run", False):
            self._console.print("[bold blue]Dry run: Changes were not applied to the file.[/bold blue]")
        else:
            self._console.print("[bold yellow]Changes were not applied to the file.[/bold yellow]")
    
    async def display_file_search_results(self, search_results: Dict[str, Any]) -> None:
        """
        Display file search results.
        
        Args:
            search_results: The search results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Search results in {search_results.get('path', 'file')}",
            title="File Search",
            border_style="blue"
        ))
        
        # Display the query
        self._console.print(f"[bold]Query:[/bold] {search_results.get('query', 'Unknown')}")
        
        # Display match count
        match_count = search_results.get("match_count", 0)
        self._console.print(f"[bold]Found {match_count} matches[/bold]")
        
        # Display matches
        if match_count > 0:
            matches = search_results.get("matches", [])
            
            for i, match in enumerate(matches, 1):
                self._console.print(f"\n[bold cyan]Match #{i}[/bold cyan] (Lines {match.get('line_start', '?')}-{match.get('line_end', '?')})")
                
                # Display the content with context
                syntax = Syntax(match.get("content", ""), search_results.get("language", "text"), theme="monokai", line_numbers=True)
                self._console.print(syntax)
                
                # Display explanation
                if "explanation" in match:
                    self._console.print(f"[italic]{match['explanation']}[/italic]")


    def print_suggestion(self, suggestion: Dict[str, Any], with_confidence: bool = True) -> None:
        """
        Print a command suggestion with rich formatting.
        
        Args:
            suggestion: The command suggestion
            with_confidence: Whether to show confidence score
        """
        self._console.print("\n")
        
        # Extract suggestion components
        command = suggestion.get("command", "")
        explanation = suggestion.get("explanation", "")
        confidence = suggestion.get("confidence", 0.0)
        
        # Display the command
        self.print_command(command)
        
        # Show confidence if requested
        if with_confidence:
            confidence_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.6 else "red"
            self._console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}]")
        
        # Show explanation
        self._console.print("\n[bold]Explanation:[/bold]")
        self._console.print(explanation)
    
    def print_proactive_suggestion(self, suggestion: str, source: str = "AI") -> None:
        """
        Print a proactive suggestion.
        
        Args:
            suggestion: The suggestion text
            source: The source of the suggestion
        """
        self._console.print("\n")
        self._console.print(Panel(
            suggestion,
            title=f"Suggestion from {source}",
            border_style="green",
            expand=False
        ))


# Global formatter instance
terminal_formatter = TerminalFormatter()
