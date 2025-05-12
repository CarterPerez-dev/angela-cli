# angela/components/shell/formatter.py
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
import random

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
from rich.align import Align
from rich.style import Style
from rich.columns import Columns

from angela.api.intent import get_advanced_task_plan_class, get_plan_step_type_enum
from angela.utils.logging import get_logger
from angela.constants import RISK_LEVELS

# Get risk level names mapping for display
RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}

# ╔══ Vibrant Color Palette ══╗
COLORS = {
    # Reds (primary)
    "red": "#ff3366",          # Primary red
    "bright_red": "#ff0055",   # Brighter red for emphasis
    "dark_red": "#cc2255",     # Darker red for backgrounds
    
    # Purples (primary)
    "purple": "#9933ff",       # True purple (not magenta/pink)
    "bright_purple": "#aa55ff", # Brighter purple for highlights
    "dark_purple": "#7722cc",  # Darker purple for backgrounds
    
    # Blues
    "bright_blue": "#00aaff",  # Bright blue for text & highlights
    "blue": "#3366ff",         # Standard blue
    "dark_blue": "#0055cc",    # Dark blue for backgrounds
    
    # Cyans & Greens
    "cyan": "#00ddff",         # Cyan for accents
    "green": "#33cc77",        # Green for success
    "bright_green": "#00ff88", # Bright green for emphasis
    
    # Minimal use colors
    "yellow": "#ffcc33",       # Yellow (use sparingly)
    "white": "#ffffff",        # White (use very sparingly)
    
    # Gradient colors for special effects
    "gradient_1": "#ff3366",
    "gradient_2": "#ff3399", 
    "gradient_3": "#cc33ff",
    "gradient_4": "#9933ff",
    "gradient_5": "#6633ff",
    "gradient_6": "#3366ff",
}

# Risk level specific color scheme
RISK_COLORS = {
    RISK_LEVELS["SAFE"]: f"[{COLORS['green']}]SAFE[/{COLORS['green']}]",
    RISK_LEVELS["LOW"]: f"[{COLORS['cyan']}]LOW[/{COLORS['cyan']}]", 
    RISK_LEVELS["MEDIUM"]: f"[{COLORS['yellow']}]MEDIUM[/{COLORS['yellow']}]",
    RISK_LEVELS["HIGH"]: f"[{COLORS['bright_red']}]HIGH[/{COLORS['bright_red']}]",  
    RISK_LEVELS["CRITICAL"]: f"[{COLORS['red']} bold]CRITICAL[/{COLORS['red']} bold]",
}

# Box styles
BOX_STYLES = {
    "default": box.ROUNDED,
    "minimal": box.SIMPLE,
    "bold": box.DOUBLE,
    "ascii": box.ASCII
}

# Custom ASCII decorations
ASCII_DECORATIONS = {
    "command": "⚡",           # Lightning bolt for commands
    "output": "✓",            # Checkmark for output
    "error": "✗",             # X for errors
    "risk": "⚠",              # Warning for risk
    "confidence": "★",        # Star for confidence
    "info": "✧",              # Sparkle for info
    "preview": "⚡",           # Lightning for preview
    "confirmation": "◈",      # Diamond for confirmation
    "execution": "⟁",         # Double triangle for execution
    "success": "✓",           # Checkmark for success
    "warning": "⚠",           # Warning symbol
    "insight": "✧",           # Sparkle for insights
    "loading": "◉",           # Circle for loading
    "plan": "⬢",              # Hexagon for plans
    "file": "📄",             # File symbol
    "search": "🔍",           # Magnifying glass
    "cool_border": "╠══════╣", # Cool border
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
        spinner_text.append(outer_char, style=color_hex)
        spinner_text.append(inner_char, style=center_style)
        
        # Quantum particle trails
        particle_pos = int(elapsed * 5) % 3
        trail = " " * particle_pos + "∴" + " " * (2 - particle_pos)
        spinner_text.append(trail, style="bright_cyan")
        
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
            
            spinner_text.append(fire_symbols[fire_idx]) # Appending a plain character
            spinner_text.append(flame_chars[flame_idx], style="bright_red")
            spinner_text.append("~", style="yellow")
            
        elif element_cycle == 1:  # Water
            water_symbols = ["≈", "≋", "≈", "∽", "∿", "≈"]
            water_idx = int(elapsed * 12) % len(water_symbols)
            
            # Wave effect
            wave_level = int(2 + 2 * math.sin(elapsed * 6))
            waves = "~" * wave_level
            
            spinner_text.append(water_symbols[water_idx], style="bright_blue")
            spinner_text.append(waves, style="cyan")
            spinner_text.append("○", style="blue")
            
        elif element_cycle == 2:  # Earth
            earth_symbols = ["◦", "•", "●", "◎", "◉", "⦿", "◉", "◎", "●", "•"]
            earth_idx = int(elapsed * 10) % len(earth_symbols)
            
            # Growth effect
            growth = [".", "․", "‥", "…", "⁘", "⁙"]
            growth_idx = int(elapsed * 6) % len(growth)
            
            spinner_text.append(earth_symbols[earth_idx], style="green")
            spinner_text.append(growth[growth_idx], style="dark_green")
            spinner_text.append("⏣", style="bright_green")
            
        else:  # Air
            air_symbols = ["≋", "≈", "≋", "≈", "≋", "≈"]
            air_idx = int(elapsed * 8) % len(air_symbols)
            
            # Wind effect
            wind_dir = int(elapsed * 4) % 2
            if wind_dir == 0:
                wind = "»»»"
            else:
                wind = "«««"
                
            spinner_text.append(air_symbols[air_idx], style="white")
            spinner_text.append(wind, style="bright_white")
            spinner_text.append("◌", style="bright_cyan")
        
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
        spinner_text.append("=", style=f"[{COLORS['bright_blue']}]")
        spinner_text.append(core_char * energy_level, style=f"[{COLORS['bright_purple']}]")
        spinner_text.append("=", style=f"[{COLORS['bright_blue']}]")
        
        # Starfield effect - stars zooming past at different speeds
        star_positions = []
        for i in range(5):  # Generate 5 stars
            # Each star moves at different speeds
            pos = (elapsed * (5 + i)) % 15
            intensity = min(1.0, 15 - pos) / 1.0  # Fade based on position
            
            if intensity > 0.7:
                style = f"[{COLORS['white']}]"
            elif intensity > 0.4:
                style = f"[{COLORS['white']}]"
            else:
                style = f"[{COLORS['white']} dim]"
                
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
        starfield_markup_list = [""] * 15  # Initialize empty spaces with placeholder
        for pos, star, style in star_positions:
            if 0 <= pos < 15:  # Ensure within bounds
                # Store as markup string in the list
                starfield_markup_list[pos] = f"{style}{star}"
        
        # Add leading stars
        for i in range(warp_speed):
            # Join the markup strings from the list for the current segment
            starfield_segment = "".join(starfield_markup_list[i*3:(i+1)*3])
            if starfield_segment.strip():  # Only add if there's visible content
                spinner_text.append(starfield_segment)
        
        # Add warp drive energy fluctuation
        fluctuation = int(elapsed * 20) % 3
        if fluctuation == 0:
            spinner_text.append("⚡", style=f"[{COLORS['cyan']}]")
        elif fluctuation == 1:
            spinner_text.append("⚡", style=f"[{COLORS['bright_purple']}]")
        else:
            spinner_text.append("⚡", style=f"[{COLORS['yellow']}]")
        
        return spinner_text
    
    def _get_random_spinner(self, elapsed: float) -> Text:
        """Get a random spinner based on object ID determinism."""
        # Use a hash of the current time's integer part to select a spinner
        # This ensures the same spinner is used throughout a single load operation
        import random
        # No need to import hashlib here as it's not used in the provided logic
        
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

    def create_styled_text(self, text: str, rainbow: bool = False) -> Text:
        """
        Create styled text with optional rainbow effect.
        
        Args:
            text: The text to style
            rainbow: Whether to apply a rainbow gradient effect
            
        Returns:
            A styled Text object
        """
        if not rainbow:
            return Text(text)
            
        styled_text = Text()
        
        # Rainbow gradient colors
        gradient_colors = [
            COLORS["gradient_1"],
            COLORS["gradient_2"],
            COLORS["gradient_3"],
            COLORS["gradient_4"],
            COLORS["gradient_5"],
            COLORS["gradient_6"],
        ]
        
        # Calculate color index for each character
        for i, char in enumerate(text):
            color_idx = i % len(gradient_colors)
            styled_text.append(char, style=f"{gradient_colors[color_idx]}")
            
        return styled_text

    def print_command(self, command: str, title: Optional[str] = None) -> None:
        """
        Display a command with syntax highlighting.
        
        Args:
            command: The command to display
            title: Optional title for the panel
        """
        title = title or f"{ASCII_DECORATIONS['command']} Command {ASCII_DECORATIONS['command']}"
        
        # Create a syntax object with proper styling
        syntax = Syntax(
            command, 
            "bash", 
            theme="monokai", 
            word_wrap=True,
            background_color="default"
        )
        
        # Create a fancy panel with the syntax
        panel = Panel(
            syntax,
            title=title,
            title_align="center",
            border_style=COLORS["bright_purple"],
            box=BOX_STYLES["default"],
            padding=(0, 1)
        )
        
        self._console.print(panel)
    
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
            style = COLORS["bright_red"]
            title = title or f"{ASCII_DECORATIONS['error']} Error {ASCII_DECORATIONS['error']}"
            border_style = COLORS["red"]
        elif output_type == OutputType.WARNING:
            style = COLORS["yellow"]
            title = title or f"{ASCII_DECORATIONS['warning']} Warning {ASCII_DECORATIONS['warning']}"
            border_style = COLORS["yellow"]
        elif output_type == OutputType.SUCCESS:
            style = COLORS["green"]
            title = title or f"{ASCII_DECORATIONS['success']} Success {ASCII_DECORATIONS['success']}"
            border_style = COLORS["green"]
        elif output_type == OutputType.INFO:
            style = COLORS["bright_blue"]
            title = title or f"{ASCII_DECORATIONS['info']} Info {ASCII_DECORATIONS['info']}"
            border_style = COLORS["bright_blue"]
        else:  # Default for STDOUT
            style = COLORS["white"]
            title = title or f"{ASCII_DECORATIONS['output']} Output {ASCII_DECORATIONS['output']}"
            border_style = COLORS["bright_blue"]
        
        # Clean up the output - remove any trailing blank lines
        cleaned_output = output.rstrip()
        
        # Create panel with output, sized to content
        panel = Panel(
            cleaned_output,
            title=title,
            title_align="center",
            border_style=border_style,
            box=BOX_STYLES["default"],
            width=min(len(max(cleaned_output.split('\n'), key=len)) + 6, self._console.width - 4),
            padding=(0, 1)
        )
        
        self._console.print(panel)
    
    def print_error_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display error analysis with fix suggestions.
        
        Args:
            analysis: The error analysis dictionary
        """
        # Create a nice header
        error_title = Text()
        error_title.append(f"{ASCII_DECORATIONS['error']} ", style=COLORS["red"])
        error_title.append("ERROR ANALYSIS", style=f"{COLORS['bright_red']} bold")
        error_title.append(f" {ASCII_DECORATIONS['error']}", style=COLORS["red"])
        
        self._console.print(error_title, justify="center")
        
        # Create a table for the error analysis with vibrant colors
        table = Table(
            expand=False,
            box=BOX_STYLES["default"],
            border_style=COLORS["dark_red"],
            highlight=True,
            width=min(100, self._console.width - 4)
        )
        
        table.add_column("Aspect", style=f"{COLORS['bright_purple']} bold")
        table.add_column("Details", style=COLORS["bright_blue"])
        
        # Add error summary
        error_text = Text(analysis.get("error_summary", "Unknown error"), style=f"{COLORS['bright_red']} bold")
        table.add_row("Error", error_text)
        
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
                # Create a vibrant suggestions panel
                suggestion_text = []
                for i, suggestion in enumerate(suggestions, 1):
                    suggestion_text.append(f"[{COLORS['bright_green']}]•[/{COLORS['bright_green']}] {suggestion}")
                
                self._console.print(Panel(
                    "\n".join(suggestion_text),
                    title=f"{ASCII_DECORATIONS['success']} Fix Suggestions {ASCII_DECORATIONS['success']}",
                    title_align="center",
                    border_style=COLORS["green"],
                    box=BOX_STYLES["default"],
                    padding=(1, 2)
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
                TextColumn(f"[{COLORS['bright_purple']} bold]{quote} [{COLORS['bright_purple']} bold]"),
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
                                self._console.print(f"[{COLORS['bright_red']} bold]{line_str}[/{COLORS['bright_red']} bold]", end="")
                        
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
                progress.update(task, description=f"[{COLORS['bright_green']} bold]Completed in {execution_time:.2f}s[/{COLORS['bright_green']} bold]", completed=True)
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
        Display a comprehensive pre-confirmation information block with stunning visuals.
        
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
        # Get console width for proper layout
        console_width = self._console.width
        content_width = min(console_width, 100)
        
        # Risk level styling
        risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
        risk_display = RISK_COLORS.get(risk_level, f"[{COLORS['yellow']}]UNKNOWN[/{COLORS['yellow']}]")
        
        # Create header
        header_text = Text()
        header_text.append(f"{ASCII_DECORATIONS['command']} ", style=COLORS["bright_purple"])
        header_text.append("Execute", style=f"{COLORS['bright_blue']} bold")
        header_text.append(" [", style=COLORS["bright_purple"])
        header_text.append(risk_display, style="")
        header_text.append(" Risk]", style=COLORS["bright_purple"])
        
        # Create a layout for a more compact, visually appealing display
        layout = Layout()
        
        # Split into main sections
        layout.split_column(
            Layout(name="header"),
            Layout(name="content")
        )
        
        # Set the header
        layout["header"].update(
            Panel(
                Syntax(command, "bash", theme="monokai", word_wrap=True, background_color="default"),
                title=header_text,
                title_align="center",
                border_style=COLORS["bright_purple"],
                box=BOX_STYLES["default"],
                padding=(0, 1),
            )
        )
        
        # Split content into sections
        layout["content"].split_row(
            Layout(name="left_panel", ratio=3),
            Layout(name="right_panel", ratio=2),
        )
        
        # Split left panel for explanation/insight
        if explanation:
            layout["left_panel"].update(
                Panel(
                    explanation,
                    title=f"{ASCII_DECORATIONS['insight']} Command Insight {ASCII_DECORATIONS['insight']}",
                    title_align="center",
                    border_style=COLORS["bright_blue"],
                    box=BOX_STYLES["default"],
                    padding=(1, 2)
                )
            )
        
        # Split right panel into sections
        layout["right_panel"].split_column(
            Layout(name="confidence", ratio=1),
            Layout(name="risk", ratio=1),
            Layout(name="preview", ratio=2 if preview else 0),
        )
        
        # Confidence score section
        if confidence_score is not None:
            # Calculate star display
            confidence_stars = int(confidence_score * 5)
            confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
            
            # Determine color based on confidence level
            if confidence_score > 0.8:
                confidence_color = COLORS["green"]
            elif confidence_score > 0.6:
                confidence_color = COLORS["bright_blue"]
            else:
                confidence_color = COLORS["bright_red"]
                
            confidence_section = Table.grid(padding=0)
            confidence_section.add_column()
            
            confidence_section.add_row(Text("Score:", style=f"{COLORS['bright_purple']} bold"))
            confidence_section.add_row(Text(f"{confidence_score:.2f}", style=f"{confidence_color} bold"))
            confidence_section.add_row(Text(confidence_display, style=confidence_color))
            confidence_section.add_row("")
            confidence_section.add_row(Text("(AI confidence in", style=f"{COLORS['purple']} italic"))
            confidence_section.add_row(Text("command accuracy)", style=f"{COLORS['purple']} italic"))
            
            layout["confidence"].update(
                Panel(
                    confidence_section,
                    title=f"{ASCII_DECORATIONS['confidence']} AI Confidence {ASCII_DECORATIONS['confidence']}",
                    title_align="center",
                    border_style=COLORS["purple"],
                    box=BOX_STYLES["default"],
                    padding=(0, 1)
                )
            )
            
        # Risk assessment section
        risk_section = Table.grid(padding=0)
        risk_section.add_column()
        
        risk_section.add_row(Text("✓ Level:", style=f"{COLORS['bright_purple']} bold"))
        risk_section.add_row(Text(risk_display, style=""))
        risk_section.add_row("")
        risk_section.add_row(Text("Reason:", style=f"{COLORS['bright_purple']} bold"))
        risk_section.add_row(Text(risk_reason, style=COLORS["bright_blue"]))
        
        layout["risk"].update(
            Panel(
                risk_section,
                title=f"{ASCII_DECORATIONS['risk']} Risk Assessment{ASCII_DECORATIONS['risk']}",
                title_align="center",
                border_style=COLORS["red"],
                box=BOX_STYLES["default"],
                padding=(0, 1)
            )
        )
        
        # Preview section (if available)
        if preview:
            layout["preview"].update(
                Panel(
                    preview,
                    title=f"{ASCII_DECORATIONS['preview']} Command Preview {ASCII_DECORATIONS['preview']}",
                    title_align="center",
                    border_style=COLORS["bright_blue"],
                    box=BOX_STYLES["default"],
                    padding=(0, 1)
                )
            )
        
        # Print the layout
        self._console.print(layout)
        
        # Add warning for critical operations
        if risk_level >= 4:  # CRITICAL
            warning_text = Text()
            warning_text.append("⚠️  ", style=COLORS["red"])
            warning_text.append("This is a CRITICAL risk operation", style=f"{COLORS['bright_red']} bold")
            warning_text.append(" ⚠️\n", style=COLORS["red"])
            warning_text.append("It may cause significant changes to your system or data loss.", style=COLORS["bright_red"])
            
            self._console.print(Panel(
                warning_text,
                border_style=COLORS["red"],
                box=BOX_STYLES["bold"],
                padding=(1, 2)
            ))

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
        prompt_panel = Text()
        prompt_panel.append(prompt_text, style=f"{COLORS['bright_purple']} bold")
        prompt_panel.append("\n\n", style="")
        prompt_panel.append("(", style=COLORS["bright_blue"])
        prompt_panel.append("y", style=COLORS["green"])
        prompt_panel.append("/", style=COLORS["bright_blue"])
        prompt_panel.append("n", style=COLORS["red"])
        prompt_panel.append(")", style=COLORS["bright_blue"])
        
        self._console.print(Panel(
            Align.center(prompt_panel),
            title=f"{ASCII_DECORATIONS['confirmation']} Awaiting Confirmation {ASCII_DECORATIONS['confirmation']}",
            title_align="center",
            border_style=COLORS["bright_purple"],
            box=BOX_STYLES["default"],
            padding=(1, 2)
        ))
        
        # Get the user's response
        self._console.print(f"[{COLORS['green']} bold]>>> [/{COLORS['green']} bold]", end="")
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
            spinner_with_text.append(spinner)
            spinner_with_text.append(" ")
            spinner_with_text.append(f"{elapsed:.2f}s", style=f"{COLORS['bright_blue']} bold")
            spinner_with_text.append(" - Executing command...")
            
            if with_philosophy:
                # For the philosophy quote
                quote_text = Text(quote, style=f"{COLORS['purple']} italic")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            panel = Panel(
                content,
                title="Command Execution",
                border_style=COLORS["bright_purple"],
                box=BOX_STYLES["default"],
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
                
                execution_time = time.time() - start_time # This is the correct variable
                live.update(
                    Panel(
                        # Use execution_time here
                        Text(f"Execution completed in {execution_time:.6f}s", style=f"{COLORS['bright_green']} bold"), 
                        title=f"{ASCII_DECORATIONS['success']} Angela Initialized {ASCII_DECORATIONS['success']}",
                        title_align="center",
                        border_style=COLORS["green"],
                        box=BOX_STYLES["default"],
                        padding=(0, 1)
                    )
                )
                
                # Brief pause to show completion
                await asyncio.sleep(0.5)
        except Exception as e:
            self._logger.error(f"Error in execution timer: {str(e)}")
            # Ensure we still wait for the process
            if process.returncode is None: # Check if process might still be running
                try:
                    # Wait for process with a timeout to avoid hanging indefinitely
                    await asyncio.wait_for(process.wait(), timeout=5.0) 
                    return_code = process.returncode if process.returncode is not None else -1
                except asyncio.TimeoutError:
                    self._logger.error("Timeout waiting for process to complete after error.")
                    if process.returncode is None: # if still none after timeout, try to kill
                        try:
                            process.kill()
                            await process.wait() # ensure it's reaped
                        except ProcessLookupError:
                            pass # process might have already exited
                        except Exception as kill_e:
                            self._logger.error(f"Error trying to kill process: {kill_e}")
                    return_code = -1 
                except Exception as proc_e:
                    self._logger.error(f"Further error waiting for process: {proc_e}")
                    return_code = -1
            elif process.returncode is not None: # Process already finished, just get its code
                return_code = process.returncode
            else: # Fallback if process object is in an unexpected state
                return_code = -1

            # Wait for the streams to complete, even in error cases
            # Use try-except for each to ensure one doesn't prevent the other
            try:
                await asyncio.wait_for(stdout_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._logger.error("Timeout waiting for stdout_task to complete after error.")
            except Exception as stream_e:
                self._logger.error(f"Error waiting for stdout_task: {stream_e}")
            
            try:
                await asyncio.wait_for(stderr_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._logger.error("Timeout waiting for stderr_task to complete after error.")
            except Exception as stream_e:
                self._logger.error(f"Error waiting for stderr_task: {stream_e}")
            
            # Recalculate execution_time up to the point of error handling completion
            execution_time = time.time() - start_time
        
        # Return the results
        return (
            "".join(stdout_chunks),
            "".join(stderr_chunks),
            return_code if isinstance(return_code, int) else -1, # Ensure return_code is an int
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
            spinner_with_text.append(spinner)
            spinner_with_text.append(" ")
            spinner_with_text.append(f"{elapsed:.2f}s", style=f"{COLORS['bright_blue']} bold")
            spinner_with_text.append(f" - {message}")
            
            if with_philosophy:
                # For the philosophy quote
                quote_text = Text(quote, style=f"{COLORS['purple']} italic")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            panel = Panel(
                content,
                title="Angela initializing...",
                border_style=COLORS["bright_purple"],
                box=BOX_STYLES["default"],
                padding=(1, 2)
            )
            
            return panel
        
        # Use try-except with asyncio.sleep to make it cancellable
        try:
            with Live(get_layout(), refresh_per_second=20, console=self._console, transient=True) as live:
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
        table = Table(
            title=title, 
            expand=False, 
            box=BOX_STYLES["default"],
            border_style=COLORS["bright_purple"],
            title_style=f"{COLORS['bright_blue']} bold",
            header_style=f"{COLORS['purple']} bold"
        )
        
        for name, style in columns:
            table.add_column(name, style=style or COLORS["bright_blue"])
            
        return table
    
    async def display_task_plan(self, plan: Any) -> None:
        """
        Display a task plan with rich interactive visualization.
        
        Args:
            plan: The task plan to display
        """
        # Create a table for the plan steps
        table = Table(
            title=f"{ASCII_DECORATIONS['plan']} Plan for: {plan.goal} {ASCII_DECORATIONS['plan']}", 
            box=BOX_STYLES["default"],
            border_style=COLORS["bright_purple"],
            title_style=f"{COLORS['bright_blue']} bold",
            header_style=f"{COLORS['purple']} bold"
        )
        
        table.add_column("#", style=COLORS["cyan"], no_wrap=True)
        table.add_column("Command", style=COLORS["green"])
        table.add_column("Explanation", style=COLORS["bright_blue"])
        table.add_column("Risk", style=COLORS["yellow"], no_wrap=True)
        table.add_column("Dependencies", style=COLORS["purple"], no_wrap=True)
        
        # Risk level names
        risk_names = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_styles = [COLORS["green"], COLORS["cyan"], COLORS["yellow"], COLORS["red"], COLORS["bright_red"]]
        
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
            title=f"{ASCII_DECORATIONS['plan']} Task Plan {ASCII_DECORATIONS['plan']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"]
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
        
        # Create a vibrant panel for the suggested command
        self._console.print(Panel(
            Syntax(command, "bash", theme="monokai", word_wrap=True, background_color="default"),
            title=f"{ASCII_DECORATIONS['command']} Command {ASCII_DECORATIONS['command']}",
            title_align="center",
            border_style=COLORS["bright_purple"],
            box=BOX_STYLES["default"],
            padding=(0, 1)
        ))
        
        # Show confidence if requested
        if with_confidence:
            confidence_color = COLORS["green"] if confidence > 0.8 else COLORS["bright_blue"] if confidence > 0.6 else COLORS["bright_red"]
            confidence_stars = int(confidence * 5)
            confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
            
            confidence_text = Text()
            confidence_text.append("Confidence: ", style=f"{COLORS['bright_purple']} bold")
            confidence_text.append(f"{confidence:.2f}", style=f"{confidence_color} bold")
            confidence_text.append(f" {confidence_display}", style=confidence_color)
            
            self._console.print(confidence_text)
        
        # Show explanation
        explanation_text = Text()
        explanation_text.append("Explanation:\n", style=f"{COLORS['bright_purple']} bold")
        explanation_text.append(explanation, style=COLORS["bright_blue"])
        
        self._console.print(explanation_text)
        
    def print_proactive_suggestion(self, suggestion: str, source: str = "AI") -> None:
        """
        Print a proactive suggestion.
        
        Args:
            suggestion: The suggestion text
            source: The source of the suggestion
        """
        self._console.print("\n")
        self._console.print(Panel(
            Text(suggestion, style=COLORS["bright_blue"]),
            title=f"{ASCII_DECORATIONS['insight']} Suggestion from {source} {ASCII_DECORATIONS['insight']}",
            title_align="center",
            border_style=COLORS["bright_purple"],
            box=BOX_STYLES["default"],
            padding=(1, 2)
        ))
    
    async def _display_dependency_graph(self, plan: Any) -> None:
        """
        Display a visual representation of the dependency graph.
        
        Args:
            plan: The task plan with dependencies
        """
        # Create a dependency tree
        tree = Tree(f"[{COLORS['bright_purple']} bold]Execution Flow[/{COLORS['bright_purple']} bold]", guide_style=f"{COLORS['bright_blue']} bold")
        
        # Track processed steps
        processed = set()
        
        # Add steps with no dependencies first (roots)
        roots = []
        for i, step in enumerate(plan.steps):
            if not step.dependencies:
                roots.append(i)
                node = tree.add(f"[{COLORS['cyan']}]Step {i+1}:[/{COLORS['cyan']}] {step.command[:30]}..." if len(step.command) > 30 else step.command)
                processed.add(i)
                
                # Add children recursively
                self._add_dependency_children(node, i, plan, processed)
        
        # Check if any steps were not processed (in case of circular dependencies)
        if len(processed) < len(plan.steps):
            for i, step in enumerate(plan.steps):
                if i not in processed:
                    node = tree.add(f"[{COLORS['cyan']}]Step {i+1}:[/{COLORS['cyan']}] {step.command[:30]}..." if len(step.command) > 30 else step.command)
                    processed.add(i)
                    
                    # Add children recursively
                    self._add_dependency_children(node, i, plan, processed)
        
        # Display the tree
        self._console.print(f"\n[{COLORS['bright_purple']} bold]Dependency Graph:[/{COLORS['bright_purple']} bold]")
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
                node = parent_node.add(f"[{COLORS['cyan']}]Step {i+1}:[/{COLORS['cyan']}] {step.command[:30]}..." 
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
        table = Table(
            title="Execution Results", 
            box=BOX_STYLES["default"],
            border_style=COLORS["bright_purple"],
            title_style=f"{COLORS['bright_blue']} bold",
            header_style=f"{COLORS['purple']} bold"
        )
        
        table.add_column("#", style=COLORS["cyan"], no_wrap=True)
        table.add_column("Command", style=COLORS["green"])
        table.add_column("Status", style=COLORS["bright_blue"], no_wrap=True)
        table.add_column("Output", style=COLORS["bright_blue"])
        
        # Add results to the table
        for i, result in enumerate(results):
            # Get the command
            command = result.get("command", plan.steps[i].command if i < len(plan.steps) else "Unknown")
            
            # Get status
            status = f"[{COLORS['green']}]Success[/{COLORS['green']}]" if result.get("success", False) else f"[{COLORS['bright_red']}]Failed[/{COLORS['bright_red']}]"
            
            # Get output (combine stdout and stderr)
            stdout = result.get("stdout", "").strip()
            stderr = result.get("stderr", "").strip()
            
            # Truncate output if too long
            output = stdout
            if stderr:
                if output:
                    output += "\n"
                output += f"[{COLORS['red']}]{stderr}[/{COLORS['red']}]"
            
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
            title=f"{ASCII_DECORATIONS['execution']} Multi-Step Execution {ASCII_DECORATIONS['execution']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"]
        ))
        
        self._console.print(table)
        
        # Display summary
        success_count = sum(1 for r in results if r.get("success", False))
        total_count = len(results)
        
        if success_count == total_count:
            self._console.print(f"[{COLORS['bright_green']} bold]All {total_count} steps completed successfully![/{COLORS['bright_green']} bold]")
        else:
            self._console.print(f"[{COLORS['yellow']} bold]{success_count} of {total_count} steps completed successfully[/{COLORS['yellow']} bold]")
            
            # Show which steps failed
            failed_steps = [i+1 for i, r in enumerate(results) if not r.get("success", False)]
            if failed_steps:
                self._console.print(f"[{COLORS['bright_red']} bold]Failed steps: {', '.join(map(str, failed_steps))}[/{COLORS['bright_red']} bold]")
    
    async def display_workflow(self, workflow: Any, variables: Dict[str, Any] = None) -> None:
        """
        Display a workflow with rich formatting.
        
        Args:
            workflow: The workflow to display
            variables: Optional variables for the workflow
        """
        # Create a table for the workflow steps
        table = Table(
            title=f"Workflow: {workflow.name}", 
            box=BOX_STYLES["default"],
            border_style=COLORS["bright_purple"],
            title_style=f"{COLORS['bright_blue']} bold",
            header_style=f"{COLORS['purple']} bold"
        )
        
        table.add_column("#", style=COLORS["cyan"], no_wrap=True)
        table.add_column("Command", style=COLORS["green"])
        table.add_column("Explanation", style=COLORS["bright_blue"])
        table.add_column("Options", style=COLORS["yellow"])
        
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
            title=f"{ASCII_DECORATIONS['plan']} Workflow: {workflow.name} {ASCII_DECORATIONS['plan']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"]
        ))
        
        self._console.print(table)
        
        # Display variables if provided
        if variables:
            var_table = Table(
                title="Variables", 
                box=BOX_STYLES["default"],
                border_style=COLORS["purple"],
                title_style=f"{COLORS['bright_blue']} bold"
            )
            
            var_table.add_column("Name", style=COLORS["cyan"])
            var_table.add_column("Value", style=COLORS["green"])
            
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
            title=f"{ASCII_DECORATIONS['file']} File Analysis {ASCII_DECORATIONS['file']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"]
        ))
        
        # Display language and type info
        file_type = analysis.get("type", "unknown")
        language = analysis.get("language")
        
        file_info_text = Text()
        file_info_text.append("File type: ", style=f"{COLORS['bright_purple']} bold")
        if language:
            file_info_text.append(f"{file_type} ({language})", style=COLORS["bright_blue"])
        else:
            file_info_text.append(file_type, style=COLORS["bright_blue"])
            
        self._console.print(file_info_text)
        
        # Display the analysis text
        analysis_text = Text()
        analysis_text.append("\nAnalysis:", style=f"{COLORS['bright_purple']} bold")
        analysis_text.append(f"\n{analysis.get('analysis', 'No analysis available')}", style=COLORS["bright_blue"])
        
        self._console.print(analysis_text)
    
    async def display_file_manipulation(self, manipulation: Dict[str, Any]) -> None:
        """
        Display file manipulation results with diff.
        
        Args:
            manipulation: The manipulation results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Changes to {manipulation.get('path', 'file')}",
            title=f"{ASCII_DECORATIONS['file']} File Manipulation {ASCII_DECORATIONS['file']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"]
        ))
        
        # Display the instruction
        instruction_text = Text()
        instruction_text.append("Instruction: ", style=f"{COLORS['bright_purple']} bold")
        instruction_text.append(manipulation.get('instruction', 'Unknown'), style=COLORS["bright_blue"])
        
        self._console.print(instruction_text)
        
        # Display the diff
        diff_text = Text()
        diff_text.append("\nChanges:", style=f"{COLORS['bright_purple']} bold")
        
        self._console.print(diff_text)
        
        syntax = Syntax(manipulation.get("diff", "No changes"), "diff", theme="monokai")
        self._console.print(syntax)
        
        # Show whether changes were applied
        if manipulation.get("changes_applied", False):
            self._console.print(f"[{COLORS['bright_green']} bold]Changes have been applied to the file.[/{COLORS['bright_green']} bold]")
        elif manipulation.get("dry_run", False):
            self._console.print(f"[{COLORS['bright_blue']} bold]Dry run: Changes were not applied to the file.[/{COLORS['bright_blue']} bold]")
        else:
            self._console.print(f"[{COLORS['yellow']} bold]Changes were not applied to the file.[/{COLORS['yellow']} bold]")
    
    async def display_file_search_results(self, search_results: Dict[str, Any]) -> None:
        """
        Display file search results.
        
        Args:
            search_results: The search results
        """
        self._console.print("\n")
        self._console.print(Panel(
            f"Search results in {search_results.get('path', 'file')}",
            title=f"{ASCII_DECORATIONS['search']} File Search {ASCII_DECORATIONS['search']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"]
        ))
        
        # Display the query
        query_text = Text()
        query_text.append("Query: ", style=f"{COLORS['bright_purple']} bold")
        query_text.append(search_results.get('query', 'Unknown'), style=COLORS["bright_blue"])
        
        self._console.print(query_text)
        
        # Display match count
        match_count = search_results.get("match_count", 0)
        self._console.print(f"[{COLORS['bright_purple']} bold]Found {match_count} matches[/{COLORS['bright_purple']} bold]")
        
        # Display matches
        if match_count > 0:
            matches = search_results.get("matches", [])
            
            for i, match in enumerate(matches, 1):
                self._console.print(f"\n[{COLORS['cyan']} bold]Match #{i}[/{COLORS['cyan']} bold] (Lines {match.get('line_start', '?')}-{match.get('line_end', '?')})")
                
                # Display the content with context
                syntax = Syntax(match.get("content", ""), search_results.get("language", "text"), theme="monokai", line_numbers=True)
                self._console.print(syntax)
                
                # Display explanation
                if "explanation" in match:
                    self._console.print(f"[{COLORS['bright_blue']} italic]{match['explanation']}[/{COLORS['bright_blue']} italic]")


# ATTENTION: This method is overridden below to fix the duplication issue!
def print_command_result(self, result: Dict[str, Any]) -> None:
    """
    Print a command execution result in a compact, visually appealing way.
    This method avoids duplicating information that's already been shown.
    
    Args:
        result: The command execution result dictionary
    """
    # Only print command and output - avoid repeating explanation or confidence
    
    # Extract components from the result
    command = result.get("command", "")
    stdout = result.get("stdout", "").strip()
    stderr = result.get("stderr", "").strip()
    
    # Print the output (if any)
    if stdout:
        self.print_output(stdout, OutputType.STDOUT)
    
    # Print error output (if any)
    if stderr:
        self.print_output(stderr, OutputType.STDERR)

# Add the method to TerminalFormatter
TerminalFormatter.print_command_result = print_command_result

async def display_complex_workflow_plan(self, workflow_plan: Any) -> None:
    """
    Display a complex workflow plan with vibrant styling.
    
    Args:
        workflow_plan: The workflow plan to display
    """
    self._console.print("\n")
    
    header_text = Text()
    header_text.append(f"{ASCII_DECORATIONS['plan']} ", style=COLORS["bright_purple"])
    header_text.append("Complex Workflow", style=f"{COLORS['bright_blue']} bold") 
    header_text.append(f" {ASCII_DECORATIONS['plan']}", style=COLORS["bright_purple"])
    
    # Display a header with the workflow name and description
    self._console.print(Panel(
        f"[{COLORS['bright_purple']} bold]{workflow_plan.name}[/{COLORS['bright_purple']} bold]\n\n"
        f"[{COLORS['bright_blue']}]{workflow_plan.description}[/{COLORS['bright_blue']}]",
        title=header_text,
        title_align="center",
        border_style=COLORS["purple"],
        box=BOX_STYLES["default"]
    ))
    
    # Create a table for the workflow steps
    table = Table(
        title="Execution Steps",
        box=BOX_STYLES["default"],
        border_style=COLORS["bright_purple"],
        title_style=f"{COLORS['purple']} bold",
        header_style=f"{COLORS['bright_blue']} bold"
    )
    
    # Determine columns based on step properties
    table.add_column("ID", style=COLORS["cyan"])
    table.add_column("Tool", style=COLORS["bright_blue"])
    table.add_column("Action", style=COLORS["green"])
    table.add_column("Description", style=COLORS["bright_purple"])
    table.add_column("Risk", style=COLORS["yellow"])
    
    # Extract step info and add to table
    for step_id, step in workflow_plan.steps.items():
        # Get tool and action
        tool = getattr(step, "tool", "")
        action = getattr(step, "action", "")
        
        # Get command if it exists
        command = getattr(step, "command", "")
        if command and not action:
            action = command
        
        # Format the description
        description = getattr(step, "description", "")
        
        # Format risk level
        risk_level = getattr(step, "risk_level", 0)
        risk_labels = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_colors = [
            COLORS["green"], 
            COLORS["cyan"], 
            COLORS["yellow"], 
            COLORS["red"], 
            COLORS["bright_red"]
        ]
        
        risk_idx = min(risk_level, len(risk_labels) - 1)
        risk_text = f"[{risk_colors[risk_idx]}]{risk_labels[risk_idx]}[/{risk_colors[risk_idx]}]"
        
        # Add row to table
        table.add_row(
            step_id,
            tool or "-",
            Text.from_markup(Syntax(action, "bash", theme="monokai").markup) if action else "-",
            description or "-",
            risk_text
        )
    
    # Display the steps table
    self._console.print(table)
    
    # Create a visual representation of the workflow flow
    flow_text = Text()
    flow_text.append("Workflow Flow:\n", style=f"{COLORS['bright_purple']} bold")
    
    # For each step, show connections
    for step_id, step in workflow_plan.steps.items():
        flow_text.append(f"{step_id} ", style=COLORS["cyan"])
        
        # Check for next steps
        next_steps = getattr(step, "next_steps", [])
        if next_steps:
            flow_text.append("→ ", style=COLORS["bright_blue"])
            for i, next_step in enumerate(next_steps):
                if i > 0:
                    flow_text.append(", ", style=COLORS["bright_blue"])
                flow_text.append(next_step, style=COLORS["cyan"])
        else:
            flow_text.append("(end)", style=COLORS["purple"])
        
        flow_text.append("\n")
    
    # Display flow
    self._console.print(Panel(
        flow_text,
        title="Execution Flow",
        title_align="center",
        border_style=COLORS["bright_blue"],
        box=BOX_STYLES["default"]
    ))
    
    # Show summary info
    tools_used = set()
    for step in workflow_plan.steps.values():
        tool = getattr(step, "tool", "")
        if tool:
            tools_used.add(tool)
    
    summary_text = Text()
    summary_text.append(f"Total Steps: ", style=f"{COLORS['bright_purple']} bold")
    summary_text.append(f"{len(workflow_plan.steps)}\n", style=COLORS["bright_blue"])
    
    summary_text.append(f"Tools Used: ", style=f"{COLORS['bright_purple']} bold")
    summary_text.append(f"{', '.join(sorted(tools_used)) if tools_used else 'None'}\n", style=COLORS["bright_blue"])
    
    summary_text.append(f"Estimated Duration: ", style=f"{COLORS['bright_purple']} bold")
    # Calculate estimated duration based on step count
    estimated_duration = len(workflow_plan.steps) * 15  # Simple estimate: 15 seconds per step
    minutes, seconds = divmod(estimated_duration, 60)
    summary_text.append(f"{int(minutes)} minutes {seconds} seconds", style=COLORS["bright_blue"])
    
    # Display summary
    self._console.print(Panel(
        summary_text,
        title="Workflow Summary",
        title_align="center",
        border_style=COLORS["purple"],
        box=BOX_STYLES["default"]
    ))

async def display_result_summary(self, result: Dict[str, Any]) -> None:
    """
    Display a beautiful summary of a command execution result.
    
    Args:
        result: The command execution result
    """
    # Extract data from the result
    command = result.get("command", "")
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    success = result.get("success", False)
    execution_time = result.get("execution_time", 0)
    
    # Create the output panels
    panels = []
    
    # Always show the command - with vibrant styling
    command_panel = Panel(
        Syntax(command, "bash", theme="monokai", word_wrap=True),
        title=f"{ASCII_DECORATIONS['command']} Command {ASCII_DECORATIONS['command']}",
        title_align="center",
        border_style=COLORS["bright_purple"],
        box=BOX_STYLES["default"],
        padding=(0, 1),
        width=min(len(command) + 10, self._console.width - 4) 
    )
    
    panels.append(command_panel)
    
    # Format the output (if any) - trim to content size
    if stdout.strip():
        stdout_panel = Panel(
            stdout.strip(),
            title=f"{ASCII_DECORATIONS['output']} Output {ASCII_DECORATIONS['output']}",
            title_align="center",
            border_style=COLORS["bright_blue"],
            box=BOX_STYLES["default"],
            padding=(0, 1),
            width=min(len(max(stdout.strip().split('\n'), key=len, default="")) + 10, self._console.width - 4)
        )
        panels.append(stdout_panel)
    
    # Format error output (if any)
    if stderr.strip():
        stderr_panel = Panel(
            stderr.strip(),
            title=f"{ASCII_DECORATIONS['error']} Error {ASCII_DECORATIONS['error']}",
            title_align="center",
            border_style=COLORS["bright_red"],
            box=BOX_STYLES["default"],
            padding=(0, 1),
            width=min(len(max(stderr.strip().split('\n'), key=len, default="")) + 10, self._console.width - 4)
        )
        panels.append(stderr_panel)
    
    # Print the panels one by one
    for panel in panels:
        self._console.print(panel)

async def confirm_advanced_plan_execution(self, plan: Any, dry_run: bool = False) -> bool:
    """
    Get confirmation for executing an advanced plan.
    
    Args:
        plan: The advanced plan to execute
        dry_run: Whether this is a dry run
        
    Returns:
        True if confirmed, False otherwise
    """
    if dry_run:
        return True  # No confirmation needed for dry run
    
    # Check for high-risk steps
    has_high_risk = False
    for step_id, step in plan.steps.items():
        if getattr(step, "estimated_risk", 0) >= 3:  # High risk
            has_high_risk = True
            break
    
    # Create a title
    title_text = Text()
    title_text.append(f"{ASCII_DECORATIONS['confirmation']} ", style=COLORS["bright_red"])
    title_text.append("Confirm Plan Execution", style=f"{COLORS['bright_purple']} bold")
    title_text.append(f" {ASCII_DECORATIONS['confirmation']}", style=COLORS["bright_red"])
    
    # Create confirmation text
    confirm_text = Text()
    
    if has_high_risk:
        confirm_text.append("⚠️  ", style=COLORS["bright_red"])
        confirm_text.append("This plan contains HIGH RISK operations", style=f"{COLORS['bright_red']} bold")
        confirm_text.append(" ⚠️\n\n", style=COLORS["bright_red"])
    
    confirm_text.append("Do you want to execute this advanced plan with ", style=COLORS["bright_blue"])
    confirm_text.append(f"{len(plan.steps)}", style=f"{COLORS['bright_purple']} bold")
    confirm_text.append(" steps?", style=COLORS["bright_blue"])
    
    # Add info about retry and recovery capabilities
    confirm_text.append("\n\nThe system will automatically attempt recovery if any step fails.", style=f"{COLORS['green']}")
    
    # Display the confirmation panel
    self._console.print(Panel(
        Align.center(confirm_text),
        title=title_text,
        title_align="center",
        border_style=COLORS["red"] if has_high_risk else COLORS["bright_purple"],
        box=BOX_STYLES["default"],
        padding=(1, 2)
    ))
    
    # Get confirmation
    self._console.print(f"[{COLORS['green']} bold]>>> [/{COLORS['green']} bold]", end="")
    response = input().strip().lower()
    
    # Consider empty response or y/yes as "yes"
    return not response or response in ("y", "yes")

# Register the new method
TerminalFormatter.display_complex_workflow_plan = display_complex_workflow_plan
TerminalFormatter.display_result_summary = display_result_summary
TerminalFormatter.confirm_advanced_plan_execution = confirm_advanced_plan_execution

# Global formatter instance
terminal_formatter = TerminalFormatter()
